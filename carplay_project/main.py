
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gst", "1.0")
gi.require_version("OsmGpsMap", "1.0")
from gi.repository import Gtk, Gdk, GLib, Gst, OsmGpsMap, Pango
import cairo
import math
import os
import json
import urllib.request
import urllib.parse
from colorthief import ColorThief
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from gi.repository import GdkPixbuf
import random
import threading
from PIL import Image
import subprocess
from services.copiloba_ai import CopilobaAssistant
import colorsys  # stdlib, junto a tus otros imports
import re

# ─────────────────────────────────────────────
# 1. ESTILOS CSS
# ─────────────────────────────────────────────
def load_all_css():
    try:
        color_thief = ColorThief("album.jpg")
        r, g, b = color_thief.get_color(quality=1)
    except:
        r, g, b = 105, 17, 173  # Morado #6911AD
    dark_r, dark_g, dark_b = max(r - 70, 0), max(g - 70, 0), max(b - 70, 0)
    css = f"""
    * {{
        font-family: "Pixel Operator";
    }}
    .music-background {{
        background-image: linear-gradient(135deg, rgba({r},{g},{b},0.95),
        rgba({dark_r},{dark_g},{dark_b},0.95));
    }}
    .sidebar-music {{ background: transparent; border-radius: 0px; padding: 20px; }}
    .dashboard-music {{ background: rgba(255,255,255,0.1); border-radius: 0px; padding: 30px; }}
    .clock-label {{ color: white; font-size: 80px; font-weight: 900; }}

    .dock-button {{
        background: transparent;
        border: none;
        box-shadow: none;
        font-size: 35px;
        color: white;
        min-width: 80px;
        min-height: 80px;
    }}
    .circle-button {{
        background: rgba(255,255,255,0.1);
        border-radius: 0px;
        min-width: 80px; min-height: 80px;
        font-size: 30px; color: white; border: none;
    }}
    .date-label {{
        color: rgba(255,255,255,0.75);
        font-size: 50px;
        font-weight: 500;
    }}
    .clock-label {{
        color: white;
        font-family: "Pixel Operator HB 8";
        font-size: 120px;
        font-weight: 900;
    }}
    .hero-song {{
        font-size: 70px;
        font-weight: 900;
        color: white;
    }}
    .hero-artist {{
        font-size: 50px;
        color: rgba(255,255,255,0.75);
    }}
    .home-song {{
        font-size: 40px;
        font-weight: 700;
        color: white;
    }}

    .home-artist {{
        font-size: 30px;
        color: rgba(255,255,255,0.7);
    }}
    .transport-button {{
        background: transparent;
        border: none;
        box-shadow: none;
        font-size: 20px;
        color: white;
        min-height: 80px;
        min-width: 80px;
    }}
    .floating-dock {{
        background: rgba(255,255,255,0.20);
        border-radius: 0px;
        padding: 14px 28px;
    }}
    .dock-button {{
        background: transparent;
        border: none;
        box-shadow: none;
        padding: 12px;
    }}
    .dock-button:hover {{
        background: rgba(255,255,255,0.25);
        border-radius: 0px;
    }}

    /* Temperature widget */
    .temp-card {{
        background: rgba(255,255,255,0.12);
        border-radius: 0px;
        padding: 16px 22px;
    }}
    .temp-value {{
        color: white;
        font-size: 60px;
        font-weight: 900;
    }}
    .temp-label {{
        color: rgba(255,255,255,0.70);
        font-size: 30px;
        font-weight: 500;
    }}
    .temp-city {{
        color: rgba(255,255,255,0.85);
        font-size: 30px;
        font-weight: 600;
    }}

    .ai-status-bubble {{
        background: rgba(11, 12, 16, 0.85);
        color: #66FCF1;
        border-radius: 20px;
        padding: 15px 30px;
        font-size: 35px;
        font-weight: bold;
    }}
    
    .temp-cabin {{
        color: white;
        font-size: 28px;
        font-weight: 700;
    }}
    .gps-chip {{
        background: rgba(11, 12, 16, 0.75);
        color: rgba(255,255,255,0.55);
        padding: 8px 18px;
        font-size: 24px;
        font-weight: bold;
    }}
    .gps-ok {{ color: #00ff88; }}
    .distance-chip {{
        background: rgba(11, 12, 16, 0.75);
        padding: 10px 30px;
        font-size: 56px;
        font-weight: 900;
    }}
    .dist-far  {{ color: #00ff88; }}
    .dist-mid  {{ color: #ffe14d; }}
    .dist-near {{ color: #ff5555; }}
    """
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, 800
    )


