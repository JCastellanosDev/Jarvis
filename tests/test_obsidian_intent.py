"""Regresión: "accede a Obsidian para que me digas quién soy" no coincidía
con ningún patrón (demasiado rígidos) y caía al chat general, que alucinaba
"no puedo acceder a tus notas" sin siquiera intentarlo."""

from unittest.mock import MagicMock, patch

from intents.obsidian import ObsidianIntent


def _ctx_falso():
    class Ctx:
        memoria = MagicMock()
        cerebro = MagicMock()
        cerebro.responder.side_effect = lambda prompt, mem, **kw: f"[LLM] {kw.get('contexto_obsidian')}"
    return Ctx()


def test_no_matchea_texto_sin_relacion():
    intent = ObsidianIntent()
    assert intent.manejar("hola como estas", ctx=_ctx_falso()) is None


def test_frase_real_que_antes_fallaba():
    with patch("intents.obsidian.buscar_en_obsidian") as mock_buscar:
        mock_buscar.return_value = "### Perfil\ncontenido"
        intent = ObsidianIntent()
        resultado = intent.manejar("accede a Obsidian para que me digas quién soy", ctx=_ctx_falso())
        assert resultado is not None
        # Debió redirigir la búsqueda a "perfil", no buscar "quien"+"soy" literal.
        assert mock_buscar.call_args.args[0] == "perfil"


def test_quien_soy_directo_tambien_busca_perfil():
    with patch("intents.obsidian.buscar_en_obsidian") as mock_buscar:
        mock_buscar.return_value = "### Perfil\ncontenido"
        intent = ObsidianIntent()
        intent.manejar("quien soy", ctx=_ctx_falso())
        assert mock_buscar.call_args.args[0] == "perfil"


def test_patrones_flexibles_de_acceso():
    with patch("intents.obsidian.buscar_en_obsidian") as mock_buscar:
        mock_buscar.return_value = "### Nota\ncontenido"
        intent = ObsidianIntent()
        for frase in [
            "entra a mis notas y dime sobre videojuegos",
            "busca en obsidian sobre videojuegos",
            "según mis notas, videojuegos",
        ]:
            assert intent.manejar(frase, ctx=_ctx_falso()) is not None, f"no matcheó: {frase!r}"


def test_sin_resultados_no_inventa_nada():
    with patch("intents.obsidian.buscar_en_obsidian") as mock_buscar:
        mock_buscar.return_value = None
        intent = ObsidianIntent()
        resultado = intent.manejar("busca en obsidian sobre algo que no existe", ctx=_ctx_falso())
        assert "no encontré nada" in resultado.lower()
