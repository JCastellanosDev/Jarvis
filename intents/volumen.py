"""Control del volumen general de la Mac por voz (no de una app en
particular)."""

from core.texto import normalizar
from skills.volumen import bajar_volumen, silenciar, subir_volumen

from .base import Intent

FRASES_SUBIR = {
    "sube el volumen", "sube volumen", "mas volumen", "aumenta el volumen",
    "subele al volumen", "subele", "mas fuerte",
}
FRASES_BAJAR = {
    "baja el volumen", "baja volumen", "menos volumen", "disminuye el volumen",
    "bajale al volumen", "bajale", "mas bajito",
}
FRASES_SILENCIAR = {
    "silencia", "mutea", "silencia el volumen", "pon en silencio",
    "quita el sonido", "sin sonido",
}


class VolumenIntent(Intent):
    def manejar(self, texto, ctx):
        t = normalizar(texto)

        if t in FRASES_SUBIR:
            return subir_volumen()

        if t in FRASES_BAJAR:
            return bajar_volumen()

        if t in FRASES_SILENCIAR:
            return silenciar()

        return None
