import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

def on_activate(app):
    win = Gtk.ApplicationWindow(application=app)
    win.set_title("Infotainment Prototype")
    win.set_default_size(800, 480)

    # 1. The Master Container (Horizontal)
    # A window can only hold ONE child in GTK4, so we create a master box to hold everything.
    master_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
    master_box.set_margin_start(10)
    master_box.set_margin_end(10)
    master_box.set_margin_top(10)
    master_box.set_margin_bottom(10)
    win.set_child(master_box)

    # 2. The Sidebar (Vertical Box)
    sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

    # Create sidebar buttons
    btn_nav = Gtk.Button(label="🗺️ Map")
    btn_cam = Gtk.Button(label="📷 Camera")
    btn_music = Gtk.Button(label="🎵 Spotify")

    # Append buttons to the sidebar box
    sidebar.append(btn_nav)
    sidebar.append(btn_cam)
    sidebar.append(btn_music)

    # Add the completed sidebar to the master box
    master_box.append(sidebar)

    # 3. The Main Dashboard Area (Grid)
    grid = Gtk.Grid(column_spacing=10, row_spacing=10)

    # Force the grid to expand and consume all remaining screen space
    grid.set_hexpand(True)
    grid.set_vexpand(True)

    # Create placeholders for our core features
    map_placeholder = Gtk.Button(label="Main Viewport (Map / Camera Feed)")
    map_placeholder.set_hexpand(True)
    map_placeholder.set_vexpand(True)  # Stretches to fill available vertical space

    media_placeholder = Gtk.Button(label="Media Player Controls & Metadata")
    media_placeholder.set_vexpand(False)  # Keep this narrow at the bottom

    # Attach to grid: widget, column, row, width (columns to span), height (rows to span)
    grid.attach(map_placeholder, 0, 0, 1, 5)
    grid.attach(media_placeholder, 0, 5, 1, 1)

    # Add the grid to the right side of the master box
    master_box.append(grid)

    win.present()


app = Gtk.Application(application_id='com.prototype.dashboard')
app.connect('activate', on_activate)
app.run(None)