# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · Pruebas de calidad
# MAGIC Corre en cada ejecución, **antes de publicar el oro**. Hay al menos una prueba por fuente y las que
# MAGIC protegen la métrica. Cada prueba deja una fila en `ops.dq_resultados` (corrida, prueba, resultado,
# MAGIC filas que fallan y acción). Si una prueba **bloqueante** falla, este paso falla, el job se detiene
# MAGIC y el oro publicado (y el tablero) siguen con la última corrida válida.

# COMMAND ----------

import json, os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "lib"))
import comun

P = comun.parametros(dbutils, {"catalogo": "vallehondo", "run_id": "", "dir_raw": "", "dir_lib": ""})
CAT, RUN_ID, INICIO = P["catalogo"], P["run_id"], comun.ahora()
B, PL, OB, O = f"{CAT}.bronce", f"{CAT}.plata", f"{CAT}.oro_borrador", f"{CAT}.oro"
q = lambda sql: spark.sql(sql).first()
pruebas = []

def prueba(capa, nombre, fuente, protege, severidad, ok, filas=0, detalle=""):
    pruebas.append({"capa": capa, "prueba": nombre, "fuente": fuente, "protege": protege, "severidad": severidad,
                    "paso_ok": bool(ok), "filas_fallan": int(filas or 0), "detalle": detalle,
                    "accion_ok": "ninguna",
                    "accion_falla": "bloquea la publicación del oro" if severidad == "bloquea" else "aviso en el registro"})

def existe(tabla):
    return spark.catalog.tableExists(tabla)

# COMMAND ----------

# ---------- Fuentes ----------
ESPERADAS = {
    "erp_ventas": {"venta_id", "fecha", "cliente_id", "mercado_id", "producto_id", "moneda_id", "vendedor_id",
                   "cajas", "precio_unitario", "descuento", "monto_neto", "anada", "zona", "mes"},
    "erp_clientes": {"cliente_id", "nombre", "mercado_id", "rut", "tipo"},
    "erp_mercados": {"mercado_id", "pais", "zona_id", "canal"},
    "erp_zonas": {"zona_id", "zona"}, "erp_cepas": {"cepa_id", "cepa", "tipo"},
    "erp_monedas": {"moneda_id", "moneda"}, "erp_vendedores": {"vendedor_id", "vendedor"},
}
faltan = []
for t, cols in ESPERADAS.items():
    if not existe(f"{B}.{t}"):
        faltan.append(f"{t} (no existe)")
    else:
        falta = cols - set(spark.table(f"{B}.{t}").columns)
        if falta:
            faltan.append(f"{t}: {sorted(falta)}")
prueba("bronce", "SQLite: están las 7 tablas del ERP con sus columnas", "origen_vina.sqlite", "fuente",
       "bloquea", not faltan, len(faltan), "; ".join(faltan) or "7 tablas completas")

r = q(f"SELECT count(*) n, count(DISTINCT venta_id) d FROM {PL}.ventas")
prueba("plata", "SQLite: venta_id único después de quitar duplicados", "origen_vina.sqlite", "fuente y métrica",
       "bloquea", r.n == r.d, r.n - r.d, f"{r.n} filas, {r.d} venta_id distintos")

cols_csv = {"producto_id", "producto", "cepa", "tier", "formato", "litros_por_caja", "anada", "costo_caja_clp", "activo"}
falta_csv = cols_csv - set(spark.table(f"{B}.costos_productos").columns)
r = q(f"SELECT count(*) n, sum(CASE WHEN litros_por_caja <> 9.0 THEN 1 ELSE 0 END) malos, "
      f"count(DISTINCT formato) formatos FROM {PL}.producto_anada")
prueba("plata", "CSV de costos: columnas esperadas y 9,0 L por caja en ambos formatos",
       "origen_costos_productos.csv", "fuente y definición (9,0 L por caja)", "bloquea",
       not falta_csv and r.malos == 0 and r.formatos == 2, (r.malos or 0) + len(falta_csv),
       f"{r.n} pares producto-añada; {r.formatos} formatos; columnas faltantes: {sorted(falta_csv) or 'ninguna'}")

r = q(f"""SELECT count(*) n,
           sum(CASE WHEN embarque_id IS NULL OR fecha_embarque IS NULL OR mercado_id IS NULL OR incoterm IS NULL THEN 1 ELSE 0 END) malos
         FROM {B}.embarques""")
