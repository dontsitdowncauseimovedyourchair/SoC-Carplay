from io import BytesIO
import threading
import unittest
from unittest.mock import MagicMock, Mock, patch

from PIL import Image

from carplay_project.services.spotify import CachedSpotifyOAuth, SpotifyService


class SpotifyTests(unittest.TestCase):
    def test_missing_token_fails_without_interactive_login(self):
        auth = object.__new__(CachedSpotifyOAuth)
        with self.assertRaisesRegex(RuntimeError, 'authorization required'):
            auth.get_auth_response()

    def test_poll_and_commands_share_one_background_thread(self):
        delivered, ready = [], threading.Event()
        service = SpotifyService(lambda *args: (delivered.append(args), ready.set()))
        self.addCleanup(service.close)
        ids, entered, release, done = [], threading.Event(), threading.Event(), threading.Event()
        self.addCleanup(release.set)
        client = Mock()
        service._client = client
        def playback():
            ids.append(threading.get_ident())
            entered.set()
            release.wait(2)
            return None
        def next_track():
            ids.append(threading.get_ident())
            done.set()
        client.current_playback.side_effect = playback
        client.next_track.side_effect = next_track
        self.assertTrue(service.poll(Mock(), Mock()))
        self.assertTrue(entered.wait(1))
        self.assertFalse(service.poll(Mock(), Mock()))
        self.assertTrue(service.command('next'))
        release.set()
        self.assertTrue(done.wait(1))
        self.assertEqual(len(set(ids)), 1)
        self.assertNotEqual(ids[0], threading.get_ident())

    def test_failed_artwork_is_retried(self):
        service = SpotifyService(lambda *args: None)
        self.addCleanup(service.close)
        service._client = Mock()
        service._client.current_playback.return_value = {
            'item': {'name': 'Song', 'artists': [], 'duration_ms': 0,
                     'album': {'images': [{'url': 'https://example.test/art'}]}},
            'progress_ms': 0,
        }
        with patch.object(service, '_artwork', side_effect=[ValueError('offline'), (b'png', None)]) as artwork:
            self.assertIsNone(service._snapshot()['art'])
            self.assertEqual(service._snapshot()['art'], (b'png', None))
            self.assertEqual(artwork.call_count, 2)

    def test_artwork_is_processed_in_memory_and_response_closed(self):
        image = BytesIO()
        Image.new('RGB', (40, 40), 'purple').save(image, format='PNG')
        response = MagicMock()
        response.__enter__.return_value = response
        response.iter_content.return_value = [image.getvalue()]
        with patch('carplay_project.services.spotify.requests.get', return_value=response):
            png, palette = SpotifyService._artwork('https://example.test/art')
        with Image.open(BytesIO(png)) as result:
            self.assertEqual(result.size, (410, 410))
        response.__exit__.assert_called_once()
