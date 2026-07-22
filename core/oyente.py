"""Responsable único de capturar audio del micrófono y transcribirlo.

Escucha en ráfagas cortas en vez de una sola escucha larga: mientras sigas
hablando (aunque hagas pausas breves para pensar), va acumulando texto entre
ráfagas sin darte por terminado. Di "cambio" al final para cortar de
inmediato en vez de esperar el margen de silencio completo — como en radio.
"""

import difflib

import speech_recognition as sr

from core.texto import normalizar

PALABRA_CAMBIO = "cambio"
# Bajo tolera transcripciones parecidas ("canvio", "cambeo") que el
# reconocimiento de voz produce seguido con ruido de fondo o al hablar
# rápido — sin esto, decir "cambio" no cortaba si Google lo transcribía mal.
UMBRAL_SIMILITUD_CAMBIO = 0.72
# Techo al umbral de energía dinámico: un ruido fuerte puntual (un portazo,
# el perro) puede disparar el auto-ajuste tan alto que luego tu voz normal
# ya no cruza el umbral y Jarvis deja de "oír" nada.
TECHO_ENERGY_THRESHOLD = 4000


class Oyente:
    # pause_threshold_rafaga: silencio para dar por terminada CADA ráfaga
    # corta (rápido a propósito). timeout_continuacion: cuánto esperar a que
    # retomes la palabra antes de asumir que ya terminaste de hablar — bajado
    # de 2.5s a 1.2s ahora que "cambio" funciona bien: ya no hace falta un
    # margen tan generoso, quien quiera una pausa larga para pensar puede
    # decir "cambio" para cortar de inmediato en vez de esperar este timeout.
    def __init__(self, idioma="es-ES", pause_threshold_rafaga=0.5, non_speaking_duration=0.4,
                 phrase_time_limit=20, timeout_inicial=6, timeout_continuacion=1.2, max_rafagas=6):
        self._idioma = idioma
        self._phrase_time_limit = phrase_time_limit
        self._timeout_inicial = timeout_inicial
        self._timeout_continuacion = timeout_continuacion
        self._max_rafagas = max_rafagas
        self._recognizer = sr.Recognizer()
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold = pause_threshold_rafaga
        self._recognizer.non_speaking_duration = non_speaking_duration

    def escuchar(self):
        segmentos = []

        for i in range(self._max_rafagas):
            es_primera = i == 0
            if es_primera:
                print("\n[Jarvis] Escuchando... (habla ahora, o di 'cambio' para terminar de inmediato)")

            texto_rafaga = self._escuchar_una_rafaga(es_primera)
            if texto_rafaga is None:
                break  # silencio real: se acabó tu turno

            termina_en_cambio, texto_limpio = self._recortar_cambio(texto_rafaga)
            if texto_limpio:
                segmentos.append(texto_limpio)
            if termina_en_cambio:
                break

        texto_final = " ".join(segmentos).strip()
        if texto_final:
            print(f"Tú: {texto_final}")
        return texto_final or None

    def _escuchar_una_rafaga(self, es_primera):
        timeout = self._timeout_inicial if es_primera else self._timeout_continuacion
        try:
            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                if self._recognizer.energy_threshold > TECHO_ENERGY_THRESHOLD:
                    self._recognizer.energy_threshold = TECHO_ENERGY_THRESHOLD
                try:
                    audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=self._phrase_time_limit)
                except sr.WaitTimeoutError:
                    if es_primera:
                        print("[Jarvis] No escuché nada (timeout).")
                    return None

            print("[Jarvis] Procesando voz...")
            try:
                return self._recognizer.recognize_google(audio, language=self._idioma)
            except sr.UnknownValueError:
                print("[Jarvis] Escuché algo pero no logré entenderlo.")
                return None
            except sr.RequestError as e:
                print(f"[Jarvis] Error de red con el reconocimiento de voz: {e}")
                return None

        except OSError as e:
            print(
                f"[Jarvis] No pude abrir el micrófono: {e}. Revisa que este proceso "
                "tenga permiso de Micrófono en Configuración del Sistema → "
                "Privacidad y Seguridad → Micrófono."
            )
            return None

    @staticmethod
    def _recortar_cambio(texto):
        """True si la última palabra de la ráfaga es (o se parece lo
        suficiente a) 'cambio', y el texto sin esa palabra. Tolera fuzzy
        match porque el reconocimiento de voz seguido la transcribe mal
        ("canvio", "cambeo") con ruido de fondo — antes solo aceptaba la
        palabra exacta y "cambio" simplemente no cortaba nada."""
        palabras_norm = normalizar(texto).split()
        if not palabras_norm:
            return False, texto

        ultima_norm = palabras_norm[-1]
        es_cambio = ultima_norm == PALABRA_CAMBIO or (
            len(ultima_norm) >= 4
            and difflib.SequenceMatcher(None, ultima_norm, PALABRA_CAMBIO).ratio() >= UMBRAL_SIMILITUD_CAMBIO
        )
        if not es_cambio:
            return False, texto

        # Recorta del texto ORIGINAL (no el normalizado) para no perder
        # tildes/mayúsculas del resto de la frase.
        palabras_originales = texto.split()
        texto_sin_cambio = " ".join(palabras_originales[:-1]).strip(" ,.")
        return True, texto_sin_cambio