# ─────────────────────────────────────────────
# 2. DIBUJOS CAIRO
# ─────────────────────────────────────────────
def rounded_rect(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.arc(x + w - r, y + r, r, 3 * math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.close_path()


class MainGradientBG(Gtk.DrawingArea):
    CELL = 20
    SQUARE = 13
    EDGE_CELLS = 2
    TEXTURE = 0.12  # qué tan visible es el patrón de cuadritos

    THEMES = [
        [(0.55, 0.18, 1.00), (0.35, 0.45, 1.00), (0.15, 0.70, 1.00)],  # violeta -> azul
        [(1.00, 0.15, 0.45), (1.00, 0.45, 0.80), (0.80, 0.35, 1.00)],  # rosa -> lila
        [(0.15, 0.90, 0.90), (0.10, 0.65, 1.00), (0.30, 0.35, 1.00)],  # cian -> azul
        [(1.00, 0.45, 0.15), (1.00, 0.75, 0.20), (1.00, 0.25, 0.55)],  # naranja -> rosa
        [(0.10, 0.85, 0.70), (0.15, 1.00, 0.55), (0.85, 1.00, 0.40)],  # turquesa -> lima
    ]

    def __init__(self):
        super().__init__()
        self.colors = random.choice(self.THEMES)
        self._cache = None
        self._cache_key = None
        self.connect("draw", self._draw)

    @staticmethod
    def _mix(c1, c2, t):
        return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(3))

    def _grad(self, t):
        a, b, c = self.colors
        t = max(0.0, min(1.0, t))
        if t < 0.5:
            return self._mix(a, b, t * 2)
        return self._mix(b, c, (t - 0.5) * 2)

    def _draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        if w <= 0 or h <= 0:
            return False

        key = (w, h, tuple(self.colors))
        if self._cache is None or self._cache_key != key:
            self._cache = self._render(w, h)
            self._cache_key = key

        cr.set_source_surface(self._cache, 0, 0)
        cr.paint()
        return False

    def _render(self, w, h):
        surf = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
        cr = cairo.Context(surf)

        # gradiente base, colores puros
        grad = cairo.LinearGradient(0, 0, w, 0)
        for pos in (0.0, 0.5, 1.0):
            r, g, b = self._grad(pos)
            grad.add_color_stop_rgb(pos, r, g, b)
        cr.set_source(grad)
        cr.paint()

        # cuadritos: versión apenas más clara / más oscura del color local
        cell, sq, k = self.CELL, self.SQUARE, self.TEXTURE
        off = (cell - sq) / 2
        cols = w // cell
        rows = h // cell + 1
        white, black = (1, 1, 1), (0, 0, 0)

        for ix in range(self.EDGE_CELLS, cols - self.EDGE_CELLS + 1):
            x = ix * cell
            base = self._grad((x + cell / 2) / w)
            ca = self._mix(base, white, k)
            cb = self._mix(base, black, k)
            for iy in range(rows):
                r, g, b = ca if (ix + iy) % 2 == 0 else cb
                cr.set_source_rgb(r, g, b)
                cr.rectangle(x + off, iy * cell + off, sq, sq)
                cr.fill()

        return surf


class MusicGradientBG(Gtk.DrawingArea):
    CELL = 13  # tamaño de celda (cuadro + espacio)
    SQUARE = 6  # tamaño del cuadrito
    SHIFT = 0.085  # qué tanto se desplaza el color de los cuadritos
    EDGE_CELLS = 2  # columnas sólidas en cada borde

    def __init__(self):
        super().__init__()
        self._cache = None
        self._cache_key = None
        self._set_stops([(168, 12, 40), (250, 235, 120), (0, 150, 84)])
        self.connect("draw", self._draw)

    # ---------- helpers ----------

    @staticmethod
    def _mix(c1, c2, t):
        return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(3))

    @staticmethod
    def _luma(c):
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    @staticmethod
    def _vivid(c, sat_boost=1.45, val_boost=1.15):
        """Sube saturación y brillo de un color extraído del cover."""
        h, s, v = colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)
        s = min(1.0, s * sat_boost)
        v = min(1.0, v * val_boost)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (r * 255, g * 255, b * 255)

    def _set_stops(self, cols):
        a, b, c = (self._vivid(x) for x in cols)
        self.stops = [
            (0.00, tuple(a)),
            (0.50, tuple(b)),
            (1.00, tuple(c)),
        ]
        self._cache = None

    def _grad(self, t):
        t = max(0.0, min(1.0, t))
        for i in range(len(self.stops) - 1):
            p0, c0 = self.stops[i]
            p1, c1 = self.stops[i + 1]
            if t <= p1:
                k = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                return self._mix(c0, c1, k)
        return self.stops[-1][1]

    # ---------- API ----------

    def set_palette(self, palette):

        filtered = []

        for r, g, b in palette:

            # quitar blancos y grises
            if abs(r - g) < 22 and abs(g - b) < 22:
                continue

            l = self._luma((r, g, b))
            if l > 215 or l < 25:
                continue

            filtered.append((r, g, b))

        if len(filtered) < 3:
            filtered = list(palette)

        cols = sorted(filtered[:3], key=self._luma)  # oscuro -> claro
        if len(cols) < 3:
            cols = (cols * 3)[:3]

        # el más claro va al centro, como en la referencia
        self._set_stops([cols[0], cols[2], cols[1]])

        self.queue_draw()

    # ---------- draw ----------

    def _draw(self, widget, cr):

        w = self.get_allocated_width()
        h = self.get_allocated_height()
        if w <= 0 or h <= 0:
            return False

        key = (w, h, tuple(self.stops))
        if self._cache is None or self._cache_key != key:
            self._cache = self._render(w, h)
            self._cache_key = key

        cr.set_source_surface(self._cache, 0, 0)
        cr.paint()
        return False

    def _render(self, w, h):

        surf = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
        cr = cairo.Context(surf)

        # 1. gradiente suave de fondo
        grad = cairo.LinearGradient(0, 0, w, 0)
        for pos, (r, g, b) in self.stops:
            grad.add_color_stop_rgb(pos, r / 255, g / 255, b / 255)
        cr.set_source(grad)
        cr.paint()

        # 2. cuadritos: cada uno toma el color del gradiente
        #    un poco adelante o atrás de su posición
        # 2. cuadritos: versión más clara / más oscura del color local
        cell, sq = self.CELL, self.SQUARE
        off = (cell - sq) / 2
        cols = w // cell
        rows = h // cell + 1
        white, black = (255, 255, 255), (0, 0, 0)

        for ix in range(self.EDGE_CELLS, cols - self.EDGE_CELLS + 1):
            x = ix * cell
            t = (x + cell / 2) / w
            base = self._grad(t)
            ca = self._mix(base, white, 0.14)  # un poco más claro
            cb = self._mix(base, black, 0.14)  # un poco más oscuro
            for iy in range(rows):
                r, g, b = ca if (ix + iy) % 2 == 0 else cb
                cr.set_source_rgb(r / 255, g / 255, b / 255)
                cr.rectangle(x + off, iy * cell + off, sq, sq)
                cr.fill()

        return surf


