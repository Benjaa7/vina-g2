"""
Generación de figuras para el Componente E (Evidencia y Caso de Negocio)
IIC3752 - Tecnologías para Inteligencia de Negocios
Caso: Viña Vallehondo (Grupo 2)
"""

import os
import matplotlib.pyplot as plt
import numpy as np

# Asegurar directorio de salida
output_dir = os.path.join(os.path.dirname(__file__), "..", "output", "figuras")
os.makedirs(output_dir, exist_ok=True)

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

# -------------------------------------------------------------------------
# FIGURA 1: Gráfico de cascada / puente (Descomposición del precio medio)
# -------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 4.2), dpi=300)

etiquetas = ["H1 2025\n(Inicial)", "Efecto\nPrecio", "Efecto\nMezcla", "Efecto\nCruzado", "H2 2025\n(Final)"]
valores = [4.574, -0.035, 0.552, -0.005, 5.085]
bottoms = [0, 4.574 - 0.035, 4.574 - 0.035, 4.574 - 0.035 + 0.552 - 0.005, 0]
alturas = [4.574, -0.035, 0.552, -0.005, 5.085]
colores = ["#2b5c8f", "#d9534f", "#2ca02c", "#d9534f", "#2b5c8f"]

bars = ax.bar(etiquetas, alturas, bottom=bottoms, color=colores, width=0.55, edgecolor="none")

# Etiquetas de valores
ax.text(0, 4.574 + 0.08, "4,574", ha="center", va="bottom", fontweight="bold")
ax.text(1, 4.574 - 0.035 - 0.18, "-0,035\n(-7%)", ha="center", va="top", color="#d9534f", fontsize=9)
ax.text(2, 4.574 - 0.035 + 0.552 + 0.08, "+0,552\n(+108%)", ha="center", va="bottom", color="#2ca02c", fontweight="bold")
ax.text(3, 5.09 - 0.18, "-0,005", ha="center", va="top", color="#d9534f", fontsize=9)
ax.text(4, 5.085 + 0.08, "5,085", ha="center", va="bottom", fontweight="bold")

ax.set_title("Descomposición del alza del precio medio de exportación (USD por litro)", pad=15, fontweight="bold")
ax.set_ylabel("USD / Litro")
ax.set_ylim(0, 6.0)
ax.grid(axis="y")
ax.text(0.5, -0.18, "Fuente: Elaboración propia a partir de transacciones consolidadas de exportación 2025.", 
        transform=ax.transAxes, ha="center", fontsize=8, color="#555555")

plt.tight_layout()
fig1_path = os.path.join(output_dir, "figura1_cascada_precio.png")
fig.savefig(fig1_path)
fig.savefig(os.path.join(output_dir, "figura1_cascada_precio.pdf"))
plt.close(fig)

# -------------------------------------------------------------------------
# FIGURA 2: Participación de volumen por tier (Barras 100% apiladas)
# -------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.5, 4.2), dpi=300)

semestres = ["Primer Semestre 2025", "Segundo Semestre 2025"]
varietal = np.array([42.6, 33.3])
reserva = np.array([34.7, 34.2])
gran_reserva = np.array([22.7, 32.5])

p1 = ax.bar(semestres, varietal, label="Varietal", color="#b0c4de", width=0.45)
p2 = ax.bar(semestres, reserva, bottom=varietal, label="Reserva", color="#4682b4", width=0.45)
p3 = ax.bar(semestres, gran_reserva, bottom=varietal + reserva, label="Gran Reserva", color="#1b365d", width=0.45)

# Textos dentro de las barras
ax.text(0, 42.6 / 2, "42,6%", ha="center", va="center", color="#222222", fontweight="bold")
ax.text(0, 42.6 + 34.7 / 2, "34,7%", ha="center", va="center", color="white", fontweight="bold")
ax.text(0, 42.6 + 34.7 + 22.7 / 2, "22,7%", ha="center", va="center", color="white", fontweight="bold")

ax.text(1, 33.3 / 2, "33,3%\n(-9,3 pp)", ha="center", va="center", color="#222222", fontweight="bold")
ax.text(1, 33.3 + 34.2 / 2, "34,2%", ha="center", va="center", color="white", fontweight="bold")
ax.text(1, 33.3 + 34.2 + 32.5 / 2, "32,5%\n(+9,8 pp)", ha="center", va="center", color="white", fontweight="bold")

