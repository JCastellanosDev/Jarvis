"""Si la frase pide información de tus notas, busca en tus bóvedas de
Obsidian primero y le pasa los fragmentos a Ollama como contexto (mismo
patrón que BusquedaWebIntent, pero sobre tus .md en vez de internet).

La búsqueda es semántica (embeddings vía core/busqueda_semantica.py) si ya
corriste "reindexa mis notas" al menos una vez; si no, o si Ollama no
responde, cae sola al match por palabra clave de siempre — nunca se queda
sin poder buscar.

Los patrones son deliberadamente flexibles (mismo aprendizaje que con
WhatsApp): frases naturales como "accede a Obsidian para que me digas quién
soy" no coinciden con un patrón rígido tipo "busca en mis notas sobre X" —
sin un patrón que matchee, cae al chat general, que no sabe que Jarvis tiene
esta capacidad y alucina que "no puede acceder"."""

import re

from core.busqueda_semantica import buscar_semantico_en_notas
from core.texto import normalizar

from .base import Intent

# Cada patrón captura solo el TEMA (no la frase completa) para no mandar
# palabras vacías como "que"/"sobre" a la búsqueda.
PATRONES_CONSULTA = [
    re.compile(r"^(accede a|entra a|busca en|revisa|abre)\s+(mis notas|mi obsidian|obsidian)"
               r"\s*(para que me digas?|para decirme|y dime|y dices?|y me digas?|sobre)?\s*(?P<consulta>.+)$"),
    re.compile(r"^que dicen mis notas( sobre)?\s+(?P<consulta>.+)$"),
    re.compile(r"^revisa mis (notas|apuntes)( sobre)?\s+(?P<consulta>.+)$"),
    re.compile(r"^que dice obsidian sobre\s+(?P<consulta>.+)$"),
    re.compile(r"^que (anote|tengo anotado|sabes de mis notas) sobre\s+(?P<consulta>.+)$"),
    re.compile(r"^segun mis notas,?\s+(?P<consulta>.+)$"),
]

# "Quién soy" es tan frecuente y de tan alto valor que no vale la pena
# forzarlo por el patrón genérico — se busca directo con "perfil" como
# término (ajusta si tu nota personal se llama distinto a "Perfil.md").
FRASES_QUIEN_SOY = {"quien soy", "quien soy yo", "sabes quien soy", "quien soy yo segun mis notas"}
CONSULTA_QUIEN_SOY = "perfil"


class ObsidianIntent(Intent):
    def manejar(self, texto, ctx):
        t_norm = normalizar(texto)

        if t_norm in FRASES_QUIEN_SOY:
            consulta = CONSULTA_QUIEN_SOY
        else:
            consulta = self._extraer_consulta(texto)
            if consulta is None:
                return None
            # "accede a obsidian para que me digas quién soy" también cae
            # aquí (el patrón genérico sí matchea) — mismo caso especial.
            if normalizar(consulta) in FRASES_QUIEN_SOY:
                consulta = CONSULTA_QUIEN_SOY

        print("[Jarvis] Buscando en tus notas de Obsidian...")
        contexto = buscar_semantico_en_notas(consulta)
        if contexto is None:
            return f"No encontré nada en tus notas sobre {consulta}."

        return ctx.cerebro.responder(texto, ctx.memoria, contexto_obsidian=contexto)

    @staticmethod
    def _extraer_consulta(texto):
        t = normalizar(texto)
        for patron in PATRONES_CONSULTA:
            m = patron.match(t)
            if m:
                return m.group("consulta").strip()
        return None
