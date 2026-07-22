"""Habilidad 4: seguimiento de hábitos (consumo de agua) con persistencia en JSON."""

import json
import os
from datetime import date

HABITOS_FILE = "habitos.json"
META_ML_DIARIA = 3500
ML_POR_VASO = 250  # ajusta al tamaño real de tu vaso


def _cargar_habitos():
    if os.path.exists(HABITOS_FILE):
        try:
            with open(HABITOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            print("[Jarvis] Aviso: habitos.json corrupto o ilegible, se reinicia.")
    return {}


def _guardar_habitos(datos):
    try:
        with open(HABITOS_FILE, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[Jarvis] No se pudo guardar hábitos: {e}")


def registrar_vaso_agua():
    datos = _cargar_habitos()
    hoy = date.today().isoformat()
    registro_hoy = datos.get(hoy, {"agua_ml": 0, "meta_alcanzada": False})

    ya_felicitado = registro_hoy.get("meta_alcanzada", False)
    registro_hoy["agua_ml"] = registro_hoy.get("agua_ml", 0) + ML_POR_VASO

    total = registro_hoy["agua_ml"]

    if total >= META_ML_DIARIA and not ya_felicitado:
        registro_hoy["meta_alcanzada"] = True
        datos[hoy] = registro_hoy
        _guardar_habitos(datos)
        return f"¡Bien hecho! Llevas {total} mililitros y alcanzaste tu meta de hoy."

    datos[hoy] = registro_hoy
    _guardar_habitos(datos)

    if total >= META_ML_DIARIA:
        return f"Ya superaste tu meta diaria, llevas {total} mililitros."

    restante = META_ML_DIARIA - total
    return f"Anotado. Llevas {total} de {META_ML_DIARIA} mililitros hoy, te faltan {restante}."
