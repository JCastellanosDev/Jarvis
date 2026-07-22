from unittest.mock import MagicMock, patch

import jarvis


@patch("intents.aplicaciones.subprocess.run")
@patch("skills.aplicaciones.subprocess.run")
@patch("core.hablante.ElevenLabs")
def test_cerrar_no_choca_con_apagado_del_sistema(mock_eleven, mock_close, mock_open):
    mock_open.return_value = MagicMock(returncode=0)
    mock_close.return_value = MagicMock(returncode=0)

    enrutador = jarvis.construir_enrutador()

    class CtxFalso:
        ctx_skills = {"ruta_repo": ".", "pedir_texto_por_voz": lambda p: None}
        esperando_repetir = False

    assert enrutador.procesar("cierra whatsapp", CtxFalso()) == "Cerrando WhatsApp."
    assert enrutador.procesar("cierra la aplicación whatsapp", CtxFalso()) == "Cerrando WhatsApp."
    assert enrutador.procesar("cierra app whatsapp", CtxFalso()) == "Cerrando WhatsApp."

    try:
        enrutador.procesar("cierra el sistema", CtxFalso())
        assert False, "debía apagar Jarvis, no tratarlo como nombre de app"
    except jarvis.DetenerJarvis:
        pass
