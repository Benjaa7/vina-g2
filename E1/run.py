# -*- coding: utf-8 -*-
"""Cadena de datos completa del componente B (Entrega 1, Grupo 2, Viña Vallehondo).

Uso (desde cualquier carpeta):  python run.py

    1. extraer   lee el SQLite, el CSV de costos, el JSON de embarques y la API del dólar
                 (2025 y 2026; si la API no responde en 60 s usa datos/raw/dolar_<año>.json)
    2. limpiar   aplica las reglas de calidad              → output/cobertura.md
    3. integrar  construye la estrella y la tabla integrada → output/estrella/, output/tabla_integrada.csv
    4. metrica   calcula la métrica y las sensibilidades    → output/tablas/, output/cifras.md
    5. graficos  dibuja las figuras de la sección E         → output/figuras/figura1..4

Al final verifica las cifras que el informe da por establecidas y sale con código 1 si
alguna no calza.
"""
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

import extraer   # noqa: E402
import graficos  # noqa: E402
import integrar  # noqa: E402
import limpiar   # noqa: E402
import metrica   # noqa: E402

# cifra esperada: (clave en los resultados, valor, decimales con que se compara)
ESPERADAS = [
    ("Universo de la métrica (filas)", "universo", 10672, 0),
    ("Gran Reserva S1 (% de los litros)", "gr_s1", 22.7, 1),
    ("Gran Reserva S2 (% de los litros)", "gr_s2", 32.5, 1),
    ("Precio S1 (USD/L)", "precio_s1", 4.574, 3),
    ("Precio S2 (USD/L)", "precio_s2", 5.085, 3),
    ("Precio anual (USD/L)", "precio_anual", 4.83, 2),
    ("Magnum, % del volumen", "magnum_vol_pct", 8.07, 2),
    ("Magnum, % de los ingresos", "magnum_ing_pct", 13.76, 2),
]


def paso(nombre, inicio):
    print(f"  listo en {time.perf_counter() - inicio:.1f} s")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.perf_counter()
    salida = RAIZ / "output"
    salida.mkdir(exist_ok=True)

    print("1/5 Extracción de las cuatro fuentes")
    t = time.perf_counter()
    fuentes = extraer.extraer()
    print(f"  ventas: {len(fuentes['erp']['ventas'])} filas | costos: {len(fuentes['costos'])} | "
          f"embarques: {len(fuentes['embarques'])} | dólar: {len(fuentes['dolar'])} días")
    paso("extraer", t)

    print("2/5 Limpieza")
    t = time.perf_counter()
    res = limpiar.limpiar(fuentes)
    limpiar.escribir_cobertura(res, salida / "cobertura.md")
    print(f"  {res['n_crudo']} filas crudas → {len(res['ventas'])} tras deduplicar → output/cobertura.md")
    paso("limpiar", t)

    print("3/5 Integración (modelo estrella)")
    t = time.perf_counter()
    estrella, integrada = integrar.integrar(res, fuentes["erp"], RAIZ)
    print("  " + " | ".join(f"{k}: {len(v)}" for k, v in estrella.items()))
    print("  → output/estrella/*.csv, output/tabla_integrada.csv")
    paso("integrar", t)

    print("4/5 Métrica, descomposición y sensibilidades")
    t = time.perf_counter()
    r, tablas = metrica.calcular(integrada, res)
    metrica.guardar_tablas(tablas, salida / "tablas")
    metrica.escribir_cifras(r, salida / "cifras.md")
    print("  → output/tablas/*.csv, output/cifras.md")
    paso("metrica", t)

    print("5/5 Figuras")
    t = time.perf_counter()
    graficos.main()
    paso("graficos", t)

    n = metrica.num
    print("\nRESUMEN")
    print(f"  Precio medio de exportación: {n(r['precio_s1'], 3)} → {n(r['precio_s2'], 3)} USD/L "
          f"({n(r['var_pct'], 1)} %); anual {n(r['precio_anual'], 2)} USD/L")
    print(f"  Gran Reserva: {n(r['gr_s1'], 1)} % → {n(r['gr_s2'], 1)} % de los litros")
    print(f"  Descomposición (base S1, sección E): mezcla {n(r['ef_mezcla'], 3)} USD/L "
          f"({n(r['mezcla_pct'], 1)} %), precio {n(r['ef_precio'], 3)} ({n(r['precio_pct'], 1)} %), "
          f"cruzado {n(r['ef_cruzado'], 3)}")
    print(f"  Mezcla según el método: entre {n(r['mezcla_pct_min'], 1)} % y {n(r['mezcla_pct_max'], 1)} % del alza")
    print(f"  Precio dentro de mercado y tier: {n(r['precio_puro'], 3)} USD/L; "
          f"mezcla de mercados: {n(r['mezcla_mercados'], 3)} USD/L")
    print(f"  Magnum: {n(r['magnum_vol_pct'], 2)} % del volumen y {n(r['magnum_ing_pct'], 2)} % de los ingresos; "
          f"anual con 18 L {n(r['magnum_18.0'], 2)} y con 4,5 L {n(r['magnum_4.5'], 2)} USD/L")

    print("\nVERIFICACIÓN")
    fallas = 0
    for nombre, clave, esperado, dec in ESPERADAS:
        ok = round(r[clave], dec) == round(esperado, dec)
        fallas += not ok
        print(f"  [{'OK' if ok else 'NO CALZA'}] {nombre}: {n(r[clave], dec)} (esperado {n(esperado, dec)})")
    print("\nFUENTE DEL DÓLAR")
    for origen in fuentes["origen_dolar"].values():
        print(f"  {origen}")
    print(f"\nTiempo total: {time.perf_counter() - t0:.1f} s")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
