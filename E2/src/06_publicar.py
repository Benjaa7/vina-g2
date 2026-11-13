# Databricks notebook source
# MAGIC %md
# MAGIC # 06 · Publicar el oro y la definición única
# MAGIC Solo corre si pasaron las pruebas bloqueantes (paso 05). Copia el borrador a `oro` y crea:
# MAGIC * **`oro.mv_vallehondo`**: la *metric view* de Unity Catalog. Es la capa semántica: el precio medio por
# MAGIC   litro, el margen bruto por litro, la participación de gran reserva y la cobertura se escriben **una sola
# MAGIC   vez** aquí. El tablero, las vistas y las cifras del informe leen de ella.
# MAGIC * `oro.v_descomposicion` y `oro.v_descomposicion_total`: mezcla, precio y cruzado (base primer semestre).
# MAGIC * `oro.v_valor_punto`: cuánto vale un punto de gran reserva en la mezcla.
# MAGIC * `oro.v_mercados`: la descomposición y el margen por mercado, con la regla que separa recomendación de hipótesis.
# MAGIC * `oro.v_pruebas`: las pruebas de calidad de la última corrida.
# MAGIC * `oro.v_estado_corrida`: lo que muestra el pie del tablero.

# COMMAND ----------

import json, os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "lib"))
import comun

P = comun.parametros(dbutils, {"catalogo": "vallehondo", "run_id": "", "dir_raw": "", "dir_lib": "",
                               "dueno_dato": "Gerencia Comercial de Exportaciones"})
CAT, RUN_ID, INICIO = P["catalogo"], P["run_id"], comun.ahora()
OB, O = f"{CAT}.oro_borrador", f"{CAT}.oro"

TABLAS = ["fact_venta", "dim_tiempo", "dim_producto", "dim_cliente", "dim_mercado", "agg_escenarios"]
for t in TABLAS:
    spark.sql(f"CREATE OR REPLACE TABLE {O}.{t} AS SELECT * FROM {OB}.{t}")
spark.sql(f"COMMENT ON TABLE {O}.fact_venta IS 'Hecho de ventas. Una fila es una línea de venta facturada: un producto de una añada, vendido a un cliente en una fecha.'")
spark.sql(f"COMMENT ON TABLE {O}.agg_escenarios IS 'Universo de la métrica (exportación, facturas 2025) agregado por semestre, mes, mercado, tier y formato, para cada escenario de moneda y fecha, litros por caja y correcciones.'")

# COMMAND ----------

MEDIDAS = {
    "litros": "SUM(litros)",
    "ingreso": "SUM(ingreso)",
    "precio_por_litro": "SUM(ingreso) / SUM(litros)",
    "margen_bruto": "SUM(margen)",
    "margen_por_litro": "SUM(margen) / SUM(litros)",
    "margen_pct": "SUM(margen) / SUM(ingreso)",
    "participacion_gran_reserva": "SUM(CASE WHEN tier = 'Gran Reserva' THEN litros ELSE 0 END) / SUM(litros)",
    "cobertura_costo_real": "SUM(litros_costo_real) / SUM(litros_abs)",
    "lineas": "SUM(lineas)",
}
DIMENSIONES = ["correcciones", "orden_correcciones", "litros_caja_magnum", "litros_caja_etiqueta", "moneda_fecha",
               "moneda", "orden_moneda", "semestre", "mes", "mercado", "zona", "hemisferio", "tier", "formato"]
yaml = "version: 0.1\n" + f"source: {O}.agg_escenarios\n" + "dimensions:\n" + "".join(
    f"  - name: {d}\n    expr: {d}\n" for d in DIMENSIONES) + "measures:\n" + "".join(
    f"  - name: {m}\n    expr: \"{e}\"\n" for m, e in MEDIDAS.items())
spark.sql(f"CREATE OR REPLACE VIEW {O}.mv_vallehondo WITH METRICS LANGUAGE YAML AS $${yaml}$$")

# COMMAND ----------

