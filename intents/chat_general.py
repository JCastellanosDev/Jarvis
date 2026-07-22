"""Último eslabón de la cadena: conversación general con memoria de corto
plazo. Siempre "maneja" la petición (nunca devuelve None salvo error de
Ollama), así que cierra el router.

De paso, registra la frase en RegistradorPatrones: si algo cae aquí muy
seguido, es una señal de que merece una skill propia en vez de chat genérico."""

from core.texto import normalizar

from .base import Intent


class ChatGeneralIntent(Intent):
    def manejar(self, texto, ctx):
        if ctx.registrador_patrones:
            ctx.registrador_patrones.registrar(normalizar(texto))
        return ctx.cerebro.responder(texto, ctx.memoria)
