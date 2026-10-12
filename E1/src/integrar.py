# -*- coding: utf-8 -*-
"""Integración: construye el modelo estrella definido en esquema.py y la tabla
integrada (la estrella ya unida) a partir de las ventas limpias.

Salidas:
    output/estrella/fact_venta.csv, dim_tiempo.csv, dim_producto.csv,
                    dim_cliente.csv, dim_mercado.csv
    output/tabla_integrada.csv

Grano (sección C): una fila es una línea de venta facturada: un producto de una
añada, vendido a un cliente en una fecha. fact_venta guarda las 13.845 líneas
deduplicadas, incluidas las facturas de 2026 y las ventas nacionales; la métrica
filtra exportación y facturas de 2025.
"""
import numpy as np
import pandas as pd

from esquema import TABLAS

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
NOMBRES_MES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
               "septiembre", "octubre", "noviembre", "diciembre"]


def columnas(tabla):
    return [c[0] for c in TABLAS[tabla]["columnas"]]


def verificar(df, tabla):
    faltan = [c for c in columnas(tabla) if c not in df.columns]
    if faltan:
        raise ValueError(f"{tabla}: faltan columnas del esquema {faltan}")


def dim_tiempo(fechas, dolar):
    """Un día por fila, desde el 1 de enero de 2025 hasta la última factura."""
    dias = pd.date_range("2025-01-01", fechas.max(), freq="D")
    publicados = set(dolar["fecha"].astype("datetime64[ns]"))
    t = pd.DataFrame({"fecha": dias})
    t["fecha_key"] = t["fecha"].dt.strftime("%Y%m%d").astype(int)
    t["dia_semana"] = t["fecha"].dt.dayofweek.map(dict(enumerate(DIAS)))
    t["semana"] = t["fecha"].dt.isocalendar().week.astype(int)
    t["mes"] = t["fecha"].dt.month
    t["nombre_mes"] = t["mes"].map(dict(enumerate(NOMBRES_MES, start=1)))
    t["trimestre"] = t["fecha"].dt.quarter
    t["semestre"] = np.where(t["mes"] <= 6, 1, 2)
    t["anio"] = t["fecha"].dt.year
    t["es_dia_habil"] = t["fecha"].isin(publicados).astype(int)
    t["es_feriado"] = ((t["fecha"].dt.dayofweek < 5) & (t["es_dia_habil"] == 0)).astype(int)
    t["fecha"] = t["fecha"].dt.date
    return t[["fecha_key", "fecha", "dia_semana", "semana", "mes", "nombre_mes", "trimestre",
              "semestre", "anio", "es_dia_habil", "es_feriado"]]


def dim_producto(pa, cepas):
    p = pa.merge(cepas[["cepa", "tipo"]].rename(columns={"tipo": "tipo_vino"}), on="cepa", how="left")
    p = p.sort_values(["producto_id", "anada"]).reset_index(drop=True)
    p.insert(0, "producto_anada_key", np.arange(1, len(p) + 1))
    p["activo"] = p["activo"].astype(int)
    return p[["producto_anada_key", "producto_id", "producto", "cepa", "tipo_vino", "tier", "formato",
              "litros_por_caja", "anada", "costo_caja_clp", "costo_imputado", "activo"]]


def dim_cliente(clientes):
    c = clientes.sort_values("cliente_id").reset_index(drop=True)
    c.insert(0, "cliente_key", np.arange(1, len(c) + 1))
    return c[["cliente_key", "cliente_id", "nombre", "tipo"]]   # el RUT queda fuera (C)


def dim_mercado(mercados, ventas):
    moneda = ventas.dropna(subset=["moneda_registrada"]).groupby("mercado_id")["moneda_registrada"]
    if (moneda.nunique() > 1).any():
        raise ValueError("un mercado factura en más de una moneda")
    m = mercados.sort_values("mercado_id").reset_index(drop=True)
    m["moneda_facturacion"] = m["mercado_id"].map(moneda.first())
    m.insert(0, "mercado_key", np.arange(1, len(m) + 1))
    return m[["mercado_key", "mercado_id", "pais", "zona", "canal", "hemisferio", "moneda_facturacion"]]


def montos(v):
    """Montos en las dos monedas, convertidos con el dólar del día de la factura."""
    usd = v["moneda"] == "USD"
    tc = v["tipo_cambio"]
    out = pd.DataFrame(index=v.index)
    for medida, col in [("bruto", "monto_bruto"), ("neto", "monto_neto")]:
        out[f"monto_{medida}_usd"] = np.where(usd, v[col], v[col] / tc)
        out[f"monto_{medida}_clp"] = np.where(usd, v[col] * tc, v[col])
    return out


