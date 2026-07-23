"""Vista gráfica de tu bóveda de Obsidian (nodos + conexiones, como la Vista
Gráfica nativa de Obsidian) controlada con gestos de mano vía la cámara —
MediaPipe Hands (en el navegador, no toca tu Mac) detecta tu dedo índice y
pulgar: pellizca cerca de un nodo para arrastrarlo, pellizca con las DOS
manos a la vez en espacio vacío para hacer zoom.

Todo el renderizado del grafo es un canvas 2D con una simulación de físicas
simple escrita a mano (sin librería externa) — MediaPipe sí se carga desde
un CDN (necesita internet la primera vez; el navegador lo cachea después).

Si Brave no tiene permiso de cámara (Chromium exige su propio permiso de
sitio ADEMÁS del permiso de macOS), la página también acepta gestos de
`panel/camara_nativa.py` — un proceso de Python aparte que abre la cámara
directo con OpenCV/AVFoundation y le manda las manos detectadas a este
servidor por POST /grafico-obsidian/gesto. La página los lee con GET al
mismo endpoint y los trata igual que si vinieran de su propia cámara."""

import threading
import time

from flask import Blueprint, jsonify, request

from skills.grafico_obsidian import construir_grafo, leer_nota
from skills.obsidian import agregar_nota

_VENCIMIENTO_GESTO_SEGUNDOS = 1.0
_bloqueo_gesto = threading.Lock()
_ultimo_gesto = {"manos": [], "recibido_en": 0.0}

PAGINA_GRAFICO = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jarvis · Grafo de Obsidian</title>
<style>
  :root {
    --bg: #030507; --panel: #0b1017; --borde: #1c2530;
    --accent: #00e5c3; --accent-dim: #00e5c355;
    --texto: #d7e2ea; --texto-dim: #6b7684; --alerta: #ffb454; --user: #7aa2ff;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; overflow: hidden; background: var(--bg); }
  body { font-family: "SF Mono", "Menlo", "Consolas", monospace; color: var(--texto); }
  #grafo { position: absolute; inset: 0; display: block; }

  #encabezado {
    position: absolute; top: 0.8rem; left: 0.8rem; z-index: 5;
    background: var(--panel); border: 1px solid var(--borde); border-radius: 10px;
    padding: 0.6rem 0.9rem; max-width: 320px;
  }
  #encabezado h1 { margin: 0 0 0.3rem; font-size: 0.85rem; letter-spacing: 0.1em; color: var(--accent); }
  #encabezado p { margin: 0.15rem 0; font-size: 0.68rem; color: var(--texto-dim); line-height: 1.4; }
  #encabezado b { color: var(--texto); }

  #video { display: none; }
  #estado-camara {
    position: absolute; bottom: 0.8rem; right: 0.8rem; z-index: 5;
    background: var(--panel); border: 1px solid var(--borde); border-radius: 8px;
    font-size: 0.68rem; color: var(--texto-dim); padding: 0.5rem 0.8rem;
    text-transform: uppercase; letter-spacing: 0.06em;
  }
  #estado-camara.ok { color: var(--accent); border-color: var(--accent-dim); }
  #estado-camara.error { color: var(--alerta); }

  #panel-nota {
    position: absolute; top: 0.8rem; right: 0.8rem; bottom: 0.8rem; z-index: 6;
    width: min(360px, 40vw); display: none; flex-direction: column;
    background: var(--panel); border: 1px solid var(--borde); border-radius: 10px;
    padding: 0.9rem; overflow: hidden;
  }
  #panel-nota.abierto { display: flex; }
  #panel-nota .fila-titulo { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; }
  #panel-nota h2 { margin: 0; font-size: 0.85rem; color: var(--accent); word-break: break-word; }
  #panel-nota .cerrar {
    background: transparent; border: 1px solid var(--borde); border-radius: 6px;
    color: var(--texto-dim); cursor: pointer; font-family: inherit; font-size: 0.8rem;
    padding: 0.1rem 0.5rem; flex-shrink: 0;
  }
  #panel-nota .cerrar:hover { color: var(--texto); border-color: var(--texto-dim); }
  #panel-nota-contenido {
    margin-top: 0.6rem; overflow-y: auto; white-space: pre-wrap; word-break: break-word;
    font-size: 0.76rem; line-height: 1.5; color: var(--texto);
  }
  #panel-nota-contenido.vacia { color: var(--texto-dim); font-style: italic; }

  #boton-agregar-nota {
    position: absolute; bottom: 0.8rem; left: 0.8rem; z-index: 5;
    display: flex; align-items: center; gap: 0.4rem;
    background: var(--panel); border: 1px solid var(--borde); border-radius: 8px;
    color: var(--texto); font-family: inherit; font-size: 0.75rem;
    padding: 0.55rem 0.9rem; cursor: pointer;
  }
  #boton-agregar-nota:hover { border-color: var(--accent); color: var(--accent); }
  #boton-agregar-nota.escuchando { border-color: var(--user); color: var(--user); }
  #aviso-nota {
    position: absolute; bottom: 3.2rem; left: 0.8rem; z-index: 5;
    font-size: 0.68rem; color: var(--texto-dim); max-width: 260px; display: none;
  }
