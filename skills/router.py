"""Capa de detección de comandos (Intent Recognizer).

Se ejecuta justo después de transcribir la voz y antes de llamar a Ollama.
Si el texto coincide con un comando de acción, devuelve la respuesta hablada
del skill correspondiente. Si no coincide con nada, devuelve None y el texto
sigue su flujo normal hacia el LLM conversacional.
"""

import re
import unicodedata

from core.integraciones import GitHubGit

from . import dev_entorno, melo_db, habitos, entretenimiento, equipo

# Mismo patrón de inyección que ruta_repo/pedir_texto_por_voz en `ctx`: si
# jarvis.py pone "control_versiones" en ctx_skills, se usa esa instancia
# (permite swapear la implementación real de GitHub, ej. en tests); si no,
# cae en la real. Ver core/integraciones.py.
_CONTROL_VERSIONES_POR_DEFECTO = GitHubGit()


def _normalizar(texto):
    texto = texto.strip().lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return texto


# --- Comandos con texto libre capturado (regex sobre el texto ORIGINAL) ---
# Van primero y son más específicos, para no chocar con los comandos simples.
COMANDOS_CON_CAPTURA = [
    (
        re.compile(r"guarda esta idea( para la universidad)?[:,]?\s*(?P<idea>.+)", re.IGNORECASE),
        lambda m, ctx: dev_entorno.guardar_idea_universidad(m.group("idea")),
    ),
]

# --- Comandos simples por palabra clave (comparación normalizada) ---
COMANDOS_SIMPLES = [
    (
        ("hora de programar", "modo desarrollo"),
        lambda ctx: dev_entorno.activar_modo_desarrollo(),
    ),
    (
        ("sube los cambios a github", "sube los cambios a git", "sube cambios a github", "sube el proyecto a github"),
        lambda ctx: ctx.get("control_versiones", _CONTROL_VERSIONES_POR_DEFECTO)
            .subir_cambios(ctx["ruta_repo"], ctx["pedir_texto_por_voz"]),
    ),
    (
        ("revisa el estado de melo", "estado de melo", "como va melo", "como esta melo"),
        lambda ctx: melo_db.revisar_estado_melo(),
    ),
    (
        ("acabo de tomar un vaso de agua", "tome un vaso de agua", "tomé agua", "beber agua"),
        lambda ctx: habitos.registrar_vaso_agua(),
    ),
    (
        ("modo otaku", "hora de jugar"),
        lambda ctx: entretenimiento.modo_otaku(),
    ),
    (
        ("avisa al equipo que termine mi parte", "avisale al equipo que termine mi parte", "avisa al equipo que termine"),
        lambda ctx: equipo.avisar_equipo(),
    ),
]


def enrutar_comando(texto_original, ctx):
    """
    texto_original: transcripción tal cual vino de SpeechRecognition.
    ctx: dict con dependencias que necesitan los skills, por ejemplo:
        {
            "ruta_repo": "/ruta/al/repo",
            "pedir_texto_por_voz": func(pregunta: str) -> str | None,
        }

    Devuelve el texto de la respuesta hablada si hubo match, o None si el
    texto debe seguir al flujo conversacional normal con Ollama.
    """
    for patron, handler in COMANDOS_CON_CAPTURA:
        m = patron.search(texto_original)
        if m:
            return handler(m, ctx)

    texto_norm = _normalizar(texto_original)
    for frases, handler in COMANDOS_SIMPLES:
        if any(frase in texto_norm for frase in frases):
            return handler(ctx)

    return None
