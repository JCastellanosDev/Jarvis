"""requests.post siempre mockeado: de verdad mandaría una notificación real
a ntfy.sh si no lo estuviera."""

import os
from unittest.mock import MagicMock, patch

from skills.notificaciones import enviar_notificacion, sugerir_tema


def test_sin_tema_configurado_no_manda_nada():
    with patch.dict(os.environ, {}, clear=True):
        ok, detalle = enviar_notificacion("Título", "mensaje")
        assert ok is False
        assert "ntfy_topic" in detalle.lower()


def test_envia_notificacion_con_tema_configurado():
    with patch.dict(os.environ, {"NTFY_TOPIC": "jarvis-test123"}), \
         patch("skills.notificaciones.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()

        ok, detalle = enviar_notificacion("Descarga completa", "Tu video ya está listo")

        assert ok is True
        url = mock_post.call_args.args[0]
        assert url == "https://ntfy.sh/jarvis-test123"
        assert mock_post.call_args.kwargs["headers"]["Title"] == "Descarga completa"


def test_error_de_red_no_truena():
    import requests as requests_mod
    with patch.dict(os.environ, {"NTFY_TOPIC": "jarvis-test123"}), \
         patch("skills.notificaciones.requests.post", side_effect=requests_mod.ConnectionError("sin red")):
        ok, detalle = enviar_notificacion("Título", "mensaje")
        assert ok is False
        assert "no pude mandar" in detalle.lower()


def test_sugerir_tema_es_random_y_con_prefijo():
    tema1 = sugerir_tema()
    tema2 = sugerir_tema()
    assert tema1.startswith("jarvis-")
    assert tema1 != tema2
