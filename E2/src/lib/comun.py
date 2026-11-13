# -*- coding: utf-8 -*-
"""Configuración y utilidades que comparten los pasos del job de la E2.

Capas (Unity Catalog, catálogo `vallehondo` por defecto):
    bronce        las fuentes tal como llegan, más _run_id, _fecha_carga y _archivo
    plata         ventas, costos, mercados y dólar depurados (reglas de la E1)
    oro_borrador  el modelo estrella antes de pasar las pruebas
    oro           el modelo publicado, la tabla de escenarios y la definición única
    ops           registro de corridas, resultado de las pruebas y salidas
Todas las tablas se reemplazan en cada corrida (carga completa); solo ops.run_log y
ops.dq_resultados guardan historia, con MERGE por (run_id, paso) y (run_id, prueba).
"""
import os
import sys
import uuid
from datetime import datetime, timezone

import pandas as pd

ESQUEMAS = ["bronce", "plata", "oro_borrador", "oro", "ops"]


def ahora():
    return datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)


def parametros(dbutils, defaults):
    """Crea los widgets (parámetros del job) y devuelve sus valores."""
    for nombre, valor in defaults.items():
        dbutils.widgets.text(nombre, valor)
    p = {n: dbutils.widgets.get(n).strip() for n in defaults}
    aqui = os.getcwd()   # carpeta del notebook en /Workspace
    p["dir_raw"] = p.get("dir_raw") or os.path.normpath(os.path.join(aqui, "..", "datos", "raw"))
    libs = p.get("dir_lib") or os.path.join(aqui, "lib")
    for ruta in reversed([x.strip() for x in libs.split(",") if x.strip()]):
        if ruta in sys.path:          # se reinserta al inicio para respetar el orden pedido
            sys.path.remove(ruta)
        sys.path.insert(0, ruta)
    p["run_id"] = p.get("run_id") or "manual-" + ahora().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    return p


def volumen(cat, esquema, nombre):
    return f"/Volumes/{cat}/{esquema}/{nombre}"


def escribir(spark, pdf, tabla):
    """Escribe un DataFrame de pandas como tabla Delta, reemplazándola (carga completa)."""
    df = spark.createDataFrame(pdf)
    (df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(tabla))
    return len(pdf)


def leer(spark, tabla, sin_metadatos=True):
    """Lee una tabla a pandas. Si trae _fila (orden de la fuente), la devuelve en ese orden: Spark no lo garantiza."""
    pdf = spark.table(tabla).toPandas()
    if "_fila" in pdf.columns:
        pdf = pdf.sort_values("_fila", kind="stable").reset_index(drop=True)
    if sin_metadatos:
        pdf = pdf[[c for c in pdf.columns if not c.startswith("_")]]
    return pdf


def registrar_paso(spark, cat, run_id, paso, estado, inicio, detalle=""):
    """Una fila por (corrida, paso) en ops.run_log. Si el paso se reintenta, se actualiza."""
    spark.sql(f"""CREATE TABLE IF NOT EXISTS {cat}.ops.run_log (
        run_id STRING, paso STRING, estado STRING, inicio TIMESTAMP, fin TIMESTAMP, detalle STRING)""")
    spark.sql(f"""MERGE INTO {cat}.ops.run_log t
        USING (SELECT :run_id AS run_id, :paso AS paso, :estado AS estado,
                      CAST(:inicio AS TIMESTAMP) AS inicio, current_timestamp() AS fin, :detalle AS detalle) s
        ON t.run_id = s.run_id AND t.paso = s.paso
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *""",
              args={"run_id": run_id, "paso": paso, "estado": estado,
                    "inicio": inicio.strftime("%Y-%m-%d %H:%M:%S"), "detalle": detalle[:4000]})


def registrar_pruebas(spark, cat, run_id, resultados):
    """resultados: lista de dicts con prueba, fuente, protege, severidad, paso_ok, filas_fallan, accion, detalle."""
    spark.sql(f"""CREATE TABLE IF NOT EXISTS {cat}.ops.dq_resultados (
        run_id STRING, momento TIMESTAMP, capa STRING, prueba STRING, fuente STRING, protege STRING,
        severidad STRING, resultado STRING, filas_fallan BIGINT, accion STRING, detalle STRING)""")
    filas = []
    for r in resultados:
        filas.append({"run_id": run_id, "momento": ahora(), "capa": r["capa"], "prueba": r["prueba"],
                      "fuente": r["fuente"], "protege": r["protege"], "severidad": r["severidad"],
                      "resultado": "pasa" if r["paso_ok"] else "falla",
                      "filas_fallan": int(r.get("filas_fallan", 0)),
                      "accion": r["accion_ok"] if r["paso_ok"] else r["accion_falla"],
                      "detalle": str(r.get("detalle", ""))[:1000]})
    spark.createDataFrame(pd.DataFrame(filas)).createOrReplaceTempView("_dq_nuevas")
    spark.sql(f"""MERGE INTO {cat}.ops.dq_resultados t USING _dq_nuevas s
        ON t.run_id = s.run_id AND t.prueba = s.prueba
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *""")
    return filas
