"""Instala programas por voz: busca en Homebrew (fuente curada, no
resultados de búsqueda al azar), te confirma por voz qué encontró, y solo
si dices que sí lo instala en segundo plano (no bloquea a Jarvis mientras
Homebrew descarga)."""

import re

from core.texto import normalizar
from skills.instalador import buscar_en_homebrew, instalar_en_segundo_plano

from .base import Intent

PATRON_INSTALAR = re.compile(r"^instala(me)?\s+(?P<programa>.+)$")
PALABRAS_CONFIRMACION = {"si", "confirmo", "dale", "adelante", "hazlo", "correcto"}


class InstaladorIntent(Intent):
    def manejar(self, texto, ctx):
        t = normalizar(texto)
        m = PATRON_INSTALAR.match(t)
        if not m:
            return None

        programa = m.group("programa").strip()
        if not programa:
            return None

        print(f"[Jarvis] Buscando '{programa}' en Homebrew...")
        candidato, tipo = buscar_en_homebrew(programa)
        if not candidato:
            return f"No encontré {programa} en Homebrew. Puede que necesite instalarse manualmente."

        respuesta = ctx.ctx_skills["pedir_texto_por_voz"](
            f"Encontré {candidato} en Homebrew, ¿confirmas que lo instale?"
        )
        if not respuesta or not any(p in normalizar(respuesta).split() for p in PALABRAS_CONFIRMACION):
            return "No confirmaste, no instalé nada."

        instalar_en_segundo_plano(candidato, tipo, ctx.hablante)
        return f"Instalando {candidato} en segundo plano, te aviso cuando termine."
