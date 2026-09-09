import importlib
import types
import unittest
from unittest.mock import Mock, patch

from native_stubs import glib_stub

fake_glib = types.SimpleNamespace(
    IO_IN=1, IO_HUP=2, IO_ERR=4, IO_NVAL=8,
    timeout_add_seconds=Mock(return_value=10),
    io_add_watch=Mock(return_value=11), source_remove=Mock(),
)
with glib_stub(fake_glib):
    module = importlib.import_module('carplay_project.services.sensors')


class SensorTests(unittest.TestCase):
    def setUp(self):
        self.service = module.RPMsgSensorService()
        fake_glib.timeout_add_seconds.reset_mock()
        fake_glib.source_remove.reset_mock()

    def test_failed_handshake_closes_fd_and_stop_cancels_retry(self):
        with patch.object(module.os, 'open', return_value=42), patch.object(module.os, 'write', side_effect=OSError()), patch.object(module.os, 'close') as close:
            self.service.start()
            close.assert_called_once_with(42)
            self.service.stop()
        fake_glib.source_remove.assert_called_once_with(10)
        self.assertFalse(self.service._retry())
        self.assertEqual(fake_glib.timeout_add_seconds.call_count, 1)

    def test_eof_disconnects_without_spinning_and_retries_once(self):
        self.service._stopped = False
        self.service._fd = 42
        self.service._watch = 11
        with patch.object(module.os, 'read', return_value=b''), patch.object(module.os, 'close') as close:
            self.assertFalse(self.service._on_data(42, fake_glib.IO_IN))
            close.assert_called_once_with(42)
        self.service._schedule_retry()
        self.assertEqual(fake_glib.timeout_add_seconds.call_count, 1)
        self.service.stop()

    def test_oversized_partial_line_is_discarded_and_parser_recovers(self):
        self.service._stopped = False
        temperatures = []
        self.service.subscribe('env', lambda *args: temperatures.append(args))
        with patch.object(module.os, 'read', side_effect=[b'x' * 4097, b'BME280: 99\nBME280: 21.5 1000\n']):
            self.service._on_data(42, fake_glib.IO_IN)
            self.assertEqual(self.service._buffer, '')
            self.service._on_data(42, fake_glib.IO_IN)
        self.assertEqual(temperatures, [(21.5, 1000.0)])
