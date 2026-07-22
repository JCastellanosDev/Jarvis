"""Servidor Flask ultraligero para controlar Jarvis desde el celular.

Pensado para usarse sobre Tailscale (red privada entre tus dispositivos, sin
exponer nada a internet público) — por eso sigue sin login por defecto. Si
defines JARVIS_REMOTE_TOKEN en el .env, /comando exige ese token como defensa
extra (útil si algún día lo expones por un túnel público en vez de Tailscale).

La página es una consola tipo HUD que habla con /comando por fetch (sin
recargar), muestra un "..." al instante al enviar, deshabilita el botón
mientras espera respuesta, y ahora además:
  - Permite dictar el comando por voz (Web Speech API del navegador).
  - Reproduce la respuesta de Jarvis como audio en el propio celular.
Del lado del servidor, `ctx.lock` se usa en modo no bloqueante: si Jarvis ya
está procesando algo (por voz o por una orden remota anterior), una orden
nueva no se encola ni se repite.
"""

import base64
import os
import threading

from flask import Flask, jsonify, request

from core.config import VOCES_DISPONIBLES
from core.pwa import META_TAGS_PWA, registrar_rutas_pwa
from intents.base import DetenerJarvis
from panel.vista import crear_blueprint_panel

PAGINA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Jarvis · Control remoto</title>
""" + META_TAGS_PWA + """
<style>
  :root {
    --bg: #05070a;
    --panel: #10161f;
    --borde: #1c2530;
    --accent: #00e5c3;
    --accent-dim: #00e5c355;
    --texto: #d7e2ea;
    --texto-dim: #6b7684;
    --user: #7aa2ff;
    --alerta: #ffb454;
  }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body { height: 100%; }
  body {
    margin: 0;
    background: radial-gradient(circle at 50% 0%, #10161f 0%, #05070a 65%);
    color: var(--texto);
    font-family: "SF Mono", "Menlo", "Consolas", monospace;
    display: flex;
    flex-direction: column;
  }
  header { padding: 1rem 1.2rem 0.8rem; border-bottom: 1px solid var(--borde); }
  h1 {
    margin: 0; font-size: 1rem; letter-spacing: 0.14em;
    color: var(--accent); text-shadow: 0 0 12px var(--accent-dim);
  }
  .estado { margin-top: 0.4rem; font-size: 0.72rem; color: var(--texto-dim); display: flex; align-items: center; gap: 0.4rem; }
  .punto { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 8px var(--accent); }
  .punto.ocupado { background: var(--alerta); box-shadow: 0 0 8px var(--alerta); animation: pulso 0.9s infinite; }
  .punto.escuchando { background: var(--user); box-shadow: 0 0 8px var(--user); animation: pulso 0.6s infinite; }
  @keyframes pulso { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }

  #log { flex: 1; overflow-y: auto; padding: 1rem 1.2rem; display: flex; flex-direction: column; gap: 0.9rem; }
  .msg { max-width: 88%; padding: 0.6rem 0.8rem; border-radius: 10px; font-size: 0.88rem; line-height: 1.4; word-wrap: break-word; }
  .msg.user { align-self: flex-end; background: #17233a; border: 1px solid #24365a; color: var(--user); }
  .msg.jarvis { align-self: flex-start; background: var(--panel); border: 1px solid var(--borde); color: var(--texto); }
  .msg .rotulo { display: block; font-size: 0.62rem; letter-spacing: 0.08em; color: var(--texto-dim); margin-bottom: 0.2rem; }
  .msg.pendiente { opacity: 0.55; }
  .dots span { animation: parpadeo 1.2s infinite; opacity: 0.2; }
  .dots span:nth-child(2) { animation-delay: 0.2s; }
  .dots span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes parpadeo { 0%, 80%, 100% { opacity: 0.2; } 40% { opacity: 1; } }

  form { display: flex; gap: 0.5rem; padding: 0.8rem; border-top: 1px solid var(--borde); background: var(--panel); }
  input[type=text] {
    flex: 1; background: var(--bg); border: 1px solid #24303e; border-radius: 8px;
    color: var(--texto); padding: 0.7rem 0.8rem; font-size: 0.95rem; font-family: inherit; min-width: 0;
  }
  input[type=text]:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-dim); }
  button {
    background: var(--accent); color: #05070a; border: none; border-radius: 8px;
    padding: 0 1rem; font-weight: 600; font-family: inherit; font-size: 0.9rem; flex-shrink: 0;
  }
  button:disabled { background: #2a3644; color: var(--texto-dim); }
  #boton-mic { background: var(--panel); color: var(--accent); border: 1px solid var(--borde); font-size: 1.1rem; padding: 0 0.9rem; }
  #boton-mic.escuchando { background: var(--user); color: #05070a; border-color: var(--user); }
</style>
</head>
<body>
  <header>
    <h1>JARVIS // CONTROL REMOTO</h1>
    <div class="estado"><span class="punto" id="punto"></span><span id="texto-estado">en línea</span></div>
  </header>

  <div id="log"></div>

  <form id="form-comando" autocomplete="off">
    <button type="button" id="boton-mic" title="Dictar por voz">&#127908;</button>
    <input type="text" id="entrada" placeholder="Escribe u ordena por voz..." autofocus>
    <button type="submit" id="boton-enviar">Enviar</button>
  </form>

<script>
  const log = document.getElementById('log');
  const form = document.getElementById('form-comando');
  const entrada = document.getElementById('entrada');
  const boton = document.getElementById('boton-enviar');
  const botonMic = document.getElementById('boton-mic');
  const punto = document.getElementById('punto');
  const textoEstado = document.getElementById('texto-estado');

  function agregarMensaje(clase, rotulo, htmlTexto) {
    const div = document.createElement('div');
    div.className = 'msg ' + clase;
    div.innerHTML = '<span class="rotulo">' + rotulo + '</span>' + htmlTexto;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return div;
  }

  function marcarOcupado(ocupado) {
    boton.disabled = ocupado;
    punto.classList.toggle('ocupado', ocupado);
    if (!ocupado) textoEstado.textContent = 'en línea';
    else textoEstado.textContent = 'procesando...';
  }

  function escaparHtml(texto) {
    const d = document.createElement('div');
    d.textContent = texto;
    return d.innerHTML;
  }

  function obtenerToken() {
    return localStorage.getItem('jarvis_token') || '';
  }

  async function enviarComando(texto) {
    agregarMensaje('user', 'TÚ', escaparHtml(texto));
    entrada.value = '';
    marcarOcupado(true);
    const pendiente = agregarMensaje('jarvis pendiente', 'JARVIS', '<span class="dots"><span>.</span><span>.</span><span>.</span></span>');

    try {
      const resp = await fetch('/comando', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Jarvis-Token': obtenerToken() },
        body: JSON.stringify({ texto }),
      });

      if (resp.status === 401) {
        const token = prompt('Este Jarvis requiere una clave de acceso:');
        if (token) {
          localStorage.setItem('jarvis_token', token);
          pendiente.remove();
          marcarOcupado(false);
          return enviarComando(texto);
        }
      }

      const datos = await resp.json();
      pendiente.classList.remove('pendiente');
      const aviso = datos.voz_sistema ? ' <i>(voz de respaldo del sistema — sin créditos de ElevenLabs)</i>' : '';
      pendiente.innerHTML = '<span class="rotulo">JARVIS</span>' + escaparHtml(datos.respuesta || '(sin respuesta)') + aviso;

      if (datos.audio_base64) {
        const mime = datos.audio_mime || 'audio/mpeg';
        new Audio('data:' + mime + ';base64,' + datos.audio_base64).play().catch(() => {});
      }
    } catch (err) {
      pendiente.classList.remove('pendiente');
      pendiente.innerHTML = '<span class="rotulo">JARVIS</span>Error de conexión.';
    } finally {
      marcarOcupado(false);
      entrada.focus();
    }
  }

  form.addEventListener('submit', (ev) => {
    ev.preventDefault();
    const texto = entrada.value.trim();
    if (!texto || boton.disabled) return;
    enviarComando(texto);
  });

  // --- Dictado por voz (Web Speech API: funciona en Chrome/Brave sobre Android) ---
  const MotorVoz = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (MotorVoz) {
    const reconocedor = new MotorVoz();
    reconocedor.lang = 'es-ES';
    reconocedor.interimResults = false;
    reconocedor.maxAlternatives = 1;
    let escuchando = false;

    reconocedor.onstart = () => {
      escuchando = true;
      botonMic.classList.add('escuchando');
      punto.classList.add('escuchando');
      textoEstado.textContent = 'escuchando...';
    };

    reconocedor.onend = () => {
      escuchando = false;
      botonMic.classList.remove('escuchando');
      punto.classList.remove('escuchando');
      if (textoEstado.textContent === 'escuchando...') textoEstado.textContent = 'en línea';
    };

    reconocedor.onresult = (ev) => {
      const texto = ev.results[0][0].transcript;
      entrada.value = texto;
      enviarComando(texto);
    };

    reconocedor.onerror = (ev) => {
      textoEstado.textContent = 'en línea';
      agregarMensaje('jarvis', 'JARVIS', 'No pude escucharte (' + ev.error + '). Si usas Brave, prueba bajar el Shield de este sitio.');
    };

    botonMic.addEventListener('click', () => {
      if (escuchando) { reconocedor.stop(); return; }
      try { reconocedor.start(); } catch (e) { /* ya estaba iniciando */ }
    });
  } else {
    botonMic.disabled = true;
    botonMic.title = 'Tu navegador no soporta dictado por voz';
  }
