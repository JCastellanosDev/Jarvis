"""Modo "repite lo que digo": Jarvis repite tal cual la SIGUIENTE frase que
digas, sin importar qué sea (aunque coincida con el patrón de otro intent) —
y solo esa vez, no se queda pegado repitiendo todo lo que sigas diciendo.

Por eso este intent debe ir PRIMERO en la cadena del router: si la bandera
`ctx.esperando_repetir` está prendida, se queda con el turno antes de que
cualquier otro intent (incluido "apaga Jarvis") tenga oportunidad de
interpretar la frase."""

from core.texto import normalizar

from .base import Intent

FRASES_ACTIVAR = {
    "repite lo que digo", "repite lo siguiente que digo",
    "repite lo que voy a decir", "repite lo proximo que diga",
    "repite lo que te voy a decir", "repite esto",
}

MENSAJE_PIDIENDO_FRASE = "Dime, y lo repito tal cual."


class RepetirIntent(Intent):
    def manejar(self, texto, ctx):
        if ctx.esperando_repetir:
            ctx.esperando_repetir = False
            return texto

        if normalizar(texto) in FRASES_ACTIVAR:
            ctx.esperando_repetir = True
            return MENSAJE_PIDIENDO_FRASE

        return None
