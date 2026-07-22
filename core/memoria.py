"""Responsable único de la memoria: hechos permanentes + historial completo
desde que existe Jarvis, con persistencia en disco entre sesiones.

`historial` es la ventana corta que se manda al LLM en cada turno (acotada,
para no disparar la latencia); `historial_completo` es el registro íntegro de
la conversación desde la primera vez que se usó Jarvis, y nunca se recorta.
"""

import json
import os


class MemoriaPersistente:
    def __init__(self, ruta_archivo, max_turnos_contexto=10):
        self._ruta = ruta_archivo
        self._max_mensajes_contexto = max_turnos_contexto * 2
        self.hechos = []
        self.historial = []
        self.historial_completo = []
        self._cargar()

    def _cargar(self):
        if os.path.exists(self._ruta):
            try:
                with open(self._ruta, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                self.hechos = datos.get("hechos", [])
                # "historial_reciente" es el nombre del formato anterior (solo
                # guardaba los últimos turnos); se respeta como fallback.
                self.historial_completo = datos.get("historial_completo") or datos.get("historial_reciente", [])
                self.historial = list(self.historial_completo[-self._max_mensajes_contexto:])
                return
            except (json.JSONDecodeError, OSError):
                print("[Jarvis] Aviso: memoria persistente corrupta o ilegible, se reinicia.")
        self.hechos = []
        self.historial = []
        self.historial_completo = []

    def registrar_mensaje(self, rol, contenido):
        mensaje = {"role": rol, "content": contenido}
        self.historial.append(mensaje)
        self.historial_completo.append(mensaje)
        if len(self.historial) > self._max_mensajes_contexto:
            del self.historial[:-self._max_mensajes_contexto]

    def deshacer_ultimo_mensaje(self):
        """Descarta el último turno si la llamada al LLM falló, tanto de la
        ventana corta como del historial completo."""
        if self.historial:
            self.historial.pop()
        if self.historial_completo:
            self.historial_completo.pop()

    def agregar_hecho(self, texto):
        self.hechos.append(texto)
        self.guardar()

    def guardar(self):
        datos = {
            "hechos": self.hechos,
            "historial_completo": self.historial_completo,
        }
        try:
            with open(self._ruta, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"[Jarvis] No se pudo guardar la memoria: {e}")
