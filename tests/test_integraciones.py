"""Los adaptadores (GitHubGit, WhatsAppDesktop) son envolturas delgadas: se
mockea la función de skills/ que envuelven, nunca I/O real (git, osascript,
red). También se confirma que satisfacen estructuralmente el Protocol
correspondiente — eso es lo que le permite a un intent depender de la
interfaz sin importar la clase concreta."""

from unittest.mock import patch

from core.integraciones import ControlVersiones, GitHubGit, Mensajeria, WhatsAppDesktop


def test_github_git_satisface_control_versiones():
    assert isinstance(GitHubGit(), ControlVersiones)


def test_whatsapp_desktop_satisface_mensajeria():
    assert isinstance(WhatsAppDesktop(), Mensajeria)


def test_github_git_sincronizar_delega_en_la_skill():
    with patch("core.integraciones.sincronizar_repos", return_value="Sincronicé tu GitHub: 2 actualizado(s).") as mock:
        resultado = GitHubGit().sincronizar()
    mock.assert_called_once_with()
    assert resultado == "Sincronicé tu GitHub: 2 actualizado(s)."


def test_github_git_subir_cambios_delega_en_la_skill():
    pedir_mensaje = lambda pregunta: "arreglo bug"
    with patch("core.integraciones.subir_cambios_github", return_value="Cambios subidos.") as mock:
        resultado = GitHubGit().subir_cambios("/ruta/repo", pedir_mensaje)
    mock.assert_called_once_with("/ruta/repo", pedir_mensaje)
    assert resultado == "Cambios subidos."


def test_whatsapp_desktop_enviar_delega_en_la_skill():
    with patch("core.integraciones.enviar_whatsapp", return_value="Mensaje enviado a chuy por WhatsApp.") as mock:
        resultado = WhatsAppDesktop().enviar("chuy", "ya voy")
    mock.assert_called_once_with("chuy", "ya voy")
    assert resultado == "Mensaje enviado a chuy por WhatsApp."
