"""
Generación de figuras para el Componente E (Evidencia y Caso de Negocio)
IIC3752 - Tecnologías para Inteligencia de Negocios
Caso: Viña Vallehondo (Grupo 2)

Lee las tablas que produce src/metrica.py en output/tablas/ (no hay cifras escritas
a mano) y escribe output/figuras/figura1..4 en PDF y PNG.
Uso: python run.py (corre toda la cadena), o python src/graficos.py si las tablas ya existen.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TABLAS = RAIZ / "output" / "tablas"
SALIDA = RAIZ / "output" / "figuras"
FUENTE = ("Fuente: elaboración propia a partir de origen_vina.sqlite, origen_costos_productos.csv "
          "y origen_embarques.json.\nExportación, facturas de 2025.")

# Estilo sobrio y formal
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "figure.titlesize": 12,
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "grid.color": "#eeeeee",
    "grid.linestyle": "--"
})


def num(x, dec):
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def con_signo(x, dec):
    return ("+" if x > 0 else "") + num(x, dec)


def leer(nombre):
    ruta = TABLAS / f"{nombre}.csv"
    if not ruta.exists():
        raise SystemExit(f"Falta {ruta.relative_to(RAIZ)}. Corre primero: python run.py")
    return pd.read_csv(ruta)


def guardar(fig, nombre):
    fig.text(0.5, 0.01, FUENTE, ha="center", va="bottom", fontsize=7.5, color="#555555")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(SALIDA / f"{nombre}.{ext}")
    plt.close(fig)


def figura1():
    """Cascada: precio S1 → efectos precio, mezcla y cruzado → precio S2."""
    t = leer("fig1_descomposicion").set_index("concepto")
    s1, s2 = t.loc["Precio S1", "usd_por_litro"], t.loc["Precio S2", "usd_por_litro"]
    efectos = ["Efecto precio", "Efecto mezcla", "Efecto cruzado"]
    fig, ax = plt.subplots(figsize=(7, 4.4), dpi=300)
    etiquetas = ["S1 2025\n(inicial)", "Efecto\nprecio", "Efecto\nmezcla", "Efecto\ncruzado", "S2 2025\n(final)"]
    acumulado, bottoms, alturas = s1, [0], [s1]
    for e in efectos:
        v = t.loc[e, "usd_por_litro"]
        bottoms.append(acumulado if v >= 0 else acumulado + v)
        alturas.append(abs(v))
        acumulado += v
    bottoms.append(0)
    alturas.append(s2)
    colores = ["#2b5c8f"] + ["#2ca02c" if t.loc[e, "usd_por_litro"] >= 0 else "#d9534f" for e in efectos] + ["#2b5c8f"]
    ax.bar(etiquetas, alturas, bottom=bottoms, color=colores, width=0.55, edgecolor="none")
    ax.text(0, s1 + 0.08, num(s1, 3), ha="center", va="bottom", fontweight="bold")
    ax.text(4, s2 + 0.08, num(s2, 3), ha="center", va="bottom", fontweight="bold")
    for i, e in enumerate(efectos, start=1):
        v, p = t.loc[e, "usd_por_litro"], t.loc[e, "pct_del_cambio"]
        tope = bottoms[i] + alturas[i]
        ax.text(i, tope + 0.08, f"{con_signo(v, 3)}\n({con_signo(p, 0)} %)", ha="center", va="bottom",
                color="#2ca02c" if v >= 0 else "#d9534f", fontsize=9,
                fontweight="bold" if e == "Efecto mezcla" else "normal")
    ax.set_title("Descomposición del alza del precio medio de exportación (USD por litro)", pad=15, fontweight="bold")
    ax.set_ylabel("USD / litro")
    ax.set_ylim(0, 6.0)
    ax.grid(axis="y")
    guardar(fig, "figura1_cascada_precio")


def figura2():
    """Participación de cada tier en los litros exportados, por semestre."""
    t = leer("fig2_mezcla_tier").set_index("tier")
    fig, ax = plt.subplots(figsize=(6.5, 4.4), dpi=300)
    semestres = ["Primer semestre 2025", "Segundo semestre 2025"]
    colores = {"Varietal": ("#b0c4de", "#222222"), "Reserva": ("#4682b4", "white"),
               "Gran Reserva": ("#1b365d", "white")}
    base = np.zeros(2)
    for tier, (color, texto) in colores.items():
        vals = np.array([t.loc[tier, "participacion_litros_s1_pct"], t.loc[tier, "participacion_litros_s2_pct"]])
        ax.bar(semestres, vals, bottom=base, label=tier, color=color, width=0.45)
        cambio = t.loc[tier, "cambio_pp"]
        for i, v in enumerate(vals):
            etiqueta = f"{num(v, 1)} %"
            if i == 1 and abs(cambio) >= 1:
                etiqueta += f"\n({con_signo(cambio, 1)} pp)"
            ax.text(i, base[i] + v / 2, etiqueta, ha="center", va="center", color=texto, fontweight="bold")
        base += vals
    ax.set_title("Participación de cada tier en los litros exportados (%)", pad=15, fontweight="bold")
    ax.set_ylabel("Porcentaje del volumen físico (%)")
    ax.set_ylim(0, 105)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=False)
    ax.grid(axis="y")
    guardar(fig, "figura2_mix_semestral")


def figura3():
    """Precio de lista por tier y semestre (ponderado por cajas), eje desde cero."""
    t = leer("fig3_precio_lista_tier")
    fig, ax = plt.subplots(figsize=(6.5, 4.4), dpi=300)
    x = np.arange(len(t))
    ancho = 0.3
    r1 = ax.bar(x - ancho / 2, t["precio_lista_s1_usd_caja"], ancho, label="Primer semestre", color="#8da0cb")
    r2 = ax.bar(x + ancho / 2, t["precio_lista_s2_usd_caja"], ancho, label="Segundo semestre", color="#fc8d62")
    for rects in (r1, r2):
        for r in rects:
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 1.2, f"${num(r.get_height(), 2)}",
                    ha="center", va="bottom", fontsize=8.5)
    for i, (v, alto) in enumerate(zip(t["variacion_pct"], t["precio_lista_s1_usd_caja"])):
        ax.text(i, alto + 7, f"variación {con_signo(v, 2)} %", ha="center", va="bottom", fontsize=8,
                color="#333333", style="italic")
    ax.set_title("Precios de lista por tier y semestre (USD por caja)", pad=15, fontweight="bold")
    ax.set_ylabel("USD / caja (9 litros)")
    ax.set_xticks(x)
    ax.set_xticklabels(t["tier"], fontweight="bold")
    ax.set_ylim(0, 95)  # eje parte estrictamente en cero
    ax.legend(loc="upper left")
    ax.grid(axis="y")
    guardar(fig, "figura3_precios_lista")


def figura4():
    """Participación de Gran Reserva en los litros de cada mercado, S1 y S2."""
    t = leer("fig4_gran_reserva_mercado").sort_values("gran_reserva_pct_litros_s2")
    fig, ax = plt.subplots(figsize=(7, 4.8), dpi=300)
    y = np.arange(len(t))
    alto = 0.38
    ax.barh(y + alto / 2, t["gran_reserva_pct_litros_s1"], alto, label="Primer semestre", color="#8da0cb")
    ax.barh(y - alto / 2, t["gran_reserva_pct_litros_s2"], alto, label="Segundo semestre", color="#1b365d")
    for i, (a, b) in enumerate(zip(t["gran_reserva_pct_litros_s1"], t["gran_reserva_pct_litros_s2"])):
        ax.text(a + 0.3, i + alto / 2, f"{num(a, 1)} %", va="center", fontsize=7.5)
        ax.text(b + 0.3, i - alto / 2, f"{num(b, 1)} %", va="center", fontsize=7.5)
    ax.set_yticks(y)
    ax.set_yticklabels(t["pais"])
    ax.set_title("Gran Reserva en los litros exportados, por mercado (%)", pad=15, fontweight="bold")
    ax.set_xlabel("Porcentaje de los litros del mercado (%)")
    ax.set_xlim(0, 40)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, frameon=False)
    ax.grid(axis="x")
    guardar(fig, "figura4_gran_reserva_mercados")


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    for f in (figura1, figura2, figura3, figura4):
        f()
    print("Figuras generadas en output/figuras/")


if __name__ == "__main__":
    main()
