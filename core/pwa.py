"""Fragmentos compartidos para que las páginas de Jarvis se puedan "Agregar a
pantalla de inicio" en el celular como si fueran una app nativa — ícono
propio, sin barra de direcciones del navegador — en vez de tener que abrir
Brave y escribir la IP y el puerto cada vez."""

ICONO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="24" fill="#05070a"/>
  <circle cx="64" cy="64" r="46" fill="none" stroke="#00e5c3" stroke-width="4"/>
  <text x="64" y="82" font-family="Menlo, monospace" font-size="56" font-weight="bold"
        fill="#00e5c3" text-anchor="middle">J</text>
</svg>"""

META_TAGS_PWA = """
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#00e5c3">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="apple-touch-icon" href="/icono.svg">
"""


def manifest_json(nombre, nombre_corto):
    return {
        "name": nombre,
        "short_name": nombre_corto,
        "start_url": "/",
        "display": "standalone",
        "background_color": "#05070a",
        "theme_color": "#00e5c3",
        "icons": [{"src": "/icono.svg", "sizes": "any", "type": "image/svg+xml"}],
    }


def registrar_rutas_pwa(app, nombre, nombre_corto):
    """Agrega /manifest.json y /icono.svg a una app Flask ya creada."""
    from flask import jsonify, Response

    @app.route("/manifest.json", methods=["GET"])
    def _manifest():
        return jsonify(manifest_json(nombre, nombre_corto))

    @app.route("/icono.svg", methods=["GET"])
    def _icono():
        return Response(ICONO_SVG, mimetype="image/svg+xml")
