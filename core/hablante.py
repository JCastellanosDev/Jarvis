"""Responsable único de convertir texto a voz y reproducirlo (ElevenLabs +
afplay), con soporte para interrumpir la reproducción a mitad de frase.

Cadena de respaldo, de mejor a peor calidad, para que Jarvis nunca se quede
mudo: ElevenLabs (nube, requiere créditos) -> Kokoro (local, gratis, buena
calidad) -> voz nativa de macOS `say` (local, última red de seguridad si
Kokoro no tiene los archivos del modelo descargados).
"""

import io
import os
import select
import subprocess
import sys
import tempfile
import threading
import uuid

from elevenlabs.client import ElevenLabs

try:
    import termios
    import tty
    _TERMINAL_INTERACTIVO = True
except ImportError:  # plataformas sin terminal POSIX (no aplica en macOS)
    _TERMINAL_INTERACTIVO = False

EXTENSION_POR_MIME = {"audio/mpeg": ".mp3", "audio/wav": ".wav"}

RUTA_MODELO_KOKORO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kokoro_modelo")
RUTA_ONNX_KOKORO = os.path.join(RUTA_MODELO_KOKORO, "kokoro-v1.0.onnx")
RUTA_VOCES_KOKORO = os.path.join(RUTA_MODELO_KOKORO, "voices-v1.0.bin")
# es-419 = español "neutro"/latinoamericano en espeak-ng (vs "es" = España),
# lo que más se acerca a "latinoamericano" que ofrece el phonemizer de Kokoro
# — la voz en sí (el timbre) no tiene acento regional propio, es el mismo
# modelo entrenado con datos multilingües genéricos.
IDIOMA_KOKORO = "es-419"
VOZ_KOKORO_POR_DEFECTO = "em_alex"  # ef_dora (mujer), em_alex/em_santa (hombre)


