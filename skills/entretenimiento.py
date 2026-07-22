"""Habilidad 5: modo entretenimiento (No Molestar + cerrar apps de trabajo + abrir webs)."""

import subprocess
import webbrowser

APPS_A_CERRAR = ["IntelliJ IDEA", "PyCharm"]

# --- PERSONALIZA tus plataformas ---
SITIOS_ENTRETENIMIENTO = [
    "https://www.crunchyroll.com",
]

# Nombre del Atajo (Shortcuts.app) que activa/desactiva Enfoque "No Molestar".
# En macOS moderno (Sonoma+) la forma soportada de togglear Focus por script
# es crear un Atajo en Shortcuts.app y dispararlo con `shortcuts run <nombre>`;
# alternar Do Not Disturb vía AppleScript puro dejó de ser fiable entre versiones.
ATAJO_ACTIVAR_NM = "Activar No Molestar"
ATAJO_DESACTIVAR_NM = "Desactivar No Molestar"


def activar_no_molestar(activar=True):
    nombre_atajo = ATAJO_ACTIVAR_NM if activar else ATAJO_DESACTIVAR_NM
    try:
        subprocess.run(["shortcuts", "run", nombre_atajo], check=False)
    except FileNotFoundError:
        print("[Jarvis] CLI 'shortcuts' no disponible (requiere macOS 12+).")


def cerrar_apps_trabajo():
    for app in APPS_A_CERRAR:
        script = f'tell application "{app}" to quit'
        subprocess.run(["osascript", "-e", script], check=False)


def modo_otaku():
    activar_no_molestar(True)
    cerrar_apps_trabajo()
    for url in SITIOS_ENTRETENIMIENTO:
        webbrowser.open(url)
    return "Modo otaku activado. No molestar encendido y tus plataformas están abiertas."
