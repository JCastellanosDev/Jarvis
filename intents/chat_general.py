"""Último eslabón de la cadena: conversación general con memoria de corto
plazo, con respaldo agéntico (function calling) para cuando ninguna frase
exacta de intents/ hizo match — el modelo puede decidir llamar una de
skills.herramientas_agente.HERRAMIENTAS (buscar en Obsidian, agregar una
nota, mandar una notificación) en vez de solo conversar. Siempre "maneja"
la petición (nunca devuelve None salvo error de Ollama), así que cierra
el router.

De paso, registra la frase en RegistradorPatrones: si algo cae aquí muy
seguido, es una señal de que merece una skill propia en vez de chat genérico."""

from core.texto import normalizar

from .base import Intent


class ChatGeneralIntent(Intent):
    def manejar(self, texto, ctx):
        if ctx.registrador_patrones:
            ctx.registrador_patrones.registrar(normalizar(texto))
        return ctx.cerebro.responder_con_herramientas(texto, ctx.memoria)
