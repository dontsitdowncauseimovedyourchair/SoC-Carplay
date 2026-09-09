"""One daemon worker with bounded pending work and optional deduplication."""

import logging
import queue
import threading

log = logging.getLogger(__name__)


class SerialWorker:
    def __init__(self, dispatch, capacity=8):
        self._dispatch = dispatch
        self._queue = queue.Queue(maxsize=capacity)
        self._keys = set()
        self._lock = threading.Lock()
        self._closed = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def submit(self, task, callback=None, error_callback=None, key=None):
        with self._lock:
            if self._closed or (key is not None and key in self._keys):
                return False
            try:
                self._queue.put_nowait((task, callback, error_callback, key))
            except queue.Full:
                return False
            if key is not None:
                self._keys.add(key)
            return True

    def _deliver(self, callback, value):
        # This check runs on the UI thread, including for already queued callbacks.
        if not self._closed:
            callback(value)
        return False

    def _run(self):
        while True:
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                if self._closed:
                    return
                continue
            task, callback, error_callback, key = item
            try:
                if self._closed:
                    continue
                value = task()
                if callback:
                    self._dispatch(self._deliver, callback, value)
            except Exception as exc:
                log.warning("Background task failed: %s", exc)
                if error_callback:
                    self._dispatch(self._deliver, error_callback, exc)
            finally:
                with self._lock:
                    self._keys.discard(key)
                self._queue.task_done()

    def close(self):
        # Do not wait on network work from GTK; discard pending jobs/callbacks.
        with self._lock:
            self._closed = True
