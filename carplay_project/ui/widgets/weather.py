"""Weather and cabin temperature display."""

import requests
from gi.repository import GLib, GdkPixbuf, Gtk

from carplay_project import config
from carplay_project.services.worker import SerialWorker


class TemperatureWidget(Gtk.Box):
    """
    Small weather card that shows current temperature.
    Uses Open-Meteo (free, no API key needed).
    Latitude/Longitude default to Ciudad López Mateos, Mexico.
    """
    LAT = config.WEATHER_LATITUDE
    LON = config.WEATHER_LONGITUDE
    CITY = config.WEATHER_CITY

    # WMO weather code → emoji
    WMO_ICONS = {
        0: config.asset_path("weather/sun.png"),
        1: config.asset_path("weather/partly_cloudy.png"),
        2: config.asset_path("weather/cloudy.png"),
        3: config.asset_path("weather/cloud.png"),

        45: config.asset_path("weather/fog.png"),
        48: config.asset_path("weather/fog.png"),

        51: config.asset_path("weather/rain.png"),
        53: config.asset_path("weather/rain.png"),
        55: config.asset_path("weather/rain.png"),

        61: config.asset_path("weather/rain.png"),
        63: config.asset_path("weather/rain.png"),
        65: config.asset_path("weather/rain.png"),

        71: config.asset_path("weather/snow.png"),
        73: config.asset_path("weather/snow.png"),
        75: config.asset_path("weather/snow.png"),

        80: config.asset_path("weather/rain.png"),
        81: config.asset_path("weather/rain.png"),
        82: config.asset_path("weather/storm.png"),

        95: config.asset_path("weather/storm.png"),
        96: config.asset_path("weather/storm.png"),
        99: config.asset_path("weather/storm.png"),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.get_style_context().add_class("temp-card")
        self.set_size_request(160, -1)

        # Top row: icon + temperature
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top_row.set_halign(Gtk.Align.CENTER)

        self.lbl_icon = Gtk.Image()

        self.lbl_temp = Gtk.Label(label="--°C")
        self.lbl_temp.get_style_context().add_class("temp-value")

        top_row.pack_start(self.lbl_icon, False, False, 0)
        top_row.pack_start(self.lbl_temp, False, False, 0)

        self.lbl_city = Gtk.Label(label=self.CITY)
        self.lbl_city.get_style_context().add_class("temp-city")
        self.lbl_city.set_halign(Gtk.Align.CENTER)

        self.lbl_desc = Gtk.Label(label="Fetching…")
        self.lbl_desc.get_style_context().add_class("temp-label")
        self.lbl_desc.set_halign(Gtk.Align.CENTER)

        self.pack_start(top_row, False, False, 0)
        self.pack_start(self.lbl_city, False, False, 0)
        self.pack_start(self.lbl_desc, False, False, 0)

        self.lbl_cabin = Gtk.Label(label="")
        self.lbl_cabin.get_style_context().add_class("temp-cabin")
        self.lbl_cabin.set_halign(Gtk.Align.CENTER)
        self.lbl_cabin.set_no_show_all(True)  # aparece solo cuando hay dato real
        self.pack_start(self.lbl_cabin, False, False, 0)

        # Fetch on start, then every 10 minutes
        self.worker = SerialWorker(GLib.idle_add, capacity=1)
        self._fetch_async()
        self._timer = GLib.timeout_add_seconds(600, self._fetch_async)

    def set_cabin(self, temp, pressure=None):
        self.lbl_cabin.set_text(f"Cabina {temp:.1f}°C")
        self.lbl_cabin.show()

    def _fetch_async(self):
        self.worker.submit(
            self._fetch, lambda result: self._update_ui(*result),
            lambda error: self._update_ui(None, None, None), key="weather",
        )
        return True

    def _fetch(self):
        with requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": self.LAT, "longitude": self.LON,
            "current_weather": "true", "temperature_unit": "celsius",
        }, timeout=(5, 8)) as response:
            response.raise_for_status()
            weather = response.json()["current_weather"]
        code = int(weather["weathercode"])
        return round(weather["temperature"]), self.WMO_ICONS.get(code, config.asset_path("weather/cloud.png")), code

    def close(self):
        GLib.source_remove(self._timer)
        self.worker.close()

    def _update_ui(self, temp, icon, code):
        if temp is not None:

            self.lbl_temp.set_text(f"{temp}°C")

            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                icon,
                96,
                96,
                True
            )

            self.lbl_icon.set_from_pixbuf(pixbuf)

            self.lbl_desc.set_text(
                self._code_to_desc(code)
            )

        else:
            self.lbl_temp.set_text("--°C")
            self.lbl_desc.set_text("Sin conexión")

        return False

    @staticmethod
    def _code_to_desc(code):
        mapping = {
            0: "Despejado", 1: "Mayormente despejado",
            2: "Parcialmente nublado", 3: "Nublado",
            45: "Niebla", 48: "Niebla con escarcha",
            51: "Llovizna ligera", 53: "Llovizna moderada", 55: "Llovizna densa",
            61: "Lluvia ligera", 63: "Lluvia moderada", 65: "Lluvia fuerte",
            71: "Nevada ligera", 73: "Nevada moderada", 75: "Nevada intensa",
            80: "Chubascos ligeros", 81: "Chubascos moderados", 82: "Chubascos fuertes",
            95: "Tormenta", 96: "Tormenta con granizo", 99: "Tormenta intensa",
        }
        return mapping.get(code, "")
