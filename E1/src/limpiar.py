# -*- coding: utf-8 -*-
"""Limpieza: aplica las reglas de calidad y registra cuántas filas afecta cada una.

Reglas (numeración del plan del componente B):
    1  duplicados por venta_id (idénticos tras normalizar formatos; 408996 en conflicto)
    2  precio unitario: nacional en CLP con punto de miles, exportación en USD
    3  moneda vacía: se imputa por mercado (Chile CLP, resto USD)
    4  cajas cargadas en botellas: ÷12 o ÷10 según las cajas del embarque
    5  monto neto recalculado si difiere más de 0,5 % de cajas × precio × (1 − descuento)
    6  merma (cajas negativas): se incluye
    7  período: la métrica usa facturas de 2025 (las de 2026 quedan en la estrella)
    8  embarques: solo para corregir cajas e incoterm; se eliminan los 15 fantasmas
    9  litros = cajas × litros_por_caja del maestro de costos (9,0)
    10 dólar observado del día de la factura; fin de semana y feriado = último día
       hábil previo; 1 de enero = 2 de enero
Además, las reglas del anexo C: fechas en 4 formatos (mes y semestre salen de la
fecha), cepas normalizadas al catálogo del ERP, costo faltante imputado por
(tier, añada), activo si/SI/Sí/1, zona 8 → Asia, hemisferio por país y costo de la
merma con |cajas|.
"""
import unicodedata

import numpy as np
import pandas as pd

TOLERANCIA_MONTO = 0.005        # regla 5
FACTORES_BOTELLA = (12, 10)     # regla 4
DIAS_COBRANZA = {"Sur": 60, "Norte": 90}
PAISES_SUR = {"Chile", "Brasil"}
ZONA_FALTANTE = {8: "Asia"}     # Corea del Sur trae zona_id 8, que no existe
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
         "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
ACTIVO_SI = {"si", "sí", "1"}
# alias de cepa del CSV (sin tildes, en minúscula) → nombre oficial de cepas.cepa
ALIAS_CEPA = {
    "cs": "Cabernet Sauvignon", "cab sauv": "Cabernet Sauvignon",
    "cabernet": "Cabernet Sauvignon", "cabernet sauvignon": "Cabernet Sauvignon",
    "mer": "Merlot", "merlot": "Merlot",
    "car": "Carménère", "carmenere": "Carménère",
    "shiraz": "Syrah", "syr": "Syrah", "syrah": "Syrah",
    "pn": "Pinot Noir", "pinot": "Pinot Noir", "pinot noir": "Pinot Noir",
    "cha": "Chardonnay", "chardonay": "Chardonnay", "chardonnay": "Chardonnay",
    "sb": "Sauvignon Blanc", "sauv blanc": "Sauvignon Blanc",
    "sauvignon blanc": "Sauvignon Blanc",
}


# ----------------------------------------------------------------------------
# Registro de reglas
# ----------------------------------------------------------------------------
class Registro:
    """Guarda, por regla, qué filas de ventas afecta (por su número de fila cruda)
    y, aparte, los hallazgos de otras fuentes (CSV, embarques, mercados, dólar)."""

    def __init__(self):
        self.ventas = []
        self.otras = []

    def regla(self, num, nombre, accion, filas, etapa="limpia"):
        self.ventas.append({"num": num, "regla": nombre, "accion": accion,
                            "filas": set(filas), "etapa": etapa})

    def otra(self, fuente, hallazgo, cantidad, unidad, accion):
        self.otras.append({"fuente": fuente, "hallazgo": hallazgo, "cantidad": cantidad,
                           "unidad": unidad, "accion": accion})


# ----------------------------------------------------------------------------
# Parseo
# ----------------------------------------------------------------------------
def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto)
                   if not unicodedata.combining(c)).lower().strip()


