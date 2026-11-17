"""Anexo C del informe de la E2: diccionario de datos con unidad, desde E2/src/lib/esquema.py.

Igual al de la E1 (E1/src/generar_diccionario.py), más la columna «Unidad» que pide el enunciado de la E2.
Uso, desde cualquier carpeta:  python E2/informe/generar_anexo_c.py   -> escribe E2/informe/anexo_C.tex
"""
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path[:0] = [str(AQUI.parent / "src" / "lib"), str(AQUI.parents[1] / "E1" / "src")]
from esquema import TABLAS          # noqa: E402  (el de la E2)
from generar_diccionario import tex  # noqa: E402  (escape de LaTeX de la E1)

SALIDA = AQUI / "anexo_C.tex"


def unidad(col, rol):
    if col in ("litros_por_caja",):
        return "L por caja"
    if col in ("costo_caja_clp",):
        return "CLP por caja"
    if col.startswith("tipo_cambio"):
        return "CLP/USD"
    if col.endswith("_clp"):
        return "CLP"
    if col.endswith("_usd"):
        return "USD"
    if col == "litros":
        return "L"
    if col.startswith("cajas"):
        return "cajas"
    if rol == "indicador" or col.startswith("es_") or col in ("costo_imputado", "activo"):
        return "0/1"
    if col in ("anada", "anio"):
        return "año"
    if col == "fecha":
        return "fecha"
    return "—"


def tabla(nombre, info):
    filas = []
    for col, rol, aditividad, desc, origen, _ in info["columnas"]:
        origen_tex = tex(origen).replace(".", ".\\allowbreak{}")
        filas.append(f"\\texttt{{{tex(col)}}} & {tex(rol)} & {tex(aditividad)} & {tex(unidad(col, rol))} & "
                     f"{tex(desc)} & {origen_tex} \\\\")
    return "\n".join([
        f"\\subsubsection*{{\\texttt{{{tex(nombre)}}}}}",
        tex(info["descripcion"]), "",
        "{\\footnotesize",
        "\\begin{longtable}{@{}>{\\raggedright\\arraybackslash}p{0.18\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.09\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.08\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.075\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.2\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.245\\textwidth}@{}}",
        "\\toprule",
        "Columna & Rol & Aditiv. & Unidad & Descripción & Origen y regla \\\\",
        "\\midrule", "\\endhead", *filas, "\\bottomrule", "\\end{longtable}", "}", ""])


partes = [
    "% Generado por E2/informe/generar_anexo_c.py desde E2/src/lib/esquema.py. No editar a mano.",
    "",
    "\\section*{Anexo C. Diccionario de datos}",
    "\\addcontentsline{toc}{section}{Anexo C. Diccionario de datos}",
    "",
    "Sale del mismo esquema que usa la cadena para construir el oro, así que no puede quedar desfasado del código. "
    "Para cada campo: su rol en el modelo, si se puede sumar, su unidad, su significado de negocio y de qué columna de "
    "origen sale y con qué regla. Las columnas nuevas de la E2 son las del dólar a la cobranza y al embarque, la marca de "
    "costo imputado y las cajas y el monto tal como venían en el ERP (sección~\\ref{sec:modelo}).",
    "",
]
partes += [tabla(n, i) for n, i in TABLAS.items()]
SALIDA.write_text("\n".join(partes), encoding="utf-8")
print("Anexo C guardado en", SALIDA)
