"""Búsqueda de texto simple sobre tus bóvedas de Obsidian, para darle
contexto a Ollama (mismo patrón que la búsqueda web: no es IA, es grep).

Tienes dos bóvedas detectadas en tu Mac; ajusta esta lista si tienes más o
si alguna cambia de lugar.
"""

import os
from datetime import datetime

from core.texto import normalizar

RUTAS_VAULTS = [
    os.path.expanduser("~/Documents/Obsidian Vault"),
    os.path.expanduser("~/Desktop/UTCH TRABAJOS"),
]

VAULT_PARA_ESCRIBIR = RUTAS_VAULTS[0]  # dónde caen las notas nuevas por voz
ARCHIVO_NOTAS_RAPIDAS = "Notas de Jarvis.md"

EXTENSIONES_VALIDAS = (".md",)
MAX_ARCHIVOS_RESULTADO = 5
MAX_CARACTERES_POR_ARCHIVO = 800

# Palabras demasiado comunes como para servir de filtro por sí solas —
# sin esto, buscar "qué anoté sobre X" haría match con CUALQUIER nota
# solo por contener "que" o "sobre".
PALABRAS_VACIAS = {
    "que", "no", "los", "las", "una", "uno", "por", "con", "para", "esta",
    "esto", "eso", "algo", "sobre", "del", "mis", "mi", "en", "de", "la",
    "el", "y", "a", "un", "se", "su", "sus", "al", "lo", "tus", "tu",
}


def _listar_archivos_md():
    for vault in RUTAS_VAULTS:
        if not os.path.isdir(vault):
            continue
        for raiz, carpetas, archivos in os.walk(vault):
            carpetas[:] = [c for c in carpetas if not c.startswith(".")]
            for nombre in archivos:
                if nombre.endswith(EXTENSIONES_VALIDAS):
                    yield os.path.join(raiz, nombre)


def buscar_en_obsidian(consulta):
    """Búsqueda por palabras clave (no semántica) sobre los .md de tus
    bóvedas. Devuelve fragmentos de los archivos que mencionan la consulta,
    o None si no hay bóvedas configuradas o no encontró nada.

    Compara todo normalizado (sin tildes, sin mayúsculas) — sin esto, buscar
    "quien" nunca encuentra un encabezado escrito "Quién" en la nota real.
    También cuenta como coincidencia si las palabras aparecen en el NOMBRE
    del archivo, no solo en su contenido (ej. tu nota "Perfil.md" puede no
    repetir la palabra "perfil" ni una vez en el cuerpo del texto)."""
    palabras = [p for p in normalizar(consulta).split() if len(p) > 2 and p not in PALABRAS_VACIAS]
    if not palabras:
        return None

    coincidencias = []
    for ruta in _listar_archivos_md():
        try:
            with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                contenido = f.read()
        except OSError:
            continue

        nombre_archivo = os.path.splitext(os.path.basename(ruta))[0]
        contenido_norm = normalizar(contenido)
        nombre_norm = normalizar(nombre_archivo)

        # Exige TODAS las palabras (no cualquiera) para ser preciso, pero
        # basta con que aparezcan en el contenido O en el nombre del archivo.
        coincide_contenido = all(palabra in contenido_norm for palabra in palabras)
        coincide_nombre = all(palabra in nombre_norm for palabra in palabras)

        if coincide_contenido or coincide_nombre:
            fragmento = contenido.strip()[:MAX_CARACTERES_POR_ARCHIVO]
            coincidencias.append(f"### {nombre_archivo}\n{fragmento}")

        if len(coincidencias) >= MAX_ARCHIVOS_RESULTADO:
            break

    if not coincidencias:
        return None

    return "\n\n".join(coincidencias)


def agregar_nota(texto):
    """Anexa una nota con marca de tiempo a un .md general de tu bóveda
    principal (distinto del archivo específico de ideas de universidad)."""
    if not texto or not texto.strip():
        return "No escuché la nota, inténtalo de nuevo."

    try:
        os.makedirs(VAULT_PARA_ESCRIBIR, exist_ok=True)
        ruta = os.path.join(VAULT_PARA_ESCRIBIR, ARCHIVO_NOTAS_RAPIDAS)
        marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(f"\n- **[{marca_tiempo}]** {texto.strip()}\n")
        return "Nota agregada a tu bóveda de Obsidian."
    except OSError as e:
        return f"No pude guardar la nota: {e}"