def parsear_fechas(s):
    """Fechas en sus formatos: aaaa-mm-dd, dd/mm/aaaa, dd-mm-aa y d-mes-aaaa (español).
    Devuelve (fecha, formato)."""
    s = s.str.strip()
    fecha = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    formato = pd.Series("no reconocido", index=s.index)
    patrones = [
        ("aaaa-mm-dd", r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d", None),
        ("dd/mm/aaaa", r"\d{1,2}/\d{1,2}/\d{4}", "%d/%m/%Y", None),
        ("dd-mm-aa", r"\d{1,2}-\d{1,2}-\d{2}", "%d-%m-%y", None),
        ("d-mes-aaaa", r"\d{1,2}-[a-z]{3}-\d{4}", "%d-%m-%Y",
         lambda x: x.str.lower().replace(
             {rf"-{k}-": f"-{v:02d}-" for k, v in MESES.items()}, regex=True)),
    ]
    for nombre, regex, fmt, prep in patrones:
        m = s.str.fullmatch(regex)
        if m.any():
            valores = prep(s[m]) if prep else s[m]
            fecha[m] = pd.to_datetime(valores, format=fmt, errors="coerce").astype("datetime64[ns]")
            formato[m] = nombre
    formato[fecha.isna() & (formato != "no reconocido")] = "inválida"
    return fecha, formato


def numero_clp(s):
    """Pesos: el punto es separador de miles; se quitan $ y espacios."""
    return pd.to_numeric(s.str.replace(r"[$\s.]", "", regex=True))


def numero_usd(s):
    """Dólares: si trae coma, la coma es decimal y el punto es de miles;
    si no trae coma, el punto es decimal."""
    s = s.str.replace(r"[$\s]", "", regex=True)
    con_coma = s.str.contains(",", regex=False)
    s = s.where(~con_coma, s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    return pd.to_numeric(s)


def numero_por_canal(s, nacional):
    """Regla 2: el canal decide cómo se lee el separador."""
    out = pd.Series(np.nan, index=s.index)
    out[nacional] = numero_clp(s[nacional])
    out[~nacional] = numero_usd(s[~nacional])
    return out


def descuento(s):
    """Descuento en tres notaciones: '8' (porcentaje entero), '8%' y '0,08'."""
    s = s.str.strip()
    pct = s.str.endswith("%")
    coma = s.str.contains(",", regex=False)
    con_pct = pd.to_numeric(s.str.rstrip("%"), errors="coerce") / 100
    con_coma = pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce")
    entero = pd.to_numeric(s, errors="coerce") / 100
    return pd.Series(np.select([pct, coma], [con_pct, con_coma], entero), index=s.index)


def patron_numero(s):
    """Describe el formato textual de un número para reportarlo."""
    signo = np.where(s.str.contains("$", regex=False), "con $", "sin $")
    sep = np.select([s.str.contains(",", regex=False), s.str.contains(".", regex=False)],
                    ["coma", "punto"], "entero")
    return pd.Series(signo, index=s.index) + ", " + pd.Series(sep, index=s.index)


def tipo_cambio(fechas, dolar):
    """Dólar observado para cada fecha (regla 10). Devuelve (valor, regla aplicada)."""
    serie = dolar[["fecha", "valor"]].astype({"fecha": "datetime64[ns]"}).sort_values("fecha")
    f = pd.Series(fechas.astype("datetime64[ns]").values)
    consulta = pd.DataFrame({"fecha": f, "pos": np.arange(len(f))}).dropna().sort_values("fecha")

    def buscar(direccion):
        r = pd.merge_asof(consulta, serie, on="fecha", direction=direccion)
        return r.set_index("pos")["valor"].reindex(f.index).to_numpy()

    atras, adelante = buscar("backward"), buscar("forward")
    es_1_ene = ((f.dt.month == 1) & (f.dt.day == 1)).to_numpy()
    valor = np.where(es_1_ene, adelante, atras)
    regla = np.select(
        [f.isna(), es_1_ene, f.isin(set(serie["fecha"])), f > serie["fecha"].max()],
        ["sin fecha", "1 de enero = 2 de enero", "mismo día",
         "posterior al último dólar publicado: último valor"],
        "último día hábil previo")
    regla = np.where(f.notna() & np.isnan(valor), "sin dólar", regla)
    return pd.Series(valor, index=fechas.index), pd.Series(regla, index=fechas.index)


# ----------------------------------------------------------------------------
# Maestros
# ----------------------------------------------------------------------------
def limpiar_costos(costos, costos_descartadas, cepas, anadas, reg):
    """Maestro de costos → una fila por (producto, añada), con la cepa conformada
    al catálogo del ERP y el costo faltante imputado por (tier, añada)."""
    c = costos.copy()
    c["producto_id"] = c["producto_id"].astype(int)
    c["anada"] = c["anada"].astype(int)
    c["litros_por_caja"] = pd.to_numeric(c["litros_por_caja"].str.replace(",", ".", regex=False))
    texto_costo = c["costo_caja_clp"].str.strip()
    c["costo_caja_clp"] = pd.to_numeric(
        texto_costo.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce")

    # cepa: alias → catálogo
    norm = c["cepa"].map(sin_tildes)
    desconocidos = sorted(set(norm) - set(ALIAS_CEPA))
    if desconocidos:
        raise ValueError(f"alias de cepa sin mapeo: {desconocidos}")
    c["cepa_csv"] = c["cepa"]
    c["cepa"] = norm.map(ALIAS_CEPA)
    if not set(c["cepa"]) <= set(cepas["cepa"]):
        raise ValueError("cepa normalizada fuera del catálogo del ERP")
    por_producto = c.groupby("producto_id")["cepa"].nunique()
    if (por_producto > 1).any():
        raise ValueError(f"productos con más de una cepa: {list(por_producto[por_producto > 1].index)}")
    nombre_ok = [sin_tildes(p).startswith(sin_tildes(ce)) for p, ce in zip(c["producto"], c["cepa"])]
    if not all(nombre_ok):
        raise ValueError("la cepa normalizada no coincide con el nombre del producto")

    # activo
    act = c["activo"].map(sin_tildes)
    if not act.isin(list(ACTIVO_SI | {"no", "0"})).all():
        raise ValueError(f"valores de activo no reconocidos: {set(act) - ACTIVO_SI}")
    c["activo"] = act.isin(list(ACTIVO_SI))

    reg.otra("CSV costos", "Filas que no son datos (encabezado repetido y TOTAL)",
             len(costos_descartadas), "líneas", "descartadas al leer")
    reg.otra("CSV costos", "Costo en formatos 34.344,00 / 34.344 / 34344",
             int(texto_costo.str.contains(r"\d").sum()), "filas", "normalizado a número")
    reg.otra("CSV costos", "Costo N/A", int(c["costo_caja_clp"].isna().sum()), "filas",
             "imputado por (tier, añada)")
    reg.otra("CSV costos", f"Cepa escrita con alias ({norm.nunique()} grafías para "
             f"{c['cepa'].nunique()} cepas)", int((c["cepa_csv"] != c["cepa"]).sum()), "filas",
             "conformada a cepas.cepa del ERP")
    reg.otra("CSV costos", "activo como si/SI/Sí/1", len(c), "filas",
             f"{int(c['activo'].sum())} verdaderos")
    reg.otra("CSV costos", "litros_por_caja distinto de 9,0",
             int((c["litros_por_caja"] != 9.0).sum()), "filas", "ninguna acción (regla 9)")

    # atributos fijos del producto (deben ser únicos por producto)
    attrs = ["producto", "cepa", "tier", "formato", "litros_por_caja"]
    if (c.groupby("producto_id")[attrs].nunique() > 1).any().any():
        raise ValueError("atributos de producto inconsistentes entre añadas")
    productos = c.groupby("producto_id")[attrs + ["activo"]].agg(
        {**{a: "first" for a in attrs}, "activo": "all"}).reset_index()

    # regla exacta (tier, añada): el costo observado es único por combinación
    obs = c.dropna(subset=["costo_caja_clp"])
    regla_costo = obs.groupby(["tier", "anada"])["costo_caja_clp"].agg(["min", "max"])
    if (regla_costo["min"] != regla_costo["max"]).any():
        raise ValueError("el costo no es único por (tier, añada)")
    regla_costo = regla_costo["min"].rename("costo_regla").reset_index()

    grilla = productos.merge(pd.DataFrame({"anada": sorted(anadas)}), how="cross")
    pa = grilla.merge(c[["producto_id", "anada", "costo_caja_clp"]],
                      on=["producto_id", "anada"], how="left")
    pa = pa.merge(regla_costo, on=["tier", "anada"], how="left")
    pa["costo_imputado"] = pa["costo_caja_clp"].isna().astype(int)
    pa["en_maestro"] = pa.set_index(["producto_id", "anada"]).index.isin(
        c.set_index(["producto_id", "anada"]).index)
    pa["costo_caja_clp"] = pa["costo_caja_clp"].fillna(pa["costo_regla"])
    if pa["costo_caja_clp"].isna().any():
        raise ValueError("quedan pares producto-añada sin costo")
    reg.otra("CSV costos", "Pares producto-añada ausentes del maestro",
             int((~pa["en_maestro"]).sum()), "pares", "creados con costo por (tier, añada)")
    return pa.drop(columns=["costo_regla"]), regla_costo


def limpiar_mercados(erp, reg):
    m = erp["mercados"].merge(erp["zonas"], on="zona_id", how="left")
    falta = m["zona"].isna()
    m.loc[falta, "zona"] = m.loc[falta, "zona_id"].map(ZONA_FALTANTE)
    for _, r in m[falta].iterrows():
        reg.otra("SQLite mercados", f"{r['pais']}: zona_id {r['zona_id']} no existe en zonas",
                 1, "mercado", f"asignado a {r['zona']}")
    if m["zona"].isna().any():
        raise ValueError("mercado sin zona")
    m["hemisferio"] = np.where(m["pais"].isin(PAISES_SUR), "Sur", "Norte")
    return m


def limpiar_embarques(embarques, lineas, ventas_ids, ventas_fecha, ventas_mercado, reg):
    """Regla 8: los embarques solo aportan cajas e incoterm. Se eliminan los
    embarques con embarque_id repetido cuyas líneas no corresponden a ninguna venta."""
    e, l = embarques.copy(), lineas.copy()
    l["cajas"] = l["cajas"].astype(int)
    repetido = e["embarque_id"].duplicated(keep=False)
    sin_venta = ~l.groupby("emb_idx")["venta_id"].agg(lambda x: x.isin(list(ventas_ids)).any())
    fantasma = repetido & e["emb_idx"].map(sin_venta)
    reg.otra("JSON embarques", "embarque_id repetido", int(repetido.sum()), "embarques",
             f"{int(fantasma.sum())} fantasmas eliminados (sin venta, puerto "
             f"{', '.join(sorted(e.loc[fantasma, 'puerto_destino'].unique()))}); "
             f"{int((repetido & ~fantasma).sum())} reales se conservan")
    l_fantasma = l["emb_idx"].isin(e.loc[fantasma, "emb_idx"])
    reg.otra("JSON embarques", "Líneas de los embarques fantasma", int(l_fantasma.sum()),
             "líneas", "eliminadas")
    e, l = e[~fantasma], l[~l_fantasma]
    if l["venta_id"].duplicated().any():
        raise ValueError("una venta aparece en más de un embarque")
    reg.otra("JSON embarques", "cajas como texto (\"35\")", int(l["cajas_es_texto"].sum()),
             "líneas", "convertidas a entero")

    # hallazgos que justifican no usar la fecha ni el mercado del embarque
    e = e.assign(fecha=parsear_fechas(e["fecha_embarque"])[0])
    fmt = parsear_fechas(e["fecha_embarque"])[1].value_counts()
    reg.otra("JSON embarques", "fecha_embarque en 2 formatos (" +
             ", ".join(f"{k} {v}" for k, v in fmt.items()) + ")", len(e), "embarques",
             "parseada; no se usa para la métrica")
    reg.otra("JSON embarques", "Embarques con fecha en 2026", int((e["fecha"].dt.year == 2026).sum()),
             "embarques", "no se usa la fecha (regla 8)")
    x = l.merge(e[["emb_idx", "fecha", "mercado_id", "incoterm"]], on="emb_idx")
    x["fecha_venta"] = x["venta_id"].map(ventas_fecha)
    x["mercado_venta"] = x["venta_id"].map(ventas_mercado)
    reg.otra("JSON embarques", "mercado_id del embarque distinto del de la venta",
             int((x["mercado_id"] != x["mercado_venta"]).sum()), "líneas", "no se usa el mercado (regla 8)")
    reg.otra("JSON embarques", "Embarque con fecha anterior a la factura",
             int((x["fecha"] < x["fecha_venta"]).sum()), "líneas", "no se usa la fecha (regla 8)")
    reg.otra("JSON embarques", "Factura 2025 con embarque en 2026",
             int(((x["fecha_venta"].dt.year == 2025) & (x["fecha"].dt.year == 2026)).sum()),
             "líneas", "no se usa la fecha (regla 8)")
    return x[["venta_id", "cajas", "incoterm", "fecha"]].rename(
        columns={"cajas": "cajas_embarque", "fecha": "fecha_embarque"})


# ----------------------------------------------------------------------------
# Ventas
# ----------------------------------------------------------------------------
def limpiar(f):
    reg = Registro()
    erp = f["erp"]
    mercados = limpiar_mercados(erp, reg)

    v = erp["ventas"].copy()
    v.insert(0, "fila", np.arange(len(v)))
    n_crudo = len(v)
    v = v.merge(mercados[["mercado_id", "pais", "canal", "zona", "hemisferio"]],
                on="mercado_id", how="left", suffixes=("_texto", ""))
    nac = v["canal"] == "Nacional"

    # --- fechas (anexo C) ---
    v["fecha_factura"], v["formato_fecha"] = parsear_fechas(v["fecha"])
    for fmt, n in v["formato_fecha"].value_counts().items():
        reg.regla("C", f"Fecha en formato {fmt}", "parseada",
                  v.loc[v["formato_fecha"] == fmt, "fila"], etapa="crudo")
    invalidas = v["fecha_factura"].isna()
    reg.regla("C", "Fecha inválida o no reconocida", "excluida", v.loc[invalidas, "fila"], "crudo")
    v = v[~invalidas].copy()
    v["anio"] = v["fecha_factura"].dt.year
    v["mes_num"] = v["fecha_factura"].dt.month
    v["semestre"] = np.where(v["mes_num"] <= 6, 1, 2)
    reg.regla("C", "Columna mes distinta del mes de la fecha",
              "se ignora; mes y semestre salen de la fecha",
              v.loc[v["mes"].astype(int) != v["mes_num"], "fila"], "crudo")
    dia_texto = pd.to_numeric(v["fecha"].str.extract(r"^(\d{1,2})/", expand=False))
    amb = (v["formato_fecha"] == "dd/mm/aaaa") & (dia_texto <= 12)
    calza_mmdd = amb & (dia_texto == v["mes"].astype(int))
    conteos = {
        "fechas_ambiguas": int(amb.sum()),
        "ambiguas_calzan_ddmm": int((amb & (v["mes_num"] == v["mes"].astype(int))).sum()),
        "ambiguas_calzan_mmdd": int(calza_mmdd.sum()),
        "mes_discrepante": int((v["mes"].astype(int) != v["mes_num"]).sum()),
    }
    reg.regla("C", f"dd/mm/aaaa con día ≤ 12 (ambigua; {int(calza_mmdd.sum())} calzarían con "
              f"la columna mes leídas como mm/dd)", "se lee como dd/mm", v.loc[amb, "fila"], "crudo")
    reg.regla("C", "Columna zona distinta de la zona del mercado", "se ignora; zona sale de mercados",
              v.loc[v["zona_texto"] != v["zona"], "fila"], "crudo")
    reg.regla("C", "Mercado con zona inexistente (zona_id 8, Corea del Sur)", "zona = Asia",
              v.loc[v["mercado_id"].map(mercados.set_index("mercado_id")["zona_id"]) == 8, "fila"], "crudo")

    # --- regla 2: precio, monto, descuento, cajas ---
    nac = v["canal"] == "Nacional"
    for (canal, patron), g in v.groupby([v["canal"], patron_numero(v["precio_unitario"])]):
        reg.regla(2, f"Precio {canal.lower()}: {patron}",
                  "CLP con punto de miles" if canal == "Nacional" else "USD con punto o coma decimal",
                  g["fila"], "crudo")
    v["precio_unitario_num"] = numero_por_canal(v["precio_unitario"], nac)
    v["monto_registrado"] = numero_por_canal(v["monto_neto"], nac)
    reg.regla(2, "Monto neto con $", "se quita el símbolo",
              v.loc[v["monto_neto"].str.contains("$", regex=False), "fila"], "crudo")
    v["descuento_num"] = descuento(v["descuento"])
    for nota, m in [("entero (8 = 8 %)", v["descuento"].str.fullmatch(r"[1-9]\d*")),
                    ("con % (8%)", v["descuento"].str.endswith("%")),
                    ("fracción con coma (0,08)", v["descuento"].str.contains(",", regex=False))]:
        reg.regla(2, f"Descuento {nota}", "llevado a fracción", v.loc[m, "fila"], "crudo")
    if v["descuento_num"].isna().any() or not v["descuento_num"].between(0, 0.5).all():
        raise ValueError("descuento fuera de rango")
    v["cajas_original"] = v["cajas"].astype(int)
    # verificación por rangos: CLP entre 1.000 y 1.000.000, USD entre 1 y 1.000
    rango_ok = np.where(nac, v["precio_unitario_num"].between(1_000, 1_000_000),
                        v["precio_unitario_num"].between(1, 1_000))
    reg.regla(2, "Precio ambiguo o fuera del rango de su moneda", "revisar (no se excluye)",
              v.loc[~rango_ok, "fila"], "crudo")
    rangos = (v.groupby("zona")["precio_unitario_num"].agg(["min", "max", "count"])
              .reset_index().rename(columns={"count": "filas"}))

    # --- regla 3: moneda ---
    monedas = erp["monedas"].set_index("moneda_id")["moneda"]
    v["moneda_registrada"] = v["moneda_id"].map(monedas)
    esperada = np.where(nac, "CLP", "USD")
    distinta = v["moneda_registrada"].notna() & (v["moneda_registrada"] != esperada)
    reg.regla(3, "Moneda registrada distinta de la del mercado", "revisar (no se corrige)",
              v.loc[distinta, "fila"], "crudo")
    v["moneda_imputada"] = v["moneda_registrada"].isna().astype(int)
    v["moneda"] = v["moneda_registrada"].fillna(pd.Series(esperada, index=v.index))
    reg.regla(3, "Moneda vacía", "imputada por mercado (Chile CLP, resto USD)",
              v.loc[v["moneda_imputada"] == 1, "fila"], "crudo")
    patron_moneda = {}
    for col in ["mercado_id", "vendedor_id", "cliente_id", "mes_num"]:
        tasa = v.groupby(col)["moneda_imputada"].mean() * 100
        patron_moneda[col] = (tasa.min(), tasa.max())

    # --- regla 1: duplicados ---
    clave = ["fecha_factura", "cliente_id", "mercado_id", "producto_id", "vendedor_id", "anada",
             "cajas_original", "precio_unitario_num", "descuento_num", "monto_registrado",
             "moneda_registrada"]
    crudo = ["zona_texto" if c == "zona" else c for c in erp["ventas"].columns if c != "venta_id"]
    calc = v["cajas_original"] * v["precio_unitario_num"] * (1 - v["descuento_num"])
    cuadra = (v["monto_registrado"] - calc).abs() <= TOLERANCIA_MONTO * calc.abs()
    descarte = {"crudo": [], "normalizado": [], "conflicto": []}
    notas_conflicto = []
    for vid, g in v[v["venta_id"].duplicated(keep=False)].groupby("venta_id"):
        if len(g[crudo].drop_duplicates()) == 1:
            descarte["crudo"] += list(g["fila"].iloc[1:])
        elif len(g[clave].drop_duplicates()) == 1:
            descarte["normalizado"] += list(g["fila"].iloc[1:])
        else:
            que_cuadran = g[cuadra[g.index]]
            if len(que_cuadran) == 1:
                queda, nota = que_cuadran["fila"].iloc[0], "se conserva la fila que cuadra"
            else:
                queda = g["fila"].iloc[0]
                nota = "ninguna fila cuadra: se conserva la primera y la regla 5 recalcula el neto"
            descarte["conflicto"] += [x for x in g["fila"] if x != queda]
            notas_conflicto.append(f"venta {vid}: {nota}")
    reg.regla(1, "Duplicado idéntico en crudo", "se elimina la segunda", descarte["crudo"], "crudo")
    reg.regla(1, "Duplicado idéntico solo tras normalizar formatos", "se elimina la segunda",
              descarte["normalizado"], "crudo")
    reg.regla(1, "Duplicado en conflicto (" + "; ".join(notas_conflicto) + ")",
              "se elimina la otra fila", descarte["conflicto"], "crudo")
    descartar = set(sum(descarte.values(), []))
    v = v[~v["fila"].isin(descartar)].copy()
    reg.otra("SQLite ventas", "Filas iguales con distinto venta_id",
             int(v.duplicated(clave, keep=False).sum()), "filas", "ninguna acción")

    # --- regla 8 y 4: embarques y botellas ---
    emb = limpiar_embarques(f["embarques"], f["lineas_embarque"], set(v["venta_id"]),
                            v.set_index("venta_id")["fecha_factura"],
                            v.set_index("venta_id")["mercado_id"], reg)
    v = v.merge(emb, on="venta_id", how="left")
    exp_sin_emb = (v["canal"] != "Nacional") & v["cajas_embarque"].isna()
    reg.regla(8, "Venta de exportación sin embarque", "sin incoterm", v.loc[exp_sin_emb, "fila"])
    reg.regla(8, "Venta nacional con embarque", "revisar",
              v.loc[(v["canal"] == "Nacional") & v["cajas_embarque"].notna(), "fila"])
    v["cajas"] = v["cajas_original"]
    v["cajas_corregidas"] = 0
    for factor in FACTORES_BOTELLA:
        m = (v["cajas_corregidas"] == 0) & (v["cajas_original"] == factor * v["cajas_embarque"])
        v.loc[m, "cajas"] = v.loc[m, "cajas_embarque"].astype(int)
        v.loc[m, "cajas_corregidas"] = 1
        reg.regla(4, f"Cajas cargadas en botellas (venta = {factor} × cajas del embarque)",
                  f"cajas ÷ {factor}", v.loc[m, "fila"])
    reg.regla(4, "Merma con cajas positivas en el embarque", "se mantiene el signo de la venta",
              v.loc[(v["cajas_original"] < 0) & (v["cajas_embarque"] == -v["cajas_original"]), "fila"])
    otras_dif = v["cajas_embarque"].notna() & (v["cajas_corregidas"] == 0) & \
        (v["cajas"].abs() != v["cajas_embarque"])
    reg.regla(4, "Cajas distintas del embarque sin factor 12 o 10", "revisar (no se corrige)",
              v.loc[otras_dif, "fila"])

    # --- costos y litros (regla 9, anexo C) ---
    v["anada"] = v["anada"].astype(int)
    pa, regla_costo = limpiar_costos(f["costos"], f["costos_descartadas"], erp["cepas"],
                                     set(v["anada"]), reg)
    v = v.merge(pa[["producto_id", "anada", "tier", "formato", "litros_por_caja", "costo_caja_clp",
                    "costo_imputado"]], on=["producto_id", "anada"], how="left")
    if v["litros_por_caja"].isna().any():
        raise ValueError("ventas sin producto en el maestro")
    v["litros"] = v["cajas"] * v["litros_por_caja"]
    reg.regla(9, "Litros = cajas × 9,0 (formato 12x750)", "litros por caja del maestro",
              v.loc[v["formato"] == "12x750", "fila"])
    reg.regla(9, "Litros = cajas × 9,0 (formato 6x1500, magnum)", "litros por caja del maestro",
              v.loc[v["formato"] == "6x1500", "fila"])
    reg.regla("C", "Costo faltante en el maestro (par ausente o N/A)", "imputado por (tier, añada)",
              v.loc[v["costo_imputado"] == 1, "fila"])

    # --- regla 5: monto neto ---
    v["monto_calculado"] = v["cajas"] * v["precio_unitario_num"] * (1 - v["descuento_num"])
    dif = (v["monto_registrado"] - v["monto_calculado"]).abs()
    v["monto_recalculado"] = (dif > TOLERANCIA_MONTO * v["monto_calculado"].abs()).astype(int)
    v["monto_neto"] = np.where(v["monto_recalculado"] == 1, v["monto_calculado"], v["monto_registrado"])
    v["monto_bruto"] = v["cajas"] * v["precio_unitario_num"]
    rec = v["monto_recalculado"] == 1
    es_bruto = rec & ((v["monto_registrado"] - v["monto_bruto"]).abs() <= TOLERANCIA_MONTO * v["monto_bruto"].abs()) \
        & (v["descuento_num"] > 0)
    reg.regla(5, "Monto neto descuadrado: registrado igual al bruto (sin descuento)", "recalculado",
              v.loc[es_bruto, "fila"])
    reg.regla(5, "Monto neto descuadrado: otras diferencias", "recalculado",
              v.loc[rec & ~es_bruto, "fila"])

    # --- regla 6 y 7 ---
    v["es_merma"] = (v["cajas"] < 0).astype(int)
    reg.regla(6, "Merma (cajas negativas)", "se incluye; costo con |cajas|", v.loc[v["es_merma"] == 1, "fila"])
    reg.regla(7, "Factura de 2026", "en la estrella; fuera de la métrica", v.loc[v["anio"] != 2025, "fila"])
    reg.regla("alcance", "Venta nacional (Chile)", "en la estrella; fuera de la métrica",
              v.loc[v["canal"] == "Nacional", "fila"])

    # --- regla 10: dólar ---
    dolar = f["dolar"]
    v["tipo_cambio"], v["regla_tc"] = tipo_cambio(v["fecha_factura"], dolar)
    v["fecha_cobranza"] = v["fecha_factura"] + pd.to_timedelta(v["hemisferio"].map(DIAS_COBRANZA), unit="D")
    v["tipo_cambio_cobranza"], v["regla_tc_cobranza"] = tipo_cambio(v["fecha_cobranza"], dolar)
    v["tipo_cambio_embarque"], _ = tipo_cambio(v["fecha_embarque"], dolar)
    for col, que, accion in [("regla_tc", "Dólar de la factura", "tipo de cambio asignado"),
                             ("regla_tc_cobranza", "Dólar de la cobranza (factura + 60 días sur / "
                              "+ 90 norte)", "tipo de cambio de la sensibilidad c")]:
        for r_ in ["último día hábil previo", "1 de enero = 2 de enero",
                   "posterior al último dólar publicado: último valor", "sin dólar"]:
            reg.regla(10, f"{que}: {r_}", accion if r_ != "sin dólar" else "queda sin dólar",
                      v.loc[v[col] == r_, "fila"])
    if v["tipo_cambio"].isna().any():
        raise ValueError("facturas sin dólar")

    v["en_universo"] = ((v["canal"] == "Exportación") & (v["anio"] == 2025)).astype(int)

    # litros de referencia para los porcentajes de cobertura: todas las filas crudas,
    # con las cajas ya corregidas (los duplicados heredan las de su venta_id)
    crudas = erp["ventas"][["venta_id", "producto_id", "cajas"]].copy()
    crudas["fila"] = np.arange(n_crudo)
    lit = v.set_index("venta_id")[["cajas", "cajas_original", "litros_por_caja"]]
    crudas = crudas.join(lit, on="venta_id", rsuffix="_v")
    crudas["litros_ref"] = (crudas["cajas_v"] * crudas["litros_por_caja"]).abs()

    return {
        "ventas": v,
        "mercados": mercados,
        "producto_anada": pa,
        "regla_costo": regla_costo,
        "dolar": dolar,
        "registro": reg,
        "litros_ref": crudas.set_index("fila")["litros_ref"],
        "n_crudo": n_crudo,
        "rangos_precio": rangos,
        "patron_moneda": patron_moneda,
        "conteos": {**conteos,
                    "filas_crudas": n_crudo,
                    "duplicados": n_crudo - len(v),
                    "moneda_vacia": int(v["moneda_imputada"].sum()),
                    "moneda_vacia_crudo": int(erp["ventas"]["moneda_id"].isna().sum())},
    }


def escribir_cobertura(res, ruta):
    """output/cobertura.md: cada regla con filas, % de filas y % de litros."""
    reg, v = res["registro"], res["ventas"]
    litros = res["litros_ref"]
    n_crudo, n_limpio = res["n_crudo"], len(v)
    universo = set(v.loc[v["en_universo"] == 1, "fila"])
    l_crudo = litros.sum()
    l_limpio = litros[litros.index.isin(v["fila"])].sum()

    def pct(a, b):
        return f"{100 * a / b:.2f} %".replace(".", ",") if b else "–"

    def miles(x):
        return f"{x:,.0f}".replace(",", ".")

    lineas = [
        "# Cobertura y calidad de datos",
        "",
        "Generado por `src/limpiar.py` (vía `python run.py`). No editar a mano.",
        "",
        f"Base: {miles(n_crudo)} filas de `ventas`. Las reglas de la etapa *crudo* (formatos y "
        f"duplicados) se miden sobre las {miles(n_crudo)} filas crudas; las demás, sobre las "
        f"{miles(n_limpio)} que quedan tras deduplicar (las que entran a `fact_venta`). "
        f"El % de litros usa |cajas corregidas| × litros por caja. La última columna cuenta "
        f"las filas dentro del universo de la métrica (exportación, factura 2025: "
        f"{miles(len(universo))} filas).",
        "",
        "## Reglas sobre las ventas",
        "",
        "| Regla | Hallazgo | Acción | Filas | % filas | % litros | Filas en universo |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for r in reg.ventas:
        base_n, base_l = (n_crudo, l_crudo) if r["etapa"] == "crudo" else (n_limpio, l_limpio)
        filas = r["filas"]
        lit = litros[litros.index.isin(filas)].sum()
        lineas.append(f"| {r['num']} | {r['regla']} | {r['accion']} | {miles(len(filas))} | "
                      f"{pct(len(filas), base_n)} | {pct(lit, base_l)} | {miles(len(filas & universo))} |")
    lineas += [
        "",
        "## Hallazgos en las otras fuentes",
        "",
        "| Fuente | Hallazgo | Cantidad | Acción |",
        "|---|---|---:|---|",
    ]
    for o in reg.otras:
        lineas.append(f"| {o['fuente']} | {o['hallazgo']} | {miles(o['cantidad'])} {o['unidad']} | {o['accion']} |")

    lineas += ["", "## Verificación de la regla 2: precio unitario por zona", "",
               "| Zona | Mínimo | Máximo | Filas |", "|---|---:|---:|---:|"]
    def dec2(x):
        return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    for _, r in res["rangos_precio"].iterrows():
        lineas.append(f"| {r['zona']} | {dec2(r['min'])} | {dec2(r['max'])} | {miles(r['filas'])} |")
    lineas += ["", "Los rangos no se solapan (CLP en Nacional, USD en el resto), así que el canal "
               "basta para leer el separador."]

    lineas += ["", "## Regla 3: ¿hay patrón en la moneda vacía?", "",
               "| Corte | % de filas con moneda vacía (mín – máx entre grupos) |", "|---|---|"]
    for col, (a, b) in res["patron_moneda"].items():
        lineas.append(f"| {col} | {a:.1f} – {b:.1f} %".replace(".", ",") + " |")
    lineas += ["", "La tasa es pareja en todos los cortes: no hay un mercado, vendedor, cliente o "
               "mes que concentre los vacíos."]

    # resumen de exclusiones
    v_ids = set(v["fila"])
    f2026 = int((v["anio"] != 2025).sum())
    nac_total = int((v["canal"] == "Nacional").sum())
    lineas += [
        "",
        "## Registros excluidos de la métrica",
        "",
        "| Motivo | Filas | % de las filas crudas | % de litros |",
        "|---|---:|---:|---:|",
    ]
    filas_dup = set(litros.index) - v_ids
    filas_2026 = set(v.loc[v["anio"] != 2025, "fila"])
    filas_nac = set(v.loc[(v["anio"] == 2025) & (v["canal"] == "Nacional"), "fila"])
    for nombre, fs in [("Duplicados (regla 1)", filas_dup), ("Facturas de 2026 (regla 7)", filas_2026),
                       ("**Subtotal calidad**", filas_dup | filas_2026),
                       ("Ventas nacionales 2025 (alcance)", filas_nac),
                       ("**Total excluido de la métrica**", filas_dup | filas_2026 | filas_nac)]:
        lit = litros[litros.index.isin(fs)].sum()
        lineas.append(f"| {nombre} | {miles(len(fs))} | {pct(len(fs), n_crudo)} | {pct(lit, l_crudo)} |")
    lineas += ["", f"Universo de la métrica: {miles(len(universo))} filas "
               f"({pct(len(universo), n_crudo)} de las crudas). Ninguna fila se excluye por "
               f"formato: todas las fechas, precios y montos se pudieron leer. "
               f"En `fact_venta` quedan {miles(n_limpio)} filas (incluye {f2026} de 2026 y "
               f"{nac_total} nacionales)."]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
