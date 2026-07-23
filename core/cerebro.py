"""Responsable único de conversar con el LLM local vía Ollama.

Además de la conversación libre de siempre (`responder`), expone
`responder_con_herramientas`: el mismo chat, pero dándole al modelo la
opción de invocar funciones de Python reales ("function calling" / tool
use) antes de contestar. Es el respaldo agéntico del router de intents/:
solo entra en juego cuando ninguna frase exacta hizo match (ver
intents/chat_general.py), así que un modelo local chico equivocándose de
herramienta no afecta a los comandos ya confiables y probados."""

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

    def __init__(self, modelo, timeout=15.0, herramientas=None, modelo_herramientas=None):
        self._modelo = modelo
        self._client = ollama.Client(timeout=timeout)
        # `herramientas`: lista de funciones Python normales (con docstring
        # estilo Google y type hints) — el cliente de Ollama las convierte
        # solo en el esquema JSON que el modelo necesita para elegir entre
        # ellas, no hace falta escribirlo a mano (ver skills/herramientas_agente.py).
        self._herramientas = list(herramientas) if herramientas else []
        self._herramientas_por_nombre = {f.__name__: f for f in self._herramientas}
        # Decidir SI usar una herramienta es más difícil que solo conversar
        # — probado en vivo, un modelo más grande acierta notablemente más
        # seguido esa decisión puntual. Por defecto usa el mismo `modelo`
        # de siempre (nada cambia si no se pasa este parámetro); la
        # respuesta final SIEMPRE se redacta con `modelo`, nunca con este.
        self._modelo_herramientas = modelo_herramientas or modelo

    def calentar(self):
        """Primera llamada 'muda' para que Ollama cargue el modelo en memoria
        antes de la primera pregunta real del usuario."""
        try:
            self._client.chat(model=self._modelo, messages=[{'role': 'user', 'content': 'hola'}])
        except Exception:
            pass

    def responder(self, prompt, memoria, contexto_web=None, contexto_obsidian=None, contexto_codigo=None):
        """Chat libre, sin herramientas — comportamiento original, intacto."""
        mensajes = self._mensajes_iniciales(prompt, memoria, contexto_web, contexto_obsidian, contexto_codigo)
        return self._transmitir_respuesta(mensajes, memoria)

    def responder_con_herramientas(self, prompt, memoria, contexto_web=None, contexto_obsidian=None, contexto_codigo=None):
        """Igual que `responder`, pero primero le da al modelo la opción de
        llamar una de `self._herramientas` (ej. buscar en Obsidian, mandar
        una notificación) antes de redactar la respuesta final — esa
        respuesta final siempre se transmite igual (en streaming), la única
        diferencia es que puede venir informada por lo que la herramienta
        devolvió."""
        mensajes = self._mensajes_iniciales(prompt, memoria, contexto_web, contexto_obsidian, contexto_codigo)
        if self._herramientas:
            mensajes = self._resolver_herramientas(mensajes)
        return self._transmitir_respuesta(mensajes, memoria)

    def _mensajes_iniciales(self, prompt, memoria, contexto_web, contexto_obsidian, contexto_codigo):
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
        return mensajes_api

    def _resolver_herramientas(self, mensajes):
        """Le pregunta al modelo (sin streaming: hace falta ver la respuesta
        completa para saber si pidió usar una herramienta) si alguna
        herramienta aplica. Si sí, las ejecuta y agrega sus resultados a la
        conversación; si no, devuelve los mensajes sin tocar. Nunca lanza:
        un fallo de Ollama o de la propia herramienta se degrada a chat
        normal en vez de tumbar la respuesta.

        La instrucción de "sé conservador" solo se manda en ESTA llamada de
        decisión (no contamina los mensajes de la respuesta final) — sin
        ella, probado en vivo con llama3.2:3b, el modelo a veces llama a
        buscar_en_obsidian hasta para preguntas de cultura general que no
        tienen nada que ver con las notas del usuario."""
        mensajes_decision = mensajes + [{
            'role': 'system',
            'content': (
                "Tienes herramientas disponibles para buscar en las notas de "
                "Obsidian del usuario, guardarle una nota nueva, o mandarle "
                "una notificación a su celular. Si el usuario pide "
                "explícitamente una de esas tres cosas, usa la herramienta "
                "correspondiente. Para cualquier otra pregunta (cultura "
                "general, charla, algo que ya sabes de memoria), responde "
                "directo sin usar ninguna herramienta."
            ),
        }]
        try:
            respuesta = self._client.chat(model=self._modelo_herramientas, messages=mensajes_decision, tools=self._herramientas)
        except Exception as e:
            print(f"[Jarvis] Error consultando herramientas: {e}")
            return mensajes

        llamadas = respuesta.message.tool_calls or []
        if not llamadas:
            return mensajes

        mensajes = mensajes + [respuesta.message]
        for llamada in llamadas:
            nombre = llamada.function.name
            argumentos = dict(llamada.function.arguments or {})
            funcion = self._herramientas_por_nombre.get(nombre)
            if not funcion:
                resultado = f"Herramienta desconocida: {nombre}"
            else:
                try:
                    resultado = funcion(**argumentos)
                except Exception as e:
                    resultado = f"Error ejecutando {nombre}: {e}"
            print(f"[Jarvis] Herramienta usada: {nombre}({argumentos}) -> {resultado}")
            mensajes.append({'role': 'tool', 'content': str(resultado), 'tool_name': nombre})

        return mensajes

    def _transmitir_respuesta(self, mensajes, memoria):
        print("[Jarvis] Pensando respuesta...\n[Jarvis]: ", end="", flush=True)
        try:
            stream = self._client.chat(model=self._modelo, messages=mensajes, stream=True)

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
