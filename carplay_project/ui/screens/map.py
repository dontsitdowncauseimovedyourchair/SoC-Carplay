"""Map screen and destination search."""

from gi.repository import GLib, GdkPixbuf, Gtk, OsmGpsMap

from carplay_project.services.navigation import NavigationSystem

from carplay_project import config


class MapScreen(Gtk.Overlay):
    HOME_LAT = 19.59326
    HOME_LON = -99.22916
    HOME_ZOOM = 14

    def __init__(self, nav_callback):

        super().__init__()

        self._nav_system = NavigationSystem(GLib.idle_add)
        self._active_tracks = []

        self._origin_lat = self.HOME_LAT
        self._origin_lon = self.HOME_LON

        # =========================
        # MAPA
        # =========================

        self.map_widget = OsmGpsMap.Map()

        osd = OsmGpsMap.MapOsd(
            show_scale=True,
            show_coordinates=False
        )

        self.map_widget.layer_add(osd)

        self.map_widget.set_center_and_zoom(
            self.HOME_LAT,
            self.HOME_LON,
            self.HOME_ZOOM
        )

        self.add(self.map_widget)

        try:
            pin = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                config.asset_path("map.png"),
                48, 48, True
            )
            self.map_widget.image_add(19.59326, -99.22916, pin)
        except Exception as e:
            print("Marker error:", e)

        # =========================
        # UI ENCIMA DEL MAPA
        # =========================

        ui_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0
        )

        ui_box.set_halign(Gtk.Align.FILL)
        ui_box.set_valign(Gtk.Align.START)

        top_bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10
        )

        top_bar.set_margin_top(16)
        top_bar.set_margin_start(16)
        top_bar.set_margin_end(16)

        # =========================
        # HOME
        # =========================

        btn_home = Gtk.Button()

        try:

            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                config.asset_path("home.png"),
                42,
                42,
                True
            )

            btn_home.set_image(
                Gtk.Image.new_from_pixbuf(
                    pixbuf
                )
            )

        except:

            btn_home.set_label("⌂")

        btn_home.connect(
            "clicked",
            lambda _: nav_callback("home")
        )

        # =========================
        # BUSCADOR
        # =========================

        self._entry = Gtk.Entry()

        self._entry.set_placeholder_text(
            "Buscar destino..."
        )

        self._entry.set_hexpand(True)

        self._entry.connect(
            "activate",
            self._on_go_clicked
        )

        # =========================
        # BOTON IR
        # =========================

        btn_go = Gtk.Button(
            label="Ir"
        )

        btn_go.connect(
            "clicked",
            self._on_go_clicked
        )

        # =========================
        # LIMPIAR
        # =========================

        btn_clear = Gtk.Button(
            label="✕"
        )

        btn_clear.connect(
            "clicked",
            self._on_clear_clicked
        )

        # =========================
        # STATUS
        # =========================

        self._lbl_status = Gtk.Label(
            label=""
        )

        self._lbl_status.set_halign(
            Gtk.Align.CENTER
        )

        # =========================
        # LAYOUT
        # =========================

        top_bar.pack_start(
            btn_home,
            False,
            False,
            0
        )

        top_bar.pack_start(
            self._entry,
            True,
            True,
            0
        )

        top_bar.pack_start(
            btn_go,
            False,
            False,
            0
        )

        top_bar.pack_start(
            btn_clear,
            False,
            False,
            0
        )

        ui_box.pack_start(
            top_bar,
            False,
            False,
            0
        )

        ui_box.pack_start(
            self._lbl_status,
            False,
            False,
            0
        )

        self.add_overlay(ui_box)

        self._has_fix = False
        self._gps_chip = Gtk.Label(label="SIN GPS")
        self._gps_chip.get_style_context().add_class("gps-chip")
        self._gps_chip.set_halign(Gtk.Align.START)
        self._gps_chip.set_valign(Gtk.Align.END)
        self._gps_chip.set_margin_start(16)
        self._gps_chip.set_margin_bottom(16)
        self.add_overlay(self._gps_chip)

    def update_gps(self, lat, lon):
        self._origin_lat = lat
        self._origin_lon = lon
        self.map_widget.gps_add(lat, lon, 0.0)  # punto azul + rastro
        if not self._has_fix:
            self._has_fix = True
            self._gps_chip.set_text("GPS ●")
            self._gps_chip.get_style_context().add_class("gps-ok")
            self.map_widget.set_center_and_zoom(lat, lon, 15)

    # ====================================
    # HELPERS
    # ====================================

    def _set_status(self, text, visible=True):

        self._lbl_status.set_text(text)

        if visible:

            self._lbl_status.show()

        else:

            self._lbl_status.hide()

    def _on_go_clicked(self, widget):
        query = self._entry.get_text().strip()
        if not query:
            return
        if len(query) > 300:
            self._set_status("Escribe un destino más corto")
            return
        accepted = self._nav_system.find_route(
            query, self._origin_lat, self._origin_lon,
            self._on_route_result, self._on_route_error,
        )
        self._set_status("Buscando ruta..." if accepted else "Búsqueda ocupada. Intenta de nuevo.")

    def _on_route_result(self, result):
        lat, lon, coordinates = result
        track = OsmGpsMap.Track()
        for pt_lon, pt_lat in coordinates:
            track.add_point(OsmGpsMap.Point.new_degrees(pt_lat, pt_lon))
        self.map_widget.track_remove_all()
        self.map_widget.track_add(track)
        self.map_widget.set_center_and_zoom(lat, lon, 13)
        self._set_status("", False)

    def _on_route_error(self, error):
        self._set_status(str(error) if isinstance(error, ValueError)
                         else "No se pudo calcular la ruta. Revisa la conexión.")

    def close(self):
        self._nav_system.close()

    def _on_clear_clicked(self, widget):
        self._nav_system.cancel()

        try:

            self.map_widget.track_remove_all()

        except:

            pass

        self.map_widget.gps_clear()

        self._entry.set_text("")

        self._set_status(
            "",
            False
        )

        self.map_widget.set_center_and_zoom(
            self.HOME_LAT,
            self.HOME_LON,
            self.HOME_ZOOM
        )
