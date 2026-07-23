"""Fixtures compartidas. Nada de esto toca ElevenLabs, afplay, Ollama ni el
micrófono reales — todo mockeado para que `pytest` corra rápido y sin efectos
secundarios (no abre Brave, no reproduce audio, no gasta créditos)."""

import tempfile
from unittest.mock import MagicMock, patch

import pytest

from core.contexto import IntentContext
from core.hablante import Hablante
from core.memoria import MemoriaPersistente


@pytest.fixture
def hablante_falso():
    with patch("core.hablante.ElevenLabs"):
        h = Hablante("fake-key", "voice123")
        h._reproducir_localmente = MagicMock()  # nunca llama afplay de verdad
        yield h


@pytest.fixture
def memoria_temporal():
    ruta = tempfile.mktemp(suffix=".json")
    m = MemoriaPersistente(ruta)
    yield m


@pytest.fixture
def cerebro_falso():
    cerebro = MagicMock()
    cerebro.responder.side_effect = lambda prompt, mem, **kw: f"[LLM MOCK] {prompt}"
    # ChatGeneralIntent llama a esta variante (con respaldo de herramientas);
    # se mockea igual que .responder para que cualquier test que dependa del
    # fixture compartido `ctx` siga recibiendo un string previsible sin
    # importar cuál de las dos use el intent.
    cerebro.responder_con_herramientas.side_effect = lambda prompt, mem, **kw: f"[LLM MOCK] {prompt}"
    return cerebro


@pytest.fixture
def ctx(hablante_falso, memoria_temporal, cerebro_falso):
    return IntentContext(
        hablante=hablante_falso,
        memoria=memoria_temporal,
        cerebro=cerebro_falso,
        ctx_skills={"ruta_repo": ".", "pedir_texto_por_voz": lambda pregunta: None},
    )
