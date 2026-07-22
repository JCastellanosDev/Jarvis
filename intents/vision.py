"""Describe lo que hay en la pantalla usando un modelo de visión local."""

from core.texto import normalizar
from skills.vision import describir_pantalla

from .base import Intent

FRASES_VISION = {
    "explicame lo que estoy viendo", "que estoy viendo", "que hay en mi pantalla",
    "que ves en mi pantalla", "describe mi pantalla", "explicame mi pantalla",
    "que tengo en pantalla", "que es esto que estoy viendo",
}


class VisionIntent(Intent):
    def manejar(self, texto, ctx):
        if normalizar(texto) not in FRASES_VISION:
            return None
        return describir_pantalla()