</style>
</head>
<body>

<canvas id="grafo"></canvas>

<div id="encabezado">
  <h1>GRAFO DE OBSIDIAN</h1>
  <p><b id="conteo-nodos">—</b> notas &middot; <b id="conteo-aristas">—</b> conexiones</p>
  <p>Pellizca cerca de un nodo y suelta rápido: ver su contenido.</p>
  <p>Pellizca cerca de un nodo y arrastra: moverlo.</p>
  <p>Pellizca en el aire y arrastra: mover la vista.</p>
  <p>Mano abierta, sin pellizcar: acércala o aléjala de la cámara para
    hacer zoom (o usa la rueda del mouse).</p>
  <p>Si el navegador tiene permiso de cámara, los nodos aparecen encima de
    tu propia imagen (realidad aumentada).</p>
  <p>Sin cámara en el navegador: corre <b>panel/camara_nativa.py</b> aparte,
    o usa el mouse (mismos gestos: clic, arrastrar, rueda).</p>
</div>

<video id="video" autoplay playsinline></video>
<div id="estado-camara">Pidiendo permiso de cámara...</div>

<div id="panel-nota">
  <div class="fila-titulo">
    <h2 id="panel-nota-titulo">—</h2>
    <button class="cerrar" id="cerrar-panel-nota">cerrar ✕</button>
  </div>
  <div id="panel-nota-contenido"></div>
</div>

<button id="boton-agregar-nota" title="Dicta una nota nueva para tu bóveda de Obsidian">
  <span>&#127908;</span>Agregar nota por voz
</button>
<div id="aviso-nota"></div>

<script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js" crossorigin="anonymous"></script>
<script>
// --- Canvas principal del grafo ---
const canvas = document.getElementById('grafo');
const ctx = canvas.getContext('2d');
function ajustarTamano() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener('resize', ajustarTamano);
ajustarTamano();

let nodos = [];
let aristas = [];
let mapaNodos = {};
let gradoPorNodo = {};

let zoom = 1;
let panX = 0, panY = 0;

// Declarados aquí (no más abajo, junto al resto de cámara/interacción) a
// propósito: dibujar() los usa y se llama de forma síncrona más abajo,
// antes de llegar a esas otras secciones — un `let`/`const` referenciado
// antes de su propia línea de declaración lanza ReferenceError (temporal
// dead zone) y mataba el loop de animación desde el primer frame, dejando
// el canvas en blanco para siempre aunque los datos sí llegaran bien.
let manosActuales = [];
const video = document.getElementById('video');
let camaraNavegadorActiva = false;  // true = hay video real que dibujar de fondo (estilo realidad aumentada)

let primeraCarga = true;

function cargarGrafo() {
  return fetch('/grafico-obsidian/datos.json').then((r) => r.json()).then((datos) => {
    document.getElementById('conteo-nodos').textContent = datos.nodes.length;
    document.getElementById('conteo-aristas').textContent = datos.edges.length;

    // Conserva la posición de los nodos que ya existían (si esto es un
    // refresco tras agregar una nota, no queremos que el grafo entero
    // vuelva a saltar a posiciones aleatorias).
    const posicionesPrevias = mapaNodos;
    nodos = datos.nodes.map((n) => {
      const previo = posicionesPrevias[n.id];
      return {
        id: n.id, existe: n.existe,
        x: previo ? previo.x : (Math.random() - 0.5) * 400,
        y: previo ? previo.y : (Math.random() - 0.5) * 400,
        vx: 0, vy: 0, fx: 0, fy: 0, sujetoPor: null,
      };
    });
    mapaNodos = {};
    nodos.forEach((n) => { mapaNodos[n.id] = n; });

    aristas = datos.edges.filter((a) => mapaNodos[a.origen] && mapaNodos[a.destino]);
    gradoPorNodo = {};
    aristas.forEach((a) => {
      gradoPorNodo[a.origen] = (gradoPorNodo[a.origen] || 0) + 1;
      gradoPorNodo[a.destino] = (gradoPorNodo[a.destino] || 0) + 1;
    });

    if (primeraCarga) {
      panX = canvas.width / 2;
      panY = canvas.height / 2;
      primeraCarga = false;
    }
  });
}
cargarGrafo();

