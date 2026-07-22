from unittest.mock import MagicMock, patch

from intents.grafico_obsidian import GraficoObsidianIntent


def _ctx_falso(puerto=5005):
    class Ctx:
        ctx_skills = {"puerto_remoto": puerto}
    return Ctx()


def test_no_matchea_texto_sin_relacion():
    assert GraficoObsidianIntent().manejar("hola como estas", ctx=_ctx_falso()) is None


def test_abre_el_grafo_con_el_puerto_correcto():
    with patch("intents.grafico_obsidian.abrir_en_brave") as mock_abrir:
        mock_abrir.return_value = True
        resultado = GraficoObsidianIntent().manejar("abre el grafo de mis notas", ctx=_ctx_falso(5005))
        assert "abriendo el grafo" in resultado.lower()
        mock_abrir.assert_called_once_with("http://localhost:5005/grafico-obsidian")


def test_variantes_de_frase():
    with patch("intents.grafico_obsidian.abrir_en_brave", return_value=True):
        intent = GraficoObsidianIntent()
        for frase in ["muéstrame el grafo de Obsidian", "abre la vista gráfica de Obsidian", "abre el mapa de mis notas"]:
            assert intent.manejar(frase, ctx=_ctx_falso()) is not None


def test_error_si_brave_no_abre():
    with patch("intents.grafico_obsidian.abrir_en_brave", return_value=False):
        resultado = GraficoObsidianIntent().manejar("abre el grafo de mis notas", ctx=_ctx_falso())
        assert "no pude abrir brave" in resultado.lower()
