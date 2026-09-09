"""Launch the Copiloba dashboard on the embedded board."""

# Also support the original `python carplay_project/main.py` invocation.
if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from carplay_project.ui.styles import load_all_css
from carplay_project.ui.window import CarPlayWindow
from gi.repository import Gst, Gtk


def main():
    Gst.init(None)
    load_all_css()
    win = CarPlayWindow()
    win.connect("destroy", win.on_destroy)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