# ─────────────────────────────────────────────
# 3. TEMPERATURA WIDGET
# ─────────────────────────────────────────────
class TemperatureWidget(Gtk.Box):
    """
    Small weather card that shows current temperature.
    Uses Open-Meteo (free, no API key needed).
    Latitude/Longitude default to Ciudad López Mateos, Mexico.
    """
    LAT = 19.5556
    LON = -99.2472
    CITY = "López Mateos"

    # WMO weather code → emoji
    WMO_ICONS = {
        0: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/sun.png",
        1: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/partly_cloudy.png",
        2: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/cloudy.png",
        3: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/cloud.png",

        45: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/fog.png",
        48: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/fog.png",

        51: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/rain.png",
        53: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/rain.png",
        55: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/rain.png",

        61: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/rain.png",
        63: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/rain.png",
        65: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/rain.png",

        71: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/snow.png",
        73: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/snow.png",
        75: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/snow.png",

        80: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/rain.png",
        81: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/rain.png",
        82: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/storm.png",

        95: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/storm.png",
        96: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/storm.png",
        99: "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/weather/storm.png",
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
        self._fetch_async()
        GLib.timeout_add_seconds(600, self._fetch_async)

    def set_cabin(self, temp, pressure=None):
        self.lbl_cabin.set_text(f"Cabina {temp:.1f}°C")
        self.lbl_cabin.show()

    def _fetch_async(self):
        t = threading.Thread(target=self._fetch, daemon=True)
        t.start()
        return True  # keep GLib timer alive

    def _fetch(self):
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={self.LAT}&longitude={self.LON}"
                f"&current_weather=true"
                f"&temperature_unit=celsius"
            )
            resp = requests.get(url, timeout=8)
            data = resp.json()
            cw = data["current_weather"]
            temp = round(cw["temperature"])
            code = int(cw["weathercode"])
            icon = self.WMO_ICONS.get(code, "🌡")
            GLib.idle_add(self._update_ui, temp, icon, code)
        except Exception as e:
            print("Weather fetch error:", e)
            GLib.idle_add(self._update_ui, None, "🌡", None)

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


