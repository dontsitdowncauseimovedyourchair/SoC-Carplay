"""Nonblocking OpenAMP/RPMsg sensor input."""

import logging
import os
import re

from gi.repository import GLib

from carplay_project import config


class RPMsgSensorService:
    """Lee los sensores del Cortex-M33 vía OpenAMP (/dev/ttyRPMSG0)
    sin bloquear GTK, y reparte las lecturas a quien se suscriba."""

    DEVICE = config.RPMSG_DEVICE
    FLOAT_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")

    def __init__(self):
        self._subs = {"gps": [], "env": [], "tof": [], "status": []}
        self._buffer = ""
        self._fd = -1
        self._watch = None
        self._retry_timer = None
        self._stopped = True
        self._discarding = False

    def subscribe(self, kind, callback):
        self._subs[kind].append(callback)

    def start(self):
        if not self._stopped:
            return
        self._stopped = False
        if not self._open():
            self._schedule_retry()

    def _schedule_retry(self):
        if not self._stopped and self._retry_timer is None:
            self._retry_timer = GLib.timeout_add_seconds(5, self._retry)

    def _retry(self):
        self._retry_timer = None
        if not self._stopped and not self._open():
            self._schedule_retry()
        return False

    def _close_fd(self):
        if self._fd >= 0:
            try:
                os.close(self._fd)
            except OSError:
                pass
        self._fd = -1
        self._buffer = ""
        self._discarding = False

    def _open(self):
        try:
            self._fd = os.open(self.DEVICE, os.O_RDWR | os.O_NONBLOCK)
            os.write(self._fd, b"wake up!\n")
            self._watch = GLib.io_add_watch(
                self._fd, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR | GLib.IO_NVAL, self._on_data
            )
            self._emit("status", True)
            return True
        except OSError:
            self._close_fd()
            self._emit("status", False)
            return False

    def _disconnected(self):
        self._watch = None  # Returning False removes the currently executing watch.
        self._close_fd()
        self._emit("status", False)
        self._schedule_retry()
        return False

    def _on_data(self, fd, condition):
        if self._stopped:
            return False
        if condition & (GLib.IO_HUP | GLib.IO_ERR | GLib.IO_NVAL):
            return self._disconnected()
        try:
            data = os.read(fd, 512)
        except BlockingIOError:
            return True
        except OSError:
            return self._disconnected()
        if not data:
            return self._disconnected()
        self._buffer += data.decode("utf-8", errors="replace")
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if not self._discarding and len(line) <= 4096:
                self._parse(line.strip())
            self._discarding = False
        if len(self._buffer) > 4096:
            self._buffer = ""
            self._discarding = True
        return True

    def _parse(self, line):
        if ":" not in line:
            return
        tag, payload = line.split(":", 1)   # ¡el tag tiene dígitos, sepáralo!
        nums = [float(x) for x in self.FLOAT_RE.findall(payload)]

        if "NEO6MV2" in tag and len(nums) >= 2:
            lat, lon = nums[0], nums[1]
            if -90 <= lat <= 90 and -180 <= lon <= 180 and (lat or lon):
                self._emit("gps", lat, lon)
            # "Searching for satellites..." no trae números: se ignora solo

        elif "VL53L0X" in tag and nums:
            self._emit("tof", nums[0])                       # mm

        elif "BME280" in tag and nums:
            self._emit("env", nums[0],
                        nums[1] if len(nums) > 1 else None)  # T, P

    def _emit(self, kind, *args):
        for callback in self._subs.get(kind, []):
            try:
                callback(*args)
            except Exception:
                logging.getLogger(__name__).exception("Sensor subscriber failed")

    def stop(self):
        self._stopped = True
        for source in (self._watch, self._retry_timer):
            if source is not None:
                GLib.source_remove(source)
        self._watch = self._retry_timer = None
        self._close_fd()
