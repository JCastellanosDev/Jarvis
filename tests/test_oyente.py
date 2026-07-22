"""'cambio' debe cortar de inmediato (sin esperar otra ráfaga); las pausas
normales entre ráfagas deben acumularse en una sola frase final."""

from unittest.mock import patch

from core.oyente import Oyente


def _oyente_con_rafagas(respuestas):
    """respuestas: lista de textos que devuelve cada ráfaga sucesiva (o None
    para simular silencio/fin)."""
    o = Oyente()
    it = iter(respuestas)
    o._escuchar_una_rafaga = lambda es_primera: next(it, None)
    return o


def test_cambio_corta_de_inmediato_sin_pedir_otra_rafaga():
    o = _oyente_con_rafagas(["ábreme youtube music cambio", "esto no debería leerse nunca"])
    resultado = o.escuchar()
    assert resultado == "ábreme youtube music"


def test_acumula_varias_rafagas_sin_cambio_hasta_silencio():
    o = _oyente_con_rafagas(["quiero que", "me ayudes con", "mi tarea de cálculo", None])
    resultado = o.escuchar()
    assert resultado == "quiero que me ayudes con mi tarea de cálculo"


def test_una_sola_rafaga_sin_cambio_ni_continuacion():
    o = _oyente_con_rafagas(["hola jarvis", None])
    assert o.escuchar() == "hola jarvis"


def test_silencio_total_devuelve_none():
    o = _oyente_con_rafagas([None])
    assert o.escuchar() is None


def test_cambio_solo_como_unica_palabra():
    o = _oyente_con_rafagas(["cambio"])
    assert o.escuchar() is None


def test_cambio_no_confunde_palabras_parecidas():
    """'cambiome' o 'intercambio' no deben confundirse con el comando."""
    o = _oyente_con_rafagas(["hice un intercambio", None])
    assert o.escuchar() == "hice un intercambio"


def test_respeta_limite_de_rafagas():
    """Nunca debe entrar en un ciclo infinito si el usuario sigue hablando
    sin decir 'cambio' y sin pausas reales."""
    o = _oyente_con_rafagas(["uno", "dos", "tres", "cuatro", "cinco", "seis", "siete"])
    resultado = o.escuchar()
    # max_rafagas=6 por defecto: se detiene ahí, no sigue para siempre.
    assert resultado == "uno dos tres cuatro cinco seis"
