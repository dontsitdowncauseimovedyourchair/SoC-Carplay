"""Run audio setup/volume commands outside GTK and own the librespot process."""

import subprocess
import threading

from carplay_project import config
from carplay_project.services.worker import SerialWorker


class SystemAudio:
    def __init__(self, dispatch):
        self.worker = SerialWorker(dispatch)
        self._lock = threading.Lock()
        self._closed = False
        self._librespot = None

    def start(self):
        self.worker.submit(self._start, key="startup")

    def _start(self):
        if config.AUDIO_SINK:
            try:
                subprocess.run(["pactl", "set-default-sink", config.AUDIO_SINK],
                               timeout=3, check=True, capture_output=True)
            except (OSError, subprocess.SubprocessError):
                pass  # Retain the current sink and still try Spotify Connect.
        already = subprocess.run(["pgrep", "-x", "librespot"], timeout=3,
                                 capture_output=True).returncode == 0
        with self._lock:
            if not already and not self._closed:
                self._librespot = subprocess.Popen([
                    config.LIBRESPOT_EXEC, "--name", "Copiloba", "--cache", config.LIBRESPOT_CACHE_PATH,
                ])

    def set_volume(self, value):
        return self.worker.submit(lambda: subprocess.run(
            ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", value],
            timeout=3, check=True, capture_output=True,
        ))

    def close(self):
        self.worker.close()
        with self._lock:
            self._closed = True
            process, self._librespot = self._librespot, None
        if process is not None:
            if process.poll() is None:
                process.terminate()
            def stop():
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            threading.Thread(target=stop, daemon=True).start()
