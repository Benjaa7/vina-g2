# Cifras del informe

Generado por `src/metrica.py` (vía `python run.py`). No editar a mano.

Universo de la métrica: exportación, fecha de factura en 2025, tras las reglas de `cobertura.md`. «Dónde» cita archivo:línea de `informe/` (A = seccion_A.tex, C = seccion_C.tex, E = seccion_E.tex, F = seccion_F.tex, Sn = anexo_bitacora.tex). «Texto»: ✔ si el valor del informe coincide al redondeo publicado; ✘ si no; – si la cifra no aparece en el texto.


## Métrica

| Cifra | Valor | Definición | Dónde | Texto |
|---|---:|---|---|---|
| Precio medio S1 | 4,574 USD/L | Σ neto USD / Σ litros; exportación, factura ene–jun 2025 | A:20, E:5, fig. 1 | ✔ |
| Precio medio S2 | 5,085 USD/L | ídem, factura jul–dic 2025 | A:20, E:5, fig. 1 | ✔ |
| Variación S1→S2 | 11,2 % | precio S2 / precio S1 − 1 | A:20 [por confirmar], E:5 | ✔ |
| Precio medio anual | 4,83 USD/L | Σ neto USD / Σ litros, año 2025 | A:37, S1 | ✔ |
| Litros S1 | 5.763.411 L | Σ cajas corregidas × 9,0 | E:5 | ✔ |
| Litros S2 | 5.674.554 L | ídem | E:5, E:9 | ✔ |
| Variación de litros | -1,5 % | litros S2 / S1 − 1 | E:5 | ✔ |
| Ingreso neto S1 | 26,36 M USD | Σ monto neto USD | E:5 | ✔ |
| Ingreso neto S2 | 28,85 M USD | ídem | E:5 | ✔ |
| Variación del ingreso | 9,5 % | ingreso S2 / S1 − 1 | E:5 | ✔ |

## Mezcla y precios

| Cifra | Valor | Definición | Dónde | Texto |
|---|---:|---|---|---|
| Varietal: % de los litros S1 | 42,6 % | litros del tier / litros totales | E:7, fig. 2 | ✔ |
| Varietal: % de los litros S2 | 33,3 % | ídem | E:7, fig. 2 | ✔ |
| Reserva: % de los litros S1 | 34,7 % | litros del tier / litros totales | fig. 2 | ✔ |
| Reserva: % de los litros S2 | 34,2 % | ídem | fig. 2 | ✔ |
| Gran Reserva: % de los litros S1 | 22,7 % | litros del tier / litros totales | A:20, E:7, fig. 2 | ✔ |
| Gran Reserva: % de los litros S2 | 32,5 % | ídem | A:20, E:7, fig. 2 | ✔ |
| Gran Reserva: cambio | 9,8 pp | S2 − S1 | E:7 | ✔ |
| Varietal: cambio | -9,3 pp | S2 − S1 | E:7 | ✔ |
| Precio de lista Varietal S1 | 23,65 USD/caja | precio unitario ponderado por cajas | fig. 3 | ✔ |
| Precio de lista Varietal S2 | 23,61 USD/caja | ídem | fig. 3 | ✔ |
| Variación de lista Varietal | -0,15 % | lista S2 / S1 − 1 | A:20, E:7 (rango «entre −0,15 % y −0,19 %») | ✔ |
| Precio de lista Reserva S1 | 43,67 USD/caja | precio unitario ponderado por cajas | fig. 3 | ✔ |
| Precio de lista Reserva S2 | 43,60 USD/caja | ídem | fig. 3 | ✔ |
| Variación de lista Reserva | -0,16 % | lista S2 / S1 − 1 | A:20, E:7 (rango «entre −0,15 % y −0,19 %») | – |
| Precio de lista Gran Reserva S1 | 77,30 USD/caja | precio unitario ponderado por cajas | fig. 3 | ✔ |
| Precio de lista Gran Reserva S2 | 77,15 USD/caja | ídem | fig. 3 | ✔ |
| Variación de lista Gran Reserva | -0,19 % | lista S2 / S1 − 1 | A:20, E:7 (rango «entre −0,15 % y −0,19 %») | ✔ |
| Descuento medio S1 | 3,82 % | descuento ponderado por cajas | A:20, E:7 | ✔ |
| Descuento medio S2 | 4,40 % | ídem | A:20, E:7 | ✔ |

## Descomposición

