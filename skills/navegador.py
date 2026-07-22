"""Utilidad compartida para abrir URLs forzando el navegador Brave en macOS,
sin importar cuál sea el navegador predeterminado del sistema."""

import subprocess

NOMBRE_APP_BRAVE = "Brave Browser"  # ajusta si tu Brave se llama distinto


def abrir_en_brave(url):
    resultado = subprocess.run(["open", "-a", NOMBRE_APP_BRAVE, url], capture_output=True, text=True)
    return resultado.returncode == 0
