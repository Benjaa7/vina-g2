"""Genera el tablero AI/BI de la E2 (vallehondo.lvdash.json).

El tablero es código: este script escribe el JSON que `correr_e2` publica en Databricks. Todas las cifras salen
del oro publicado (`oro.mv_vallehondo` y sus vistas); el tablero no redefine ninguna fórmula.

Uso:  python generar_tablero.py            -> escribe vallehondo.lvdash.json junto a este archivo
"""
import json
from pathlib import Path

CATALOGO, ESQUEMA = "vallehondo", "oro"
VINO, GRIS, ROSA, TOSTADO, AZUL = "#7B2D43", "#9AA5B1", "#C0697D", "#D4A373", "#3C6E91"
VERDE, AMBAR = "#2A9D8F", "#E9A23B"
TIERS = ["Varietal", "Reserva", "Gran Reserva"]
COLOR_TIER = [{"value": "Varietal", "color": TOSTADO}, {"value": "Reserva", "color": AZUL},
              {"value": "Gran Reserva", "color": VINO}]
COLOR_SEM = [{"value": "1.er sem.", "color": GRIS}, {"value": "2.º sem.", "color": VINO}]
COLOR_APORTE = [{"value": "Mezcla", "color": VINO}, {"value": "Precio", "color": GRIS},
                {"value": "Cruzado", "color": GRIS}, {"value": "Alza total", "color": AZUL}]

ESC = ("WITH esc AS (SELECT DISTINCT correcciones, litros_caja_magnum, litros_caja_etiqueta, moneda_fecha, moneda, orden_moneda "
       "FROM agg_escenarios)")
CLAVE = "USING (correcciones, litros_caja_magnum, moneda_fecha)"

FILTRO_ESC = ("e.moneda_fecha = :moneda AND e.correcciones = :correcciones "
              "AND e.litros_caja_etiqueta = :litros")
FILTRO_ESC_SIN_MONEDA = "e.correcciones = :correcciones AND e.litros_caja_etiqueta = :litros"
FILTRO_MV = "moneda_fecha = :moneda AND correcciones = :correcciones AND litros_caja_etiqueta = :litros"

# Parámetros con su valor por defecto (el escenario principal). Un parámetro siempre tiene un valor, así que los
# filtros del tablero no ofrecen "Todos", que mezclaría escenarios en una misma cifra.
DEFECTOS = {"moneda": "USD", "correcciones": "Con todas las correcciones (principal)",
            "litros": "9,0 L (principal)", "mercado": "Todos los mercados"}