| Cifra | Valor | Definición | Dónde | Texto |
|---|---:|---|---|---|
| Efecto precio (principal) | -0,035 USD/L | Σ s1·Δp por tier | fig. 1 | ✔ |
| Efecto mezcla (principal) | 0,551 USD/L | Σ Δs·p1 por tier | E:9, fig. 1 | ✘ (texto: 0,552 USD/L) |
| Efecto cruzado (principal) | -0,005 USD/L | Σ Δs·Δp por tier | fig. 1 | ✔ |
| Mezcla, % del cambio (principal) | 108 % | efecto mezcla / (S2 − S1) | E:5, fig. 1 | ✔ |
| Precio, % del cambio (principal) | -7 % | efecto precio / (S2 − S1) | fig. 1 | ✔ |
| Simétrico de punto medio: mezcla | 0,549 USD/L | precio -0,038 USD/L; mezcla = 107,4 % del cambio | sensibilidad | – |
| Secuencial, mezcla primero: mezcla | 0,551 USD/L | precio -0,041 USD/L; mezcla = 107,9 % del cambio | sensibilidad | – |
| Secuencial, precio primero: mezcla | 0,546 USD/L | precio -0,035 USD/L; mezcla = 106,9 % del cambio | sensibilidad | – |
| Mezcla, % del cambio: mínimo entre métodos | 106,9 % | 4 métodos | sensibilidad | – |
| Mezcla, % del cambio: máximo entre métodos | 107,9 % | 4 métodos | sensibilidad | – |
| Precio dentro de un mismo mercado y tier | -0,006 USD/L | Σ s1·Δp por celda tier × mercado | nuevo (no está en E) | – |
| Mezcla de mercados dentro de cada tier | -0,033 USD/L | mezcla por celda tier × mercado − mezcla por tier | nuevo (no está en E) | – |
| Término cruzado por celda | -0,002 USD/L | Σ Δs·Δp por celda | nuevo (no está en E) | – |

## Caso de negocio

| Cifra | Valor | Definición | Dónde | Texto |
|---|---:|---|---|---|
| Mezcla × litros S2 | 3,13 M USD | efecto mezcla principal × litros S2 | E:9 | ✔ |
| Ídem con el método simétrico | 3,115 M USD | sensibilidad |  | – |
| Tipo de cambio efectivo S2 | 946,34 CLP/USD | Σ neto CLP / Σ neto USD, dólar del día de la factura | E:9 | ✔ |
| Mezcla en pesos | 2.961 M CLP | M USD × TC S2 | E:9 (E:11 lo redondea a 3.000) | ✔ |

## Magnum

| Cifra | Valor | Definición | Dónde | Texto |
|---|---:|---|---|---|
| Magnum: % del volumen | 8,07 % | litros 6x1500 / litros totales | pedido | ✔ |
| Magnum: % del ingreso | 13,76 % | neto USD 6x1500 / total | pedido | ✔ |
| Magnum: precio de lista por caja | 77,26 USD/caja | lista ponderada por cajas | A:35 | ✔ |
| Gran Reserva estándar: precio de lista por caja | 77,20 USD/caja | ídem, GR 12x750 | A:35 | ✔ |
| Magnum: neto por caja | 74,05 USD/caja | Σ neto / Σ cajas | aclaración para A:35 | – |
| Gran Reserva estándar: neto por caja | 74,08 USD/caja | ídem | aclaración para A:35 | – |
| Precio anual si el magnum rinde 18 L | 4,47 USD/L | sensibilidad a) | A:37 [por confirmar], S1 | ✔ |
| Precio anual si el magnum rinde 4,5 L | 5,03 USD/L | sensibilidad a) | A:37 [por confirmar], S1 | ✔ |
| Diferencia con 18 L | -7,5 % | vs 9 L | S1 | ✔ |
| Diferencia con 4,5 L | 4,2 % | vs 9 L | S1 | ✔ |

## Universo y cobertura

| Cifra | Valor | Definición | Dónde | Texto |
|---|---:|---|---|---|
| Filas crudas de ventas | 13.983 | origen_vina.sqlite: ventas | F:3 | ✔ |
| Filas de fact_venta | 13.845 | tras deduplicar; incluye 2026 y nacional | C:21 [por confirmar] | ✔ |
| Universo de la métrica | 10.672 | exportación, factura 2025 | C:21 [por confirmar], F:5 | ✔ |
| Filas de dim_producto | 96 | 24 productos × 4 añadas | C:27 [por confirmar] | ✔ |
| Duplicados | 138 | regla 1 | F:3 | ✔ |
| Facturas de 2026 | 83 | regla 7 | F:3 | ✔ |
| Excluidas por calidad | 221 | duplicados + 2026 | F:3 | ✔ |
| Excluidas por calidad, % | 1,6 % | sobre 13.983 | F:3 | ✔ |
| Nacionales 2025 | 3.090 | fuera por alcance | F:3 | ✔ |
| Montos recalculados (universo) | 555 | regla 5 | F:5 | ✔ |
| Cajas en botellas (universo) | 151 | regla 4 | F:5 | ✔ |
| Moneda imputada (todas las filas crudas) | 698 | regla 3 | F:5 | ✔ |
| Moneda imputada (universo) | 542 | regla 3; F:5 mezcla bases | F:5 | – |
| Costo imputado (universo) | 1.852 | par ausente o N/A | F:5 | ✔ |

## Bitácora

