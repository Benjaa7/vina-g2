# -*- coding: utf-8 -*-
"""Métrica: precio promedio por litro de exportación y su descomposición.

    precio (USD/L) = Σ monto neto USD / Σ litros
    universo: exportación, factura de 2025; corte por semestre de la fecha de factura

Descomposición S1 → S2 por tier (s = participación en los litros, p = USD/L del tier):
    principal (la de la sección E, base S1 con término cruzado):
        precio = Σ s1·Δp     mezcla = Σ Δs·p1     cruzado = Σ Δs·Δp
    sensibilidad: simétrica de punto medio, mezcla primero y precio primero.
El efecto precio se separa además en precio dentro de un mismo mercado y tier y en
mezcla de mercados dentro del tier (descomposición por celda tier × mercado).

Salidas: output/tablas/*.csv y output/cifras.md.
"""
import numpy as np
import pandas as pd

TIERS = ["Varietal", "Reserva", "Gran Reserva"]
MAGNUM = "6x1500"
LITROS_MAGNUM = {"principal (9 L)": 9.0, "magnum 18 L (2 × 9)": 18.0, "magnum 4,5 L (9 ÷ 2)": 4.5}


# ----------------------------------------------------------------------------
# Formato
# ----------------------------------------------------------------------------
def num(x, dec=0):
    texto = f"{x:,.{dec}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, dec=1):
    return num(x, dec) + " %"


# ----------------------------------------------------------------------------
# Cálculos base
# ----------------------------------------------------------------------------
def litros_con(df, litros_magnum):
    return df["cajas"] * np.where(df["formato"] == MAGNUM, litros_magnum, df["litros_por_caja"])


def precio_por_semestre(df, monto="monto_neto_usd", litros=None):
    lit = df["litros"] if litros is None else litros
    g = pd.DataFrame({"semestre": df["semestre"], "monto": df[monto], "litros": lit}).groupby("semestre").sum()
    s1, s2 = g.loc[1, "monto"] / g.loc[1, "litros"], g.loc[2, "monto"] / g.loc[2, "litros"]
    anual = g["monto"].sum() / g["litros"].sum()
    return s1, s2, anual


def celdas(df, clave, monto="monto_neto_usd", litros=None):
    """Participación en los litros (s) y precio por litro (p) por celda y semestre."""
    x = pd.DataFrame({"semestre": df["semestre"], "monto": df[monto],
                      "litros": df["litros"] if litros is None else litros})
    for c in clave:
        x[c] = df[c]
    g = x.groupby(["semestre"] + clave)[["monto", "litros"]].sum()
    g["s"] = g["litros"] / g.groupby("semestre")["litros"].transform("sum")
    g["p"] = g["monto"] / g["litros"]
    t = g[["s", "p"]].unstack("semestre")
    t.columns = [f"{a}{b}" for a, b in t.columns]
    return t.fillna(0.0)


def descomponer(t):
    """Los cuatro métodos sobre una tabla de celdas con s1, s2, p1, p2."""
    ds, dp = t["s2"] - t["s1"], t["p2"] - t["p1"]
    return {
        "Base S1 con término cruzado (principal, sección E)": {
            "mezcla": (ds * t["p1"]).sum(), "precio": (t["s1"] * dp).sum(), "cruzado": (ds * dp).sum()},
        "Simétrico de punto medio": {
            "mezcla": (ds * (t["p1"] + t["p2"]) / 2).sum(), "precio": (dp * (t["s1"] + t["s2"]) / 2).sum(),
            "cruzado": 0.0},
        "Secuencial, mezcla primero": {
            "mezcla": (ds * t["p1"]).sum(), "precio": (dp * t["s2"]).sum(), "cruzado": 0.0},
        "Secuencial, precio primero": {
            "mezcla": (ds * t["p2"]).sum(), "precio": (dp * t["s1"]).sum(), "cruzado": 0.0},
    }


PRINCIPAL = "Base S1 con término cruzado (principal, sección E)"


def mezcla_pct(df, monto="monto_neto_usd", litros=None):
    """% del cambio S1→S2 que explica la mezcla de tiers (método principal)."""
    s1, s2, _ = precio_por_semestre(df, monto, litros)
    d = descomponer(celdas(df, ["tier"], monto, litros))[PRINCIPAL]
    return 100 * d["mezcla"] / (s2 - s1)


def ponderado(df, valor, peso="cajas"):
    return (df[valor] * df[peso]).sum() / df[peso].sum()


