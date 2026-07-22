"""Control del volumen general de macOS (no de una app en particular, del
sistema completo) vía AppleScript."""

import subprocess

PASO_VOLUMEN = 15
TIMEOUT = 5


def _volumen_actual():
    resultado = subprocess.run(
        ["osascript", "-e", "output volume of (get volume settings)"],
        capture_output=True, text=True, timeout=TIMEOUT,
    )
    return int(resultado.stdout.strip())


def _fijar_volumen(nuevo_volumen):
    nuevo_volumen = max(0, min(100, nuevo_volumen))
    subprocess.run(
        ["osascript", "-e", f"set volume output volume {nuevo_volumen}"],
        capture_output=True, text=True, timeout=TIMEOUT,
    )
    return nuevo_volumen


def subir_volumen(paso=PASO_VOLUMEN):
    try:
        actual = _volumen_actual()
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return "No pude leer el volumen actual."
    nuevo = _fijar_volumen(actual + paso)
    return f"Subí el volumen a {nuevo}."


def bajar_volumen(paso=PASO_VOLUMEN):
    try:
        actual = _volumen_actual()
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return "No pude leer el volumen actual."
    nuevo = _fijar_volumen(actual - paso)
    return f"Bajé el volumen a {nuevo}."


def silenciar():
    _fijar_volumen(0)
    return "Silenciado."
