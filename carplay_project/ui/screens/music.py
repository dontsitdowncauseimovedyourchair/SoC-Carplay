"""Spotify playback screen and album artwork."""

from gi.repository import GLib, GdkPixbuf, Gtk

from carplay_project import config
from carplay_project.services.spotify import SpotifyService
from carplay_project.ui.backgrounds import MusicGradientBG
from carplay_project.ui.widgets.volume import VolumeWidget


class MusicScreen(Gtk.Overlay):
    def __init__(self, nav_callback, home_card, audio):
        self.home_card = home_card
        super().__init__()

        self.service = SpotifyService(GLib.idle_add)
        self._closed = False
        self.current_cover = None

        self.music_bg = MusicGradientBG()
        self.add(self.music_bg)

        fixed = Gtk.Fixed()
        self.add_overlay(fixed)

        # Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.get_style_context().add_class("sidebar-music")
        volume_widget = VolumeWidget(audio)
        fixed.put(volume_widget, 1050, 20)

        btn_back = Gtk.Button()
        pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            config.asset_path("home.png"), 50, 50, True)
        img = Gtk.Image.new_from_pixbuf(pix)
        btn_back.set_image(
            Gtk.Image.new_from_pixbuf(pix)
        )

        btn_back.set_relief(Gtk.ReliefStyle.NONE)

        btn_back.set_image(img)
        btn_back.get_style_context().add_class("circle-button")
        btn_back.connect("clicked", lambda x: nav_callback("home"))
        sidebar.pack_start(btn_back, False, False, 0)

        # Center content
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=25)
        center.set_halign(Gtk.Align.CENTER)
        center.set_valign(Gtk.Align.CENTER)

        self.album_image = Gtk.Image()
        self.album_image.set_halign(Gtk.Align.CENTER)
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale("album.jpg", 320, 320, True)
            self.album_image.set_from_pixbuf(pixbuf)

        except Exception:
            pass

        self.lbl_song = Gtk.Label(label="Loading...")
        self.lbl_song.get_style_context().add_class("hero-song")

        self.lbl_art = Gtk.Label(label="")
        self.lbl_art.get_style_context().add_class("hero-artist")

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=40)
        self.btn_prev = Gtk.Button()
        self.btn_play = Gtk.Button()
        self.btn_next = Gtk.Button()

        for (btn, path) in [
            (self.btn_prev, config.asset_path("rewind.png")),
            (self.btn_play, config.asset_path("play.png")),
            (self.btn_next, config.asset_path("next.png")),
        ]:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 80, 80, True)
            btn.set_image(Gtk.Image.new_from_pixbuf(pix))
            btn.get_style_context().add_class("transport-button")

        controls.pack_start(self.btn_prev, False, False, 0)
        controls.pack_start(self.btn_play, False, False, 0)
        controls.pack_start(self.btn_next, False, False, 0)

        self.btn_prev.connect("clicked", self.previous_track)
        self.btn_play.connect("clicked", self.toggle_play)
        self.btn_next.connect("clicked", self.next_track)

        fixed.put(sidebar, 0, 0)

        fixed.put(self.album_image, 150, 160)
        fixed.put(self.lbl_song, 600, 200)
        fixed.put(self.lbl_art, 600, 330)
        fixed.put(controls, 700, 450)

        self.update_spotify()
        self._poll_timer = GLib.timeout_add(2000, self.update_spotify)

    def update_spotify(self):
        if self._closed:
            return False
        self.service.poll(self._apply_playback, self._show_error)
        return True

    def _apply_playback(self, playback):
        if playback is None:
            self.lbl_song.set_text("No music playing")
            self.lbl_art.set_text("")
            self.home_card.update_card("No music playing", "")
            self.home_card.update_progress(0)
            self.album_image.clear()
            self.home_card.cover.clear()
            self.current_cover = None
            return
        self.lbl_song.set_text(playback["song"])
        self.lbl_art.set_text(playback["artist"])
        self.home_card.update_card(playback["song"], playback["artist"])
        self.home_card.update_progress(playback["progress"])
        if playback["cover"] != self.current_cover:
            self.album_image.clear()
            self.home_card.cover.clear()
        if playback["art"]:
            png, palette = playback["art"]
            loader = GdkPixbuf.PixbufLoader.new_with_type("png")
            loader.write(png)
            loader.close()
            pixbuf = loader.get_pixbuf()
            self.album_image.set_from_pixbuf(pixbuf)
            self.home_card.update_cover(pixbuf.scale_simple(300, 300, GdkPixbuf.InterpType.NEAREST))
            if palette:
                self.music_bg.set_palette(palette)
        self.current_cover = playback["cover"]

    def _show_error(self, error):
        self.lbl_song.set_text("Spotify no disponible")
        self.lbl_art.set_text("Revisa la conexión y la autorización")

    def _command(self, action, query=""):
        if not self.service.command(action, query, self._show_error):
            self.lbl_art.set_text("Spotify está ocupado. Intenta de nuevo.")

    def next_track(self, widget):
        self._command("next")

    def previous_track(self, widget):
        self._command("previous")

    def toggle_play(self, widget):
        self._command("toggle")

    def play_song(self, query):
        self._command("play", query)

    def close(self):
        self._closed = True
        GLib.source_remove(self._poll_timer)
        self.service.close()
