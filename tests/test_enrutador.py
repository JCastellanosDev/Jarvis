"""Regresión de un bug real (visto en logs/jarvis.out.log): decir "Jarvis,
quiero ver una película" o "jarvis quiero ver spider-man" nunca abría nada
y caía al chat general, que alucinaba una respuesta ("¿quieres ver las
primeras dos películas...") sin ejecutar ningún intent real. La causa: el
"Jarvis" inicial quedaba pegado al texto capturado y ningún patrón exacto
("^quiero ver...") lo reconocía. Ahora el enrutador lo quita una sola vez
antes de probar la cadena de intents."""

from unittest.mock import MagicMock

from intents.enrutador import EnrutadorIntents


def _ctx_falso():
    return MagicMock()


def test_quita_jarvis_inicial_antes_de_probar_los_intents():
    intent = MagicMock()
    intent.manejar.side_effect = lambda texto, ctx: f"recibido: {texto}"
    enrutador = EnrutadorIntents([intent])

    enrutador.procesar("jarvis Quiero ver una película", _ctx_falso())

    texto_recibido = intent.manejar.call_args.args[0]
    assert "jarvis" not in texto_recibido.lower()
    assert texto_recibido == "Quiero ver una película"


def test_quita_variantes_oye_hey_jarvis():
    intent = MagicMock()
    intent.manejar.side_effect = lambda texto, ctx: f"recibido: {texto}"
    enrutador = EnrutadorIntents([intent])

    for frase, esperado in [
        ("Jarvis, ábreme WhatsApp", "ábreme WhatsApp"),
        ("oye jarvis pon música", "pon música"),
        ("hey Jarvis quiero ver spider-man", "quiero ver spider-man"),
    ]:
        enrutador.procesar(frase, _ctx_falso())
        assert intent.manejar.call_args.args[0] == esperado


def test_no_toca_jarvis_si_no_esta_al_inicio():
    intent = MagicMock()
    intent.manejar.side_effect = lambda texto, ctx: f"recibido: {texto}"
    enrutador = EnrutadorIntents([intent])

    enrutador.procesar("cuéntame sobre Jarvis de Iron Man", _ctx_falso())

    assert intent.manejar.call_args.args[0] == "cuéntame sobre Jarvis de Iron Man"


def test_primer_intent_que_responde_gana_y_no_llama_al_resto():
    intent1 = MagicMock()
    intent1.manejar.return_value = "listo"
    intent2 = MagicMock()
    intent2.manejar.return_value = "nunca debería llamarse"
    enrutador = EnrutadorIntents([intent1, intent2])

    resultado = enrutador.procesar("jarvis apágate", _ctx_falso())

    assert resultado == "listo"
    intent2.manejar.assert_not_called()
