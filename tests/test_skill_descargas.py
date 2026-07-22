"""yt_dlp, requests y osascript siempre mockeados: de verdad descargaría
archivos y llamaría a Brave si no lo estuvieran."""

from unittest.mock import MagicMock, patch

from skills.descargas import (
    descargar_lo_abierto_en_navegador, descargar_lo_abierto_en_navegador_en_segundo_plano,
    descargar_youtube, descargar_youtube_en_segundo_plano,
)


def test_descargar_youtube_arma_bien_las_opciones_de_audio():
    with patch("skills.descargas.yt_dlp.YoutubeDL") as MockYDL:
        instancia = MockYDL.return_value.__enter__.return_value
        instancia.extract_info.return_value = {"title": "Bohemian Rhapsody"}

        resultado = descargar_youtube("bohemian rhapsody", solo_audio=True)

        assert "audio" in resultado.lower()
        assert "Bohemian Rhapsody" in resultado
        opciones = MockYDL.call_args.args[0]
        assert opciones["postprocessors"][0]["preferredcodec"] == "mp3"


def test_descargar_youtube_video_no_agrega_postprocesador_de_audio():
    with patch("skills.descargas.yt_dlp.YoutubeDL") as MockYDL:
        instancia = MockYDL.return_value.__enter__.return_value
        instancia.extract_info.return_value = {"title": "Un video"}

        descargar_youtube("un video", solo_audio=False)

        opciones = MockYDL.call_args.args[0]
        assert "postprocessors" not in opciones


def test_descargar_youtube_toma_el_primero_si_es_busqueda():
    with patch("skills.descargas.yt_dlp.YoutubeDL") as MockYDL:
        instancia = MockYDL.return_value.__enter__.return_value
        instancia.extract_info.return_value = {"entries": [{"title": "Resultado 1"}, {"title": "Resultado 2"}]}

        resultado = descargar_youtube("algo", solo_audio=False)

        assert "Resultado 1" in resultado


def test_descargar_youtube_error_no_truena():
    with patch("skills.descargas.yt_dlp.YoutubeDL") as MockYDL:
        MockYDL.return_value.__enter__.return_value.extract_info.side_effect = Exception("network down")
        resultado = descargar_youtube("algo", solo_audio=False)
        assert "no pude descargar" in resultado.lower()


def test_descargar_lo_abierto_en_navegador_detecta_youtube():
    with patch("skills.descargas.subprocess.run") as mock_run, \
         patch("skills.descargas.descargar_youtube") as mock_ytdlp:
        mock_run.return_value = MagicMock(returncode=0, stdout="https://www.youtube.com/watch?v=abc123\n")
        mock_ytdlp.return_value = "Descargué el video."

        resultado = descargar_lo_abierto_en_navegador()

        assert resultado == "Descargué el video."
        mock_ytdlp.assert_called_once_with("https://www.youtube.com/watch?v=abc123", solo_audio=False)


def test_descargar_lo_abierto_en_navegador_sin_brave_abierto():
    with patch("skills.descargas.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        resultado = descargar_lo_abierto_en_navegador()
        assert "no pude ver" in resultado.lower()


def test_descargar_lo_abierto_en_navegador_archivo_directo():
    with patch("skills.descargas.subprocess.run") as mock_run, \
         patch("skills.descargas.requests.get") as mock_get:
        mock_run.return_value = MagicMock(returncode=0, stdout="https://example.com/archivo.pdf\n")
        mock_get.return_value = MagicMock(content=b"contenido falso", status_code=200)
        mock_get.return_value.raise_for_status = MagicMock()

        with patch("builtins.open", MagicMock()), patch("skills.descargas.os.makedirs"):
            resultado = descargar_lo_abierto_en_navegador()

        assert "archivo.pdf" in resultado


def test_descarga_en_segundo_plano_no_bloquea_y_avisa_por_voz_y_push():
    hablante = MagicMock()
    with patch("skills.descargas.descargar_youtube", return_value="Descargué el video de X."), \
         patch("skills.descargas.enviar_notificacion") as mock_notificar:
        hilo = descargar_youtube_en_segundo_plano("bohemian rhapsody", False, hablante)
        assert hilo.daemon is True
        hilo.join(timeout=2)

    hablante.hablar.assert_called_once_with("Descargué el video de X.")
    mock_notificar.assert_called_once_with("Descarga completa", "Descargué el video de X.")


def test_descarga_de_lo_abierto_en_segundo_plano():
    hablante = MagicMock()
    with patch("skills.descargas.descargar_lo_abierto_en_navegador", return_value="Descargué lo abierto."), \
         patch("skills.descargas.enviar_notificacion") as mock_notificar:
        hilo = descargar_lo_abierto_en_navegador_en_segundo_plano(hablante)
        hilo.join(timeout=2)

    hablante.hablar.assert_called_once_with("Descargué lo abierto.")
    mock_notificar.assert_called_once_with("Descarga completa", "Descargué lo abierto.")
