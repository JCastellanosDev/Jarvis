"""Responsable único de convertir texto a voz y reproducirlo (ElevenLabs +
afplay), con soporte para interrumpir la reproducción a mitad de frase.

Si ElevenLabs falla (sin créditos, sin conexión, error de API), cae
automáticamente a la voz nativa de macOS (`say`) en vez de quedarse mudo.
Es una voz de menor calidad, pero Jarvis nunca deja de poder hablar.
"""

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


class Hablante:
    def __init__(self, api_key, voice_id, modelo="eleven_multilingual_v2", voz_sistema="Paulina",
                 forzar_voz_sistema=False):
        self._cliente = ElevenLabs(api_key=api_key) if api_key else None
        self.voice_id = voice_id  # mutable: CambioVozIntent lo actualiza en caliente
        self._modelo = modelo
        self._voz_sistema = voz_sistema  # voz de respaldo de macOS (`say -v '?'` lista las instaladas)
        # Mientras no tengas créditos de ElevenLabs, evita el intento de red
        # que de todos modos va a fallar (más lento) — usa la voz del
        # sistema directo. Cámbialo a False en cuanto recuperes créditos.
        self.forzar_voz_sistema = forzar_voz_sistema
        self._proceso_actual = None
        self.hablando = False  # el panel lo sondea para animar la esfera aunque el audio no venga de él
        self.usando_voz_sistema = False  # el panel/remoto puede mostrarlo como aviso

    def sintetizar(self, texto):
        """Genera el audio y devuelve (bytes, mime_type), o (None, None) si
        todo falla. Intenta ElevenLabs primero; si no hay créditos/conexión,
        cae a la voz nativa de macOS (o si forzar_voz_sistema está activo, ni
        siquiera lo intenta)."""
        if not texto or not texto.strip():
            return None, None

        if not self.forzar_voz_sistema:
            audio_bytes = self._sintetizar_elevenlabs(texto)
            if audio_bytes:
                self.usando_voz_sistema = False
                return audio_bytes, "audio/mpeg"
            print("[Jarvis] ElevenLabs no disponible (¿sin créditos?), uso la voz del sistema.")

        audio_bytes = self._sintetizar_sistema(texto)
        if audio_bytes:
            self.usando_voz_sistema = True
            return audio_bytes, "audio/wav"

        return None, None

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
        self._reproducir_localmente(audio_bytes, mime_type)
        return audio_bytes, mime_type

    def reproducir_en_segundo_plano(self, audio_bytes, mime_type, al_terminar=None):
        """Reproduce localmente en un hilo aparte y regresa de inmediato —
        para que quien llama pueda responder (ej. al celular) sin esperar a
        que termine de sonar en la Mac.

        IMPORTANTE: quien llama sigue siendo responsable de no dejar que
        entre un comando nuevo mientras esto suena (ej. soltando un lock
        compartido solo en `al_terminar`, no antes) — si dos reproducciones
        se superponen vas a escuchar dos voces a la vez."""
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
