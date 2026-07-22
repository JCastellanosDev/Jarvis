"""subprocess.run (brew) siempre mockeado: de verdad instalaría software en
esta máquina si no lo estuviera."""

from unittest.mock import MagicMock, patch

from skills.instalador import buscar_en_homebrew, instalar_en_segundo_plano


def test_prefiere_cask_sobre_formula():
    with patch("skills.instalador.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="spotify\n", stderr="")
        candidato, tipo = buscar_en_homebrew("spotify")
        assert candidato == "spotify"
        assert tipo == "cask"
        # Solo debió buscar en casks; no hizo falta caer a fórmulas.
        assert mock_run.call_count == 1


def test_cae_a_formula_si_no_hay_cask():
    respuestas = [
        MagicMock(returncode=0, stdout="", stderr=""),  # brew search --cask: nada
        MagicMock(returncode=0, stdout="==> Formulae\nwget\n", stderr=""),
    ]
    with patch("skills.instalador.subprocess.run", side_effect=respuestas):
        candidato, tipo = buscar_en_homebrew("wget")
        assert candidato == "wget"
        assert tipo == "formula"


def test_nada_encontrado_devuelve_none():
    with patch("skills.instalador.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        candidato, tipo = buscar_en_homebrew("programaquenoexiste123")
        assert candidato is None
        assert tipo is None


def test_instalar_en_segundo_plano_no_bloquea_y_avisa_por_voz_y_push_al_terminar():
    """No debe bloquear el hilo que llama (Jarvis debe seguir funcionando
    mientras Homebrew instala) y debe avisar por voz + notificación push
    cuando termine."""
    hablante = MagicMock()
    with patch("skills.instalador.subprocess.run") as mock_run, \
         patch("skills.instalador.enviar_notificacion") as mock_notificar:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        hilo = instalar_en_segundo_plano("spotify", "cask", hablante)
        assert hilo.daemon is True
        hilo.join(timeout=2)

    hablante.hablar.assert_called_once()
    assert "instalado" in hablante.hablar.call_args.args[0].lower()
    mock_notificar.assert_called_once()


def test_instalar_reporta_error_por_voz_si_brew_falla():
    hablante = MagicMock()
    with patch("skills.instalador.subprocess.run") as mock_run, \
         patch("skills.instalador.enviar_notificacion"):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="No available formula")

        hilo = instalar_en_segundo_plano("noexiste", "formula", hablante)
        hilo.join(timeout=2)

    mensaje = hablante.hablar.call_args.args[0].lower()
    assert "no pude instalar" in mensaje
