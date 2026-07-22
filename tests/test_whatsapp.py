"""osascript/pbcopy SIEMPRE mockeados aquí: de verdad enviaría un WhatsApp a
una persona real si no lo estuviera. Se mockean las funciones auxiliares
(_leer_portapapeles, _escribir_portapapeles, _ejecutar_applescript) en vez de
subprocess.run crudo, porque ahora hay varias llamadas distintas (pbpaste,
pbcopy, osascript x2) y mockear por función es más claro y menos frágil."""

from contextlib import contextmanager
from unittest.mock import DEFAULT, MagicMock, patch

from intents.whatsapp import WhatsAppIntent
import skills.whatsapp as whatsapp_skill


@contextmanager
def _mockear_flujo(encontrado=True, envio_ok=True):
    """Mockea todo el I/O de enviar_whatsapp; da acceso a cada mock por
    nombre para hacer aserciones sobre cómo se llamó."""
    with patch.multiple(
        whatsapp_skill,
        _leer_portapapeles=DEFAULT,
        _restaurar_portapapeles=DEFAULT,
        _escribir_portapapeles=DEFAULT,
        _ejecutar_applescript=DEFAULT,
    ) as mocks:
        mocks["_leer_portapapeles"].return_value = b"lo que tenia copiado antes"
        mocks["_ejecutar_applescript"].side_effect = [
            MagicMock(returncode=0, stdout="OK_ENCONTRADO" if encontrado else "NO_ENCONTRADO", stderr=""),
            MagicMock(returncode=0 if envio_ok else 1, stdout="", stderr="" if envio_ok else "boom"),
        ]
        yield mocks


def test_no_matchea_texto_sin_relacion():
    intent = WhatsAppIntent()
    assert intent.manejar("hola como estas", ctx=None) is None


def test_contacto_desconocido_no_ejecuta_nada():
    with _mockear_flujo() as mocks:
        intent = WhatsAppIntent()
        resultado = intent.manejar("mándale un mensaje a fulano diciendo hola", ctx=None)
        assert "no tengo guardado" in resultado.lower()
        mocks["_ejecutar_applescript"].assert_not_called()


def test_contacto_conocido_copia_nombre_y_mensaje_al_portapapeles():
    with patch.object(whatsapp_skill, "CONTACTOS", {"chuy": "Chuy"}), \
         _mockear_flujo(encontrado=True) as mocks:
        intent = WhatsAppIntent()
        resultado = intent.manejar("mándale un mensaje a chuy diciendo ya voy saliendo", ctx=None)

        assert "enviado a chuy" in resultado.lower()
        llamadas = mocks["_escribir_portapapeles"].call_args_list
        assert llamadas[0].args[0] == "Chuy"  # primero copia el nombre a buscar
        assert llamadas[1].args[0] == "ya voy saliendo"  # luego el mensaje
        # El AppleScript en sí nunca debe llevar el texto acentuado/real incrustado.
        for llamada in mocks["_ejecutar_applescript"].call_args_list:
            assert "ya voy saliendo" not in llamada.args[0]
            assert "Chuy" not in llamada.args[0]


def test_nombre_del_contacto_viaja_por_variable_de_entorno_no_incrustado():
    """El nombre a verificar se pasa vía system attribute/env var, no como
    texto literal en el AppleScript (mismo problema de codificación que ya
    mordió dos veces con el texto incrustado)."""
    with patch.object(whatsapp_skill, "CONTACTOS", {"prueba": "Tú"}), \
         _mockear_flujo(encontrado=True) as mocks:
        WhatsAppIntent().manejar("mándale un mensaje a prueba diciendo hola", ctx=None)

        primera_llamada = mocks["_ejecutar_applescript"].call_args_list[0]
        variables_env = primera_llamada.kwargs.get("variables_env") or primera_llamada.args[1]
        assert variables_env == {"JARVIS_WA_NOMBRE": "Tú"}
        assert "Tú" not in primera_llamada.args[0]


def test_restaura_el_portapapeles_original_al_final():
    with patch.object(whatsapp_skill, "CONTACTOS", {"chuy": "Chuy"}), \
         _mockear_flujo(encontrado=True) as mocks:
        WhatsAppIntent().manejar("mándale un mensaje a chuy diciendo hola", ctx=None)
        mocks["_restaurar_portapapeles"].assert_called_once_with(b"lo que tenia copiado antes")


def test_verificacion_de_seguridad_aborta_si_no_encuentra_el_nombre():
    """Regresión: antes se comparaba contra el TÍTULO de la ventana, que en
    WhatsApp Desktop siempre es 'WhatsApp' sin importar el chat abierto —
    así que SIEMPRE abortaba, incluso cuando el chat correcto sí se abrió.
    Ahora busca el nombre en toda la ventana en vez de solo el título."""
    with patch.object(whatsapp_skill, "CONTACTOS", {"chuy": "Chuy"}), \
         _mockear_flujo(encontrado=False) as mocks:
        resultado = WhatsAppIntent().manejar("escríbele a chuy que ya voy", ctx=None)
        assert "no mandé nada" in resultado.lower()
        # Solo debió llamar al AppleScript de búsqueda, nunca al de enviar mensaje.
        assert mocks["_ejecutar_applescript"].call_count == 1


def test_escribele_que_tambien_matchea():
    with patch.object(whatsapp_skill, "CONTACTOS", {"angel": "Angel Pérez"}), \
         _mockear_flujo(encontrado=True):
        resultado = WhatsAppIntent().manejar("escríbele a angel que llego en 10 minutos", ctx=None)
        assert "enviado a angel" in resultado.lower()


def test_regresion_frases_reales_del_log():
    """Transcripciones reales capturadas en uso real: antes de ampliar los
    patrones, NINGUNA de estas coincidía y todas caían al chat general."""
    intent = WhatsAppIntent()

    with patch.object(whatsapp_skill, "CONTACTOS", {"prueba": "Tú"}), \
         _mockear_flujo(encontrado=True):
        assert intent.manejar(
            "mándale un mensaje a prueba diciendo hola esto es una prueba", ctx=None
        ) is not None

    with patch.object(whatsapp_skill, "CONTACTOS", {"prueba": "Tú"}), \
         _mockear_flujo(encontrado=True):
        resultado = intent.manejar(
            "Mándale un mensaje a prueba diciendo Hola Esto es una", ctx=None
        )
        assert resultado is not None


def test_frases_con_palabras_realmente_perdidas_no_deben_matchear():
    """Si el reconocimiento de voz perdió información esencial (el
    contacto, o la palabra 'mensaje a' completa), es correcto que NO
    matchee — no hay forma honesta de adivinar lo que falta."""
    intent = WhatsAppIntent()
    assert intent.manejar("Mándale un mamá diciendo hola", ctx=None) is None
    assert intent.manejar("Mándale un whatsapp a mamá", ctx=None) is None
    assert intent.manejar("Mándale un mensaje a prueba", ctx=None) is None
