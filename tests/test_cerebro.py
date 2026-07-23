"""responder_con_herramientas() es el respaldo agéntico: le da al modelo la
opción de llamar una función de Python antes de contestar. Todo mockeado
(nunca toca un Ollama real) — se simula la respuesta de "decisión" (con o
sin tool_calls) y la respuesta final en streaming por separado, tal como
hace el código real en dos llamadas distintas."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.cerebro import CerebroOllama


def _memoria_falsa():
    memoria = MagicMock()
    memoria.hechos = []
    memoria.historial = []
    return memoria


def _chunks_streaming(texto):
    """Simula el formato de un chunk de streaming de Ollama: dict indexable,
    no un objeto con atributos (así responde la librería real en modo
    stream). Un solo chunk basta — estos tests no verifican granularidad
    de streaming, solo que el texto final se concatene y devuelva bien."""
    return [{'message': {'content': texto}}]


def _tool_call_falso(nombre, argumentos):
    return SimpleNamespace(function=SimpleNamespace(name=nombre, arguments=argumentos))


def test_responder_normal_no_toca_herramientas():
    """responder() (sin _con_herramientas) debe seguir streameando directo,
    en una sola llamada a chat(), exactamente como antes de este cambio."""
    with patch("core.cerebro.ollama.Client") as MockClient:
        cliente = MockClient.return_value
        cliente.chat.return_value = iter(_chunks_streaming("Hola mundo"))
        cerebro = CerebroOllama("modelo-falso", herramientas=[lambda: None])

        resultado = cerebro.responder("hola", _memoria_falsa())

        assert resultado == "Hola mundo"
        cliente.chat.assert_called_once()
        assert cliente.chat.call_args.kwargs.get("stream") is True


def test_responder_con_herramientas_sin_configurar_se_comporta_como_responder():
    with patch("core.cerebro.ollama.Client") as MockClient:
        cliente = MockClient.return_value
        cliente.chat.return_value = iter(_chunks_streaming("Hola"))
        cerebro = CerebroOllama("modelo-falso")  # sin herramientas=

        resultado = cerebro.responder_con_herramientas("hola", _memoria_falsa())

        assert resultado == "Hola"
        cliente.chat.assert_called_once()  # nunca intenta resolver herramientas si no hay ninguna


def test_modelo_no_pide_ninguna_herramienta():
    with patch("core.cerebro.ollama.Client") as MockClient:
        cliente = MockClient.return_value
        decision = SimpleNamespace(message=SimpleNamespace(tool_calls=None))
        cliente.chat.side_effect = [decision, iter(_chunks_streaming("Todo normal"))]

        herramienta_falsa = MagicMock(__name__="herramienta_falsa")
        cerebro = CerebroOllama("modelo-falso", herramientas=[herramienta_falsa])

        resultado = cerebro.responder_con_herramientas("hola", _memoria_falsa())

        assert resultado == "Todo normal"
        herramienta_falsa.assert_not_called()
        assert cliente.chat.call_count == 2


def test_modelo_pide_una_herramienta_y_se_ejecuta():
    with patch("core.cerebro.ollama.Client") as MockClient:
        cliente = MockClient.return_value
        llamada = _tool_call_falso("buscar_en_obsidian", {"consulta": "React"})
        decision = SimpleNamespace(message=SimpleNamespace(tool_calls=[llamada]))
        cliente.chat.side_effect = [decision, iter(_chunks_streaming("Encontré algo"))]

        def buscar_en_obsidian(consulta):
            return f"resultado para {consulta}"
        buscar_en_obsidian.__name__ = "buscar_en_obsidian"

        cerebro = CerebroOllama("modelo-falso", herramientas=[buscar_en_obsidian])
        resultado = cerebro.responder_con_herramientas("busca React", _memoria_falsa())

        assert resultado == "Encontré algo"
        # La segunda llamada (la del streaming final) debe incluir el
        # resultado de la herramienta en los mensajes que le manda a Ollama.
        segunda_llamada_mensajes = cliente.chat.call_args_list[1].kwargs["messages"]
        mensajes_de_herramienta = [m for m in segunda_llamada_mensajes if isinstance(m, dict) and m.get("role") == "tool"]
        assert len(mensajes_de_herramienta) == 1
        assert mensajes_de_herramienta[0]["content"] == "resultado para React"


def test_herramienta_desconocida_no_truena():
    """El modelo puede alucinar un nombre de herramienta que no existe —
    no debe tumbar la respuesta. (herramientas=[] sería falsy y ni
    intentaría resolver nada, por eso se registra una DISTINTA a la que
    el modelo "pide", para forzar el camino de "no encontrada".)"""
    with patch("core.cerebro.ollama.Client") as MockClient:
        cliente = MockClient.return_value
        llamada = _tool_call_falso("no_existe", {})
        decision = SimpleNamespace(message=SimpleNamespace(tool_calls=[llamada]))
        cliente.chat.side_effect = [decision, iter(_chunks_streaming("Sigo funcionando"))]

        otra_herramienta = MagicMock(__name__="otra_herramienta")
        cerebro = CerebroOllama("modelo-falso", herramientas=[otra_herramienta])
        resultado = cerebro.responder_con_herramientas("hola", _memoria_falsa())

        assert resultado == "Sigo funcionando"
        otra_herramienta.assert_not_called()


def test_herramienta_que_lanza_excepcion_no_truena():
    with patch("core.cerebro.ollama.Client") as MockClient:
        cliente = MockClient.return_value
        llamada = _tool_call_falso("falla", {})
        decision = SimpleNamespace(message=SimpleNamespace(tool_calls=[llamada]))
        cliente.chat.side_effect = [decision, iter(_chunks_streaming("Sigo funcionando"))]

        def falla():
            raise RuntimeError("boom")
        falla.__name__ = "falla"

        cerebro = CerebroOllama("modelo-falso", herramientas=[falla])
        resultado = cerebro.responder_con_herramientas("hola", _memoria_falsa())

        assert resultado == "Sigo funcionando"


def test_usa_un_modelo_distinto_solo_para_decidir_la_herramienta():
    """Probado en vivo: un modelo más grande acierta más seguido CUÁNDO usar
    una herramienta, pero es más lento — por eso es opcional y separado del
    modelo que redacta la respuesta final (ese siempre usa `modelo`)."""
    with patch("core.cerebro.ollama.Client") as MockClient:
        cliente = MockClient.return_value
        decision = SimpleNamespace(message=SimpleNamespace(tool_calls=None))
        cliente.chat.side_effect = [decision, iter(_chunks_streaming("listo"))]

        herramienta_falsa = MagicMock(__name__="herramienta_falsa")
        cerebro = CerebroOllama(
            "llama3.2:3b", herramientas=[herramienta_falsa], modelo_herramientas="qwen2.5:7b-instruct",
        )
        cerebro.responder_con_herramientas("hola", _memoria_falsa())

        modelo_llamada_decision = cliente.chat.call_args_list[0].kwargs["model"]
        modelo_llamada_final = cliente.chat.call_args_list[1].kwargs["model"]
        assert modelo_llamada_decision == "qwen2.5:7b-instruct"
        assert modelo_llamada_final == "llama3.2:3b"


def test_sin_modelo_de_herramientas_explicito_usa_el_mismo_de_siempre():
    with patch("core.cerebro.ollama.Client") as MockClient:
        cliente = MockClient.return_value
        decision = SimpleNamespace(message=SimpleNamespace(tool_calls=None))
        cliente.chat.side_effect = [decision, iter(_chunks_streaming("listo"))]

        herramienta_falsa = MagicMock(__name__="herramienta_falsa")
        cerebro = CerebroOllama("llama3.2:3b", herramientas=[herramienta_falsa])
        cerebro.responder_con_herramientas("hola", _memoria_falsa())

        assert cliente.chat.call_args_list[0].kwargs["model"] == "llama3.2:3b"


def test_error_consultando_herramientas_degrada_a_chat_normal():
    """Si Ollama truena en la llamada de "decisión" (ej. el modelo no
    soporta tools), no debe tumbar la respuesta — sigue como chat normal."""
    with patch("core.cerebro.ollama.Client") as MockClient:
        cliente = MockClient.return_value
        cliente.chat.side_effect = [Exception("el modelo no soporta tools"), iter(_chunks_streaming("Aun asi respondo"))]

        herramienta_falsa = MagicMock(__name__="herramienta_falsa")
        cerebro = CerebroOllama("modelo-falso", herramientas=[herramienta_falsa])

        resultado = cerebro.responder_con_herramientas("hola", _memoria_falsa())

        assert resultado == "Aun asi respondo"
