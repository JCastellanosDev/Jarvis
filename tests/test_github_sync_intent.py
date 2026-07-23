"""GithubSyncIntent dispara sincronizar() en un hilo aparte y avisa por voz
al terminar — se mockea la interfaz ControlVersiones inyectada, nunca la
skill real (sin red, sin git de por medio)."""

import time
from unittest.mock import MagicMock

from intents.github_sync import GithubSyncIntent


def _ctx_falso():
    class CtxFalso:
        lock = MagicMock()
        hablante = MagicMock()
    ctx = CtxFalso()
    ctx.lock.__enter__ = MagicMock(return_value=None)
    ctx.lock.__exit__ = MagicMock(return_value=None)
    return ctx


def test_no_matchea_texto_sin_relacion():
    control_falso = MagicMock()
    assert GithubSyncIntent(control_falso).manejar("hola como estas", ctx=_ctx_falso()) is None
    control_falso.sincronizar.assert_not_called()


def test_responde_de_inmediato_sin_esperar_la_sincronizacion():
    control_falso = MagicMock()
    control_falso.sincronizar.return_value = "listo"
    resultado = GithubSyncIntent(control_falso).manejar("sincroniza mi github", ctx=_ctx_falso())
    assert "segundo plano" in resultado.lower()


def test_llama_a_sincronizar_y_avisa_por_voz_al_terminar():
    control_falso = MagicMock()
    control_falso.sincronizar.return_value = "Sincronicé tu GitHub: 3 actualizado(s)."
    ctx = _ctx_falso()

    GithubSyncIntent(control_falso).manejar("actualiza mis repos", ctx=ctx)
    time.sleep(0.05)  # el hilo de fondo alcanza a correr

    control_falso.sincronizar.assert_called_once_with()
    ctx.hablante.hablar.assert_called_once_with("Sincronicé tu GitHub: 3 actualizado(s).")


def test_variantes_de_frase():
    control_falso = MagicMock()
    intent = GithubSyncIntent(control_falso)
    for frase in ["sincroniza github", "actualiza github", "actualiza mi codigo"]:
        assert intent.manejar(frase, ctx=_ctx_falso()) is not None


def test_sin_inyectar_nada_usa_la_implementacion_real_por_defecto():
    from core.integraciones import GitHubGit
    assert isinstance(GithubSyncIntent()._control_versiones, GitHubGit)