// --- Físicas: repulsión entre todos los nodos + resortes en cada arista ---
const REPULSION = 2200;
const RIGIDEZ_RESORTE = 0.02;
const LONGITUD_IDEAL = 70;
const AMORTIGUACION = 0.85;
const VELOCIDAD_MAX = 12;

function pasoFisica() {
  for (let i = 0; i < nodos.length; i++) {
    nodos[i].fx = 0; nodos[i].fy = 0;
  }
  for (let i = 0; i < nodos.length; i++) {
    for (let j = i + 1; j < nodos.length; j++) {
      const a = nodos[i], b = nodos[j];
      const dx = a.x - b.x, dy = a.y - b.y;
      const distSq = dx * dx + dy * dy + 0.01;
      const dist = Math.sqrt(distSq);
      const f = REPULSION / distSq;
      const fx = (dx / dist) * f, fy = (dy / dist) * f;
      a.fx += fx; a.fy += fy;
      b.fx -= fx; b.fy -= fy;
    }
  }
  for (const arista of aristas) {
    const a = mapaNodos[arista.origen], b = mapaNodos[arista.destino];
    const dx = b.x - a.x, dy = b.y - a.y;
    const dist = Math.hypot(dx, dy) || 0.01;
    const fuerza = (dist - LONGITUD_IDEAL) * RIGIDEZ_RESORTE;
    const fx = (dx / dist) * fuerza, fy = (dy / dist) * fuerza;
    a.fx += fx; a.fy += fy;
    b.fx -= fx; b.fy -= fy;
  }
  for (const n of nodos) {
    if (n.sujetoPor !== null) continue;
    n.vx = (n.vx + n.fx * 0.02) * AMORTIGUACION;
    n.vy = (n.vy + n.fy * 0.02) * AMORTIGUACION;
    n.vx = Math.max(-VELOCIDAD_MAX, Math.min(VELOCIDAD_MAX, n.vx));
    n.vy = Math.max(-VELOCIDAD_MAX, Math.min(VELOCIDAD_MAX, n.vy));
    n.x += n.vx - n.x * 0.0006;
    n.y += n.vy - n.y * 0.0006;
  }
}

// --- Dibujo ---
// Tu propia cámara de fondo (si el navegador tiene permiso): los nodos
// quedan dibujados encima, estilo realidad aumentada, en vez de en una
// cajita aparte. Espejada para que coincida con el espacio "selfie" en el
// que ya se calculan las posiciones de las manos.
function dibujarFondoCamara() {
  if (!camaraNavegadorActiva || video.readyState < 2 || !video.videoWidth) return;
  try {
    ctx.save();
    ctx.scale(-1, 1);
    ctx.translate(-canvas.width, 0);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    ctx.restore();
    ctx.fillStyle = 'rgba(3, 5, 7, 0.5)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  } catch (e) {
    // Si drawImage falla por lo que sea (algunos navegadores no dejan
    // dibujar un <video> con display:none, por ejemplo), no te quedes sin
    // grafo por eso: apaga el fondo de cámara y sigue dibujando lo demás.
    camaraNavegadorActiva = false;
    console.error('[Jarvis] No pude dibujar el video de fondo, lo desactivo:', e);
  }
}

