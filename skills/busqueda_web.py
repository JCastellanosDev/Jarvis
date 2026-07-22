"""Búsqueda web ligera (DuckDuckGo) para dar contexto reciente a Ollama.

Requiere: pip install ddgs
(el paquete anterior, duckduckgo-search, fue renombrado a ddgs; se mantiene
como fallback por si el entorno solo tiene instalado el nombre viejo)
"""


def buscar_en_internet(consulta, max_resultados=4):
    """Devuelve un bloque de texto con los resultados principales, o None si
    la búsqueda falla o no hay resultados (el llamador debe manejar ese caso)."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            print("[Jarvis] Falta la librería de búsqueda web: pip install ddgs")
            return None

    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(consulta, region="es-es", max_results=max_resultados))
    except Exception as e:
        print(f"[Jarvis] Error en la búsqueda web: {e}")
        return None

    if not resultados:
        return None

    bloques = []
    for r in resultados:
        titulo = r.get("title", "").strip()
        cuerpo = r.get("body", "").strip()
        if titulo or cuerpo:
            bloques.append(f"- {titulo}: {cuerpo}")

    return "\n".join(bloques) if bloques else None
