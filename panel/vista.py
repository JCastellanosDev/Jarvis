"""Panel visual tipo HUD para usar en la propia Mac (o cualquier navegador en
tu red/Tailscale): reloj, barra lateral con accesos a habilidades reales de
Jarvis, y una esfera de partículas que reacciona en vivo al audio de la
respuesta (Web Audio API `AnalyserNode`).

A diferencia de la página de control remoto para el celular, el panel
reproduce el audio ÉL MISMO (le pide al backend `reproducir_local: false`)
para no duplicar el sonido si lo abres en un navegador de la misma Mac que
tiene los parlantes — así la animación queda perfectamente sincronizada con
lo que realmente estás escuchando, en vez de reaccionar a un clip que ya
terminó de sonar por afplay.
"""

from flask import Blueprint

PAGINA_PANEL = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jarvis · Panel</title>
<style>
  :root {
    --bg: #030507;
    --panel: #0b1017;
    --borde: #1c2530;
    --accent: #00e5c3;
    --accent-dim: #00e5c355;
    --texto: #d7e2ea;
    --texto-dim: #6b7684;
    --user: #7aa2ff;
    --alerta: #ffb454;
  }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body { height: 100%; margin: 0; }
  body {
    background: radial-gradient(circle at 50% 30%, #0d141d 0%, #030507 70%);
    color: var(--texto);
    font-family: "SF Mono", "Menlo", "Consolas", monospace;
    display: grid;
    grid-template-columns: 230px 1fr;
    grid-template-rows: 100px 1fr 110px;
    grid-template-areas: "sidebar reloj" "sidebar esfera" "sidebar controles";
    overflow: hidden;
  }

  /* --- Reloj --- */
  #reloj-zona { grid-area: reloj; display: flex; flex-direction: column; align-items: center; justify-content: center; }
  #reloj { font-size: 2.1rem; letter-spacing: 0.12em; color: var(--accent); text-shadow: 0 0 16px var(--accent-dim); }
  #fecha { font-size: 0.68rem; letter-spacing: 0.15em; color: var(--texto-dim); text-transform: uppercase; margin-top: 0.2rem; }

  /* --- Sidebar --- */
  #sidebar { grid-area: sidebar; background: var(--panel); border-right: 1px solid var(--borde); padding: 1rem 0.8rem; overflow-y: auto; }
  #sidebar h1 { font-size: 0.85rem; letter-spacing: 0.18em; color: var(--accent); margin: 0 0 1.2rem; text-shadow: 0 0 10px var(--accent-dim); }
  .seccion-titulo { font-size: 0.62rem; letter-spacing: 0.12em; color: var(--texto-dim); margin: 1rem 0 0.4rem; text-transform: uppercase; }
  .item {
    display: flex; align-items: center; gap: 0.5rem; width: 100%;
    background: transparent; border: 1px solid transparent; border-radius: 6px;
    color: var(--texto); font-family: inherit; font-size: 0.78rem;
    padding: 0.5rem 0.6rem; text-align: left; cursor: pointer; margin-bottom: 0.15rem;
  }
  .item:hover { background: #131b26; border-color: var(--borde); }
  .item .ico { color: var(--accent); }
  .dato { display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--texto-dim); padding: 0.3rem 0.6rem; }
  .dato b { color: var(--texto); font-weight: 500; }
  #version { margin-top: 1.5rem; font-size: 0.6rem; color: var(--texto-dim); text-align: center; letter-spacing: 0.1em; }

  /* --- Esfera --- */
  #esfera-zona { grid-area: esfera; position: relative; display: flex; align-items: center; justify-content: center; }
  #esfera { width: min(70vh, 90%); height: min(70vh, 90%); }
  #caption { position: absolute; bottom: 0.5rem; font-size: 0.75rem; color: var(--texto-dim); text-align: center; max-width: 80%; }
  #caption b { color: var(--accent); }

  #lista-voces {
    position: absolute; top: 1rem; display: none;
    background: var(--panel); border: 1px solid var(--borde); border-radius: 10px;
    padding: 0.6rem; gap: 0.4rem; flex-direction: column; min-width: 160px;
  }
  #lista-voces .titulo { font-size: 0.62rem; letter-spacing: 0.1em; color: var(--texto-dim); text-transform: uppercase; margin-bottom: 0.2rem; }
  .boton-voz {
    background: transparent; border: 1px solid var(--borde); border-radius: 6px;
    color: var(--texto); font-family: inherit; font-size: 0.8rem; padding: 0.4rem 0.6rem;
    text-align: left; cursor: pointer;
  }
  .boton-voz:hover { border-color: var(--accent); }
  .boton-voz.activa { color: var(--accent); border-color: var(--accent); background: #0d1f1c; }

  /* --- Botón flotante: abrir el grafo de Obsidian (arriba a la derecha) --- */
  #boton-grafo-obsidian {
    position: absolute; top: 0.8rem; right: 0.8rem; z-index: 5;
    display: flex; align-items: center; gap: 0.4rem;
    background: var(--panel); border: 1px solid var(--borde); border-radius: 8px;
    color: var(--texto); font-family: inherit; font-size: 0.75rem;
    padding: 0.5rem 0.8rem; cursor: pointer;
  }
  #boton-grafo-obsidian:hover { border-color: var(--accent); color: var(--accent); }
  #boton-grafo-obsidian .ico { color: var(--accent); }

  /* --- Controles --- */
  #controles { grid-area: controles; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.6rem; border-top: 1px solid var(--borde); background: var(--panel); }
  .fila-botones { display: flex; gap: 0.8rem; align-items: center; }
  .boton-redondo {
    width: 52px; height: 52px; border-radius: 50%; border: 1px solid var(--borde);
    background: #0d141d; color: var(--accent); font-size: 1.3rem; cursor: pointer;
  }
  .boton-redondo.mic.escuchando { background: var(--user); color: #05070a; border-color: var(--user); box-shadow: 0 0 14px var(--user); }
  .boton-redondo.stop { color: var(--alerta); }
  #estado-texto { font-size: 0.72rem; letter-spacing: 0.1em; color: var(--texto-dim); text-transform: uppercase; }
  #estado-texto.activo { color: var(--accent); }
</style>
</head>
<body>

  <aside id="sidebar">
    <h1>JARVIS</h1>

    <div class="seccion-titulo">Estado</div>
    <div class="dato"><span>Voz</span><b id="dato-voz">—</b></div>
    <div class="dato"><span>Hechos guardados</span><b id="dato-hechos">—</b></div>
    <div class="dato"><span>Turnos totales</span><b id="dato-turnos">—</b></div>

    <div class="seccion-titulo">Habilidades</div>
    <button class="item" data-comando="modo desarrollo"><span class="ico">&#9881;</span>Modo desarrollo</button>
    <button class="item" data-comando="pon música"><span class="ico">&#9835;</span>Música que me gusta</button>
    <button class="item" data-comando="modo otaku"><span class="ico">&#127909;</span>Modo otaku</button>
    <button class="item" data-comando="qué hora es"><span class="ico">&#128337;</span>Hora y fecha</button>
    <button class="item" data-comando="sube los cambios a github"><span class="ico">&#128190;</span>Subir a GitHub</button>
    <button class="item" data-comando="revisa el estado de melo"><span class="ico">&#128202;</span>Estado de Melo</button>

    <div class="seccion-titulo">Control remoto</div>
    <button class="item" id="item-detener"><span class="ico">&#9209;</span>Interrumpir voz</button>

    <div id="version">JARVIS OS &middot; PANEL v1.0</div>
  </aside>

  <button id="boton-grafo-obsidian" title="Abrir el grafo de tus notas de Obsidian (con gestos por cámara)">
    <span class="ico">&#128279;</span>Grafo de Obsidian
  </button>

  <div id="reloj-zona">
    <div id="reloj">--:--:--</div>
    <div id="fecha">-- -- ----</div>
  </div>

  <div id="esfera-zona">
    <canvas id="esfera"></canvas>
    <div id="lista-voces"><div class="titulo">Voces disponibles</div></div>
    <div id="caption">Toca el micrófono o escribe abajo.</div>
  </div>

  <div id="controles">
    <div id="estado-texto">en línea</div>
    <div class="fila-botones">
      <button class="boton-redondo mic" id="boton-mic" title="Dictar por voz">&#127908;</button>
      <input type="text" id="entrada" placeholder="Escribe una orden..." style="background:#0d141d;border:1px solid #24303e;border-radius:8px;color:var(--texto);padding:0.6rem 0.8rem;font-family:inherit;font-size:0.85rem;width:280px;">
      <button class="boton-redondo stop" id="boton-stop" title="Interrumpir">&#9632;</button>
    </div>
  </div>

<script>
  // --- Reloj ---
  function actualizarReloj() {
    const ahora = new Date();
    document.getElementById('reloj').textContent = ahora.toLocaleTimeString('es-ES', { hour12: false });
    document.getElementById('fecha').textContent = ahora.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  }
  actualizarReloj();
  setInterval(actualizarReloj, 1000);

  // --- Estado: sidebar, esfera reactiva cuando Jarvis habla por voz/celular,
  // lista de voces bajo pedido, y cierre automático si el servidor se apaga. ---
  function obtenerToken() { return localStorage.getItem('jarvis_token') || ''; }

  const listaVoces = document.getElementById('lista-voces');
  let audioLocalActivo = false;    // true mientras EL PANEL reproduce su propio <audio>
  let ultimoEventoId = null;
  let fallosSeguidos = 0;

  function mostrarListaVoces(vocesDisponibles, vozActual) {
    listaVoces.innerHTML = '<div class="titulo">Voces disponibles</div>';
    vocesDisponibles.forEach((nombre) => {
      const boton = document.createElement('button');
      boton.className = 'boton-voz' + (nombre === vozActual ? ' activa' : '');
      boton.textContent = nombre.charAt(0).toUpperCase() + nombre.slice(1) + (nombre === vozActual ? ' (activa)' : '');
      boton.addEventListener('click', () => enviarComando('cambia la voz a ' + nombre));
      listaVoces.appendChild(boton);
    });
    listaVoces.style.display = 'flex';
    clearTimeout(listaVoces._temporizador);
    listaVoces._temporizador = setTimeout(() => { listaVoces.style.display = 'none'; }, 12000);
  }

  async function actualizarEstado() {
    try {
      const resp = await fetch('/estado', { headers: { 'X-Jarvis-Token': obtenerToken() } });
      if (!resp.ok) throw new Error('estado no ok');
      fallosSeguidos = 0;

      const datos = await resp.json();
      document.getElementById('dato-voz').textContent = datos.voz;
      document.getElementById('dato-hechos').textContent = datos.hechos;
      document.getElementById('dato-turnos').textContent = datos.turnos;

      // La esfera reacciona aunque el audio no venga del propio panel (voz o celular).
      if (!audioLocalActivo) {
        objetivoAudio = datos.hablando ? (0.35 + 0.35 * Math.sin(Date.now() / 150)) : 0;
      }

      if (datos.evento && datos.evento.tipo === 'voces' && datos.evento.id !== ultimoEventoId) {
        ultimoEventoId = datos.evento.id;
        mostrarListaVoces(datos.voces_disponibles, datos.voz);
      }
    } catch (e) {
      fallosSeguidos++;
      if (fallosSeguidos >= 4) {
        caption.textContent = 'Jarvis se apagó. Puedes cerrar esta ventana.';
        window.close();
      }
    }
  }
  actualizarEstado();
  setInterval(actualizarEstado, 250);

  // --- Esfera de partículas, reactiva al audio ---
  const canvas = document.getElementById('esfera');
  const ctx2d = canvas.getContext('2d');
  let ancho, alto;
  function ajustarTamano() {
    const rect = canvas.getBoundingClientRect();
    ancho = canvas.width = rect.width * devicePixelRatio;
    alto = canvas.height = rect.height * devicePixelRatio;
  }
  window.addEventListener('resize', ajustarTamano);
  ajustarTamano();

  const N_PUNTOS = 160;
  const puntos = [];
  for (let i = 0; i < N_PUNTOS; i++) {
    const y = 1 - (i / (N_PUNTOS - 1)) * 2;
    const radioEnY = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = i * Math.PI * (3 - Math.sqrt(5));
    puntos.push({ xo: Math.cos(theta) * radioEnY, yo: y, zo: Math.sin(theta) * radioEnY });
  }

  let anguloY = 0;
  const anguloX = 0.35;
  let nivelAudio = 0;
  let objetivoAudio = 0;

  function rotarPunto(x, y, z, ay, ax) {
    const x1 = x * Math.cos(ay) - z * Math.sin(ay);
    const z1 = x * Math.sin(ay) + z * Math.cos(ay);
    const y2 = y * Math.cos(ax) - z1 * Math.sin(ax);
    const z2 = y * Math.sin(ax) + z1 * Math.cos(ax);
    return [x1, y2, z2];
  }

  function dibujar() {
    requestAnimationFrame(dibujar);
    ctx2d.clearRect(0, 0, ancho, alto);

    nivelAudio += (objetivoAudio - nivelAudio) * 0.15;
    anguloY += 0.0025 + nivelAudio * 0.012;

    const cx = ancho / 2, cy = alto / 2;
    const escala = Math.min(ancho, alto) * 0.34 * (1 + nivelAudio * 0.12);
    const jitter = nivelAudio * 0.07;

    const proyectados = puntos.map((p, i) => {
      const r = 1 + Math.sin(i * 12.9 + anguloY * 8) * jitter;
      const [x, y, z] = rotarPunto(p.xo * r, p.yo * r, p.zo * r, anguloY, anguloX);
      const perspectiva = 2.4 / (2.4 - z);
      return {
        x: cx + x * escala * perspectiva,
        y: cy + y * escala * perspectiva,
        brillo: 0.3 + 0.7 * ((z + 1) / 2),
      };
    });

    ctx2d.lineWidth = 1;
    const umbral = escala * 0.3;
    for (let i = 0; i < proyectados.length; i++) {
      for (let j = i + 1; j < proyectados.length; j++) {
        const dx = proyectados[i].x - proyectados[j].x;
        const dy = proyectados[i].y - proyectados[j].y;
        const dist = Math.hypot(dx, dy);
        if (dist < umbral) {
          const alfa = (1 - dist / umbral) * 0.18 * Math.min(proyectados[i].brillo, proyectados[j].brillo);
          ctx2d.strokeStyle = `rgba(0, 229, 195, ${alfa})`;
          ctx2d.beginPath();
          ctx2d.moveTo(proyectados[i].x, proyectados[i].y);
          ctx2d.lineTo(proyectados[j].x, proyectados[j].y);
          ctx2d.stroke();
        }
      }
    }

    for (const p of proyectados) {
      ctx2d.fillStyle = `rgba(0, 229, 195, ${p.brillo})`;
      const radioPunto = devicePixelRatio * (1.1 + nivelAudio * 1.4);
      ctx2d.beginPath();
      ctx2d.arc(p.x, p.y, radioPunto, 0, Math.PI * 2);
      ctx2d.fill();
    }
  }
  dibujar();

  // --- Audio: el panel reproduce la respuesta él mismo, conectado al
  // analizador para leer su amplitud en vivo y mover la esfera. ---
  let audioCtx;
  function obtenerAudioCtx() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    return audioCtx;
  }

  function reproducirRespuesta(base64, mime) {
    const ctxAudio = obtenerAudioCtx();
    const el = new Audio('data:' + (mime || 'audio/mpeg') + ';base64,' + base64);
    const fuente = ctxAudio.createMediaElementSource(el);
    const analizador = ctxAudio.createAnalyser();
    analizador.fftSize = 64;
    fuente.connect(analizador);
    analizador.connect(ctxAudio.destination);
    const datosFrec = new Uint8Array(analizador.frequencyBinCount);

    function actualizarNivel() {
      if (el.paused || el.ended) { objetivoAudio = 0; return; }
      analizador.getByteFrequencyData(datosFrec);
      const promedio = datosFrec.reduce((a, b) => a + b, 0) / datosFrec.length;
      objetivoAudio = Math.min(1, promedio / 90);
      requestAnimationFrame(actualizarNivel);
    }

    el.play().then(actualizarNivel).catch(() => {});
    el.onended = () => { objetivoAudio = 0; };
    window._audioActual = el;
  }

  // --- Envío de comandos ---
  const entrada = document.getElementById('entrada');
  const estadoTexto = document.getElementById('estado-texto');
  const caption = document.getElementById('caption');
  const botonMic = document.getElementById('boton-mic');
  const botonStop = document.getElementById('boton-stop');

  function marcarOcupado(ocupado) {
    estadoTexto.textContent = ocupado ? 'procesando...' : 'en línea';
    estadoTexto.classList.toggle('activo', ocupado);
  }

  async function enviarComando(texto) {
    if (!texto) return;
    caption.innerHTML = '<b>TÚ:</b> ' + texto;
    entrada.value = '';
    marcarOcupado(true);
    try {
      const resp = await fetch('/comando', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Jarvis-Token': obtenerToken() },
        body: JSON.stringify({ texto, reproducir_local: false }),
      });
      if (resp.status === 401) {
        const token = prompt('Este Jarvis requiere una clave de acceso:');
        if (token) { localStorage.setItem('jarvis_token', token); marcarOcupado(false); return enviarComando(texto); }
      }
      const datos = await resp.json();
      const nombresMotor = { kokoro: 'voz local: Kokoro', sistema: 'voz local: sistema' };
      const aviso = datos.voz_sistema ? ' (' + (nombresMotor[datos.motor_voz] || 'voz local') + ')' : '';
      caption.innerHTML = '<b>JARVIS:</b> ' + (datos.respuesta || '(sin respuesta)') + aviso;
      if (datos.audio_base64) reproducirRespuesta(datos.audio_base64, datos.audio_mime);
      actualizarEstado();
    } catch (e) {
      caption.innerHTML = '<b>JARVIS:</b> Error de conexión.';
    } finally {
      marcarOcupado(false);
    }
  }

  entrada.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter') enviarComando(entrada.value.trim());
  });

  document.querySelectorAll('.item[data-comando]').forEach((boton) => {
    boton.addEventListener('click', () => enviarComando(boton.dataset.comando));
  });

  botonStop.addEventListener('click', async () => {
    if (window._audioActual) window._audioActual.pause();
    objetivoAudio = 0;
    try { await fetch('/detener', { method: 'POST', headers: { 'X-Jarvis-Token': obtenerToken() } }); } catch (e) {}
  });

  document.getElementById('item-detener').addEventListener('click', () => botonStop.click());

  document.getElementById('boton-grafo-obsidian').addEventListener('click', () => enviarComando('abre el grafo de mis notas'));

  // --- Dictado por voz ---
  const MotorVoz = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (MotorVoz) {
    const reconocedor = new MotorVoz();
    reconocedor.lang = 'es-ES';
    reconocedor.interimResults = false;
    let escuchando = false;

    reconocedor.onstart = () => { escuchando = true; botonMic.classList.add('escuchando'); caption.textContent = 'Escuchando...'; };
    reconocedor.onend = () => { escuchando = false; botonMic.classList.remove('escuchando'); };
    reconocedor.onresult = (ev) => enviarComando(ev.results[0][0].transcript);
    reconocedor.onerror = (ev) => { caption.textContent = 'No pude escucharte (' + ev.error + ').'; };

    botonMic.addEventListener('click', () => {
      if (escuchando) { reconocedor.stop(); return; }
      try { reconocedor.start(); } catch (e) {}
    });
  } else {
    botonMic.disabled = true;
    botonMic.title = 'Tu navegador no soporta dictado por voz';
  }
</script>
</body>
</html>
"""


def crear_blueprint_panel():
    panel = Blueprint("panel", __name__)

    @panel.route("/panel", methods=["GET"])
    def vista_panel():
        return PAGINA_PANEL

    return panel
