"""Application window, screen navigation, and assistant command dispatch."""


from gi.repository import GLib, GdkPixbuf, Gtk

from carplay_project.services.copiloba_ai import CopilobaAssistant
from carplay_project.services.sensors import RPMsgSensorService
from carplay_project.services.system_audio import SystemAudio
from carplay_project.commands import validate_command
from carplay_project.ui.backgrounds import MainGradientBG
from carplay_project.ui.screens.camera import CameraScreen
from carplay_project.ui.screens.map import MapScreen
from carplay_project.ui.screens.music import MusicScreen
from carplay_project.ui.widgets.clock import ClockWidget
from carplay_project.ui.widgets.spotify_card import HomeSpotifyCard
from carplay_project.ui.widgets.weather import TemperatureWidget

from carplay_project import config


class CarPlayWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="CarPlay OS")
        self._closed = False
        self.audio = SystemAudio(GLib.idle_add)
        self.audio.start()
        self.fullscreen()

        # --- NEW GLOBAL OVERLAY ---
        self.global_overlay = Gtk.Overlay()
        self.add(self.global_overlay)

        # 1. Initialize the AI Assistant
        self.ai_assistant = CopilobaAssistant(
            status_callback=self.update_ai_status,
            command_callback=self.execute_command,
            busy_callback=self.set_ai_busy,
        )

        # 2. Create the floating AI Status Label
        self.ai_status_label = Gtk.Label(label="")
        self.ai_status_label.get_style_context().add_class("ai-status-bubble")
        self.ai_status_label.set_valign(Gtk.Align.START)  # Float at the top
        self.ai_status_label.set_halign(Gtk.Align.CENTER)  # Centered horizontally
        self.ai_status_label.set_margin_top(20)  # Push down slightly
        self.ai_status_label.set_no_show_all(True)  # Keep hidden by default

        # --- YOUR EXISTING STACK ---
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        # Add the stack as the base of the global overlay, and the label on top!
        self.global_overlay.add(self.stack)
        self.global_overlay.add_overlay(self.ai_status_label)

        # Home screen (must be built first so home_card exists)
        self.stack.add_named(self._build_home(), "home")

        # Music screen
        self.music_screen = MusicScreen(self.navigate, self.home_card, self.audio)
        self.stack.add_named(self.music_screen, "music")

        # Camera screen
        self.camera_screen = CameraScreen(self.navigate)
        self.stack.add_named(self.camera_screen, "camera")

        # Map screen
        self.map_screen = MapScreen(self.navigate)
        self.stack.add_named(self.map_screen, "map")

        self.sensors = RPMsgSensorService()
        self.sensors.subscribe("env", self.temp_widget.set_cabin)
        self.sensors.subscribe("gps", self.map_screen.update_gps)
        self.sensors.start()

    def _build_home(self):
        overlay = Gtk.Overlay()
        overlay.add(MainGradientBG())

        fixed = Gtk.Fixed()
        fixed.set_hexpand(True)
        fixed.set_vexpand(True)

        # Clock — top-right area
        clock = ClockWidget()
        fixed.put(clock, 550, 230)

        # Spotify card
        self.home_card = HomeSpotifyCard()
        fixed.put(self.home_card, 0, 0)

        # Temperature widget — top-left
        self.temp_widget = TemperatureWidget()
        fixed.put(self.temp_widget, 30, 500)

        # Dock — bottom-center
        dock = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        dock.get_style_context().add_class("floating-dock")

        def create_icon_button(path):
            btn = Gtk.Button()
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 42, 42, True)
            img = Gtk.Image.new_from_pixbuf(pixbuf)
            btn.set_image(img)
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.get_style_context().add_class("dock-button")
            return btn

        btn_music = Gtk.Button()
        pixmusic = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            config.asset_path("music.png"),
            70,
            70,
            True
        )
        btn_music.set_image(
            Gtk.Image.new_from_pixbuf(pixmusic)
        )

        btn_cam = Gtk.Button()
        pixcam = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            config.asset_path("camera.png"),
            70,
            70,
            True
        )
        btn_cam.set_image(
            Gtk.Image.new_from_pixbuf(pixcam)
        )
        # Map button — uses your map.png icon
        btn_map = Gtk.Button()
        pixmap = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            config.asset_path("map.png"),
            70,
            70,
            True
        )
        btn_map.set_image(
            Gtk.Image.new_from_pixbuf(pixmap)
        )

        btn_mic = self.btn_mic = Gtk.Button()
        pixmic = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            config.asset_path("copiloba.png"),
            70,
            70,
            True
        )
        btn_mic.set_image(
            Gtk.Image.new_from_pixbuf(pixmic)
        )

        btn_music.get_style_context().add_class("dock-button")
        btn_cam.get_style_context().add_class("dock-button")
        btn_map.get_style_context().add_class("dock-button")
        btn_mic.get_style_context().add_class("dock-button")

        for b in [btn_music, btn_cam, btn_map, btn_mic]:
            dock.pack_start(b, False, False, 0)

        btn_music.connect("clicked", lambda x: self.navigate("music"))
        btn_cam.connect("clicked", lambda x: self.navigate("camera"))
        btn_map.connect("clicked", lambda x: self.navigate("map"))
        btn_mic.connect("clicked", self.on_ai_button_clicked)

        fixed.put(dock, 600, 530)

        overlay.add_overlay(fixed)
        return overlay

    def navigate(self, name):
        if name == "camera":
            self.camera_screen.start_camera()
        else:
            self.camera_screen.stop_camera()
        self.stack.set_visible_child_name(name)

    def on_destroy(self, widget):
        self._closed = True
        self.ai_assistant.close()
        self.music_screen.close()
        self.map_screen.close()
        self.temp_widget.close()
        self.camera_screen.stop_camera()
        self.sensors.stop()
        self.audio.close()
        Gtk.main_quit()

    def on_ai_button_clicked(self, widget):
        self.ai_assistant.trigger_assistant()

    def set_ai_busy(self, busy):
        if not self._closed:
            self.btn_mic.set_sensitive(not busy)

    def update_ai_status(self, message):
        """Safely updates the floating AI label from the background thread."""
        if self._closed:
            return False
        if message:
            self.ai_status_label.set_text(message)
            self.ai_status_label.show()
        else:
            self.ai_status_label.hide()
        return False  # Required for GTK3 to prevent infinite loops

    def execute_command(self, cmd):
        """Llamado desde el hilo del asistente con el dict del servidor."""
        if self._closed:
            return
        try:
            command = validate_command(cmd)
        except ValueError:
            return
        if command["action"] != "none":
            self._run_command(command["action"], command["args"])

    def _run_command(self, action, args):
        try:
            if action == "volume_up":
                self._set_volume("10%+")
            elif action == "volume_down":
                self._set_volume("10%-")
            elif action == "volume_set":
                pct = max(0, min(100, int(args.get("percent", 50))))
                self._set_volume(f"{pct}%")

            elif action == "music_next":
                self.music_screen.next_track(None)
            elif action == "music_prev":
                self.music_screen.previous_track(None)
            elif action == "music_toggle":
                self.music_screen.toggle_play(None)
            elif action == "music_play":
                self._play_song(args.get("query", ""))

            elif action in ("open_music", "open_camera", "open_map", "open_home"):
                self.navigate(action.replace("open_", ""))

            elif action == "navigate_to":
                dest = (args.get("destination") or "").strip()
                if dest:
                    self.navigate("map")
                    self.map_screen._entry.set_text(dest)
                    self.map_screen._on_go_clicked(None)
        except Exception as e:
            print("Command error:", action, e)
        return False  # idle_add: ejecutar una sola vez

    def _set_volume(self, value):
        self.audio.set_volume(value)

    def _play_song(self, query):
        self.music_screen.play_song(query)
