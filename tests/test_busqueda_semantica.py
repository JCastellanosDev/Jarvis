"""Búsqueda semántica: nunca toca Ollama de verdad (se mockea _embed) ni
escribe en el índice real del proyecto (RUTA_INDICE apunta a un directorio
temporal por test, vía el fixture `indice_temporal`).

Los tests de "vectores conocidos" verifican la matemática real de la
similitud coseno con embeddings de juguete donde el resultado esperado es
calculable a mano — no solo que las funciones se llamen, sino que el
ranking que producen es el correcto."""

import json

import numpy as np
import pytest

import core.busqueda_semantica as bs


@pytest.fixture
def indice_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "RUTA_INDICE", str(tmp_path))
    return tmp_path


# --- construir_indice() ---

def test_construir_indice_vacio_no_llama_a_ollama(indice_temporal):
    with _mock_embed() as mock_embed:
        resultado = bs.construir_indice("notas", [])
    assert resultado == 0
    mock_embed.assert_not_called()


def test_construir_indice_guarda_vectores_normalizados(indice_temporal):
    documentos = [{"id": "a", "texto": "hola"}, {"id": "b", "texto": "mundo"}]
    with _mock_embed() as mock_embed:
        mock_embed.return_value = np.array([[3.0, 4.0], [1.0, 0.0]], dtype=np.float32)  # norma 5 y 1
        n = bs.construir_indice("notas", documentos)

    assert n == 2
    vectores = np.load(bs._ruta_vectores("notas"))
    normas = np.linalg.norm(vectores, axis=1)
    np.testing.assert_allclose(normas, [1.0, 1.0], atol=1e-6)

    with open(bs._ruta_metadatos("notas")) as f:
        metadatos = json.load(f)
    assert metadatos == documentos


# --- buscar(): sin índice / fallo de Ollama ---

def test_buscar_sin_indice_devuelve_none(indice_temporal):
    assert bs.buscar("notas", "cualquier cosa") is None


def test_buscar_si_ollama_falla_en_la_consulta_devuelve_none(indice_temporal):
    documentos = [{"id": "a", "texto": "hola"}]
    with _mock_embed() as mock_embed:
        mock_embed.return_value = np.array([[1.0, 0.0]], dtype=np.float32)
        bs.construir_indice("notas", documentos)

    with _mock_embed() as mock_embed:
        mock_embed.side_effect = Exception("ollama no responde")
        assert bs.buscar("notas", "hola") is None


# --- buscar(): matemática de similitud coseno con vectores conocidos ---

def test_buscar_ordena_por_similitud_coseno_correctamente(indice_temporal):
    documentos = [
        {"id": "identico", "texto": "x"},
        {"id": "perpendicular", "texto": "y"},
        {"id": "opuesto", "texto": "z"},
    ]
    with _mock_embed() as mock_embed:
        mock_embed.return_value = np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]], dtype=np.float32)
        bs.construir_indice("notas", documentos)

    with _mock_embed() as mock_embed:
        mock_embed.return_value = np.array([[1.0, 0.0]], dtype=np.float32)  # igual al de "identico"
        resultados = bs.buscar("notas", "consulta", top_k=3, umbral=-2)  # umbral bajo: quiero ver los 3

    assert [r["id"] for r in resultados] == ["identico", "perpendicular", "opuesto"]
    assert resultados[0]["score"] == pytest.approx(1.0, abs=1e-6)
    assert resultados[1]["score"] == pytest.approx(0.0, abs=1e-6)
    assert resultados[2]["score"] == pytest.approx(-1.0, abs=1e-6)


def test_buscar_filtra_por_umbral(indice_temporal):
    documentos = [{"id": "relevante", "texto": "x"}, {"id": "irrelevante", "texto": "y"}]
    with _mock_embed() as mock_embed:
        mock_embed.return_value = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        bs.construir_indice("notas", documentos)

    with _mock_embed() as mock_embed:
        mock_embed.return_value = np.array([[1.0, 0.0]], dtype=np.float32)
        resultados = bs.buscar("notas", "consulta", umbral=0.5)

    assert [r["id"] for r in resultados] == ["relevante"]


def test_buscar_respeta_top_k(indice_temporal):
    documentos = [{"id": str(i), "texto": str(i)} for i in range(5)]
    vectores = np.array([[1.0, 0.9 - 0.1 * i] for i in range(5)], dtype=np.float32)  # 5 vectores distintos, cerca de [1,1]
    with _mock_embed() as mock_embed:
        mock_embed.return_value = vectores
        bs.construir_indice("notas", documentos)

    with _mock_embed() as mock_embed:
        mock_embed.return_value = np.array([[1.0, 1.0]], dtype=np.float32)
        resultados = bs.buscar("notas", "consulta", top_k=2, umbral=-2)

    assert len(resultados) == 2


# --- buscar_semantico_en_notas() / buscar_semantico_en_codigo(): fallback ---

def test_buscar_semantico_en_notas_cae_a_palabra_clave_sin_indice(indice_temporal, monkeypatch):
    llamado_con = {}

    def _keyword_falso(consulta):
        llamado_con["consulta"] = consulta
        return "resultado por palabra clave"

    monkeypatch.setattr("skills.obsidian.buscar_en_obsidian", _keyword_falso)
    resultado = bs.buscar_semantico_en_notas("mi consulta")

    assert resultado == "resultado por palabra clave"
    assert llamado_con["consulta"] == "mi consulta"


