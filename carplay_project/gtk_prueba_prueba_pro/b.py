import sys

import gi

gi.require_version('Gtk', '4.0')

from gi.repository import GLib, Gtk, Gdk, Gio

class copilobaWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Copiloba")
        self.set_default_size(1024, 600)
        self.add_styles()
        self.dashboard()

    def add_styles(self):
        css = Gtk.CssProvider()
        css.load_from_file(Gio.File.new_for_path("styles/default.css"))
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def dashboard(self):
        grid = Gtk.Grid()
        grid.set_hexpand(True)
        grid.set_vexpand(True)

        self.set_child(grid)

        left = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)
        left.add_css_class("bordered")
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)
        right.add_css_class("bordered")

        grid.attach(left,0,1,3,1)
        grid.attach(right,3,1,2,1)

        grid.set_hexpand(True)
        grid.set_vexpand(True)
        grid.set_margin_start(15)
        grid.set_margin_end(15)
        grid.set_margin_top(15)
        grid.set_margin_bottom(15)

        left_label = Gtk.Label(label="HOLA")
        left_label.set_hexpand(True)
        left_label.set_vexpand(True)

        right_label = Gtk.Label(label="PAPUS")
        right_label.set_hexpand(True)
        right_label.set_vexpand(True)

        left.append(left_label)
        right.append(right_label)



def on_activate(app):
    win = copilobaWindow(app)
    win.present()

app = Gtk.Application(application_id="com.copiloba.inicio")
app.connect("activate", on_activate)
app.run(None)
