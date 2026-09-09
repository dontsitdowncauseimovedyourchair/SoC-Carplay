"""Shared device/backend settings, loaded from the repository's local .env."""

import os
from pathlib import Path
from tempfile import gettempdir

from dotenv import load_dotenv

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parent
# An explicitly exported environment variable takes precedence over .env.
load_dotenv(REPO_DIR / ".env", override=False)


def asset_path(name):
    """Return a bundled media path independently of the working directory."""
    return str(PACKAGE_DIR / "media" / name)


SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
SPOTIFY_CACHE_PATH = os.getenv("SPOTIFY_CACHE_PATH", str(Path.home() / "spotify.cache"))

COPILOBA_SERVER_URL = os.getenv("COPILOBA_SERVER_URL", "http://localhost:5000/ask_audio")
AUDIO_RECORD_DEVICE = os.getenv("AUDIO_RECORD_DEVICE", "plughw:1,0")
AUDIO_TEMP_DIR = os.getenv("AUDIO_TEMP_DIR", gettempdir())
AUDIO_SINK = os.getenv("AUDIO_SINK", "")
CAMERA_DEVICE = os.getenv("CAMERA_DEVICE", "/dev/video7")
RPMSG_DEVICE = os.getenv("RPMSG_DEVICE", "/dev/ttyRPMSG0")
LIBRESPOT_EXEC = os.getenv("LIBRESPOT_EXEC", "librespot")
LIBRESPOT_CACHE_PATH = os.getenv("LIBRESPOT_CACHE_PATH", str(Path.home() / ".cache" / "librespot"))

WEATHER_LATITUDE = float(os.getenv("WEATHER_LATITUDE", "19.5556"))
WEATHER_LONGITUDE = float(os.getenv("WEATHER_LONGITUDE", "-99.2472"))
WEATHER_CITY = os.getenv("WEATHER_CITY", "López Mateos")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
PIPER_VOICE_MODEL = os.getenv("PIPER_VOICE_MODEL", "models/es_AR-daniela-high.onnx")
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "5000"))

# Bound slow devices and model services. HTTP values are connect/read timeouts.
COPILOBA_API_TOKEN = os.getenv("COPILOBA_API_TOKEN", "")
RECORD_TIMEOUT = float(os.getenv("RECORD_TIMEOUT", "12"))
PLAYBACK_TIMEOUT = float(os.getenv("PLAYBACK_TIMEOUT", "50"))
WHISPER_TIMEOUT = float(os.getenv("WHISPER_TIMEOUT", "60"))
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "30"))
PIPER_TIMEOUT = float(os.getenv("PIPER_TIMEOUT", "20"))
PIPER_LOAD_TIMEOUT = float(os.getenv("PIPER_LOAD_TIMEOUT", "60"))
ASSISTANT_READ_TIMEOUT = float(os.getenv(
    "ASSISTANT_READ_TIMEOUT", str(WHISPER_TIMEOUT + OLLAMA_TIMEOUT + PIPER_LOAD_TIMEOUT + PIPER_TIMEOUT + 20)
))
SPOTIFY_TIMEOUT = float(os.getenv("SPOTIFY_TIMEOUT", "5"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(2 * 1024 * 1024)))
MAX_RESPONSE_BYTES = int(os.getenv("MAX_RESPONSE_BYTES", str(2 * 1024 * 1024)))
MAX_RECORDING_SECONDS = float(os.getenv("MAX_RECORDING_SECONDS", "15"))
