import gi
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Gdk

from colorthief import ColorThief

# EXTRAER COLOR DOMINANTE
color_thief = ColorThief("album.jpg")
dominant_color = color_thief.get_color(quality=1)

r, g, b = dominant_color

# COLOR MÁS OSCURO PARA EL DEGRADADO
dark_r = max(r - 70, 0)
dark_g = max(g - 70, 0)
dark_b = max(b - 70, 0)

# GENERAR CSS DINÁMICO
dynamic_css = f"""
window {{
    background: #111111;
}}

.background {{
    background-image: linear-gradient(
        135deg,
        rgba({r}, {g}, {b}, 0.95),
        rgba({dark_r}, {dark_g}, {dark_b}, 0.95)
    );
}}

/* SIDEBAR */

.sidebar {{
    background: rgba(30,30,30,0.55);

    border-radius: 35px;

    padding: 30px;

    min-width: 70px;
}}

/* MAIN DASHBOARD */

.dashboard {{

    background: rgba(255,255,255,0.10);

    border-radius: 50px;

    padding: 40px;
}}

/* DATE */

.date-label {{

    color: rgba(255,255,255,0.75);

    font-size: 20px;

    font-weight: 300;
}}

/* CLOCK */

.clock-label {{

    color: white;

    font-size: 120px;

    font-weight: 900;
}}

/* ALBUM COVER */

.album-cover {{

    border-radius: 30px;
}}

/* MAP CARD */

.map-card {{

    background: rgba(255,255,255,0.15);

    border-radius: 40px;

    padding: 20px;
}}

.map-text {{

    color: rgba(255,255,255,0.5);

    font-size: 42px;

    font-weight: bold;
}}

/* MUSIC CARD */

.music-card {{

    background: rgba(255,255,255,0.15);

    border-radius: 40px;

    padding: 30px;
}}

/* TEXT */

.artist-label {{

    color: rgba(255,255,255,0.7);

    font-size: 22px;
}}

.song-label {{

    color: white;

    font-size: 42px;

    font-weight: 900;
}}

.controls-label {{

    color: rgba(255,255,255,0.8);

    font-size: 60px;
}}

/* CIRCLE BUTTONS */

.circle-button {{

    background: rgba(255,255,255,0.15);

    border-radius: 999px;

    min-width: 90px;
    min-height: 90px;

    font-size: 36px;

    color: white;
}}

/* SIDEBAR APPS */

.sidebar-app {{

    background: #4dc7ff;

    color: black;

    border-radius: 999px;

    min-width: 70px;
    min-height: 70px;

    font-size: 28px;
}}

.spotify-app {{

    background: #1ed760;

    color: black;

    border-radius: 999px;

    min-width: 70px;
    min-height: 70px;

    font-size: 28px;
}}
"""

# GUARDAR CSS AUTOMÁTICAMENTE
with open("dynamic_style.css", "w") as f:
    f.write(dynamic_css)


class CarPlayApp(Gtk.Application):

    def __init__(self):
        super().__init__()

    def load_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("dynamic_style.css")

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def create_circle_button(self, icon):
        button = Gtk.Button(label=icon)
        button.add_css_class("circle-button")
        return button

    def do_activate(self):

        self.load_css()

        window = Gtk.ApplicationWindow(application=self)
        window.set_title("Jesucristo OS")
        window.set_default_size(1280, 720)

        overlay = Gtk.Overlay()

        background = Gtk.Box()
        background.add_css_class("background")

        overlay.set_child(background)

        main_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=30
        )

        main_box.set_margin_top(40)
        main_box.set_margin_bottom(40)
        main_box.set_margin_start(40)
        main_box.set_margin_end(40)

        overlay.add_overlay(main_box)

        # SIDEBAR
        sidebar = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=30
        )

        sidebar.add_css_class("sidebar")

        waze_btn = Gtk.Button(label="🙂")
        waze_btn.add_css_class("sidebar-app")

        spotify_btn = Gtk.Button(label="♫")
        spotify_btn.add_css_class("spotify-app")

        sidebar.append(Gtk.Box())
        sidebar.append(waze_btn)
        sidebar.append(spotify_btn)

        # DASHBOARD
        dashboard = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=20
        )

        dashboard.add_css_class("dashboard")

        top_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=20
        )

        # LEFT PANEL
        left_panel = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=15
        )

        date_label = Gtk.Label(label="Mon 18 May")
        date_label.add_css_class("date-label")

        clock_label = Gtk.Label(label="11:34")
        clock_label.add_css_class("clock-label")

        album_cover = Gtk.Picture.new_for_filename(
            "album.jpg"
        )

        album_cover.set_size_request(270, 270)
        album_cover.add_css_class("album-cover")

        # BUTTONS
        buttons_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=20
        )

        location_btn = self.create_circle_button("⌖")
        phone_btn = self.create_circle_button("📞")
        settings_btn = self.create_circle_button("⚙")

        buttons_row.append(location_btn)
        buttons_row.append(phone_btn)
        buttons_row.append(settings_btn)

        left_panel.append(date_label)
        left_panel.append(clock_label)
        left_panel.append(album_cover)
        left_panel.append(buttons_row)

        # RIGHT PANEL
        right_panel = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=20
        )

        map_card = Gtk.Box()
        map_card.set_size_request(500, 280)
        map_card.add_css_class("map-card")

        map_label = Gtk.Label(label="MAP")
        map_label.add_css_class("map-text")

        map_card.append(map_label)

        music_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10
        )

        music_card.set_size_request(500, 220)
        music_card.add_css_class("music-card")

        artist_label = Gtk.Label(label="Labrinth")
        artist_label.add_css_class("artist-label")

        song_label = Gtk.Label(label="ALL FOR US")
        song_label.add_css_class("song-label")

        controls = Gtk.Label(label="⏮  ⏸  ⏭")
        controls.add_css_class("controls-label")

        music_card.append(artist_label)
        music_card.append(song_label)
        music_card.append(controls)

        right_panel.append(map_card)
        right_panel.append(music_card)

        top_row.append(left_panel)
        top_row.append(right_panel)

        dashboard.append(top_row)

        main_box.append(sidebar)
        main_box.append(dashboard)

        window.set_child(overlay)

        window.present()


app = CarPlayApp()
app.run()