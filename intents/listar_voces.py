"""Responde qué voces hay disponibles y le pide al panel que las muestre."""

import time

from core.texto import normalizar

from .base import Intent

FRASES_LISTAR_VOCES = [
    "que voces tienes", "que voces hay", "cuales voces tienes",
    "cuales son las voces disponibles", "dime las voces disponibles",
    "que voces puedo usar", "que voces tienes disponibles",
]


class ListarVocesIntent(Intent):
    def __init__(self, voces_disponibles):
        self._voces_disponibles = voces_disponibles

    def manejar(self, texto, ctx):
        t = normalizar(texto)
        if not any(t == frase or t.startswith(frase) for frase in FRASES_LISTAR_VOCES):
            return None

        ctx.panel_evento = {"tipo": "voces", "id": time.time()}

        nombres = [nombre.capitalize() for nombre in self._voces_disponibles.keys()]
        return "Tengo tres voces disponibles: " + ", ".join(nombres) + ". Te las muestro en el panel."
