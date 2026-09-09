import unittest
from unittest.mock import MagicMock, patch

from carplay_project.commands import validate_command
from carplay_project.backend.language import ask_copiloba


class CommandTests(unittest.TestCase):
    def test_rejects_invalid_shapes_and_arguments(self):
        for value in ([], None, 3, {"action": []}, {"action": "made_up"},
                      {"action": "none", "args": "wrong"},
                      {"action": "volume_set", "args": {"percent": True}},
                      {"action": "volume_set", "args": {"percent": 101}},
                      {"action": "music_play", "args": {"query": " "}},
                      {"action": "navigate_to", "args": {}},
                      {"action": "none", "say": 123}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_command(value, require_speech=True)

    def test_normalizes_valid_command(self):
        self.assertEqual(validate_command({"action": "navigate_to", "args": {
            "destination": " Puebla ", "extra": "ignored"}, "say": "ignored"}),
            {"action": "navigate_to", "args": {"destination": "Puebla"}})

    def test_invalid_ollama_output_preserves_fallback_destination(self):
        for raw in ('[]', 'null', '{"action": "invalid", "say": "Listo"}',
                    '{"action": "none", "say": 123}', 'not json'):
            response = MagicMock()
            response.__enter__.return_value = response
            response.json.return_value = {"response": raw}
            with self.subTest(raw=raw), patch('carplay_project.backend.language.requests.post', return_value=response):
                result = ask_copiloba("llévame a Puebla")
            self.assertEqual(result['action'], 'navigate_to')
            self.assertEqual(result['args'], {'destination': 'puebla'})
            response.__exit__.assert_called_once()

    def test_http_failure_uses_fallback(self):
        import requests
        response = MagicMock()
        response.__enter__.return_value = response
        response.raise_for_status.side_effect = requests.HTTPError()
        with patch('carplay_project.backend.language.requests.post', return_value=response):
            self.assertEqual(ask_copiloba('baja el volumen')['action'], 'volume_down')