| Cifra | Valor | Definición | Dónde | Texto |
|---|---:|---|---|---|
| S3: distorsión con monto crudo, exportación | 2.095,7 M CLP | Σ (neto registrado − neto final) en CLP, universo | S3 | ✘ (texto: 2.782,0 M CLP) |
| S3: ídem, todos los canales 2025 | 855,2 M CLP | ídem, facturas 2025 de ambos canales | S3 | ✘ (texto: 2.782,0 M CLP) |
| S3: filas que cuadran a ±0,5 % | 94,5 % | 13.845 filas de fact_venta | S3 («95 %») | ✔ |
| S4: moneda vacía | 5,0 % | filas crudas | S4 | ✔ |
| S5: filas con costo imputado | 17,4 % | universo | S5 | ✔ |
| S6: CLP a fecha de embarque vs factura | -0,91 % | Σ neto CLP; fecha de embarque no confiable (regla 8) | S6 | ✘ (texto: -0,69 %) |
| S6: CLP a fecha de cobranza vs factura | -2,14 % | Σ neto CLP; factura + 60 días sur / + 90 norte; dólar 2025 y 2026 | S6 | ✘ (texto: -1,44 %) |
| S7: margen bruto (costo de la merma sin reversar) | 47,25 % | 1 − Σ costo |cajas| / Σ neto CLP, universo | S7 | ✔ |
| S7: margen si se reversara el costo de la merma | 48,05 % | costo con signo | S7 | ✔ |
| S7: brecha | 419 M CLP | costo |cajas| − costo con signo | S7 | ✔ |
| S8: Brasil, Gran Reserva % litros S1 | 22,7 % | mercado de control (hemisferio sur) | S8 | – |
| S8: Brasil, Gran Reserva % litros S2 | 31,5 % | ídem | S8 | – |
| S8: Gran Reserva % litros, mes mínimo | 19,8 % | mes 1 (serie en tablas/mensual.csv) | S8 | – |
| S8: Gran Reserva % litros, mes máximo | 35,9 % | mes 11 | S8 | – |
| S12: fechas dd/mm/aaaa ambiguas (día ≤ 12) | 1.387 | filas crudas | S12 | – |
| S12: ambiguas que calzan con la columna mes como dd/mm | 1.281 |  | S12 | ✔ |
| S12: ambiguas que calzan con la columna mes como mm/dd | 121 |  | S12 («7 casos») | ✘ (texto: 7) |
| S12: filas cuya columna mes no coincide con la fecha | 981 | todos los formatos, también ISO | S12 | – |

## Figura 4

| Cifra | Valor | Definición | Dónde | Texto |
|---|---:|---|---|---|
| Corea del Sur: Gran Reserva % litros (anual) | 25,3 % | S1 21,7 % → S2 29,4 % | fig. 4 | ✘ (texto: 28,1 %) |
| China: Gran Reserva % litros (anual) | 27,0 % | S1 23,4 % → S2 30,9 % | fig. 4 | ✔ |
| Brasil: Gran Reserva % litros (anual) | 26,6 % | S1 22,7 % → S2 31,5 % | fig. 4 | ✘ (texto: 27,8 %) |
| México: Gran Reserva % litros (anual) | 27,2 % | S1 23,1 % → S2 31,7 % | fig. 4 | ✘ (texto: 28,5 %) |
| Estados Unidos: Gran Reserva % litros (anual) | 27,1 % | S1 21,1 % → S2 32,6 % | fig. 4 | ✘ (texto: 26,5 %) |
| Países Bajos: Gran Reserva % litros (anual) | 29,2 % | S1 23,1 % → S2 33,2 % | fig. 4 | ✔ |
| Alemania: Gran Reserva % litros (anual) | 27,9 % | S1 23,3 % → S2 33,2 % | fig. 4 | ✘ (texto: 25,8 %) |
| Canadá: Gran Reserva % litros (anual) | 28,3 % | S1 23,7 % → S2 33,3 % | fig. 4 | ✘ (texto: 27,4 %) |
| Reino Unido: Gran Reserva % litros (anual) | 27,4 % | S1 22,0 % → S2 33,3 % | fig. 4 | ✘ (texto: 25,3 %) |
| Japón: Gran Reserva % litros (anual) | 29,2 % | S1 23,0 % → S2 35,3 % | fig. 4 | ✘ (texto: 26,2 %) |

## Notas

- **S3:** los CLP 2.782 M de la bitácora no se reproducen con ninguna de las dos definiciones de arriba. El autor de S3 debe aclarar qué sumó.
- **Efecto mezcla (E:9, fig. 1):** el valor es 0,5515 USD/L, que redondea a 0,551; los derivados (108 %, USD 3,13 M, CLP ≈ 2.960 M) sí coinciden.
- **S6:** la bitácora usaba el último dólar de 2025 para las fechas posteriores al 30-dic-2025; ahora se usa el dólar observado de 2026 (API /dolar/2026), por eso cambia.
- **Figura 4:** se regenera desde `tablas/fig4_gran_reserva_mercado.csv` y ahora muestra S1 y S2 por mercado. Los valores escritos a mano en la versión anterior no salían de los datos.
- **S6:** la fecha de embarque no es confiable (regla 8); la cifra se informa solo porque la bitácora la cita.
