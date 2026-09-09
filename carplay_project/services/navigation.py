"""Bounded background route searches that discard cancelled or stale results."""

import requests

from carplay_project.services.worker import SerialWorker


class NavigationSystem:
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
    USER_AGENT = "STM32-Carplay-Dev"

    def __init__(self, dispatch):
        self.worker = SerialWorker(dispatch, capacity=1)
        self._generation = 0

    def find_route(self, query, start_lat, start_lon, callback, error_callback):
        self._generation += 1
        generation = self._generation

        def deliver(handler, value):
            if generation == self._generation:
                handler(value)

        accepted = self.worker.submit(
            lambda: self._fetch(query, start_lat, start_lon),
            lambda result: deliver(callback, result),
            lambda error: deliver(error_callback, error),
        )
        if not accepted:
            self._generation -= 1
        return accepted

    def _fetch(self, query, start_lat, start_lon):
        headers = {"User-Agent": self.USER_AGENT}
        with requests.get(self.NOMINATIM_URL, params={"q": query, "format": "json", "limit": 1},
                          headers=headers, timeout=(5, 10)) as response:
            response.raise_for_status()
            matches = response.json()
        if not matches:
            raise ValueError("Destino no encontrado")
        lat, lon = float(matches[0]["lat"]), float(matches[0]["lon"])
        url = f"{self.OSRM_URL}/{start_lon},{start_lat};{lon},{lat}"
        with requests.get(url, params={"overview": "full", "geometries": "geojson"},
                          headers=headers, timeout=(5, 15)) as response:
            response.raise_for_status()
            route = response.json()
        if route.get("code") != "Ok" or not route.get("routes"):
            raise ValueError("No se encontró una ruta")
        return lat, lon, route["routes"][0]["geometry"]["coordinates"]

    def cancel(self):
        self._generation += 1

    def close(self):
        self.cancel()
        self.worker.close()