ax.set_title("Participación de cada tier en los litros exportados (%)", pad=15, fontweight="bold")
ax.set_ylabel("Porcentaje del volumen físico (%)")
ax.set_ylim(0, 105)
ax.legend(loc="upper right", frameon=True)
ax.grid(axis="y")
ax.text(0.5, -0.18, "Fuente: Elaboración propia a partir de registros de venta de exportación 2025.", 
        transform=ax.transAxes, ha="center", fontsize=8, color="#555555")

plt.tight_layout()
fig2_path = os.path.join(output_dir, "figura2_mix_semestral.png")
fig.savefig(fig2_path)
fig.savefig(os.path.join(output_dir, "figura2_mix_semestral.pdf"))
plt.close(fig)

# -------------------------------------------------------------------------
# FIGURA 3: Estabilidad de precios de lista (Eje desde cero)
# -------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.5, 4.2), dpi=300)

tiers = ["Varietal", "Reserva", "Gran Reserva"]
h1_precios = [23.65, 43.67, 77.30]
h2_precios = [23.61, 43.60, 77.15]

x = np.arange(len(tiers))
width = 0.3

rects1 = ax.bar(x - width/2, h1_precios, width, label="Primer Semestre", color="#8da0cb")
rects2 = ax.bar(x + width/2, h2_precios, width, label="Segundo Semestre", color="#fc8d62")

# Etiquetas de datos
for r in rects1:
    ax.text(r.get_x() + r.get_width()/2, r.get_height() + 1.2, f"${r.get_height():.2f}", ha="center", va="bottom", fontsize=8.5)
for r in rects2:
    ax.text(r.get_x() + r.get_width()/2, r.get_height() + 1.2, f"${r.get_height():.2f}", ha="center", va="bottom", fontsize=8.5)

ax.set_title("Precios de lista contractuales por tier y semestre (USD por caja)", pad=15, fontweight="bold")
ax.set_ylabel("USD / Caja (9 litros)")
ax.set_xticks(x)
ax.set_xticklabels(tiers, fontweight="bold")
ax.set_ylim(0, 95)  # Eje parte estrictamente en cero
ax.legend(loc="upper left")
ax.grid(axis="y")
ax.text(0.5, -0.18, "Fuente: Elaboración propia a partir de catálogo de precios contractuales 2025.", 
        transform=ax.transAxes, ha="center", fontsize=8, color="#555555")

plt.tight_layout()
fig3_path = os.path.join(output_dir, "figura3_precios_lista.png")
fig.savefig(fig3_path)
fig.savefig(os.path.join(output_dir, "figura3_precios_lista.pdf"))
plt.close(fig)

# -------------------------------------------------------------------------
# FIGURA 4: Participación de Gran Reserva por Mercado
# -------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 4.2), dpi=300)

mercados = ["Reino Unido", "Alemania", "Japón", "EE.UU.", "China", "Canadá", "Brasil", "Países Bajos", "Corea del Sur", "México"]
porcentajes = [25.3, 25.8, 26.2, 26.5, 27.0, 27.4, 27.8, 29.2, 28.1, 28.5]

# Ordenar de menor a mayor
indices_ordenados = np.argsort(porcentajes)
mercados_ord = [mercados[i] for i in indices_ordenados]
porcentajes_ord = [porcentajes[i] for i in indices_ordenados]

colores_mercados = ["#2b5c8f" if m != "Países Bajos" else "#e66101" for m in mercados_ord]

ax.barh(mercados_ord, porcentajes_ord, color=colores_mercados, height=0.6)

for i, v in enumerate(porcentajes_ord):
    ax.text(v + 0.3, i, f"{v:.1f}%", va="center", fontsize=8.5)

ax.set_title("Participación de Gran Reserva sobre litros totales por mercado (%)", pad=15, fontweight="bold")
ax.set_xlabel("Porcentaje de litros (%)")
ax.set_xlim(0, 35)
ax.grid(axis="x")
ax.text(0.5, -0.18, "Fuente: Elaboración propia a partir de ventas por mercado de exportación 2025.", 
        transform=ax.transAxes, ha="center", fontsize=8, color="#555555")

plt.tight_layout()
fig4_path = os.path.join(output_dir, "figura4_gran_reserva_mercados.png")
fig.savefig(fig4_path)
fig.savefig(os.path.join(output_dir, "figura4_gran_reserva_mercados.pdf"))
plt.close(fig)

print("Figuras generadas exitosamente en output/figuras/")