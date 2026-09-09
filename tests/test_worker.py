import threading
import unittest

from carplay_project.services.worker import SerialWorker


class WorkerTests(unittest.TestCase):
    def test_serial_bounded_queue_dedup_and_nonblocking_submission(self):
        callbacks = []
        worker = SerialWorker(lambda *args: callbacks.append(args), capacity=1)
        entered, release, done = threading.Event(), threading.Event(), threading.Event()
        self.addCleanup(worker.close)
        self.addCleanup(release.set)
        order = []

        def first():
            entered.set()
            if not release.wait(2):
                raise TimeoutError()
            order.append('first')
        self.assertTrue(worker.submit(first, key='poll'))
        self.assertTrue(entered.wait(1))
        self.assertFalse(worker.submit(lambda: None, key='poll'))
        self.assertTrue(worker.submit(lambda: (order.append('second'), done.set())))
        self.assertFalse(worker.submit(lambda: None))
        release.set()
        self.assertTrue(done.wait(1))
        self.assertEqual(order, ['first', 'second'])
        self.assertNotEqual(worker._thread.ident, threading.get_ident())

    def test_exception_does_not_kill_worker_and_late_callbacks_are_suppressed(self):
        delivered, ready = [], threading.Event()
        def dispatch(*args):
            delivered.append(args)
            ready.set()
        worker = SerialWorker(dispatch)
        self.addCleanup(worker.close)
        seen = []
        worker.submit(lambda: 1 / 0, error_callback=seen.append)
        self.assertTrue(ready.wait(1))
        ready.clear()
        worker.submit(lambda: 42, callback=seen.append)
        self.assertTrue(ready.wait(1))
        worker.close()
        for callback, *args in delivered:
            callback(*args)
        self.assertEqual(seen, [])
        self.assertFalse(worker.submit(lambda: None))
