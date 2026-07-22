"""Memoria: historial completo nunca se recorta; solo la ventana corta que
se manda al LLM. Deshacer un turno debe quitarlo de ambos lados."""

import json
import os
import tempfile

from core.memoria import MemoriaPersistente


def test_historial_completo_nunca_se_recorta():
    ruta = tempfile.mktemp(suffix=".json")
    m = MemoriaPersistente(ruta, max_turnos_contexto=2)

    for i in range(10):
        m.registrar_mensaje("user", f"mensaje {i}")

    assert len(m.historial) == 4  # 2 turnos = 4 mensajes (user+assistant... aquí solo user)
    assert len(m.historial_completo) == 10

    # registrar_mensaje() no guarda a disco solo (eso lo hace Cerebro tras
    # tener la respuesta completa); si no hay guardar() explícito, no hay
    # archivo que limpiar.
    if os.path.exists(ruta):
        os.remove(ruta)


def test_deshacer_ultimo_mensaje_quita_de_ambos_lados():
    ruta = tempfile.mktemp(suffix=".json")
    m = MemoriaPersistente(ruta, max_turnos_contexto=5)
    m.registrar_mensaje("user", "hola")
    m.deshacer_ultimo_mensaje()
    assert m.historial == []
    assert m.historial_completo == []
    if os.path.exists(ruta):
        os.remove(ruta)


def test_persiste_y_recarga_entre_sesiones():
    ruta = tempfile.mktemp(suffix=".json")
    m1 = MemoriaPersistente(ruta, max_turnos_contexto=5)
    m1.registrar_mensaje("user", "hola")
    m1.registrar_mensaje("assistant", "hola, ¿qué tal?")
    m1.agregar_hecho("le gusta el café")
    m1.guardar()

    m2 = MemoriaPersistente(ruta, max_turnos_contexto=5)
    assert len(m2.historial_completo) == 2
    assert m2.hechos == ["le gusta el café"]
    os.remove(ruta)


def test_migra_formato_anterior_historial_reciente():
    """Compatibilidad: el formato viejo guardaba 'historial_reciente' en vez
    de 'historial_completo'."""
    ruta = tempfile.mktemp(suffix=".json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"hechos": [], "historial_reciente": [{"role": "user", "content": "hola"}]}, f)

    m = MemoriaPersistente(ruta, max_turnos_contexto=5)
    assert len(m.historial_completo) == 1
    os.remove(ruta)
