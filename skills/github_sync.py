"""Sincroniza tus repos públicos de GitHub localmente y los deja disponibles
para que Jarvis busque en tu código real como referencia de estilo — mismo
patrón que Obsidian, pero sobre tu código en vez de tus notas.

No necesita token: tus 12 repos son públicos, se clonan por HTTPS sin login.
"""

import json
import os
import ssl
import subprocess
import urllib.request

import certifi

# El Python de python.org en macOS no siempre trae enlazados los certificados
# raíz del sistema (falta correr "Install Certificates.command"). En vez de
# depender de eso, se usa el bundle de certifi explícitamente.
_CONTEXTO_SSL = ssl.create_default_context(cafile=certifi.where())

USUARIO_GITHUB = "JCastellanosDev"
CARPETA_REPOS = os.path.expanduser("~/jarvis_codigo_referencia")

EXTENSIONES_CODIGO = (
    ".py", ".java", ".js", ".ts", ".html", ".css", ".kt", ".swift",
    ".cpp", ".c", ".cs", ".php",
)
CARPETAS_IGNORADAS = {
    ".git", "node_modules", "build", "target", "dist", "__pycache__",
    ".idea", ".gradle", "bin", "obj", "venv",
}
PALABRAS_VACIAS_CODIGO = {
    "que", "de", "la", "el", "en", "un", "una", "para", "con", "como",
    "por", "los", "las", "mi", "mis",
}


def _listar_repos_publicos():
    url = f"https://api.github.com/users/{USUARIO_GITHUB}/repos?per_page=100"
    try:
        peticion = urllib.request.Request(url, headers={"User-Agent": "jarvis-local"})
        with urllib.request.urlopen(peticion, timeout=10, context=_CONTEXTO_SSL) as resp:
            datos = json.load(resp)
        return [(r["name"], r["clone_url"]) for r in datos if not r.get("fork")]
    except Exception as e:
        print(f"[Jarvis] No pude listar tus repos de GitHub: {e}")
        return []


def sincronizar_repos():
    """Clona los repos que no tengas localmente y actualiza (git pull) los
    que ya existan. Puede tardar según cuántos repos tengas — pensado para
    correr en segundo plano, no bloquea el resto de Jarvis mientras corre."""
    repos = _listar_repos_publicos()
    if not repos:
        return "No pude conectar con GitHub para sincronizar tus repos."

    os.makedirs(CARPETA_REPOS, exist_ok=True)
    actualizados, nuevos, fallidos = 0, 0, 0

    for nombre, url_clone in repos:
        ruta_local = os.path.join(CARPETA_REPOS, nombre)
        if os.path.isdir(os.path.join(ruta_local, ".git")):
            resultado = subprocess.run(
                ["git", "pull", "--quiet"], cwd=ruta_local, capture_output=True, text=True, timeout=60,
            )
            if resultado.returncode == 0:
                actualizados += 1
            else:
                fallidos += 1
        else:
            resultado = subprocess.run(
                ["git", "clone", "--quiet", url_clone, ruta_local], capture_output=True, text=True, timeout=120,
            )
            if resultado.returncode == 0:
                nuevos += 1
            else:
                fallidos += 1

    partes = []
    if nuevos:
        partes.append(f"{nuevos} nuevo(s)")
    if actualizados:
        partes.append(f"{actualizados} actualizado(s)")
    if fallidos:
        partes.append(f"{fallidos} con error")

    if not partes:
        return "No había nada que sincronizar."
    return "Sincronicé tu GitHub: " + ", ".join(partes) + "."


def _listar_archivos_codigo():
    if not os.path.isdir(CARPETA_REPOS):
        return
    for raiz, carpetas, archivos in os.walk(CARPETA_REPOS):
        carpetas[:] = [c for c in carpetas if c not in CARPETAS_IGNORADAS and not c.startswith(".")]
        for nombre in archivos:
            if nombre.endswith(EXTENSIONES_CODIGO):
                yield os.path.join(raiz, nombre)


def buscar_en_mi_codigo(consulta, max_archivos=3, max_caracteres=1200):
    """Búsqueda por palabras clave (no semántica) sobre tu código ya
    sincronizado. None si no hay nada sincronizado aún o no encontró nada."""
    palabras = [p for p in consulta.lower().split() if len(p) > 2 and p not in PALABRAS_VACIAS_CODIGO]
    if not palabras:
        return None

    coincidencias = []
    for ruta in _listar_archivos_codigo():
        try:
            with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                contenido = f.read()
        except OSError:
            continue

        contenido_lower = contenido.lower()
        if all(palabra in contenido_lower for palabra in palabras):
            nombre_relativo = os.path.relpath(ruta, CARPETA_REPOS)
            fragmento = contenido.strip()[:max_caracteres]
            coincidencias.append(f"### {nombre_relativo}\n```\n{fragmento}\n```")

        if len(coincidencias) >= max_archivos:
            break

    return "\n\n".join(coincidencias) if coincidencias else None