</script>
</body>
</html>
"""


def crear_app(enrutador, ctx, hablante, token=None):
    app = Flask(__name__)
    app.register_blueprint(crear_blueprint_panel())
    registrar_rutas_pwa(app, "Jarvis Control Remoto", "Jarvis")

    def _autorizado():
        if not token:
            return True
        return request.headers.get("X-Jarvis-Token") == token

    @app.route("/", methods=["GET"])
    def index():
        return PAGINA

    @app.route("/comando", methods=["POST"])
    def comando():
        if not _autorizado():
            return jsonify(respuesta="Falta la clave de acceso."), 401

        datos = request.get_json(silent=True) or {}
        texto = (datos.get("texto") or "").strip()
        if not texto:
            return jsonify(respuesta=None), 400

        # El panel de la Mac reproduce el audio él mismo (perfectamente
        # sincronizado con la animación) y no quiere que además suene por
        # afplay — evita el eco de escuchar la respuesta dos veces.
        reproducir_local = datos.get("reproducir_local", True)

        adquirido = ctx.lock.acquire(blocking=False)
        if not adquirido:
            return jsonify(respuesta="Sigo procesando tu orden anterior, dame un segundo.")

        # Por defecto el propio "finally" suelta el lock. Si disparamos la
        # reproducción local en un hilo aparte, es ESE hilo el que lo suelta
        # cuando de verdad termine de sonar — si lo soltáramos antes, un
        # comando nuevo podría procesarse mientras el anterior sigue sonando
        # y se oirían dos respuestas (dos voces) encimadas.
        lock_transferido_a_hilo = False

        audio_bytes, mime_type = None, None
        try:
            try:
                respuesta = enrutador.procesar(texto, ctx)
            except DetenerJarvis as e:
                respuesta = e.mensaje_despedida
                # Va a matar el proceso en 1.5s de todos modos: aquí sí es
                # seguro bloquear, no hay un "siguiente comando" que proteger.
                if reproducir_local:
                    audio_bytes, mime_type = hablante.hablar_y_obtener_audio(respuesta)
                else:
                    audio_bytes, mime_type = hablante.sintetizar(respuesta)
                ctx.memoria.guardar()
                # Da tiempo a que la respuesta HTTP salga antes de matar el proceso.
                threading.Timer(1.5, lambda: os._exit(0)).start()
            else:
                if respuesta:
                    audio_bytes, mime_type = hablante.sintetizar(respuesta)
                    if reproducir_local and audio_bytes:
                        lock_transferido_a_hilo = True
                        hablante.reproducir_en_segundo_plano(audio_bytes, mime_type, al_terminar=ctx.lock.release)
        finally:
            if not lock_transferido_a_hilo:
                ctx.lock.release()

        return jsonify(
            respuesta=respuesta or "(sin respuesta)",
            audio_base64=base64.b64encode(audio_bytes).decode("ascii") if audio_bytes else None,
            audio_mime=mime_type,
            voz_sistema=hablante.usando_voz_sistema,
        )

    @app.route("/estado", methods=["GET"])
    def estado():
        if not _autorizado():
            return jsonify(error="no autorizado"), 401

        nombre_voz = next(
            (nombre for nombre, vid in VOCES_DISPONIBLES.items() if vid == hablante.voice_id),
            "personalizada",
        )
        return jsonify(
            voz=nombre_voz,
            voces_disponibles=list(VOCES_DISPONIBLES.keys()),
            hechos=len(ctx.memoria.hechos),
            turnos=len(ctx.memoria.historial_completo) // 2,
            ocupado=ctx.lock.locked(),
            hablando=hablante.hablando,
            evento=ctx.panel_evento,
        )

    @app.route("/detener", methods=["POST"])
    def detener():
        if not _autorizado():
            return jsonify(ok=False), 401
        hablante.detener()
        return jsonify(ok=True)

    return app


def iniciar_servidor_remoto(enrutador, ctx, hablante, puerto=5005, token=None):
    app = crear_app(enrutador, ctx, hablante, token=token)
    hilo = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=puerto, debug=False, use_reloader=False, threaded=True),
        daemon=True,
    )
    hilo.start()
    return hilo
