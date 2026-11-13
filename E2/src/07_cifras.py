# Databricks notebook source
# MAGIC %md
# MAGIC # 07 · Cifras del informe
# MAGIC Todas las cifras que cita el informe salen de aquí, y todas se leen de la definición única
# MAGIC (`oro.mv_vallehondo` y las vistas del oro). Quedan en `ops.cifras_informe` y en `ops.salidas/cifras.md`.

# COMMAND ----------

import json, os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "lib"))
import comun
import pandas as pd

P = comun.parametros(dbutils, {"catalogo": "vallehondo", "run_id": "", "dir_raw": "", "dir_lib": ""})
CAT, RUN_ID, INICIO = P["catalogo"], P["run_id"], comun.ahora()
O = f"{CAT}.oro"
PRINCIPAL = "correcciones = 'Con todas las correcciones (principal)' AND litros_caja_magnum = 9.0"
cifras = []

def cifra(seccion, nombre, valor, unidad, definicion):
    cifras.append({"seccion": seccion, "cifra": nombre, "valor": None if valor is None else float(valor),
                   "unidad": unidad, "definicion": definicion, "run_id": RUN_ID})

# COMMAND ----------

d = spark.sql(f"SELECT * FROM {O}.v_descomposicion_total WHERE mercado = 'Todos los mercados'").toPandas()
def fila(corr="Con todas las correcciones (principal)", lpc=9.0, mon="USD"):
    x = d[(d.correcciones == corr) & (d.litros_caja_magnum == lpc) & (d.moneda_fecha == mon)]
    return x.iloc[0]

r = fila()
cifra("Métrica", "Precio medio por litro, primer semestre", r.precio_s1, "USD/L", "Σ ingreso neto USD ÷ Σ litros; exportación, facturas ene–jun 2025")
cifra("Métrica", "Precio medio por litro, segundo semestre", r.precio_s2, "USD/L", "Ídem, facturas jul–dic 2025")
cifra("Métrica", "Alza del precio medio por litro", 100 * r.alza_pct, "%", "S2 ÷ S1 − 1")
cifra("Métrica", "Mezcla, % del alza", 100 * r.mezcla_pct_del_alza, "%", "Σ (w2 − w1)·p1 ÷ (P2 − P1); base primer semestre")
cifra("Métrica", "Precio, % del alza", 100 * r.precio_pct_del_alza, "%", "Σ w1·(p2 − p1) ÷ (P2 − P1)")
cifra("Métrica", "Gran Reserva, % de los litros, primer semestre", 100 * r.gran_reserva_s1, "%", "litros GR ÷ litros")
cifra("Métrica", "Gran Reserva, % de los litros, segundo semestre", 100 * r.gran_reserva_s2, "%", "litros GR ÷ litros")

for mon in ["CLP · fecha de factura", "CLP · cobranza estimada", "CLP · fecha de embarque (no confiable)"]:
    r = fila(mon=mon)
    cifra("Fecha del dólar", f"Alza del precio por litro en pesos ({mon})", 100 * r.alza_pct, "%", "precio por litro en CLP, S2 ÷ S1 − 1")

m = spark.sql(f"""SELECT moneda_fecha, semestre, MEASURE(margen_por_litro) AS ml, MEASURE(margen_pct) AS mp
                  FROM {O}.mv_vallehondo WHERE {PRINCIPAL} GROUP BY moneda_fecha, semestre""").toPandas()
for mon in ["CLP · fecha de factura", "CLP · cobranza estimada"]:
    s1 = m[(m.moneda_fecha == mon) & (m.semestre == 1)].ml.iloc[0]
    s2 = m[(m.moneda_fecha == mon) & (m.semestre == 2)].ml.iloc[0]
    cifra("Fecha del dólar", f"Margen bruto por litro, primer semestre ({mon})", s1, "CLP/L", "(ingreso neto − costo de producto) ÷ litros")
    cifra("Fecha del dólar", f"Margen bruto por litro, segundo semestre ({mon})", s2, "CLP/L", "Ídem")
    cifra("Fecha del dólar", f"Alza del margen bruto por litro ({mon})", 100 * (s2 / s1 - 1), "%", "S2 ÷ S1 − 1")

# Tipo de cambio implícito de cada semestre: ingreso en pesos con esa fecha del dólar ÷ ingreso en dólares.
# Explica por qué el alza en pesos depende de la fecha; no se usa para convertir (cada línea usa el dólar de su día).
ing = spark.sql(f"""SELECT moneda_fecha, semestre, MEASURE(ingreso) AS ingreso
                    FROM {O}.mv_vallehondo WHERE {PRINCIPAL} GROUP BY moneda_fecha, semestre""").toPandas()
