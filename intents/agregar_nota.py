"""Agrega una nota rápida a tu bóveda de Obsidian por voz.

A diferencia de otros intents, el patrón corre sobre el texto ORIGINAL (no el
normalizado) para no perder tildes/mayúsculas del contenido real de la nota —
aquí sí importa cómo quede escrita, no solo detectar la intención.
"""

import re

from skills.obsidian import agregar_nota

from .base import Intent

PATRON_AGREGAR_NOTA = re.compile(
    r"^(anota|apunta|agrega|guarda)\s+(en\s+)?(obsidian|mi\s+b[oó]veda|mis\s+notas)\s+que\s+(?P<nota>.+)$",
    re.IGNORECASE,
)


class AgregarNotaIntent(Intent):
    def manejar(self, texto, ctx):
        m = PATRON_AGREGAR_NOTA.match(texto.strip())
        if not m:
            return None
        return agregar_nota(m.group("nota").strip())
