"""Instala programas por voz usando Homebrew — deliberadamente NO busca en
la web al azar y descarga lo primero que aparezca (un sitio de phishing o un
instalador con malware puede rankear arriba en Google); Homebrew es un
catálogo curado, y de paso ya sabe que tu Mac es Apple Silicon (arm64) y
resuelve la build correcta solo con eso.

Siempre pide confirmación por voz antes de instalar (ver
intents/instalador.py) — decidiste esa red de seguridad en vez de
instalación automática sin preguntar, para no instalar el programa
equivocado si el nombre no fue exacto.
"""

import subprocess
import threading

TIMEOUT_BUSQUEDA = 20
TIMEOUT_INSTALACION = 600  # casks grandes (navegadores, IDEs) pueden tardar


def _brew(*args, timeout):
    return subprocess.run(["brew", *args], capture_output=True, text=True, timeout=timeout)


def _buscar_candidato(nombre):
    """Busca primero entre casks (apps con interfaz gráfica, lo más común
    que se pide por voz); si no hay, cae a fórmulas (herramientas CLI)."""
    resultado = _brew("search", "--cask", nombre, timeout=TIMEOUT_BUSQUEDA)
    candidatos_cask = [l.strip() for l in resultado.stdout.splitlines() if l.strip()]
    if candidatos_cask:
        return candidatos_cask[0], "cask"

    resultado = _brew("search", nombre, timeout=TIMEOUT_BUSQUEDA)
    candidatos_formula = [l.strip() for l in resultado.stdout.splitlines() if l.strip() and not l.startswith("==>")]
    if candidatos_formula:
        return candidatos_formula[0], "formula"

    return None, None


def buscar_en_homebrew(nombre):
    """Devuelve (candidato, tipo) donde tipo es 'cask' o 'formula', o
    (None, None) si no encontró nada o Homebrew falló/tardó demasiado."""
    try:
        return _buscar_candidato(nombre)
    except (subprocess.TimeoutExpired, OSError):
        return None, None


def _instalar(candidato, tipo, hablante):
    args = ["install", "--cask", candidato] if tipo == "cask" else ["install", candidato]
    try:
        resultado = _brew(*args, timeout=TIMEOUT_INSTALACION)
        if resultado.returncode == 0:
            mensaje = f"Listo, {candidato} ya está instalado."
        else:
            mensaje = f"No pude instalar {candidato}: {resultado.stderr.strip()[-300:]}"
    except subprocess.TimeoutExpired:
        mensaje = f"La instalación de {candidato} está tardando demasiado, revísala tú en la Terminal."
    except OSError as e:
        mensaje = f"No pude instalar {candidato}: {e}"
    hablante.hablar(mensaje)


def instalar_en_segundo_plano(candidato, tipo, hablante):
    """No bloquea a Jarvis mientras Homebrew descarga/instala (puede tardar
    varios minutos) — corre en un hilo aparte y avisa por voz al terminar."""
    hilo = threading.Thread(target=_instalar, args=(candidato, tipo, hablante), daemon=True)
    hilo.start()
    return hilo