ESC = "correcciones, litros_caja_magnum, moneda_fecha"
spark.sql(f"""
CREATE OR REPLACE VIEW {O}.v_descomposicion AS
WITH t AS (
  SELECT {ESC}, 'Todos los mercados' AS mercado, tier, semestre,
         MEASURE(litros) AS litros, MEASURE(precio_por_litro) AS p
  FROM {O}.mv_vallehondo GROUP BY {ESC}, tier, semestre
  UNION ALL
  SELECT {ESC}, mercado, tier, semestre, MEASURE(litros) AS litros, MEASURE(precio_por_litro) AS p
  FROM {O}.mv_vallehondo GROUP BY {ESC}, mercado, tier, semestre
),
w AS (
  SELECT *, litros / sum(litros) OVER (PARTITION BY {ESC}, mercado, semestre) AS w FROM t
),
piv AS (
  SELECT {ESC}, mercado, tier,
         max(CASE WHEN semestre = 1 THEN w END) AS w1, max(CASE WHEN semestre = 2 THEN w END) AS w2,
         max(CASE WHEN semestre = 1 THEN p END) AS p1, max(CASE WHEN semestre = 2 THEN p END) AS p2
  FROM w GROUP BY {ESC}, mercado, tier
)
SELECT {ESC}, mercado, tier,
       w1 AS participacion_s1, w2 AS participacion_s2, p1 AS precio_s1, p2 AS precio_s2,
       (w2 - w1) * p1 AS efecto_mezcla, w1 * (p2 - p1) AS efecto_precio, (w2 - w1) * (p2 - p1) AS efecto_cruzado
FROM piv
""")
spark.sql(f"""
CREATE OR REPLACE VIEW {O}.v_descomposicion_total AS
SELECT {ESC}, mercado,
       sum(participacion_s1 * precio_s1) AS precio_s1,
       sum(participacion_s2 * precio_s2) AS precio_s2,
       sum(participacion_s2 * precio_s2) / sum(participacion_s1 * precio_s1) - 1 AS alza_pct,
       sum(efecto_mezcla) AS efecto_mezcla, sum(efecto_precio) AS efecto_precio, sum(efecto_cruzado) AS efecto_cruzado,
       sum(efecto_mezcla) / (sum(participacion_s2 * precio_s2) - sum(participacion_s1 * precio_s1)) AS mezcla_pct_del_alza,
       sum(efecto_precio) / (sum(participacion_s2 * precio_s2) - sum(participacion_s1 * precio_s1)) AS precio_pct_del_alza,
       max(CASE WHEN tier = 'Gran Reserva' THEN participacion_s1 END) AS gran_reserva_s1,
       max(CASE WHEN tier = 'Gran Reserva' THEN participacion_s2 END) AS gran_reserva_s2
FROM {O}.v_descomposicion GROUP BY {ESC}, mercado
""")
spark.sql(f"""
CREATE OR REPLACE VIEW {O}.v_valor_punto AS
WITH t AS (
  SELECT {ESC}, tier, MEASURE(litros) AS litros, MEASURE(margen_por_litro) AS m
  FROM {O}.mv_vallehondo GROUP BY {ESC}, tier
), x AS (
  SELECT {ESC}, sum(litros) AS litros_anuales,
         max(CASE WHEN tier = 'Gran Reserva' THEN m END) AS margen_litro_gran_reserva,
         max(CASE WHEN tier = 'Reserva' THEN m END) AS margen_litro_reserva,
         max(CASE WHEN tier = 'Varietal' THEN m END) AS margen_litro_varietal
  FROM t GROUP BY {ESC}
)
SELECT *,
       0.01 * litros_anuales * (margen_litro_gran_reserva - margen_litro_varietal) AS valor_punto_vs_varietal,
       0.01 * litros_anuales * (margen_litro_gran_reserva - margen_litro_reserva)  AS valor_punto_vs_reserva,
       9.0 * (margen_litro_gran_reserva - margen_litro_varietal)                   AS valor_caja_vs_varietal,
       0.01 * litros_anuales / 9.0                                                 AS cajas_por_punto
FROM x
""")
spark.sql(f"""
CREATE OR REPLACE VIEW {O}.v_estado_corrida AS
WITH ultima AS (
  SELECT run_id, max(fin) AS fin FROM {CAT}.ops.run_log WHERE paso = '06_publicar' AND estado = 'ok'
  GROUP BY run_id ORDER BY fin DESC LIMIT 1
), pr AS (
  SELECT run_id, count(*) AS total, sum(CASE WHEN resultado = 'pasa' THEN 1 ELSE 0 END) AS pasan
  FROM {CAT}.ops.dq_resultados GROUP BY run_id
), fd AS (
  SELECT concat_ws(' · ', collect_list(concat('dólar ', anio, ': ',
           CASE WHEN fuente = 'API' THEN 'API mindicador.cl' ELSE concat('respaldo descargado el ', descargado_el) END))) AS dolar
  FROM {CAT}.ops.fuente_dolar
)
SELECT u.run_id, u.fin AS ultima_actualizacion_utc, pr.pasan AS pruebas_en_verde, pr.total AS pruebas_total, fd.dolar,
       'ERP comercial (origen_vina.sqlite), maestro de costos (CSV), embarques (JSON) y dólar observado' AS fuente,
       '{P["dueno_dato"]}' AS dueno_dato,
       'Facturas de exportación 2025; primer semestre = enero a junio' AS periodo
FROM ultima u LEFT JOIN pr USING (run_id) CROSS JOIN fd
""")

