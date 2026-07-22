"""Lanzador/cerrador dinámico de aplicaciones de macOS: "abre <app>" /
"cierra <app>", usando `open -a` para abrir y AppleScript `quit` para cerrar.

Es el intent "genérico" para apps: va después de MultimediaIntent y
AccionesSkillsIntent en el router para que comandos más específicos (música,
modo desarrollo, etc.) se resuelvan primero.
"""

import re
import subprocess

from core.texto import normalizar
from skills.aplicaciones import cerrar_app, resolver_nombre_app

from .base import Intent

PATRON_ABRIR = re.compile(r"^(jarvis[, ]+)?abr[ie]r?\s+(?P<app>.+)$")
PATRON_CERRAR = re.compile(r"^(jarvis[, ]+)?cierra\s+(la\s+)?((aplicacion|app)\s+de\s+|(aplicacion|app)\s+)?(?P<app>.+)$")

# El STT devuelve el nombre "hablado" de la app; aquí se traduce al nombre
# real del bundle en macOS. Agrega aquí tus apps más usadas.
ALIAS_APPS = {
    "vs code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "chrome": "Google Chrome",
    "brave": "Brave Browser",
    "whatsapp": "WhatsApp",
    "spotify": "Spotify",
    "terminal": "Terminal",
    "finder": "Finder",
    "notas": "Obsidian",
    "calendario": "Calendar",
    "correo": "Mail",
    "intelli": "IntelliJ IDEA",
    "pycharm": "PyCharm",
}


def _resolver(nombre_pedido):
    return ALIAS_APPS.get(nombre_pedido) or resolver_nombre_app(nombre_pedido) or nombre_pedido.title()


class AplicacionesIntent(Intent):
    def manejar(self, texto, ctx):
        t = normalizar(texto)

        m_cerrar = PATRON_CERRAR.match(t)
        if m_cerrar:
            nombre_app = _resolver(m_cerrar.group("app").strip())
            if cerrar_app(nombre_app):
                return f"Cerrando {nombre_app}."
            return f"No pude cerrar {nombre_app}. ¿Está abierta?"

        m_abrir = PATRON_ABRIR.match(t)
        if m_abrir:
            nombre_app = _resolver(m_abrir.group("app").strip())
            resultado = subprocess.run(["open", "-a", nombre_app], capture_output=True, text=True)
            if resultado.returncode != 0:
                return f"No encontré una aplicación llamada {nombre_app} en tu Mac."
            return f"Abriendo {nombre_app}."

        return None
