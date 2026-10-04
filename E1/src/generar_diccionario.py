# -*- coding: utf-8 -*-
"""Escribe el diccionario de datos del modelo en LaTeX, desde esquema.py.

Salida: informe/anexo_C_diccionario.tex (requiere los paquetes array, longtable y booktabs).
Uso:    python src/generar_diccionario.py   (desde la carpeta entrega1/)
"""
from pathlib import Path

from esquema import TABLAS

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "informe" / "anexo_C_diccionario.tex"

# El orden importa: primero los caracteres reservados, después los símbolos
# Unicode que pdflatex no conoce (sus reemplazos traen $ y llaves a propósito).
REEMPLAZOS = [
    ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
    ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
    ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
    ("→", r"$\rightarrow$"), ("−", "$-$"), ("×", r"$\times$"),
    ("÷", r"$\div$"), ("·", r"$\cdot$"), ("|", r"\textbar{}"),
]


def tex(texto):
    for viejo, nuevo in REEMPLAZOS:
        texto = texto.replace(viejo, nuevo)
    return texto


def tabla_latex(nombre, info):
    filas = []
    for col, rol, aditividad, desc, origen, _ in info["columnas"]:
        # permite cortar la línea después de un punto (tabla.columna)
        origen_tex = tex(origen).replace(".", ".\\allowbreak{}")
        filas.append(f"\\texttt{{{tex(col)}}} & {tex(rol)} & {tex(aditividad)} & "
                     f"{tex(desc)} & {origen_tex} \\\\")
    return "\n".join([
        f"\\subsubsection*{{\\texttt{{{tex(nombre)}}}}}",
        f"{tex(info['descripcion'])}",
        "",
        "{\\footnotesize",
        "\\begin{longtable}{@{}>{\\raggedright\\arraybackslash}p{0.19\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.1\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.085\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.205\\textwidth}"
        ">{\\raggedright\\arraybackslash}p{0.27\\textwidth}@{}}",
        "\\toprule",
        "Columna & Rol & Aditiv. & Descripción & Origen y regla \\\\",
        "\\midrule",
        "\\endhead",
        *filas,
        "\\bottomrule",
        "\\end{longtable}",
        "}",
        "",
    ])


def main():
    partes = ["% Generado por src/generar_diccionario.py desde src/esquema.py. No editar a mano.",
              ""]
    partes += [tabla_latex(nombre, info) for nombre, info in TABLAS.items()]
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text("\n".join(partes), encoding="utf-8")
    print("Diccionario guardado en", SALIDA)


if __name__ == "__main__":
    main()
