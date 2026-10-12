# -*- coding: utf-8 -*-
"""Extracción: lee las cuatro fuentes del caso sin transformarlas.

Fuentes:
    datos/raw/origen_vina.sqlite            todas las tablas del ERP
    datos/raw/origen_costos_productos.csv   maestro de costos (latin-1, separador ;)
    datos/raw/origen_embarques.json         embarques de exportación
    API https://mindicador.cl/api/dolar/<año> dólar observado 2025 y 2026; si la API
        falla (sin red, timeout de 60 s o respuesta inválida) se usa el respaldo
        datos/raw/dolar_<año>.json. Se imprime qué fuente se usó para cada año.

Devuelve DataFrames con los valores tal como vienen (texto donde la fuente es texto).
"""
import json
import sqlite3
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "datos" / "raw"
API_DOLAR = "https://mindicador.cl/api/dolar/{anio}"
ANIOS_DOLAR = (2025, 2026)
TIMEOUT_API = 60   # la API suele tardar entre 8 y 30 s


def leer_sqlite():
    """Todas las tablas de origen_vina.sqlite, en modo solo lectura."""
    ruta = (RAW / "origen_vina.sqlite").as_uri() + "?mode=ro"
    with sqlite3.connect(ruta, uri=True) as con:
        nombres = [n for (n,) in con.execute(
            "select name from sqlite_master where type = 'table' order by name")]
        return {n: pd.read_sql_query(f'select * from "{n}"', con) for n in nombres}


def leer_costos():
    """Maestro de costos. Se leen todas las columnas como texto; las filas que no
    son de datos (encabezado repetido y TOTAL) se separan para reportarlas."""
    crudo = pd.read_csv(RAW / "origen_costos_productos.csv", sep=";",
                        encoding="latin-1", dtype=str, keep_default_na=False)
    es_dato = crudo["producto_id"].str.fullmatch(r"\d+")
    return crudo[es_dato].reset_index(drop=True), crudo[~es_dato].reset_index(drop=True)


def leer_embarques():
    """Embarques y sus líneas. Como embarque_id viene repetido, cada embarque se
    identifica también por su posición en el archivo (emb_idx)."""
    with open(RAW / "origen_embarques.json", encoding="utf-8") as f:
        datos = json.load(f)
    embarques, lineas = [], []
    for idx, e in enumerate(datos["embarques"]):
        embarques.append({"emb_idx": idx, "embarque_id": e["embarque_id"],
                          "fecha_embarque": e["fecha_embarque"], "incoterm": e["incoterm"],
                          "puerto_destino": e["puerto_destino"], "mercado_id": e["mercado_id"],
                          "n_lineas": len(e["lineas"])})
        for l in e["lineas"]:
            lineas.append({"emb_idx": idx, "venta_id": l["venta_id"],
                           "cajas": l["cajas"], "cajas_es_texto": isinstance(l["cajas"], str)})
    return pd.DataFrame(embarques), pd.DataFrame(lineas)


def _serie_dolar(datos):
    serie = pd.DataFrame(datos["serie"])
    if serie.empty or not {"fecha", "valor"} <= set(serie.columns):
        raise ValueError("respuesta sin serie de valores")
    # la API entrega la fecha en UTC a las 03:00, que corresponde al día chileno
    serie["fecha"] = pd.to_datetime(serie["fecha"].str[:10])
    serie["valor"] = serie["valor"].astype(float)
    return serie.sort_values("fecha").reset_index(drop=True)


def leer_dolar(anio):
    """Dólar observado de un año: primero la API; si falla, el respaldo local.
    Devuelve (serie, texto que describe la fuente usada)."""
    url = API_DOLAR.format(anio=anio)
    try:
        pedido = urllib.request.Request(url, headers={"User-Agent": "vallehondo-g2/1.0"})
        with urllib.request.urlopen(pedido, timeout=TIMEOUT_API) as resp:
            serie = _serie_dolar(json.loads(resp.read().decode("utf-8")))
        return serie, f"Dólar {anio}: API mindicador.cl (OK)"
    except Exception as error:  # sin red, timeout, HTTP o JSON inválido
        respaldo = RAW / f"dolar_{anio}.json"
        with open(respaldo, encoding="utf-8") as f:
            serie = _serie_dolar(json.load(f))
        return serie, (f"Dólar {anio}: API no respondió ({type(error).__name__}) → respaldo "
                       f"{respaldo.relative_to(RAIZ).as_posix()}")


def extraer():
    erp = leer_sqlite()
    costos, costos_descartadas = leer_costos()
    embarques, lineas = leer_embarques()
    dolar, origen_dolar = [], {}
    for anio in ANIOS_DOLAR:
        print(f"  Dólar {anio}: consultando la API (hasta {TIMEOUT_API} s)...", flush=True)
        serie, origen = leer_dolar(anio)
        print(f"  {origen}", flush=True)
        dolar.append(serie)
        origen_dolar[anio] = origen
    dolar = pd.concat(dolar, ignore_index=True).drop_duplicates("fecha").sort_values("fecha")
    return {
        "erp": erp,
        "costos": costos,
        "costos_descartadas": costos_descartadas,
        "embarques": embarques,
        "lineas_embarque": lineas,
        "dolar": dolar.reset_index(drop=True),
        "origen_dolar": origen_dolar,
    }


if __name__ == "__main__":
    f = extraer()
    for t, df in f["erp"].items():
        print(f"{t}: {len(df)} filas")
    print("costos:", len(f["costos"]), "filas de datos;", len(f["costos_descartadas"]), "descartadas")
    print("embarques:", len(f["embarques"]), "| líneas:", len(f["lineas_embarque"]))
    print("dólar:", len(f["dolar"]), "días", f["origen_dolar"])
