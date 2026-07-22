import re

from core.texto import normalizar
from .base import Intent

PATRONES_RECORDAR = [
    r"^recuerda que (.+)$",
    r"^acu[eé]rdate de que (.+)$",
    r"^acu[eé]rdate que (.+)$",
    r"^no olvides que (.+)$",
    r"^apunta que (.+)$",
]


class RecordarIntent(Intent):
    def manejar(self, texto, ctx):
        hecho = self._extraer_hecho(texto)
        if hecho is None:
            return None

        ctx.memoria.agregar_hecho(hecho)
        return "Entendido, lo recordaré."

    @staticmethod
    def _extraer_hecho(texto):
        t = normalizar(texto)
        for patron in PATRONES_RECORDAR:
            m = re.match(patron, t)
            if m:
                return m.group(1).strip()
        return None