# ─────────────────────────────────────────────
# 4. NAVIGATION SYSTEM + MAP SCREEN
# ─────────────────────────────────────────────
class NavigationSystem:
    """
    Handles geocoding (Nominatim) and turn-by-turn routing (OSRM).
    All network calls run in daemon threads; results are sent back to
    the GTK main loop via GLib.idle_add so the UI never freezes.
    """

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
    USER_AGENT = "STM32-Carplay-Dev"

    def geocode_async(self, query, callback):
        """Resolve a place name to (lat, lon).  callback(lat, lon) on success,
        callback(None, None) on failure — always called on the GTK thread."""
        threading.Thread(
            target=self._geocode_task,
            args=(query, callback),
            daemon=True,
        ).start()

    def _geocode_task(self, query, callback):
        try:
            params = urllib.parse.urlencode({
                "q": query,
                "format": "json",
                "limit": 1,
            })
            url = f"{self.NOMINATIM_URL}?{params}"
            req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                GLib.idle_add(callback, lat, lon)
            else:
                print(f"Geocode: no results for '{query}'")
                GLib.idle_add(callback, None, None)
        except Exception as e:
            print(f"Geocode error: {e}")
            GLib.idle_add(callback, None, None)

    def request_osrm_route(self, map_widget, start_lat, start_lon, end_lat, end_lon):
        """Spawn a background thread to fetch the route without freezing the UI."""
        threading.Thread(
            target=self._fetch_route_task,
            args=(map_widget, start_lat, start_lon, end_lat, end_lon),
            daemon=True,
        ).start()

    def _fetch_route_task(self, map_widget, start_lat, start_lon, end_lat, end_lon):
        # ⚠️ CRITICAL PITFALL: OSRM expects Longitude FIRST in the URL!
        url = (
            f"{self.OSRM_URL}/"
            f"{start_lon},{start_lat};{end_lon},{end_lat}"
            f"?overview=full&geometries=geojson"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            if data["code"] == "Ok":
                coordinates = data["routes"][0]["geometry"]["coordinates"]
                GLib.idle_add(self._draw_route_on_map, map_widget, coordinates)
            else:
                print("OSRM routing failed:", data.get("code"))
        except Exception as e:
            print(f"Error connecting to OSRM: {e}")

    def _draw_route_on_map(self, map_widget, coordinates):
        """Executes on the main GTK thread to render the polyline."""
        track = OsmGpsMap.Track()
        for pt in coordinates:
            pt_lon, pt_lat = pt[0], pt[1]
            # ⚠️ CRITICAL PITFALL: OsmGpsMap expects Latitude FIRST!
            map_point = OsmGpsMap.Point.new_degrees(pt_lat, pt_lon)
            track.add_point(map_point)
        map_widget.track_add(track)
        return False  # stop GLib from re-calling


class MapScreen(Gtk.Overlay):
    HOME_LAT = 19.59326
    HOME_LON = -99.22916
    HOME_ZOOM = 14

    def __init__(self, nav_callback):

        super().__init__()

        self._nav_system = NavigationSystem()
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
                "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/map.png",
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
                "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/home.png",
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

        self._set_status(
            "🔍 Buscando..."
        )

        self._nav_system.geocode_async(
            query,
            self._on_geocode_result
        )

    def _on_geocode_result(self, lat, lon):

        if lat is None:
            self._set_status(
                "Destino no encontrado"
            )

            return

        self._set_status(
            "Calculando ruta..."
        )

        self._nav_system.request_osrm_route(
            self.map_widget,
            self._origin_lat,
            self._origin_lon,
            lat,
            lon
        )

        self.map_widget.set_center_and_zoom(
            lat,
            lon,
            13
        )

        self._set_status(
            "",
            False
        )

    def _on_clear_clicked(self, widget):

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


# ─────────────────────────────────────────────
# 5. MÚSICA — HomeSpotifyCard
# ─────────────────────────────────────────────
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
            "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/rewind.png",
            45,
            45,
            True
        )

        btn_prev.set_image(
            Gtk.Image.new_from_pixbuf(pix)
        )

        btn_play = Gtk.Button()
        play_pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/play.png",
            45,
            45,
            True
        )
        btn_play.set_image(
            Gtk.Image.new_from_pixbuf(play_pix)
        )
        btn_next = Gtk.Button()
        next_pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/next.png",
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


