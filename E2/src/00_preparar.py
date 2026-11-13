# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Preparar
# MAGIC Crea el catálogo, los esquemas de cada capa y los volúmenes, y copia los archivos fuente
# MAGIC del repositorio (`E2/datos/raw`) al volumen de llegada `bronce.llegada`. Desde ahí lee bronce.

# COMMAND ----------

import hashlib, json, os, shutil, sys
sys.path.insert(0, os.path.join(os.getcwd(), "lib"))
import comun

P = comun.parametros(dbutils, {"catalogo": "vallehondo", "run_id": "", "dir_raw": "", "dir_lib": ""})
CAT, RUN_ID, INICIO = P["catalogo"], P["run_id"], comun.ahora()
print(P)

# COMMAND ----------

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CAT}")
for esquema in comun.ESQUEMAS:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CAT}.{esquema}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CAT}.bronce.llegada")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CAT}.ops.salidas")

# COMMAND ----------

ARCHIVOS = ["origen_vina.sqlite", "origen_costos_productos.csv", "origen_embarques.json",
            "dolar_2025.json", "dolar_2026.json", "respaldo_dolar.json"]
llegada = comun.volumen(CAT, "bronce", "llegada")
manifiesto = []
for nombre in ARCHIVOS:
    # dir_raw puede traer varias carpetas separadas por coma: se usa la primera que tenga el archivo
    candidatos = [os.path.join(d.strip(), nombre) for d in P["dir_raw"].split(",") if d.strip()]
    origen = next((c for c in candidatos if os.path.exists(c)), None)
    if origen is None:
        raise FileNotFoundError(f"falta la fuente {nombre} en {P['dir_raw']}")
    shutil.copyfile(origen, f"{llegada}/{nombre}")
    with open(origen, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    manifiesto.append({"archivo": nombre, "bytes": os.path.getsize(origen), "md5": md5,
                       "origen": origen, "run_id": RUN_ID, "copiado": comun.ahora()})

import pandas as pd
comun.escribir(spark, pd.DataFrame(manifiesto), f"{CAT}.ops.archivos_llegada")
comun.registrar_paso(spark, CAT, RUN_ID, "00_preparar", "ok", INICIO,
                     json.dumps({"archivos": len(manifiesto)}))
display(pd.DataFrame(manifiesto))
