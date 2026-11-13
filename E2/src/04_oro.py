# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Oro (borrador): modelo estrella y escenarios
# MAGIC Construye el modelo estrella de la E1 (`lib/integrar.py`, grano: **una fila es una línea de venta
# MAGIC facturada**) en el esquema `oro_borrador`, y la tabla de escenarios que alimenta la métrica y el
# MAGIC tablero. Nada se publica en `oro` hasta que pasen las pruebas (paso 05).
# MAGIC
# MAGIC **Escenarios precalculados** (el tablero solo filtra; nadie recalcula):
# MAGIC * moneda y fecha de conversión: USD · CLP a fecha de factura · CLP a cobranza estimada · CLP a fecha de embarque
# MAGIC * litros por caja del magnum: 9,0 (principal) · 18 · 4,5 (extremos hipotéticos)
# MAGIC * correcciones de datos: todas (principal) · sin montos recalculados · sin cajas corregidas · sin monedas imputadas · sin ninguna

# COMMAND ----------

import json, os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "lib"))
import comun
import pandas as pd
from pathlib import Path

P = comun.parametros(dbutils, {"catalogo": "vallehondo", "run_id": "", "dir_raw": "", "dir_lib": ""})
CAT, RUN_ID, INICIO = P["catalogo"], P["run_id"], comun.ahora()
import integrar

# COMMAND ----------

v = comun.leer(spark, f"{CAT}.plata.ventas")
for c in ["fecha_factura", "fecha_cobranza", "fecha_embarque"]:
    v[c] = pd.to_datetime(v[c])
res = {"ventas": v,
       "dolar": comun.leer(spark, f"{CAT}.plata.dolar_diario"),
       "producto_anada": comun.leer(spark, f"{CAT}.plata.producto_anada"),
       "mercados": comun.leer(spark, f"{CAT}.plata.mercados")}
res["dolar"]["fecha"] = pd.to_datetime(res["dolar"]["fecha"])
erp = {"cepas": comun.leer(spark, f"{CAT}.bronce.erp_cepas"),
       "clientes": comun.leer(spark, f"{CAT}.bronce.erp_clientes")}
estrella, integrada = integrar.integrar(res, erp, Path("/tmp/vallehondo_e2"))
n = {nombre: comun.escribir(spark, df, f"{CAT}.oro_borrador.{nombre}") for nombre, df in estrella.items()}

# COMMAND ----------

# Tabla de escenarios: universo de la métrica (exportación, facturas 2025) × escenarios,
# agregada por semestre, mes, mercado, tier y formato
spark.sql(f"""
CREATE OR REPLACE TABLE {CAT}.oro_borrador.agg_escenarios AS
WITH base AS (
  SELECT f.*, t.anio, t.semestre, t.mes, p.tier, p.formato, p.litros_por_caja, p.costo_caja_clp,
         m.pais AS mercado, m.zona, m.hemisferio, m.canal
  FROM {CAT}.oro_borrador.fact_venta f
  JOIN {CAT}.oro_borrador.dim_tiempo   t USING (fecha_key)
  JOIN {CAT}.oro_borrador.dim_producto p USING (producto_anada_key)
  JOIN {CAT}.oro_borrador.dim_mercado  m USING (mercado_key)
  WHERE m.canal = 'Exportación' AND t.anio = 2025
),
corr AS (
  SELECT * FROM VALUES
    ('Con todas las correcciones (principal)', 1, true,  true,  true),
    ('Sin montos recalculados',                2, false, true,  true),
    ('Sin cajas corregidas',                   3, true,  false, true),
    ('Sin monedas imputadas',                  4, true,  true,  false),
    ('Sin ninguna corrección',                 5, false, false, false)
  AS c(correcciones, orden_correcciones, usa_monto, usa_cajas, usa_moneda)
),
lpc AS (
  SELECT * FROM VALUES (9.0, '9,0 L (principal)'), (18.0, '18 L (extremo hipotético)'), (4.5, '4,5 L (extremo hipotético)')
  AS l(litros_caja_magnum, litros_caja_etiqueta)
),
mon AS (
  SELECT * FROM VALUES ('USD', 'USD', 1), ('CLP · fecha de factura', 'CLP', 2),
                       ('CLP · cobranza estimada', 'CLP', 3), ('CLP · fecha de embarque (no confiable)', 'CLP', 4)
  AS m(moneda_fecha, moneda, orden_moneda)
),
fila AS (
  SELECT b.*, c.correcciones, c.orden_correcciones, l.litros_caja_magnum, l.litros_caja_etiqueta,
         mo.moneda_fecha, mo.moneda, mo.orden_moneda,
         CASE WHEN c.usa_cajas THEN b.cajas ELSE b.cajas_registradas END AS cajas_esc,
         CASE WHEN c.usa_monto THEN b.monto_neto_usd ELSE b.monto_neto_registrado_usd END AS monto_usd_esc
  FROM base b CROSS JOIN corr c CROSS JOIN lpc l CROSS JOIN mon mo
  WHERE c.usa_moneda OR b.moneda_imputada = 0
),
calc AS (
  SELECT *,
         cajas_esc * CASE WHEN formato = '6x1500' THEN litros_caja_magnum ELSE litros_por_caja END AS litros_esc,
         CASE moneda_fecha WHEN 'USD' THEN 1.0
                           WHEN 'CLP · fecha de factura' THEN tipo_cambio
                           WHEN 'CLP · cobranza estimada' THEN tipo_cambio_cobranza
                           ELSE tipo_cambio_embarque END AS factor,
         abs(cajas_esc) * costo_caja_clp AS costo_clp_esc
  FROM fila
)
SELECT correcciones, orden_correcciones, litros_caja_magnum, litros_caja_etiqueta,
       moneda_fecha, moneda, orden_moneda, semestre, mes, mercado, zona, hemisferio, tier, formato,
       count(*)                                                             AS lineas,
       sum(litros_esc)                                                      AS litros,
       sum(abs(litros_esc))                                                 AS litros_abs,
       sum(CASE WHEN costo_imputado = 0 THEN abs(litros_esc) ELSE 0 END)    AS litros_costo_real,
       sum(monto_usd_esc * factor)                                          AS ingreso,
       sum(CASE WHEN moneda = 'USD' THEN costo_clp_esc / tipo_cambio ELSE costo_clp_esc END) AS costo,
       sum(monto_usd_esc * factor
           - CASE WHEN moneda = 'USD' THEN costo_clp_esc / tipo_cambio ELSE costo_clp_esc END) AS margen
FROM calc
GROUP BY ALL
""")
n["agg_escenarios"] = spark.table(f"{CAT}.oro_borrador.agg_escenarios").count()
comun.registrar_paso(spark, CAT, RUN_ID, "04_oro", "ok", INICIO, json.dumps(n))
print(json.dumps(n, indent=2))
dbutils.notebook.exit(json.dumps(n))
