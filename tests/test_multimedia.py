"""Regresión del bug real: "pon música de Queen" se clasificaba como genérico
(por usar startswith) y reproducía la playlist de Me Gusta en vez de buscar
la canción pedida."""

from unittest.mock import MagicMock, patch

import pytest

from intents.multimedia import MultimediaIntent


@pytest.fixture
def intent_musica():
    with patch("skills.navegador.subprocess.run") as mock_run, \
         patch("skills.musica._obtener_cliente_ytmusic") as mock_cliente:
        mock_run.return_value = MagicMock(returncode=0)
        mock_cliente.return_value.search.return_value = [{"videoId": "XYZ", "title": "prueba"}]
        yield MultimediaIntent(), mock_cliente


def test_generico_reproduce_playlist_me_gusta(intent_musica):
    intent, _ = intent_musica
    assert intent.manejar("pon musica", ctx=None) == "Reproduciendo tu música que te gusta."


def test_cancion_con_palabra_musica_no_cae_en_generico(intent_musica):
    """Este es el bug exacto que se reportó y corrigió."""
    intent, mock_cliente = intent_musica
    resultado = intent.manejar("pon musica de queen", ctx=None)
    assert resultado != "Reproduciendo tu música que te gusta."
    assert "queen" in resultado.lower()
    mock_cliente.return_value.search.assert_called_with("queen", filter="songs", limit=1)


def test_cancion_especifica_limpia_relleno(intent_musica):
    intent, mock_cliente = intent_musica
    intent.manejar("pon la cancion bohemian rhapsody de queen", ctx=None)
    mock_cliente.return_value.search.assert_called_with("bohemian rhapsody de queen", filter="songs", limit=1)


def test_frase_sin_relacion_no_matchea(intent_musica):
    intent, _ = intent_musica
    assert intent.manejar("hola como estas", ctx=None) is None


def test_pausa_la_musica():
    with patch("intents.multimedia.pausar_musica") as mock_pausar:
        mock_pausar.return_value = "Música pausada."
        intent = MultimediaIntent()
        assert intent.manejar("pausa la musica", ctx=None) == "Música pausada."
        mock_pausar.assert_called_once()


def test_reanuda_la_musica():
    with patch("intents.multimedia.reanudar_musica") as mock_reanudar:
        mock_reanudar.return_value = "Reanudando la música."
        intent = MultimediaIntent()
        assert intent.manejar("reanuda la musica", ctx=None) == "Reanudando la música."
        mock_reanudar.assert_called_once()
