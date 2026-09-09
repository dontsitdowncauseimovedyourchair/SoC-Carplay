import base64
import importlib
import json
from pathlib import Path
import subprocess
import threading
import types
import unittest
from unittest.mock import MagicMock, Mock, patch

import requests

from native_stubs import glib_stub

from carplay_project.audio_stream import CONTENT_TYPE, STREAM_VERSION, audio_event, end_event

# Only GLib dispatch is replaced; network/files/process orchestration is the real code.
with glib_stub(types.SimpleNamespace(idle_add=Mock())):
    client_module = importlib.import_module('carplay_project.services.copiloba_ai')


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.callbacks = []
        self.dispatch = patch.object(client_module.GLib, 'idle_add', side_effect=lambda *args: self.callbacks.append(args))
        self.dispatch.start()
        self.addCleanup(self.dispatch.stop)
        self.command = Mock()
        self.busy = Mock()
        self.assistant = client_module.CopilobaAssistant(command_callback=self.command, busy_callback=self.busy)
        self.addCleanup(self.assistant.close)
        self.response = MagicMock()
        self.response.__enter__.return_value = self.response
        self.response.status_code = 200
        self.response.headers = {
            'Content-Type': CONTENT_TYPE,
            'X-Copiloba-Stream-Version': STREAM_VERSION,
            'X-Copiloba-Action': base64.b64encode(json.dumps({'action': 'open_camera', 'args': {}}).encode()).decode(),
        }
        self.response.iter_content.return_value = [audio_event(b'\0\0' * 10), end_event()]
        playback = patch.object(client_module, 'StreamingPlayer')
        self.player = playback.start().return_value
        self.addCleanup(playback.stop)
        self.files = []

    def process(self, command, timeout):
        self.files.append(Path(command[-1]))
        if command[0] == 'arecord':
            Path(command[-1]).write_bytes(b'recording')

    def run_worker(self):
        self.assertTrue(self.assistant._busy.acquire(blocking=False))
        self.assistant._listen_and_ask_worker()
        self.assertFalse(self.assistant._busy.locked())

    def flush(self):
        for callback, *args in self.callbacks:
            callback(*args)
        self.callbacks.clear()

    def test_success_closes_response_cleans_files_and_dispatches_once(self):
        with patch.object(self.assistant, '_run_process', side_effect=self.process), patch.object(client_module.requests, 'post', return_value=self.response) as post:
            self.run_worker()
        self.flush()
        self.command.assert_called_once_with({'action': 'open_camera', 'args': {}})
        self.busy.assert_called_once_with(False)
        self.assertTrue(all(not path.parent.exists() for path in self.files))
        self.response.__exit__.assert_called_once()
        self.assertIn('timeout', post.call_args.kwargs)

    def test_failed_download_or_invalid_command_never_executes_action(self):
        for failure in ('timeout', 'header', 'oversized', 'empty'):
            with self.subTest(failure=failure):
                self.response.headers['X-Copiloba-Action'] = 'bad' if failure == 'header' else base64.b64encode(b'{"action":"open_camera","args":{}}').decode()
                self.response.iter_content.side_effect = requests.Timeout() if failure == 'timeout' else None
                self.response.iter_content.return_value = [audio_event(b'\0\0' * 20), end_event()] if failure == 'oversized' else []
                with patch.object(self.assistant, '_run_process', side_effect=self.process), patch.object(client_module.requests, 'post', return_value=self.response), patch.object(client_module.config, 'MAX_RESPONSE_BYTES', 20):
                    self.run_worker()
                self.flush()
                self.command.assert_not_called()
                self.assertTrue(all(not path.parent.exists() for path in self.files))

    def test_repeated_taps_start_only_one_worker(self):
        with patch.object(client_module.threading, 'Thread') as thread:
            self.assertTrue(self.assistant.trigger_assistant())
            self.assertFalse(self.assistant.trigger_assistant())
            thread.return_value.start.assert_called_once()
        self.assistant._busy.release()

    def test_process_timeout_kills_and_reaps(self):
        process = Mock()
        process.wait.side_effect = [subprocess.TimeoutExpired('arecord', 1), 0]
        with patch.object(client_module.subprocess, 'Popen', return_value=process), self.assertRaises(subprocess.TimeoutExpired):
            self.assistant._run_process(['arecord'], 1)
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_count, 2)
        self.assertIsNone(self.assistant._process)

    def test_close_kills_active_process_and_suppresses_queued_callbacks(self):
        process = Mock()
        process.poll.return_value = None
        self.assistant._process = process
        self.assistant._notify(self.command, {'action': 'open_camera'})
        self.assistant.close()
        process.kill.assert_called_once()
        self.flush()
        self.command.assert_not_called()
        self.assertFalse(self.assistant.trigger_assistant())
        self.assistant._process = None

    def test_real_worker_finishes_after_network_failure(self):
        threads = []
        original = threading.Thread
        def create_thread(*args, **kwargs):
            thread = original(*args, **kwargs)
            threads.append(thread)
            return thread
        with patch.object(self.assistant, '_run_process', side_effect=self.process), patch.object(client_module.requests, 'post', side_effect=requests.ConnectionError()), patch.object(client_module.threading, 'Thread', side_effect=create_thread):
            self.assertTrue(self.assistant.trigger_assistant())
            threads[0].join(1)
        self.assertFalse(threads[0].is_alive())
        self.assertFalse(self.assistant._busy.locked())
        self.assertFalse(self.files[0].parent.exists())

    def test_playback_starts_before_download_finishes(self):
        def streaming():
            yield audio_event(b"\0\0" * 10)
            self.player.write.assert_called_once_with(b"\0\0" * 10)
            self.player.finish.assert_not_called()
            yield audio_event(b"\1\0" * 10)
            yield end_event()
        self.response.iter_content.side_effect = lambda **kwargs: streaming()
        with patch.object(self.assistant, '_run_process', side_effect=self.process), patch.object(client_module.requests, 'post', return_value=self.response):
            self.run_worker()
        self.flush()
        self.assertEqual(self.player.write.call_count, 2)
        self.player.finish.assert_called_once()
        self.player.close.assert_called_once()
        self.command.assert_called_once()

    def test_interrupted_stream_stops_player_without_replaying_command(self):
        def streaming():
            yield audio_event(b"\0\0" * 10)
            raise requests.ConnectionError('disconnected')
        self.response.iter_content.side_effect = lambda **kwargs: streaming()
        with patch.object(self.assistant, '_run_process', side_effect=self.process), patch.object(client_module.requests, 'post', return_value=self.response):
            self.run_worker()
        self.flush()
        self.player.close.assert_called_once()
        self.player.finish.assert_not_called()
        self.command.assert_called_once()
        self.assertIsNone(self.assistant._process)
