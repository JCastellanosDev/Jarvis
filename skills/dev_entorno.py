"""Habilidad 1: control del entorno de desarrollo y notas rápidas."""

import os
import subprocess
from datetime import datetime

# --- PERSONALIZA ESTAS RUTAS ---
RUTA_PROYECTO = os.path.expanduser("~/Desktop/jarvis_project")
RUTA_OBSIDIAN_VAULT = os.path.expanduser("~/Documents/Obsidian Vault")
ARCHIVO_IDEAS_UNI = "Ideas Universidad.md"

APPS_IDE = ["IntelliJ IDEA", "PyCharm"]
APPS_VM = ["UTM", "VirtualBox"]


def activar_modo_desarrollo():
    """Abre IDEs, máquinas virtuales y una Terminal en la ruta del proyecto."""
    for app in APPS_IDE:
        try:
            subprocess.Popen(["open", "-a", app])
        except Exception as e:
            print(f"[Jarvis] No pude abrir {app}: {e}")

    for app in APPS_VM:
        try:
            subprocess.Popen(["open", "-a", app])
        except Exception as e:
            print(f"[Jarvis] No pude abrir {app}: {e}")

    try:
        script = f'tell application "Terminal" to do script "cd {RUTA_PROYECTO}"'
        subprocess.run(["osascript", "-e", script], check=False)
    except Exception as e:
        print(f"[Jarvis] No pude abrir la Terminal: {e}")

    return "Modo desarrollo activado. IDEs, máquinas virtuales y terminal listos."


def guardar_idea_universidad(texto_idea):
    """Anexa una idea con marca de tiempo a un .md dentro de la bóveda de Obsidian."""
    if not texto_idea or not texto_idea.strip():
        return "No escuché la idea, inténtalo de nuevo."

    try:
        os.makedirs(RUTA_OBSIDIAN_VAULT, exist_ok=True)
        ruta = os.path.join(RUTA_OBSIDIAN_VAULT, ARCHIVO_IDEAS_UNI)
        marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(f"\n- **[{marca_tiempo}]** {texto_idea.strip()}\n")
        return "Idea guardada en tu bóveda de Obsidian."
    except OSError as e:
        return f"No pude guardar la idea: {e}"
