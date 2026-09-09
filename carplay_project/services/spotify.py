"""Serialize Spotify API/auth work and prepare album art outside the GTK thread."""

from io import BytesIO
import logging

from colorthief import ColorThief
from PIL import Image
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from carplay_project import config
from carplay_project.services.worker import SerialWorker

log = logging.getLogger(__name__)


class CachedSpotifyOAuth(SpotifyOAuth):
    def get_auth_response(self, open_browser=None):
        # The dashboard must never block on stdin or a browser authorization flow.
        raise RuntimeError("Spotify authorization required; create a token cache before launching")


class SpotifyService:
    def __init__(self, dispatch):
        self.worker = SerialWorker(dispatch)
        self._client = None
        self._cover = None

    def _get_client(self):
        if self._client is None:
            auth = CachedSpotifyOAuth(
                client_id=config.SPOTIFY_CLIENT_ID,
                client_secret=config.SPOTIFY_CLIENT_SECRET,
                redirect_uri=config.SPOTIFY_REDIRECT_URI,
                scope="user-read-playback-state user-modify-playback-state",
                cache_path=config.SPOTIFY_CACHE_PATH, open_browser=False,
                requests_timeout=(5, config.SPOTIFY_TIMEOUT),
            )
            self._client = spotipy.Spotify(
                auth_manager=auth, requests_timeout=(5, config.SPOTIFY_TIMEOUT),
                retries=0, status_retries=0,
            )
        return self._client

    def poll(self, callback, error_callback):
        return self.worker.submit(self._snapshot, callback, error_callback, key="poll")

    def _snapshot(self):
        playback = self._get_client().current_playback()
        track = (playback or {}).get("item")
        if not track:
            self._cover = None
            return None
        images = (track.get("album") or {}).get("images") or []
        cover = images[0].get("url") if images else None
        result = {
            "song": track.get("name", ""),
            "artist": ", ".join(a.get("name", "") for a in track.get("artists", [])),
            "progress": min(1, max(0, (playback.get("progress_ms") or 0)
                                  / max(1, track.get("duration_ms") or 1))),
            "cover": cover, "art": None,
        }
        if cover and cover != self._cover:
            try:
                result["art"] = self._artwork(cover)
                self._cover = cover  # Failures remain eligible for the next poll.
            except Exception as exc:
                log.warning("Album artwork failed: %s", type(exc).__name__)
        if not cover:
            self._cover = None
        return result

    @staticmethod
    def _artwork(url):
        data = bytearray()
        with requests.get(url, timeout=(5, 10), stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_content(16384):
                data.extend(chunk)
                if len(data) > 5 * 1024 * 1024:
                    raise ValueError("Album artwork is too large")
        with Image.open(BytesIO(data)) as original:
            if original.width * original.height > 16_000_000:
                raise ValueError("Album dimensions are too large")
            small = original.convert("RGB").resize((32, 32), Image.Resampling.NEAREST)
            output = BytesIO()
            small.resize((410, 410), Image.Resampling.NEAREST).save(output, format="PNG")
        palette = None
        try:
            palette = ColorThief(BytesIO(data)).get_palette(color_count=6)
        except Exception:
            log.warning("Could not extract album palette")
        return output.getvalue(), palette

    def command(self, action, query="", error_callback=None):
        def task():
            sp = self._get_client()
            if action == "next":
                sp.next_track()
            elif action == "previous":
                sp.previous_track()
            elif action == "toggle":
                playback = sp.current_playback()
                if playback and playback.get("is_playing"):
                    sp.pause_playback()
                else:
                    sp.start_playback(device_id=self._device_id(sp))
            elif action == "play" and query:
                items = sp.search(q=query, type="track", limit=1).get("tracks", {}).get("items", [])
                if not items:
                    raise ValueError("No matching song")
                sp.start_playback(device_id=self._device_id(sp), uris=[items[0]["uri"]])
        return self.worker.submit(task, error_callback=error_callback)

    @staticmethod
    def _device_id(sp):
        return next((d["id"] for d in sp.devices().get("devices", [])
                     if d.get("name") == "Copiloba"), None)

    def close(self):
        self.worker.close()
