"""Abre servicios de streaming de video (Prime Video / Paramount+) vía Brave.

- "abre prime video" / "abre paramount" -> abre el catálogo general directo.
- "quiero ver películas" (genérico, sin decir cuál) -> pregunta por voz en
  cuál servicio, y abre el que elijas.
- "quiero ver <película>" -> busca en cuál de las dos apps está de verdad
  (vía búsqueda web) y abre esa; si no aparece en ninguna, abre la primera
  página que encuentre donde poder verla.

Nota: el trigger de película específica es "quiero ver" (no "pon"/"reproduce")
a propósito — esas palabras ya las usa MultimediaIntent para música, y como
va antes en la cadena, "pon <algo>" siempre se interpretaría como canción.
"""

import re

from core.texto import normalizar
from skills.video import abrir_paramount, abrir_prime_video, buscar_donde_ver

from .base import Intent

FRASES_PRIME_DIRECTO = {"abre prime video", "abre amazon prime", "abre amazon prime video"}
FRASES_PARAMOUNT_DIRECTO = {"abre paramount", "abre paramount plus", "abre paramount+"}
FRASES_ELEGIR_SERVICIO = {
    "quiero ver peliculas", "quiero ver una pelicula", "quiero ver una serie",
    "quiero ver algo", "vamos a ver una pelicula", "vamos a ver algo",
}

PATRON_PELICULA_ESPECIFICA = re.compile(r"^quiero ver\s+(?P<pelicula>.+)$")
PATRON_RELLENO_INICIAL = re.compile(r"^(la\s+)?pelicula\s+")


class VideoIntent(Intent):
    def manejar(self, texto, ctx):
        t = normalizar(texto)

        if t in FRASES_PRIME_DIRECTO:
            return abrir_prime_video()

        if t in FRASES_PARAMOUNT_DIRECTO:
            return abrir_paramount()

        if t in FRASES_ELEGIR_SERVICIO:
            return self._elegir_servicio(ctx)

        m = PATRON_PELICULA_ESPECIFICA.match(t)
        if m:
            pelicula = PATRON_RELLENO_INICIAL.sub("", m.group("pelicula").strip())
            if pelicula:
                print(f"[Jarvis] Buscando dónde ver '{pelicula}'...")
                return buscar_donde_ver(pelicula)

        return None

    @staticmethod
    def _elegir_servicio(ctx):
        respuesta = ctx.ctx_skills["pedir_texto_por_voz"]("¿En Prime Video o en Paramount?")
        if not respuesta:
            return "No escuché tu respuesta, inténtalo de nuevo."

        t = normalizar(respuesta)
        if "prime" in t:
            return abrir_prime_video()
        if "paramount" in t:
            return abrir_paramount()
        return "No entendí cuál, di Prime o Paramount."
