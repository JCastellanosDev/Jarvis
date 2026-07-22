"""Ruta Flask del panel principal — solo se verifica que sirva contenido y
que incluya el botón para abrir el grafo de Obsidian (arriba a la derecha)."""

from unittest.mock import MagicMock

from remoto.servidor import crear_app


def _cliente():
    app = crear_app(MagicMock(), MagicMock(), MagicMock())
    return app.test_client()


def test_pagina_del_panel_carga():
    resultado = _cliente().get("/panel")
    assert resultado.status_code == 200
    assert b"JARVIS" in resultado.data


def test_incluye_el_boton_del_grafo_de_obsidian():
    resultado = _cliente().get("/panel")
    assert b"boton-grafo-obsidian" in resultado.data
    assert b"abre el grafo de mis notas" in resultado.data
