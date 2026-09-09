"""Check .env discovery and precedence without loading the hardware UI."""

import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.package = self.root / "carplay_project"
        self.package.mkdir()
        source = Path(__file__).resolve().parents[1] / "carplay_project" / "config.py"
        shutil.copyfile(source, self.package / "config.py")
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def load_config(self):
        spec = importlib.util.spec_from_file_location(
            "isolated_config", self.package / "config.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_loads_env_next_to_package_from_another_working_directory(self):
        (self.root / ".env").write_text(
            'SPOTIFY_CLIENT_ID=test-client\n'
            'COPILOBA_SERVER_URL=http://backend.test:5000/ask_audio\n'
            'WEATHER_CITY="López Mateos"\n'
            'BACKEND_PORT=5010\n', encoding="utf-8"
        )
        other = self.root / "unrelated"
        other.mkdir()
        previous = Path.cwd()
        try:
            os.chdir(other)
            config = self.load_config()
        finally:
            os.chdir(previous)
        self.assertEqual(config.SPOTIFY_CLIENT_ID, "test-client")
        self.assertEqual(config.COPILOBA_SERVER_URL, "http://backend.test:5000/ask_audio")
        self.assertEqual(config.WEATHER_CITY, "López Mateos")
        self.assertEqual(config.BACKEND_PORT, 5010)
        self.assertEqual(config.asset_path("home.png"), str(self.package / "media" / "home.png"))

    def test_exported_environment_overrides_dotenv(self):
        (self.root / ".env").write_text("SPOTIFY_CLIENT_SECRET=file-value\n")
        os.environ["SPOTIFY_CLIENT_SECRET"] = "exported-value"
        self.assertEqual(self.load_config().SPOTIFY_CLIENT_SECRET, "exported-value")

    def test_defaults_without_dotenv(self):
        config = self.load_config()
        self.assertEqual(config.SPOTIFY_CLIENT_SECRET, "")
        self.assertEqual(config.AUDIO_SINK, "")
        self.assertEqual(config.BACKEND_PORT, 5000)
        self.assertEqual(config.CAMERA_DEVICE, "/dev/video7")

    def test_windows_paths_are_preserved(self):
        (self.root / ".env").write_text("PIPER_VOICE_MODEL='C:\\workspace\\piper\\voice.onnx'\n")
        self.assertEqual(self.load_config().PIPER_VOICE_MODEL, r"C:\workspace\piper\voice.onnx")


if __name__ == "__main__":
    unittest.main()
