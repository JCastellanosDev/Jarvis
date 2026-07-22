"""Reproducción de música en YouTube Music, forzando el navegador Brave.

Requiere: pip install ytmusicapi

Pausar/reanudar controla el <video> de la pestaña activa de Brave vía
JavaScript (más preciso que un toggle de teclado: pausar siempre pausa,
reanudar siempre reanuda, sin adivinar el estado actual). Esto requiere
activar "Permitir JavaScript desde Apple Events" en Brave: menú Ver >
Desarrollador > Permitir JavaScript desde Apple Events — sin eso, Brave
rechaza la orden y Jarvis te lo va a avisar en vez de fallar en silencio.
"""

import subprocess

from skills.navegador import abrir_en_brave

URL_BASE = "https://music.youtube.com"
ID_PLAYLIST_ME_GUSTA = "LM"  # ID fijo de YouTube Music para "Música que te gusta"
TIMEOUT_JS = 10

_cliente_ytmusic = None


def _obtener_cliente_ytmusic():
    global _cliente_ytmusic
    if _cliente_ytmusic is None:
        from ytmusicapi import YTMusic
        _cliente_ytmusic = YTMusic()  # búsqueda anónima, sin login
    return _cliente_ytmusic


def reproducir_musica_que_me_gusta():
    """Requiere que ya hayas iniciado sesión con tu cuenta de Google en Brave;
    si no, YouTube Music mostrará la pantalla de inicio de sesión."""
    url = f"{URL_BASE}/watch?list={ID_PLAYLIST_ME_GUSTA}"
    if not abrir_en_brave(url):
        return "No pude abrir Brave. ¿Está instalado como 'Brave Browser'?"
    return "Reproduciendo tu música que te gusta."


def _buscar_id_cancion(consulta):
    try:
        cliente = _obtener_cliente_ytmusic()
        resultados = cliente.search(consulta, filter="songs", limit=1)
    except ImportError:
        print("[Jarvis] Falta la librería ytmusicapi: pip install ytmusicapi")
        return None
    except Exception as e:
        print(f"[Jarvis] Error buscando en YouTube Music: {e}")
        return None

    if not resultados:
        return None
    return resultados[0].get("videoId")


def reproducir_cancion(consulta):
    video_id = _buscar_id_cancion(consulta)
    if not video_id:
        return f"No encontré {consulta} en YouTube Music."

    url = f"{URL_BASE}/watch?v={video_id}"
    if not abrir_en_brave(url):
        return "No pude abrir Brave. ¿Está instalado como 'Brave Browser'?"
    return f"Reproduciendo {consulta}."


def _ejecutar_js_en_pestana_activa(codigo_js):
    script = f'''
    tell application "Brave Browser"
        if (count of windows) is 0 then return "SIN_VENTANA"
        return execute active tab of front window javascript "{codigo_js}"
    end tell
    '''
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=TIMEOUT_JS)


def _mensaje_error_js(resultado):
    detalle = resultado.stderr.strip()[:200]
    return (
        "No pude controlar la reproducción en Brave. Activa 'Permitir JavaScript "
        "desde Apple Events' en el menú Ver > Desarrollador de Brave. "
        f"Detalle: {detalle}"
    )


def _controlar_video(accion_js, mensaje_ok):
    codigo = f"(function(){{var v=document.querySelector('video'); if(!v) return 'SIN_VIDEO'; v.{accion_js}; return 'OK';}})();"
    try:
        resultado = _ejecutar_js_en_pestana_activa(codigo)
    except (subprocess.TimeoutExpired, OSError) as e:
        return f"No pude controlar la reproducción: {e}"

    if resultado.returncode != 0:
        return _mensaje_error_js(resultado)
    if "SIN_VENTANA" in resultado.stdout:
        return "No tienes Brave abierto."
    if "SIN_VIDEO" in resultado.stdout:
        return "No encontré nada reproduciéndose en la pestaña activa de Brave."
    return mensaje_ok


def pausar_musica():
    return _controlar_video("pause()", "Música pausada.")


def reanudar_musica():
    return _controlar_video("play()", "Reanudando la música.")
