"""Reproduce música en YouTube Music (vía Brave):
- Pedido genérico ("pon música", "quiero música") -> tu playlist "Me gusta".
- Pedido de una canción concreta ("pon <canción>") -> la busca y la reproduce.
"""

import re

from core.texto import normalizar
from skills.musica import (
    pausar_musica, reanudar_musica, reproducir_cancion, reproducir_musica_que_me_gusta,
)

from .base import Intent

# Coincidencia EXACTA (no por prefijo): "pon musica" es genérico, pero
# "pon musica de queen" NO debe caer aquí solo por empezar igual, o nunca se
# podría pedir una canción concreta que mencione la palabra "música".
FRASES_MUSICA_GENERICA = {
    "quiero musica", "quiero escuchar musica", "pon musica", "pon algo de musica",
    "reproduce musica", "pon mi musica", "pon mis canciones", "pon mi playlist",
    "pon la musica que me gusta", "pon lo que me gusta", "abre youtube music",
    "abre la musica", "abre musica",
}

FRASES_PAUSAR = {
    "pausa", "pausalo", "pausala", "pausa la musica", "pausa la cancion",
    "pausa esto", "pon en pausa", "pon pausa", "detén la musica", "detente",
}
FRASES_REANUDAR = {
    "reanuda", "reanudalo", "reanudala", "reanuda la musica", "reanuda la cancion",
    "continua la musica", "sigue reproduciendo", "quita la pausa", "play", "dale play",
}

# Muletillas al final de la frase que no aportan nada a la búsqueda ni a la
# clasificación genérico/específico (ej. "pon música por favor").
MULETILLAS_FINALES = ("por favor", "porfa", "porfavor")

PATRON_CANCION_ESPECIFICA = re.compile(
    r"^(pon|ponme|reproduce|quiero escuchar)\s+(?P<cancion>.+)$"
)

# Relleno inicial en la consulta capturada que le resta precisión a la
# búsqueda ("pon *música* bohemian rhapsody" -> solo interesa lo de después).
PATRON_RELLENO_INICIAL = re.compile(r"^(la\s+)?(cancion|musica)(\s+de)?\s+")


class MultimediaIntent(Intent):
    def manejar(self, texto, ctx):
        t = self._quitar_muletillas(normalizar(texto))

        if t in FRASES_PAUSAR:
            return pausar_musica()

        if t in FRASES_REANUDAR:
            return reanudar_musica()

        if t in FRASES_MUSICA_GENERICA:
            return reproducir_musica_que_me_gusta()

        m = PATRON_CANCION_ESPECIFICA.match(t)
        if m:
            cancion = PATRON_RELLENO_INICIAL.sub("", m.group("cancion").strip())
            if cancion:
                return reproducir_cancion(cancion)

        return None

    @staticmethod
    def _quitar_muletillas(texto_normalizado):
        for muletilla in MULETILLAS_FINALES:
            if texto_normalizado.endswith(" " + muletilla):
                return texto_normalizado[: -(len(muletilla) + 1)].strip()
        return texto_normalizado
