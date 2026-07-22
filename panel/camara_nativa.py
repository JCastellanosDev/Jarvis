"""App nativa de escritorio (no navegador) que abre la cámara directo con
OpenCV/AVFoundation y detecta gestos de mano con MediaPipe, evitando por
completo la capa de permisos de Brave — macOS le pide permiso de cámara a
este proceso de Python, no al navegador.

Corre en una ventana aparte (cv2.imshow) y manda lo que ve al servidor de
Jarvis (POST /grafico-obsidian/gesto) para que la página del grafo, ya
abierta en Brave, mueva los nodos con esos datos en vez de con su propia
cámara.

Se ejecuta con: venv/bin/python3 panel/camara_nativa.py [puerto]

Nota: el paquete `mediapipe` para macOS/arm64 ya no trae la API vieja
`mp.solutions.hands` — solo la nueva "Tasks API" (`HandLandmarker`), que
necesita un archivo de modelo aparte (~8MB). Se descarga solo la primera
vez desde el CDN oficial de Google, igual que hicimos con Kokoro."""

import os
import sys
import time

import cv2
import mediapipe as mp
import requests
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

UMBRAL_PINZA_NORMALIZADO = 0.06
FPS_ENVIO = 15
TITULO_VENTANA = "Jarvis - gestos (ESC o Q para cerrar)"

RUTA_MODELO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modelo_gestos", "hand_landmarker.task")
URL_MODELO = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)


def _asegurar_modelo():
    """Usa `requests` (no `urllib`) a propósito: los builds de Python de
    python.org en macOS no traen certificados SSL propios y `urllib` falla
    con CERTIFICATE_VERIFY_FAILED, mientras que `requests` sí trae los
    suyos vía `certifi` (ya es dependencia del proyecto)."""
    ruta = os.path.abspath(RUTA_MODELO)
    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        return ruta
    print(f"[Jarvis] Descargando el modelo de detección de manos a {ruta}...")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    respuesta = requests.get(URL_MODELO, timeout=30)
    respuesta.raise_for_status()
    with open(ruta, "wb") as f:
        f.write(respuesta.content)
    print("[Jarvis] Modelo descargado.")
    return ruta


def _construir_url_gesto(puerto):
    return f"http://localhost:{puerto}/grafico-obsidian/gesto"


def _extraer_manos(resultado):
    manos = []
    if not resultado or not resultado.hand_landmarks:
        return manos
    for puntos in resultado.hand_landmarks:
        pulgar = puntos[4]
        indice = puntos[8]
        # Espejo horizontal (cámara "selfie"): igual que el lado del navegador.
        x = 1 - indice.x
        y = indice.y
        distancia = ((pulgar.x - indice.x) ** 2 + (pulgar.y - indice.y) ** 2) ** 0.5
        # Tamaño de la mano en el cuadro (muñeca a base del dedo medio): más
        # grande cuanto más cerca de la cámara la tengas — el navegador lo
        # usa como control de zoom con una sola mano (sin pellizcar).
        muneca = puntos[0]
        base_medio = puntos[9]
        tamano = ((base_medio.x - muneca.x) ** 2 + (base_medio.y - muneca.y) ** 2) ** 0.5
        manos.append({
            "x": x, "y": y, "pinzando": distancia < UMBRAL_PINZA_NORMALIZADO, "tamano": tamano,
        })
    return manos


def ejecutar(puerto=5005):
    ruta_modelo = _asegurar_modelo()
    url_gesto = _construir_url_gesto(puerto)

    captura = cv2.VideoCapture(0)
    if not captura.isOpened():
        print("[Jarvis] No pude abrir la cámara (¿permiso denegado o en uso por otra app?).")
        return 1

    opciones = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=ruta_modelo),
        running_mode=RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.6,
        min_tracking_confidence=0.5,
    )
    ultimo_envio = 0.0
    marca_de_tiempo_ms = 0

    with HandLandmarker.create_from_options(opciones) as detector:
        print(f"[Jarvis] Cámara nativa activa, mandando gestos a {url_gesto}")
        try:
            while True:
                ok, cuadro = captura.read()
                if not ok:
                    break

                cuadro = cv2.flip(cuadro, 1)  # espejo, como una selfie
                rgb = cv2.cvtColor(cuadro, cv2.COLOR_BGR2RGB)
                imagen_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                marca_de_tiempo_ms += 1
                resultado = detector.detect_for_video(imagen_mp, marca_de_tiempo_ms)

                if resultado and resultado.hand_landmarks:
                    alto, ancho = cuadro.shape[:2]
                    for puntos in resultado.hand_landmarks:
                        for p in puntos:
                            cv2.circle(cuadro, (int(p.x * ancho), int(p.y * alto)), 3, (0, 229, 195), -1)

                ahora = time.monotonic()
                if ahora - ultimo_envio >= 1 / FPS_ENVIO:
                    manos = _extraer_manos(resultado)
                    try:
                        requests.post(url_gesto, json={"manos": manos}, timeout=0.5)
                    except requests.RequestException:
                        pass  # el panel puede no estar corriendo aún; sigue mostrando la cámara igual
                    ultimo_envio = ahora

                cv2.imshow(TITULO_VENTANA, cuadro)
                if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                    break
        finally:
            captura.release()
            cv2.destroyAllWindows()
            try:
                requests.post(url_gesto, json={"manos": []}, timeout=0.5)
            except requests.RequestException:
                pass
    return 0


if __name__ == "__main__":
    puerto_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 5005
    sys.exit(ejecutar(puerto_arg))
