"""Si pides ayuda programando algo, busca primero en tu propio código (ya
sincronizado de GitHub) y se lo pasa a Ollama como referencia de tu estilo,
mismo patrón que BusquedaWebIntent/ObsidianIntent.

Búsqueda semántica (ver core/busqueda_semantica.py) si ya reindexaste al
menos una vez; si no, cae sola al match por palabra clave de siempre."""

import re

from core.busqueda_semantica import buscar_semantico_en_codigo
from core.texto import normalizar

from .base import Intent

PATRONES_CONSULTA = [
    re.compile(r"^busca en mi codigo( sobre)?\s+(?P<consulta>.+)$"),
    re.compile(r"^revisa mi codigo( sobre)?\s+(?P<consulta>.+)$"),
    re.compile(r"^como programo( yo)?\s+(?P<consulta>.+)$"),
    re.compile(r"^como suelo hacer\s+(?P<consulta>.+)$"),
    re.compile(r"^ayudame a programar\s+(?P<consulta>.+)( como yo lo hago)?$"),
]


class BuscarCodigoIntent(Intent):
    def manejar(self, texto, ctx):
        consulta = self._extraer_consulta(texto)
        if consulta is None:
            return None

        print("[Jarvis] Buscando en tu código de GitHub...")
        contexto = buscar_semantico_en_codigo(consulta)
        if contexto is None:
            # Sin coincidencias en tu código: igual responde, solo que sin
            # ese contexto extra (puede que aún no hayas sincronizado nada).
            return ctx.cerebro.responder(texto, ctx.memoria)

        return ctx.cerebro.responder(texto, ctx.memoria, contexto_codigo=contexto)

    @staticmethod
    def _extraer_consulta(texto):
        t = normalizar(texto)
        for patron in PATRONES_CONSULTA:
            m = patron.match(t)
            if m:
                return m.group("consulta").strip()
        return None
