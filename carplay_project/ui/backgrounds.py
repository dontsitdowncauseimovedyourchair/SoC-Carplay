"""Cached Cairo backgrounds for the dashboard and music screen."""

import colorsys
import random

import cairo
from gi.repository import Gtk


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
