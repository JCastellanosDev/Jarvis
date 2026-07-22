import pytest

from intents.apagado import ApagadoIntent
from intents.base import DetenerJarvis


@pytest.mark.parametrize("frase", [
    "apágate", "apágate jarvis", "cerrar", "cierra", "salir", "sal", "apaga",
])
def test_frases_de_apagado_disparan_cierre(frase):
    intent = ApagadoIntent()
    with pytest.raises(DetenerJarvis):
        intent.manejar(frase, ctx=None)


@pytest.mark.parametrize("frase", [
    "no me apagues por favor",
    "hoy me despedí de mi jefe",
    "cierra la puerta",
    "vamos a salir a comer",
])
def test_frases_similares_no_disparan_cierre(frase):
    intent = ApagadoIntent()
    assert intent.manejar(frase, ctx=None) is None


def test_despedida_varia():
    """Regresión: la despedida debe elegirse al azar, no ser siempre la misma."""
    intent = ApagadoIntent()
    mensajes = set()
    for _ in range(30):
        try:
            intent.manejar("apágate", ctx=None)
        except DetenerJarvis as e:
            mensajes.add(e.mensaje_despedida)
    assert len(mensajes) > 1
