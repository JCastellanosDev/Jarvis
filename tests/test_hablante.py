"""Regresión: cuando ElevenLabs falla (sin créditos, sin conexión), Hablante
debe caer a la voz del sistema en vez de quedarse mudo."""

from unittest.mock import patch

from core.hablante import Hablante


def test_cae_a_voz_de_sistema_si_elevenlabs_falla():
    with patch("core.hablante.ElevenLabs"):
        h = Hablante("fake-key", "voice123")
        h._cliente.text_to_speech.convert.side_effect = Exception("quota_exceeded")

        audio_bytes, mime = h.sintetizar("hola, esto es una prueba")

        assert mime == "audio/wav"
        assert audio_bytes and len(audio_bytes) > 0
        assert audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE"
        assert h.usando_voz_sistema is True


def test_usa_elevenlabs_si_funciona():
    with patch("core.hablante.ElevenLabs"):
        h = Hablante("fake-key", "voice123")
        h._cliente.text_to_speech.convert.return_value = [b"fake", b"mp3", b"bytes"]

        audio_bytes, mime = h.sintetizar("hola")

        assert mime == "audio/mpeg"
        assert audio_bytes == b"fakemp3bytes"
        assert h.usando_voz_sistema is False


def test_texto_vacio_no_sintetiza_nada():
    with patch("core.hablante.ElevenLabs"):
        h = Hablante("fake-key", "voice123")
        assert h.sintetizar("") == (None, None)
        assert h.sintetizar("   ") == (None, None)
