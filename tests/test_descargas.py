from unittest.mock import MagicMock, patch

from intents.descargas import MENSAJE_EN_PROGRESO, DescargasIntent


def _ctx_falso():
    class Ctx:
        hablante = MagicMock()
    return Ctx()


def test_no_matchea_texto_sin_relacion():
    intent = DescargasIntent()
    assert intent.manejar("hola como estas", ctx=_ctx_falso()) is None


def test_descarga_video_por_titulo_corre_en_segundo_plano():
    with patch("intents.descargas.descargar_youtube_en_segundo_plano") as mock_descargar:
        ctx = _ctx_falso()
        intent = DescargasIntent()
        resultado = intent.manejar("descarga el video de bohemian rhapsody", ctx)
        assert resultado == MENSAJE_EN_PROGRESO
        mock_descargar.assert_called_once_with("bohemian rhapsody", False, ctx.hablante)


def test_descarga_audio_por_titulo():
    with patch("intents.descargas.descargar_youtube_en_segundo_plano") as mock_descargar:
        ctx = _ctx_falso()
        intent = DescargasIntent()
        intent.manejar("descarga en mp3 bohemian rhapsody", ctx)
        mock_descargar.assert_called_once_with("bohemian rhapsody", True, ctx.hablante)


def test_descarga_cancion_es_solo_audio():
    with patch("intents.descargas.descargar_youtube_en_segundo_plano") as mock_descargar:
        ctx = _ctx_falso()
        intent = DescargasIntent()
        intent.manejar("descarga la cancion shape of you", ctx)
        mock_descargar.assert_called_once_with("shape of you", True, ctx.hablante)


def test_descarga_lo_abierto_en_el_navegador():
    with patch("intents.descargas.descargar_lo_abierto_en_navegador_en_segundo_plano") as mock_abierto:
        ctx = _ctx_falso()
        intent = DescargasIntent()
        for frase in ["descarga esto", "descarga lo que tengo abierto", "descarga esta pagina"]:
            resultado = intent.manejar(frase, ctx)
            assert resultado == MENSAJE_EN_PROGRESO
        assert mock_abierto.call_count == 3
        mock_abierto.assert_called_with(ctx.hablante)
