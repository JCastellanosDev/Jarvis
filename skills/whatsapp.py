"""Automatiza WhatsApp Desktop por completo: busca el contacto, abre el
chat, escribe el mensaje y lo ENVÍA sin pedir confirmación.

ADVERTENCIA — leíste el riesgo y decidiste seguir con esto de todos modos:
WhatsApp Desktop no es scriptable de forma nativa (no tiene diccionario de
AppleScript), así que esto simula clics reales vía System Events
(Accesibilidad). Es inherentemente frágil:
  - Si WhatsApp cambia su interfaz en una actualización, esto se rompe.
  - Si la búsqueda del contacto no da como primer resultado exactamente a
    quien esperabas, el mensaje puede irse a la persona equivocada.
  - No lo pude probar en vivo contra la interfaz real (este entorno no tiene
    permiso de Accesibilidad profundo) — los tiempos de espera (`delay`)
    son estimados.

Historial de por qué está hecho así (para no repetir los mismos bugs):
  1ra versión: `keystroke "Tú"` escribía "ta" — problema típico de
  `keystroke` con acentos, depende del layout de teclado.
  2da versión: portapapeles + pegar, pero incrustando el texto ACENTUADO
  directo en el string del AppleScript — seguía escribiendo "ta", porque el
  problema real era de codificación al construir el script en Python.
  3ra versión: pbcopy + pegar, con el AppleScript en ASCII puro — esto SÍ
  escribió "Tú" correctamente. Pero la verificación de seguridad comparaba
  contra `name of window 1`, y WhatsApp Desktop mantiene el título de la
  ventana fijo en "WhatsApp" sin importar qué chat esté abierto — así que
  SIEMPRE abortaba diciendo "se abrió WhatsApp en vez de Tú", aunque el chat
  correcto sí se hubiera abierto.
  4ta versión: en vez de mirar el título de la ventana, recorre TODOS los
  elementos de accesibilidad de la ventana buscando el nombre del contacto
  en algún lado. El nombre se pasa como VARIABLE DE ENTORNO al proceso de
  osascript (`system attribute` en AppleScript), no incrustado en el script
  — evita de nuevo el problema de codificación de la 2da versión. PERO esta
  versión seguía navegando el resultado de la búsqueda con flecha-abajo +
  Return (`key code 125` + `keystroke return`) — funciona en listas nativas
  de macOS, pero WhatsApp Desktop es una app Electron y su lista de
  resultados de búsqueda no siempre le da el foco de teclado a esas flechas:
  el chat nunca se abría, y como nunca se abrió, tampoco había dónde escribir
  el mensaje (mismo síntoma reportado dos veces: "no selecciona el contacto"
  y "no escribe el mensaje" eran UN solo bug, no dos).
  5ta versión (esta): en vez de navegar por teclado, se busca en el árbol de
  accesibilidad el elemento cuyo valor contiene el nombre buscado (evitando
  el propio campo de búsqueda) y se hace CLIC REAL ahí (`click at {x, y}` de
  System Events, sobre las coordenadas del elemento) — un clic de verdad
  funciona igual sin importar cómo Electron exponga el foco de teclado.
  Antes de escribir el mensaje, se busca y clickea explícitamente la caja de
  texto del chat (rol "AXTextArea") en vez de asumir que el foco ya está ahí
  después de abrir el chat.

Requiere: Configuración del Sistema → Privacidad y Seguridad → Accesibilidad
→ dar permiso a Terminal (o a la app que lance jarvis.py).

No lo pude probar en vivo contra la interfaz real de tu WhatsApp (este
entorno no tiene acceso a tu Mac) — si el clic no cae exactamente sobre la
fila de resultado o la caja de texto no se detecta con rol "AXTextArea",
dímelo con el mensaje de error que te devuelva Jarvis para ajustar esto.
"""

import os
import subprocess

# Agrega aquí los contactos a los que le mandas mensajes seguido. La clave va
# en MINÚSCULAS (así se compara: nombre_contacto.lower()); el valor es el
# nombre EXACTO tal como aparece en tu lista de chats de WhatsApp.
CONTACTOS = {
    # "angel": "Angel Pérez",
    # "chuy": "Chuy",
    "mama": "Mama",
    "prueba": "Tú",  # "Mensajes a mí mismo" — VERIFICA este nombre contra tu lista real de chats antes de probar
}

_TIMEOUT_OSASCRIPT = 25

