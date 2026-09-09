"""Explicit terminal authorization; the dashboard only uses cached tokens."""

from spotipy.oauth2 import SpotifyOAuth

from carplay_project import config


def main():
    auth = SpotifyOAuth(
        client_id=config.SPOTIFY_CLIENT_ID,
        client_secret=config.SPOTIFY_CLIENT_SECRET,
        redirect_uri=config.SPOTIFY_REDIRECT_URI,
        scope="user-read-playback-state user-modify-playback-state",
        cache_path=config.SPOTIFY_CACHE_PATH,
        open_browser=False,
        requests_timeout=(5, config.SPOTIFY_TIMEOUT),
    )
    auth.get_access_token(as_dict=False)
    print("Spotify authorization saved to the configured token cache.")


if __name__ == "__main__":
    main()
