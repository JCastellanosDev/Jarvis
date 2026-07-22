"""Si la frase pide información externa/reciente, busca en internet primero
y le pasa los resultados a Ollama como contexto para que formule la
respuesta final (en vez de responder solo con el conocimiento del modelo
local, que es pequeño y no tiene datos recientes)."""

import re

from core.texto import normalizar
from skills.busqueda_web import buscar_en_internet

from .base import Intent

FRASES_BUSQUEDA_EXPLICITA = [
    "busca en internet", "buscar en internet", "buscalo en internet",
    "buscame", "investiga sobre", "investiga en internet",
    "que noticias hay", "noticias sobre",
]

PATRONES_BUSQUEDA_FACTUAL = [
    r"^que es\b", r"^quien es\b", r"^quienes son\b", r"^cuando fue\b",
    r"^cuanto cuesta\b", r"^cuanto vale\b", r"^donde queda\b", r"^donde esta\b",
    r"^que paso con\b", r"^como esta el clima\b", r"^que clima hace\b",
]


class BusquedaWebIntent(Intent):
    def manejar(self, texto, ctx):
        if not self._es_peticion_busqueda(texto):
            return None

        print("[Jarvis] Buscando en internet...")
        contexto_web = buscar_en_internet(texto)
        return ctx.cerebro.responder(texto, ctx.memoria, contexto_web=contexto_web)

    @staticmethod
    def _es_peticion_busqueda(texto):
        t = normalizar(texto)
        if any(frase in t for frase in FRASES_BUSQUEDA_EXPLICITA):
            return True
        return any(re.match(p, t) for p in PATRONES_BUSQUEDA_FACTUAL)