# ─────────────────────────────────────────────
# 6. MÚSICA — MusicScreen
# ─────────────────────────────────────────────
class MusicScreen(Gtk.Overlay):
    def __init__(self, nav_callback, home_card):
        self.home_card = home_card
        super().__init__()

        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id="6186b61db32f4eb59ae55a299ef475ad",
                client_secret="7dea9bd274b0436fafea5b676838c71c",
                redirect_uri="http://127.0.0.1:8888/callback",
                scope="user-read-playback-state user-modify-playback-state",
                cache_path="/home/root/spotify.cache",
                open_browser=False,
            )
        )
        self.current_cover = None

        self.music_bg = MusicGradientBG()
        self.add(self.music_bg)

        fixed = Gtk.Fixed()
        self.add_overlay(fixed)

        # Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.get_style_context().add_class("sidebar-music")
        volume_widget = VolumeWidget()
        fixed.put(volume_widget, 1050, 20)

        btn_back = Gtk.Button()
        pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/home.png", 50, 50, True)
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
            (self.btn_prev, "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/rewind.png"),
            (self.btn_play, "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/play.png"),
            (self.btn_next, "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/next.png"),
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
        GLib.timeout_add(2000, self.update_spotify)

    def pixelate_album(self, input_path, output_path):
        img = Image.open(input_path)

        small = img.resize(
            (32, 32),
            Image.NEAREST
        )

        pixel = small.resize(
            img.size,
            Image.NEAREST
        )

        pixel.save(output_path)

    def update_album_art(self, url):
        try:
            response = requests.get(url, timeout=10)
            with open("current_album.jpg", "wb") as f:
                f.write(response.content)

            self.pixelate_album(
                "current_album.jpg",
                "current_album_pixel.jpg"
            )
            try:
                color_thief = ColorThief("current_album.jpg")
                palette = color_thief.get_palette(color_count=6)
                self.music_bg.set_palette([palette[0], palette[1], palette[2], palette[3]])
            except Exception as e:
                print("ColorThief error:", e)
            pixbuf = GdkPixbuf.Pixbuf.new_from_file("current_album_pixel.jpg")
            pixbuf = pixbuf.scale_simple(410, 410, GdkPixbuf.InterpType.NEAREST)
            self.album_image.set_from_pixbuf(pixbuf)

            home_pixbuf = pixbuf.scale_simple(
                300,
                300,
                GdkPixbuf.InterpType.NEAREST
            )
            self.home_card.update_cover(home_pixbuf)

        except Exception as e:
            print("Album art error:", e)

    def update_spotify(self):
        try:
            playback = self.sp.current_playback()
            if not playback:
                return True
            track = playback["item"]
            if not track:
                return True
            fraction = playback["progress_ms"] / track["duration_ms"]
            song = track["name"]
            artist = track["artists"][0]["name"]
            cover = track["album"]["images"][0]["url"]
            self.lbl_song.set_text(song)
            self.lbl_art.set_text(artist)
            self.home_card.update_card(song, artist)
            self.home_card.update_progress(fraction)
            if cover != self.current_cover:
                self.current_cover = cover
                self.update_album_art(cover)
        except Exception as e:
            print("Spotify error:", e)
        return True

    def next_track(self, widget):
        try:
            self.sp.next_track()
        except Exception as e:
            print(e)

    def previous_track(self, widget):
        try:
            self.sp.previous_track()
        except Exception as e:
            print(e)

    def toggle_play(self, widget):
        def task():
            try:
                playback = self.sp.current_playback()
                if playback and playback.get("is_playing"):
                    self.sp.pause_playback()
                else:
                    dev = None
                    for d in self.sp.devices().get("devices", []):
                        if d["name"] == "Copiloba":
                            dev = d["id"]
                            break
                    self.sp.start_playback(device_id=dev)
            except Exception as e:
                print("Toggle error:", e)

        threading.Thread(target=task, daemon=True).start()


