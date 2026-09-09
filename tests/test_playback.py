import subprocess
import sys
import tempfile
import threading
from pathlib import Path
import unittest
from unittest.mock import patch

from carplay_project.services.playback import StreamingPlayer


class PlaybackTests(unittest.TestCase):
    def make_player(self, script, timeout):
        original = subprocess.Popen
        with patch('carplay_project.services.playback.subprocess.Popen',
                   side_effect=lambda command, **kwargs: original([sys.executable, '-c', script], **kwargs)):
            player = StreamingPlayer(timeout, threading.Event())
        self.addCleanup(player.close)
        return player

    def test_streamed_bytes_arrive_intact_and_process_is_reaped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'received.pcm'
            player = self.make_player(
                f'import sys; from pathlib import Path; Path({str(path)!r}).write_bytes(sys.stdin.buffer.read())', 3
            )
            player.write(b'\0\0' * 1000)
            player.write(b'\1\0' * 1000)
            player.finish()
            self.assertEqual(path.read_bytes(), b'\0\0' * 1000 + b'\1\0' * 1000)
            self.assertEqual(player.process.returncode, 0)

    def test_player_that_stops_reading_cannot_block_writer_forever(self):
        player = self.make_player('import threading; threading.Event().wait(10)', 0.2)
        with self.assertRaises(TimeoutError):
            player.write(b'\0' * (1024 * 1024))
        player.close()
        self.assertIsNotNone(player.process.poll())

    def test_cancelled_playback_rejects_further_writes(self):
        player = self.make_player('import threading; threading.Event().wait(10)', 3)
        player.cancelled.set()
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            player.write(b'\0\0')