for sem in [1, 2]:
    usd = ing[(ing.moneda_fecha == "USD") & (ing.semestre == sem)].ingreso.iloc[0]
    for mon in ["CLP · fecha de factura", "CLP · cobranza estimada"]:
        clp = ing[(ing.moneda_fecha == mon) & (ing.semestre == sem)].ingreso.iloc[0]
        cifra("Fecha del dólar", f"Tipo de cambio implícito, {'primer' if sem == 1 else 'segundo'} semestre ({mon})",
              clp / usd, "CLP/USD", "ingreso neto en CLP con esa fecha ÷ ingreso neto en USD (promedio ponderado por monto)")

for corr in ["Sin montos recalculados", "Sin cajas corregidas", "Sin monedas imputadas", "Sin ninguna corrección"]:
    r = fila(corr=corr)
    cifra("Robustez", f"Alza del precio por litro, {corr.lower()}", 100 * r.alza_pct, "%", "escenario sin esa corrección")
    cifra("Robustez", f"Mezcla, % del alza, {corr.lower()}", 100 * r.mezcla_pct_del_alza, "%", "escenario sin esa corrección")
for lpc in [18.0, 4.5]:
    r = fila(lpc=lpc)
    cifra("Robustez", f"Mezcla, % del alza, magnum de {lpc:g} L por caja", 100 * r.mezcla_pct_del_alza, "%", "extremo hipotético")

vp = spark.sql(f"SELECT * FROM {O}.v_valor_punto WHERE {PRINCIPAL}").toPandas()
for mon in ["CLP · fecha de factura", "CLP · cobranza estimada"]:
    x = vp[vp.moneda_fecha == mon].iloc[0]
    cifra("Valor", f"Valor de un punto de gran reserva en vez de varietal ({mon})", x.valor_punto_vs_varietal / 1e6,
          "MM CLP de margen bruto al año", "1 % de los litros 2025 × (margen/L GR − margen/L varietal)")
    cifra("Valor", f"Valor de un punto de gran reserva en vez de reserva ({mon})", x.valor_punto_vs_reserva / 1e6,
          "MM CLP de margen bruto al año", "1 % de los litros 2025 × (margen/L GR − margen/L reserva)")
    cifra("Valor", f"Margen adicional por caja de gran reserva en vez de varietal ({mon})", x.valor_caja_vs_varietal,
          "CLP por caja", "9 L × (margen/L GR − margen/L varietal)")
cifra("Valor", "Cajas por punto de mezcla", vp.iloc[0].cajas_por_punto, "cajas al año", "1 % de los litros 2025 ÷ 9 L")

c = spark.sql(f"""SELECT MEASURE(cobertura_costo_real) cob, MEASURE(lineas) n FROM {O}.mv_vallehondo
                  WHERE {PRINCIPAL} AND moneda_fecha = 'USD'""").first()
cifra("Cobertura", "Litros con margen calculado con costo real", 100 * c.cob, "%", "litros con costo no imputado ÷ litros")
cifra("Cobertura", "Líneas en el universo de la métrica", c.n, "líneas", "exportación, facturas 2025")

# COMMAND ----------

df = pd.DataFrame(cifras)
comun.escribir(spark, df, f"{CAT}.ops.cifras_informe")
num = lambda x, u: (f"{x:,.3f}" if u in ("USD/L",) else f"{x:,.1f}" if u in ("%", "CLP/USD") else f"{x:,.0f}").replace(",", "X").replace(".", ",").replace("X", ".")
lineas = ["# Cifras del informe (E2)", "",
          f"Generado por el paso 07 del job, corrida `{RUN_ID}`. Todas salen de `oro.mv_vallehondo` y las vistas del oro.", ""]
for sec, g in df.groupby("seccion", sort=False):
    lineas += [f"## {sec}", "", "| Cifra | Valor | Unidad | Cómo se calcula |", "|---|---:|---|---|"]
    lineas += [f"| {r.cifra} | {num(r.valor, r.unidad)} | {r.unidad} | {r.definicion} |" for r in g.itertuples()]
    lineas.append("")
with open(f"{comun.volumen(CAT, 'ops', 'salidas')}/cifras.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lineas))
comun.registrar_paso(spark, CAT, RUN_ID, "07_cifras", "ok", INICIO, json.dumps({"cifras": len(df)}))
dbutils.notebook.exit(df[["cifra", "valor", "unidad"]].to_json(orient="records", force_ascii=False))