DATASETS = {
    "ds_resumen": ("Resumen por escenario y mercado", f"""{ESC}
SELECT e.correcciones, e.litros_caja_etiqueta, e.moneda_fecha, e.moneda, t.mercado,
       t.precio_s1, t.precio_s2, t.alza_pct, t.mezcla_pct_del_alza, t.precio_pct_del_alza,
       t.gran_reserva_s1, t.gran_reserva_s2
FROM v_descomposicion_total t JOIN esc e {CLAVE}
WHERE {FILTRO_ESC} AND t.mercado = :mercado""", ["moneda", "correcciones", "litros", "mercado"]),
    "ds_puente": ("Puente mezcla / precio / cruzado", f"""{ESC}
SELECT e.correcciones, e.litros_caja_etiqueta, e.moneda_fecha, t.mercado,
       stack(4, 1, 'Mezcla', t.efecto_mezcla, 2, 'Precio', t.efecto_precio,
             3, 'Cruzado', t.efecto_cruzado, 4, 'Alza total', t.precio_s2 - t.precio_s1) AS (orden, componente, valor)
FROM v_descomposicion_total t JOIN esc e {CLAVE}
WHERE {FILTRO_ESC} AND t.mercado = :mercado
ORDER BY orden""", ["moneda", "correcciones", "litros", "mercado"]),
    "ds_tier": ("Participación y precio por tier", f"""{ESC}
SELECT e.correcciones, e.litros_caja_etiqueta, e.moneda_fecha, d.mercado, d.tier,
       stack(2, '1.er sem.', d.participacion_s1, d.precio_s1,
                '2.º sem.', d.participacion_s2, d.precio_s2) AS (semestre, participacion, precio_litro)
FROM v_descomposicion d JOIN esc e {CLAVE}
WHERE {FILTRO_ESC} AND d.mercado = :mercado""", ["moneda", "correcciones", "litros", "mercado"]),
    "ds_mercados": ("Lectura por mercado", f"""{ESC}
SELECT e.correcciones, e.litros_caja_etiqueta, e.moneda_fecha, m.mercado, m.zona, m.hemisferio, m.lectura,
       m.motivo_hipotesis, m.alza_pct, m.mezcla_pct_del_alza, m.gran_reserva_s1, m.gran_reserva_s2,
       m.precio_s1, m.precio_s2, m.margen_litro_s1, m.margen_litro_s2, m.alza_margen_litro_pct,
       m.cobertura_costo_real, m.lineas, m.litros_anuales
FROM v_mercados m JOIN esc e {CLAVE}
WHERE {FILTRO_ESC}
ORDER BY m.litros_anuales DESC""", ["moneda", "correcciones", "litros"]),
    "ds_valor": ("Valor de un punto de mezcla (CLP)", f"""{ESC}
SELECT e.correcciones, e.litros_caja_etiqueta, v.moneda_fecha AS fecha_dolar,
       v.valor_punto_vs_varietal / 1e6 AS valor_punto_varietal_mm,
       v.valor_punto_vs_reserva / 1e6 AS valor_punto_reserva_mm,
       v.valor_caja_vs_varietal, v.cajas_por_punto
FROM v_valor_punto v JOIN esc e {CLAVE}
WHERE v.moneda_fecha IN ('CLP · fecha de factura', 'CLP · cobranza estimada') AND {FILTRO_ESC_SIN_MONEDA}
ORDER BY fecha_dolar DESC""", ["correcciones", "litros"]),
    "ds_estado": ("Estado de la última corrida", """SELECT concat(pruebas_en_verde, ' de ', pruebas_total, ' en verde') AS pruebas,
       date_format(from_utc_timestamp(ultima_actualizacion_utc, 'America/Santiago'), 'yyyy-MM-dd HH:mm') AS actualizado,
       run_id AS corrida, dolar, dueno_dato, periodo, fuente
FROM v_estado_corrida""", []),
    "ds_mes_tier": ("Precio por litro por mes y tier (metric view)", f"""SELECT tier, make_date(2025, CAST(mes AS INT), 1) AS mes,
       MEASURE(precio_por_litro) AS precio_por_litro
FROM mv_vallehondo
WHERE {FILTRO_MV}
GROUP BY ALL""", ["moneda", "correcciones", "litros"]),
    "ds_mes": ("Gran reserva por mes (metric view)", f"""SELECT make_date(2025, CAST(mes AS INT), 1) AS mes,
       MEASURE(participacion_gran_reserva) AS participacion_gran_reserva, MEASURE(precio_por_litro) AS precio_por_litro
FROM mv_vallehondo
WHERE {FILTRO_MV}
GROUP BY ALL""", ["moneda", "correcciones", "litros"]),
    "ds_monedas": ("El alza según la moneda y la fecha del dólar", f"""{ESC}
SELECT e.moneda_fecha, e.orden_moneda, t.precio_s1, t.precio_s2, t.alza_pct, t.mezcla_pct_del_alza
FROM v_descomposicion_total t JOIN esc e {CLAVE}
WHERE {FILTRO_ESC_SIN_MONEDA} AND t.mercado = 'Todos los mercados'
ORDER BY e.orden_moneda""", ["correcciones", "litros"]),
    "ds_pruebas": ("Pruebas de calidad de la última corrida", """SELECT capa, prueba, severidad, resultado, filas_fallan, accion, detalle
FROM v_pruebas
ORDER BY CASE resultado WHEN 'falla' THEN 0 ELSE 1 END, capa, prueba""", []),
    # Solo para poblar las opciones de los filtros.
    "op_moneda": ("Opciones: moneda y fecha del dólar",
                  "SELECT DISTINCT moneda_fecha, orden_moneda FROM agg_escenarios ORDER BY orden_moneda", []),
    "op_correcciones": ("Opciones: correcciones",
                        "SELECT DISTINCT correcciones, orden_correcciones FROM agg_escenarios ORDER BY orden_correcciones", []),
    "op_litros": ("Opciones: litros por caja magnum",
                  "SELECT DISTINCT litros_caja_etiqueta, litros_caja_magnum FROM agg_escenarios ORDER BY litros_caja_magnum DESC", []),
    "op_mercado": ("Opciones: mercado",
                   "SELECT DISTINCT mercado FROM v_descomposicion_total ORDER BY mercado = 'Todos los mercados' DESC, mercado", []),
}