# ─────────────────────────────────────────────
# 7. CAMERA SCREEN
# ─────────────────────────────────────────────
class CameraScreen(Gtk.Overlay):
    def __init__(self, nav_callback):
        super().__init__()
        self.pipeline = Gst.parse_launch(
            "v4l2src device=/dev/video7 ! "
            "image/jpeg,width=640,height=360 ! "
            "jpegdec ! videoconvert ! gtksink name=sink"
        )
        sink = self.pipeline.get_by_name("sink")
        video_widget = sink.get_property("widget")
        self.add(video_widget)

        btn_home = Gtk.Button()
        pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/home.png",
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


# ─────────────────────────────────────────────
# 8. RELOJ
# ─────────────────────────────────────────────
class ClockWidget(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=30)
        self.lbl_date = Gtk.Label()
        self.lbl_clock = Gtk.Label()
        self.lbl_date.set_xalign(0.5)
        self.lbl_clock.set_xalign(0.5)
        self.lbl_date.get_style_context().add_class("date-label")
        self.lbl_clock.get_style_context().add_class("clock-label")
        self.pack_start(self.lbl_date, False, False, 0)
        self.pack_start(self.lbl_clock, False, False, 0)
        self.update_clock()
        GLib.timeout_add(1000, self.update_clock)

    def update_clock(self):
        now = datetime.now()
        self.lbl_clock.set_text(now.strftime("%H:%M"))
        self.lbl_date.set_text(now.strftime("%a %d %b"))
        return True


# ─────────────────────────────────────────────
# 9. VENTANA PRINCIPAL
# ─────────────────────────────────────────────
class CarPlayWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="CarPlay OS")
        try:
            subprocess.run([
                "pactl",
                "set-default-sink",
                "bluez_output.54_71_DD_B5_AB_B2.1"
            ])
        except Exception as e:
            print("Bluetooth sink error:", e)

        try:

            already = subprocess.run(["pgrep", "-x", "librespot"],
                                     capture_output=True).returncode == 0
            if not already:
                self.librespot = subprocess.Popen([
                    "/home/root/librespot",
                    "--name", "Copiloba",
                    "--cache", "/home/root/.cache/librespot",
                ])
        except Exception as e:
            print("Librespot error:", e)

        self.fullscreen()

        self.fullscreen()

        # --- NEW GLOBAL OVERLAY ---
        self.global_overlay = Gtk.Overlay()
        self.add(self.global_overlay)

        # 1. Initialize the AI Assistant
        self.ai_assistant = CopilobaAssistant(
            status_callback=self.update_ai_status,
            command_callback=self.execute_command,
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
        self.music_screen = MusicScreen(self.navigate, self.home_card)
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
            "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/music.png",
            70,
            70,
            True
        )
        btn_music.set_image(
            Gtk.Image.new_from_pixbuf(pixmusic)
        )

        btn_cam = Gtk.Button()
        pixcam = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/camera.png",
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
            "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/map.png",
            70,
            70,
            True
        )
        btn_map.set_image(
            Gtk.Image.new_from_pixbuf(pixmap)
        )

        btn_mic = Gtk.Button()
        pixmic = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/copiloba.png",
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

        if hasattr(self, "librespot"):
            self.librespot.terminate()

        if hasattr(self, "sensors"):
            self.sensors.stop()

        Gtk.main_quit()

    def on_ai_button_clicked(self, widget):
        print("🎙️ AI Button Clicked!")

        # Make sure the UI bubble updates to let the user know it's listening
        self.update_ai_status("Escuchando...")

        # Trigger your CopilobaAssistant
        # (Replace '.start()' or '.listen()' with the actual method name you
        # wrote inside your services/copiloba_ai.py file)
        if hasattr(self, 'ai_assistant'):
            # It's best to run this in a thread so Groq/Piper doesn't freeze the GTK UI
            self.ai_assistant.trigger_assistant()
        else:
            print("NO ATTRIBUTE ai_assistant")

    def update_ai_status(self, message):
        """Safely updates the floating AI label from the background thread."""
        if message:
            self.ai_status_label.set_text(message)
            self.ai_status_label.show()
        else:
            self.ai_status_label.hide()
        return False  # Required for GTK3 to prevent infinite loops

    def execute_command(self, cmd):
        """Llamado desde el hilo del asistente con el dict del servidor."""
        action = cmd.get("action", "none")
        args = cmd.get("args") or {}
        if action != "none":
            GLib.idle_add(self._run_command, action, args)

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
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", value])

    def _play_song(self, query):
        if not query:
            return

        def task():
            try:
                sp = self.music_screen.sp
                res = sp.search(q=query, type="track", limit=1)
                items = res["tracks"]["items"]
                if items:
                    sp.start_playback(uris=[items[0]["uri"]])
            except Exception as e:
                print("Play song error:", e)

        threading.Thread(target=task, daemon=True).start()


