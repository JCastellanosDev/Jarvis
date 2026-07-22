"""Rutas Flask del grafo servidas contra el server real (sin mock del
Blueprint) — solo se mockea construir_grafo() para no depender de que exista
una bóveda de Obsidian real en la máquina que corre los tests."""

from unittest.mock import MagicMock, patch

from remoto.servidor import crear_app


def _cliente():
    app = crear_app(MagicMock(), MagicMock(), MagicMock())
    return app.test_client()


def test_pagina_del_grafo_carga():
    resultado = _cliente().get("/grafico-obsidian")
    assert resultado.status_code == 200
    assert b"grafo" in resultado.data.lower()
    assert b"Hands" in resultado.data


def test_datos_del_grafo_son_json_valido():
    grafo_falso = {"nodes": [{"id": "a", "existe": True}], "edges": []}
    with patch("panel.grafico.construir_grafo", return_value=grafo_falso):
        resultado = _cliente().get("/grafico-obsidian/datos.json")
    assert resultado.status_code == 200
    assert resultado.get_json() == grafo_falso
