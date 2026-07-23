"""Herramientas expuestas al LLM para "function calling" (ver
core/cerebro.py y skills/herramientas_agente.HERRAMIENTAS).

Solo entran en juego como RESPALDO: cuando ninguna frase exacta de
intents/ hizo match, ChatGeneralIntent le da al modelo la opción de llamar
una de estas funciones en vez de solo conversar. Cada una es una
envoltura delgada sobre una skill YA existente y probada — no se toca su
código, solo se adapta la firma/docstring al formato que Ollama necesita
para generar el esquema de la herramienta automáticamente (nombre de la
función, descripción, y una sección "Args:" en el docstring).

A propósito la lista es corta y de bajo riesgo (buscar, agregar una nota,
mandar una notificación push). Nada destructivo o que modifique el sistema
(instalar software, cerrar apps, apagar Jarvis) se expone aquí: un modelo
local de pocos parámetros puede interpretar mal una frase ambigua, y para
esas acciones ya existe un intent con match exacto en intents/ — ese sigue
siendo el único camino para ejecutarlas."""

from skills.notificaciones import enviar_notificacion as _enviar_notificacion
from skills.obsidian import agregar_nota as _agregar_nota
from skills.obsidian import buscar_en_obsidian as _buscar_en_obsidian


def buscar_en_obsidian(consulta: str) -> str:
    """Busca por palabra clave en las notas de Obsidian del usuario.

    Úsala cuando el usuario pregunte algo que podría estar anotado en sus
    notas personales (ej. "qué anoté sobre X", "busca en mis notas de Y").

    Args:
        consulta: qué buscar, en lenguaje natural (ej. "notas sobre React").
    """
    resultado = _buscar_en_obsidian(consulta)
    return resultado or "No encontré nada relacionado en las notas de Obsidian."


def agregar_nota(texto: str) -> str:
    """Guarda una nota nueva, con fecha y hora, en la bóveda de Obsidian del usuario.

    Úsala cuando el usuario pida explícitamente anotar o recordar algo por
    escrito (ej. "anota que...", "guárdame la idea de...").

    Args:
        texto: el contenido exacto de la nota a guardar.
    """
    return _agregar_nota(texto)


def enviar_notificacion_push(titulo: str, mensaje: str) -> str:
    """Manda una notificación push al celular del usuario (vía ntfy.sh).

    Úsala cuando el usuario pida explícitamente que le avises o notifiques
    algo a su celular.

    Args:
        titulo: título corto de la notificación.
        mensaje: cuerpo del mensaje a mandar.
    """
    _ok, detalle = _enviar_notificacion(titulo, mensaje)
    return detalle


HERRAMIENTAS = [buscar_en_obsidian, agregar_nota, enviar_notificacion_push]
