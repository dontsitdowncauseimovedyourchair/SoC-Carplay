"""Persistent Piper inference with streamed PCM and restartable process isolation."""

import multiprocessing
import threading
import time

from carplay_project import config
from carplay_project.audio_stream import CHUNK_BYTES, SAMPLE_RATE


def _piper_worker(connection, model_path, max_bytes):
    try:
        from piper import PiperVoice, SynthesisConfig

        voice = PiperVoice.load(model_path)
        if voice.config.sample_rate != SAMPLE_RATE:
            raise ValueError("The selected voice must produce 22050 Hz audio")
        # Preserve the existing voice's speed and 100 ms sentence pauses.
        settings = SynthesisConfig(length_scale=0.82)
        silence = b"\0\0" * int(SAMPLE_RATE * 0.1)
        connection.send(("ready", None))
        while True:
            text = connection.recv()
            try:
                total = 0
                for chunk in voice.synthesize(text, syn_config=settings):
                    if (chunk.sample_rate, chunk.sample_width, chunk.sample_channels) != (SAMPLE_RATE, 2, 1):
                        raise ValueError("Unexpected Piper audio format")
                    pcm = chunk.audio_int16_bytes
                    if not pcm or len(pcm) % 2:
                        raise ValueError("Invalid Piper audio")
                    total += len(pcm) + len(silence)
                    if total > max_bytes:
                        raise ValueError("Speech response is too large")
                    for data in (pcm, silence):
                        for offset in range(0, len(data), CHUNK_BYTES):
                            connection.send(("audio", data[offset:offset + CHUNK_BYTES]))
                if not total:
                    raise ValueError("Piper produced no speech")
                connection.send(("done", None))
            except Exception:
                connection.send(("error", None))
    except (EOFError, BrokenPipeError):
        pass
    except Exception:
        try:
            connection.send(("error", None))
        except (OSError, EOFError):
            pass
    finally:
        connection.close()


class PiperSynthesizer:
    def __init__(self):
        self._process = None
        self._connection = None
        self._busy = threading.Lock()

    def _receive(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not self._connection.poll(remaining):
            raise TimeoutError("Piper timed out")
        return self._connection.recv()

    def _start(self):
        if self._process is not None and self._process.is_alive():
            return
        self.close()
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        self._connection = parent
        self._process = context.Process(
            target=_piper_worker,
            args=(child, config.PIPER_VOICE_MODEL, config.MAX_RESPONSE_BYTES), daemon=True,
        )
        try:
            self._process.start()
        except Exception:
            parent.close()
            self._process.close()
            self._connection = self._process = None
            raise
        finally:
            child.close()
        kind, _ = self._receive(time.monotonic() + config.PIPER_LOAD_TIMEOUT)
        if kind != "ready":
            raise RuntimeError("Piper could not load the voice model")

    def stream(self, text):
        if not self._busy.acquire(blocking=False):
            raise RuntimeError("Piper is busy")
        completed = False
        try:
            self._start()
            self._connection.send(text)
            remaining = config.PIPER_TIMEOUT
            total = 0
            while True:
                started = time.monotonic()
                kind, data = self._receive(started + remaining)
                remaining -= time.monotonic() - started
                if kind == "done":
                    if not total:
                        raise RuntimeError("Piper produced no audio")
                    completed = True
                    return
                if kind != "audio" or not isinstance(data, bytes):
                    raise RuntimeError("Piper synthesis failed")
                total += len(data)
                if not 0 < len(data) <= CHUNK_BYTES or len(data) % 2 or total > config.MAX_RESPONSE_BYTES:
                    raise RuntimeError("Invalid Piper PCM output")
                yield data
        finally:
            # A cancelled/failed stream may leave unread frames or a blocked worker.
            if not completed:
                self.close()
            self._busy.release()

    def close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        if self._process is not None:
            if self._process.is_alive():
                self._process.terminate()
            self._process.join(timeout=2)
            if self._process.is_alive():
                self._process.kill()
                self._process.join(timeout=2)
            self._process.close()
            self._process = None
