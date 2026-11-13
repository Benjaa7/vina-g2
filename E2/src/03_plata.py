# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Plata: reglas de limpieza
# MAGIC Lee bronce y aplica las mismas reglas de la E1 (`lib/limpiar.py`): formatos de fecha y monto,
# MAGIC duplicados, monedas vacías, cajas cargadas en botellas, montos recalculados, costos imputados
# MAGIC y dólar diario. **Cada corrección queda marcada en su fila** (`moneda_imputada`,
# MAGIC `cajas_corregidas`, `monto_recalculado`, `costo_imputado`) junto al valor original, para que
# MAGIC el oro pueda calcular el escenario sin correcciones. También deja `cobertura.md` en `ops.salidas`.

# COMMAND ----------

import json, os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "lib"))
import comun
import pandas as pd

P = comun.parametros(dbutils, {"catalogo": "vallehondo", "run_id": "", "dir_raw": "", "dir_lib": ""})
CAT, RUN_ID, INICIO = P["catalogo"], P["run_id"], comun.ahora()
import limpiar

# COMMAND ----------

# Se arma la misma estructura que entregaba extraer.py en la E1, pero leyendo bronce
erp = {}
for t in ["cepas", "clientes", "mercados", "monedas", "vendedores", "ventas", "zonas"]:
    erp[t] = comun.leer(spark, f"{CAT}.bronce.erp_{t}")
costos_crudo = comun.leer(spark, f"{CAT}.bronce.costos_productos")
es_dato = costos_crudo["producto_id"].str.fullmatch(r"\d+")
dolar = comun.leer(spark, f"{CAT}.bronce.dolar_observado")
dolar["fecha"] = pd.to_datetime(dolar["fecha"].str[:10])   # la API entrega 03:00 UTC = día chileno
dolar = (dolar[["fecha", "valor"]].drop_duplicates("fecha").sort_values("fecha").reset_index(drop=True))
fuentes = {
    "erp": erp,
    "costos": costos_crudo[es_dato].reset_index(drop=True),
    "costos_descartadas": costos_crudo[~es_dato].reset_index(drop=True),
    "embarques": comun.leer(spark, f"{CAT}.bronce.embarques").sort_values("emb_idx").reset_index(drop=True),
    "lineas_embarque": comun.leer(spark, f"{CAT}.bronce.embarques_lineas").sort_values(["emb_idx"], kind="stable").reset_index(drop=True),
    "dolar": dolar,
}
res = limpiar.limpiar(fuentes)

# COMMAND ----------

v = res["ventas"]
n = {}
n["ventas"] = comun.escribir(spark, v, f"{CAT}.plata.ventas")
n["producto_anada"] = comun.escribir(spark, res["producto_anada"], f"{CAT}.plata.producto_anada")
n["mercados"] = comun.escribir(spark, res["mercados"], f"{CAT}.plata.mercados")
n["dolar_diario"] = comun.escribir(spark, res["dolar"], f"{CAT}.plata.dolar_diario")
n["regla_costo"] = comun.escribir(spark, res["regla_costo"], f"{CAT}.plata.regla_costo")

# Registro de reglas: cuántas filas toca cada una y cuántas caen en el universo de la métrica
universo = set(v.loc[v["en_universo"] == 1, "fila"])
reglas = pd.DataFrame([{"tema": r["tema"], "hallazgo": r["regla"], "accion": r["accion"], "grupo": r["grupo"],
                        "etapa": r["etapa"], "filas": len(r["filas"]), "filas_universo": len(r["filas"] & universo)}
                       for r in res["registro"].ventas])
reglas["run_id"] = RUN_ID
comun.escribir(spark, reglas, f"{CAT}.ops.reglas_limpieza")
otras = pd.DataFrame(res["registro"].otras)
otras["cantidad"] = otras["cantidad"].astype("int64")
otras["run_id"] = RUN_ID
comun.escribir(spark, otras, f"{CAT}.ops.hallazgos_fuentes")
from pathlib import Path
limpiar.escribir_cobertura(res, Path(comun.volumen(CAT, "ops", "salidas")) / "cobertura.md")

# COMMAND ----------

resumen = {"filas_crudas": res["n_crudo"], **n, "universo": int(v["en_universo"].sum()),
           "monto_recalculado_universo": int(v.loc[v.en_universo == 1, "monto_recalculado"].sum()),
           "moneda_imputada_universo": int(v.loc[v.en_universo == 1, "moneda_imputada"].sum()),
           "cajas_corregidas_universo": int(v.loc[v.en_universo == 1, "cajas_corregidas"].sum()),
           "costo_imputado_universo": int(v.loc[v.en_universo == 1, "costo_imputado"].sum())}
comun.registrar_paso(spark, CAT, RUN_ID, "03_plata", "ok", INICIO, json.dumps(resumen))
print(json.dumps(resumen, indent=2))
dbutils.notebook.exit(json.dumps(resumen))
