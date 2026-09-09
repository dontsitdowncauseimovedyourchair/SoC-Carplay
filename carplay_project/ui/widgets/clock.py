"""Dashboard clock."""

from datetime import datetime

from gi.repository import GLib, Gtk


class ClockWidget(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=30)
        self.lbl_date = Gtk.Label()
        self.lbl_clock = Gtk.Label()
        self.lbl_date.set_xalign(0.5)
        self.lbl_clock.set_xalign(0.5)
        self.lbl_date.get_style_context().add_class("date-label")
        self.lbl_clock.get_style_context().add_class("clock-label")
        self.pack_start(self.lbl_date, False, False, 0)
        self.pack_start(self.lbl_clock, False, False, 0)
        self.update_clock()
        GLib.timeout_add(1000, self.update_clock)

    def update_clock(self):
        now = datetime.now()
        self.lbl_clock.set_text(now.strftime("%H:%M"))
        self.lbl_date.set_text(now.strftime("%a %d %b"))
        return True
