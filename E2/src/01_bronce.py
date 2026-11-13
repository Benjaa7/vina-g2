# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Bronce: las fuentes tal como llegan
# MAGIC Lee los archivos del volumen de llegada y los guarda como tablas Delta **sin transformar**:
# MAGIC mismos valores y mismos tipos que en el origen, más `_run_id`, `_fecha_carga` y `_archivo`.
# MAGIC La única operación es estructural: el JSON de embarques se separa en embarques y líneas.
# MAGIC Carga completa: cada corrida reemplaza las tablas.

# COMMAND ----------

import json, os, shutil, sqlite3, sys
sys.path.insert(0, os.path.join(os.getcwd(), "lib"))
import comun
import pandas as pd
from pyspark.sql import types as T

P = comun.parametros(dbutils, {"catalogo": "vallehondo", "run_id": "", "dir_raw": "", "dir_lib": ""})
CAT, RUN_ID, INICIO = P["catalogo"], P["run_id"], comun.ahora()
LLEGADA = comun.volumen(CAT, "bronce", "llegada")
CARGA = comun.ahora()

def con_metadatos(df, archivo):
    from pyspark.sql import functions as F
    return (df.withColumn("_run_id", F.lit(RUN_ID))
              .withColumn("_fecha_carga", F.lit(CARGA).cast("timestamp"))
              .withColumn("_archivo", F.lit(archivo)))

def guardar(df, tabla):
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{CAT}.bronce.{tabla}")
    return spark.table(f"{CAT}.bronce.{tabla}").count()

conteos = {}

# COMMAND ----------

# SQLite: cada tabla del ERP con el tipo declarado en la base (INTEGER → bigint, TEXT → string).
# _fila guarda el orden de la base: Spark no garantiza el orden al releer, y la limpieza (como en la E1) conserva
# la primera copia de cada venta duplicada, así que plata ordena por _fila antes de limpiar.
shutil.copyfile(f"{LLEGADA}/origen_vina.sqlite", "/tmp/origen_vina.sqlite")
con = sqlite3.connect("file:/tmp/origen_vina.sqlite?mode=ro", uri=True)
tablas = [n for (n,) in con.execute("select name from sqlite_master where type = 'table' order by name")]
for t in tablas:
    cols = [(r[1], r[2].upper()) for r in con.execute(f'pragma table_info("{t}")')]
    esquema = T.StructType([T.StructField("_fila", T.LongType(), False)] +
                           [T.StructField(c, T.LongType() if tipo == "INTEGER" else T.StringType(), True)
                            for c, tipo in cols])
    filas = [(i,) + tuple(None if v is None else (int(v) if tipo == "INTEGER" else str(v))
                          for v, (_, tipo) in zip(fila, cols))
             for i, fila in enumerate(con.execute(f'select * from "{t}"'), start=1)]
    conteos[f"erp_{t}"] = guardar(con_metadatos(spark.createDataFrame(filas, esquema), "origen_vina.sqlite"), f"erp_{t}")
con.close()

# COMMAND ----------

# CSV de costos: todas las columnas como texto y todas las filas (incluidas las que no son datos)
crudo = pd.read_csv(f"{LLEGADA}/origen_costos_productos.csv", sep=";", encoding="latin-1",
                    dtype=str, keep_default_na=False)
crudo.insert(0, "_fila", range(1, len(crudo) + 1))
conteos["costos_productos"] = guardar(con_metadatos(spark.createDataFrame(crudo), "origen_costos_productos.csv"),
                                      "costos_productos")

# COMMAND ----------

# JSON de embarques: embarques y líneas; las cajas se guardan como texto porque vienen
# a veces como número y a veces como texto ("35"), y se marca cuál era el caso
with open(f"{LLEGADA}/origen_embarques.json", encoding="utf-8") as f:
    datos = json.load(f)
emb, lin = [], []
for idx, e in enumerate(datos["embarques"]):
    emb.append((idx, str(e["embarque_id"]), str(e["fecha_embarque"]), e.get("incoterm"),
                e.get("puerto_destino"), int(e["mercado_id"]), len(e["lineas"])))
    for l in e["lineas"]:
        lin.append((idx, int(l["venta_id"]), str(l["cajas"]), isinstance(l["cajas"], str)))
esq_emb = T.StructType([T.StructField("emb_idx", T.LongType()), T.StructField("embarque_id", T.StringType()),
                        T.StructField("fecha_embarque", T.StringType()), T.StructField("incoterm", T.StringType()),
                        T.StructField("puerto_destino", T.StringType()), T.StructField("mercado_id", T.LongType()),
                        T.StructField("n_lineas", T.LongType())])
esq_lin = T.StructType([T.StructField("emb_idx", T.LongType()), T.StructField("venta_id", T.LongType()),
                        T.StructField("cajas", T.StringType()), T.StructField("cajas_es_texto", T.BooleanType())])
conteos["embarques"] = guardar(con_metadatos(spark.createDataFrame(emb, esq_emb), "origen_embarques.json"), "embarques")
conteos["embarques_lineas"] = guardar(con_metadatos(spark.createDataFrame(lin, esq_lin), "origen_embarques.json"),
                                      "embarques_lineas")

# COMMAND ----------

comun.registrar_paso(spark, CAT, RUN_ID, "01_bronce", "ok", INICIO, json.dumps(conteos))
print(json.dumps(conteos, indent=2))