# ----------------------------------------------------------------------------
# Cálculo completo
# ----------------------------------------------------------------------------
def calcular(integrada, res):
    t = integrada
    u = t[t["en_universo"] == 1].copy()
    sem = {s: u[u["semestre"] == s] for s in (1, 2)}
    r = {}  # resultados con nombre, para cifras.md y run.py

    # --- métrica principal ---
    s1, s2, anual = precio_por_semestre(u)
    r.update(precio_s1=s1, precio_s2=s2, precio_anual=anual, delta=s2 - s1, var_pct=100 * (s2 / s1 - 1))
    tabla_sem = u.groupby("semestre").agg(filas=("venta_id", "size"), cajas=("cajas", "sum"),
                                          litros=("litros", "sum"), ingreso_neto_usd=("monto_neto_usd", "sum"),
                                          ingreso_bruto_usd=("monto_bruto_usd", "sum"))
    tabla_sem["usd_por_litro"] = tabla_sem["ingreso_neto_usd"] / tabla_sem["litros"]
    r.update(litros_s1=tabla_sem.loc[1, "litros"], litros_s2=tabla_sem.loc[2, "litros"],
             ingreso_s1=tabla_sem.loc[1, "ingreso_neto_usd"], ingreso_s2=tabla_sem.loc[2, "ingreso_neto_usd"])
    r["var_litros_pct"] = 100 * (r["litros_s2"] / r["litros_s1"] - 1)
    r["var_ingreso_pct"] = 100 * (r["ingreso_s2"] / r["ingreso_s1"] - 1)
    r["universo"] = len(u)

    # --- mezcla por tier (figura 2) ---
    ct = celdas(u, ["tier"]).reindex(TIERS)
    fig2 = pd.DataFrame({"tier": TIERS,
                         "participacion_litros_s1_pct": 100 * ct["s1"].values,
                         "participacion_litros_s2_pct": 100 * ct["s2"].values,
                         "usd_por_litro_s1": ct["p1"].values, "usd_por_litro_s2": ct["p2"].values})
    fig2["cambio_pp"] = fig2["participacion_litros_s2_pct"] - fig2["participacion_litros_s1_pct"]
    for tier, k in zip(TIERS, ["var", "res", "gr"]):
        f = fig2[fig2["tier"] == tier].iloc[0]
        r[f"{k}_s1"], r[f"{k}_s2"] = f["participacion_litros_s1_pct"], f["participacion_litros_s2_pct"]

    # --- descomposición (figura 1) ---
    metodos = descomponer(ct)
    filas_m = []
    for nombre, d in metodos.items():
        filas_m.append({"metodo": nombre, "precio_s1": s1, "precio_s2": s2, "cambio": s2 - s1,
                        "efecto_mezcla": d["mezcla"], "efecto_precio": d["precio"],
                        "efecto_cruzado": d["cruzado"],
                        "mezcla_pct_del_cambio": 100 * d["mezcla"] / (s2 - s1),
                        "precio_pct_del_cambio": 100 * d["precio"] / (s2 - s1),
                        "cruzado_pct_del_cambio": 100 * d["cruzado"] / (s2 - s1),
                        "suma_verifica": d["mezcla"] + d["precio"] + d["cruzado"] - (s2 - s1)})
    tabla_metodos = pd.DataFrame(filas_m)
    p = metodos[PRINCIPAL]
    r.update(ef_mezcla=p["mezcla"], ef_precio=p["precio"], ef_cruzado=p["cruzado"],
             mezcla_pct=100 * p["mezcla"] / (s2 - s1), precio_pct=100 * p["precio"] / (s2 - s1))
    r["mezcla_pct_min"] = tabla_metodos["mezcla_pct_del_cambio"].min()
    r["mezcla_pct_max"] = tabla_metodos["mezcla_pct_del_cambio"].max()
    r["metodos"] = tabla_metodos
    # aporte de cada tier a los tres efectos del método principal
    ds, dp = ct["s2"] - ct["s1"], ct["p2"] - ct["p1"]
    por_tier = pd.DataFrame({"tier": TIERS, "efecto_mezcla": (ds * ct["p1"]).values,
                             "efecto_precio": (ct["s1"] * dp).values, "efecto_cruzado": (ds * dp).values})
    por_tier["total_tier"] = por_tier[["efecto_mezcla", "efecto_precio", "efecto_cruzado"]].sum(axis=1)
    por_tier = pd.concat([por_tier, pd.DataFrame([{"tier": "Total", **por_tier.drop(columns="tier").sum()}])],
                         ignore_index=True)
    r["por_tier"] = por_tier
    r["tier_sp"] = ct
    fig1 = pd.DataFrame({
        "concepto": ["Precio S1", "Efecto precio", "Efecto mezcla", "Efecto cruzado", "Precio S2"],
        "usd_por_litro": [s1, p["precio"], p["mezcla"], p["cruzado"], s2],
        "pct_del_cambio": [np.nan, 100 * p["precio"] / (s2 - s1), 100 * p["mezcla"] / (s2 - s1),
                           100 * p["cruzado"] / (s2 - s1), np.nan]})

    # --- efecto precio: dentro de mercado y tier vs mezcla de mercados ---
    cm = celdas(u, ["tier", "mercado_id"])
    dm = descomponer(cm)
    dt = metodos
    split = []
    for nombre in [PRINCIPAL, "Simétrico de punto medio"]:
        mezcla_mercados = dm[nombre]["mezcla"] - dt[nombre]["mezcla"]
        comp = [("Mezcla de tiers", dt[nombre]["mezcla"]),
                ("Mezcla de mercados dentro de cada tier", mezcla_mercados),
                ("Precio dentro de un mismo mercado y tier", dm[nombre]["precio"]),
                ("Término cruzado (celda tier × mercado)", dm[nombre]["cruzado"])]
        for c, val in comp:
            split.append({"metodo": nombre, "componente": c, "usd_por_litro": val,
                          "pct_del_cambio": 100 * val / (s2 - s1)})
    tabla_split = pd.DataFrame(split)
    r["split"] = tabla_split
    sp = tabla_split[tabla_split["metodo"] == PRINCIPAL].set_index("componente")["usd_por_litro"]
    r["precio_puro"] = sp["Precio dentro de un mismo mercado y tier"]
    r["mezcla_mercados"] = sp["Mezcla de mercados dentro de cada tier"]
    r["cruzado_celda"] = sp["Término cruzado (celda tier × mercado)"]

    # --- precios de lista y descuento (figura 3) ---
    fig3 = []
    for tier in TIERS:
        a = [ponderado(sem[s][sem[s]["tier"] == tier], "precio_lista_usd_caja") for s in (1, 2)]
        fig3.append({"tier": tier, "precio_lista_s1_usd_caja": a[0], "precio_lista_s2_usd_caja": a[1],
                     "variacion_pct": 100 * (a[1] / a[0] - 1)})
    fig3 = pd.DataFrame(fig3)
    for tier, k in zip(TIERS, ["var", "res", "gr"]):
        f = fig3[fig3["tier"] == tier].iloc[0]
        r[f"lista_{k}_s1"], r[f"lista_{k}_s2"], r[f"lista_{k}_var"] = (
            f["precio_lista_s1_usd_caja"], f["precio_lista_s2_usd_caja"], f["variacion_pct"])
    r["desc_s1"], r["desc_s2"] = (100 * ponderado(sem[s], "descuento") for s in (1, 2))

    # --- gran reserva por mercado (figura 4, sensibilidad e) ---
    fig4 = []
    for pais, g in u.groupby("pais"):
        fila = {"pais": pais}
        for s in (1, 2):
            gs = g[g["semestre"] == s]
            fila[f"gran_reserva_pct_litros_s{s}"] = 100 * gs.loc[gs["tier"] == "Gran Reserva", "litros"].sum() / gs["litros"].sum()
        fila["gran_reserva_pct_litros_anual"] = 100 * g.loc[g["tier"] == "Gran Reserva", "litros"].sum() / g["litros"].sum()
        fila["cambio_pp"] = fila["gran_reserva_pct_litros_s2"] - fila["gran_reserva_pct_litros_s1"]
        fila["litros_anual"] = g["litros"].sum()
        fig4.append(fila)
    fig4 = pd.DataFrame(fig4).sort_values("gran_reserva_pct_litros_s2").reset_index(drop=True)
    r["fig4"] = fig4

    # --- magnum ---
    mg = u["formato"] == MAGNUM
    gr_std = (u["tier"] == "Gran Reserva") & ~mg
    r["magnum_vol_pct"] = 100 * u.loc[mg, "litros"].sum() / u["litros"].sum()
    r["magnum_ing_pct"] = 100 * u.loc[mg, "monto_neto_usd"].sum() / u["monto_neto_usd"].sum()
    r["magnum_lista_caja"] = ponderado(u[mg], "precio_lista_usd_caja")
    r["grstd_lista_caja"] = ponderado(u[gr_std], "precio_lista_usd_caja")
    r["magnum_neto_caja"] = u.loc[mg, "monto_neto_usd"].sum() / u.loc[mg, "cajas"].sum()
    r["grstd_neto_caja"] = u.loc[gr_std, "monto_neto_usd"].sum() / u.loc[gr_std, "cajas"].sum()
    pa = res["producto_anada"]
    costo_gr = pa[pa["tier"] == "Gran Reserva"].groupby(["anada", "formato"])["costo_caja_clp"].agg(["min", "max"])
    r["magnum_costo_dif_max"] = (costo_gr["max"].groupby("anada").max() - costo_gr["min"].groupby("anada").min()).max()

    # --- sensibilidades ---
    sens = []

    def fila_sens(grupo, definicion, unidad, df, monto="monto_neto_usd", litros=None, ref=None):
        a1, a2, an = precio_por_semestre(df, monto, litros)
        fila = {"sensibilidad": grupo, "definicion": definicion, "unidad": unidad,
                "s1": a1, "s2": a2, "anual": an, "variacion_s1_s2_pct": 100 * (a2 / a1 - 1),
                "mezcla_pct_del_cambio": mezcla_pct(df, monto, litros),
                "dif_anual_vs_principal_pct": np.nan if ref is None else 100 * (an / ref - 1)}
        sens.append(fila)
        return fila

    for nombre, lm in LITROS_MAGNUM.items():
        f = fila_sens("a) litros por caja del magnum", nombre, "USD/L", u, litros=litros_con(u, lm), ref=anual)
        r[f"magnum_{lm}"] = f["anual"]
    f = fila_sens("b) líneas negativas (merma)", "excluidas", "USD/L", u[u["cajas"] > 0], ref=anual)
    r["sin_merma_s1"], r["sin_merma_s2"] = f["s1"], f["s2"]
    fila_sens("b) líneas negativas (merma)", "incluidas (principal)", "USD/L", u, ref=anual)
    fila_sens("c) moneda y fecha de conversión", "USD (principal)", "USD/L", u, ref=anual)
    fc = fila_sens("c) moneda y fecha de conversión", "CLP a fecha de factura", "CLP/L", u, "monto_neto_clp")
    fb = fila_sens("c) moneda y fecha de conversión", "CLP a fecha estimada de cobranza (+60 sur, +90 norte)",
                   "CLP/L", u, "monto_neto_clp_cobranza", ref=fc["anual"])
    fe = fila_sens("c) moneda y fecha de conversión", "CLP a fecha de embarque (solo para el supuesto S6 de la bitácora; fecha de embarque no confiable)",
                   "CLP/L", u, "monto_neto_clp_embarque", ref=fc["anual"])
    r["clp_cobranza_vs_factura"] = fb["dif_anual_vs_principal_pct"]
    r["clp_embarque_vs_factura"] = fe["dif_anual_vs_principal_pct"]
    r["clp_s1"], r["clp_s2"] = fc["s1"], fc["s2"]
    f = fila_sens("d) precio neto vs precio de lista", "precio de lista (bruto, sin descuento)", "USD/L", u,
                  "monto_bruto_usd", ref=anual)
    r["lista_s1"], r["lista_s2"] = f["s1"], f["s2"]
    fila_sens("d) precio neto vs precio de lista", "precio neto (principal)", "USD/L", u, ref=anual)
    tabla_sens = pd.DataFrame(sens)
    r["sens"] = tabla_sens

    # --- caso de negocio (sección E) ---
    r["tc_s2"] = sem[2]["monto_neto_clp"].sum() / sem[2]["monto_neto_usd"].sum()
    r["mezcla_usd_total"] = p["mezcla"] * r["litros_s2"]
    r["mezcla_clp_total"] = r["mezcla_usd_total"] * r["tc_s2"]
    sym = metodos["Simétrico de punto medio"]
    r["mezcla_usd_total_sim"] = sym["mezcla"] * r["litros_s2"]

    # --- bitácora ---
    c = res["conteos"]
    t25 = t[t["anio"] == 2025]
    r["s3_exp"] = (u["monto_neto_registrado_clp"] - u["monto_neto_clp"]).sum()
    r["s3_todos"] = (t25["monto_neto_registrado_clp"] - t25["monto_neto_clp"]).sum()
    r["cuadra_05"] = 100 * (1 - t["monto_recalculado"].mean())
    costo_signo = (u["cajas"] * u["costo_caja_clp"]).sum()
    ing = u["monto_neto_clp"].sum()
    r["margen"] = 100 * (1 - u["costo_total_clp"].sum() / ing)
    r["margen_reversa"] = 100 * (1 - costo_signo / ing)
    r["brecha_merma"] = u["costo_total_clp"].sum() - costo_signo
    r["costo_imputado_pct"] = 100 * u["costo_imputado"].mean()
    r["moneda_vacia_pct"] = 100 * c["moneda_vacia_crudo"] / c["filas_crudas"]
    br = u[u["pais"] == "Brasil"]
    r["brasil_gr"] = [100 * br.loc[(br["semestre"] == s) & (br["tier"] == "Gran Reserva"), "litros"].sum()
                      / br.loc[br["semestre"] == s, "litros"].sum() for s in (1, 2)]
    mensual = u.groupby("mes").apply(lambda g: pd.Series({
        "gran_reserva_pct_litros": 100 * g.loc[g["tier"] == "Gran Reserva", "litros"].sum() / g["litros"].sum(),
        "usd_por_litro": g["monto_neto_usd"].sum() / g["litros"].sum(),
        "litros": g["litros"].sum()}), include_groups=False).reset_index()
    r["mensual"] = mensual
    r["conteos"] = c
    r["fact_filas"] = len(t)
    r["dim_producto_filas"] = len(res["producto_anada"])
    r["recalc_u"] = int(u["monto_recalculado"].sum())
    r["botellas_u"] = int(u["cajas_corregidas"].sum())
    r["moneda_u"] = int(u["moneda_imputada"].sum())
    r["costo_imp_u"] = int(u["costo_imputado"].sum())
    r["f2026"] = int((t["anio"] != 2025).sum())
    r["nac_2025"] = int(((t["anio"] == 2025) & (t["canal"] == "Nacional")).sum())

    tablas = {
        "fig1_descomposicion": fig1,
        "fig2_mezcla_tier": fig2,
        "fig3_precio_lista_tier": fig3,
        "fig4_gran_reserva_mercado": fig4,
        "precio_semestre": tabla_sem.reset_index(),
        "descomposicion_metodos": tabla_metodos,
        "descomposicion_por_tier": por_tier,
        "descomposicion_precio_mercado": tabla_split,
        "sensibilidades": tabla_sens,
        "mensual": mensual,
    }
    return r, tablas


