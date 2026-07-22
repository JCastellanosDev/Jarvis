"""Habilidad 2: automatización de Git (add, commit por voz, push)."""

import subprocess


def _ejecutar(cmd, ruta_repo):
    return subprocess.run(cmd, cwd=ruta_repo, capture_output=True, text=True)


def subir_cambios_github(ruta_repo, pedir_texto_por_voz):
    """
    ruta_repo: carpeta del repositorio git a operar.
    pedir_texto_por_voz: callable(pregunta: str) -> str|None, para pedir
        el mensaje del commit por voz sin acoplar este módulo a
        speech_recognition / ElevenLabs directamente.
    """
    r_add = _ejecutar(["git", "add", "."], ruta_repo)
    if r_add.returncode != 0:
        return f"Error en git add: {r_add.stderr.strip()}"

    r_status = _ejecutar(["git", "status", "--porcelain"], ruta_repo)
    if not r_status.stdout.strip():
        return "No hay cambios pendientes para subir."

    mensaje = pedir_texto_por_voz("¿Cuál es el mensaje del commit?")
    if not mensaje or not mensaje.strip():
        return "No escuché el mensaje del commit, cancelo la subida."

    r_commit = _ejecutar(["git", "commit", "-m", mensaje.strip()], ruta_repo)
    if r_commit.returncode != 0:
        return f"Error en git commit: {r_commit.stderr.strip()}"

    r_push = _ejecutar(["git", "push"], ruta_repo)
    if r_push.returncode != 0:
        return f"Error en git push: {r_push.stderr.strip()}"

    return f"Cambios subidos a GitHub con el mensaje: {mensaje.strip()}"
