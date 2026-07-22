"""Regla de negocio importante: NUNCA debe instalar nada sin que el usuario
confirme por voz — Jarvis busca en Homebrew (no en resultados de búsqueda
al azar) y siempre pregunta antes de ejecutar la instalación real."""

from unittest.mock import MagicMock, patch

from intents.instalador import InstaladorIntent


def _ctx_falso(respuesta_confirmacion):
    class Ctx:
        hablante = MagicMock()
        ctx_skills = {"pedir_texto_por_voz": lambda pregunta: respuesta_confirmacion}
    return Ctx()


def test_no_matchea_texto_sin_relacion():
    intent = InstaladorIntent()
    assert intent.manejar("hola como estas", ctx=_ctx_falso("si")) is None


def test_no_encontrado_en_homebrew_no_instala_nada():
    with patch("intents.instalador.buscar_en_homebrew", return_value=(None, None)), \
         patch("intents.instalador.instalar_en_segundo_plano") as mock_instalar:
        intent = InstaladorIntent()
        resultado = intent.manejar("instala programaquenoexiste123", ctx=_ctx_falso("si"))
        assert "no encontré" in resultado.lower()
        mock_instalar.assert_not_called()


def test_confirma_antes_de_instalar():
    with patch("intents.instalador.buscar_en_homebrew", return_value=("spotify", "cask")), \
         patch("intents.instalador.instalar_en_segundo_plano") as mock_instalar:
        intent = InstaladorIntent()
        resultado = intent.manejar("instala spotify", ctx=_ctx_falso("si por favor"))
        assert "instalando spotify" in resultado.lower()
        mock_instalar.assert_called_once()
        assert mock_instalar.call_args.args[0] == "spotify"
        assert mock_instalar.call_args.args[1] == "cask"


def test_no_instala_si_no_confirmas():
    with patch("intents.instalador.buscar_en_homebrew", return_value=("spotify", "cask")), \
         patch("intents.instalador.instalar_en_segundo_plano") as mock_instalar:
        intent = InstaladorIntent()
        resultado = intent.manejar("instala spotify", ctx=_ctx_falso("no, mejor no"))
        assert "no confirmaste" in resultado.lower()
        mock_instalar.assert_not_called()


def test_sin_respuesta_no_instala_nada():
    with patch("intents.instalador.buscar_en_homebrew", return_value=("spotify", "cask")), \
         patch("intents.instalador.instalar_en_segundo_plano") as mock_instalar:
        intent = InstaladorIntent()
        resultado = intent.manejar("instalame spotify", ctx=_ctx_falso(None))
        assert "no confirmaste" in resultado.lower()
        mock_instalar.assert_not_called()
