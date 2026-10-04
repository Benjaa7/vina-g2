# -*- coding: utf-8 -*-
"""Dibuja el modelo estrella desde esquema.py.

Salida: output/figuras/modelo_estrella.pdf (para LaTeX) y .png (para revisar).
Uso:    python src/diagrama_modelo.py   (desde la carpeta entrega1/)
"""
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from esquema import GRANO, TABLAS

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "output" / "figuras"

ACENTO = "#1f3a5f"      # azul oscuro, el único color
GRIS = "#666666"
ALTO_LINEA = 2.6        # en unidades de los ejes
ANCHO_DIM = 29
ANCHO_HECHO = 31

# centro (x, y) de cada tabla en un lienzo de 100 × 90
POSICION = {
    "fact_venta": (50, 44),
    "dim_tiempo": (15.5, 70),
    "dim_producto": (84.5, 66),
    "dim_mercado": (15.5, 17),
    "dim_cliente": (84.5, 21),
}


def lineas_de(tabla):
    """Lista de (texto, estilo) que se escriben dentro de la caja."""
    info = TABLAS[tabla]
    visibles = [c for c in info["columnas"] if c[5]]
    if info["tipo"] != "hecho":
        return [(c[0], "atributo") for c in visibles]
    llaves = [(c[0], "llave") for c in visibles if c[1] in ("llave", "degenerada")]
    medidas = [(c[0], "medida") for c in visibles if c[1] in ("medida", "contexto")]
    n_ind = sum(1 for c in info["columnas"] if c[1] == "indicador")
    return llaves + [("", "separador")] + medidas + [
        (f"+ {n_ind} indicadores de calidad (0/1)", "nota")]


def dibujar_caja(ax, tabla):
    info = TABLAS[tabla]
    cx, cy = POSICION[tabla]
    es_hecho = info["tipo"] == "hecho"
    ancho = ANCHO_HECHO if es_hecho else ANCHO_DIM
    lineas = lineas_de(tabla)
    alto_lineas = sum(0.5 if e == "separador" else 1 for _, e in lineas)
    alto = ALTO_LINEA * (alto_lineas + 2.9)
    x0, y0 = cx - ancho / 2, cy - alto / 2

    ax.add_patch(FancyBboxPatch(
        (x0, y0), ancho, alto, boxstyle="round,pad=0.3,rounding_size=1.0",
        linewidth=1.6 if es_hecho else 0.9, edgecolor=ACENTO,
        facecolor="#eef2f7" if es_hecho else "white", zorder=2))

    y = y0 + alto - ALTO_LINEA * 0.8
    ax.text(cx, y, info["titulo"], ha="center", va="center", fontsize=9,
            fontweight="bold", color=ACENTO, zorder=3)
    y -= ALTO_LINEA * 0.85
    ax.text(cx, y, info.get("subtitulo", ""), ha="center", va="center",
            fontsize=6.6, style="italic", color=GRIS, zorder=3)
    y -= ALTO_LINEA * 0.55
    ax.plot([x0 + 1, x0 + ancho - 1], [y, y], color=ACENTO, linewidth=0.6, zorder=3)
    y -= ALTO_LINEA * 0.45

    for texto, estilo in lineas:
        if estilo == "separador":
            y -= ALTO_LINEA * 0.25
            ax.plot([x0 + 2, x0 + ancho - 2], [y, y], color=GRIS,
                    linewidth=0.4, linestyle=(0, (2, 2)), zorder=3)
            y -= ALTO_LINEA * 0.25
            continue
        y -= ALTO_LINEA * 0.5
        if estilo == "nota":
            ax.text(x0 + 2, y, texto, ha="left", va="center", fontsize=6.4,
                    style="italic", color=GRIS, zorder=3)
        else:
            etiqueta = "  (llave)" if estilo == "llave" and texto.endswith("_key") else ""
            ax.text(x0 + 2, y, texto, ha="left", va="center", fontsize=7,
                    family="monospace",
                    color=GRIS if estilo == "llave" else "black", zorder=3)
            if etiqueta:
                ax.text(x0 + ancho - 2, y, "FK", ha="right", va="center",
                        fontsize=6, color=GRIS, zorder=3)
        y -= ALTO_LINEA * 0.5


def dibujar(con_grano):
    fig, ax = plt.subplots(figsize=(7.4, 6.4 if con_grano else 6.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(-6 if con_grano else 2, 88)
    ax.axis("off")

    # una línea del hecho a cada dimensión: todas a un solo salto
    fx, fy = POSICION["fact_venta"]
    for t, (dx, dy) in POSICION.items():
        if t != "fact_venta":
            ax.plot([fx, dx], [fy, dy], color=GRIS, linewidth=0.9,
                    linestyle=(0, (3, 2)), zorder=1)

    for t in POSICION:
        dibujar_caja(ax, t)

    if con_grano:
        grano = textwrap.fill("Grano: " + GRANO.replace("Una fila es ", "una fila es "), 95)
        ax.text(50, -1, grano, ha="center", va="center", fontsize=7.6,
                style="italic", color=ACENTO)
    return fig


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    # informe: sin el grano (el texto de la sección C lo declara)
    fig = dibujar(con_grano=False)
    for ext in ("pdf", "png"):
        fig.savefig(SALIDA / f"modelo_estrella.{ext}", bbox_inches="tight",
                    dpi=300 if ext == "png" else None)
    plt.close(fig)
    # presentación: la lámina técnica lleva el grano escrito
    fig = dibujar(con_grano=True)
    fig.savefig(SALIDA / "modelo_estrella_lamina.png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("Diagramas guardados en", SALIDA)


if __name__ == "__main__":
    main()