function dibujar() {
  // Blindado a propósito: un error en CUALQUIER parte de un cuadro (la
  // cámara de fondo, un dato raro, lo que sea) ya nos dejó el canvas en
  // blanco para siempre una vez (ver el commit que arregló el
  // ReferenceError de manosActuales) porque mataba este loop entero antes
  // de llegar al requestAnimationFrame de más abajo. Ahora, pase lo que
  // pase, el loop sigue vivo y los nodos se siguen intentando dibujar.
  try {
    pasoFisica();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    dibujarFondoCamara();

    ctx.save();
    ctx.translate(panX, panY);
    ctx.scale(zoom, zoom);

    ctx.strokeStyle = 'rgba(0,229,195,0.22)';
    ctx.lineWidth = 1 / zoom;
    for (const arista of aristas) {
      const a = mapaNodos[arista.origen], b = mapaNodos[arista.destino];
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    for (const n of nodos) {
      const grado = gradoPorNodo[n.id] || 1;
      const radio = Math.min(14, 3 + grado * 1.3);
      ctx.beginPath();
      ctx.arc(n.x, n.y, radio, 0, Math.PI * 2);
      ctx.fillStyle = n.sujetoPor !== null ? '#ffb454' : (n.existe ? '#00e5c3' : '#555f6b');
      ctx.fill();
      if (grado >= 2 || zoom > 1.2) {
        ctx.fillStyle = '#d7e2ea';
        ctx.font = (11 / zoom) + 'px monospace';
        ctx.fillText(n.id, n.x + radio + 3, n.y + 4);
      }
    }
    ctx.restore();

    for (const mano of manosActuales) {
      ctx.beginPath();
      ctx.arc(mano.x, mano.y, mano.pinzando ? 11 : 7, 0, Math.PI * 2);
      ctx.strokeStyle = mano.pinzando ? '#ffb454' : '#7aa2ff';
      ctx.lineWidth = 2.5;
      ctx.stroke();
    }
  } catch (e) {
    console.error('[Jarvis] Error dibujando un cuadro del grafo (sigo intentando el siguiente):', e);
  }

  requestAnimationFrame(dibujar);
}
dibujar();

// --- Interacción: TODO con una sola mano (compartido por gesto y mouse) ---
// Vocabulario de gestos:
//   · Pellizca (pulgar+índice) cerca de un nodo y suelta rápido, sin apenas
//     mover la mano  -> abre esa nota (equivalente a un clic).
//   · Pellizca cerca de un nodo y ARRASTRA                      -> lo mueve.
//   · Pellizca en el aire (lejos de cualquier nodo) y arrastra  -> mueve la
//     vista completa (paneo), como si agarraras el lienzo.
//   · Mano ABIERTA (sin pellizcar) y la acercas o alejas de la cámara
//     -> zoom in/out, usando el tamaño aparente de la mano en el cuadro
//     como distancia (más grande = más cerca = zoom in). No hace falta la
//     segunda mano para nada.
const sujetadoPorIndice = [null, null];
const paneandoDesdePorIndice = [null, null];
const pellizcoInicioPorIndice = [null, null];
const tamanoAnteriorPorIndice = [null, null];
const UMBRAL_TOQUE_PX = 15;
const UMBRAL_TOQUE_MS = 450;

function aScreenAWorld(x, y) {
  return { x: (x - panX) / zoom, y: (y - panY) / zoom };
}

function actualizarInteraccion(entradas) {
  // entradas: [{x, y, pinzando, tamano?}, ...] en espacio de PANTALLA.
  const ahora = performance.now();

  entradas.forEach((entrada, idx) => {
    const mundo = aScreenAWorld(entrada.x, entrada.y);

    if (entrada.pinzando) {
      tamanoAnteriorPorIndice[idx] = null;  // pellizcando no cuenta para el zoom

      if (sujetadoPorIndice[idx] === null && paneandoDesdePorIndice[idx] === null) {
        let mejor = null, mejorDist = 34 / zoom;
        for (const n of nodos) {
          const d = Math.hypot(n.x - mundo.x, n.y - mundo.y);
          if (d < mejorDist) { mejor = n; mejorDist = d; }
        }
        pellizcoInicioPorIndice[idx] = { x: entrada.x, y: entrada.y, t: ahora, nodoId: mejor ? mejor.id : null };
        if (mejor) {
          sujetadoPorIndice[idx] = mejor.id;
          mejor.sujetoPor = idx;
        } else {
          paneandoDesdePorIndice[idx] = { x: entrada.x, y: entrada.y };
        }
      }

      if (sujetadoPorIndice[idx] !== null) {
        const n = mapaNodos[sujetadoPorIndice[idx]];
        n.x = mundo.x; n.y = mundo.y; n.vx = 0; n.vy = 0;
      } else if (paneandoDesdePorIndice[idx] !== null) {
        panX += entrada.x - paneandoDesdePorIndice[idx].x;
        panY += entrada.y - paneandoDesdePorIndice[idx].y;
        paneandoDesdePorIndice[idx] = { x: entrada.x, y: entrada.y };
      }
      return;
    }

    // Se soltó el pellizco (o esta mano nunca estuvo pellizcando).
    if (sujetadoPorIndice[idx] !== null) mapaNodos[sujetadoPorIndice[idx]].sujetoPor = null;

    const inicio = pellizcoInicioPorIndice[idx];
    if (inicio && inicio.nodoId) {
      const distanciaMovida = Math.hypot(entrada.x - inicio.x, entrada.y - inicio.y);
      if (distanciaMovida < UMBRAL_TOQUE_PX && (ahora - inicio.t) < UMBRAL_TOQUE_MS) {
        mostrarNota(inicio.nodoId);  // fue un toque, no un arrastre: abre la nota
      }
    }
    sujetadoPorIndice[idx] = null;
    paneandoDesdePorIndice[idx] = null;
    pellizcoInicioPorIndice[idx] = null;

    // Zoom con una sola mano abierta: compara el tamaño de la mano en este
    // cuadro contra el del cuadro anterior. Solo con UNA mano visible, para
    // no pelearse con la otra si algún día hay dos en pantalla.
    if (entradas.length === 1 && entrada.tamano) {
      if (tamanoAnteriorPorIndice[idx] !== null) {
        const factor = entrada.tamano / tamanoAnteriorPorIndice[idx];
        zoom = Math.max(0.3, Math.min(3, zoom * Math.pow(factor, 0.6)));
      }
      tamanoAnteriorPorIndice[idx] = entrada.tamano;
    } else {
      tamanoAnteriorPorIndice[idx] = null;
    }
  });
}

// --- Respaldo con mouse (por si no hay cámara o no la quieres usar) ---
// Pasa por la MISMA actualizarInteraccion de arriba: arrastrar nodos, hacer
// clic para ver una nota, y arrastrar en vacío para mover la vista también
// funcionan con el mouse, gratis, al ser el mismo código.
let manoMouse = { x: 0, y: 0, pinzando: false };
canvas.addEventListener('mousemove', (ev) => { manoMouse.x = ev.clientX; manoMouse.y = ev.clientY; });
canvas.addEventListener('mousedown', () => { manoMouse.pinzando = true; });
window.addEventListener('mouseup', () => { manoMouse.pinzando = false; });

// --- Zoom con la rueda del mouse (respaldo directo, sin gestos) ---
canvas.addEventListener('wheel', (ev) => {
  ev.preventDefault();
  const factor = ev.deltaY < 0 ? 1.1 : 1 / 1.1;
  zoom = Math.max(0.3, Math.min(3, zoom * factor));
}, { passive: false });

const panelNota = document.getElementById('panel-nota');
const panelNotaTitulo = document.getElementById('panel-nota-titulo');
const panelNotaContenido = document.getElementById('panel-nota-contenido');

function mostrarNota(id) {
  panelNotaTitulo.textContent = id;
  panelNotaContenido.textContent = 'Cargando...';
  panelNotaContenido.classList.remove('vacia');
  panelNota.classList.add('abierto');

  fetch('/grafico-obsidian/nota?id=' + encodeURIComponent(id)).then((r) => r.json()).then((datos) => {
    if (!datos.existe) {
      panelNotaContenido.textContent = 'Esta nota todavía no existe — es solo una referencia desde otra nota.';
      panelNotaContenido.classList.add('vacia');
    } else {
      panelNotaContenido.textContent = datos.contenido || '(nota vacía)';
      panelNotaContenido.classList.toggle('vacia', !datos.contenido);
    }
  }).catch(() => {
    panelNotaContenido.textContent = 'No pude cargar el contenido.';
    panelNotaContenido.classList.add('vacia');
  });
}

document.getElementById('cerrar-panel-nota').addEventListener('click', () => {
  panelNota.classList.remove('abierto');
});

// --- Gestos de la app nativa (panel/camara_nativa.py), si está corriendo ---
// Cuando Brave no tiene permiso de cámara, esta es la fuente real de manos:
// la app nativa abre la cámara ella misma (fuera del navegador) y manda lo
// que ve por POST a este mismo servidor; aquí solo lo leemos por polling.
let manosNativas = [];
let appNativaConectada = false;
setInterval(() => {
  fetch('/grafico-obsidian/gesto').then((r) => r.json()).then((datos) => {
    manosNativas = (datos.manos || []).map((m) => ({
      x: m.x * canvas.width, y: m.y * canvas.height, pinzando: !!m.pinzando, tamano: m.tamano || 0,
    }));
    appNativaConectada = datos.activa;
  }).catch(() => { appNativaConectada = false; });
}, 1000 / 15);

setInterval(() => {
  // Prioridad: cámara del navegador > app nativa > mouse.
  const entradas = manosActuales.length > 0 ? manosActuales
    : manosNativas.length > 0 ? manosNativas
    : [manoMouse];
  actualizarInteraccion(entradas);
}, 1000 / 30);

// --- Cámara + MediaPipe Hands ---
// El video ya NO se dibuja aparte en una cajita: se mete de fondo en el
// canvas principal (ver dibujar()) para que los nodos aparezcan encima de
// tu propia cámara, estilo realidad aumentada — y los puntitos de las
// manos (ver el loop de "manosActuales" en dibujar()) también quedan sobre
// el video real en vez de en un recuadro chico aparte.
const estadoCamara = document.getElementById('estado-camara');
const UMBRAL_PINZA_PX = 40;

function onResultadosManos(resultados) {
  manosActuales = [];
  if (resultados.multiHandLandmarks) {
    for (const puntos of resultados.multiHandLandmarks) {
      const pulgar = puntos[4], indice = puntos[8];
      // Espejo horizontal: cámara "selfie", movimiento natural.
      const xIndice = (1 - indice.x) * canvas.width;
      const yIndice = indice.y * canvas.height;
      const xPulgar = (1 - pulgar.x) * canvas.width;
      const yPulgar = pulgar.y * canvas.height;
      const distPinza = Math.hypot(xIndice - xPulgar, yIndice - yPulgar);

      // Tamaño de la mano en el cuadro (muñeca a base del dedo medio, en
      // espacio normalizado 0..1) — más grande cuanto más cerca de la
      // cámara la tengas. Sirve como "control de zoom" con una sola mano.
      const muneca = puntos[0], baseMedio = puntos[9];
      const tamanoMano = Math.hypot(baseMedio.x - muneca.x, baseMedio.y - muneca.y);

      manosActuales.push({ x: xIndice, y: yIndice, pinzando: distPinza < UMBRAL_PINZA_PX, tamano: tamanoMano });
    }
  }
}

async function iniciarCamara() {
  try {
    const hands = new Hands({
      locateFile: (archivo) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${archivo}`,
    });
    hands.setOptions({ maxNumHands: 2, modelComplexity: 1, minDetectionConfidence: 0.6, minTrackingConfidence: 0.5 });
    hands.onResults(onResultadosManos);

    const camara = new Camera(video, {
      onFrame: async () => { await hands.send({ image: video }); },
      width: 640, height: 480,
    });
    await camara.start();

    camaraNavegadorActiva = true;
    estadoCamara.textContent = 'Cámara del navegador activa — detectando manos';
    estadoCamara.className = 'ok';
  } catch (e) {
    camaraNavegadorActiva = false;
    estadoCamara.textContent = 'Sin permiso de cámara en el navegador...';
    estadoCamara.className = 'error';
  }
}
iniciarCamara();

// Si el navegador no tiene cámara pero la app nativa sí está mandando datos,
// que el estado lo refleje (se re-evalúa cada vez que llega un gesto nuevo).
setInterval(() => {
  if (manosActuales.length > 0) return;  // la cámara del navegador manda, no pisar ese estado
  if (appNativaConectada) {
    estadoCamara.textContent = 'Usando panel/camara_nativa.py — detectando manos';
    estadoCamara.className = 'ok';
  } else if (estadoCamara.className === 'error') {
    estadoCamara.textContent = 'Sin cámara (corre panel/camara_nativa.py o usa el mouse)';
  }
}, 500);

// --- Agregar nota por voz (dictado con la Web Speech API del navegador) ---
const botonAgregarNota = document.getElementById('boton-agregar-nota');
const avisoNota = document.getElementById('aviso-nota');

function mostrarAvisoNota(texto, duracionMs) {
  avisoNota.textContent = texto;
  avisoNota.style.display = 'block';
  clearTimeout(avisoNota._temporizador);
  avisoNota._temporizador = setTimeout(() => { avisoNota.style.display = 'none'; }, duracionMs || 4000);
}

function guardarNotaDictada(texto) {
  mostrarAvisoNota('Guardando: "' + texto + '"...', 6000);
  fetch('/grafico-obsidian/nota', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ texto }),
  }).then((r) => r.json()).then((datos) => {
    mostrarAvisoNota(datos.mensaje || (datos.ok ? 'Nota guardada.' : 'No pude guardar la nota.'));
    if (datos.ok) cargarGrafo();
  }).catch(() => mostrarAvisoNota('Error de conexión al guardar la nota.'));
}

const MotorVozNota = window.SpeechRecognition || window.webkitSpeechRecognition;
if (MotorVozNota) {
  const reconocedorNota = new MotorVozNota();
  reconocedorNota.lang = 'es-ES';
  reconocedorNota.interimResults = false;
  reconocedorNota.maxAlternatives = 1;
  let escuchandoNota = false;

  reconocedorNota.onstart = () => {
    escuchandoNota = true;
    botonAgregarNota.classList.add('escuchando');
    mostrarAvisoNota('Escuchando... dicta tu nota.', 8000);
  };
  reconocedorNota.onend = () => {
    escuchandoNota = false;
    botonAgregarNota.classList.remove('escuchando');
  };
  reconocedorNota.onresult = (ev) => guardarNotaDictada(ev.results[0][0].transcript);
  reconocedorNota.onerror = (ev) => mostrarAvisoNota('No pude escucharte (' + ev.error + ').');

  botonAgregarNota.addEventListener('click', () => {
    if (escuchandoNota) { reconocedorNota.stop(); return; }
    try { reconocedorNota.start(); } catch (e) { /* ya estaba iniciando */ }
  });
} else {
  botonAgregarNota.disabled = true;
  botonAgregarNota.title = 'Tu navegador no soporta dictado por voz';
}
</script>
</body>
</html>
"""


def crear_blueprint_grafico():
    grafico = Blueprint("grafico_obsidian", __name__)

    @grafico.route("/grafico-obsidian", methods=["GET"])
    def vista_grafico():
        return PAGINA_GRAFICO

    @grafico.route("/grafico-obsidian/datos.json", methods=["GET"])
    def datos_grafico():
        return jsonify(construir_grafo())

    @grafico.route("/grafico-obsidian/gesto", methods=["POST"])
    def recibir_gesto():
        """panel/camara_nativa.py llama aquí en cada cuadro con las manos que
        detectó, para que la página del grafo (que puede no tener permiso de
        cámara en el navegador) las use igual."""
        cuerpo = request.get_json(silent=True) or {}
        with _bloqueo_gesto:
            _ultimo_gesto["manos"] = cuerpo.get("manos", [])
            _ultimo_gesto["recibido_en"] = time.monotonic()
        return jsonify(ok=True)

    @grafico.route("/grafico-obsidian/gesto", methods=["GET"])
    def leer_gesto():
        """La página del grafo hace polling aquí. Si no ha llegado nada
        reciente (la app nativa no está corriendo, o se cerró), se reporta
        como inactiva para no dejar manos fantasma congeladas en pantalla."""
        with _bloqueo_gesto:
            vencido = (time.monotonic() - _ultimo_gesto["recibido_en"]) > _VENCIMIENTO_GESTO_SEGUNDOS
            manos = [] if vencido else _ultimo_gesto["manos"]
            activa = not vencido and _ultimo_gesto["recibido_en"] > 0
        return jsonify(manos=manos, activa=activa)

    @grafico.route("/grafico-obsidian/nota", methods=["GET"])
    def ver_nota():
        """Contenido de la nota que se clickeó en el grafo. `id` va en la
        query string (no en la ruta) porque los nombres de nota traen
        espacios y acentos que no vale la pena pelearse con encodear en un
        path segment."""
        nombre = request.args.get("id", "")
        contenido = leer_nota(nombre)
        if contenido is None:
            return jsonify(existe=False, contenido=None)
        return jsonify(existe=True, contenido=contenido)

    @grafico.route("/grafico-obsidian/nota", methods=["POST"])
    def crear_nota():
        """Agrega una nota dictada desde la propia vista del grafo (mismo
        comportamiento que decirle "agrega una nota..." por voz)."""
        cuerpo = request.get_json(silent=True) or {}
        texto = (cuerpo.get("texto") or "").strip()
        if not texto:
            return jsonify(ok=False, mensaje="No hay nada que guardar."), 400
        mensaje = agregar_nota(texto)
        return jsonify(ok=True, mensaje=mensaje)

    return grafico
