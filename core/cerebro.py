"""Responsable único de conversar con el LLM local vía Ollama."""

import ollama


class CerebroOllama:
    PROMPT_BASE = (
        "Eres Jarvis, un asistente de IA sofisticado y directo. Responde siempre en "
        "español. Sé extremadamente conciso: responde en máximo una o dos oraciones "
        "breves. No utilices asteriscos ni emojis. Cada mensaje nuevo del usuario "
        "puede ser un tema completamente distinto al anterior: responde SOLO a lo "
        "que se te pregunta ahora, no sigas hablando del tema de turnos previos a "
        "menos que la pregunta actual claramente continúe esa conversación."
    )

    def __init__(self, modelo, timeout=15.0):
        self._modelo = modelo
        self._client = ollama.Client(timeout=timeout)

    def calentar(self):
        """Primera llamada 'muda' para que Ollama cargue el modelo en memoria
        antes de la primera pregunta real del usuario."""
        try:
            self._client.chat(model=self._modelo, messages=[{'role': 'user', 'content': 'hola'}])
        except Exception:
            pass

    def responder(self, prompt, memoria, contexto_web=None, contexto_obsidian=None, contexto_codigo=None):
        print("[Jarvis] Pensando respuesta...\n[Jarvis]: ", end="", flush=True)

        memoria.registrar_mensaje('user', prompt)

        mensajes_api = [
            {'role': 'system', 'content': self._construir_prompt_sistema(memoria.hechos)}
        ]

        # Estos contextos son efímeros: ayudan a responder esta pregunta
        # puntual, pero no se guardan en el historial para no inflar la
        # memoria persistente con resultados de búsqueda.
        if contexto_web:
            mensajes_api.append({
                'role': 'system',
                'content': (
                    "Resultados de una búsqueda web reciente, úsalos para responder "
                    "con precisión y de forma natural, sin leer URLs ni citar fuentes "
                    f"textualmente:\n{contexto_web}"
                ),
            })

        if contexto_obsidian:
            mensajes_api.append({
                'role': 'system',
                'content': (
                    "Fragmentos de las notas de Obsidian del usuario, úsalos para "
                    "responder con precisión; si citas algo, di de qué nota viene:\n"
                    f"{contexto_obsidian}"
                ),
            })

        if contexto_codigo:
            mensajes_api.append({
                'role': 'system',
                'content': (
                    "Fragmentos de código real del usuario (de sus propios repos de "
                    "GitHub), úsalos como referencia de SU estilo (nombres, "
                    "estructura, convenciones) si te pide ayuda programando algo "
                    f"parecido:\n{contexto_codigo}"
                ),
            })

        mensajes_api += memoria.historial

        try:
            stream = self._client.chat(model=self._modelo, messages=mensajes_api, stream=True)

            respuesta_completa = ""
            for chunk in stream:
                fragmento = chunk['message']['content']
                print(fragmento, end="", flush=True)
                respuesta_completa += fragmento

            print()

            memoria.registrar_mensaje('assistant', respuesta_completa)
            memoria.guardar()
            return respuesta_completa

        except Exception as e:
            print(f"\n[Jarvis] Error en Ollama: {e}")
            memoria.deshacer_ultimo_mensaje()
            return None

    def _construir_prompt_sistema(self, hechos):
        base = self.PROMPT_BASE
        if hechos:
            lista = "\n".join(f"- {h}" for h in hechos)
            base += (
                "\n\nDatos permanentes que sabes del usuario (úsalos solo si vienen al "
                f"caso, no los repitas sin que se te pregunte):\n{lista}"
            )
        return base
