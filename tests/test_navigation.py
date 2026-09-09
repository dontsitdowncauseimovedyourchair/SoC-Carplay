import threading
import unittest
from unittest.mock import Mock

from carplay_project.services.navigation import NavigationSystem


class NavigationTests(unittest.TestCase):
    def test_clear_and_new_search_discard_old_results(self):
        callbacks, ready = [], threading.Event()
        def dispatch(*args):
            callbacks.append(args)
            ready.set()
        service = NavigationSystem(dispatch)
        self.addCleanup(service.close)
        service._fetch = Mock(side_effect=lambda query, *args: query)
        results, errors = [], []
        self.assertTrue(service.find_route('old', 0, 0, results.append, errors.append))
        self.assertTrue(ready.wait(1))
        ready.clear()
        service.cancel()
        self.assertTrue(service.find_route('new', 0, 0, results.append, errors.append))
        self.assertTrue(ready.wait(1))
        for callback, *args in callbacks:
            callback(*args)
        self.assertEqual(results, ['new'])
        self.assertEqual(errors, [])

    def test_failed_route_is_reported_on_dispatch_thread(self):
        callbacks, ready = [], threading.Event()
        service = NavigationSystem(lambda *args: (callbacks.append(args), ready.set()))
        self.addCleanup(service.close)
        service._fetch = Mock(side_effect=ValueError('No route'))
        errors = []
        service.find_route('unknown', 0, 0, Mock(), errors.append)
        self.assertTrue(ready.wait(1))
        self.assertEqual(errors, [])
        callback, *args = callbacks[0]
        callback(*args)
        self.assertEqual(str(errors[0]), 'No route')
