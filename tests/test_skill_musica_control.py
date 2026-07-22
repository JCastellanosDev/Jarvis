"""osascript siempre mockeado. Pausar/reanudar usan v.pause()/v.play() (no un
toggle de teclado): pausar SIEMPRE pausa, reanudar SIEMPRE reanuda, sin
adivinar el estado actual del video."""

from unittest.mock import MagicMock, patch

from skills.musica import pausar_musica, reanudar_musica


def test_pausar_llama_pause_no_toggle():
    with patch("skills.musica.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        resultado = pausar_musica()
        assert resultado == "Música pausada."
        script = mock_run.call_args.args[0][-1]
        assert "v.pause()" in script
        assert "v.play()" not in script


def test_reanudar_llama_play_no_toggle():
    with patch("skills.musica.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        resultado = reanudar_musica()
        assert resultado == "Reanudando la música."
        script = mock_run.call_args.args[0][-1]
        assert "v.play()" in script


def test_sin_video_en_la_pestana():
    with patch("skills.musica.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="SIN_VIDEO", stderr="")
        resultado = pausar_musica()
        assert "no encontré nada reproduciéndose" in resultado.lower()


def test_sin_brave_abierto():
    with patch("skills.musica.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="SIN_VENTANA", stderr="")
        resultado = pausar_musica()
        assert "no tienes brave abierto" in resultado.lower()


def test_error_de_applescript_avisa_permiso_de_javascript():
    with patch("skills.musica.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Not allowed to send Apple events")
        resultado = pausar_musica()
        assert "permitir javascript" in resultado.lower()