r2 = q(f"""SELECT count(*) n,
            sum(CASE WHEN venta_id IS NULL OR NOT (cajas RLIKE '^-?[0-9]+$') THEN 1 ELSE 0 END) malos
          FROM {B}.embarques_lineas""")
prueba("bronce", "JSON de embarques: estructura, campos requeridos y cajas numéricas", "origen_embarques.json",
       "fuente", "bloquea", (r.malos or 0) + (r2.malos or 0) == 0, (r.malos or 0) + (r2.malos or 0),
       f"{r.n} embarques y {r2.n} líneas")

fuente = spark.table(f"{CAT}.ops.fuente_dolar").toPandas()
r = q(f"""SELECT sum(CASE WHEN tipo_cambio IS NULL OR tipo_cambio_cobranza IS NULL THEN 1 ELSE 0 END) sin_tc,
                 sum(CASE WHEN tipo_cambio NOT BETWEEN 600 AND 1200 OR tipo_cambio_cobranza NOT BETWEEN 600 AND 1200
                          THEN 1 ELSE 0 END) fuera
          FROM {PL}.ventas""")
prueba("plata", "Dólar: valor para cada fecha de factura y de cobranza, entre 600 y 1.200 CLP/USD",
       "API mindicador.cl o respaldo", "fuente", "bloquea", (r.sin_tc or 0) + (r.fuera or 0) == 0,
       (r.sin_tc or 0) + (r.fuera or 0),
       "; ".join(f"{a}: {f}" for a, f in zip(fuente["anio"], fuente["detalle"])))

# COMMAND ----------

# ---------- Métrica ----------
r = q(f"SELECT count(*) n, count(DISTINCT venta_id) d FROM {OB}.fact_venta")
prueba("oro", "fact_venta: clave única", "modelo", "métrica", "bloquea", r.n == r.d, r.n - r.d, f"{r.n} líneas")

r = q(f"""SELECT
  (SELECT count(*) FROM {OB}.fact_venta f LEFT ANTI JOIN {OB}.dim_tiempo   d USING (fecha_key)) t,
  (SELECT count(*) FROM {OB}.fact_venta f LEFT ANTI JOIN {OB}.dim_producto d USING (producto_anada_key)) p,
  (SELECT count(*) FROM {OB}.fact_venta f LEFT ANTI JOIN {OB}.dim_cliente  d USING (cliente_key)) c,
  (SELECT count(*) FROM {OB}.fact_venta f LEFT ANTI JOIN {OB}.dim_mercado  d USING (mercado_key)) m""")
huerf = r.t + r.p + r.c + r.m
prueba("oro", "fact_venta: sin huérfanos en las cuatro dimensiones", "modelo", "métrica", "bloquea", huerf == 0,
       huerf, f"tiempo {r.t}, producto {r.p}, cliente {r.c}, mercado {r.m}")

r = q(f"""SELECT min(fecha_key) mn, max(fecha_key) mx,
                 sum(CASE WHEN fecha_key < 20250101 OR fecha_key > 20261231 THEN 1 ELSE 0 END) fuera
          FROM {OB}.fact_venta""")
prueba("oro", "Fechas de factura dentro del período (2025 en la métrica; 2026 queda fuera por filtro)",
       "modelo", "métrica", "bloquea", (r.fuera or 0) == 0, r.fuera, f"facturas entre {r.mn} y {r.mx}")

r = q(f"""SELECT (SELECT sum(litros) FROM {PL}.ventas) lp, (SELECT sum(litros) FROM {OB}.fact_venta) lo,
                 (SELECT count(*) FROM {PL}.ventas) np, (SELECT count(*) FROM {OB}.fact_venta) no""")
ok = r.np == r.no and abs(r.lp - r.lo) < 1e-6
prueba("oro", "Conciliación plata → oro: no se pierden líneas ni litros", "modelo", "métrica", "bloquea", ok,
       abs(r.np - r.no), f"plata {r.np} líneas y {r.lp:,.0f} L; oro {r.no} líneas y {r.lo:,.0f} L")

r = q(f"SELECT sum(CASE WHEN litros = 0 OR litros IS NULL THEN 1 ELSE 0 END) malos FROM {OB}.fact_venta")
prueba("oro", "Litros distintos de cero en todas las líneas", "modelo", "métrica", "bloquea", (r.malos or 0) == 0,
       r.malos)

r = q(f"""SELECT sum(CASE WHEN descuento_num NOT BETWEEN 0 AND 0.30 THEN 1 ELSE 0 END) d,
                 sum(CASE WHEN canal = 'Exportación' AND precio_unitario_num NOT BETWEEN 15 AND 120 THEN 1 ELSE 0 END) p
          FROM {PL}.ventas""")
