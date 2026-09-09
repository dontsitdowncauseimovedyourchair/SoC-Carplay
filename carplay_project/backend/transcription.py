"""Keep Whisper warm in a process that can be replaced after an inference hang."""

import multiprocessing

from carplay_project import config


def _whisper_worker(connection, model_name):
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        while True:
            path = connection.recv()
            try:
                segments, _ = model.transcribe(path, beam_size=5, language="es")
                text = " ".join(segment.text for segment in segments).strip()
                connection.send((True, text))
            except Exception:
                connection.send((False, "Speech recognition failed"))
    except (EOFError, BrokenPipeError):
        pass
    finally:
        connection.close()


class Transcriber:
    """Called serially by the server's admission lock; starts lazily on first use."""

    def __init__(self):
        self._process = None
        self._connection = None

    def transcribe(self, path):
        if self._process is None or not self._process.is_alive():
            self.close()
            context = multiprocessing.get_context("spawn")
            parent, child = context.Pipe()
            self._connection = parent
            self._process = context.Process(
                target=_whisper_worker, args=(child, config.WHISPER_MODEL), daemon=True
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
        try:
            self._connection.send(str(path))
            if not self._connection.poll(config.WHISPER_TIMEOUT):
                raise TimeoutError("Speech recognition timed out")
            success, text = self._connection.recv()
            if not success:
                raise RuntimeError(text)
            return text
        except (TimeoutError, EOFError, BrokenPipeError, OSError):
            self.close()
            raise

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
