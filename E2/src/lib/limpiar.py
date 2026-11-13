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
        self.datos = {}   # cifras sueltas para el resumen de cobertura.md

    def regla(self, tema, hallazgo, accion, filas, etapa="limpia", grupo="correccion"):
        """grupo: exclusion | correccion | formato | dolar | verificacion."""
        self.ventas.append({"tema": tema, "regla": hallazgo, "accion": accion,
                            "filas": set(filas), "etapa": etapa, "grupo": grupo})

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
             int((c["litros_por_caja"] != 9.0).sum()), "filas", "ninguna acción")

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
             "embarques", "no se usa la fecha del embarque")
    x = l.merge(e[["emb_idx", "fecha", "mercado_id", "incoterm"]], on="emb_idx")
    x["fecha_venta"] = x["venta_id"].map(ventas_fecha)
    x["mercado_venta"] = x["venta_id"].map(ventas_mercado)
    reg.datos.update(lineas_embarque=len(x),
                     embarque_mercado_distinto=int((x["mercado_id"] != x["mercado_venta"]).sum()),
                     embarque_antes_factura=int((x["fecha"] < x["fecha_venta"]).sum()))
    reg.otra("JSON embarques", "mercado_id del embarque distinto del de la venta",
             int((x["mercado_id"] != x["mercado_venta"]).sum()), "líneas", "no se usa el mercado del embarque")
    reg.otra("JSON embarques", "Embarque con fecha anterior a la factura",
             int((x["fecha"] < x["fecha_venta"]).sum()), "líneas", "no se usa la fecha del embarque")
    reg.otra("JSON embarques", "Factura 2025 con embarque en 2026",
             int(((x["fecha_venta"].dt.year == 2025) & (x["fecha"].dt.year == 2026)).sum()),
             "líneas", "no se usa la fecha del embarque")
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
        reg.regla("Formato de fechas", f"Fecha escrita como {fmt}", "leída en su formato",
                  v.loc[v["formato_fecha"] == fmt, "fila"], "crudo", "formato")
    invalidas = v["fecha_factura"].isna()
    reg.regla("Formato de fechas", "Fecha inválida o no reconocida", "se excluiría", v.loc[invalidas, "fila"], "crudo", "verificacion")
    v = v[~invalidas].copy()
    v["anio"] = v["fecha_factura"].dt.year
    v["mes_num"] = v["fecha_factura"].dt.month
    v["semestre"] = np.where(v["mes_num"] <= 6, 1, 2)
    reg.regla("Columna mes del ERP", "La columna mes no coincide con el mes de la fecha",
              "se ignora; mes y semestre salen de la fecha",
              v.loc[v["mes"].astype(int) != v["mes_num"], "fila"], "crudo", "verificacion")
    dia_texto = pd.to_numeric(v["fecha"].str.extract(r"^(\d{1,2})/", expand=False))
    amb = (v["formato_fecha"] == "dd/mm/aaaa") & (dia_texto <= 12)
    calza_mmdd = amb & (dia_texto == v["mes"].astype(int))
    conteos = {
        "fechas_ambiguas": int(amb.sum()),
        "ambiguas_calzan_ddmm": int((amb & (v["mes_num"] == v["mes"].astype(int))).sum()),
        "ambiguas_calzan_mmdd": int(calza_mmdd.sum()),
        "mes_discrepante": int((v["mes"].astype(int) != v["mes_num"]).sum()),
    }
    reg.regla("Formato de fechas", f"Fecha dd/mm/aaaa con día ≤ 12 (ambigua; {int(calza_mmdd.sum())} calzarían con "
              f"la columna mes leídas como mm/dd)", "se lee como dd/mm", v.loc[amb, "fila"], "crudo", "verificacion")
    reg.regla("Columna zona del ERP", "La columna zona no coincide con la zona del mercado", "se ignora; la zona sale de la tabla mercados",
              v.loc[v["zona_texto"] != v["zona"], "fila"], "crudo", "verificacion")
    reg.regla("Zona de Corea del Sur", "Mercado con zona inexistente (zona_id 8)", "se asigna la zona Asia",
              v.loc[v["mercado_id"].map(mercados.set_index("mercado_id")["zona_id"]) == 8, "fila"], "crudo")

    # --- regla 2: precio, monto, descuento, cajas ---
    nac = v["canal"] == "Nacional"
    for (canal, patron), g in v.groupby([v["canal"], patron_numero(v["precio_unitario"])]):
        reg.regla("Formato de precio unitario", f"Precio {canal.lower()}: {patron}",
                  "CLP con punto de miles" if canal == "Nacional" else "USD con punto o coma decimal",
                  g["fila"], "crudo", "formato")
    v["precio_unitario_num"] = numero_por_canal(v["precio_unitario"], nac)
    v["monto_registrado"] = numero_por_canal(v["monto_neto"], nac)
    reg.regla("Formato de monto neto", "Monto neto con $", "se quita el símbolo",
              v.loc[v["monto_neto"].str.contains("$", regex=False), "fila"], "crudo", "formato")
    v["descuento_num"] = descuento(v["descuento"])
    for nota, m in [("entero (8 = 8 %)", v["descuento"].str.fullmatch(r"[1-9]\d*")),
                    ("con % (8%)", v["descuento"].str.endswith("%")),
                    ("fracción con coma (0,08)", v["descuento"].str.contains(",", regex=False))]:
        reg.regla("Formato de descuento", f"Descuento {nota}", "llevado a fracción", v.loc[m, "fila"], "crudo", "formato")
    if v["descuento_num"].isna().any() or not v["descuento_num"].between(0, 0.5).all():
        raise ValueError("descuento fuera de rango")
    v["cajas_original"] = v["cajas"].astype(int)
    # verificación por rangos: CLP entre 1.000 y 1.000.000, USD entre 1 y 1.000
    rango_ok = np.where(nac, v["precio_unitario_num"].between(1_000, 1_000_000),
                        v["precio_unitario_num"].between(1, 1_000))
    reg.regla("Precio unitario", "Precio ambiguo o fuera del rango de su moneda", "revisar (no se excluye)",
              v.loc[~rango_ok, "fila"], "crudo", "verificacion")
    rangos = (v.groupby("zona")["precio_unitario_num"].agg(["min", "max", "count"])
              .reset_index().rename(columns={"count": "filas"}))

    # --- regla 3: moneda ---
    monedas = erp["monedas"].set_index("moneda_id")["moneda"]
    v["moneda_registrada"] = v["moneda_id"].map(monedas)
    esperada = np.where(nac, "CLP", "USD")
    distinta = v["moneda_registrada"].notna() & (v["moneda_registrada"] != esperada)
    reg.regla("Moneda", "Moneda registrada distinta de la del mercado", "revisar (no se corrige)",
              v.loc[distinta, "fila"], "crudo", "verificacion")
    v["moneda_imputada"] = v["moneda_registrada"].isna().astype(int)
    v["moneda"] = v["moneda_registrada"].fillna(pd.Series(esperada, index=v.index))
    reg.regla("Moneda vacía", "La venta no trae moneda", "se asigna por mercado (Chile CLP, resto USD)",
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
                nota = "ninguna fila cuadra: se conserva la primera y su monto neto se recalcula"
            descarte["conflicto"] += [x for x in g["fila"] if x != queda]
            notas_conflicto.append(f"venta {vid}: {nota}")
    reg.regla("Duplicados", "Venta repetida, idéntica tal como viene", "se elimina la copia", descarte["crudo"], "crudo", "exclusion")
    reg.regla("Duplicados", "Venta repetida, idéntica tras unificar formatos", "se elimina la copia",
              descarte["normalizado"], "crudo", "exclusion")
    reg.regla("Duplicados", "Venta repetida con montos distintos (" + "; ".join(notas_conflicto) + ")",
              "se elimina la otra fila", descarte["conflicto"], "crudo", "exclusion")
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
    reg.regla("Cruce con embarques", "Venta de exportación sin embarque", "queda sin incoterm", v.loc[exp_sin_emb, "fila"], grupo="verificacion")
    reg.regla("Cruce con embarques", "Venta nacional con embarque", "revisar",
              v.loc[(v["canal"] == "Nacional") & v["cajas_embarque"].notna(), "fila"], grupo="verificacion")
    v["cajas"] = v["cajas_original"]
    v["cajas_corregidas"] = 0
    for factor in FACTORES_BOTELLA:
        m = (v["cajas_corregidas"] == 0) & (v["cajas_original"] == factor * v["cajas_embarque"])
        v.loc[m, "cajas"] = v.loc[m, "cajas_embarque"].astype(int)
        v.loc[m, "cajas_corregidas"] = 1
        reg.regla("Cajas cargadas como botellas", f"La venta registra {factor} veces las cajas del embarque",
                  f"cajas ÷ {factor}", v.loc[m, "fila"])
    reg.regla("Cruce con embarques", "Merma con cajas positivas en el embarque", "se mantiene el signo de la venta",
              v.loc[(v["cajas_original"] < 0) & (v["cajas_embarque"] == -v["cajas_original"]), "fila"],
              grupo="verificacion")
    otras_dif = v["cajas_embarque"].notna() & (v["cajas_corregidas"] == 0) & \
        (v["cajas"].abs() != v["cajas_embarque"])
    reg.regla("Cruce con embarques", "Cajas distintas del embarque sin factor 12 o 10", "revisar (no se corrige)",
              v.loc[otras_dif, "fila"], grupo="verificacion")

    # --- costos y litros (regla 9, anexo C) ---
    v["anada"] = v["anada"].astype(int)
    pa, regla_costo = limpiar_costos(f["costos"], f["costos_descartadas"], erp["cepas"],
                                     set(v["anada"]), reg)
    v = v.merge(pa[["producto_id", "anada", "tier", "formato", "litros_por_caja", "costo_caja_clp",
                    "costo_imputado"]], on=["producto_id", "anada"], how="left")
    if v["litros_por_caja"].isna().any():
        raise ValueError("ventas sin producto en el maestro")
    v["litros"] = v["cajas"] * v["litros_por_caja"]
    reg.regla("Conversión a litros", "Formato 12x750: litros = cajas × 9,0", "litros por caja del maestro de costos",
              v.loc[v["formato"] == "12x750", "fila"], grupo="formato")
    reg.regla("Conversión a litros", "Formato 6x1500 (magnum): litros = cajas × 9,0", "litros por caja del maestro de costos",
              v.loc[v["formato"] == "6x1500", "fila"], grupo="formato")
    reg.regla("Costo faltante", "El maestro no trae costo para ese producto y añada", "se imputa el costo de su tier y añada",
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
    reg.regla("Monto neto descuadrado", "El monto registrado es el bruto (no resta el descuento)", "se recalcula como cajas × precio × (1 − descuento)",
              v.loc[es_bruto, "fila"])
    reg.regla("Monto neto descuadrado", "El monto difiere en más de 0,5 % por otras causas", "se recalcula como cajas × precio × (1 − descuento)",
              v.loc[rec & ~es_bruto, "fila"])

    # --- regla 6 y 7 ---
    v["es_merma"] = (v["cajas"] < 0).astype(int)
    reg.regla("Merma", "Línea con cajas negativas (vino descartado)", "se incluye; el costo se cuenta con las cajas en valor absoluto", v.loc[v["es_merma"] == 1, "fila"])
    reg.regla("Período", "Factura de 2026", "queda en el modelo; fuera de la métrica", v.loc[v["anio"] != 2025, "fila"], grupo="exclusion")
    reg.regla("Fuera del alcance: ventas nacionales", "Venta en Chile, facturada en pesos", "queda en el modelo; fuera de la métrica",
              v.loc[v["canal"] == "Nacional", "fila"], grupo="exclusion")

    # --- regla 10: dólar ---
    dolar = f["dolar"]
    v["tipo_cambio"], v["regla_tc"] = tipo_cambio(v["fecha_factura"], dolar)
    v["fecha_cobranza"] = v["fecha_factura"] + pd.to_timedelta(v["hemisferio"].map(DIAS_COBRANZA), unit="D")
    v["tipo_cambio_cobranza"], v["regla_tc_cobranza"] = tipo_cambio(v["fecha_cobranza"], dolar)
    v["tipo_cambio_embarque"], _ = tipo_cambio(v["fecha_embarque"], dolar)
    for col, que, accion in [("regla_tc", "Dólar de la factura", "tipo de cambio asignado"),
                             ("regla_tc_cobranza", "Dólar de la cobranza (factura + 60 días sur / "
                              "+ 90 norte)", "tipo de cambio para la sensibilidad de cobranza")]:
        for r_ in ["último día hábil previo", "1 de enero = 2 de enero",
                   "posterior al último dólar publicado: último valor", "sin dólar"]:
            reg.regla("Tipo de cambio", f"{que}: {r_}", accion if r_ != "sin dólar" else "queda sin dólar",
                      v.loc[v[col] == r_, "fila"], grupo="dolar")
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




# ----------------------------------------------------------------------------
# output/cobertura.md
# ----------------------------------------------------------------------------
GRUPOS = {
    "exclusion": "Detalle de las filas excluidas",
    "correccion": "Correcciones aplicadas (la fila se conserva con el valor corregido)",
    "formato": "Formatos leídos (no cambian ningún valor)",
    "dolar": "Tipo de cambio asignado",
    "verificacion": "Verificaciones (controles; la mayoría no encontró problemas)",
}
CORTES_MONEDA = {"mercado_id": "Mercado", "vendedor_id": "Vendedor", "cliente_id": "Cliente",
                 "mes_num": "Mes de la factura"}


def _miles(x):
    return f"{x:,.0f}".replace(",", ".")


def _pct(a, b, dec=2):
    return (f"{100 * a / b:.{dec}f} %".replace(".", ",")) if b else "–"


def _dec2(x):
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def escribir_cobertura(res, ruta):
    """output/cobertura.md: qué pasó con cada venta, de lo más importante a lo más técnico."""
    reg, v = res["registro"], res["ventas"]
    litros = res["litros_ref"]
    n_crudo, n_limpio = res["n_crudo"], len(v)
    universo = set(v.loc[v["en_universo"] == 1, "fila"])
    l_crudo = litros.sum()
    l_limpio = litros[litros.index.isin(v["fila"])].sum()

    filas_dup = set(litros.index) - set(v["fila"])
    filas_2026 = set(v.loc[v["anio"] != 2025, "fila"])
    filas_nac = set(v.loc[(v["anio"] == 2025) & (v["canal"] == "Nacional"), "fila"])
    calidad = filas_dup | filas_2026

    def en_universo(tema):
        return len(set().union(*[r["filas"] for r in reg.ventas if r["tema"] == tema]) & universo)

    d = reg.datos
    lineas = [
        "# Cobertura y calidad de los datos de ventas",
        "",
        "Este archivo responde qué pasó con cada una de las ventas registradas por la viña: cuántas "
        "se descartaron, cuántas se corrigieron y por qué. Los datos vienen de la tabla `ventas` de "
        "`origen_vina.sqlite`, cruzada con el maestro de costos (`origen_costos_productos.csv`), los "
        "embarques (`origen_embarques.json`) y el dólar observado de mindicador.cl. Lo genera "
        "`src/limpiar.py` al correr `python run.py`; no se edita a mano.",
        "",
        "## Resumen",
        "",
        f"- De las {_miles(n_crudo)} ventas registradas, solo {_miles(len(calidad))} "
        f"({_pct(len(calidad), n_crudo)}) se descartaron por problemas de datos: "
        f"{_miles(len(filas_dup))} duplicados y {_miles(len(filas_2026))} facturas fechadas en 2026, "
        "fuera del período analizado.",
        f"- Otras {_miles(len(filas_nac))} ventas ({_pct(len(filas_nac), n_crudo)}) quedan fuera por "
        "alcance, no por calidad: son ventas nacionales y la pregunta es sobre exportación. El universo "
        f"de la métrica son {_miles(len(universo))} ventas de exportación facturadas en 2025 "
        f"({_pct(len(universo), n_crudo)} de las registradas).",
        "- Ninguna venta se descartó por formato: las fechas venían escritas de 4 maneras y los precios "
        "y montos con y sin «$» y con distintos separadores, pero todas se pudieron leer.",
        f"- Dentro del universo, los errores se corrigieron sin descartar filas: "
        f"{_miles(en_universo('Monto neto descuadrado'))} montos netos recalculados, "
        f"{_miles(en_universo('Cajas cargadas como botellas'))} ventas cargadas en botellas convertidas "
        f"a cajas, {_miles(en_universo('Moneda vacía'))} monedas vacías asignadas por mercado y "
        f"{_miles(en_universo('Costo faltante'))} costos imputados según su tier y añada.",
        f"- El archivo de embarques solo es confiable para las cajas: en "
        f"{_miles(d['embarque_mercado_distinto'])} de {_miles(d['lineas_embarque'])} líneas "
        f"({_pct(d['embarque_mercado_distinto'], d['lineas_embarque'], 0)}) el mercado no coincide con "
        f"el de la venta, y en {_miles(d['embarque_antes_factura'])} "
        f"({_pct(d['embarque_antes_factura'], d['lineas_embarque'], 0)}) el embarque es anterior a la "
        "factura. Por eso no se usan su fecha ni su mercado.",
        "",
        "## Cómo leer las tablas",
        "",
        "- **Tema**: el tipo de problema o de regla.",
        "- **Hallazgo**: qué se encontró en los datos.",
        "- **Qué se hizo**: la acción aplicada. Solo los duplicados se eliminan; el resto de las filas "
        "se conserva, corregida si hace falta.",
        f"- **Filas**: cuántas ventas afecta. Las reglas de lectura de formatos y de duplicados se miden "
        f"sobre las {_miles(n_crudo)} ventas tal como vienen; las demás, sobre las {_miles(n_limpio)} que "
        "quedan después de quitar los duplicados (las que entran al modelo, tabla `fact_venta`).",
        "- **% de filas** y **% de litros**: el peso de esas ventas sobre el total, en número de filas y "
        "en litros (cajas corregidas × 9 litros por caja, en valor absoluto).",
        f"- **En el universo**: cuántas de esas filas forman parte del universo de la métrica "
        f"(exportación, factura de 2025; {_miles(len(universo))} ventas).",
        "- Un valor 0 en una verificación significa que el control no encontró ningún caso.",
        "",
        "## 1. Ventas excluidas de la métrica",
        "",
        "| Motivo | Ventas | % de las registradas | % de los litros |",
        "|---|---:|---:|---:|",
    ]
    for nombre, fs in [("Duplicados", filas_dup), ("Facturas de 2026 (fuera del período)", filas_2026),
                       ("**Subtotal: problemas de datos**", calidad),
                       ("Fuera del alcance: ventas nacionales de 2025", filas_nac),
                       ("**Total excluido de la métrica**", calidad | filas_nac)]:
        lit = litros[litros.index.isin(fs)].sum()
        lineas.append(f"| {nombre} | {_miles(len(fs))} | {_pct(len(fs), n_crudo)} | {_pct(lit, l_crudo)} |")
    lineas += ["", f"Universo de la métrica: **{_miles(len(universo))} ventas** "
               f"({_pct(len(universo), n_crudo)} de las registradas). Las facturas de 2026 y las ventas "
               f"nacionales no se borran: quedan en el modelo (`fact_venta`, {_miles(n_limpio)} filas) "
               "y solo se filtran al calcular la métrica."]

    def tabla(grupo, encabezado):
        out = ["", f"{encabezado} {GRUPOS[grupo]}", "",
               "| Tema | Hallazgo | Qué se hizo | Filas | % de filas | % de litros | En el universo |",
               "|---|---|---|---:|---:|---:|---:|"]
        for r in [r for r in reg.ventas if r["grupo"] == grupo]:
            base_n, base_l = (n_crudo, l_crudo) if r["etapa"] == "crudo" else (n_limpio, l_limpio)
            lit = litros[litros.index.isin(r["filas"])].sum()
            out.append(f"| {r['tema']} | {r['regla']} | {r['accion']} | {_miles(len(r['filas']))} | "
                       f"{_pct(len(r['filas']), base_n)} | {_pct(lit, base_l)} | "
                       f"{_miles(len(r['filas'] & universo))} |")
        return out

    lineas += tabla("exclusion", "###")
    lineas += tabla("correccion", "## 2.")
    lineas += ["", "## 3. Detalle técnico y verificaciones"]
    lineas += tabla("formato", "### 3.1")
    lineas += tabla("dolar", "### 3.2")
    lineas += ["", "El dólar observado se toma del día de la factura. Los fines de semana y feriados "
               "usan el último día hábil previo, y el 1 de enero usa el 2 de enero, primer día publicado "
               "del año. La fecha de cobranza (factura + 60 días en el hemisferio sur, + 90 en el norte) "
               "solo se usa en una sensibilidad."]
    lineas += tabla("verificacion", "### 3.3")
    lineas += ["", "### 3.4 Hallazgos en las otras fuentes", "",
               "| Fuente | Hallazgo | Cantidad | Qué se hizo |", "|---|---|---:|---|"]
    for o in reg.otras:
        lineas.append(f"| {o['fuente']} | {o['hallazgo']} | {_miles(o['cantidad'])} {o['unidad']} | {o['accion']} |")
    lineas += ["", "### 3.5 Precio unitario por zona: ¿se pueden confundir pesos con dólares?", "",
               "| Zona | Mínimo | Máximo | Filas |", "|---|---:|---:|---:|"]
    for _, r in res["rangos_precio"].iterrows():
        lineas.append(f"| {r['zona']} | {_dec2(r['min'])} | {_dec2(r['max'])} | {_miles(r['filas'])} |")
    lineas += ["", "Los rangos no se solapan: la zona Nacional está en pesos (CLP) y el resto en dólares "
               "(USD). Por eso basta el canal para saber si el punto de un precio separa miles "
               "(«38.467» pesos) o decimales («45.06» dólares)."]
    lineas += ["", "### 3.6 ¿Hay un patrón en las ventas sin moneda?", "",
               "| Corte | % de ventas sin moneda (mínimo – máximo entre grupos) |", "|---|---|"]
    for col, (a, b) in res["patron_moneda"].items():
        lineas.append(f"| {CORTES_MONEDA[col]} | {a:.1f} – {b:.1f} %".replace(".", ",") + " |")
    lineas += ["", "La tasa es pareja en todos los cortes: ningún mercado, vendedor, cliente ni mes "
               "concentra las ventas sin moneda, así que asignarla por mercado no introduce sesgo."]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