prueba("plata", "Precio de lista (15–120 USD por caja) y descuento (0–30 %) dentro de rango", "origen_vina.sqlite",
       "métrica", "avisa", (r.d or 0) + (r.p or 0) == 0, (r.d or 0) + (r.p or 0),
       f"descuentos fuera de rango {r.d}; precios fuera de rango {r.p}")

r = q(f"""SELECT
  round(sum(CASE WHEN semestre = 1 THEN ingreso END) / sum(CASE WHEN semestre = 1 THEN litros END), 3) p1,
  round(sum(CASE WHEN semestre = 2 THEN ingreso END) / sum(CASE WHEN semestre = 2 THEN litros END), 3) p2,
  sum(lineas) n
  FROM {OB}.agg_escenarios
  WHERE correcciones = 'Con todas las correcciones (principal)' AND litros_caja_magnum = 9.0 AND moneda_fecha = 'USD'""")
ok = float(r.p1) == 4.574 and float(r.p2) == 5.085 and r.n == 10672
prueba("oro", "Cifras de control de la E1 (4,574 y 5,085 USD/L; 10.672 líneas)", "modelo", "métrica", "avisa", ok,
       0 if ok else 1, f"S1 {r.p1} USD/L, S2 {r.p2} USD/L, {r.n} líneas")

if existe(f"{O}.fact_venta"):
    r = q(f"""SELECT (SELECT count(*) FROM {O}.fact_venta) n0, (SELECT count(*) FROM {OB}.fact_venta) n1,
                     (SELECT round(sum(monto_neto_usd), 2) FROM {O}.fact_venta) m0,
                     (SELECT round(sum(monto_neto_usd), 2) FROM {OB}.fact_venta) m1""")
    ok, det = (r.n0 == r.n1 and r.m0 == r.m1), f"corrida anterior {r.n0} líneas y USD {r.m0:,.2f}; esta {r.n1} y USD {r.m1:,.2f}"
else:
    ok, det = True, "primera corrida: no hay oro publicado con qué comparar"
prueba("oro", "Idempotencia: mismas entradas dejan las mismas líneas y montos que la corrida anterior", "modelo",
       "operación", "avisa", ok, 0 if ok else 1, det)

r = q(f"""SELECT sum(litros_costo_real) / sum(litros_abs) c FROM {OB}.agg_escenarios
          WHERE correcciones = 'Con todas las correcciones (principal)' AND litros_caja_magnum = 9.0 AND moneda_fecha = 'USD'""")
prueba("oro", "Acuerdo de servicio: al menos 80 % de los litros con costo real (no imputado)", "modelo",
       "acuerdo de servicio (completitud)", "avisa", r.c >= 0.80, 0, f"cobertura {r.c:.1%}")

r = q(f"SELECT (SELECT count(*) FROM {OB}.fact_venta) n, (SELECT count(*) FROM {B}.erp_ventas) c")
prueba("oro", "Acuerdo de servicio: al menos 98 % de las ventas registradas llega a fact_venta", "modelo",
       "acuerdo de servicio (completitud)", "avisa", r.n / r.c >= 0.98, r.c - r.n, f"{r.n} de {r.c} ({r.n / r.c:.1%})")

# COMMAND ----------

filas = comun.registrar_pruebas(spark, CAT, RUN_ID, pruebas)
bloqueantes = [p for p in pruebas if p["severidad"] == "bloquea" and not p["paso_ok"]]
resumen = {"pruebas": len(pruebas), "pasan": sum(p["paso_ok"] for p in pruebas),
           "fallan_bloqueantes": [p["prueba"] for p in bloqueantes],
           "fallan_avisos": [p["prueba"] for p in pruebas if p["severidad"] == "avisa" and not p["paso_ok"]]}
comun.registrar_paso(spark, CAT, RUN_ID, "05_pruebas", "falla" if bloqueantes else "ok", INICIO, json.dumps(resumen, ensure_ascii=False))
display(spark.table(f"{CAT}.ops.dq_resultados").where(f"run_id = '{RUN_ID}'"))
if bloqueantes:
    raise Exception("Pruebas bloqueantes en rojo; el oro no se publica: " + "; ".join(resumen["fallan_bloqueantes"]))
dbutils.notebook.exit(json.dumps(resumen, ensure_ascii=False))
