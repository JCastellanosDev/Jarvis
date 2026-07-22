"""Paquete de dependencias que se pasa a cada Intent (inversión de dependencias:
los intents dependen de este contrato, no de las clases concretas directamente)."""

import threading
from dataclasses import dataclass, field


@dataclass
class IntentContext:
    hablante: "core.hablante.Hablante"
    memoria: "core.memoria.MemoriaPersistente"
    cerebro: "core.cerebro.CerebroOllama"
    ctx_skills: dict
    lock: threading.Lock = field(default_factory=threading.Lock)
    # Señal de un solo uso para que un intent le pida algo visual al panel
    # (ej. mostrar la lista de voces). El panel la sondea vía /estado.
    panel_evento: dict = None
    registrador_patrones: "core.patrones.RegistradorPatrones" = None
