"""Cada función de herramientas_agente.py es una envoltura delgada sobre una
skill ya probada — se mockea la skill de abajo, no hay red ni Ollama real de
por medio. También se verifica que Ollama pueda convertir cada función en un
esquema de herramienta válido (mismo mecanismo que usa core.cerebro al
pasarlas directo a `tools=`), para no descubrir un docstring mal formado
hasta la primera vez que el modelo intente usarla de verdad."""

from unittest.mock import patch

from ollama._utils import convert_function_to_tool

from skills.herramientas_agente import HERRAMIENTAS, agregar_nota, buscar_en_obsidian, enviar_notificacion_push


def test_buscar_en_obsidian_delega_en_la_skill():
    with patch("skills.herramientas_agente._buscar_en_obsidian", return_value="fragmento encontrado") as mock_buscar:
        resultado = buscar_en_obsidian("React")
    mock_buscar.assert_called_once_with("React")
    assert resultado == "fragmento encontrado"


def test_buscar_en_obsidian_sin_resultados_da_mensaje_claro():
    with patch("skills.herramientas_agente._buscar_en_obsidian", return_value=None):
        resultado = buscar_en_obsidian("algo que no existe")
    assert "no encontré" in resultado.lower()


def test_agregar_nota_delega_en_la_skill():
    with patch("skills.herramientas_agente._agregar_nota", return_value="Nota agregada.") as mock_agregar:
        resultado = agregar_nota("comprar leche")
    mock_agregar.assert_called_once_with("comprar leche")
    assert resultado == "Nota agregada."


def test_enviar_notificacion_push_delega_en_la_skill_y_devuelve_el_detalle():
    with patch("skills.herramientas_agente._enviar_notificacion", return_value=(True, "Notificación enviada.")) as mock_enviar:
        resultado = enviar_notificacion_push("Aviso", "algo pasó")
    mock_enviar.assert_called_once_with("Aviso", "algo pasó")
    assert resultado == "Notificación enviada."


def test_todas_las_herramientas_generan_un_esquema_valido_para_ollama():
    """Si el docstring de alguna no sigue el formato "Args:" que Ollama
    espera, esto lo detecta aquí en vez de fallar en silencio (una
    herramienta con parámetros mal descritos el modelo la usa peor) la
    primera vez que se intente usar de verdad."""
    assert len(HERRAMIENTAS) == 3
    for funcion in HERRAMIENTAS:
        tool = convert_function_to_tool(funcion)
        assert tool.function.name == funcion.__name__
        assert tool.function.description  # el docstring sí se parseó
        assert tool.function.parameters.properties  # los Args: sí se parsearon
        for nombre_param, propiedad in tool.function.parameters.properties.items():
            assert propiedad.description, f"{funcion.__name__}: falta describir el parámetro '{nombre_param}'"
