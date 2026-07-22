from unittest.mock import patch

from intents.volumen import VolumenIntent


def test_no_matchea_texto_sin_relacion():
    assert VolumenIntent().manejar("hola como estas", ctx=None) is None


def test_sube_el_volumen():
    with patch("intents.volumen.subir_volumen") as mock_subir:
        mock_subir.return_value = "Subí el volumen a 50."
        resultado = VolumenIntent().manejar("sube el volumen", ctx=None)
        assert resultado == "Subí el volumen a 50."
        mock_subir.assert_called_once()


def test_baja_el_volumen():
    with patch("intents.volumen.bajar_volumen") as mock_bajar:
        mock_bajar.return_value = "Bajé el volumen a 20."
        resultado = VolumenIntent().manejar("baja el volumen", ctx=None)
        assert resultado == "Bajé el volumen a 20."
        mock_bajar.assert_called_once()


def test_silenciar():
    with patch("intents.volumen.silenciar") as mock_silenciar:
        mock_silenciar.return_value = "Silenciado."
        resultado = VolumenIntent().manejar("silencia", ctx=None)
        assert resultado == "Silenciado."
        mock_silenciar.assert_called_once()
