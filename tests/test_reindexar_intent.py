"""ReindexarIntent dispara reindexar_todo() en un hilo aparte y avisa por
voz al terminar — mismo patrón que GithubSyncIntent."""

import time
from unittest.mock import MagicMock, patch

from intents.reindexar import ReindexarIntent


def _ctx_falso():
    class CtxFalso:
        lock = MagicMock()
        hablante = MagicMock()
    ctx = CtxFalso()
    ctx.lock.__enter__ = MagicMock(return_value=None)
    ctx.lock.__exit__ = MagicMock(return_value=None)
    return ctx


def test_no_matchea_texto_sin_relacion():
    assert ReindexarIntent().manejar("hola como estas", ctx=_ctx_falso()) is None


def test_responde_de_inmediato_sin_esperar_el_reindexado():
    with patch("intents.reindexar.reindexar_todo", return_value=(5, 2)):
        resultado = ReindexarIntent().manejar("reindexa mis notas", ctx=_ctx_falso())
    assert "segundo plano" in resultado.lower()


def test_avisa_por_voz_con_los_conteos_al_terminar():
    ctx = _ctx_falso()
    with patch("intents.reindexar.reindexar_todo", return_value=(12, 4)):
        ReindexarIntent().manejar("reindexa mis notas", ctx=ctx)
        time.sleep(0.05)

    mensaje = ctx.hablante.hablar.call_args.args[0]
    assert "12" in mensaje
    assert "4" in mensaje


def test_si_falla_avisa_el_error_en_vez_de_tronar():
    ctx = _ctx_falso()
    with patch("intents.reindexar.reindexar_todo", side_effect=Exception("ollama no responde")):
        ReindexarIntent().manejar("actualiza el indice semantico", ctx=ctx)
        time.sleep(0.05)

    mensaje = ctx.hablante.hablar.call_args.args[0]
    assert "no pude reindexar" in mensaje.lower()


def test_variantes_de_frase():
    with patch("intents.reindexar.reindexar_todo", return_value=(0, 0)):
        intent = ReindexarIntent()
        for frase in ["reindexa el indice semantico", "actualiza la busqueda semantica", "reindexa mis notas y mi codigo"]:
            assert intent.manejar(frase, ctx=_ctx_falso()) is not None
