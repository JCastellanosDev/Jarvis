"""Regresión del bug real: al mandar audio al celular sin esperar a que
terminara de sonar en la Mac, el lock se soltaba ANTES de que la reproducción
local terminara — un segundo comando podía colarse y sonar encimado (dos
voces a la vez), y a veces "apágate" se perdía en esa ventana."""

import time
from unittest.mock import MagicMock

from remoto.servidor import crear_app


def test_lock_se_mantiene_hasta_que_termina_de_sonar(ctx):
    # Simula que la reproducción real tarda 300ms.
    def reproduccion_lenta(audio_bytes, mime_type="audio/mpeg"):
        time.sleep(0.3)
    ctx.hablante._reproducir_localmente = reproduccion_lenta
    ctx.hablante._cliente.text_to_speech.convert.return_value = [b"fakemp3"]

    from intents.enrutador import EnrutadorIntents
    from intents.chat_general import ChatGeneralIntent
    enrutador = EnrutadorIntents([ChatGeneralIntent()])

    app = crear_app(enrutador, ctx, ctx.hablante, token=None)
    cliente = app.test_client()

    inicio = time.time()
    r1 = cliente.post("/comando", json={"texto": "hola"})
    transcurrido = time.time() - inicio
    assert transcurrido < 0.2, "la respuesta no debería esperar a que termine de sonar"
    assert "sigo procesando" not in r1.get_json()["respuesta"].lower()

    # Mientras el audio del comando 1 SIGUE sonando (300ms no han pasado),
    # un segundo comando debe rebotar, no ejecutarse encimado.
    r2 = cliente.post("/comando", json={"texto": "otra cosa"})
    assert "sigo procesando" in r2.get_json()["respuesta"].lower()

    # Tras esperar a que termine, el lock ya debe estar libre.
    time.sleep(0.35)
    r3 = cliente.post("/comando", json={"texto": "una más"})
    assert "sigo procesando" not in r3.get_json()["respuesta"].lower()


def test_panel_no_reproduce_localmente(ctx):
    """reproducir_local=False (panel) no debe tocar afplay en la Mac, para
    no duplicar el audio si el panel está abierto en la misma Mac."""
    ctx.hablante._cliente.text_to_speech.convert.return_value = [b"fakemp3"]
    ctx.hablante._reproducir_localmente = MagicMock()

    from intents.enrutador import EnrutadorIntents
    from intents.chat_general import ChatGeneralIntent
    enrutador = EnrutadorIntents([ChatGeneralIntent()])

    app = crear_app(enrutador, ctx, ctx.hablante, token=None)
    cliente = app.test_client()

    r = cliente.post("/comando", json={"texto": "hola", "reproducir_local": False})
    assert r.get_json()["audio_base64"] is not None
    ctx.hablante._reproducir_localmente.assert_not_called()
