import threading
import unittest
from unittest.mock import Mock, patch
import sys
import types

from carplay_project.backend.speech import PiperSynthesizer, _piper_worker


def warm_worker(connection, model_path, max_bytes):
    connection.send(('ready', None))
    try:
        while True:
            text = connection.recv()
            connection.send(('audio', b'\0\0'))
            if text == 'hang':
                threading.Event().wait(10)
            else:
                connection.send(('audio', b'\1\0'))
                connection.send(('done', None))
    except (EOFError, BrokenPipeError):
        pass
    finally:
        connection.close()


def failed_load(connection, model_path, max_bytes):
    connection.send(('error', None))
    connection.close()


class SpeechWorkerTests(unittest.TestCase):
    def setUp(self):
        self.synth = PiperSynthesizer()
        self.addCleanup(self.synth.close)
        worker = patch('carplay_project.backend.speech._piper_worker', warm_worker)
        worker.start()
        self.addCleanup(worker.stop)
        timeout = patch('carplay_project.config.PIPER_LOAD_TIMEOUT', 3)
        timeout.start()
        self.addCleanup(timeout.stop)

    def test_successive_requests_reuse_loaded_process(self):
        self.assertEqual(list(self.synth.stream('first')), [b'\0\0', b'\1\0'])
        pid = self.synth._process.pid
        self.assertEqual(list(self.synth.stream('second')), [b'\0\0', b'\1\0'])
        self.assertEqual(self.synth._process.pid, pid)

    def test_timeout_after_first_audio_kills_worker_and_next_request_recovers(self):
        with patch('carplay_project.config.PIPER_TIMEOUT', 0.1):
            stream = self.synth.stream('hang')
            self.assertEqual(next(stream), b'\0\0')
            with self.assertRaises(TimeoutError):
                next(stream)
        self.assertIsNone(self.synth._process)
        self.assertEqual(len(list(self.synth.stream('recovered'))), 2)

    def test_cancelled_stream_restarts_worker_and_concurrent_calls_are_rejected(self):
        stream = self.synth.stream('hang')
        self.assertEqual(next(stream), b'\0\0')
        with self.assertRaisesRegex(RuntimeError, 'busy'):
            next(self.synth.stream('overlapping'))
        stream.close()
        self.assertIsNone(self.synth._process)
        self.assertEqual(len(list(self.synth.stream('next'))), 2)

    def test_model_load_failure_releases_busy_lock(self):
        with patch('carplay_project.backend.speech._piper_worker', failed_load):
            with self.assertRaises(RuntimeError):
                next(self.synth.stream('first'))
        self.assertIsNone(self.synth._process)
        self.assertEqual(len(list(self.synth.stream('next'))), 2)


class PiperApiTests(unittest.TestCase):
    def test_actual_worker_loads_voice_once_for_multiple_requests(self):
        connection = Mock()
        connection.recv.side_effect = ['first', 'second', EOFError()]
        voice = Mock()
        voice.config.sample_rate = 22050
        chunk = types.SimpleNamespace(sample_rate=22050, sample_width=2,
                                      sample_channels=1, audio_int16_bytes=b"\0\0" * 10)
        voice.synthesize.side_effect = lambda *args, **kwargs: iter([chunk])
        piper = types.SimpleNamespace(PiperVoice=Mock(), SynthesisConfig=Mock())
        piper.PiperVoice.load.return_value = voice
        with patch.dict(sys.modules, {'piper': piper}):
            _piper_worker(connection, 'same-voice.onnx', 10000)
        piper.PiperVoice.load.assert_called_once_with('same-voice.onnx')
        piper.SynthesisConfig.assert_called_once_with(length_scale=0.82)
        self.assertEqual(voice.synthesize.call_count, 2)
        self.assertEqual(sum(call.args == (('done', None),) for call in connection.send.call_args_list), 2)
        connection.close.assert_called_once()
