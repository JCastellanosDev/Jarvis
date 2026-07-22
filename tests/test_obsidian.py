"""Regresión del bug real: la búsqueda usaba la frase completa como palabras
clave (incluía "que", "en", "no", "algo"), así que casi cualquier nota
calificaba como resultado. Ahora exige TODAS las palabras (sin las vacías)."""

from unittest.mock import patch

from skills.obsidian import buscar_en_obsidian


def _con_archivos_falsos(mapa_archivos, funcion_bajo_prueba, *args):
    """mapa_archivos: {ruta: contenido}. Simula _listar_archivos_md() y las
    lecturas de archivo sin tocar el disco real."""
    def _open_falso(ruta, *a, **kw):
        from unittest.mock import mock_open
        return mock_open(read_data=mapa_archivos[ruta])(*a, **kw)

    with patch("skills.obsidian._listar_archivos_md", return_value=list(mapa_archivos.keys())), \
         patch("builtins.open", side_effect=_open_falso):
        return funcion_bajo_prueba(*args)


def test_no_matchea_solo_por_palabras_vacias():
    """El bug exacto: antes, "busca ... sobre algo que definitivamente no
    existe" encontraba resultados solo porque "que"/"no"/"algo" están en
    cualquier nota."""
    archivos = {"/vault/nota1.md": "Contenido normal sin relación con la búsqueda."}
    resultado = _con_archivos_falsos(archivos, buscar_en_obsidian, "algo que definitivamente no existe xyz123")
    assert resultado is None


def test_matchea_tema_real():
    archivos = {
        "/vault/videojuegos.md": "Mis videojuegos favoritos son Zelda y Elden Ring.",
        "/vault/comida.md": "Receta de tacos al pastor.",
    }
    resultado = _con_archivos_falsos(archivos, buscar_en_obsidian, "videojuegos")
    assert resultado is not None
    assert "videojuegos" in resultado.lower()
    assert "tacos" not in resultado.lower()


def test_exige_todas_las_palabras_no_cualquiera():
    archivos = {"/vault/nota.md": "Habla de Python pero no menciona el otro tema para nada."}
    # Pide dos palabras; la nota solo tiene una -> no debe matchear.
    resultado = _con_archivos_falsos(archivos, buscar_en_obsidian, "python javascript")
    assert resultado is None


def test_ignora_acentos_en_contenido():
    """Bug real: buscar 'quien' no encontraba un encabezado escrito 'Quién'
    porque la comparación era sensible a tildes."""
    archivos = {"/vault/perfil.md": "## Quién Soy\nMe llamo Jesús."}
    resultado = _con_archivos_falsos(archivos, buscar_en_obsidian, "quien soy")
    assert resultado is not None


def test_matchea_por_nombre_de_archivo_aunque_no_este_en_el_contenido():
    """Bug real: una nota llamada 'Perfil.md' cuyo cuerpo nunca repite la
    palabra 'perfil' no aparecía en resultados — solo se buscaba en contenido."""
    archivos = {"/vault/Perfil.md": "Nombre: Jesús. Edad: 22. Ubicación: Chihuahua."}
    resultado = _con_archivos_falsos(archivos, buscar_en_obsidian, "perfil")
    assert resultado is not None
    assert "Perfil" in resultado
