"""Abre la vista gráfica de tu bóveda de Obsidian (nodos + conexiones,
controlable con gestos de mano por cámara) en Brave."""

from core.texto import normalizar
from skills.grafico_obsidian import abrir_camara_nativa
from skills.navegador import abrir_en_brave

from .base import Intent

FRASES_ABRIR_GRAFICO = {
    "abre el grafo de mis notas", "abre el grafo de obsidian",
    "muestrame el grafo de obsidian", "muestrame el grafico de obsidian",
    "abre la vista grafica de obsidian", "abre el mapa de mis notas",
    "quiero ver el grafo de mis notas", "abre el grafo con gestos",
}

MENSAJE_OK = (
    "Abriendo el grafo de tus notas y la cámara nativa para los gestos. "
    "Pellizca con los dedos frente a la ventana de la cámara para arrastrar nodos."
)
MENSAJE_SOLO_NAVEGADOR = (
    "Abrí el grafo, pero no pude abrir la cámara nativa. "
    "Usa la cámara del navegador o arrastra con el mouse."
)
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

        if not abrir_camara_nativa(puerto):
            return MENSAJE_SOLO_NAVEGADOR
        return MENSAJE_OK
