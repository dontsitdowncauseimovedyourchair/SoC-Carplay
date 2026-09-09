"""Compact playback display for the home screen."""

from gi.repository import GdkPixbuf, Gtk, Pango

from carplay_project import config


class HomeSpotifyCard(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=25)
        self.set_size_request(100, 720)
        self.set_hexpand(False)
        self.set_vexpand(False)
        self.get_style_context().add_class("dashboard-music")

        self.cover = Gtk.Image()
        self.cover.set_size_request(50, 50)

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.lbl_song = Gtk.Label(label="No music playing")
        self.lbl_song.get_style_context().add_class("home-song")
        self.lbl_song.set_xalign(0)
        self.lbl_song.set_max_width_chars(18)
        self.lbl_song.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_song.set_line_wrap(False)
        self.lbl_song.set_size_request(180, -1)

        self.lbl_artist = Gtk.Label(label="")
        self.lbl_artist.get_style_context().add_class("home-artist")
        self.lbl_artist.set_xalign(0)

        self.progress = Gtk.ProgressBar()

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)

        btn_prev = Gtk.Button()
        pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            config.asset_path("rewind.png"),
            45,
            45,
            True
        )

        btn_prev.set_image(
            Gtk.Image.new_from_pixbuf(pix)
        )

        btn_play = Gtk.Button()
        play_pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            config.asset_path("play.png"),
            45,
            45,
            True
        )
        btn_play.set_image(
            Gtk.Image.new_from_pixbuf(play_pix)
        )
        btn_next = Gtk.Button()
        next_pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            config.asset_path("next.png"),
            45,
            45,
            True
        )
        btn_next.set_image(
            Gtk.Image.new_from_pixbuf(next_pix)
        )

        btn_prev.get_style_context().add_class("transport-button")
        btn_play.get_style_context().add_class("transport-button")
        btn_next.get_style_context().add_class("transport-button")

        controls.pack_start(btn_prev, False, False, 0)
        controls.pack_start(btn_play, False, False, 0)
        controls.pack_start(btn_next, False, False, 0)

        left.pack_start(self.cover, False, False, 0)
        left.pack_start(self.lbl_song, False, False, 0)
        left.pack_start(self.lbl_artist, False, False, 0)
        left.pack_start(self.progress, False, False, 0)
        left.pack_start(controls, False, False, 0)

        self.pack_start(left, True, True, 0)

    def update_progress(self, fraction):
        self.progress.set_fraction(fraction)

    def update_card(self, song, artist):
        self.lbl_song.set_text(song)
        self.lbl_artist.set_text(artist)

    def update_cover(self, pixbuf):
        print(pixbuf)
        self.cover.set_from_pixbuf(pixbuf)