# Busca el contacto y hace CLIC REAL sobre el resultado (en vez de navegar
# con flecha-abajo + Return, que no siempre le da el foco a la lista de
# resultados de WhatsApp por ser una app Electron). Devuelve "OK_ENCONTRADO"
# / "NO_ENCONTRADO" según si el nombre aparece en la ventana tras el clic.
_SCRIPT_BUSCAR_Y_ABRIR = '''
set nombreBuscado to system attribute "JARVIS_WA_NOMBRE"

tell application "WhatsApp" to activate
delay 1

set filaX to -1
set filaY to -1
tell application "System Events"
    tell process "WhatsApp"
        keystroke "f" using command down
        delay 0.5
        keystroke "v" using command down
        delay 1.2

        try
            set todosLosElementos to entire contents of window 1
            repeat with elem in todosLosElementos
                try
                    if role of elem is not "AXTextField" then
                        if (value of elem as text) contains nombreBuscado then
                            set {posX, posY} to position of elem
                            set {anchoW, altoH} to size of elem
                            set filaX to posX + (anchoW / 2)
                            set filaY to posY + (altoH / 2)
                            exit repeat
                        end if
                    end if
                end try
            end repeat
        end try
    end tell
end tell

if filaX is -1 then
    return "NO_ENCONTRADO"
end if

tell application "System Events" to click at {filaX, filaY}
delay 1

tell application "System Events"
    tell process "WhatsApp"
        set encontrado to false
        try
            set elementosChat to entire contents of window 1
            repeat with elem2 in elementosChat
                try
                    if (value of elem2 as text) contains nombreBuscado then
                        set encontrado to true
                        exit repeat
                    end if
                end try
            end repeat
        end try

        if encontrado then
            return "OK_ENCONTRADO"
        else
            return "NO_ENCONTRADO"
        end if
    end tell
end tell
'''

# Clickea la caja de texto del chat ANTES de pegar el mensaje — no asume que
# el foco ya quedó ahí después de abrir el chat (ese supuesto era parte del
# bug: si el clic anterior no abrió el chat, tampoco había caja de texto
# enfocada, y "escribir" el mensaje no iba a ningún lado).
_SCRIPT_ESCRIBIR_Y_ENVIAR = '''
set cajaX to -1
set cajaY to -1
tell application "System Events"
    tell process "WhatsApp"
        try
            set todosLosElementos to entire contents of window 1
            repeat with elem in todosLosElementos
                try
                    if role of elem is "AXTextArea" then
                        set {posX, posY} to position of elem
                        set {anchoW, altoH} to size of elem
                        set cajaX to posX + (anchoW / 2)
                        set cajaY to posY + (altoH / 2)
                        exit repeat
                    end if
                end try
            end repeat
        end try
    end tell
end tell

if cajaX is not -1 then
    tell application "System Events" to click at {cajaX, cajaY}
    delay 0.3
end if

tell application "System Events"
    tell process "WhatsApp"
        keystroke "v" using command down
        delay 0.3
        keystroke return
    end tell
end tell
'''


def _leer_portapapeles():
    try:
        resultado = subprocess.run(["pbpaste"], capture_output=True, timeout=5)
        return resultado.stdout
    except Exception:
        return b""


def _escribir_portapapeles(texto):
    subprocess.run(["pbcopy"], input=texto.encode("utf-8"), timeout=5)


def _restaurar_portapapeles(contenido_original):
    subprocess.run(["pbcopy"], input=contenido_original, timeout=5)


def _ejecutar_applescript(script, variables_env=None):
    """El script debe ser SIEMPRE ASCII puro — cualquier texto con acentos
    va por portapapeles (para lo que se ESCRIBE) o por variable de entorno
    (para lo que el propio AppleScript necesita COMPARAR), nunca incrustado
    literalmente en el código fuente."""
    entorno = os.environ.copy()
    if variables_env:
        entorno.update(variables_env)
    return subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True,
        timeout=_TIMEOUT_OSASCRIPT, env=entorno,
    )


def enviar_whatsapp(nombre_contacto, mensaje):
    nombre_buscado = CONTACTOS.get(nombre_contacto.lower())
    if not nombre_buscado:
        disponibles = ", ".join(CONTACTOS.keys()) or "ninguno todavía"
        return (
            f"No tengo guardado a {nombre_contacto}. Agrégalo en "
            f"skills/whatsapp.py (CONTACTOS). Disponibles: {disponibles}."
        )

    portapapeles_original = _leer_portapapeles()

    try:
        # 1. Buscar y abrir el chat del contacto, y verificar que sí es el
        # correcto buscando su nombre en cualquier parte de la ventana (no
        # en el título — WhatsApp Desktop mantiene el título fijo en
        # "WhatsApp" sin importar qué chat esté abierto).
        _escribir_portapapeles(nombre_buscado)
        resultado = _ejecutar_applescript(
            _SCRIPT_BUSCAR_Y_ABRIR, variables_env={"JARVIS_WA_NOMBRE": nombre_buscado}
        )

        if resultado.returncode != 0:
            return (
                f"No pude automatizar WhatsApp: {resultado.stderr.strip()}. "
                "¿Le diste permiso de Accesibilidad a Terminal en Configuración "
                "del Sistema → Privacidad y Seguridad?"
            )

        if resultado.stdout.strip() != "OK_ENCONTRADO":
            return (
                f"No mandé nada por seguridad: no encontré '{nombre_buscado}' en la "
                "ventana de WhatsApp tras buscarlo. Puede que se haya abierto el chat "
                "equivocado, o que la búsqueda no encontrara nada."
            )

        # 2. Escribir y enviar el mensaje en el chat ya abierto.
        _escribir_portapapeles(mensaje)
        resultado2 = _ejecutar_applescript(_SCRIPT_ESCRIBIR_Y_ENVIAR)

        if resultado2.returncode != 0:
            return f"Abrí el chat de {nombre_contacto} pero no pude mandar el mensaje: {resultado2.stderr.strip()}"

        return f"Mensaje enviado a {nombre_contacto} por WhatsApp."

    finally:
        _restaurar_portapapeles(portapapeles_original)
