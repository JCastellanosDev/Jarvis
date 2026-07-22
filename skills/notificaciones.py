"""Notificaciones push a tu celular vía ntfy.sh — gratis, sin cuenta ni API
key: es un servidor público de pub/sub por HTTP.

Setup (una sola vez):
1. Instala la app "ntfy" en tu Android (Play Store).
2. Define NTFY_TOPIC en tu .env con un nombre único e impredecible (el tema
   actúa como "contraseña" del canal — cualquiera que lo sepa puede leer o
   mandar ahí, es un servidor público). Usa sugerir_tema() para generar uno.
3. En la app ntfy, suscríbete a ese mismo tema.
"""

import os
import secrets

import requests
from dotenv import load_dotenv

# No asumas que otro módulo ya cargó el .env antes que este (frágil si
# alguna vez se usa este skill desde un script/test que no pasa primero por
# core.config) — cargarlo aquí también es gratis y a prueba de orden de imports.
load_dotenv()

URL_BASE = "https://ntfy.sh"
TIMEOUT = 10


def _tema():
    return os.getenv("NTFY_TOPIC") or None


def sugerir_tema():
    """Nombre de tema random para configurar en el .env — no uses algo
    adivinable como 'jarvis' en un servidor público."""
    return f"jarvis-{secrets.token_hex(6)}"


def enviar_notificacion(titulo, mensaje, prioridad="default", tags=None):
    """Devuelve (ok: bool, detalle: str)."""
    tema = _tema()
    if not tema:
        return False, (
            "No configuraste NTFY_TOPIC en tu .env. Sugerencia: "
            f"NTFY_TOPIC={sugerir_tema()} — e instala/suscríbete en la app ntfy de tu celular."
        )

    encabezados = {"Title": titulo, "Priority": prioridad}
    if tags:
        encabezados["Tags"] = ",".join(tags)

    try:
        respuesta = requests.post(
            f"{URL_BASE}/{tema}", data=mensaje.encode("utf-8"), headers=encabezados, timeout=TIMEOUT,
        )
        respuesta.raise_for_status()
    except (requests.RequestException, UnicodeEncodeError) as e:
        return False, f"No pude mandar la notificación: {e}"

    return True, "Notificación enviada."
