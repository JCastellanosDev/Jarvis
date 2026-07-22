"""Normalización de texto compartida por todos los intents y el core."""

import re
import unicodedata


def normalizar(texto):
    """minúsculas + sin tildes + sin puntuación, para comparar frases de forma robusta."""
    texto = texto.strip().lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    texto = re.sub(r"[^\w\s]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


# Muchos intents matchean con un prefijo exacto ("quiero ver...", "pon...").
# Si dices "Jarvis, quiero ver..." (dirigiéndote a él por costumbre, o
# porque aún no tienes wake word configurado), ese "Jarvis" inicial queda
# como parte del texto capturado y ningún patrón exacto lo reconoce — cae
# al chat general en vez de ejecutar el comando real.
PATRON_DIRECCION_JARVIS = re.compile(r"^\s*(oye|hey|ey)?[,\s]*jarvis\b[,\s]*", re.IGNORECASE)


def quitar_direccion_jarvis(texto):
    """Quita un 'Jarvis' (u 'oye/hey Jarvis') inicial de dirección, dejando
    el resto del texto ORIGINAL intacto (tildes/mayúsculas), para que los
    intents que comparan contra el texto sin normalizar (ej. WhatsApp) sigan
    recibiendo el mensaje tal cual lo dijiste."""
    return PATRON_DIRECCION_JARVIS.sub("", texto, count=1)
