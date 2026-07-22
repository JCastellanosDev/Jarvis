from unittest.mock import patch

from intents.descargas import DescargasIntent


def test_no_matchea_texto_sin_relacion():
    intent = DescargasIntent()
    assert intent.manejar("hola como estas", ctx=None) is None


def test_descarga_video_por_titulo():
    with patch("intents.descargas.descargar_youtube") as mock_descargar:
        mock_descargar.return_value = "Descargué el video de X."
        intent = DescargasIntent()
        resultado = intent.manejar("descarga el video de bohemian rhapsody", ctx=None)
        assert resultado == "Descargué el video de X."
        mock_descargar.assert_called_once_with("bohemian rhapsody", solo_audio=False)


def test_descarga_audio_por_titulo():
    with patch("intents.descargas.descargar_youtube") as mock_descargar:
        mock_descargar.return_value = "Descargué el audio."
        intent = DescargasIntent()
        intent.manejar("descarga en mp3 bohemian rhapsody", ctx=None)
        mock_descargar.assert_called_once_with("bohemian rhapsody", solo_audio=True)


def test_descarga_cancion_es_solo_audio():
    with patch("intents.descargas.descargar_youtube") as mock_descargar:
        mock_descargar.return_value = "ok"
        intent = DescargasIntent()
        intent.manejar("descarga la cancion shape of you", ctx=None)
        mock_descargar.assert_called_once_with("shape of you", solo_audio=True)


def test_descarga_lo_abierto_en_el_navegador():
    with patch("intents.descargas.descargar_lo_abierto_en_navegador") as mock_abierto:
        mock_abierto.return_value = "Descargué lo que tenías abierto."
        intent = DescargasIntent()
        for frase in ["descarga esto", "descarga lo que tengo abierto", "descarga esta pagina"]:
            resultado = intent.manejar(frase, ctx=None)
            assert resultado == "Descargué lo que tenías abierto."
        assert mock_abierto.call_count == 3
