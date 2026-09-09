"""Single-flight voice capture, bounded backend requests, and cancellable playback."""

import base64
import json
import logging
from pathlib import Path
import subprocess
import tempfile
import threading
import time

import requests
from gi.repository import GLib

from carplay_project import config
from carplay_project.commands import validate_command
from carplay_project.audio_stream import CONTENT_TYPE, STREAM_VERSION, iter_audio
from carplay_project.services.playback import StreamingPlayer

log = logging.getLogger(__name__)


class CopilobaAssistant:
    def __init__(self, status_callback=None, command_callback=None, busy_callback=None):
        self.status_callback = status_callback
        self.command_callback = command_callback
        self.busy_callback = busy_callback
        self._busy = threading.Lock()
        self._process_lock = threading.Lock()
        self._process = None
        self._closed = threading.Event()
        self._generation = 0

    def _deliver(self, generation, callback, value):
        if not self._closed.is_set() and generation == self._generation and callback:
            callback(value)
        return False

    def _notify(self, callback, value):
        GLib.idle_add(self._deliver, self._generation, callback, value)

    def _run_process(self, command, timeout):
        with self._process_lock:
            if self._closed.is_set():
                raise RuntimeError("Assistant stopped")
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
            self._process = process
        try:
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
                raise
            if code:
                raise subprocess.CalledProcessError(code, command)
        finally:
            with self._process_lock:
                self._process = None

    def _listen_and_ask_worker(self):
        try:
            with tempfile.TemporaryDirectory(prefix="copiloba-", dir=config.AUDIO_TEMP_DIR) as directory:
                recording = Path(directory) / "recording.wav"
                self._notify(self.status_callback, "Háblale a Copiloba... (6s)")
                self._run_process([
                    "arecord", "-D", config.AUDIO_RECORD_DEVICE, "-c", "2", "-d", "6",
                    "-f", "S16_LE", "-r", "16000", str(recording),
                ], config.RECORD_TIMEOUT)
                if self._closed.is_set():
                    return
                self._notify(self.status_callback, "Pensando Lobamente...")
                headers = {}
                if config.COPILOBA_API_TOKEN:
                    headers["Authorization"] = f"Bearer {config.COPILOBA_API_TOKEN}"
                with recording.open("rb") as audio:
                    with requests.post(
                        config.COPILOBA_SERVER_URL,
                        files={"audio": ("recording.wav", audio, "audio/wav")},
                        headers=headers, stream=True,
                        timeout=(5, config.ASSISTANT_READ_TIMEOUT),
                    ) as response:
                        if response.status_code == 503:
                            self._notify(self.status_callback, "Copiloba está ocupada. Intenta de nuevo.")
                            return
                        response.raise_for_status()
                        if response.headers.get("Content-Type", "").split(";")[0] != CONTENT_TYPE:
                            raise ValueError("Unexpected audio response")
                        if response.headers.get("X-Copiloba-Stream-Version") != STREAM_VERSION:
                            raise ValueError("Unsupported audio stream version")
                        encoded = response.headers.get("X-Copiloba-Action", "")
                        if len(encoded) > 4096:
                            raise ValueError("Command header is too large")
                        command = validate_command(json.loads(base64.b64decode(encoded, validate=True)))
                        self._play_stream(response, command)
                self._notify(self.status_callback, "")
        except (requests.Timeout, TimeoutError, subprocess.TimeoutExpired):
            log.warning("Assistant operation timed out")
            self._notify(self.status_callback, "Copiloba tardó demasiado. Intenta de nuevo.")
        except Exception as exc:
            log.warning("Assistant failed: %s", type(exc).__name__)
            self._notify(self.status_callback, "No se pudo completar la solicitud. Intenta de nuevo.")
        finally:
            self._notify(self.busy_callback, False)
            self._busy.release()

    def _play_stream(self, response, command):
        player = None
        deadline = time.monotonic() + config.ASSISTANT_READ_TIMEOUT

        def network_chunks():
            for chunk in response.iter_content(chunk_size=1024):
                if self._closed.is_set():
                    raise RuntimeError("Assistant stopped")
                if time.monotonic() > deadline:
                    raise TimeoutError("Audio stream timed out")
                yield chunk

        try:
            for pcm in iter_audio(network_chunks(), config.MAX_RESPONSE_BYTES):
                if player is None:
                    with self._process_lock:
                        if self._closed.is_set():
                            return
                        player = StreamingPlayer(config.PLAYBACK_TIMEOUT, self._closed)
                        self._process = player.process
                    # Execute once, only after validated audio reaches the player.
                    player.write(pcm)
                    self._notify(self.command_callback, command)
                    self._notify(self.status_callback, "Copiloba responde...")
                else:
                    player.write(pcm)
            if player is not None:
                player.finish()
        finally:
            if player is not None:
                try:
                    player.close()
                finally:
                    with self._process_lock:
                        self._process = None

    def trigger_assistant(self):
        if self._closed.is_set() or not self._busy.acquire(blocking=False):
            return False
        self._generation += 1
        self._notify(self.busy_callback, True)
        try:
            threading.Thread(target=self._listen_and_ask_worker, daemon=True).start()
        except Exception:
            self._notify(self.busy_callback, False)
            self._busy.release()
            raise
        return True

    def close(self):
        self._closed.set()
        with self._process_lock:
            if self._process is not None and self._process.poll() is None:
                # kill() is immediate; the worker waits/reaps without blocking GTK.
                self._process.kill()
