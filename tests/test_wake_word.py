"""EscuchadorPalabraClave sin hardware real: mockea Model (openWakeWord) y
PyAudio para probar que 'esperar()' bloquea hasta que el score de predicción
cruza el umbral, y que cierra el stream de audio al terminar (para no
competir por el micrófono con Oyente mientras Jarvis procesa el comando)."""

from unittest.mock import MagicMock, patch

from core.wake_word import EscuchadorPalabraClave, TAMANO_FRAGMENTO


def test_esperar_bloquea_hasta_cruzar_el_umbral():
    with patch("core.wake_word.Model") as MockModel, patch("core.wake_word.pyaudio.PyAudio") as MockPyAudio:
        modelo = MockModel.return_value
        modelo.predict.side_effect = [
            {"hey_jarvis": 0.0},
            {"hey_jarvis": 0.2},
            {"hey_jarvis": 0.9},
        ]
        stream = MockPyAudio.return_value.open.return_value
        stream.read.return_value = b"\x00" * (TAMANO_FRAGMENTO * 2)

        escuchador = EscuchadorPalabraClave()
        escuchador.esperar()

        assert modelo.predict.call_count == 3
        modelo.reset.assert_called_once()
        stream.stop_stream.assert_called_once()
        stream.close.assert_called_once()


def test_cerrar_libera_pyaudio():
    with patch("core.wake_word.Model"), patch("core.wake_word.pyaudio.PyAudio") as MockPyAudio:
        escuchador = EscuchadorPalabraClave()
        escuchador.cerrar()
        MockPyAudio.return_value.terminate.assert_called_once()
