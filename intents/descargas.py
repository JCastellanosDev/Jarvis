"""Descarga contenido cuando se lo pides por voz:
- "descarga el video de X" -> lo busca en YouTube y lo baja en video.
- "descarga la canción X" / "descarga en mp3 X" -> lo baja solo en audio.
- "descarga esto" / "descarga lo que tengo abierto" -> toma la pestaña
  activa de Brave y la descarga (YouTube o archivo directo).

Todas corren en segundo plano (no bloquean a Jarvis mientras se descarga un
video largo) — Jarvis avisa por voz y por notificación push cuando termina."""

import re

from core.texto import normalizar
from skills.descargas import (
    descargar_lo_abierto_en_navegador_en_segundo_plano, descargar_youtube_en_segundo_plano,
)

from .base import Intent

FRASES_DESCARGAR_ABIERTO = {
    "descarga esto", "descargalo", "descarga eso", "descarga esta pagina",
    "descarga esta pestana", "descarga lo que tengo abierto",
    "descarga lo que esta abierto", "descarga la pagina que tengo abierta",
}

PATRON_AUDIO = re.compile(
    r"^descarga(me)?\s+(en mp3|el audio de|la cancion|la musica de)\s+(?P<consulta>.+)$"
)
PATRON_VIDEO = re.compile(
    r"^descarga(me)?\s+(el video de|la pelicula de)?\s*(?P<consulta>.+)$"
)

MENSAJE_EN_PROGRESO = "Descargando en segundo plano, te aviso cuando termine."


class DescargasIntent(Intent):
    def manejar(self, texto, ctx):
        t = normalizar(texto)

        if t in FRASES_DESCARGAR_ABIERTO:
            print("[Jarvis] Descargando lo que tienes abierto en Brave...")
            descargar_lo_abierto_en_navegador_en_segundo_plano(ctx.hablante)
            return MENSAJE_EN_PROGRESO

        m_audio = PATRON_AUDIO.match(t)
        if m_audio:
            consulta = m_audio.group("consulta").strip()
            if consulta:
                print(f"[Jarvis] Descargando audio de '{consulta}'...")
                descargar_youtube_en_segundo_plano(consulta, True, ctx.hablante)
                return MENSAJE_EN_PROGRESO

        m_video = PATRON_VIDEO.match(t)
        if m_video:
            consulta = m_video.group("consulta").strip()
            if consulta:
                print(f"[Jarvis] Descargando video de '{consulta}'...")
                descargar_youtube_en_segundo_plano(consulta, False, ctx.hablante)
                return MENSAJE_EN_PROGRESO

        return None
