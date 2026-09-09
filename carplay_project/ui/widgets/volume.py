"""System volume controls."""

from gi.repository import GdkPixbuf, Gtk

from carplay_project import config


class VolumeWidget(Gtk.Box):

    def __init__(self, audio):
        self.audio = audio
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10
        )

        self.get_style_context().add_class(
            "volume-widget"
        )

        btn_down = Gtk.Button()
        btn_up = Gtk.Button()

        pix_down = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            config.asset_path("lessvolume.png"),
            40,
            40,
            True
        )

        pix_up = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            config.asset_path("morevolume.png"),
            55,
            55,
            True
        )

        btn_down.set_image(
            Gtk.Image.new_from_pixbuf(pix_down)
        )

        btn_up.set_image(
            Gtk.Image.new_from_pixbuf(pix_up)
        )

        btn_down.connect(
            "clicked",
            self.volume_down
        )

        btn_up.connect(
            "clicked",
            self.volume_up
        )

        self.pack_start(btn_down, False, False, 0)
        self.pack_start(btn_up, False, False, 0)

    def volume_up(self, widget):
        self.audio.set_volume("5%+")

    def volume_down(self, widget):
        self.audio.set_volume("5%-")
