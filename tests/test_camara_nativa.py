"""_extraer_manos() es lógica pura (sin cámara ni modelo real de por medio):
convierte landmarks crudos de MediaPipe en el mismo formato {x, y, pinzando,
distanciaDedos, angulo} que espera panel/grafico.py."""

import math
from types import SimpleNamespace

from panel.camara_nativa import UMBRAL_PINZA_NORMALIZADO, _extraer_manos


def _punto(x, y):
    return SimpleNamespace(x=x, y=y)


def _landmarks_falsos(por_indice):
    """21 puntos en (0,0) salvo los que se pasen explícitamente por índice."""
    puntos = [_punto(0.0, 0.0) for _ in range(21)]
    for indice, (x, y) in por_indice.items():
        puntos[indice] = _punto(x, y)
    return puntos


def test_sin_manos_devuelve_lista_vacia():
    assert _extraer_manos(None) == []
    assert _extraer_manos(SimpleNamespace(hand_landmarks=[])) == []


def test_no_espeja_las_coordenadas_el_cuadro_ya_viene_espejado():
    """El cuadro ya se espeja con cv2.flip() antes de detectar, así que x
    debe pasar tal cual (sin el 1 - x que sí necesita el navegador, que
    detecta sobre el video SIN espejar antes)."""
    puntos = _landmarks_falsos({8: (0.3, 0.4)})  # índice (fingertip)
    resultado = SimpleNamespace(hand_landmarks=[puntos])

    manos = _extraer_manos(resultado)

    assert len(manos) == 1
    assert manos[0]["x"] == 0.3
    assert manos[0]["y"] == 0.4


def test_detecta_pellizco_por_debajo_del_umbral():
    puntos = _landmarks_falsos({4: (0.5, 0.5), 8: (0.5, 0.5)})  # pulgar e índice juntos
    resultado = SimpleNamespace(hand_landmarks=[puntos])

    manos = _extraer_manos(resultado)

    assert manos[0]["pinzando"] is True
    assert manos[0]["distanciaDedos"] == 0.0


def test_no_pellizca_si_los_dedos_estan_separados():
    puntos = _landmarks_falsos({4: (0.0, 0.0), 8: (1.0, 0.0)})  # bien separados
    resultado = SimpleNamespace(hand_landmarks=[puntos])

    manos = _extraer_manos(resultado)

    assert manos[0]["pinzando"] is False
    assert manos[0]["distanciaDedos"] > UMBRAL_PINZA_NORMALIZADO


def test_angulo_de_la_mano_apuntando_hacia_arriba():
    # muñeca (0) abajo, base del dedo medio (9) arriba -> vector (0, -1) -> -pi/2.
    puntos = _landmarks_falsos({0: (0.5, 0.8), 9: (0.5, 0.2)})
    resultado = SimpleNamespace(hand_landmarks=[puntos])

    manos = _extraer_manos(resultado)

    assert manos[0]["angulo"] == math.atan2(0.2 - 0.8, 0.5 - 0.5)


def test_varias_manos_devuelve_varias_entradas():
    puntos1 = _landmarks_falsos({8: (0.1, 0.1)})
    puntos2 = _landmarks_falsos({8: (0.9, 0.9)})
    resultado = SimpleNamespace(hand_landmarks=[puntos1, puntos2])

    manos = _extraer_manos(resultado)

    assert len(manos) == 2