spark.sql(f"""
CREATE OR REPLACE VIEW {O}.v_mercados AS
WITH m AS (
  SELECT {ESC}, mercado, hemisferio, zona,
         MEASURE(litros) AS litros_anuales,
         MEASURE(lineas) AS lineas,
         MEASURE(margen_por_litro) FILTER (WHERE semestre = 1) AS margen_litro_s1,
         MEASURE(margen_por_litro) FILTER (WHERE semestre = 2) AS margen_litro_s2,
         MEASURE(cobertura_costo_real) AS cobertura_costo_real
  FROM {O}.mv_vallehondo GROUP BY {ESC}, mercado, hemisferio, zona
), x AS (
  SELECT m.*, d.precio_s1, d.precio_s2, d.alza_pct, d.mezcla_pct_del_alza, d.precio_pct_del_alza,
         d.gran_reserva_s1, d.gran_reserva_s2, d.gran_reserva_s2 - d.gran_reserva_s1 AS cambio_gran_reserva,
         m.margen_litro_s2 / m.margen_litro_s1 - 1 AS alza_margen_litro_pct
  FROM m JOIN {O}.v_descomposicion_total d USING ({ESC}, mercado)
)
-- Regla de lectura por mercado: el patrón del total (alza explicada por la mezcla hacia gran reserva) se
-- trata como recomendación solo si se repite en el mercado con datos suficientes; si no, es hipótesis.
SELECT *,
       CASE WHEN alza_pct > 0 AND mezcla_pct_del_alza >= 0.8 AND cambio_gran_reserva >= 0.05
                 AND cobertura_costo_real >= 0.8 AND lineas >= 300
            THEN 'Recomendación' ELSE 'Hipótesis' END AS lectura,
       concat_ws('; ',
         CASE WHEN alza_pct <= 0 THEN 'el precio por litro no sube' END,
         CASE WHEN mezcla_pct_del_alza < 0.8 THEN 'la mezcla explica menos del 80 % del alza' END,
         CASE WHEN cambio_gran_reserva < 0.05 THEN 'gran reserva sube menos de 5 puntos' END,
         CASE WHEN cobertura_costo_real < 0.8 THEN 'menos del 80 % de los litros con costo real' END,
         CASE WHEN lineas < 300 THEN 'menos de 300 líneas' END) AS motivo_hipotesis
FROM x
""")
spark.sql(f"""
CREATE OR REPLACE VIEW {O}.v_pruebas AS
SELECT capa, prueba, severidad, resultado, filas_fallan, fuente, protege, accion, detalle, run_id, momento
FROM {CAT}.ops.dq_resultados
WHERE run_id = (SELECT run_id FROM {CAT}.ops.dq_resultados ORDER BY momento DESC LIMIT 1)
""")

# COMMAND ----------

comun.registrar_paso(spark, CAT, RUN_ID, "06_publicar", "ok", INICIO, json.dumps({"tablas": TABLAS}))
display(spark.sql(f"SELECT * FROM {O}.v_descomposicion_total WHERE mercado = 'Todos los mercados' ORDER BY {ESC}"))