class VolumeWidget(Gtk.Box):

    def __init__(self):
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
            "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/lessvolume.png",
            40,
            40,
            True
        )

        pix_up = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            "/home/root/copilobarepo/SoC-Carplay/carplay_project/media/morevolume.png",
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
        subprocess.run([
            "wpctl",
            "set-volume",
            "@DEFAULT_AUDIO_SINK@",
            "5%+"
        ])

    def volume_down(self, widget):
        subprocess.run([
            "wpctl",
            "set-volume",
            "@DEFAULT_AUDIO_SINK@",
            "5%-"
        ])

class RPMsgSensorService:
    """Lee los sensores del Cortex-M33 vía OpenAMP (/dev/ttyRPMSG0)
    sin bloquear GTK, y reparte las lecturas a quien se suscriba."""

    DEVICE = "/dev/ttyRPMSG0"
    FLOAT_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")

    def __init__(self):
        self._subs = {"gps": [], "env": [], "tof": [], "status": []}
        self._buffer = ""
        self._fd = -1

    def subscribe(self, kind, callback):
        self._subs[kind].append(callback)

    def start(self):
        if not self._open():
            GLib.timeout_add_seconds(5, self._retry)

    def _retry(self):
        return not self._open()   # True = reintenta en 5s, False = conectado

    def _open(self):
        try:
            self._fd = os.open(self.DEVICE, os.O_RDWR | os.O_NONBLOCK)
            os.write(self._fd, b"wake up!\n")   # registra nuestro endpoint en el M33
            GLib.io_add_watch(self._fd, GLib.IO_IN, self._on_data)
            self._emit("status", True)
            print("✅ RPMsg conectado al M33")
            return True
        except Exception as e:
            print("RPMsg no disponible aún:", e)
            self._fd = -1
            self._emit("status", False)
            return False

    def _on_data(self, fd, condition):
        try:
            data = os.read(fd, 512)
        except BlockingIOError:
            return True
        except OSError as e:
            print("❌ RPMsg perdido:", e)
            self._fd = -1
            self._emit("status", False)
            GLib.timeout_add_seconds(5, self._retry)
            return False   # quita este watch; _retry crea uno nuevo

        if data:
            self._buffer += data.decode("utf-8", errors="replace")
            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                self._parse(line.strip())
        return True

    def _parse(self, line):
        if ":" not in line:
            return
        tag, payload = line.split(":", 1)   # ¡el tag tiene dígitos, sepáralo!
        nums = [float(x) for x in self.FLOAT_RE.findall(payload)]

        if "NEO6MV2" in tag and len(nums) >= 2:
            lat, lon = nums[0], nums[1]
            if -90 <= lat <= 90 and -180 <= lon <= 180 and (lat or lon):
                self._emit("gps", lat, lon)
            # "Searching for satellites..." no trae números: se ignora solo

        elif "VL53L0X" in tag and nums:
            self._emit("tof", nums[0])                       # mm

        elif "BME280" in tag and nums:
            self._emit("env", nums[0],
                        nums[1] if len(nums) > 1 else None)  # T, P

    def _emit(self, kind, *args):
        # io_add_watch corre en el main loop de GTK: es seguro tocar la UI
        for cb in self._subs.get(kind, []):
            cb(*args)

    def stop(self):
        if self._fd >= 0:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = -1


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    Gst.init(None)
    load_all_css()
    win = CarPlayWindow()
    win.connect("destroy", win.on_destroy)  # antes: Gtk.main_quit
    win.show_all()
    Gtk.main()