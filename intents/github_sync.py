"""Sincroniza tus repos de GitHub en segundo plano — puede tardar, así que no
bloquea a Jarvis: responde de inmediato y avisa por voz cuando termina.

Depende de la interfaz `ControlVersiones` (core/integraciones.py), no
directo de skills.github_sync — si GitHub cambia su API, o el día de
mañana se agrega otro hosting (GitLab, etc.), este intent no se toca, solo
la implementación inyectada."""

import threading

from core.integraciones import ControlVersiones, GitHubGit
from core.texto import normalizar

from .base import Intent

FRASES_SYNC = {
    "sincroniza mi github", "sincroniza mis repos", "actualiza mi codigo",
    "actualiza mis repos", "sincroniza github", "actualiza github",
}


class GithubSyncIntent(Intent):
    def __init__(self, control_versiones: ControlVersiones = None):
        self._control_versiones = control_versiones or GitHubGit()

    def manejar(self, texto, ctx):
        if normalizar(texto) not in FRASES_SYNC:
            return None

        def _tarea():
            resultado = self._control_versiones.sincronizar()
            with ctx.lock:
                ctx.hablante.hablar(resultado)

        threading.Thread(target=_tarea, daemon=True).start()
        return "Sincronizando tu GitHub en segundo plano, te aviso cuando termine."
