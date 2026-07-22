"""Cadena de respaldo de 3 niveles: ElevenLabs -> Kokoro (voz local) -> `say`
de macOS (último recurso). Cada nivel se mockea por separado para que los
tests no dependan de tener los archivos reales del modelo de Kokoro ni de
llamar a un servicio real."""

from unittest.mock import patch

from core.hablante import Hablante


def test_usa_elevenlabs_si_funciona():
    with patch("core.hablante.ElevenLabs"):
        h = Hablante("fake-key", "voice123")
        h._cliente.text_to_speech.convert.return_value = [b"fake", b"mp3", b"bytes"]

        audio_bytes, mime = h.sintetizar("hola")

        assert mime == "audio/mpeg"
        assert audio_bytes == b"fakemp3bytes"
        assert h.usando_voz_sistema is False
        assert h.motor_voz == "elevenlabs"


def test_cae_a_kokoro_si_elevenlabs_falla():
    with patch("core.hablante.ElevenLabs"), patch.object(Hablante, "_sintetizar_kokoro") as mock_kokoro:
        h = Hablante("fake-key", "voice123")
        h._cliente.text_to_speech.convert.side_effect = Exception("quota_exceeded")
        mock_kokoro.return_value = b"audio kokoro falso"

        audio_bytes, mime = h.sintetizar("hola, esto es una prueba")

        assert mime == "audio/wav"
        assert audio_bytes == b"audio kokoro falso"
        assert h.usando_voz_sistema is True
        assert h.motor_voz == "kokoro"


def test_cae_a_voz_de_sistema_si_elevenlabs_y_kokoro_fallan():
    """Última red de seguridad: si ni ElevenLabs ni Kokoro funcionan (ej. no
    se descargaron los archivos del modelo), sigue sin quedarse mudo."""
    with patch("core.hablante.ElevenLabs"), patch.object(Hablante, "_sintetizar_kokoro", return_value=None):
        h = Hablante("fake-key", "voice123")
        h._cliente.text_to_speech.convert.side_effect = Exception("quota_exceeded")

        audio_bytes, mime = h.sintetizar("hola, esto es una prueba")

        assert mime == "audio/wav"
        assert audio_bytes and len(audio_bytes) > 0
        assert audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE"
        assert h.usando_voz_sistema is True
        assert h.motor_voz == "sistema"


def test_forzar_voz_sistema_salta_elevenlabs_pero_prueba_kokoro_primero():
    with patch("core.hablante.ElevenLabs"), patch.object(Hablante, "_sintetizar_kokoro") as mock_kokoro:
        h = Hablante("fake-key", "voice123", forzar_voz_sistema=True)
        mock_kokoro.return_value = b"audio kokoro falso"

        audio_bytes, mime = h.sintetizar("hola")

        h._cliente.text_to_speech.convert.assert_not_called()
        assert audio_bytes == b"audio kokoro falso"
        assert mime == "audio/wav"


def test_kokoro_usa_espanol_latinoamericano_y_la_voz_configurada():
    with patch("core.hablante.ElevenLabs"), \
         patch.object(Hablante, "_obtener_kokoro") as mock_obtener, \
         patch("soundfile.write") as mock_write:
        h = Hablante("fake-key", "voice123", voz_kokoro="ef_dora")
        kokoro_falso = mock_obtener.return_value
        kokoro_falso.create.return_value = ([0.1, 0.2, 0.3], 24000)

        h._sintetizar_kokoro("hola")

        kokoro_falso.create.assert_called_once_with("hola", voice="ef_dora", speed=1.0, lang="es-419")


def test_texto_vacio_no_sintetiza_nada():
    with patch("core.hablante.ElevenLabs"):
        h = Hablante("fake-key", "voice123")
        assert h.sintetizar("") == (None, None)
        assert h.sintetizar("   ") == (None, None)


def test_hablar_registra_el_ultimo_texto_dicho():
    """El bucle principal usa esto para descartar el eco de la propia voz de
    Jarvis en el micrófono (ver core/eco.py) — sin registrar qué dijo, no
    hay nada contra qué comparar."""
    with patch("core.hablante.ElevenLabs"), patch.object(Hablante, "_reproducir_localmente"):
        h = Hablante("fake-key", "voice123")
        h._cliente.text_to_speech.convert.return_value = [b"audio"]
        assert h.ultimo_texto_hablado is None
        h.hablar("Notificación mandada a tu celular.")
        assert h.ultimo_texto_hablado == "Notificación mandada a tu celular."


def test_reproducir_en_segundo_plano_tambien_registra_el_texto():
    """Se registra de inmediato (no espera al hilo de fondo) — el bucle
    principal debe poder comparar contra esto tan pronto Jarvis empieza a
    sonar, no cuando termine."""
    with patch("core.hablante.ElevenLabs"), patch.object(Hablante, "_reproducir_localmente"):
        h = Hablante("fake-key", "voice123")
        h.reproducir_en_segundo_plano(b"audio", "audio/mpeg", texto="Instalando spotify.")
        assert h.ultimo_texto_hablado == "Instalando spotify."
