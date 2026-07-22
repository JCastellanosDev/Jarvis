"""Captura la pantalla y la describe con un modelo de visión local en Ollama.

Requiere:
- `ollama pull moondream` (o el modelo que definas en MODELO_VISION_OLLAMA).
- Permiso de "Grabación de pantalla" para tu terminal/Python en Configuración
  del Sistema → Privacidad y Seguridad. Esto NO es lo mismo que permisos de
  administrador/root — es un permiso específico y acotado a esa sola cosa.
"""

import os
import subprocess
import tempfile

import ollama

MODELO_VISION = os.getenv("MODELO_VISION_OLLAMA", "moondream")

PREGUNTA_POR_DEFECTO = (
    "Describe brevemente en español, en un par de oraciones, qué se ve en "
    "esta captura de pantalla: qué aplicación está abierta y qué contenido "
    "principal muestra."
)


def _capturar_pantalla():
    descriptor, ruta = tempfile.mkstemp(suffix=".png")
    os.close(descriptor)
    resultado = subprocess.run(["screencapture", "-x", ruta], capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta) or os.path.getsize(ruta) == 0:
        return None
    return ruta


def describir_pantalla(pregunta=PREGUNTA_POR_DEFECTO):
    ruta = _capturar_pantalla()
    if not ruta:
        return (
            "No pude tomar la captura de pantalla. Dale permiso de 'Grabación "
            "de pantalla' a tu terminal en Configuración del Sistema → "
            "Privacidad y Seguridad, y reinicia la terminal."
        )

    try:
        cliente = ollama.Client(timeout=30.0)
        respuesta = cliente.chat(
            model=MODELO_VISION,
            messages=[{"role": "user", "content": pregunta, "images": [ruta]}],
        )
        return respuesta["message"]["content"]
    except Exception as e:
        return f"No pude analizar la pantalla: {e}"
    finally:
        os.remove(ruta)
