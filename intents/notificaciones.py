"""Manda una notificación push a tu celular por voz — útil también para
probar que ntfy.sh está bien configurado antes de depender de los avisos
automáticos (descargas/instalaciones en segundo plano)."""

import re

from core.texto import normalizar
from skills.notificaciones import enviar_notificacion

from .base import Intent

PATRONES_NOTIFICAR = [
    re.compile(
        r"^(mandame|enviame|avisame)\s+(una\s+)?(notificacion|aviso)\s+"
        r"(al celular\s+)?(que diga|diciendo|con)?\s*(?P<mensaje>.+)$"
    ),
    re.compile(
        r"^(mandame|enviame|avisame)\s+al celular\s+(que diga|diciendo|con)?\s*(?P<mensaje>.+)$"
    ),
]


class NotificacionesIntent(Intent):
    def manejar(self, texto, ctx):
        t = normalizar(texto)
        m = None
        for patron in PATRONES_NOTIFICAR:
            m = patron.match(t)
            if m:
                break
        if not m:
            return None

        mensaje = m.group("mensaje").strip()
        if not mensaje:
            return None

        ok, detalle = enviar_notificacion("Jarvis", mensaje)
        if not ok:
            return detalle
        return "Notificación mandada a tu celular."
