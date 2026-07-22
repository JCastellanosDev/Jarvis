"""Fecha y hora exactas leídas del reloj del sistema (datetime.now()),
respondidas al instante sin pasar por el LLM.

No se usa `locale` porque macOS no siempre trae instalado el locale es_ES, lo
que puede romper `strftime` de forma silenciosa o con excepción según la
máquina; en su lugar se usan tablas fijas en español.
"""

from datetime import datetime

from core.texto import normalizar
from .base import Intent

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

FRASES_FECHA = [
    "que dia es hoy", "que dia es", "que fecha es", "a que estamos",
    "en que fecha estamos", "cual es la fecha", "que fecha tenemos",
]

FRASES_HORA = [
    "que hora es", "que horas son", "dime la hora", "me dices la hora",
    "tienes hora", "sabes que hora es", "que hora tenemos",
]


def _periodo_del_dia(hora24):
    if 0 <= hora24 < 6:
        return "de la madrugada"
    if 6 <= hora24 < 12:
        return "de la mañana"
    if 12 <= hora24 < 19:
        return "de la tarde"
    return "de la noche"


class FechaHoraIntent(Intent):
    def manejar(self, texto, ctx):
        t = normalizar(texto)

        if self._coincide(t, FRASES_HORA):
            return self._hora_hablada()

        if self._coincide(t, FRASES_FECHA):
            return self._fecha_hablada()

        return None

    @staticmethod
    def _coincide(texto_normalizado, frases):
        return any(texto_normalizado == f or texto_normalizado.startswith(f) for f in frases)

    @staticmethod
    def _fecha_hablada():
        ahora = datetime.now()
        dia_semana = DIAS_SEMANA[ahora.weekday()]
        mes = MESES[ahora.month - 1]
        return f"Hoy es {dia_semana} {ahora.day} de {mes} de {ahora.year}."

    @staticmethod
    def _hora_hablada():
        ahora = datetime.now()
        hora12 = ahora.hour % 12 or 12
        periodo = _periodo_del_dia(ahora.hour)
        if ahora.minute == 0:
            return f"Son las {hora12} en punto {periodo}."
        return f"Son las {hora12} y {ahora.minute} {periodo}."
