"""Rutas Flask del grafo servidas contra el server real (sin mock del
Blueprint) — solo se mockea construir_grafo() para no depender de que exista
una bóveda de Obsidian real en la máquina que corre los tests."""

from unittest.mock import MagicMock, patch

import pytest

import panel.grafico as modulo_grafico
from remoto.servidor import crear_app


@pytest.fixture(autouse=True)
def _resetear_estado_gesto():
    """_ultimo_gesto es estado compartido a nivel de módulo (así lo necesita
    la app real, para que camara_nativa.py y el navegador hablen del mismo
    dato) — sin resetearlo, un test dejaría manos "fantasma" para el
    siguiente sin importar el orden en que corran."""
    modulo_grafico._ultimo_gesto["manos"] = []
    modulo_grafico._ultimo_gesto["recibido_en"] = 0.0
    yield
    modulo_grafico._ultimo_gesto["manos"] = []
    modulo_grafico._ultimo_gesto["recibido_en"] = 0.0


def _cliente():
    app = crear_app(MagicMock(), MagicMock(), MagicMock())
    return app.test_client()


def test_pagina_del_grafo_carga():
    resultado = _cliente().get("/grafico-obsidian")
    assert resultado.status_code == 200
    assert b"grafo" in resultado.data.lower()
    assert b"Hands" in resultado.data


def test_pagina_incluye_panel_de_nota_y_zoom_y_dictado():
    resultado = _cliente().get("/grafico-obsidian")
    assert b"panel-nota" in resultado.data
    assert b"boton-agregar-nota" in resultado.data
    assert b"addEventListener('wheel'" in resultado.data


def test_datos_del_grafo_son_json_valido():
    grafo_falso = {"nodes": [{"id": "a", "existe": True}], "edges": []}
    with patch("panel.grafico.construir_grafo", return_value=grafo_falso):
        resultado = _cliente().get("/grafico-obsidian/datos.json")
    assert resultado.status_code == 200
    assert resultado.get_json() == grafo_falso


def test_gesto_no_recibido_reporta_inactivo():
    """Antes de que panel/camara_nativa.py mande algo, no debe haber manos
    fantasma ni marcarse como activa."""
    resultado = _cliente().get("/grafico-obsidian/gesto")
    assert resultado.status_code == 200
    datos = resultado.get_json()
    assert datos["manos"] == []
    assert datos["activa"] is False


def test_gesto_recibido_se_puede_leer_de_vuelta():
    cliente = _cliente()
    manos = [{"x": 0.4, "y": 0.6, "pinzando": True}]
    resultado_post = cliente.post("/grafico-obsidian/gesto", json={"manos": manos})
    assert resultado_post.status_code == 200

    resultado_get = cliente.get("/grafico-obsidian/gesto")
    datos = resultado_get.get_json()
    assert datos["manos"] == manos
    assert datos["activa"] is True


def test_gesto_vencido_se_reporta_inactivo():
    cliente = _cliente()
    cliente.post("/grafico-obsidian/gesto", json={"manos": [{"x": 0.1, "y": 0.1, "pinzando": False}]})

    with patch("panel.grafico.time.monotonic", return_value=modulo_grafico._ultimo_gesto["recibido_en"] + 5):
        resultado = cliente.get("/grafico-obsidian/gesto")
    datos = resultado.get_json()
    assert datos["manos"] == []
    assert datos["activa"] is False


def test_ver_nota_existente():
    with patch("panel.grafico.leer_nota", return_value="Contenido de la nota."):
        resultado = _cliente().get("/grafico-obsidian/nota?id=Mi%20nota")
    datos = resultado.get_json()
    assert datos["existe"] is True
    assert datos["contenido"] == "Contenido de la nota."


def test_ver_nota_inexistente():
    with patch("panel.grafico.leer_nota", return_value=None):
        resultado = _cliente().get("/grafico-obsidian/nota?id=fantasma")
    datos = resultado.get_json()
    assert datos["existe"] is False
    assert datos["contenido"] is None


def test_crear_nota_llama_a_agregar_nota():
    with patch("panel.grafico.agregar_nota", return_value="Nota agregada a tu bóveda de Obsidian.") as mock_agregar:
        resultado = _cliente().post("/grafico-obsidian/nota", json={"texto": "Comprar leche"})
    assert resultado.status_code == 200
    datos = resultado.get_json()
    assert datos["ok"] is True
    assert "agregada" in datos["mensaje"].lower()
    mock_agregar.assert_called_once_with("Comprar leche")


def test_crear_nota_sin_texto_da_error():
    resultado = _cliente().post("/grafico-obsidian/nota", json={"texto": "   "})
    assert resultado.status_code == 400
    assert resultado.get_json()["ok"] is False
