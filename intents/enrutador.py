"""Router de intents: cadena de responsabilidad ordenada.

Prueba cada intent en orden; el primero que devuelva algo distinto de None
"gana". ChatGeneralIntent va al final y siempre responde, así que la cadena
siempre termina con una respuesta (o None si el LLM falló)."""

from core.texto import quitar_direccion_jarvis


class EnrutadorIntents:
    def __init__(self, intents):
        self._intents = list(intents)

    def procesar(self, texto, ctx):
        # Se quita UNA sola vez aquí (no en cada intent) para que ningún
        # patrón exacto falle solo porque dijiste "Jarvis, ..." antes del
        # comando real.
        texto = quitar_direccion_jarvis(texto)
        for intent in self._intents:
            respuesta = intent.manejar(texto, ctx)
            if respuesta is not None:
                return respuesta
        return None
