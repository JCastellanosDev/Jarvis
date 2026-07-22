"""Descarga videos/audio de YouTube (yt-dlp) o lo que tengas abierto en
Brave, directo a tu carpeta de Descargas.

Requiere ffmpeg para mezclar audio+video en buena calidad y para extraer
mp3 — instálalo una vez con `brew install ffmpeg` si no lo tienes."""

import os
import subprocess
from urllib.parse import urlparse

import requests
import yt_dlp

CARPETA_DESCARGAS = os.path.expanduser("~/Downloads")
DOMINIOS_YOUTUBE = ("youtube.com", "youtu.be", "music.youtube.com")
TIMEOUT_DESCARGA_DIRECTA = 30
TIMEOUT_TAB_ACTIVA = 5


def _es_youtube(url):
    return any(dominio in urlparse(url).netloc for dominio in DOMINIOS_YOUTUBE)


def _descargar_con_ytdlp(consulta_o_url, solo_audio):
    opciones = {
        "outtmpl": os.path.join(CARPETA_DESCARGAS, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "default_search": "ytsearch1",
    }
    if solo_audio:
        opciones["format"] = "bestaudio/best"
        opciones["postprocessors"] = [{
            "key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192",
        }]
    else:
        opciones["format"] = "bestvideo+bestaudio/best"

    with yt_dlp.YoutubeDL(opciones) as ydl:
        info = ydl.extract_info(consulta_o_url, download=True)
        if info and "entries" in info:  # resultado de búsqueda: toma el primero
            info = info["entries"][0]
        return (info or {}).get("title", consulta_o_url)


def descargar_youtube(consulta_o_url, solo_audio=False):
    try:
        titulo = _descargar_con_ytdlp(consulta_o_url, solo_audio)
    except Exception as e:
        return f"No pude descargar eso: {e}"
    tipo = "audio" if solo_audio else "video"
    return f"Descargué el {tipo} de {titulo} en tu carpeta de Descargas."


def _url_pestana_activa_brave():
    try:
        resultado = subprocess.run(
            ["osascript", "-e", 'tell application "Brave Browser" to get URL of active tab of front window'],
            capture_output=True, text=True, timeout=TIMEOUT_TAB_ACTIVA,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if resultado.returncode != 0:
        return None
    return resultado.stdout.strip() or None


def _descargar_url_directa(url):
    try:
        respuesta = requests.get(url, timeout=TIMEOUT_DESCARGA_DIRECTA)
        respuesta.raise_for_status()
    except requests.RequestException as e:
        return f"No pude descargar el archivo: {e}"

    nombre = os.path.basename(urlparse(url).path) or "descarga"
    os.makedirs(CARPETA_DESCARGAS, exist_ok=True)
    ruta = os.path.join(CARPETA_DESCARGAS, nombre)
    with open(ruta, "wb") as f:
        f.write(respuesta.content)
    return f"Descargué {nombre} en tu carpeta de Descargas."


def descargar_lo_abierto_en_navegador():
    """Toma la URL de la pestaña activa de Brave: si es de YouTube la baja
    con yt-dlp, si no, la descarga tal cual (sirve para PDFs, imágenes, etc.
    directamente ligados, no para páginas web genéricas)."""
    url = _url_pestana_activa_brave()
    if not url:
        return "No pude ver qué tienes abierto en Brave. ¿Está abierto?"
    if _es_youtube(url):
        return descargar_youtube(url, solo_audio=False)
    return _descargar_url_directa(url)
