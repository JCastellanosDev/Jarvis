import re

from core.texto import normalizar
from .base import Intent


class CambioVozIntent(Intent):
    def __init__(self, voces_disponibles):
        self._voces_disponibles = voces_disponibles
        self._patron = re.compile(
            r"\b(cambia|usa|pon|activa)\w*\s+(la\s+)?voz\s+(a|de)\s+(?P<voz>" +
            "|".join(voces_disponibles.keys()) + r")\b"
        )

    def manejar(self, texto, ctx):
        m = self._patron.search(normalizar(texto))
        if not m:
            return None

        nombre_voz = m.group("voz")
        ctx.hablante.voice_id = self._voces_disponibles[nombre_voz]
        return f"Cambiando a la voz de {nombre_voz.capitalize()}. ¿Qué tal suena?"
