"""Sincroniza tus repos de GitHub en segundo plano — puede tardar, así que no
bloquea a Jarvis: responde de inmediato y avisa por voz cuando termina."""

import threading

from core.texto import normalizar
from skills.github_sync import sincronizar_repos

from .base import Intent

FRASES_SYNC = {
    "sincroniza mi github", "sincroniza mis repos", "actualiza mi codigo",
    "actualiza mis repos", "sincroniza github", "actualiza github",
}


class GithubSyncIntent(Intent):
    def manejar(self, texto, ctx):
        if normalizar(texto) not in FRASES_SYNC:
            return None

        def _tarea():
            resultado = sincronizar_repos()
            with ctx.lock:
                ctx.hablante.hablar(resultado)

        threading.Thread(target=_tarea, daemon=True).start()
        return "Sincronizando tu GitHub en segundo plano, te aviso cuando termine."
