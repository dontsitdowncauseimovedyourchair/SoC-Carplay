import base64
from io import BytesIO
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import Mock, patch
import wave

from carplay_project.audio_stream import iter_audio
from carplay_project.copilobaserver import create_app


def wav_bytes(seconds=0.01):
    output = BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b'\0\0' * int(16000 * seconds))
    return output.getvalue()


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.transcriber = Mock()
        self.transcriber.transcribe.return_value = 'abre la cámara'
        self.synthesizer = Mock()
        self.synthesizer.stream.side_effect = lambda text: (part for part in (b"\0\0" * 10,))
        self.app = create_app(self.transcriber, self.synthesizer)
        self.app.config.update(TESTING=True, API_TOKEN='')
        self.client = self.app.test_client()
        self.paths = []

        def transcribe(path):
            self.paths.append(Path(path))
            self.assertTrue(Path(path).is_file())
            return 'abre la cámara'
        self.transcriber.transcribe.side_effect = transcribe
        self.ask = patch('carplay_project.copilobaserver.ask_copiloba', return_value={
            'action': 'open_camera', 'args': {}, 'say': 'Listo',
        })
        self.ask.start()
        self.addCleanup(self.ask.stop)

    def post(self, data=None, filename='../../server.py', headers=None, buffered=True):
        response = self.client.post('/ask_audio', data={
            'audio': (BytesIO(wav_bytes() if data is None else data), filename),
        }, headers=headers or {}, buffered=buffered)
        # Werkzeug's test multipart encoder owns a spooled request body for large WAVs.
        response.request.environ['wsgi.input'].close()
        self.addCleanup(response.close)
        return response

    def test_success_unique_files_and_cleanup(self):
        for _ in range(2):
            response = self.post()
            self.assertEqual(response.status_code, 200)
            command = json.loads(base64.b64decode(response.headers['X-Copiloba-Action']))
            self.assertEqual(command, {'action': 'open_camera', 'args': {}})
            self.assertEqual(b''.join(iter_audio([response.data], 100)), b'\0\0' * 10)
        self.assertNotEqual(self.paths[0], self.paths[1])
        self.assertTrue(all(not path.parent.exists() for path in self.paths))

    def test_missing_malformed_truncated_long_and_oversized_uploads(self):
        self.assertEqual(self.client.post('/ask_audio').status_code, 400)
        self.assertEqual(self.post(b'not a wav').status_code, 400)
        self.assertEqual(self.post(wav_bytes()[:-2]).status_code, 400)
        self.assertEqual(self.post(wav_bytes(16)).status_code, 400)
        self.app.config['MAX_CONTENT_LENGTH'] = 100
        self.assertEqual(self.post().status_code, 413)
        self.transcriber.transcribe.assert_not_called()

    def test_authentication_happens_before_processing(self):
        self.app.config['API_TOKEN'] = 'test-token'
        self.assertEqual(self.post().status_code, 401)
        self.assertEqual(self.post(headers={'Authorization': 'Bearer wrong'}).status_code, 401)
        self.transcriber.transcribe.assert_not_called()
        self.assertEqual(self.post(headers={'Authorization': 'Bearer test-token'}).status_code, 200)

    def test_busy_request_is_rejected_and_next_request_recovers(self):
        entered, release = threading.Event(), threading.Event()

        def blocked(path):
            entered.set()
            if not release.wait(2):
                raise TimeoutError()
            return 'hello'
        self.transcriber.transcribe.side_effect = blocked
        results = []
        thread = threading.Thread(target=lambda: results.append(self.post().status_code))
        thread.start()
        try:
            self.assertTrue(entered.wait(1))
            response = self.post()
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.headers['Retry-After'], '1')
        finally:
            release.set()
            thread.join(2)
        self.assertEqual(results, [200])
        self.assertEqual(self.post().status_code, 200)

    def test_timeout_cleans_upload_and_releases_admission(self):
        def timeout(path):
            self.paths.append(Path(path))
            raise TimeoutError()
        self.transcriber.transcribe.side_effect = timeout
        self.assertEqual(self.post().status_code, 504)
        self.assertFalse(self.paths[0].parent.exists())
        self.transcriber.transcribe.side_effect = lambda path: 'hello'
        self.assertEqual(self.post().status_code, 200)

    def test_speech_failure_is_json_error_without_command(self):
        self.synthesizer.stream.side_effect = RuntimeError("Piper failed")
        response = self.post()
        self.assertEqual(response.status_code, 502)
        self.assertTrue(response.is_json)
        self.assertNotIn('X-Copiloba-Action', response.headers)

    def test_empty_transcript_never_runs_speech(self):
        self.transcriber.transcribe.side_effect = lambda path: ' '
        self.assertEqual(self.post().status_code, 400)
        self.synthesizer.stream.assert_not_called()

    def test_stream_sends_first_chunk_before_synthesis_completes_and_holds_admission(self):
        completed, cancelled = [], []
        def speech(text):
            try:
                yield b"\0\0" * 10
                completed.append(True)
                yield b"\0\0" * 10
            finally:
                cancelled.append(True)
        self.synthesizer.stream.side_effect = speech
        response = self.post(buffered=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(completed, [])
        self.assertEqual(self.post().status_code, 503)
        response.close()
        self.assertEqual(cancelled, [True])
        self.assertFalse(self.app.extensions['admission'].locked())
        self.assertEqual(self.post().status_code, 200)

    def test_midstream_failure_has_error_marker_and_releases_admission(self):
        def speech(text):
            yield b"\0\0"
            raise TimeoutError("Piper stalled")
        self.synthesizer.stream.side_effect = speech
        response = self.post()
        self.assertEqual(response.status_code, 200)
        with self.assertRaises(RuntimeError):
            list(iter_audio([response.data], 100))
        self.assertFalse(self.app.extensions['admission'].locked())

    def test_response_closed_before_iteration_releases_admission(self):
        with self.app.test_request_context('/ask_audio', method='POST', data={
            'audio': (BytesIO(wav_bytes()), 'recording.wav'),
        }):
            response = self.app.full_dispatch_request()
            self.assertTrue(self.app.extensions['admission'].locked())
            response.close()
            self.assertFalse(self.app.extensions['admission'].locked())
