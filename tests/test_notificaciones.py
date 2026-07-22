from unittest.mock import patch

from intents.notificaciones import NotificacionesIntent


def test_no_matchea_texto_sin_relacion():
    assert NotificacionesIntent().manejar("hola como estas", ctx=None) is None


def test_manda_notificacion_por_voz():
    with patch("intents.notificaciones.enviar_notificacion") as mock_enviar:
        mock_enviar.return_value = (True, "Notificación enviada.")
        resultado = NotificacionesIntent().manejar(
            "mandame una notificacion que diga ya llegue a casa", ctx=None
        )
        assert "notificación mandada" in resultado.lower()
        mock_enviar.assert_called_once_with("Jarvis", "ya llegue a casa")


def test_devuelve_el_error_si_no_esta_configurado():
    with patch("intents.notificaciones.enviar_notificacion") as mock_enviar:
        mock_enviar.return_value = (False, "No configuraste NTFY_TOPIC en tu .env.")
        resultado = NotificacionesIntent().manejar("avisame al celular que ya acabe", ctx=None)
        assert "ntfy_topic" in resultado.lower()
