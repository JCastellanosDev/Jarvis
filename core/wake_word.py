"""Detección local de la palabra clave "Hey Jarvis" (openWakeWord), para que
Jarvis esté escuchando siempre pero solo procese lo que digas después de
llamarlo por su nombre — mientras espera, el audio nunca sale de tu Mac ni
se manda a Google (a diferencia de Oyente, que sí usa reconocimiento en la
nube para el comando real).

100% gratis y SIN cuenta de ningún tipo: se probó primero con Porcupine
(Picovoice), pero su formulario de registro exige un email de "empresa" y
rechaza Gmail/Yahoo/etc. incluso para el plan Personal gratuito. openWakeWord
es open source, no pide registro, y ya trae pre-entrenado el modelo
"hey_jarvis" (no hay que entrenar nada personalizado).
"""

import os
import time

import numpy as np
import pyaudio
from openwakeword.model import Model

TASA_MUESTREO = 16000
TAMANO_FRAGMENTO = 1280  # 80ms a 16kHz — tamaño de bloque recomendado por openWakeWord
# 0.5 (el default "de catálogo") resultó demasiado exigente en pruebas reales
# con acento — bájalo más (env WAKE_WORD_UMBRAL) si sigue sin activarse, o
# súbelo si se activa solo con ruido de fondo.
UMBRAL_DETECCION = float(os.getenv("WAKE_WORD_UMBRAL", "0.35"))
# DEBUG_WAKE_WORD=true en .env: imprime el score de cada fragmento de audio,
# para ver en vivo qué tan cerca (o lejos) está tu voz del umbral — sin esto
# es imposible saber si el mic no está captando nada o si solo falta afinar
# el umbral.
DEBUG_ACTIVO = os.getenv("DEBUG_WAKE_WORD", "").lower() in ("1", "true", "si", "sí")
INTERVALO_LATIDO = 10  # segundos entre "sigo esperando..." (evita el silencio total)


class EscuchadorPalabraClave:
    def __init__(self, palabra_clave="hey_jarvis", umbral=UMBRAL_DETECCION):
        self._modelo = Model(wakeword_models=[palabra_clave], inference_framework="onnx")
        self._nombre_modelo = palabra_clave
        self._umbral = umbral
        self._pyaudio = pyaudio.PyAudio()
        info = self._pyaudio.get_default_input_device_info()
        print(f"[WakeWord] Micrófono: {info['name']} (umbral={umbral}).")

    def esperar(self):
        """Bloquea hasta detectar la palabra clave. Abre su propio stream de
        audio y lo cierra antes de devolver el control, para no competir por
        el micrófono con Oyente (speech_recognition) mientras procesa el
        comando que sigue."""
        self._modelo.reset()
        stream = self._pyaudio.open(
            rate=TASA_MUESTREO, channels=1, format=pyaudio.paInt16,
            input=True, frames_per_buffer=TAMANO_FRAGMENTO,
        )
        try:
            ultimo_latido = time.monotonic()
            mejor_score_desde_latido = 0.0
            while True:
                datos = stream.read(TAMANO_FRAGMENTO, exception_on_overflow=False)
                fragmento = np.frombuffer(datos, dtype=np.int16)
                prediccion = self._modelo.predict(fragmento)
                score = prediccion.get(self._nombre_modelo, 0.0)
                mejor_score_desde_latido = max(mejor_score_desde_latido, score)

                if DEBUG_ACTIVO and score > 0.03:
                    print(f"[WakeWord] score={score:.3f}")

                if score >= self._umbral:
                    return

                ahora = time.monotonic()
                if ahora - ultimo_latido >= INTERVALO_LATIDO:
                    print(f"[WakeWord] Sigo esperando 'Hey Jarvis'... (mejor score reciente: {mejor_score_desde_latido:.3f})")
                    ultimo_latido = ahora
                    mejor_score_desde_latido = 0.0
        finally:
            stream.stop_stream()
            stream.close()

    def cerrar(self):
        self._pyaudio.terminate()
