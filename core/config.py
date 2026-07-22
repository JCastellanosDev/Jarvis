"""Carga y validación de configuración (.env) en un único lugar."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# --- VOCES DISPONIBLES (plan gratuito de ElevenLabs) ---
VOCES_DISPONIBLES = {
    "brian": "nPczCjzI2devNBz1zQrb",
    "charlie": "IKne3meq5aSn9XLyUdCD",
    "callum": "N2lVS1w4EtoT3dr4eOWO",
}
VOZ_POR_DEFECTO = "brian"


@dataclass(frozen=True)
class Settings:
    elevenlabs_api_key: str
    voice_id: str
    modelo_ollama: str
    memoria_file: str = "memoria_jarvis.json"
    # Ventana enviada al LLM en cada turno (el historial completo nunca se
    # recorta). Bajado de 10 a 4: con un modelo tan chico (llama3.2:1b),
    # meterle 10 turnos previos de contexto lo hacía "quedarse pegado" al
    # tema anterior y responder cosas de una petición vieja en vez de la
    # pregunta nueva. Ajustable con MAX_TURNOS_CONTEXTO en tu .env.
    max_turnos_contexto: int = 4
    puerto_remoto: int = 5005
    token_remoto: str = None  # si se define JARVIS_REMOTE_TOKEN, /comando lo exige
    forzar_voz_sistema: bool = False  # FORZAR_VOZ_SISTEMA=true en .env: ni intenta ElevenLabs
    # Desactivado por defecto: en pruebas reales "Hey Jarvis" no se detectaba
    # bien (se quedaba mudo o solo respondía "Dime" sin procesar lo que
    # seguía). Reactívalo con ACTIVAR_WAKE_WORD=true en tu .env cuando
    # quieras retomarlo/afinarlo (ver core/wake_word.py).
    wake_word_activo: bool = False

    @classmethod
    def desde_env(cls):
        # Sin key de ElevenLabs, Jarvis igual arranca: Hablante cae a la voz
        # nativa de macOS automáticamente (ver core/hablante.py).
        api_key = os.getenv("ELEVENLABS_API_KEY") or None
        if not api_key:
            print("[Jarvis] Aviso: sin ELEVENLABS_API_KEY, usaré la voz del sistema (macOS) todo el tiempo.")

        forzar_voz_sistema = os.getenv("FORZAR_VOZ_SISTEMA", "").lower() in ("1", "true", "si", "sí")
        if forzar_voz_sistema:
            print("[Jarvis] FORZAR_VOZ_SISTEMA activo: uso la voz de macOS directo, sin intentar ElevenLabs.")

        wake_word_activo = os.getenv("ACTIVAR_WAKE_WORD", "").lower() in ("1", "true", "si", "sí")
        if wake_word_activo:
            print("[Jarvis] ACTIVAR_WAKE_WORD activo: espero 'Hey Jarvis' antes de procesar nada.")

        return cls(
            elevenlabs_api_key=api_key,
            voice_id=os.getenv("VOICE_ID") or VOCES_DISPONIBLES[VOZ_POR_DEFECTO],
            modelo_ollama=os.getenv("MODELO_OLLAMA", "llama3.2:1b"),
            max_turnos_contexto=int(os.getenv("MAX_TURNOS_CONTEXTO", "4")),
            puerto_remoto=int(os.getenv("JARVIS_REMOTE_PORT", "5005")),
            token_remoto=os.getenv("JARVIS_REMOTE_TOKEN") or None,
            forzar_voz_sistema=forzar_voz_sistema,
            wake_word_activo=wake_word_activo,
        )
