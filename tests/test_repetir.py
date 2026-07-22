from dataclasses import dataclass

from intents.repetir import RepetirIntent


@dataclass
class _CtxFalso:
    esperando_repetir: bool = False


def test_no_matchea_frase_normal_sin_bandera():
    assert RepetirIntent().manejar("hola como estas", ctx=_CtxFalso()) is None


def test_activa_la_bandera_con_la_frase_disparadora():
    ctx = _CtxFalso()
    resultado = RepetirIntent().manejar("repite lo que digo", ctx)
    assert resultado is not None
    assert ctx.esperando_repetir is True


def test_variantes_de_frase_disparadora():
    for frase in ["Repite lo siguiente que digo", "repite lo que voy a decir", "repite esto"]:
        ctx = _CtxFalso()
        assert RepetirIntent().manejar(frase, ctx) is not None
        assert ctx.esperando_repetir is True


def test_repite_tal_cual_la_siguiente_frase_y_apaga_la_bandera():
    ctx = _CtxFalso(esperando_repetir=True)
    resultado = RepetirIntent().manejar("Hola Mundo, cómo estás?", ctx)
    assert resultado == "Hola Mundo, cómo estás?"
    assert ctx.esperando_repetir is False


def test_repite_incluso_si_coincide_con_otra_frase_de_comando():
    """El punto de "repite lo que digo" es que gane sobre CUALQUIER otro
    intent — incluso si lo que dices después suena a un comando real."""
    ctx = _CtxFalso(esperando_repetir=True)
    assert RepetirIntent().manejar("apaga jarvis", ctx) == "apaga jarvis"
    assert ctx.esperando_repetir is False


def test_solo_repite_una_vez_no_se_queda_pegado():
    ctx = _CtxFalso(esperando_repetir=True)
    RepetirIntent().manejar("esto se repite", ctx)
    assert ctx.esperando_repetir is False
    # La siguiente frase ya NO se repite automáticamente.
    assert RepetirIntent().manejar("esto ya no se repite", ctx) is None
