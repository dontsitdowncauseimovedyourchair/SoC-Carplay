"""GStreamer camera preview and parking guides."""

from gi.repository import GdkPixbuf, Gst, Gtk

from carplay_project import config


class CameraScreen(Gtk.Overlay):
    def __init__(self, nav_callback):
        super().__init__()
        self.pipeline = Gst.parse_launch(
            f'v4l2src device="{config.CAMERA_DEVICE}" ! '
            "image/jpeg,width=640,height=360 ! "
            "jpegdec ! videoconvert ! gtksink name=sink"
        )
        sink = self.pipeline.get_by_name("sink")
        video_widget = sink.get_property("widget")
        self.add(video_widget)

        btn_home = Gtk.Button()
        pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            config.asset_path("home.png"),
            50,
            50,
            True
        )
        btn_home.set_image(
            Gtk.Image.new_from_pixbuf(pix)
        )
        btn_home.set_halign(Gtk.Align.START)
        btn_home.set_valign(Gtk.Align.START)
        btn_home.set_margin_start(20)
        btn_home.set_margin_top(20)
        btn_home.set_size_request(64, 64)
        btn_home.connect("clicked", lambda x: nav_callback("home"))

        guide_layer = Gtk.DrawingArea()
        guide_layer.set_can_focus(False)
        guide_layer.set_sensitive(False)
        guide_layer.connect("draw", self.draw_guides)

        self.add_overlay(guide_layer)
        self.add_overlay(btn_home)

    def draw_guides(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cr.set_line_width(8)
        # Verde (lejos)
        cr.set_source_rgba(0, 1, 0, 0.85)
        cr.move_to(w * 0.20, h * 0.55);
        cr.line_to(w * 0.80, h * 0.55);
        cr.stroke()
        # Amarillo (medio)
        cr.set_source_rgba(1, 1, 0, 0.85)
        cr.move_to(w * 0.15, h * 0.72);
        cr.line_to(w * 0.85, h * 0.72);
        cr.stroke()
        # Rojo (peligro)
        cr.set_source_rgba(1, 0, 0, 0.85)
        cr.move_to(w * 0.10, h * 0.88);
        cr.line_to(w * 0.90, h * 0.88);
        cr.stroke()
        return False

    def start_camera(self):
        print("START CAMERA")
        self.pipeline.set_state(Gst.State.PLAYING)

    def stop_camera(self):
        self.pipeline.set_state(Gst.State.NULL)