class Hablante:
    def __init__(self, api_key, voice_id, modelo="eleven_multilingual_v2", voz_sistema="Paulina",
                 forzar_voz_sistema=False, voz_kokoro=None):
        self._cliente = ElevenLabs(api_key=api_key) if api_key else None
        self.voice_id = voice_id  # mutable: CambioVozIntent lo actualiza en caliente
        self._modelo = modelo
        self._voz_sistema = voz_sistema  # voz de respaldo de macOS (`say -v '?'` lista las instaladas)
        self._voz_kokoro = voz_kokoro or os.getenv("KOKORO_VOZ", VOZ_KOKORO_POR_DEFECTO)
        self._kokoro = None  # instancia perezosa: cargar el modelo tarda, solo la primera vez
        self._kokoro_no_disponible = False  # evita reintentar cargar en cada frase si ya falló una vez
        # Mientras no tengas créditos de ElevenLabs, evita el intento de red
        # que de todos modos va a fallar (más lento) — usa Kokoro (voz local)
        # directo. Cámbialo a False en cuanto recuperes créditos.
        self.forzar_voz_sistema = forzar_voz_sistema
        self._proceso_actual = None
        self.hablando = False  # el panel lo sondea para animar la esfera aunque el audio no venga de él
        self.usando_voz_sistema = False  # True si NO es ElevenLabs (Kokoro o macOS); el panel/remoto lo usa como aviso
        self.motor_voz = "elevenlabs"  # "elevenlabs" | "kokoro" | "sistema" — cuál sonó de verdad
        # Lo último que Jarvis dijo por CUALQUIER canal (voz local o remoto):
        # el bucle principal lo usa para descartar que el micrófono se
        # escuche a sí mismo y lo trate como un comando nuevo (ver core/eco.py).
        self.ultimo_texto_hablado = None

    def sintetizar(self, texto):
        """Genera el audio y devuelve (bytes, mime_type), o (None, None) si
        todo falla. Orden: ElevenLabs (si hay créditos y no está forzada la
        voz local) -> Kokoro (voz local de buena calidad) -> `say` de macOS
        como último recurso si Kokoro no tiene los archivos del modelo."""
        if not texto or not texto.strip():
            return None, None

        if not self.forzar_voz_sistema:
            audio_bytes = self._sintetizar_elevenlabs(texto)
            if audio_bytes:
                self.usando_voz_sistema = False
                self.motor_voz = "elevenlabs"
                return audio_bytes, "audio/mpeg"
            print("[Jarvis] ElevenLabs no disponible (¿sin créditos?), uso Kokoro (voz local).")

        audio_bytes = self._sintetizar_kokoro(texto)
        if audio_bytes:
            self.usando_voz_sistema = True
            self.motor_voz = "kokoro"
            return audio_bytes, "audio/wav"

        print("[Jarvis] Kokoro no disponible, uso la voz nativa de macOS como último recurso.")
        audio_bytes = self._sintetizar_sistema(texto)
        if audio_bytes:
            self.usando_voz_sistema = True
            self.motor_voz = "sistema"
            return audio_bytes, "audio/wav"

        return None, None

    def _obtener_kokoro(self):
        if self._kokoro is not None or self._kokoro_no_disponible:
            return self._kokoro
        try:
            from kokoro_onnx import Kokoro
            if not os.path.exists(RUTA_ONNX_KOKORO) or not os.path.exists(RUTA_VOCES_KOKORO):
                raise FileNotFoundError(
                    f"Faltan los archivos del modelo en {RUTA_MODELO_KOKORO} "
                    "(kokoro-v1.0.onnx y voices-v1.0.bin)."
                )
            self._kokoro = Kokoro(RUTA_ONNX_KOKORO, RUTA_VOCES_KOKORO)
        except Exception as e:
            print(f"[Jarvis] No pude cargar Kokoro: {e}")
            self._kokoro_no_disponible = True
        return self._kokoro

    def _sintetizar_kokoro(self, texto):
        kokoro = self._obtener_kokoro()
        if not kokoro:
            return None
        try:
            import soundfile as sf
            muestras, tasa_muestreo = kokoro.create(
                texto, voice=self._voz_kokoro, speed=1.0, lang=IDIOMA_KOKORO
            )
            buffer = io.BytesIO()
            sf.write(buffer, muestras, tasa_muestreo, format="WAV")
            return buffer.getvalue()
        except Exception as e:
            print(f"[Jarvis] Error en Kokoro: {e}")
            return None

    def _sintetizar_elevenlabs(self, texto):
        if not self._cliente:
            return None
        try:
            audio_stream = self._cliente.text_to_speech.convert(
                voice_id=self.voice_id,
                optimize_streaming_latency="2",
                output_format="mp3_44100_128",
                text=texto,
                model_id=self._modelo,
            )
            return b"".join(audio_stream)
        except Exception as e:
            print(f"[Jarvis] Error en ElevenLabs: {e}")
            return None

    def _sintetizar_sistema(self, texto):
        descriptor, ruta = tempfile.mkstemp(suffix=".wav")
        os.close(descriptor)
        try:
            resultado = subprocess.run(
                ["say", "-v", self._voz_sistema, "-o", ruta,
                 "--file-format=WAVE", "--data-format=LEI16@22050", texto],
                capture_output=True, text=True, timeout=30,
            )
            if resultado.returncode != 0 or not os.path.exists(ruta) or os.path.getsize(ruta) == 0:
                print(f"[Jarvis] Error en la voz del sistema: {resultado.stderr.strip()}")
                return None
            with open(ruta, "rb") as f:
                return f.read()
        except Exception as e:
            print(f"[Jarvis] Error en la voz del sistema: {e}")
            return None
        finally:
            if os.path.exists(ruta):
                os.remove(ruta)

    def hablar(self, texto):
        """Sintetiza y reproduce por los parlantes de la Mac."""
        self.hablar_y_obtener_audio(texto)

    def hablar_y_obtener_audio(self, texto):
        """Igual que hablar(), pero además devuelve (bytes, mime_type),
        para quien los necesite (ej. reproducirlos en el celular)."""
        audio_bytes, mime_type = self.sintetizar(texto)
        if not audio_bytes:
            return None, None
        self.ultimo_texto_hablado = texto
        self._reproducir_localmente(audio_bytes, mime_type)
        return audio_bytes, mime_type

    def reproducir_en_segundo_plano(self, audio_bytes, mime_type, texto=None, al_terminar=None):
        """Reproduce localmente en un hilo aparte y regresa de inmediato —
        para que quien llama pueda responder (ej. al celular) sin esperar a
        que termine de sonar en la Mac.

        IMPORTANTE: quien llama sigue siendo responsable de no dejar que
        entre un comando nuevo mientras esto suena (ej. soltando un lock
        compartido solo en `al_terminar`, no antes) — si dos reproducciones
        se superponen vas a escuchar dos voces a la vez."""
        if texto:
            self.ultimo_texto_hablado = texto

        def _tarea():
            try:
                self._reproducir_localmente(audio_bytes, mime_type)
            finally:
                if al_terminar:
                    al_terminar()
        threading.Thread(target=_tarea, daemon=True).start()

    def detener(self):
        """Corta en seco la reproducción local en curso, si hay una."""
        if self._proceso_actual and self._proceso_actual.poll() is None:
            self._proceso_actual.terminate()

    def _reproducir_localmente(self, audio_bytes, mime_type="audio/mpeg"):
        extension = EXTENSION_POR_MIME.get(mime_type, ".mp3")
        # Nombre único por reproducción: con reproducir_en_segundo_plano()
        # puede haber más de una reproducción en curso, y un nombre fijo
        # causaría que una borre el archivo de la otra.
        archivo_audio = f"respuesta_jarvis_{uuid.uuid4().hex}{extension}"
        self.hablando = True
        try:
            with open(archivo_audio, "wb") as f:
                f.write(audio_bytes)

            print("\n[Jarvis hablando... (ESPACIO + Enter para interrumpir)]")
            self._proceso_actual = subprocess.Popen(["afplay", archivo_audio])
            self._esperar_con_interrupcion(self._proceso_actual)

        finally:
            if os.path.exists(archivo_audio):
                os.remove(archivo_audio)
            self._proceso_actual = None
            self.hablando = False

    @staticmethod
    def _esperar_con_interrupcion(proceso):
        """Espera a que termine `proceso` (afplay), pero lo corta antes si el
        usuario presiona espacio en la terminal. Sin mic de por medio: no hay
        riesgo de que Jarvis se interrumpa solo por escucharse a sí mismo."""
        if not _TERMINAL_INTERACTIVO or not sys.stdin.isatty():
            proceso.wait()
            return

        descriptor = sys.stdin.fileno()
        configuracion_previa = termios.tcgetattr(descriptor)
        try:
            tty.setcbreak(descriptor)
            while proceso.poll() is None:
                listos, _, _ = select.select([sys.stdin], [], [], 0.1)
                if listos and sys.stdin.read(1) == " ":
                    proceso.terminate()
                    print("\n[Jarvis] Interrumpido.")
                    break
        finally:
            termios.tcsetattr(descriptor, termios.TCSADRAIN, configuracion_previa)
            proceso.wait()
