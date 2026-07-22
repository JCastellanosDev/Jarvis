"""Habilidad 3: estado de la base de datos del proyecto "melo" (POS/KDS)."""

import os

# --- PERSONALIZA ---
# True -> sqlite3 (bueno para desarrollo local)
# False -> pymysql (requiere `pip install pymysql` y un servidor MySQL)
USAR_SQLITE = True

RUTA_SQLITE_MELO = os.path.expanduser("~/Desktop/melo/melo.db")

MYSQL_CONFIG = {
    "host": os.getenv("MELO_DB_HOST", "localhost"),
    "user": os.getenv("MELO_DB_USER", "root"),
    "password": os.getenv("MELO_DB_PASSWORD", ""),
    "database": os.getenv("MELO_DB_NAME", "melo"),
}

# AJUSTA nombres de tabla/columnas a tu esquema real de "melo".
QUERY_SQLITE = """
    SELECT estado, COUNT(*)
    FROM comandas
    WHERE date(creado_en) = date('now', 'localtime')
    GROUP BY estado
"""

QUERY_MYSQL = """
    SELECT estado, COUNT(*)
    FROM comandas
    WHERE DATE(creado_en) = CURDATE()
    GROUP BY estado
"""


def revisar_estado_melo():
    try:
        filas = _consultar_sqlite() if USAR_SQLITE else _consultar_mysql()
    except Exception as e:
        return f"No pude conectar con la base de datos de melo: {e}"

    if not filas:
        return "No hay comandas registradas hoy en melo."

    partes = [f"{cantidad} en estado {estado}" for estado, cantidad in filas]
    return "Estado de melo hoy: " + ", ".join(partes) + "."


def _consultar_sqlite():
    import sqlite3
    conn = sqlite3.connect(RUTA_SQLITE_MELO)
    try:
        cur = conn.cursor()
        cur.execute(QUERY_SQLITE)
        return cur.fetchall()
    finally:
        conn.close()


def _consultar_mysql():
    import pymysql
    conn = pymysql.connect(**MYSQL_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(QUERY_MYSQL)
        return cur.fetchall()
    finally:
        conn.close()
