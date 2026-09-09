import threading
import unittest
from unittest.mock import patch

from carplay_project.backend.transcription import Transcriber


def hanging_worker(connection, model_name):
    threading.Event().wait(10)


def echo_worker(connection, model_name):
    try:
        while True:
            text = connection.recv()
            connection.send((True, text))
    except EOFError:
        pass
    finally:
        connection.close()


class TranscriptionTests(unittest.TestCase):
    def test_hung_worker_is_replaced_and_warm_worker_is_reused(self):
        transcriber = Transcriber()
        self.addCleanup(transcriber.close)
        with patch('carplay_project.backend.transcription._whisper_worker', hanging_worker), patch('carplay_project.config.WHISPER_TIMEOUT', 0.1):
            with self.assertRaises(TimeoutError):
                transcriber.transcribe('first.wav')
        self.assertIsNone(transcriber._process)
        with patch('carplay_project.backend.transcription._whisper_worker', echo_worker), patch('carplay_project.config.WHISPER_TIMEOUT', 3):
            self.assertEqual(transcriber.transcribe('second.wav'), 'second.wav')
            pid = transcriber._process.pid
            self.assertEqual(transcriber.transcribe('third.wav'), 'third.wav')
            self.assertEqual(transcriber._process.pid, pid)
