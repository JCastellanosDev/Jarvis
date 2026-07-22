"""Construye un grafo (nodos + conexiones) a partir de los wikilinks
`[[Nota]]` de tus bóvedas de Obsidian, para dibujarlo en el navegador —
mismo dato que alimenta la Vista Gráfica nativa de Obsidian, reconstruido
aquí a mano porque Obsidian no expone esto por ningún API/archivo propio."""

import os
import re
import subprocess
import sys

from skills.obsidian import EXTENSIONES_VALIDAS, RUTAS_VAULTS

PATRON_WIKILINK = re.compile(r"\[\[([^\]|#]+)")

_RUTA_CAMARA_NATIVA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "panel", "camara_nativa.py")
_proceso_camara_nativa = None  # evita abrir dos ventanas de cámara si ya está corriendo


def _listar_archivos_md():
    for vault in RUTAS_VAULTS:
        if not os.path.isdir(vault):
            continue
        for raiz, carpetas, archivos in os.walk(vault):
            carpetas[:] = [c for c in carpetas if not c.startswith(".")]
            for nombre in archivos:
                if nombre.endswith(EXTENSIONES_VALIDAS):
                    yield os.path.join(raiz, nombre)


def construir_grafo():
    """Devuelve {"nodes": [{"id", "existe"}], "edges": [{"origen", "destino"}]}.

    "existe" distingue una nota real de un link roto a una nota que no
    existe (Obsidian los muestra distinto en su grafo real)."""
    ids_reales = set()
    enlaces = []

    rutas = list(_listar_archivos_md())
    for ruta in rutas:
        nombre = os.path.splitext(os.path.basename(ruta))[0]
        ids_reales.add(nombre)

    for ruta in rutas:
        origen = os.path.splitext(os.path.basename(ruta))[0]
        try:
            with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                contenido = f.read()
        except OSError:
            continue

        for m in PATRON_WIKILINK.finditer(contenido):
            destino = m.group(1).strip()
            if destino and destino != origen:
                enlaces.append((origen, destino))

    ids_referenciados = {destino for _, destino in enlaces}
    todos_los_ids = ids_reales | ids_referenciados

    nodos = [{"id": nid, "existe": nid in ids_reales} for nid in sorted(todos_los_ids)]
    # Sin duplicados (dos notas pueden linkearse entre sí más de una vez).
    aristas_unicas = sorted(set(enlaces))
    aristas = [{"origen": o, "destino": d} for o, d in aristas_unicas]

    return {"nodes": nodos, "edges": aristas}


def abrir_camara_nativa(puerto):
    """Lanza panel/camara_nativa.py en su propia ventana, aparte de Brave —
    para cuando el navegador no tiene permiso de cámara. Idempotente: si ya
    hay una instancia corriendo, no abre una segunda.

    Devuelve True si la dejó corriendo (ya sea recién lanzada o de antes)."""
    global _proceso_camara_nativa
    if _proceso_camara_nativa is not None and _proceso_camara_nativa.poll() is None:
        return True
    try:
        _proceso_camara_nativa = subprocess.Popen([sys.executable, _RUTA_CAMARA_NATIVA, str(puerto)])
        return True
    except OSError:
        return False
