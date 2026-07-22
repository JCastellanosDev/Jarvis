"""Resolución de nombres de apps instaladas vía Spotlight (mdfind), para que
"abre X" funcione con CUALQUIER app de tu Mac por nombre aproximado, no solo
las que están en un diccionario de alias a mano."""

import subprocess

_cache_apps_instaladas = None


def _listar_apps_instaladas():
    global _cache_apps_instaladas
    if _cache_apps_instaladas is not None:
        return _cache_apps_instaladas

    try:
        resultado = subprocess.run(
            ["mdfind", "kMDItemContentType == 'com.apple.application-bundle'"],
            capture_output=True, text=True, timeout=5,
        )
        _cache_apps_instaladas = [
            ruta.rsplit("/", 1)[-1][:-4]  # nombre del .app sin la extensión
            for ruta in resultado.stdout.splitlines()
            if ruta.endswith(".app")
        ]
    except Exception:
        _cache_apps_instaladas = []

    return _cache_apps_instaladas


def resolver_nombre_app(nombre_pedido):
    """Busca entre las apps REALMENTE instaladas cuál coincide mejor con lo
    que se pidió. None si no encuentra ninguna coincidencia razonable."""
    pedido = nombre_pedido.lower()
    candidatos = [app for app in _listar_apps_instaladas() if pedido in app.lower()]
    if not candidatos:
        return None
    # La coincidencia más corta suele ser la más "exacta" (ej. "chrome" ->
    # "Google Chrome" antes que "Google Chrome Canary").
    candidatos.sort(key=len)
    return candidatos[0]


def cerrar_app(nombre_app):
    """Cierra una app por AppleScript ('quit' es más limpio que matar el
    proceso — le da chance de guardar cambios pendientes, etc.)."""
    resultado = subprocess.run(
        ["osascript", "-e", f'tell application "{nombre_app}" to quit'],
        capture_output=True, text=True, timeout=10,
    )
    return resultado.returncode == 0
