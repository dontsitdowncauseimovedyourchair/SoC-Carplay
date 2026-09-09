"""Ollama command generation with deterministic fallback on invalid output."""

import json
import logging
import re

import requests

from carplay_project import config
from carplay_project.commands import validate_command

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """Eres Copiloba, la asistente de voz de un auto. Eres mujer y muy entusiasta.
Respondes SIEMPRE con un único objeto JSON, sin texto extra, con esta forma exacta:
{"action": "...", "args": {}, "say": "..."}

Acciones disponibles (usa "none" si es solo conversación):
- "volume_up" / "volume_down": subir o bajar el volumen
- "volume_set": fijar el volumen, args {"percent": 0-100}
- "music_next" / "music_prev": siguiente o anterior canción
- "music_toggle": pausar o reanudar la música
- "music_play": reproducir algo específico, args {"query": "canción o artista"}
- "open_music" / "open_camera" / "open_map" / "open_home": abrir esa pantalla
- "navigate_to": trazar una ruta, args {"destination": "el lugar como lo escribirías en un mapa"}

Reglas para "say":
- ¡Muy breve, se convertirá en audio! Usa signos de exclamación.
- Llama al conductor "Loba" al menos una vez, pero varía cómo empiezas.
- Si ejecutas una acción, confírmala en "say".

Ejemplos:
Conductor: "bájale tantito" -> {"action":"volume_down","args":{},"say":"¡Claro Loba, le bajo un poquito!"}
Conductor: "pon la que sigue" -> {"action":"music_next","args":{},"say":"¡Va la siguiente, Loba!"}
Conductor: "pon algo de Bad Bunny" -> {"action":"music_play","args":{"query":"Bad Bunny"},"say":"¡Sonando Bad Bunny, Loba!"}
Conductor: "llévame al Ángel de la Independencia" -> {"action":"navigate_to","args":{"destination":"Ángel de la Independencia, Ciudad de México"},"say":"¡Trazando la ruta, Loba!"}
Conductor: "abre la cámara" -> {"action":"open_camera","args":{},"say":"¡Cámara lista, Loba!"}
Conductor: "¿cómo estás?" -> {"action":"none","args":{},"say":"¡Súper bien Loba, lista para el camino!"}
"""


def keyword_fallback(text):
    """Plan B por si el modelo no devuelve JSON válido."""
    t = text.lower()
    if re.search(r"b[aá]ja|menos volumen|m[aá]s bajito", t):
        return {"action": "volume_down", "args": {}}
    if re.search(r"s[uú]be|m[aá]s volumen|m[aá]s fuerte", t):
        return {"action": "volume_up", "args": {}}
    if re.search(r"siguiente|que sigue|c[aá]mbiale", t):
        return {"action": "music_next", "args": {}}
    if re.search(r"anterior|reg[rR][eé]sale", t):
        return {"action": "music_prev", "args": {}}
    if re.search(r"pausa|p[aá]usale|contin[uú]a|reanuda", t):
        return {"action": "music_toggle", "args": {}}
    if re.search(r"c[aá]mara", t):
        return {"action": "open_camera", "args": {}}
    m = re.search(r"(?:ll[eé]vame|ruta|vamos|navega)\s+(?:al|a|hacia)\s+(.+)", t)
    if m:
        return {"action": "navigate_to", "args": {"destination": m.group(1).strip()}}
    return {"action": "none", "args": {}}


def ask_copiloba(prompt):
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": SYSTEM_PROMPT + f'\nConductor: {json.dumps(prompt, ensure_ascii=False)}\nJSON:',
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.4, "num_predict": 256},
    }
    try:
        with requests.post(config.OLLAMA_URL, json=payload,
                           timeout=(5, config.OLLAMA_TIMEOUT)) as response:
            response.raise_for_status()
            data = json.loads(response.json()["response"])
        return validate_command(data, require_speech=True)
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        log.warning("Ollama response rejected; using keyword fallback: %s", type(exc).__name__)
        command = keyword_fallback(prompt)
        command["say"] = ("¡Voy a intentarlo, Loba!" if command["action"] != "none"
                          else "¡Perdón Loba, no te entendí!")
        # Validate the fallback too, including the destination length.
        try:
            return validate_command(command, require_speech=True)
        except ValueError:
            return {"action": "none", "args": {}, "say": "¡Perdón Loba, no te entendí!"}