def integrar(res, erp, raiz):
    v = res["ventas"].copy()
    tiempo = dim_tiempo(v["fecha_factura"], res["dolar"])
    producto = dim_producto(res["producto_anada"], erp["cepas"])
    cliente = dim_cliente(erp["clientes"])
    mercado = dim_mercado(res["mercados"], v)

    v = v.join(montos(v))
    v["fecha_key"] = v["fecha_factura"].dt.strftime("%Y%m%d").astype(int)
    v = v.merge(producto[["producto_anada_key", "producto_id", "anada"]], on=["producto_id", "anada"], how="left")
    v = v.merge(cliente[["cliente_key", "cliente_id"]], on="cliente_id", how="left")
    v = v.merge(mercado[["mercado_key", "mercado_id"]], on="mercado_id", how="left")
    if v[["producto_anada_key", "cliente_key", "mercado_key"]].isna().any().any():
        raise ValueError("líneas de venta sin llave de dimensión")
    if not v["fecha_key"].isin(tiempo["fecha_key"]).all():
        raise ValueError("líneas de venta sin fecha en dim_tiempo")
    v["costo_total_clp"] = v["cajas"].abs() * v["costo_caja_clp"]   # la merma no reversa el costo

    fact = v[columnas("fact_venta")].sort_values("venta_id").reset_index(drop=True)
    for df, nombre in [(fact, "fact_venta"), (tiempo, "dim_tiempo"), (producto, "dim_producto"),
                       (cliente, "dim_cliente"), (mercado, "dim_mercado")]:
        verificar(df, nombre)

    # tabla integrada: la estrella unida, más incoterm y los tipos de cambio de las sensibilidades
    usd = v["moneda"] == "USD"
    neto_usd = v["monto_neto_usd"]
    integrada = (fact
                 .merge(tiempo[["fecha_key", "fecha", "anio", "semestre", "mes"]], on="fecha_key")
                 .merge(producto.drop(columns=["costo_imputado"]), on="producto_anada_key")
                 .merge(cliente.rename(columns={"nombre": "cliente", "tipo": "tipo_cliente"}), on="cliente_key")
                 .merge(mercado, on="mercado_key"))
    extra = pd.DataFrame({
        "venta_id": v["venta_id"],
        "moneda": v["moneda"],
        "incoterm": v["incoterm"],
        "precio_lista_usd_caja": np.where(usd, v["precio_unitario_num"], v["precio_unitario_num"] / v["tipo_cambio"]),
        "descuento": v["descuento_num"],
        "costo_imputado": v["costo_imputado"],
        "fecha_cobranza": v["fecha_cobranza"].dt.date,
        "tipo_cambio_cobranza": v["tipo_cambio_cobranza"],
        "monto_neto_clp_cobranza": np.where(usd, neto_usd * v["tipo_cambio_cobranza"], v["monto_neto"]),
        "fecha_embarque": v["fecha_embarque"].dt.date,
        "tipo_cambio_embarque": v["tipo_cambio_embarque"],
        "monto_neto_clp_embarque": np.where(usd, neto_usd * v["tipo_cambio_embarque"], v["monto_neto"]),
        "monto_neto_registrado_usd": np.where(usd, v["monto_registrado"], v["monto_registrado"] / v["tipo_cambio"]),
        "monto_neto_registrado_clp": np.where(usd, v["monto_registrado"] * v["tipo_cambio"], v["monto_registrado"]),
        "en_universo": v["en_universo"],
    })
    integrada = integrada.merge(extra, on="venta_id")
    orden = ["venta_id", "fecha", "anio", "semestre", "mes",
             "producto_id", "producto", "cepa", "tipo_vino", "tier", "formato", "anada", "litros_por_caja",
             "cliente_id", "cliente", "tipo_cliente",
             "mercado_id", "pais", "zona", "canal", "hemisferio", "moneda", "incoterm",
             "cajas", "litros", "precio_lista_usd_caja", "descuento",
             "monto_bruto_usd", "monto_neto_usd", "monto_bruto_clp", "monto_neto_clp", "tipo_cambio",
             "fecha_cobranza", "tipo_cambio_cobranza", "monto_neto_clp_cobranza",
             "fecha_embarque", "tipo_cambio_embarque", "monto_neto_clp_embarque",
             "monto_neto_registrado_usd", "monto_neto_registrado_clp",
             "costo_caja_clp", "costo_imputado", "costo_total_clp",
             "es_merma", "monto_recalculado", "cajas_corregidas", "moneda_imputada", "en_universo",
             "fecha_key", "producto_anada_key", "cliente_key", "mercado_key"]
    integrada = integrada[orden].sort_values("venta_id").reset_index(drop=True)

    carpeta = raiz / "output" / "estrella"
    carpeta.mkdir(parents=True, exist_ok=True)
    estrella = {"fact_venta": fact, "dim_tiempo": tiempo, "dim_producto": producto,
                "dim_cliente": cliente, "dim_mercado": mercado}
    for nombre, df in estrella.items():
        df.to_csv(carpeta / f"{nombre}.csv", index=False, encoding="utf-8")
    integrada.to_csv(raiz / "output" / "tabla_integrada.csv", index=False, encoding="utf-8")
    return estrella, integrada
