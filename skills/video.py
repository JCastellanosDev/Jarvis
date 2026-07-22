"""Abre servicios de streaming de video, forzando el navegador Brave."""

from urllib.parse import quote_plus

from skills.navegador import abrir_en_brave

URL_PRIME_VIDEO = "https://www.primevideo.com"
URL_PARAMOUNT = "https://www.paramountplus.com"

# Formato de búsqueda de primevideo.com; no lo pude verificar en vivo (no
# tengo forma de probarlo con sesión real), pruébalo y avísame si no cae en
# los resultados correctos para ajustar el parámetro.
URL_BUSQUEDA_PRIME = "https://www.primevideo.com/search/ref=atv_nb_sr?phrase={consulta}&ie=UTF8"

MENSAJE_ERROR_BRAVE = "No pude abrir Brave. ¿Está instalado como 'Brave Browser'?"


def _abrir(url, mensaje_ok):
    if not abrir_en_brave(url):
        return MENSAJE_ERROR_BRAVE
    return mensaje_ok


def abrir_prime_video():
    """Requiere que ya hayas iniciado sesión con tu cuenta de Amazon en
    Brave; si no, Prime Video mostrará la pantalla de inicio de sesión."""
    return _abrir(URL_PRIME_VIDEO, "Abriendo Prime Video.")


def abrir_paramount():
    """Requiere que ya hayas iniciado sesión con tu cuenta en Brave; si no,
    Paramount+ mostrará la pantalla de inicio de sesión."""
    return _abrir(URL_PARAMOUNT, "Abriendo Paramount+.")


def buscar_pelicula_en_prime(titulo):
    url = URL_BUSQUEDA_PRIME.format(consulta=quote_plus(titulo))
    return _abrir(url, f"Buscando {titulo} en Prime Video.")


def _buscar_resultados_raw(consulta, max_resultados=5):
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            print("[Jarvis] Falta la librería de búsqueda web: pip install ddgs")
            return []

    try:
        with DDGS() as ddgs:
            return list(ddgs.text(consulta, region="es-es", max_results=max_resultados))
    except Exception as e:
        print(f"[Jarvis] Error en la búsqueda web: {e}")
        return []


def buscar_donde_ver(titulo):
    """Busca en cuál de tus dos apps de streaming está la película antes de
    abrir nada; si no aparece en ninguna, abre el primer resultado general
    que encuentre (una página cualquiera donde poder verla), como pediste."""
    resultados = _buscar_resultados_raw(f"{titulo} ver online streaming")
    if not resultados:
        return f"No encontré dónde ver {titulo}."

    for r in resultados:
        href = (r.get("href") or "").lower()
        if "primevideo.com" in href:
            return _abrir(URL_PRIME_VIDEO, f"Encontré {titulo} en Prime Video, abriéndolo.")
        if "paramountplus.com" in href:
            return _abrir(URL_PARAMOUNT, f"Encontré {titulo} en Paramount+, abriéndolo.")

    # No apareció en ninguna de tus dos apps: abre la primera página que
    # haya encontrado, tal cual pediste como respaldo.
    primer_resultado = resultados[0]
    href = primer_resultado.get("href")
    if not href:
        return f"No encontré dónde ver {titulo}."

    # Los títulos de resultados de búsqueda a veces vienen concatenados/sucios
    # (varios nombres de sitio pegados); si no es corto y limpio, mejor no
    # leerlo en voz alta.
    titulo_pagina = primer_resultado.get("title", "").strip()
    if not titulo_pagina or len(titulo_pagina) > 60:
        titulo_pagina = "una página"

    return _abrir(
        href,
        f"No la vi en Prime ni en Paramount, te abro {titulo_pagina} sobre {titulo}.",
    )
