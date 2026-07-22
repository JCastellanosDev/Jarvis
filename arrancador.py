"""Lanzador remoto ultraligero.

A diferencia de jarvis.py (que sigues arrancando tú manualmente), ESTE script
está pensado para correr siempre en segundo plano vía LaunchAgent — pero no
usa el micrófono ni el LLM, solo espera una orden HTTP para arrancar o
detener el proceso real de Jarvis. Así resuelves "quiero prenderlo desde el
celular sin ir a mi Mac" sin que nada esté escuchando por voz hasta que tú
mismo lo enciendas.

Para detener Jarvis reutiliza su propio comando de apagado (vía /comando),
en vez de matar el proceso a la fuerza, así se despide y guarda memoria igual
que si le hubieras dicho "apágate" por voz.

Jarvis se lanza dentro de una ventana real de Warp (no como proceso
invisible en segundo plano): un proceso lanzado directo desde launchd tiene
otra identidad de macOS y nunca llega a que se le conceda permiso de
Micrófono — lanzarlo así hereda el mismo permiso que ya funciona cuando lo
corres tú a mano. La primera vez que esto pase, macOS probablemente pida
permiso de Micrófono para "Warp" — acéptalo, igual que hiciste antes con
Terminal.

Usa una "Launch Configuration" de Warp (~/.warp/launch_configurations/) en
vez de AppleScript "do script" (que era para Terminal.app) — Warp no tiene
diccionario de AppleScript, pero sí soporta abrir una config guardada vía su
esquema de URL (`warp://launch/<nombre>`), y esa config corre el comando
automáticamente al abrir la ventana.
"""

import json
import os
import socket
import subprocess
import urllib.error
import urllib.request

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from core.pwa import META_TAGS_PWA, registrar_rutas_pwa

load_dotenv()

RUTA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
PYTHON_VENV = os.path.join(RUTA_PROYECTO, "venv", "bin", "python3")
SCRIPT_JARVIS = os.path.join(RUTA_PROYECTO, "jarvis.py")
LOG_OUT = os.path.join(RUTA_PROYECTO, "logs", "jarvis.out.log")

NOMBRE_LAUNCH_CONFIG = "jarvis"
RUTA_LAUNCH_CONFIGS = os.path.expanduser("~/.warp/launch_configurations")
RUTA_LAUNCH_CONFIG_JARVIS = os.path.join(RUTA_LAUNCH_CONFIGS, f"{NOMBRE_LAUNCH_CONFIG}.yaml")

PUERTO_ARRANCADOR = int(os.getenv("JARVIS_ARRANCADOR_PORT", "5006"))
PUERTO_JARVIS = int(os.getenv("JARVIS_REMOTE_PORT", "5005"))
TOKEN = os.getenv("JARVIS_REMOTE_TOKEN") or None

