"""construir_grafo() reconstruye a mano lo que la Vista Gráfica nativa de
Obsidian ya sabe (nodos = notas, aristas = wikilinks [[...]])."""

from unittest.mock import patch

from skills.grafico_obsidian import construir_grafo


def _con_archivos_falsos(mapa_archivos):
    def _open_falso(ruta, *a, **kw):
        from unittest.mock import mock_open
        return mock_open(read_data=mapa_archivos[ruta])(*a, **kw)

    return patch("skills.grafico_obsidian._listar_archivos_md", return_value=list(mapa_archivos.keys())), \
        patch("builtins.open", side_effect=_open_falso)


def test_nota_sin_links_es_nodo_aislado():
    archivos = {"/vault/sola.md": "No menciona a nadie."}
    with _con_archivos_falsos(archivos)[0], _con_archivos_falsos(archivos)[1]:
        g = construir_grafo()
    assert g["nodes"] == [{"id": "sola", "existe": True}]
    assert g["edges"] == []


def test_wikilink_simple_crea_arista():
    archivos = {
        "/vault/a.md": "Habla de [[b]] en este texto.",
        "/vault/b.md": "Nota B, sin links.",
    }
    p1, p2 = _con_archivos_falsos(archivos)
    with p1, p2:
        g = construir_grafo()
    ids = {n["id"] for n in g["nodes"]}
    assert ids == {"a", "b"}
    assert g["edges"] == [{"origen": "a", "destino": "b"}]


def test_link_a_nota_que_no_existe_se_marca_como_no_existente():
    archivos = {"/vault/a.md": "Referencia a [[nota fantasma]] que no existe."}
    p1, p2 = _con_archivos_falsos(archivos)
    with p1, p2:
        g = construir_grafo()
    fantasma = next(n for n in g["nodes"] if n["id"] == "nota fantasma")
    real = next(n for n in g["nodes"] if n["id"] == "a")
    assert fantasma["existe"] is False
    assert real["existe"] is True


def test_alias_y_encabezados_se_ignoran_en_el_link():
    """[[Nota|Alias]] y [[Nota#Encabezado]] deben apuntar a "Nota", no al
    alias ni al encabezado."""
    archivos = {
        "/vault/a.md": "Ve [[b|texto alterno]] y también [[b#sección uno]].",
        "/vault/b.md": "Nota B.",
    }
    p1, p2 = _con_archivos_falsos(archivos)
    with p1, p2:
        g = construir_grafo()
    destinos = {a["destino"] for a in g["edges"]}
    assert destinos == {"b"}


def test_no_hay_auto_enlaces_ni_duplicados():
    archivos = {
        "/vault/a.md": "Se referencia a sí misma [[a]] y dos veces a [[b]] y [[b]] otra vez.",
        "/vault/b.md": "Nota B.",
    }
    p1, p2 = _con_archivos_falsos(archivos)
    with p1, p2:
        g = construir_grafo()
    assert g["edges"] == [{"origen": "a", "destino": "b"}]
