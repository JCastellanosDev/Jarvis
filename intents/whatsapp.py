"""Manda un WhatsApp por voz: busca al contacto, escribe y envía, todo
automático (ver skills/whatsapp.py para la advertencia de riesgo/fragilidad).

Coincide sobre el texto ORIGINAL (no normalizado) para no perder tildes ni
mayúsculas del mensaje real que se va a mandar.

Los patrones son deliberadamente flexibles (varias piezas opcionales): en la
práctica el reconocimiento de voz rara vez transcribe la frase exacta que uno
imagina — "mensaje"/"un" se pierden seguido, o dice "para" en vez de "a".

Depende de la interfaz `Mensajeria` (core/integraciones.py), no directo de
skills.whatsapp — si el mañana WhatsApp Desktop deja de ser automatizable
así y hay que cambiar de mecanismo (o agregar Telegram/iMessage), este
intent no se toca, solo la implementación inyectada."""

import re

from core.integraciones import Mensajeria, WhatsAppDesktop

from .base import Intent

PATRONES_MENSAJE = [
    # "mándale (un) (mensaje/whatsapp) a/para <contacto> diciendo/que <mensaje>"
    re.compile(
        r"^(m[áa]ndale?|env[íi]ale?)\s+(un\s+)?(mensaje\s+|whatsapp\s+)?"
        r"(a|para)\s+(?P<contacto>\w+)\s+(diciendo|que dice|que diga|que)\s+(?P<mensaje>.+)$",
        re.IGNORECASE,
    ),
    # "escríbele a <contacto> que <mensaje>"
    re.compile(r"^escr[íi]bele\s+a\s+(?P<contacto>\w+)\s+que\s+(?P<mensaje>.+)$", re.IGNORECASE),
    # Forma corta con separador: "mándale a X: mensaje" / "mándale a X, mensaje"
    re.compile(r"^(m[áa]ndale?|env[íi]ale?)\s+a\s+(?P<contacto>\w+)[:,]\s*(?P<mensaje>.+)$", re.IGNORECASE),
]


class WhatsAppIntent(Intent):
    def __init__(self, mensajeria: Mensajeria = None):
        self._mensajeria = mensajeria or WhatsAppDesktop()

    def manejar(self, texto, ctx):
        t = texto.strip()
        for patron in PATRONES_MENSAJE:
            m = patron.match(t)
            if m:
                return self._mensajeria.enviar(m.group("contacto"), m.group("mensaje").strip())
        return None