# ----------------------------------------------------------------------------
# cifras.md
# ----------------------------------------------------------------------------
# Valores de la figura 4 tal como estaban escritos a mano en la versión anterior
# (commit 1048bf2), anuales por país, para contrastarlos con los datos.
FIG4_TEXTO = {"Reino Unido": 25.3, "Alemania": 25.8, "Japón": 26.2, "Estados Unidos": 26.5,
              "China": 27.0, "Canadá": 27.4, "Brasil": 27.8, "Países Bajos": 29.2,
              "Corea del Sur": 28.1, "México": 28.5}

POR_CONFIRMAR = " (marcada «por confirmar»)"
NO_APARECE = "No aparece en el informe"


def escribir_cifras(r, ruta):
    filas = []

    def cifra(seccion, nombre, valor, dec, unidad, definicion, donde="", texto=None, tol=None):
        """texto: el valor que hoy dice el informe (None si la cifra no aparece en él)."""
        v = f"{num(valor, dec)}{unidad}"
        if texto is None:
            estado = "–"
        else:
            tol_ = tol if tol is not None else 0.5 * 10 ** (-dec) + 1e-9
            estado = "✔" if abs(valor - texto) <= tol_ else f"✘ (el informe dice {num(texto, dec)}{unidad})"
        filas.append((seccion, nombre, v, definicion, donde or NO_APARECE, estado))

    cs = r["conteos"]
    S = "1. Precio medio por litro de exportación (métrica principal)"
    cifra(S, "Precio medio, 1.er semestre (ene-jun)", r["precio_s1"], 3, " USD/L",
          "Ingreso neto en dólares ÷ litros; ventas de exportación facturadas entre enero y junio de 2025",
          "Sección A, línea 20; Sección E, línea 5; Figura 1", 4.574)
    cifra(S, "Precio medio, 2.º semestre (jul-dic)", r["precio_s2"], 3, " USD/L",
          "Ídem, facturas entre julio y diciembre de 2025", "Sección A, línea 20; Sección E, línea 5; Figura 1", 5.085)
    cifra(S, "Variación del precio medio", r["var_pct"], 1, " %", "Precio del 2.º semestre ÷ precio del 1.er semestre − 1",
          "Sección A, línea 20" + POR_CONFIRMAR + "; Sección E, línea 5", 11.2)
    cifra(S, "Precio medio anual 2025", r["precio_anual"], 2, " USD/L", "Ingreso neto en dólares ÷ litros, año completo",
          "Sección A, línea 37; Bitácora, supuesto S1", 4.83)
    cifra(S, "Litros exportados, 1.er semestre", r["litros_s1"], 0, " L", "Cajas (corregidas) × 9 litros por caja",
          "Sección E, línea 5", 5763411)
    cifra(S, "Litros exportados, 2.º semestre", r["litros_s2"], 0, " L", "Ídem", "Sección E, líneas 5 y 9", 5674554)
    cifra(S, "Variación de los litros", r["var_litros_pct"], 1, " %", "Litros del 2.º semestre ÷ litros del 1.er semestre − 1",
          "Sección E, línea 5", -1.5)
    cifra(S, "Ingreso neto, 1.er semestre", r["ingreso_s1"] / 1e6, 2, " M USD", "Suma del monto neto (después de descuento)",
          "Sección E, línea 5", 26.36)
    cifra(S, "Ingreso neto, 2.º semestre", r["ingreso_s2"] / 1e6, 2, " M USD", "Ídem", "Sección E, línea 5", 28.85)
    cifra(S, "Variación del ingreso neto", r["var_ingreso_pct"], 1, " %", "Ingreso del 2.º semestre ÷ ingreso del 1.er semestre − 1",
          "Sección E, línea 5", 9.5)

    S = "2. Mezcla por tier, precios de lista y descuento"
    for k, tier, t1, t2, d1 in [("var", "Varietal", 42.6, 33.3, "Sección E, línea 7; Figura 2"),
                                ("res", "Reserva", 34.7, 34.2, "Figura 2"),
                                ("gr", "Gran Reserva", 22.7, 32.5, "Sección A, línea 20; Sección E, línea 7; Figura 2")]:
        cifra(S, f"{tier}: participación en los litros, 1.er semestre", r[f"{k}_s1"], 1, " %",
              "Litros del tier ÷ litros totales exportados", d1, t1)
        cifra(S, f"{tier}: participación en los litros, 2.º semestre", r[f"{k}_s2"], 1, " %", "Ídem", d1, t2)
    cifra(S, "Gran Reserva: cambio de participación", r["gr_s2"] - r["gr_s1"], 1, " pp",
          "Participación del 2.º semestre − la del 1.er semestre (puntos porcentuales)", "Sección E, línea 7", 9.8)
    cifra(S, "Varietal: cambio de participación", r["var_s2"] - r["var_s1"], 1, " pp", "Ídem", "Sección E, línea 7", -9.3)
    for k, tier, t1, t2, tv in [("var", "Varietal", 23.65, 23.61, -0.15), ("res", "Reserva", 43.67, 43.60, None),
                                ("gr", "Gran Reserva", 77.30, 77.15, -0.19)]:
        cifra(S, f"Precio de lista {tier}, 1.er semestre", r[f"lista_{k}_s1"], 2, " USD/caja",
              "Precio unitario antes de descuento, promedio ponderado por cajas", "Figura 3", t1)
        cifra(S, f"Precio de lista {tier}, 2.º semestre", r[f"lista_{k}_s2"], 2, " USD/caja", "Ídem", "Figura 3", t2)
        cifra(S, f"Variación del precio de lista {tier}", r[f"lista_{k}_var"], 2, " %",
              "Lista del 2.º semestre ÷ lista del 1.er semestre − 1",
              "Sección A, línea 20; Sección E, línea 7 (rango «entre −0,15 % y −0,19 %»)", tv)
    cifra(S, "Descuento medio, 1.er semestre", r["desc_s1"], 2, " %", "Descuento de cada venta, promedio ponderado por cajas",
          "Sección A, línea 20; Sección E, línea 7", 3.82)
    cifra(S, "Descuento medio, 2.º semestre", r["desc_s2"], 2, " %", "Ídem", "Sección A, línea 20; Sección E, línea 7", 4.40)

    S = "3. Descomposición del alza: ¿precio o mezcla?"
    cifra(S, "Efecto precio (método principal)", r["ef_precio"], 3, " USD/L",
          "Cambio del precio por litro de cada tier, ponderado por su participación en el 1.er semestre", "Figura 1", -0.035)
    cifra(S, "Efecto mezcla (método principal)", r["ef_mezcla"], 3, " USD/L",
          "Cambio de la participación de cada tier, valorado al precio por litro del 1.er semestre",
          "Sección E, línea 9; Figura 1", 0.552)
    cifra(S, "Efecto cruzado (método principal)", r["ef_cruzado"], 3, " USD/L",
          "Cambio de participación × cambio de precio (no se atribuye a uno solo)", "Figura 1", -0.005)
    cifra(S, "Mezcla como % del alza (método principal)", r["mezcla_pct"], 0, " %",
          "Efecto mezcla ÷ alza total del precio (más de 100 % porque el efecto precio es negativo)",
          "Sección E, línea 5; Figura 1", 108)
    cifra(S, "Precio como % del alza (método principal)", r["precio_pct"], 0, " %", "Efecto precio ÷ alza total del precio",
          "Figura 1", -7)
    for _, m in r["metodos"].iterrows():
        if m["metodo"] == PRINCIPAL:
            continue
        cifra(S, f"Efecto mezcla, método {m['metodo'].lower()}", m["efecto_mezcla"], 3, " USD/L",
              f"Sensibilidad. Efecto precio {num(m['efecto_precio'], 3)} USD/L; "
              f"la mezcla explica {num(m['mezcla_pct_del_cambio'], 1)} % del alza")
    cifra(S, "Mezcla como % del alza: mínimo entre los 4 métodos", r["mezcla_pct_min"], 1, " %", "Sensibilidad")
    cifra(S, "Mezcla como % del alza: máximo entre los 4 métodos", r["mezcla_pct_max"], 1, " %", "Sensibilidad")
    cifra(S, "Precio dentro de un mismo mercado y tier", r["precio_puro"], 3, " USD/L",
          "Parte del efecto precio que es cambio de precio real, comparando el mismo tier en el mismo mercado")
    cifra(S, "Mezcla de mercados dentro de cada tier", r["mezcla_mercados"], 3, " USD/L",
          "Parte del efecto precio que viene de vender más en mercados de menor precio")
    cifra(S, "Término cruzado por mercado y tier", r["cruzado_celda"], 3, " USD/L",
          "Resto de la separación anterior; las tres partes suman el efecto precio más el cruzado")

    S = "4. Caso de negocio"
    cifra(S, "Valor de la mezcla en el 2.º semestre", r["mezcla_usd_total"] / 1e6, 2, " M USD",
          "Efecto mezcla (método principal) × litros del 2.º semestre", "Sección E, línea 9", 3.13)
    cifra(S, "Ídem con el método simétrico", r["mezcla_usd_total_sim"] / 1e6, 3, " M USD", "Sensibilidad")
    cifra(S, "Tipo de cambio efectivo del 2.º semestre", r["tc_s2"], 2, " CLP/USD",
          "Ingreso neto en pesos ÷ ingreso neto en dólares, con el dólar del día de cada factura",
          "Sección E, línea 9", 946.34)
    cifra(S, "Valor de la mezcla en pesos", r["mezcla_clp_total"] / 1e6, 0, " M CLP",
          "Valor en dólares × tipo de cambio efectivo del 2.º semestre",
          "Sección E, línea 9 (la línea 11 lo redondea a 3.000)", 2960, tol=5)

    S = "5. Formato magnum y litros por caja"
    cifra(S, "Magnum: participación en el volumen", r["magnum_vol_pct"], 2, " %",
          "Litros de formato 6x1500 ÷ litros totales exportados", "Verificación pedida por el equipo", 8.07)
    cifra(S, "Magnum: participación en el ingreso", r["magnum_ing_pct"], 2, " %",
          "Ingreso neto de formato 6x1500 ÷ ingreso neto total", "Verificación pedida por el equipo", 13.76)
    cifra(S, "Magnum: precio de lista por caja", r["magnum_lista_caja"], 2, " USD/caja",
          "Precio antes de descuento, ponderado por cajas", "Sección A, línea 35", 77.26)
    cifra(S, "Gran Reserva estándar (12x750): precio de lista por caja", r["grstd_lista_caja"], 2, " USD/caja",
          "Ídem", "Sección A, línea 35", 77.20)
    cifra(S, "Magnum: ingreso neto por caja", r["magnum_neto_caja"], 2, " USD/caja", "Ingreso neto ÷ cajas",
          "Aclaración para la sección A, línea 35")
    cifra(S, "Gran Reserva estándar: ingreso neto por caja", r["grstd_neto_caja"], 2, " USD/caja", "Ídem",
          "Aclaración para la sección A, línea 35")
    cifra(S, "Precio anual si el magnum rindiera 18 litros por caja", r["magnum_18.0"], 2, " USD/L",
          "Sensibilidad: solo cambian los litros del formato 6x1500",
          "Sección A, línea 37" + POR_CONFIRMAR + "; Bitácora, supuesto S1", 4.47)
    cifra(S, "Precio anual si el magnum rindiera 4,5 litros por caja", r["magnum_4.5"], 2, " USD/L", "Ídem",
          "Sección A, línea 37" + POR_CONFIRMAR + "; Bitácora, supuesto S1", 5.03)
    cifra(S, "Diferencia con 18 litros", 100 * (r["magnum_18.0"] / r["precio_anual"] - 1), 1, " %",
          "Contra el precio anual con 9 litros", "Bitácora, supuesto S1", -7.5)
    cifra(S, "Diferencia con 4,5 litros", 100 * (r["magnum_4.5"] / r["precio_anual"] - 1), 1, " %",
          "Contra el precio anual con 9 litros", "Bitácora, supuesto S1", 4.2)

    S = "6. Universo y cobertura de datos"
    cifra(S, "Ventas registradas", cs["filas_crudas"], 0, "", "Filas de la tabla ventas del ERP", "Sección F, línea 3", 13983)
    cifra(S, "Filas del modelo (tabla fact_venta)", r["fact_filas"], 0, "",
          "Ventas sin duplicados; incluye las de 2026 y las nacionales", "Sección C, línea 21" + POR_CONFIRMAR, 13845)
    cifra(S, "Universo de la métrica", r["universo"], 0, "", "Ventas de exportación facturadas en 2025",
          "Sección C, línea 21" + POR_CONFIRMAR + "; Sección F, línea 5", 10672)
    cifra(S, "Filas de la dimensión producto", r["dim_producto_filas"], 0, "", "24 productos × 4 añadas",
          "Sección C, línea 27" + POR_CONFIRMAR, 96)
    cifra(S, "Duplicados eliminados", cs["duplicados"], 0, "", "Misma venta registrada dos veces", "Sección F, línea 3", 138)
    cifra(S, "Facturas de 2026 excluidas", r["f2026"], 0, "", "Fuera del período analizado", "Sección F, línea 3", 83)
    cifra(S, "Excluidas por problemas de datos", cs["duplicados"] + r["f2026"], 0, "", "Duplicados + facturas de 2026",
          "Sección F, línea 3", 221)
    cifra(S, "Excluidas por problemas de datos, %", 100 * (cs["duplicados"] + r["f2026"]) / cs["filas_crudas"], 1, " %",
          "Sobre las ventas registradas", "Sección F, línea 3", 1.6)
    cifra(S, "Ventas nacionales de 2025 (fuera del alcance)", r["nac_2025"], 0, "", "La pregunta es sobre exportación",
          "Sección F, línea 3", 3090)
    cifra(S, "Montos netos recalculados (universo)", r["recalc_u"], 0, "",
          "El monto registrado difería más de 0,5 % de cajas × precio × (1 − descuento)", "Sección F, línea 5", 555)
    cifra(S, "Ventas cargadas en botellas (universo)", r["botellas_u"], 0, "", "Cajas divididas por 12 o 10 según el embarque",
          "Sección F, línea 5", 151)
    cifra(S, "Monedas vacías asignadas (todas las ventas registradas)", cs["moneda_vacia_crudo"], 0, "",
          "Se asigna por mercado", "Sección F, línea 5", 698)
    cifra(S, "Monedas vacías asignadas (universo)", r["moneda_u"], 0, "",
          "Ídem, solo dentro del universo (la sección F mezcla ambas bases)", "Sección F, línea 5")
    cifra(S, "Costos imputados (universo)", r["costo_imp_u"], 0, "", "El maestro no traía costo para ese producto y añada",
          "Sección F, línea 5", 1852)

    S = "7. Bitácora de supuestos (anexo)"
    cifra(S, "Supuesto S3: diferencia si se usara el monto registrado, exportación", r["s3_exp"] / 1e6, 1, " M CLP",
          "Monto neto registrado − monto neto corregido, en pesos, dentro del universo", "Bitácora, supuesto S3", 2782, tol=0.05)
    cifra(S, "Supuesto S3: ídem, todos los canales de 2025", r["s3_todos"] / 1e6, 1, " M CLP",
          "Ídem, facturas de 2025 de exportación y nacionales", "Bitácora, supuesto S3", 2782, tol=0.05)
    cifra(S, "Supuesto S3: ventas cuyo monto cuadra a ±0,5 %", r["cuadra_05"], 1, " %", "Sobre las 13.845 filas del modelo",
          "Bitácora, supuesto S3 (dice «95 %»)", 95, tol=0.5)
    cifra(S, "Supuesto S4: ventas sin moneda", r["moneda_vacia_pct"], 1, " %", "Sobre las ventas registradas",
          "Bitácora, supuesto S4", 5.0)
    cifra(S, "Supuesto S5: ventas con costo imputado", r["costo_imputado_pct"], 1, " %", "Dentro del universo",
          "Bitácora, supuesto S5", 17.4)
    cifra(S, "Supuesto S6: ingreso en pesos a fecha de embarque vs. a fecha de factura", r["clp_embarque_vs_factura"], 2,
          " %", "Diferencia del ingreso total en pesos; la fecha de embarque no es confiable", "Bitácora, supuesto S6", -0.69)
    cifra(S, "Supuesto S6: ingreso en pesos a fecha de cobranza vs. a fecha de factura", r["clp_cobranza_vs_factura"], 2,
          " %", "Cobranza = factura + 60 días (hemisferio sur) o + 90 (norte); dólar observado 2025 y 2026",
          "Bitácora, supuesto S6", -1.44)
    cifra(S, "Supuesto S7: margen bruto (sin reversar el costo de la merma)", r["margen"], 2, " %",
          "1 − costo total ÷ ingreso neto en pesos, dentro del universo", "Bitácora, supuesto S7", 47.25)
    cifra(S, "Supuesto S7: margen si se reversara el costo de la merma", r["margen_reversa"], 2, " %",
          "Ídem, restando el costo de las líneas negativas", "Bitácora, supuesto S7", 48.05)
    cifra(S, "Supuesto S7: diferencia de costo", r["brecha_merma"] / 1e6, 0, " M CLP",
          "Costo con cajas en valor absoluto − costo con signo", "Bitácora, supuesto S7", 419)
    cifra(S, "Supuesto S8: Brasil, Gran Reserva en los litros, 1.er semestre", r["brasil_gr"][0], 1, " %",
          "Mercado de control del hemisferio sur", "Bitácora, supuesto S8")
    cifra(S, "Supuesto S8: Brasil, Gran Reserva en los litros, 2.º semestre", r["brasil_gr"][1], 1, " %", "Ídem",
          "Bitácora, supuesto S8")
    m = r["mensual"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
             "octubre", "noviembre", "diciembre"]
    cifra(S, "Supuesto S8: Gran Reserva en los litros, mes más bajo", m["gran_reserva_pct_litros"].min(), 1, " %",
          f"{meses[int(m.loc[m['gran_reserva_pct_litros'].idxmin(), 'mes']) - 1].capitalize()} "
          "(serie completa en tablas/mensual.csv)", "Bitácora, supuesto S8")
    cifra(S, "Supuesto S8: Gran Reserva en los litros, mes más alto", m["gran_reserva_pct_litros"].max(), 1, " %",
          meses[int(m.loc[m['gran_reserva_pct_litros'].idxmax(), 'mes']) - 1].capitalize(), "Bitácora, supuesto S8")
    cifra(S, "Supuesto S12: fechas dd/mm/aaaa ambiguas (día ≤ 12)", cs["fechas_ambiguas"], 0, "",
          "Ventas registradas cuya fecha se podría leer como día/mes o mes/día", "Bitácora, supuesto S12")
    cifra(S, "Supuesto S12: ambiguas que coinciden con la columna mes leídas como día/mes", cs["ambiguas_calzan_ddmm"], 0,
          "", "", "Bitácora, supuesto S12", 1281)
    cifra(S, "Supuesto S12: ambiguas que coinciden con la columna mes leídas como mes/día", cs["ambiguas_calzan_mmdd"], 0,
          "", "", "Bitácora, supuesto S12 (dice «7 casos»)", 7)
    cifra(S, "Supuesto S12: ventas cuya columna mes no coincide con la fecha", cs["mes_discrepante"], 0, "",
          "En todos los formatos, también en fechas sin ambigüedad", "Bitácora, supuesto S12")

    S = "8. Figura 4: Gran Reserva por mercado"
    for _, f in r["fig4"].iterrows():
        cifra(S, f"{f['pais']}: Gran Reserva en los litros, año 2025", f["gran_reserva_pct_litros_anual"], 1, " %",
              f"1.er semestre {num(f['gran_reserva_pct_litros_s1'], 1)} % → 2.º semestre "
              f"{num(f['gran_reserva_pct_litros_s2'], 1)} %", "Figura 4 (versión anterior)", FIG4_TEXTO.get(f["pais"]))

    S = "9. Sección D: métrica y sensibilidad"
    D = "Sección D"
    sens = r["sens"].set_index("definicion")
    sp, pt = r["tier_sp"], r["por_tier"].set_index("tier")
    cifra(S, "Líneas de exportación de 2025 en la suma", r["universo"], 0, "", "Universo de la métrica", D, 10672)
    cifra(S, "P, 1.er semestre", r["precio_s1"], 3, " USD/L", "Σ monto neto USD ÷ Σ litros", D, 4.574)
    cifra(S, "P, 2.º semestre", r["precio_s2"], 3, " USD/L", "Ídem", D, 5.085)
    cifra(S, "Alza de P", r["delta"], 3, " USD/L", "P del 2.º semestre − P del 1.er semestre", D, 0.511)
    cifra(S, "Alza de P, %", r["var_pct"], 1, " %", "P del 2.º semestre ÷ P del 1.er semestre − 1", D, 11.2)
    texto_entrada = {"Varietal": (42.6, 33.3, 2.528, 2.501), "Reserva": (34.7, 34.2, 4.659, 4.643),
                     "Gran Reserva": (22.7, 32.5, 8.277, 8.197)}
    for tier, (w1, w2, q1, q2) in texto_entrada.items():
        cifra(S, f"{tier}: proporción de litros (w), 1.er semestre", 100 * sp.loc[tier, "s1"], 1, " %",
              "Tabla «Datos de entrada»", D, w1)
        cifra(S, f"{tier}: proporción de litros (w), 2.º semestre", 100 * sp.loc[tier, "s2"], 1, " %", "Ídem", D, w2)
        cifra(S, f"{tier}: precio por litro (p), 1.er semestre", sp.loc[tier, "p1"], 3, " USD/L",
              "Σ monto neto USD ÷ Σ litros del tier", D, q1)
        cifra(S, f"{tier}: precio por litro (p), 2.º semestre", sp.loc[tier, "p2"], 3, " USD/L", "Ídem", D, q2)
    cifra(S, "Tiers cuyo precio por litro bajó entre semestres", int((sp["p2"] < sp["p1"]).sum()), 0, "",
          "«Los tres precios por tier bajaron»", D, 3)
    texto_aportes = {"Varietal": (-0.235, -0.012, 0.003), "Reserva": (-0.023, -0.006, 0.000),
                     "Gran Reserva": (0.809, -0.018, -0.008), "Total": (0.551, -0.035, -0.005)}
    for tier, (tm, tp, tc_) in texto_aportes.items():
        cifra(S, f"{tier}: aporte al efecto mezcla", pt.loc[tier, "efecto_mezcla"], 3, " USD/L",
              "(w del 2.º sem. − w del 1.er sem.) × p del 1.er sem.; tabla «Cálculo»", D, tm)
        cifra(S, f"{tier}: aporte al efecto precio", pt.loc[tier, "efecto_precio"], 3, " USD/L",
              "w del 1.er sem. × (p del 2.º sem. − p del 1.er sem.)", D, tp)
        cifra(S, f"{tier}: aporte al término cruzado", pt.loc[tier, "efecto_cruzado"], 3, " USD/L",
              "(cambio de w) × (cambio de p)", D, tc_)
    cifra(S, "Gran Reserva: puntos de proporción ganados", r["gr_s2"] - r["gr_s1"], 1, " pp", "«9,8 puntos más»", D, 9.8)
    cifra(S, "Gran Reserva: lo que suma al precio medio", pt.loc["Gran Reserva", "efecto_mezcla"], 2, " USD/L",
          "«suma 0,81 USD/L»", D, 0.81)
    cifra(S, "Varietal: puntos de proporción perdidos", r["var_s1"] - r["var_s2"], 1, " pp", "«9,3 puntos menos»", D, 9.3)
    cifra(S, "Varietal: lo que resta al precio medio", -pt.loc["Varietal", "efecto_mezcla"], 2, " USD/L",
          "«resta 0,23»", D, 0.23)
    suma_red = sum(round(pt.loc[t, "efecto_precio"], 3) for t in TIERS)
    cifra(S, "Columna de precio sumando los valores redondeados", suma_red, 3, " USD/L",
          "Suma de los tres aportes ya redondeados a 3 decimales («suma −0,036 en vez de −0,035»)", D, -0.036)
    cifra(S, "Mezcla, % del alza", r["mezcla_pct"], 0, " %", "Tabla «Resultado»", D, 108)
    cifra(S, "Precio, % del alza", r["precio_pct"], 0, " %", "Ídem", D, -7)
    cifra(S, "Cruzado, % del alza", 100 * r["ef_cruzado"] / r["delta"], 0, " %", "Ídem («apenas el 1 %»)", D, -1)
    cifra(S, "Variación del precio de lista Varietal", r["lista_var_var"], 2, " %",
          "Extremo del rango «entre 0,15 % y 0,19 %»", D, -0.15)
    cifra(S, "Variación del precio de lista Gran Reserva", r["lista_gr_var"], 2, " %", "Ídem", D, -0.19)
    cifra(S, "Descuento medio, 1.er semestre", r["desc_s1"], 2, " %", "Ponderado por cajas", D, 3.82)
    cifra(S, "Descuento medio, 2.º semestre", r["desc_s2"], 2, " %", "Ídem", D, 4.40)
    cifra(S, "Magnum vs Gran Reserva estándar: diferencia de precio de lista por caja",
          r["magnum_lista_caja"] - r["grstd_lista_caja"], 2, " USD/caja",
          f"«el precio por caja coincide»: {num(r['magnum_lista_caja'], 2)} vs {num(r['grstd_lista_caja'], 2)}", D)
    cifra(S, "Magnum vs Gran Reserva estándar: diferencia máxima de costo por caja (misma añada)",
          r["magnum_costo_dif_max"], 0, " CLP/caja", "«el costo por caja coincide»", D, 0)
    texto_def = {"principal (9 L)": (4.574, 5.085, 11.2, 107.9), "magnum 18 L (2 × 9)": (4.287, 4.646, 8.4, 108.2),
                 "magnum 4,5 L (9 ÷ 2)": (4.733, 5.337, 12.8, 108.2)}
    for defi, (a1, a2, av, am) in texto_def.items():
        f = sens.loc[defi]
        f = f.iloc[0] if isinstance(f, pd.DataFrame) else f
        nombre = {"principal (9 L)": "9,0 L (adoptada)", "magnum 18 L (2 × 9)": "18,0 L",
                  "magnum 4,5 L (9 ÷ 2)": "4,5 L"}[defi]
        cifra(S, f"Magnum {nombre}: P del 1.er semestre", f["s1"], 3, " USD/L", "Análisis completo con esa definición", D, a1)
        cifra(S, f"Magnum {nombre}: P del 2.º semestre", f["s2"], 3, " USD/L", "Ídem", D, a2)
        cifra(S, f"Magnum {nombre}: alza del precio", f["variacion_s1_s2_pct"], 1, " %", "P₂ ÷ P₁ − 1", D, av)
        cifra(S, f"Magnum {nombre}: mezcla, % del alza", f["mezcla_pct_del_cambio"], 1, " %",
              "Descomposición principal con esa definición", D, am)
    cifra(S, "Precio anual con magnum de 9 L", r["precio_anual"], 2, " USD/L", "Definición adoptada", D, 4.83)
    cifra(S, "Precio anual con magnum de 18 L", r["magnum_18.0"], 2, " USD/L", "Definición alternativa", D, 4.47)
    cifra(S, "Precio anual con magnum de 4,5 L", r["magnum_4.5"], 2, " USD/L", "Definición alternativa", D, 5.03)
    cifra(S, "Cambio del precio anual con 18 L", 100 * (r["magnum_18.0"] / r["precio_anual"] - 1), 1, " %",
          "Contra 9 L («un 7,5 % menos»)", D, -7.5)
    cifra(S, "Cambio del precio anual con 4,5 L", 100 * (r["magnum_4.5"] / r["precio_anual"] - 1), 1, " %",
          "Contra 9 L", D, 4.2)
    mezclas_magnum = [sens.loc[d_, "mezcla_pct_del_cambio"] for d_ in texto_def]
    cifra(S, "Mezcla, % del alza: mínimo entre las tres definiciones", min(mezclas_magnum), 0, " %",
          "«108 % con las tres definiciones»", D, 108)
    cifra(S, "Mezcla, % del alza: máximo entre las tres definiciones", max(mezclas_magnum), 0, " %", "Ídem", D, 108)
    cifra(S, "Método de descomposición: mezcla, % del alza (mínimo)", r["mezcla_pct_min"], 1, " %",
          "Cuatro métodos (base 1.er semestre, simétrico y dos secuenciales)", D, 106.9)
    cifra(S, "Método de descomposición: mezcla, % del alza (máximo)", r["mezcla_pct_max"], 1, " %", "Ídem", D, 107.9)
    cifra(S, "Sin las cajas descartadas por merma (cadena de frío, fallas de suministro): mezcla, % del alza",
          sens.loc["excluidas", "mezcla_pct_del_cambio"], 1, " %", "Se ignoran las líneas de merma", D, 108.0)
    cifra(S, "Con precio de lista: mezcla, % del alza", sens.loc["precio de lista (bruto, sin descuento)",
          "mezcla_pct_del_cambio"], 1, " %", "Antes de descuento", D, 101.7)
    alternativas = [sens.loc["excluidas", "mezcla_pct_del_cambio"],
                    sens.loc["precio de lista (bruto, sin descuento)", "mezcla_pct_del_cambio"],
                    r["mezcla_pct_min"]] + mezclas_magnum
    cifra(S, "Mezcla, % del alza: mínimo entre todas las alternativas en USD", min(alternativas), 1, " %",
          "«en ninguna alternativa la mezcla baja del 100 %»", D)
    cifra(S, "Alza del precio en pesos, dólar de la fecha de factura",
          sens.loc["CLP a fecha de factura", "variacion_s1_s2_pct"], 1, " %", "CLP/L", D, 10.1)
    cifra(S, "Alza del precio en pesos, dólar de la fecha estimada de cobranza",
          sens.loc["CLP a fecha estimada de cobranza (+60 sur, +90 norte)", "variacion_s1_s2_pct"], 1, " %",
          "Factura + 60 días (sur) o + 90 (norte)", D, 6.3)
    cifra(S, "Alza del precio en dólares", r["var_pct"], 1, " %", "Para comparar con las dos anteriores", D, 11.2)

    # resumen
    contrastadas = [x for x in filas if x[5] != "–"]
    distintas = [x for x in contrastadas if x[5].startswith("✘")]
    fig4_mal = [x for x in distintas if x[0].startswith("8.")]
    otras_mal = [x[1] for x in distintas if not x[0].startswith("8.")]
    sm = r["metodos"].set_index("metodo")
    lineas = [
        "# Cifras del informe",
        "",
        "Este archivo lista cada cifra del informe del Grupo 2 (caso Viña Vallehondo, pregunta 2: el precio "
        "promedio por litro de exportación subió en 2025, ¿por alza de precios o por mayor proporción de "
        "Gran Reserva?), explica cómo se calcula y dice si el valor escrito en el informe coincide con los "
        "datos. Las cifras salen de las cuatro fuentes del caso (ERP de ventas, maestro de costos, embarques "
        "y dólar observado) después de la limpieza descrita en `cobertura.md`. Lo genera `src/metrica.py` "
        "al correr `python run.py`; no se edita a mano.",
        "",
        "## Resumen",
        "",
        f"- El precio medio de exportación subió de {num(r['precio_s1'], 3)} USD por litro en el 1.er semestre "
        f"de 2025 (S1, enero a junio) a {num(r['precio_s2'], 3)} en el 2.º semestre (S2, julio a diciembre), "
        f"un alza de {num(r['var_pct'], 1)} %, mientras los litros exportados bajaron "
        f"{num(-r['var_litros_pct'], 1)} %.",
        f"- El alza se explica por la mezcla, no por los precios: Gran Reserva pasó de {num(r['gr_s1'], 1)} % "
        f"a {num(r['gr_s2'], 1)} % de los litros. El efecto mezcla aporta {num(r['ef_mezcla'], 3)} USD/L "
        f"({num(r['mezcla_pct'], 0)} % del alza) y el efecto precio {num(r['ef_precio'], 3)} USD/L. Con "
        f"cualquiera de los cuatro métodos de descomposición, la mezcla explica entre "
        f"{num(r['mezcla_pct_min'], 1)} % y {num(r['mezcla_pct_max'], 1)} % del alza.",
        f"- Los precios de lista bajaron levemente (entre {num(r['lista_var_var'], 2)} % y "
        f"{num(r['lista_gr_var'], 2)} % según el tier) y el descuento medio subió de {num(r['desc_s1'], 2)} % a "
        f"{num(r['desc_s2'], 2)} %. Comparando el mismo tier en el mismo mercado, el precio por litro cambió "
        f"apenas {num(r['precio_puro'], 3)} USD/L.",
        f"- La conclusión no depende de cuántos litros rinda el magnum: con 18 o 4,5 litros por caja el "
        f"precio anual sería {num(r['magnum_18.0'], 2)} o {num(r['magnum_4.5'], 2)} USD/L en vez de "
        f"{num(r['precio_anual'], 2)}, y la mezcla sigue explicando más del 100 % del alza "
        "(tabla `tablas/sensibilidades.csv`).",
        f"- De las {len(contrastadas)} cifras del informe que se pudieron contrastar con los datos, "
        f"{len(contrastadas) - len(distintas)} coinciden. No coinciden: "
        + "; ".join(otras_mal)
        + (f"; y {len(fig4_mal)} de los 10 valores de la figura 4" if fig4_mal else "")
        + ". El detalle de qué corregir está en `discrepancias.md`.",
        "",
        "## Cómo leer las tablas",
        "",
        "- **Cifra**: qué se mide.",
        "- **Valor**: el resultado que entrega la cadena con los datos actuales.",
        "- **Cómo se calcula**: la definición en una línea.",
        "- **Dónde aparece en el informe**: archivo y línea del `.tex` en `informe/` (sección A = "
        "`seccion_A.tex`, etc.; «Bitácora» = `anexo_bitacora.tex`). «Marcada por confirmar» indica que el "
        "informe la tiene pendiente de verificación. La sección D todavía no está en el repositorio, así "
        "que se cita sin número de línea.",
        "- **¿Coincide?**: ✔ el valor del informe coincide con el de los datos al redondeo con que está "
        "escrito; ✘ no coincide (entre paréntesis, lo que dice el informe); – la cifra no aparece en el "
        "informe (es de apoyo, una sensibilidad o un hallazgo nuevo).",
        "",
        "Términos: **1.er semestre** = facturas de enero a junio de 2025; **2.º semestre** = julio a "
        "diciembre. **Universo** = ventas de exportación facturadas en 2025 (10.672). **Tier** = Varietal, "
        "Reserva o Gran Reserva. **Magnum** = formato 6x1500 (6 botellas de 1,5 L). **pp** = puntos "
        "porcentuales. **Supuesto Sn** = fila n de la bitácora de supuestos del anexo (no confundir con "
        "los semestres). **Ingreso neto** = después de descuento. **Sensibilidad** = la misma cifra "
        "calculada con otra definición, para ver si la conclusión cambia.",
        "",
    ]
    actual = None
    for seccion, nombre, v, definicion, donde, estado in filas:
        if seccion != actual:
            lineas += ["", f"## {seccion}", "",
                       "| Cifra | Valor | Cómo se calcula | Dónde aparece en el informe | ¿Coincide? |",
                       "|---|---:|---|---|---|"]
            actual = seccion
        lineas.append(f"| {nombre} | {v} | {definicion} | {donde} | {estado} |")
    lineas += ["", "## Notas", "",
               "- **Supuesto S3:** los CLP 2.782 millones de la bitácora no se reproducen con ninguna de las "
               "dos definiciones de la tabla 7. Quien escribió el supuesto debe aclarar qué sumó.",
               "- **Efecto mezcla (sección E, línea 9; figura 1):** el valor es "
               f"{num(r['ef_mezcla'], 4)} USD/L, que redondea a {num(r['ef_mezcla'], 3)}. Las cifras que se "
               "derivan de él (108 %, USD 3,13 millones, CLP ≈ 2.960 millones) sí coinciden.",
               "- **Supuesto S6:** la fecha de embarque no es confiable (en 30 % de las ventas es anterior a la "
               "factura), así que la cifra se informa solo porque la bitácora la cita. Además, la versión "
               "anterior usaba el último dólar de 2025 para las fechas posteriores al 30 de diciembre de 2025; "
               "ahora se usa el dólar observado de 2026, y por eso cambia.",
               "- **Figura 4:** ahora se genera desde `tablas/fig4_gran_reserva_mercado.csv` y muestra el "
               "1.er y el 2.º semestre por mercado. Los valores escritos a mano en la versión anterior no "
               "salían de los datos.",
               f"- **Métodos de descomposición:** el principal es el de la sección E (base 1.er semestre, con "
               f"término cruzado). Los otros tres (simétrico, mezcla primero y precio primero) dan la mezcla "
               f"entre {num(sm['efecto_mezcla'].min(), 3)} y {num(sm['efecto_mezcla'].max(), 3)} USD/L; "
               "detalle en `tablas/descomposicion_metodos.csv`."]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def guardar_tablas(tablas, carpeta):
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, df in tablas.items():
        df.to_csv(carpeta / f"{nombre}.csv", index=False, encoding="utf-8", float_format="%.6f")