def dataset(nombre, titulo, sql, parametros):
    lineas = sql.strip().split("\n")
    d = {"name": nombre, "displayName": titulo, "queryLines": [l + "\n" for l in lineas],
         "catalog": CATALOGO, "schema": ESQUEMA}
    if parametros:
        d["parameters"] = [{"displayName": p, "keyword": p, "dataType": "STRING", "defaultSelection": {
            "values": {"dataType": "STRING", "values": [{"value": DEFECTOS[p]}]}}} for p in parametros]
    return d


def pos(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def texto(nombre, lineas, p):
    return {"widget": {"name": nombre, "multilineTextboxSpec": {"lines": lineas}}, "position": p}


def campo(nombre, expr=None):
    return {"name": nombre, "expression": expr or f"`{nombre}`"}


def consulta(ds, campos, desagregado=False, filtros=None):
    q = {"datasetName": ds, "fields": campos, "disaggregated": desagregado}
    if filtros:
        q["filters"] = [{"expression": f} for f in filtros]
    return [{"name": "main_query", "query": q}]


def marco(titulo, descripcion=None):
    m = {"showTitle": True, "title": titulo}
    if descripcion:
        m.update({"showDescription": True, "description": descripcion})
    return m


def fmt_num(dec, exacto=False):
    return {"type": "number-plain", "abbreviation": "none", "decimalPlaces": {"type": "exact" if exacto else "max", "places": dec}}


def fmt_pct(dec):
    return {"type": "number-percent", "decimalPlaces": {"type": "max", "places": dec}}


def contador(nombre, ds, valor, titulo, descripcion, formato, p, meta=None, filtros=None, plantilla=None):
    campos = [campo(f"min({valor})", f"MIN(`{valor}`)")]
    enc = {"value": {"fieldName": f"min({valor})", "format": formato}}
    if plantilla:
        enc["value"]["formatTemplate"] = plantilla
    if meta:
        campos.append(campo(f"min({meta})", f"MIN(`{meta}`)"))
        enc["target"] = {"fieldName": f"min({meta})", "displayName": "1.er semestre", "format": formato}
    return {"widget": {"name": nombre, "queries": consulta(ds, campos, filtros=filtros),
                       "spec": {"version": 2, "widgetType": "counter", "encodings": enc,
                                "frame": marco(titulo, descripcion)}}, "position": p}


def barras(nombre, ds, y, y_nombre, formato, titulo, descripcion, p):
    campos = [campo("tier"), campo("semestre"), campo(f"sum({y})", f"SUM(`{y}`)")]
    spec = {"version": 3, "widgetType": "bar",
            "encodings": {
                "x": {"fieldName": "tier", "displayName": "Tier",
                      "scale": {"type": "categorical", "sort": {"by": "custom-order", "orderedValues": TIERS}}},
                "y": {"fieldName": f"sum({y})", "displayName": y_nombre, "scale": {"type": "quantitative"},
                      "format": formato},
                "color": {"fieldName": "semestre", "displayName": "Semestre",
                          "scale": {"type": "categorical", "mappings": COLOR_SEM},
                          "legend": {"hide": True}},
                "label": {"show": True}},
            "mark": {"layout": "group"}, "frame": marco(titulo, descripcion)}
    return {"widget": {"name": nombre, "queries": consulta(ds, campos), "spec": spec}, "position": p}


def tabla(nombre, ds, columnas, titulo, descripcion, p):
    campos = [campo(c[0]) for c in columnas]
    cols = []
    for c in columnas:
        col = {"fieldName": c[0], "displayName": c[1]}
        if len(c) > 2 and c[2]:
            col["format"] = c[2]
        cols.append(col)
    return {"widget": {"name": nombre, "queries": consulta(ds, campos, desagregado=True),
                       "spec": {"version": 2, "widgetType": "table", "encodings": {"columns": cols},
                                "frame": marco(titulo, descripcion)}}, "position": p}


def filtro(nombre, titulo, opciones, campo_op, parametro, datasets, p):
    queries = [{"name": f"{nombre}_opciones", "query": {"datasetName": opciones, "fields": [campo(campo_op)],
                                                       "disaggregated": False}}]
    fields = [{"fieldName": campo_op, "displayName": titulo, "queryName": f"{nombre}_opciones"}]
    for ds in datasets:
        qn = f"{nombre}_{ds}"
        queries.append({"name": qn, "query": {"datasetName": ds, "parameters": [{"name": parametro, "keyword": parametro}],
                                              "disaggregated": False}})
        fields.append({"parameterName": parametro, "queryName": qn})
    spec = {"version": 2, "widgetType": "filter-single-select", "encodings": {"fields": fields},
            "selection": {"defaultSelection": {"values": {"dataType": "STRING",
                                                          "values": [{"value": DEFECTOS[parametro]}]}}},
            "frame": marco(titulo)}
    return {"widget": {"name": nombre, "queries": queries, "spec": spec}, "position": p}


def filtros_escenario(prefijo, ds_moneda, ds_resto, y, con_mercado=None):
    ancho = 3 if con_mercado else 4
    out = [
        filtro(f"{prefijo}_moneda", "Moneda y fecha del dólar", "op_moneda", "moneda_fecha", "moneda", ds_moneda,
               pos(0, y, ancho, 2)),
        filtro(f"{prefijo}_correcciones", "Correcciones de datos", "op_correcciones", "correcciones", "correcciones",
               ds_resto, pos(ancho, y, ancho, 2)),
        filtro(f"{prefijo}_litros", "Litros por caja magnum", "op_litros", "litros_caja_etiqueta", "litros", ds_resto,
               pos(2 * ancho, y, ancho, 2)),
    ]
    if con_mercado:
        out.append(filtro(f"{prefijo}_mercado", "Mercado", "op_mercado", "mercado", "mercado", con_mercado,
                          pos(9, y, 3, 2)))
    return out


ESTADO = tabla("t_estado", "ds_estado",
               [("actualizado", "Actualizado (hora de Chile)"), ("pruebas", "Pruebas de calidad"),
                ("dolar", "Dólar observado"), ("dueno_dato", "Dueño del dato"), ("periodo", "Período"),
                ("fuente", "Fuentes"), ("corrida", "Corrida")],
               "Estado del dato", None, pos(0, 0, 12, 3))

# --------------------------------------------------------------------------------------------- página 1
P1 = [texto("titulo", [
    "## ¿El alza del precio por litro de exportación fue por precio o por mezcla?\n", "\n",
    "Facturas de exportación 2025; primer semestre = enero a junio, segundo = julio a diciembre. "
    "Con la definición principal, casi toda el alza viene de vender más **gran reserva**: el precio dentro de "
    "cada tier no subió. Cambie la moneda, la fecha del dólar, las correcciones o los litros por caja y todo se "
    "recalcula. Al final, la tabla dice si cada mercado es recomendación o hipótesis; la pestaña "
    "**Definición y calidad** compara las monedas y fechas del dólar lado a lado."], pos(0, 0, 12, 2))]
P1 += filtros_escenario("f1", ["ds_resumen", "ds_puente", "ds_tier", "ds_mercados"],
                        ["ds_resumen", "ds_puente", "ds_tier", "ds_mercados", "ds_valor"], 2,
                        con_mercado=["ds_resumen", "ds_puente", "ds_tier"])
P1 += [
    contador("c_alza", "ds_resumen", "alza_pct", "Alza del precio por litro",
             "2.º semestre contra el 1.º, en la moneda elegida.", fmt_pct(1), pos(0, 4, 2, 5)),
    contador("c_precio", "ds_resumen", "precio_s2", "Precio medio por litro, 2.º semestre",
             "Abajo, el 1.er semestre. USD/L o CLP/L según la moneda.", fmt_num(2, True),
             pos(2, 4, 3, 5), meta="precio_s1"),
    contador("c_mezcla", "ds_resumen", "mezcla_pct_del_alza", "Parte del alza que explica la mezcla",
             "Sobre 100 % porque el precio restó.", fmt_pct(0), pos(5, 4, 2, 5)),
    contador("c_gr", "ds_resumen", "gran_reserva_s2", "Gran reserva, % de los litros, 2.º semestre",
             "Abajo, el 1.er semestre.", fmt_pct(1), pos(7, 4, 2, 5), meta="gran_reserva_s1"),
    contador("c_valor", "ds_valor", "valor_punto_varietal_mm", "Valor de 1 punto de gran reserva (MM CLP)",
             "Margen extra al año, en millones de pesos, si 1 % de los litros pasa de varietal a gran reserva.", fmt_num(0),
             pos(9, 4, 3, 5), filtros=["`fecha_dolar` = 'CLP · fecha de factura'"], plantilla="{{@formatted}} MM"),
    {"widget": {"name": "w_puente",
                "queries": consulta("ds_puente", [campo("componente"), campo("sum(valor)", "SUM(`valor`)")]),
                "spec": {"version": 3, "widgetType": "bar",
                         "encodings": {
                             "x": {"fieldName": "componente", "displayName": "Componente",
                                   "scale": {"type": "categorical", "sort": {"by": "custom-order", "orderedValues": [
                                       "Mezcla", "Precio", "Cruzado", "Alza total"]}}},
                             "y": {"fieldName": "sum(valor)", "displayName": "Por litro, en la moneda elegida",
                                   "scale": {"type": "quantitative"}, "format": fmt_num(3)},
                             "color": {"fieldName": "componente", "displayName": "Componente",
                                       "scale": {"type": "categorical", "mappings": COLOR_APORTE},
                                       "legend": {"hide": True}},
                             "label": {"show": True}},
                         "frame": marco("¿De dónde sale el alza del precio por litro?",
                                        "Mezcla, precio y cruzado suman el alza total. La mezcla aporta más que el total porque el precio y el cruzado restan.")}},
     "position": pos(0, 9, 4, 6)},
    barras("w_mezcla", "ds_tier", "participacion", "% de los litros", fmt_pct(0),
           "Participación de cada tier en los litros",
           "Qué parte de los litros es de cada tier. Gris: 1.er semestre; vino: 2.º semestre.",
           pos(4, 9, 4, 6)),
    barras("w_precio_tier", "ds_tier", "precio_litro", "Precio por litro", fmt_num(2),
           "Precio por litro dentro de cada tier",
           "Cuánto se cobró por litro en cada tier. Gris: 1.er semestre; vino: 2.º semestre.",
           pos(8, 9, 4, 6)),
    tabla("t_valor", "ds_valor",
          [("fecha_dolar", "Dólar a la"), ("valor_punto_varietal_mm", "1 punto GR en vez de varietal (MM CLP/año)", fmt_num(0)),
           ("valor_punto_reserva_mm", "1 punto GR en vez de reserva (MM CLP/año)", fmt_num(0)),
           ("valor_caja_vs_varietal", "Margen extra por caja GR vs varietal (CLP)", fmt_num(0)),
           ("cajas_por_punto", "Cajas que son 1 punto", fmt_num(0))],
          "Cuánto vale mover la mezcla (margen bruto, CLP)",
          "Una acción para vender más gran reserva se paga si su costo anual es menor que los puntos que mueve por el valor de un punto.",
          pos(0, 15, 12, 3)),
    tabla("t_mercados", "ds_mercados",
          [("mercado", "Mercado"), ("lectura", "Lectura"), ("alza_pct", "Alza precio/L", fmt_pct(1)),
           ("mezcla_pct_del_alza", "Mezcla, % del alza", fmt_pct(0)), ("gran_reserva_s1", "GR 1.er sem.", fmt_pct(0)),
           ("gran_reserva_s2", "GR 2.º sem.", fmt_pct(0)), ("precio_s1", "Precio/L 1.er sem.", fmt_num(2)),
           ("precio_s2", "Precio/L 2.º sem.", fmt_num(2)), ("alza_margen_litro_pct", "Alza margen/L", fmt_pct(1)),
           ("cobertura_costo_real", "Litros con costo real", fmt_pct(0)), ("lineas", "Líneas", fmt_num(0)),
           ("hemisferio", "Hemisferio"), ("motivo_hipotesis", "Por qué es hipótesis")],
          "Por mercado: ¿recomendación o hipótesis?",
          "Recomendación si el precio por litro sube, la mezcla explica al menos 80 % del alza, gran reserva sube al menos "
          "5 puntos, al menos 80 % de los litros tiene costo real y hay al menos 300 líneas. Si falla algo, es hipótesis.",
          pos(0, 18, 12, 7)),
]
e1 = json.loads(json.dumps(ESTADO)); e1["position"] = pos(0, 25, 12, 3)
P1.append(e1)

# --------------------------------------------------------------------------------------------- página 2
DEF = [
    "### Definición única\n", "\n",
    "**Precio medio por litro** = Σ ingreso neto ÷ Σ litros. Universo: líneas de exportación con factura de 2025; "
    "semestre según la fecha de factura.\n", "\n",
    "**Litros** = cajas × 9 L (12×750 y 6×1500). Los magnum a 18 o 4,5 L son extremos hipotéticos, no datos.\n", "\n",
    "**Pesos (CLP)**: cada línea se convierte con el dólar observado de su propia fecha (factura, cobranza estimada "
    "o embarque), nunca con un promedio anual.\n", "\n",
    "**Mezcla, precio y cruzado** (base 1.er semestre): mezcla = Σ(w₂−w₁)·p₁; precio = Σw₁·(p₂−p₁); "
    "cruzado = Σ(w₂−w₁)(p₂−p₁); w = participación de litros del tier, p = su precio por litro.\n", "\n",
    "**Margen bruto** = ingreso neto − costo de producto del maestro de costos. Si falta el costo, se imputa y "
    "la cobertura lo dice.\n", "\n",
    "**Valor de un punto de gran reserva** = 1 % de los litros del año × (margen/L gran reserva − margen/L varietal).\n",
    "\n",
    "Estas fórmulas viven una sola vez en la metric view `oro.mv_vallehondo` de Unity Catalog; el tablero, "
    "las vistas y las cifras del informe leen de ella.",
]
P2 = [texto("titulo2", ["## Definición y calidad del dato\n", "\n",
                        "Los gráficos de esta página leen directo de la metric view. Abajo, las pruebas que corren "
                        "antes de publicar: si una bloqueante falla, el oro no se actualiza."], pos(0, 0, 12, 2))]
P2 += filtros_escenario("f2", ["ds_mes_tier", "ds_mes"], ["ds_mes_tier", "ds_mes", "ds_monedas"], 2)
P2 += [
    tabla("t_monedas", "ds_monedas",
          [("moneda_fecha", "Moneda y fecha del dólar"), ("precio_s1", "Precio/L 1.er sem.", fmt_num(2)),
           ("precio_s2", "Precio/L 2.º sem.", fmt_num(2)), ("alza_pct", "Alza del precio por litro", fmt_pct(1)),
           ("mezcla_pct_del_alza", "Mezcla, % del alza", fmt_pct(0))],
          "La decisión de definición: ¿con qué dólar se convierte?",
          "Todos los mercados. En dólares el alza no depende de la fecha; en pesos, sí. La fecha de embarque no es confiable: en 30 % de las líneas es anterior a la factura.",
          pos(0, 4, 12, 4)),
    {"widget": {"name": "w_precio_mes",
                "queries": consulta("ds_mes_tier", [campo("monthly(mes)", 'DATE_TRUNC("MONTH", `mes`)'), campo("tier"),
                                                    campo("min(precio_por_litro)", "MIN(`precio_por_litro`)")]),
                "spec": {"version": 3, "widgetType": "line",
                         "encodings": {
                             "x": {"fieldName": "monthly(mes)", "displayName": "Mes", "scale": {"type": "temporal"}},
                             "y": {"fieldName": "min(precio_por_litro)", "displayName": "Precio por litro",
                                   "scale": {"type": "quantitative"}, "format": fmt_num(2)},
                             "color": {"fieldName": "tier", "displayName": "Tier",
                                       "scale": {"type": "categorical", "mappings": COLOR_TIER}}},
                         "frame": marco("Precio por litro de cada tier, mes a mes",
                                        "Todos los mercados. MEASURE(precio_por_litro) por tier.")}},
     "position": pos(0, 8, 6, 6)},
    {"widget": {"name": "w_gr_mes",
                "queries": consulta("ds_mes", [campo("monthly(mes)", 'DATE_TRUNC("MONTH", `mes`)'),
                                               campo("min(participacion_gran_reserva)", "MIN(`participacion_gran_reserva`)")]),
                "spec": {"version": 3, "widgetType": "line",
                         "encodings": {
                             "x": {"fieldName": "monthly(mes)", "displayName": "Mes", "scale": {"type": "temporal"}},
                             "y": {"fieldName": "min(participacion_gran_reserva)", "displayName": "Gran reserva, % de los litros",
                                   "scale": {"type": "quantitative"}, "format": fmt_pct(0)}},
                         "annotations": [{"type": "vertical-line", "encodings": {
                             "x": {"dataValue": "2025-07-01T00:00:00.000", "dataType": "DATETIME"},
                             "label": {"value": "Comienza el 2.º semestre"},
                             "color": {"value": GRIS}}}],
                         "frame": marco("Gran reserva, % de los litros, mes a mes",
                                        "Todos los mercados. MEASURE(participacion_gran_reserva).")}},
     "position": pos(6, 8, 6, 6)},
    texto("definicion", DEF, pos(0, 14, 5, 9)),
    tabla("t_pruebas", "ds_pruebas",
          [("resultado", "Resultado"), ("severidad", "Severidad"), ("capa", "Capa"), ("prueba", "Prueba"),
           ("filas_fallan", "Filas que fallan", fmt_num(0)), ("accion", "Qué se hizo"), ("detalle", "Detalle")],
          "Pruebas de calidad de la última corrida",
          "Bloquea: si falla, el job se detiene y el tablero sigue mostrando el último oro bueno. Avisa: se publica y se informa.",
          pos(5, 14, 7, 9)),
]
e2 = json.loads(json.dumps(ESTADO)); e2["position"] = pos(0, 23, 12, 3)
P2.append(e2)

TABLERO = {
    "datasets": [dataset(n, t, q, par) for n, (t, q, par) in DATASETS.items()],
    "pages": [
        {"name": "respuesta", "displayName": "Respuesta", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1",
         "layout": P1},
        {"name": "definicion", "displayName": "Definición y calidad", "pageType": "PAGE_TYPE_CANVAS",
         "layoutVersion": "GRID_V1", "layout": P2},
    ],
    "uiSettings": {"theme": {
        "canvasBackgroundColor": {"light": "#FAF8F6", "dark": "#1F1A1C"},
        "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#141012"},
        "widgetBorderColor": {"light": "#FFFFFF", "dark": "#141012"},
        "fontColor": {"light": "#2B1D22", "dark": "#EDE6E8"},
        "selectionColor": {"light": "#2272B4", "dark": "#8ACAFF"},
        "visualizationColors": [VINO, "#3C6E91", TOSTADO, "#5E8C6A", ROSA, "#4A4E69", "#E9C46A"],
        "widgetHeaderAlignment": "LEFT"}},
}

if __name__ == "__main__":
    salida = Path(__file__).with_name("vallehondo.lvdash.json")
    salida.write_text(json.dumps(TABLERO, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{salida} ({salida.stat().st_size} bytes, {sum(len(p['layout']) for p in TABLERO['pages'])} widgets)")