def test_buscar_semantico_en_notas_no_cae_a_palabra_clave_si_el_indice_no_encontro_nada(indice_temporal, monkeypatch):
    """Si el índice semántico SÍ existe pero no encontró nada relevante,
    no tiene sentido reintentar con palabra clave (subconjunto más
    estricto de lo que la búsqueda semántica ya intentó) — se reporta
    "nada encontrado" directo."""
    documentos = [{"id": "a", "titulo": "a", "texto": "x"}]
    with _mock_embed() as mock_embed:
        mock_embed.return_value = np.array([[1.0, 0.0]], dtype=np.float32)
        bs.construir_indice("notas", documentos)

    llamado = {"veces": 0}
    monkeypatch.setattr("skills.obsidian.buscar_en_obsidian", lambda c: llamado.update(veces=llamado["veces"] + 1))

    with _mock_embed() as mock_embed:
        mock_embed.return_value = np.array([[-1.0, 0.0]], dtype=np.float32)  # opuesto: similitud negativa
        resultado = bs.buscar_semantico_en_notas("algo sin relación")

    assert resultado is None
    assert llamado["veces"] == 0


def test_buscar_semantico_en_notas_formatea_los_resultados(indice_temporal):
    documentos = [{"id": "a", "titulo": "Mi Nota", "texto": "contenido completo de la nota"}]
    with _mock_embed() as mock_embed:
        mock_embed.return_value = np.array([[1.0, 0.0]], dtype=np.float32)
        bs.construir_indice("notas", documentos)

    with _mock_embed() as mock_embed:
        mock_embed.return_value = np.array([[1.0, 0.0]], dtype=np.float32)
        resultado = bs.buscar_semantico_en_notas("consulta")

    assert "Mi Nota" in resultado
    assert "contenido completo de la nota" in resultado


def test_buscar_semantico_en_codigo_cae_a_palabra_clave_sin_indice(indice_temporal, monkeypatch):
    monkeypatch.setattr("skills.github_sync.buscar_en_mi_codigo", lambda c: "resultado de código por palabra clave")
    assert bs.buscar_semantico_en_codigo("consulta") == "resultado de código por palabra clave"


# --- indexar_notas() / indexar_codigo(): ingestión ---

def test_indexar_notas_lee_archivos_y_construye_el_indice(indice_temporal, monkeypatch):
    from unittest.mock import mock_open, patch

    rutas = ["/vault/a.md", "/vault/b.md"]
    contenidos = {"/vault/a.md": "contenido A", "/vault/b.md": "contenido B"}
    monkeypatch.setattr("skills.obsidian._listar_archivos_md", lambda: iter(rutas))

    open_real = open

    def _open_falso(ruta, *a, **kw):
        # Solo intercepta las notas fuente — construir_indice() también usa
        # open() para ESCRIBIR el índice (metadatos.json), eso sí debe ir
        # al disco temporal real, no al mock de lectura.
        if ruta in contenidos:
            return mock_open(read_data=contenidos[ruta])(*a, **kw)
        return open_real(ruta, *a, **kw)

    with patch("builtins.open", side_effect=_open_falso), _mock_embed() as mock_embed:
        mock_embed.return_value = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        n = bs.indexar_notas()

    assert n == 2
    with open(bs._ruta_metadatos("notas")) as f:
        metadatos = json.load(f)
    assert {m["titulo"] for m in metadatos} == {"a", "b"}


def test_indexar_codigo_parte_archivos_largos_en_fragmentos(indice_temporal, monkeypatch):
    from unittest.mock import mock_open, patch

    contenido_largo = "x" * (bs.MAX_CARACTERES_CHUNK * 2 + 100)  # 3 fragmentos
    ruta_fuente = "/repos/proyecto/archivo.py"
    monkeypatch.setattr("skills.github_sync._listar_archivos_codigo", lambda: iter([ruta_fuente]))
    monkeypatch.setattr("skills.github_sync.CARPETA_REPOS", "/repos")

    open_real = open

    def _open_falso(ruta, *a, **kw):
        if ruta == ruta_fuente:
            return mock_open(read_data=contenido_largo)(*a, **kw)
        return open_real(ruta, *a, **kw)

    with patch("builtins.open", side_effect=_open_falso), _mock_embed() as mock_embed:
        mock_embed.return_value = np.array([[1.0, 0.0]] * 3, dtype=np.float32)
        n = bs.indexar_codigo()

    assert n == 3
    with open(bs._ruta_metadatos("codigo")) as f:
        metadatos = json.load(f)
    assert all(m["archivo"] == "proyecto/archivo.py" for m in metadatos)


def test_reindexar_todo_llama_ambos_y_devuelve_conteos(indice_temporal, monkeypatch):
    monkeypatch.setattr(bs, "indexar_notas", lambda: 7)
    monkeypatch.setattr(bs, "indexar_codigo", lambda: 3)
    assert bs.reindexar_todo() == (7, 3)


# --- helper: mockea core.busqueda_semantica._embed sin tocar Ollama ---

def _mock_embed():
    from unittest.mock import patch
    return patch("core.busqueda_semantica._embed")
