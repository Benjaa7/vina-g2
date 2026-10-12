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
    fe = fila_sens("c) moneda y fecha de conversión", "CLP a fecha de embarque (solo para S6; regla 8)",
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
        "descomposicion_precio_mercado": tabla_split,
        "sensibilidades": tabla_sens,
        "mensual": mensual,
    }
    return r, tablas


# ----------------------------------------------------------------------------
# cifras.md
# ----------------------------------------------------------------------------
# Valores de la figura 4 tal como están hoy en src/graficos.py (anual, por país)
FIG4_TEXTO = {"Reino Unido": 25.3, "Alemania": 25.8, "Japón": 26.2, "Estados Unidos": 26.5,
              "China": 27.0, "Canadá": 27.4, "Brasil": 27.8, "Países Bajos": 29.2,
              "Corea del Sur": 28.1, "México": 28.5}


def escribir_cifras(r, ruta):
    filas = []

    def cifra(seccion, nombre, valor, dec, unidad, definicion, donde="", texto=None, tol=None):
        """texto: el valor que hoy dice el informe (None si la cifra no aparece)."""
        v = f"{num(valor, dec)}{unidad}"
        if texto is None:
            estado = "–"
        else:
            tol_ = tol if tol is not None else 0.5 * 10 ** (-dec) + 1e-9
            estado = "✔" if abs(valor - texto) <= tol_ else f"✘ (texto: {num(texto, dec)}{unidad})"
        filas.append((seccion, nombre, v, definicion, donde, estado))

    cs = r["conteos"]
    # 1. métrica principal
    S = "Métrica"
    cifra(S, "Precio medio S1", r["precio_s1"], 3, " USD/L", "Σ neto USD / Σ litros; exportación, factura ene–jun 2025",
          "A:20, E:5, fig. 1", 4.574)
    cifra(S, "Precio medio S2", r["precio_s2"], 3, " USD/L", "ídem, factura jul–dic 2025", "A:20, E:5, fig. 1", 5.085)
    cifra(S, "Variación S1→S2", r["var_pct"], 1, " %", "precio S2 / precio S1 − 1", "A:20 [por confirmar], E:5", 11.2)
    cifra(S, "Precio medio anual", r["precio_anual"], 2, " USD/L", "Σ neto USD / Σ litros, año 2025", "A:37, S1", 4.83)
    cifra(S, "Litros S1", r["litros_s1"], 0, " L", "Σ cajas corregidas × 9,0", "E:5", 5763411)
    cifra(S, "Litros S2", r["litros_s2"], 0, " L", "ídem", "E:5, E:9", 5674554)
    cifra(S, "Variación de litros", r["var_litros_pct"], 1, " %", "litros S2 / S1 − 1", "E:5", -1.5)
    cifra(S, "Ingreso neto S1", r["ingreso_s1"] / 1e6, 2, " M USD", "Σ monto neto USD", "E:5", 26.36)
    cifra(S, "Ingreso neto S2", r["ingreso_s2"] / 1e6, 2, " M USD", "ídem", "E:5", 28.85)
    cifra(S, "Variación del ingreso", r["var_ingreso_pct"], 1, " %", "ingreso S2 / S1 − 1", "E:5", 9.5)

    S = "Mezcla y precios"
    for k, tier, t1, t2, d1 in [("var", "Varietal", 42.6, 33.3, "E:7, fig. 2"),
                                ("res", "Reserva", 34.7, 34.2, "fig. 2"),
                                ("gr", "Gran Reserva", 22.7, 32.5, "A:20, E:7, fig. 2")]:
        cifra(S, f"{tier}: % de los litros S1", r[f"{k}_s1"], 1, " %", "litros del tier / litros totales", d1, t1)
        cifra(S, f"{tier}: % de los litros S2", r[f"{k}_s2"], 1, " %", "ídem", d1, t2)
    cifra(S, "Gran Reserva: cambio", r["gr_s2"] - r["gr_s1"], 1, " pp", "S2 − S1", "E:7", 9.8)
    cifra(S, "Varietal: cambio", r["var_s2"] - r["var_s1"], 1, " pp", "S2 − S1", "E:7", -9.3)
    for k, tier, t1, t2, tv in [("var", "Varietal", 23.65, 23.61, -0.15), ("res", "Reserva", 43.67, 43.60, None),
                                ("gr", "Gran Reserva", 77.30, 77.15, -0.19)]:
        cifra(S, f"Precio de lista {tier} S1", r[f"lista_{k}_s1"], 2, " USD/caja",
              "precio unitario ponderado por cajas", "fig. 3", t1)
        cifra(S, f"Precio de lista {tier} S2", r[f"lista_{k}_s2"], 2, " USD/caja", "ídem", "fig. 3", t2)
        cifra(S, f"Variación de lista {tier}", r[f"lista_{k}_var"], 2, " %", "lista S2 / S1 − 1",
              "A:20, E:7 (rango «entre −0,15 % y −0,19 %»)", tv)
    cifra(S, "Descuento medio S1", r["desc_s1"], 2, " %", "descuento ponderado por cajas", "A:20, E:7", 3.82)
    cifra(S, "Descuento medio S2", r["desc_s2"], 2, " %", "ídem", "A:20, E:7", 4.40)

    S = "Descomposición"
    cifra(S, "Efecto precio (principal)", r["ef_precio"], 3, " USD/L", "Σ s1·Δp por tier", "fig. 1", -0.035)
    cifra(S, "Efecto mezcla (principal)", r["ef_mezcla"], 3, " USD/L", "Σ Δs·p1 por tier", "E:9, fig. 1", 0.552)
    cifra(S, "Efecto cruzado (principal)", r["ef_cruzado"], 3, " USD/L", "Σ Δs·Δp por tier", "fig. 1", -0.005)
    cifra(S, "Mezcla, % del cambio (principal)", r["mezcla_pct"], 0, " %", "efecto mezcla / (S2 − S1)", "E:5, fig. 1", 108)
    cifra(S, "Precio, % del cambio (principal)", r["precio_pct"], 0, " %", "efecto precio / (S2 − S1)", "fig. 1", -7)
    for _, m in r["metodos"].iterrows():
        if m["metodo"] == PRINCIPAL:
            continue
        cifra(S, f"{m['metodo']}: mezcla", m["efecto_mezcla"], 3, " USD/L",
              f"precio {num(m['efecto_precio'], 3)} USD/L; mezcla = {num(m['mezcla_pct_del_cambio'], 1)} % del cambio",
              "sensibilidad")
    cifra(S, "Mezcla, % del cambio: mínimo entre métodos", r["mezcla_pct_min"], 1, " %", "4 métodos", "sensibilidad")
    cifra(S, "Mezcla, % del cambio: máximo entre métodos", r["mezcla_pct_max"], 1, " %", "4 métodos", "sensibilidad")
    cifra(S, "Precio dentro de un mismo mercado y tier", r["precio_puro"], 3, " USD/L",
          "Σ s1·Δp por celda tier × mercado", "nuevo (no está en E)")
    cifra(S, "Mezcla de mercados dentro de cada tier", r["mezcla_mercados"], 3, " USD/L",
          "mezcla por celda tier × mercado − mezcla por tier", "nuevo (no está en E)")
    cifra(S, "Término cruzado por celda", r["cruzado_celda"], 3, " USD/L", "Σ Δs·Δp por celda", "nuevo (no está en E)")

    S = "Caso de negocio"
    cifra(S, "Mezcla × litros S2", r["mezcla_usd_total"] / 1e6, 2, " M USD", "efecto mezcla principal × litros S2", "E:9", 3.13)
    cifra(S, "Ídem con el método simétrico", r["mezcla_usd_total_sim"] / 1e6, 3, " M USD", "sensibilidad", "")
    cifra(S, "Tipo de cambio efectivo S2", r["tc_s2"], 2, " CLP/USD",
          "Σ neto CLP / Σ neto USD, dólar del día de la factura", "E:9", 946.34)
    cifra(S, "Mezcla en pesos", r["mezcla_clp_total"] / 1e6, 0, " M CLP", "M USD × TC S2", "E:9 (E:11 lo redondea a 3.000)", 2960, tol=5)

    S = "Magnum"
    cifra(S, "Magnum: % del volumen", r["magnum_vol_pct"], 2, " %", "litros 6x1500 / litros totales", "pedido", 8.07)
    cifra(S, "Magnum: % del ingreso", r["magnum_ing_pct"], 2, " %", "neto USD 6x1500 / total", "pedido", 13.76)
    cifra(S, "Magnum: precio de lista por caja", r["magnum_lista_caja"], 2, " USD/caja", "lista ponderada por cajas", "A:35", 77.26)
    cifra(S, "Gran Reserva estándar: precio de lista por caja", r["grstd_lista_caja"], 2, " USD/caja", "ídem, GR 12x750", "A:35", 77.20)
    cifra(S, "Magnum: neto por caja", r["magnum_neto_caja"], 2, " USD/caja", "Σ neto / Σ cajas", "aclaración para A:35")
    cifra(S, "Gran Reserva estándar: neto por caja", r["grstd_neto_caja"], 2, " USD/caja", "ídem", "aclaración para A:35")
    cifra(S, "Precio anual si el magnum rinde 18 L", r["magnum_18.0"], 2, " USD/L", "sensibilidad a)", "A:37 [por confirmar], S1", 4.47)
    cifra(S, "Precio anual si el magnum rinde 4,5 L", r["magnum_4.5"], 2, " USD/L", "sensibilidad a)", "A:37 [por confirmar], S1", 5.03)
    cifra(S, "Diferencia con 18 L", 100 * (r["magnum_18.0"] / r["precio_anual"] - 1), 1, " %", "vs 9 L", "S1", -7.5)
    cifra(S, "Diferencia con 4,5 L", 100 * (r["magnum_4.5"] / r["precio_anual"] - 1), 1, " %", "vs 9 L", "S1", 4.2)

    S = "Universo y cobertura"
    cifra(S, "Filas crudas de ventas", cs["filas_crudas"], 0, "", "origen_vina.sqlite: ventas", "F:3", 13983)
    cifra(S, "Filas de fact_venta", r["fact_filas"], 0, "", "tras deduplicar; incluye 2026 y nacional", "C:21 [por confirmar]", 13845)
    cifra(S, "Universo de la métrica", r["universo"], 0, "", "exportación, factura 2025", "C:21 [por confirmar], F:5", 10672)
    cifra(S, "Filas de dim_producto", r["dim_producto_filas"], 0, "", "24 productos × 4 añadas", "C:27 [por confirmar]", 96)
    cifra(S, "Duplicados", cs["duplicados"], 0, "", "regla 1", "F:3", 138)
    cifra(S, "Facturas de 2026", r["f2026"], 0, "", "regla 7", "F:3", 83)
    cifra(S, "Excluidas por calidad", cs["duplicados"] + r["f2026"], 0, "", "duplicados + 2026", "F:3", 221)
    cifra(S, "Excluidas por calidad, %", 100 * (cs["duplicados"] + r["f2026"]) / cs["filas_crudas"], 1, " %", "sobre 13.983", "F:3", 1.6)
    cifra(S, "Nacionales 2025", r["nac_2025"], 0, "", "fuera por alcance", "F:3", 3090)
    cifra(S, "Montos recalculados (universo)", r["recalc_u"], 0, "", "regla 5", "F:5", 555)
    cifra(S, "Cajas en botellas (universo)", r["botellas_u"], 0, "", "regla 4", "F:5", 151)
    cifra(S, "Moneda imputada (todas las filas crudas)", cs["moneda_vacia_crudo"], 0, "", "regla 3", "F:5", 698)
    cifra(S, "Moneda imputada (universo)", r["moneda_u"], 0, "", "regla 3; F:5 mezcla bases", "F:5")
    cifra(S, "Costo imputado (universo)", r["costo_imp_u"], 0, "", "par ausente o N/A", "F:5", 1852)

    S = "Bitácora"
    cifra(S, "S3: distorsión con monto crudo, exportación", r["s3_exp"] / 1e6, 1, " M CLP",
          "Σ (neto registrado − neto final) en CLP, universo", "S3", 2782, tol=0.05)
    cifra(S, "S3: ídem, todos los canales 2025", r["s3_todos"] / 1e6, 1, " M CLP",
          "ídem, facturas 2025 de ambos canales", "S3", 2782, tol=0.05)
    cifra(S, "S3: filas que cuadran a ±0,5 %", r["cuadra_05"], 1, " %", "13.845 filas de fact_venta", "S3 («95 %»)", 95, tol=0.5)
    cifra(S, "S4: moneda vacía", r["moneda_vacia_pct"], 1, " %", "filas crudas", "S4", 5.0)
    cifra(S, "S5: filas con costo imputado", r["costo_imputado_pct"], 1, " %", "universo", "S5", 17.4)
    cifra(S, "S6: CLP a fecha de embarque vs factura", r["clp_embarque_vs_factura"], 2, " %",
          "Σ neto CLP; fecha de embarque no confiable (regla 8)", "S6", -0.69)
    cifra(S, "S6: CLP a fecha de cobranza vs factura", r["clp_cobranza_vs_factura"], 2, " %",
          "Σ neto CLP; factura + 60 días sur / + 90 norte; dólar 2025 y 2026", "S6", -1.44)
    cifra(S, "S7: margen bruto (costo de la merma sin reversar)", r["margen"], 2, " %",
          "1 − Σ costo |cajas| / Σ neto CLP, universo", "S7", 47.25)
    cifra(S, "S7: margen si se reversara el costo de la merma", r["margen_reversa"], 2, " %", "costo con signo", "S7", 48.05)
    cifra(S, "S7: brecha", r["brecha_merma"] / 1e6, 0, " M CLP", "costo |cajas| − costo con signo", "S7", 419)
    cifra(S, "S8: Brasil, Gran Reserva % litros S1", r["brasil_gr"][0], 1, " %", "mercado de control (hemisferio sur)", "S8")
    cifra(S, "S8: Brasil, Gran Reserva % litros S2", r["brasil_gr"][1], 1, " %", "ídem", "S8")
    m = r["mensual"]
    cifra(S, "S8: Gran Reserva % litros, mes mínimo", m["gran_reserva_pct_litros"].min(), 1, " %",
          f"mes {int(m.loc[m['gran_reserva_pct_litros'].idxmin(), 'mes'])} (serie en tablas/mensual.csv)", "S8")
    cifra(S, "S8: Gran Reserva % litros, mes máximo", m["gran_reserva_pct_litros"].max(), 1, " %",
          f"mes {int(m.loc[m['gran_reserva_pct_litros'].idxmax(), 'mes'])}", "S8")
    cs_ = r["conteos"]
    cifra(S, "S12: fechas dd/mm/aaaa ambiguas (día ≤ 12)", cs_["fechas_ambiguas"], 0, "", "filas crudas", "S12")
    cifra(S, "S12: ambiguas que calzan con la columna mes como dd/mm", cs_["ambiguas_calzan_ddmm"], 0, "", "", "S12", 1281)
    cifra(S, "S12: ambiguas que calzan con la columna mes como mm/dd", cs_["ambiguas_calzan_mmdd"], 0, "", "", "S12 («7 casos»)", 7)
    cifra(S, "S12: filas cuya columna mes no coincide con la fecha", cs_["mes_discrepante"], 0, "",
          "todos los formatos, también ISO", "S12")

    S = "Figura 4"
    for _, f in r["fig4"].iterrows():
        cifra(S, f"{f['pais']}: Gran Reserva % litros (anual)", f["gran_reserva_pct_litros_anual"], 1, " %",
              f"S1 {num(f['gran_reserva_pct_litros_s1'], 1)} % → S2 {num(f['gran_reserva_pct_litros_s2'], 1)} %",
              "fig. 4", FIG4_TEXTO.get(f["pais"]))

    lineas = ["# Cifras del informe", "",
              "Generado por `src/metrica.py` (vía `python run.py`). No editar a mano.", "",
              "Universo de la métrica: exportación, fecha de factura en 2025, tras las reglas de "
              "`cobertura.md`. «Dónde» cita archivo:línea de `informe/` (A = seccion_A.tex, "
              "C = seccion_C.tex, E = seccion_E.tex, F = seccion_F.tex, Sn = anexo_bitacora.tex). "
              "«Texto»: ✔ si el valor del informe coincide al redondeo publicado; ✘ si no; – si la "
              "cifra no aparece en el texto.", ""]
    actual = None
    for seccion, nombre, v, definicion, donde, estado in filas:
        if seccion != actual:
            lineas += ["", f"## {seccion}", "", "| Cifra | Valor | Definición | Dónde | Texto |",
                       "|---|---:|---|---|---|"]
            actual = seccion
        lineas.append(f"| {nombre} | {v} | {definicion} | {donde} | {estado} |")
    lineas += ["", "## Notas", "",
               "- **S3:** los CLP 2.782 M de la bitácora no se reproducen con ninguna de las dos "
               "definiciones de arriba. El autor de S3 debe aclarar qué sumó.",
               "- **Efecto mezcla (E:9, fig. 1):** el valor es "
               f"{num(r['ef_mezcla'], 4)} USD/L, que redondea a {num(r['ef_mezcla'], 3)}; "
               "los derivados (108 %, USD 3,13 M, CLP ≈ 2.960 M) sí coinciden.",
               "- **S6:** la bitácora usaba el último dólar de 2025 para las fechas posteriores al "
               "30-dic-2025; ahora se usa el dólar observado de 2026 (API /dolar/2026), por eso cambia.",
               "- **Figura 4:** se regenera desde `tablas/fig4_gran_reserva_mercado.csv` y ahora "
               "muestra S1 y S2 por mercado. Los valores escritos a mano en la versión anterior no "
               "salían de los datos.",
               "- **S6:** la fecha de embarque no es confiable (regla 8); la cifra se informa solo "
               "porque la bitácora la cita."]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def guardar_tablas(tablas, carpeta):
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, df in tablas.items():
        df.to_csv(carpeta / f"{nombre}.csv", index=False, encoding="utf-8", float_format="%.6f")
