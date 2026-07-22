"""Regresión de un bug real visto en logs: "Tú: notificación mandada a tu
celular" era literalmente la respuesta anterior de Jarvis resonando de
vuelta al micrófono (parlantes y mic muy cerca en una MacBook), no algo que
el usuario dijo. Como no matchea ningún intent real, caía al chat general
con una respuesta inventada ("no tengo acceso a mis dispositivos...")."""

from core.eco import es_eco_de_si_mismo


def test_repeticion_exacta_es_eco():
    assert es_eco_de_si_mismo(
        "notificación mandada a tu celular", "Notificación mandada a tu celular."
    ) is True


def test_cola_parcial_tambien_es_eco():
    """El mic no siempre alcanza a captar la frase completa, solo la cola."""
    assert es_eco_de_si_mismo(
        "a tu celular", "Notificación mandada a tu celular."
    ) is True


def test_comando_real_no_se_confunde_con_eco():
    assert es_eco_de_si_mismo(
        "mándale un mensaje a mamá diciendo ya voy para allá", "Notificación mandada a tu celular."
    ) is False


def test_frase_corta_real_no_se_marca_como_eco():
    """Frases cortas reales ('sí', 'no', 'apágate') no deben descartarse solo
    por coincidir parcialmente con alguna palabra de la última respuesta."""
    assert es_eco_de_si_mismo("si", "Sistemas en línea, ¿qué hacemos hoy?") is False


def test_sin_respuesta_previa_nunca_es_eco():
    assert es_eco_de_si_mismo("cualquier cosa que diga larga y completa", None) is False


def test_texto_oido_vacio_no_es_eco():
    assert es_eco_de_si_mismo("", "algo que dijo Jarvis") is False
