from unittest.mock import MagicMock, patch

import pytest

from intents.enrutador import EnrutadorIntents
from intents.video import VideoIntent


@pytest.fixture
def intent_video():
    with patch("skills.navegador.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        yield VideoIntent(), mock_run


def test_abre_prime_directo(intent_video):
    intent, mock_run = intent_video
    assert intent.manejar("abre prime video", ctx=None) == "Abriendo Prime Video."
    assert "primevideo.com" in mock_run.call_args.args[0][-1]


def test_abre_paramount_directo(intent_video):
    intent, mock_run = intent_video
    assert intent.manejar("abre paramount", ctx=None) == "Abriendo Paramount+."
    assert "paramountplus.com" in mock_run.call_args.args[0][-1]


def test_generico_pregunta_y_respeta_eleccion(intent_video):
    intent, mock_run = intent_video

    class CtxFalso:
        ctx_skills = {"pedir_texto_por_voz": lambda pregunta: "paramount"}

    resultado = intent.manejar("quiero ver algo", CtxFalso())
    assert resultado == "Abriendo Paramount+."


def test_generico_sin_respuesta_no_falla(intent_video):
    intent, _ = intent_video

    class CtxFalso:
        ctx_skills = {"pedir_texto_por_voz": lambda pregunta: None}

    resultado = intent.manejar("quiero ver una serie", CtxFalso())
    assert "no escuché" in resultado.lower()


def test_no_choca_con_musica():
    """'pon X' es de MultimediaIntent; VideoIntent solo usa 'quiero ver'."""
    intent = VideoIntent()
    assert intent.manejar("pon bohemian rhapsody", ctx=None) is None


def test_regresion_jarvis_inicial_no_bloquea_pelicula_especifica():
    """Bug real capturado en logs/jarvis.out.log: decir "jarvis Quiero ver
    spider-man" nunca abría nada y caía al chat general, porque el "jarvis"
    inicial rompía el patrón exacto "^quiero ver". Pasa por el enrutador
    real (no solo por VideoIntent directo) para probar el arreglo tal como
    corre en producción."""
    with patch("intents.video.buscar_donde_ver") as mock_buscar:
        mock_buscar.return_value = "Buscando spider-man."
        enrutador = EnrutadorIntents([VideoIntent()])

        resultado = enrutador.procesar("jarvis Quiero ver spider-man", ctx=None)

        assert resultado == "Buscando spider-man."
        mock_buscar.assert_called_once_with("spiderman")
