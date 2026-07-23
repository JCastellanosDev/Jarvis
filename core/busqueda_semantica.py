"""Búsqueda semántica (embeddings) sobre tus notas de Obsidian y tu código
sincronizado de GitHub — mejora el match por palabra clave que ya usaban
skills/obsidian.py y skills/github_sync.py: "qué anoté sobre mi carro"
ahora puede encontrar una nota titulada "Honda Civic - mantenimiento"
aunque no comparta ni una palabra literal con la pregunta.

Nada de ChromaDB/FAISS: con un puñado de notas y repos, un escaneo lineal
con similitud coseno (numpy, ya es dependencia del proyecto) es
instantáneo — no hace falta indexación aproximada. Los embeddings los
genera Ollama (`ollama pull nomic-embed-text`, ~274MB, una sola vez), así
que tampoco se agrega ningún servicio nuevo.

Si el índice no existe todavía, o Ollama no responde, las funciones
`buscar_semantico_en_*` caen automáticamente al match por palabra clave
de siempre — nunca dejan a Jarvis sin poder buscar."""

import json
import os

import numpy as np
import ollama

MODELO_EMBEDDINGS = "nomic-embed-text"
RUTA_INDICE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "indice_semantico")

TOP_K_NOTAS = 5
TOP_K_CODIGO = 3
MAX_CARACTERES_CHUNK = 1500
UMBRAL_SIMILITUD = 0.35  # coseno por debajo de esto: se descarta como "no relevante"


def _ruta_vectores(nombre):
    return os.path.join(RUTA_INDICE, f"{nombre}.npy")


def _ruta_metadatos(nombre):
    return os.path.join(RUTA_INDICE, f"{nombre}.json")


def _embed(textos):
    """textos: list[str]. Devuelve np.ndarray (n, dim) float32."""
    respuesta = ollama.Client().embed(model=MODELO_EMBEDDINGS, input=textos)
    return np.array(respuesta.embeddings, dtype=np.float32)


def _normalizar_filas(vectores):
    normas = np.linalg.norm(vectores, axis=1, keepdims=True)
    normas[normas == 0] = 1
    return vectores / normas


def construir_indice(nombre, documentos):
    """documentos: [{"id": str, "texto": str, ...metadata}]. Genera
    embeddings para todos y los persiste en disco. Devuelve cuántos
    documentos quedaron indexados (0 si `documentos` viene vacío — no
    hay nada que preguntarle a Ollama)."""
    if not documentos:
        return 0

    textos = [d["texto"] for d in documentos]
    vectores = _normalizar_filas(_embed(textos))

    os.makedirs(RUTA_INDICE, exist_ok=True)
    np.save(_ruta_vectores(nombre), vectores)
    with open(_ruta_metadatos(nombre), "w", encoding="utf-8") as f:
        json.dump(documentos, f, ensure_ascii=False)

    return len(documentos)


def _cargar_indice(nombre):
    ruta_vec, ruta_meta = _ruta_vectores(nombre), _ruta_metadatos(nombre)
    if not os.path.exists(ruta_vec) or not os.path.exists(ruta_meta):
        return None, None
    vectores = np.load(ruta_vec)
    with open(ruta_meta, "r", encoding="utf-8") as f:
        metadatos = json.load(f)
    return vectores, metadatos


def buscar(nombre, consulta, top_k=5, umbral=UMBRAL_SIMILITUD):
    """Devuelve una lista de documentos (metadata + "texto" + "score"),
    ordenada por similitud descendente y filtrada por `umbral`. None si no
    hay índice construido todavía o si Ollama no respondió (para que quien
    llama sepa que debe caer a un respaldo, en vez de asumir "sin resultados")."""
    vectores, metadatos = _cargar_indice(nombre)
    if vectores is None:
        return None

    try:
        consulta_vec = _embed([consulta])[0]
    except Exception as e:
        print(f"[Jarvis] Error generando el embedding de la consulta: {e}")
        return None

    norma = np.linalg.norm(consulta_vec)
    if norma == 0:
        return []
    consulta_vec = consulta_vec / norma

    similitudes = vectores @ consulta_vec
    mejores = np.argsort(-similitudes)[:top_k]

    return [
        {**metadatos[i], "score": float(similitudes[i])}
        for i in mejores if similitudes[i] >= umbral
    ]


def indexar_notas():
    """Reindexa todas las notas de tus bóvedas de Obsidian. Devuelve
    cuántas quedaron indexadas."""
    from skills.obsidian import _listar_archivos_md

    documentos = []
    for ruta in _listar_archivos_md():
        try:
            with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                contenido = f.read()
        except OSError:
            continue
        if not contenido.strip():
            continue
        nombre = os.path.splitext(os.path.basename(ruta))[0]
        documentos.append({
            "id": nombre, "titulo": nombre, "texto": contenido[:MAX_CARACTERES_CHUNK],
        })

    return construir_indice("notas", documentos)


def indexar_codigo():
    """Reindexa el código ya sincronizado de GitHub (Python, Java, etc. —
    ver skills/github_sync.py). Los archivos largos se parten en
    fragmentos de MAX_CARACTERES_CHUNK: si se indexara el archivo entero
    como un solo vector, un archivo de 2000 líneas diluiría el embedding
    hasta volverlo inútil para encontrar la función específica que
    importa. Devuelve cuántos fragmentos quedaron indexados."""
    from skills.github_sync import CARPETA_REPOS, _listar_archivos_codigo

    documentos = []
    for ruta in _listar_archivos_codigo():
        try:
            with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                contenido = f.read()
        except OSError:
            continue
        if not contenido.strip():
            continue

        nombre_relativo = os.path.relpath(ruta, CARPETA_REPOS)
        for inicio in range(0, len(contenido), MAX_CARACTERES_CHUNK):
            fragmento = contenido[inicio:inicio + MAX_CARACTERES_CHUNK]
            if not fragmento.strip():
                continue
            documentos.append({
                "id": f"{nombre_relativo}#{inicio}", "archivo": nombre_relativo, "texto": fragmento,
            })

    return construir_indice("codigo", documentos)


def reindexar_todo():
    """Reconstruye ambos índices (notas + código). Pensado para correr en
    un hilo de fondo (ver intents/reindexar.py) — puede tardar según
    cuánto haya que indexar, una llamada a Ollama por documento."""
    n_notas = indexar_notas()
    n_codigo = indexar_codigo()
    return n_notas, n_codigo


def buscar_semantico_en_notas(consulta, top_k=TOP_K_NOTAS):
    """Mismo contrato que skills.obsidian.buscar_en_obsidian: string
    formateado con los fragmentos encontrados, o None si no hay nada
    relevante. Cae a esa misma búsqueda por palabra clave si el índice
    semántico no existe todavía o Ollama no respondió."""
    from skills.obsidian import buscar_en_obsidian

    resultados = buscar("notas", consulta, top_k=top_k)
    if resultados is None:
        return buscar_en_obsidian(consulta)
    if not resultados:
        return None
    return "\n\n".join(f"### {r['titulo']}\n{r['texto'][:800]}" for r in resultados)


def buscar_semantico_en_codigo(consulta, top_k=TOP_K_CODIGO):
    """Mismo contrato que skills.github_sync.buscar_en_mi_codigo."""
    from skills.github_sync import buscar_en_mi_codigo

    resultados = buscar("codigo", consulta, top_k=top_k)
    if resultados is None:
        return buscar_en_mi_codigo(consulta)
    if not resultados:
        return None
    return "\n\n".join(f"### {r['archivo']}\n```\n{r['texto']}\n```" for r in resultados)
