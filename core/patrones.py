"""Registra qué frases no coinciden con ninguna skill específica (caen en
ChatGeneralIntent) para que TÚ decidas si vale la pena construir una skill
nueva para ellas. Jarvis NO se modifica solo — solo lleva la cuenta y te lo
reporta cuando le preguntes, human-in-the-loop en vez de autónomo."""

import json
import os


class RegistradorPatrones:
    def __init__(self, ruta_archivo="patrones_jarvis.json"):
        self._ruta = ruta_archivo
        self.conteos = {}
        self._cargar()

    def _cargar(self):
        if os.path.exists(self._ruta):
            try:
                with open(self._ruta, "r", encoding="utf-8") as f:
                    self.conteos = json.load(f)
                return
            except (json.JSONDecodeError, OSError):
                print("[Jarvis] Aviso: patrones_jarvis.json corrupto o ilegible, se reinicia.")
        self.conteos = {}

    def registrar(self, texto_normalizado):
        self.conteos[texto_normalizado] = self.conteos.get(texto_normalizado, 0) + 1
        self._guardar()

    def _guardar(self):
        try:
            with open(self._ruta, "w", encoding="utf-8") as f:
                json.dump(self.conteos, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"[Jarvis] No se pudo guardar patrones: {e}")

    def mas_frecuentes(self, minimo=2, top=5):
        frecuentes = [(texto, c) for texto, c in self.conteos.items() if c >= minimo]
        frecuentes.sort(key=lambda item: -item[1])
        return frecuentes[:top]
