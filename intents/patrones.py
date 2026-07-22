"""Reporta qué frases repites seguido sin que Jarvis tenga una skill
específica para ellas — para que decidas si vale la pena construir una."""

from core.texto import normalizar

from .base import Intent

FRASES_PATRONES = {
    "que patrones has notado", "que podrias aprender de mi",
    "que comandos te gustaria tener", "que patrones notaste",
    "que has aprendido de mi", "en que deberia mejorarte",
}


class PatronesIntent(Intent):
    def manejar(self, texto, ctx):
        if normalizar(texto) not in FRASES_PATRONES:
            return None

        if not ctx.registrador_patrones:
            return "No tengo un registro de patrones activo."

        frecuentes = ctx.registrador_patrones.mas_frecuentes()
        if not frecuentes:
            return "Todavía no noto ningún patrón repetido en lo que me pides."

        resumen = "; ".join(f'"{texto}" ({veces} veces)' for texto, veces in frecuentes)
        return (
            f"He notado que repites estas frases sin tener una habilidad específica: "
            f"{resumen}. Dile a quien te programa que te agregue algo para eso."
        )
