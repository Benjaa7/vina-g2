# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Dólar observado: API con respaldo
# MAGIC Decisión de falla de fuente (componente B):
# MAGIC 1. ¿Responde la API de mindicador.cl? **Sí** → se usa y se guarda como nuevo respaldo.
# MAGIC 2. **No** → ¿hay respaldo con fecha en el volumen de llegada? **Sí** → se usa y se avisa
# MAGIC    (queda en `ops.fuente_dolar`, que lee el pie del tablero).
# MAGIC 3. **No** → el paso falla y el job no publica el oro; el tablero sigue con la última corrida válida.
# MAGIC
# MAGIC Para probar la falla, se corre el job con `url_dolar` apuntando a una URL incorrecta.

# COMMAND ----------

import json, os, sys, time, urllib.request
sys.path.insert(0, os.path.join(os.getcwd(), "lib"))
import comun
import pandas as pd

P = comun.parametros(dbutils, {"catalogo": "vallehondo", "run_id": "", "dir_raw": "", "dir_lib": "",
                               "url_dolar": "https://mindicador.cl/api/dolar/{anio}", "timeout_api_s": "20"})
CAT, RUN_ID, INICIO = P["catalogo"], P["run_id"], comun.ahora()
LLEGADA = comun.volumen(CAT, "bronce", "llegada")
SALIDAS = comun.volumen(CAT, "ops", "salidas")
ANIOS = (2025, 2026)   # facturas de 2025 y cobranzas que caen en 2026
with open(f"{LLEGADA}/respaldo_dolar.json", encoding="utf-8") as f:
    MANIFIESTO = json.load(f)["archivos"]

def serie_valida(datos):
    serie = datos.get("serie") or []
    if not serie or not all({"fecha", "valor"} <= set(x) for x in serie):
        raise ValueError("respuesta sin serie de valores")
    return serie

filas, fuentes = [], []
for anio in ANIOS:
    url = P["url_dolar"].format(anio=anio)
    t0 = time.time()
    try:
        pedido = urllib.request.Request(url, headers={"User-Agent": "vallehondo-g2/2.0"})
        with urllib.request.urlopen(pedido, timeout=float(P["timeout_api_s"])) as r:
            crudo = r.read().decode("utf-8")
        serie = serie_valida(json.loads(crudo))
        hoy = comun.ahora().strftime("%Y-%m-%d")
        with open(f"{SALIDAS}/dolar_{anio}_api_{hoy}.json", "w", encoding="utf-8") as f:
            f.write(crudo)
        fuente = {"anio": anio, "fuente": "API", "detalle": f"API mindicador.cl respondió en {time.time() - t0:.1f} s",
                  "archivo": url, "descargado_el": hoy}
    except Exception as error:
        archivo = f"dolar_{anio}.json"
        with open(f"{LLEGADA}/{archivo}", encoding="utf-8") as f:
            serie = serie_valida(json.load(f))
        fuente = {"anio": anio, "fuente": "respaldo",
                  "detalle": f"API no respondió ({type(error).__name__}: {str(error)[:120]}) → respaldo {archivo}",
                  "archivo": archivo, "descargado_el": MANIFIESTO[archivo]["descargado_el"]}
    fuentes.append(fuente)
    for x in serie:
        filas.append({"anio": anio, "fecha": str(x["fecha"]), "valor": float(x["valor"]),
                      "fuente": fuente["fuente"], "descargado_el": fuente["descargado_el"]})

# COMMAND ----------

from pyspark.sql import functions as F
df = (spark.createDataFrame(pd.DataFrame(filas))
      .withColumn("_run_id", F.lit(RUN_ID)).withColumn("_fecha_carga", F.current_timestamp())
      .withColumn("_archivo", F.lit("mindicador.cl / respaldo")))
df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{CAT}.bronce.dolar_observado")
fu = pd.DataFrame(fuentes)
fu["run_id"] = RUN_ID
comun.escribir(spark, fu, f"{CAT}.ops.fuente_dolar")
comun.registrar_paso(spark, CAT, RUN_ID, "02_dolar", "ok", INICIO, json.dumps(fuentes, ensure_ascii=False))
display(fu)
