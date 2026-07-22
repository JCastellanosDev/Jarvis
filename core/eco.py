"""Filtra transcripciones que en realidad son la propia voz de Jarvis
resonando de vuelta al micrófono — en una MacBook los parlantes y el
micrófono están físicamente muy cerca, así que la respuesta que Jarvis
ACABA de decir a veces se transcribe como si fuera un comando nuevo tuyo
(bug real visto en logs: "Tú: notificación mandada a tu celular" era
literalmente la respuesta anterior de Jarvis, no algo que el usuario dijo).
Como ese eco no matchea ningún intent real, caía al chat general con una
respuesta inventada.
"""

import difflib

from core.texto import normalizar

UMBRAL_SIMILITUD_ECO = 0.82
MIN_CARACTERES_PARA_COMPARAR = 8  # evita falsos positivos con frases cortas


def es_eco_de_si_mismo(texto_oido, ultima_respuesta_hablada):
    """True si `texto_oido` parece ser la propia `ultima_respuesta_hablada`
    de Jarvis (completa o solo la cola, si el mic no alcanzó a captar todo)."""
    if not ultima_respuesta_hablada or not texto_oido:
        return False

    oido = normalizar(texto_oido)
    dicho = normalizar(ultima_respuesta_hablada)
    if len(oido) < MIN_CARACTERES_PARA_COMPARAR or not dicho:
        return False

    if oido in dicho:
        return True

    return difflib.SequenceMatcher(None, oido, dicho).ratio() >= UMBRAL_SIMILITUD_ECO
