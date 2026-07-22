"""Abre la vista gráfica de tu bóveda de Obsidian (nodos + conexiones,
controlable con gestos de mano por cámara) en Brave."""

from core.texto import normalizar
from skills.navegador import abrir_en_brave

from .base import Intent

FRASES_ABRIR_GRAFICO = {
    "abre el grafo de mis notas", "abre el grafo de obsidian",
    "muestrame el grafo de obsidian", "muestrame el grafico de obsidian",
    "abre la vista grafica de obsidian", "abre el mapa de mis notas",
    "quiero ver el grafo de mis notas", "abre el grafo con gestos",
}

MENSAJE_OK = "Abriendo el grafo de tus notas. Usa la cámara para arrastrar nodos pellizcando con los dedos."
MENSAJE_ERROR = "No pude abrir Brave. ¿Está instalado como 'Brave Browser'?"


class GraficoObsidianIntent(Intent):
    def manejar(self, texto, ctx):
        t = normalizar(texto)
        if t not in FRASES_ABRIR_GRAFICO:
            return None

        puerto = ctx.ctx_skills.get("puerto_remoto", 5005)
        url = f"http://localhost:{puerto}/grafico-obsidian"
        if not abrir_en_brave(url):
            return MENSAJE_ERROR
        return MENSAJE_OK
