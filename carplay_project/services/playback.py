"""Stream PCM into aplay with nonblocking writes and a bounded playback deadline."""

import os
import select
import subprocess
import time

from carplay_project.audio_stream import SAMPLE_RATE


class StreamingPlayer:
    def __init__(self, timeout, cancelled):
        self.deadline = time.monotonic() + timeout
        self.cancelled = cancelled
        self.process = subprocess.Popen(
            ['aplay', '-r', str(SAMPLE_RATE), '-f', 'S16_LE', '-t', 'raw', '-c', '1'],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        try:
            os.set_blocking(self.process.stdin.fileno(), False)
        except Exception:
            self.close()
            raise

    def _remaining(self):
        if self.cancelled.is_set():
            raise RuntimeError("Playback cancelled")
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Audio playback timed out")
        return remaining

    def write(self, pcm):
        data = memoryview(pcm)
        fd = self.process.stdin.fileno()
        while data:
            remaining = self._remaining()
            if self.process.poll() is not None:
                raise RuntimeError("Audio player exited early")
            # Linux pipe writes stay responsive even if aplay stops consuming data.
            _, writable, _ = select.select([], [fd], [], min(0.1, remaining))
            if not writable:
                continue
            try:
                count = os.write(fd, data)
            except BlockingIOError:
                continue
            if count <= 0:
                raise RuntimeError("Audio player stopped accepting data")
            data = data[count:]

    def finish(self):
        self.process.stdin.close()
        try:
            code = self.process.wait(timeout=self._remaining())
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("Audio playback timed out") from exc
        if code:
            raise RuntimeError("Audio playback failed")

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=2)
        self.process.stdin.close()
