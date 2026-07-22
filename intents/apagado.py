import random

from core.texto import normalizar
from .base import DetenerJarvis, Intent

# Coincidencia EXACTA (tras normalizar), no por substring, para que frases como
# "no me apagues" o "hoy me despedí de mi jefe" no disparen el cierre.
COMANDOS_APAGADO = {
    "apágate", "apágate jarvis", "jarvis apágate", "apaga", "apágalo",
    "hasta luego jarvis", "adiós jarvis", "adiós jarvis, hasta luego",
    "apaga el sistema", "apaga sistema", "cierra el sistema", "cierra sistema",
    "cierra jarvis", "cierra", "cerrar", "termina el programa", "sal del programa",
    "sal", "salir",
}

FRASES_DESPEDIDA = [
    "Apagando sistemas. Hasta luego.",
    "Listo, me voy a dormir. Nos vemos.",
    "Cerrando todo por aquí. Que estés bien.",
    "Hasta la próxima.",
    "Jarvis fuera de línea. Cuídate.",
    "Sistemas apagados. Aquí ando cuando me necesites.",
]


class ApagadoIntent(Intent):
    def __init__(self, comandos_apagado=COMANDOS_APAGADO):
        self._comandos_norm = {normalizar(c) for c in comandos_apagado}

    def manejar(self, texto, ctx):
        if normalizar(texto) in self._comandos_norm:
            raise DetenerJarvis(random.choice(FRASES_DESPEDIDA))
        return None
