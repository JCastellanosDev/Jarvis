"""Contrato común de todos los intents (patrón Chain of Responsibility).

Cada Intent implementa `manejar`: si reconoce la frase, devuelve el texto a
hablar; si no, devuelve None y el EnrutadorIntents prueba el siguiente. Esto
permite agregar habilidades nuevas creando una clase más, sin tocar el router
ni los intents existentes (principio abierto/cerrado).
"""

from abc import ABC, abstractmethod
from typing import Optional


class DetenerJarvis(Exception):
    """Señal de apagado limpio: se lanza desde ApagadoIntent y la captura
    el punto de entrada (bucle de voz o servidor remoto)."""

    def __init__(self, mensaje_despedida):
        super().__init__(mensaje_despedida)
        self.mensaje_despedida = mensaje_despedida


class Intent(ABC):
    @abstractmethod
    def manejar(self, texto: str, ctx) -> Optional[str]:
        """Devuelve el texto a hablar si esta habilidad maneja `texto`,
        o None para delegar al siguiente intent de la cadena."""
        raise NotImplementedError
