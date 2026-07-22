"""Descarga contenido cuando se lo pides por voz:
- "descarga el video de X" -> lo busca en YouTube y lo baja en video.
- "descarga la canción X" / "descarga en mp3 X" -> lo baja solo en audio.
- "descarga esto" / "descarga lo que tengo abierto" -> toma la pestaña
  activa de Brave y la descarga (YouTube o archivo directo)."""

import re

from core.texto import normalizar
from skills.descargas import descargar_lo_abierto_en_navegador, descargar_youtube

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


class DescargasIntent(Intent):
    def manejar(self, texto, ctx):
        t = normalizar(texto)

        if t in FRASES_DESCARGAR_ABIERTO:
            print("[Jarvis] Descargando lo que tienes abierto en Brave...")
            return descargar_lo_abierto_en_navegador()

        m_audio = PATRON_AUDIO.match(t)
        if m_audio:
            consulta = m_audio.group("consulta").strip()
            if consulta:
                print(f"[Jarvis] Descargando audio de '{consulta}'...")
                return descargar_youtube(consulta, solo_audio=True)

        m_video = PATRON_VIDEO.match(t)
        if m_video:
            consulta = m_video.group("consulta").strip()
            if consulta:
                print(f"[Jarvis] Descargando video de '{consulta}'...")
                return descargar_youtube(consulta, solo_audio=False)

        return None
