"""osascript siempre mockeado: de verdad cambiaría el volumen real de esta
Mac si no lo estuviera."""

from unittest.mock import MagicMock, patch

from skills.volumen import bajar_volumen, silenciar, subir_volumen


def test_subir_volumen_suma_el_paso_y_clampa_a_100():
    with patch("skills.volumen.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="95\n")
        resultado = subir_volumen(paso=15)
        assert resultado == "Subí el volumen a 100."
        ultima_llamada = mock_run.call_args_list[-1].args[0]
        assert "set volume output volume 100" in ultima_llamada[-1]


def test_bajar_volumen_resta_el_paso_y_clampa_a_0():
    with patch("skills.volumen.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="10\n")
        resultado = bajar_volumen(paso=15)
        assert resultado == "Bajé el volumen a 0."
        ultima_llamada = mock_run.call_args_list[-1].args[0]
        assert "set volume output volume 0" in ultima_llamada[-1]


def test_silenciar_fija_en_cero():
    with patch("skills.volumen.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="")
        resultado = silenciar()
        assert resultado == "Silenciado."
        ultima_llamada = mock_run.call_args_list[-1].args[0]
        assert "set volume output volume 0" in ultima_llamada[-1]


def test_error_leyendo_volumen_no_truena():
    with patch("skills.volumen.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="no-es-un-numero")
        resultado = subir_volumen()
        assert "no pude leer" in resultado.lower()