PAGINA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jarvis · Arrancador</title>
""" + META_TAGS_PWA + """
<style>
  body {
    margin: 0; height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1.2rem;
    background: #05070a; color: #d7e2ea; font-family: "SF Mono", "Menlo", monospace;
  }
  h1 { letter-spacing: 0.14em; color: #00e5c3; text-shadow: 0 0 12px #00e5c355; font-size: 1rem; }
  #punto { width: 10px; height: 10px; border-radius: 50%; background: #444; display: inline-block; margin-right: 0.4rem; }
  #punto.on { background: #00e5c3; box-shadow: 0 0 8px #00e5c3; }
  button {
    background: #00e5c3; color: #05070a; border: none; border-radius: 10px;
    padding: 1rem 2rem; font-size: 1rem; font-weight: 600; font-family: inherit; cursor: pointer;
  }
  button.detener { background: #ffb454; }
  button:disabled { background: #2a3644; color: #6b7684; }
  #boton-remoto {
    background: transparent; color: #00e5c3; border: 1px solid #00e5c3;
    display: none; text-decoration: none;
  }
  #boton-remoto.visible { display: inline-block; }
  #texto-estado { font-size: 0.78rem; color: #6b7684; letter-spacing: 0.08em; text-transform: uppercase; }
</style>
</head>
<body>
  <h1>JARVIS // ARRANCADOR</h1>
  <div id="texto-estado"><span id="punto"></span>consultando...</div>
  <button id="boton-accion" disabled>...</button>
  <a id="boton-remoto" href="#">Abrir modo remoto</a>

<script>
  function obtenerToken() { return localStorage.getItem('jarvis_token') || ''; }
  const boton = document.getElementById('boton-accion');
  const botonRemoto = document.getElementById('boton-remoto');
  const punto = document.getElementById('punto');
  const texto = document.getElementById('texto-estado');
  const puertoRemoto = """ + str(PUERTO_JARVIS) + """;

  async function refrescar() {
    try {
      const resp = await fetch('/estado');
      const datos = await resp.json();
      punto.classList.toggle('on', datos.corriendo);
      texto.textContent = datos.corriendo ? 'Jarvis está encendido' : 'Jarvis está apagado';
      boton.textContent = datos.corriendo ? 'Apagar Jarvis' : 'Encender Jarvis';
      boton.className = datos.corriendo ? 'detener' : '';
      boton.disabled = false;
      botonRemoto.classList.toggle('visible', datos.corriendo);
      botonRemoto.href = 'http://' + location.hostname + ':' + puertoRemoto + '/';
    } catch (e) {
      texto.textContent = 'No pude conectar con el arrancador.';
    }
  }

  boton.addEventListener('click', async () => {
    boton.disabled = true;
    const encendiendo = boton.textContent === 'Encender Jarvis';
    const ruta = encendiendo ? '/iniciar' : '/detener';
    try {
      await fetch(ruta, { method: 'POST', headers: { 'X-Jarvis-Token': obtenerToken() } });
    } catch (e) {}
    setTimeout(refrescar, encendiendo ? 2000 : 500);
  });

  refrescar();
  setInterval(refrescar, 4000);
</script>
</body>
</html>
"""

app = Flask(__name__)
registrar_rutas_pwa(app, "Jarvis Arrancador", "Jarvis ON")


def _autorizado():
    if not TOKEN:
        return True
    return request.headers.get("X-Jarvis-Token") == TOKEN


def _jarvis_esta_corriendo():
    try:
        with socket.create_connection(("127.0.0.1", PUERTO_JARVIS), timeout=0.5):
            return True
    except OSError:
        return False


def _escribir_launch_config():
    """Crea/actualiza la Launch Configuration de Warp que arranca Jarvis.
    Se reescribe en cada /iniciar (idempotente) para que siempre apunte a la
    ruta real del proyecto, sin depender de que ya exista de antes."""
    os.makedirs(RUTA_LAUNCH_CONFIGS, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_OUT), exist_ok=True)
    contenido = f"""---
name: {NOMBRE_LAUNCH_CONFIG}
windows:
  - tabs:
      - title: Jarvis
        layout:
          cwd: {RUTA_PROYECTO}
          commands:
            - exec: {PYTHON_VENV} -u {SCRIPT_JARVIS} 2>&1 | tee -a {LOG_OUT}
"""
    with open(RUTA_LAUNCH_CONFIG_JARVIS, "w", encoding="utf-8") as f:
        f.write(contenido)


def _lanzar_jarvis_en_warp():
    """Abre Jarvis en una ventana real de Warp (en vez de un proceso
    invisible en segundo plano vía subprocess).

    Un proceso lanzado directo desde launchd (como este arrancador) tiene una
    identidad de macOS distinta a la de un proceso que corres tú a mano desde
    una terminal — y nunca llega a que se le conceda permiso de Micrófono.
    Lanzándolo dentro de Warp, Jarvis corre con la identidad de Warp, a la
    que le das permiso de Micrófono la primera vez (mismo mecanismo que ya
    funcionaba con Terminal.app antes)."""
    _escribir_launch_config()
    subprocess.Popen(["open", f"warp://launch/{NOMBRE_LAUNCH_CONFIG}"])


def _peticion_a_jarvis(ruta, cuerpo):
    url = f"http://127.0.0.1:{PUERTO_JARVIS}{ruta}"
    datos = json.dumps(cuerpo).encode("utf-8")
    peticion = urllib.request.Request(url, data=datos, method="POST", headers={"Content-Type": "application/json"})
    if TOKEN:
        peticion.add_header("X-Jarvis-Token", TOKEN)
    with urllib.request.urlopen(peticion, timeout=5) as resp:
        return json.loads(resp.read())


@app.route("/", methods=["GET"])
def index():
    return PAGINA


@app.route("/estado", methods=["GET"])
def estado():
    return jsonify(corriendo=_jarvis_esta_corriendo())


@app.route("/iniciar", methods=["POST"])
def iniciar():
    if not _autorizado():
        return jsonify(ok=False, error="no autorizado"), 401

    if _jarvis_esta_corriendo():
        return jsonify(ok=True, ya_corria=True)

    _lanzar_jarvis_en_warp()
    return jsonify(ok=True, ya_corria=False)


@app.route("/detener", methods=["POST"])
def detener():
    if not _autorizado():
        return jsonify(ok=False, error="no autorizado"), 401

    if not _jarvis_esta_corriendo():
        return jsonify(ok=True, ya_estaba_apagado=True)

    try:
        # Reutiliza el propio flujo de apagado de Jarvis (se despide y
        # guarda memoria), en vez de matar el proceso a la fuerza.
        respuesta = _peticion_a_jarvis("/comando", {"texto": "apágate"})
        return jsonify(ok=True, respuesta=respuesta.get("respuesta"))
    except (urllib.error.URLError, OSError) as e:
        return jsonify(ok=False, error=str(e)), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PUERTO_ARRANCADOR, debug=False)
