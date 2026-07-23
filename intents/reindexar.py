"""Reconstruye el índice de búsqueda semántica (embeddings de tus notas de
Obsidian y tu código sincronizado de GitHub) — hace falta correr esto al
menos una vez para que ObsidianIntent/BuscarCodigoIntent busquen por
significado en vez de por palabra clave (ver core/busqueda_semantica.py).

Puede tardar (una llamada a Ollama por documento/fragmento), así que corre
en segundo plano — mismo patrón que GithubSyncIntent."""

import threading

from core.busqueda_semantica import reindexar_todo
from core.texto import normalizar

from .base import Intent

FRASES_REINDEXAR = {
    "reindexa mis notas", "reindexa el indice semantico", "actualiza el indice semantico",
    "reindexa mis notas y mi codigo", "actualiza la busqueda semantica",
}


class ReindexarIntent(Intent):
    def manejar(self, texto, ctx):
        if normalizar(texto) not in FRASES_REINDEXAR:
            return None

        def _tarea():
            try:
                n_notas, n_codigo = reindexar_todo()
                mensaje = f"Reindexé {n_notas} nota(s) y {n_codigo} fragmento(s) de código."
            except Exception as e:
                mensaje = f"No pude reindexar: {e}"
            with ctx.lock:
                ctx.hablante.hablar(mensaje)

        threading.Thread(target=_tarea, daemon=True).start()
        return "Reindexando tus notas y tu código en segundo plano, te aviso cuando termine."
