# Discrepancias entre el informe y la cadena de datos

Para: autores de las secciones A, C, E y F y de la bitácora.
Fuente de cada valor: `output/cifras.md`, generado por `python run.py` (componente B). Las líneas citadas corresponden a los `.tex` del commit 1048bf2. **Nada de esto se modificó en `informe/`**: cada autor decide cómo corregir su parte.

## Resumen

La conclusión se mantiene: el alza de 4,574 a 5,085 USD/L (+11,2 %) es de mezcla, no de precio. Todas las cifras de titular coinciden con los datos. Quedan tres correcciones de fondo (figura 4, S6 y S12), una cifra sin respaldo (S3) y varios ajustes de redacción.

## 1. Hay que corregir

| Dónde | Dice | Los datos dan | Qué hacer |
|---|---|---|---|
| Figura 4 (caption en `seccion_E.tex:41`) | Valores escritos a mano (p. ej. Japón 26,2 %, Corea 28,1 %, Reino Unido 25,3 %) | Gran Reserva anual por mercado: Corea 25,3 %, Brasil 26,6 %, China 27,0 %, EE.UU. 27,1 %, México 27,2 %, Reino Unido 27,4 %, Alemania 27,9 %, Canadá 28,3 %, Japón 29,2 %, Países Bajos 29,2 % | La figura ya se regeneró desde los datos y ahora muestra S1 y S2 por mercado. El caption sigue siendo válido. Si algún texto cita porcentajes por mercado o destaca a Países Bajos, hay que revisarlo: **los 10 mercados suben entre 7,5 y 12,3 pp** (Japón, el que más; China, el que menos) |
| `anexo_bitacora.tex:20` (S6) | −0,69 % a fecha de embarque; −1,44 % a fecha de cobranza | **−0,91 %** y **−2,14 %** | Antes, las fechas posteriores al 30-dic-2025 usaban el último dólar de 2025. Ahora la cadena usa el dólar observado de 2026 (API `/dolar/2026`). Además, la fecha de embarque no es confiable: el 30 % de las líneas de embarque tiene fecha anterior a la factura |
| `anexo_bitacora.tex:32` (S12) | «1.281 registros consistentes […] frente a solo 7 casos anómalos» | 1.281 ✔, pero **121** (no 7) calzan con la columna `mes` leídas como mm/dd | Además, la columna `mes` no coincide con la fecha en **981 filas**, también en fechas ISO sin ambigüedad. Esa columna es ruidosa y no sirve como evidencia. Sugerencia: «se leen como dd/mm; la columna mes no sirve para validarlo (discrepa en 981 filas)» |
| `anexo_bitacora.tex:14` (S3) | Distorsión de CLP 2.782 millones si se usara el monto crudo | No se reproduce: **CLP 2.095,7 M** en el universo de exportación y **CLP 855,2 M** en todos los canales de 2025 (Σ neto registrado − neto final) | **El autor de S3 debe aclarar qué sumó.** De paso, el «95 % cuadra exacto» es en realidad 94,5 % a ±0,5 % (y 76 % a ±0,01 %) |

## 2. Ajustes menores

| Dónde | Observación |
|---|---|
| `seccion_E.tex:9` y figura 1 | El efecto mezcla es 0,551478 USD/L: **redondea a 0,551, no a 0,552**. La figura regenerada muestra +0,551. Los derivados no cambian: 108 %, USD 3,13 M y CLP 2.961 M (el texto dice 2.960, que vale como redondeo). Por qué el texto dice 0,552: ver «Redondeo del efecto mezcla» más abajo |
| `seccion_E.tex:5` | «108 % a cambio de mezcla» ✔ con el método de E. Con los otros tres métodos de descomposición la mezcla explica entre **106,9 % y 107,9 %**. Sugerencia: «entre 107 % y 108 % según el método» |
| `seccion_A.tex:20` y `seccion_E.tex:7` | «Precios de lista bajaron entre 0,15 % y 0,19 %» ✔ (−0,15 / −0,16 / −0,19 %). «Descuento medio de 3,82 % a 4,40 %» ✔. Falta decir que ambos son **promedios ponderados por cajas**: el promedio simple da otros valores (descuento 3,78 → 4,39 %) |
| `seccion_A.tex:35` | USD 77,26 y 77,20 por caja ✔, pero son **precios de lista** ponderados. En precio neto la coincidencia se mantiene (USD 74,05 vs 74,08), así que el argumento se refuerza si se dice |
| `seccion_F.tex:5` | Mezcla bases distintas: 555, 151 y 1.852 se cuentan sobre el universo de exportación (10.672 filas), pero 698 se cuenta sobre todas las filas crudas. Dentro del universo, las monedas imputadas son **542** |

### Redondeo del efecto mezcla

El efecto mezcla se calcula como Σ (participación del 2.º semestre − participación del 1.er semestre) × precio por litro del 1.er semestre, sumando sobre los tres tiers. Con los valores completos que usa la cadena (`output/tablas/fig2_mezcla_tier.csv`) da **0,551478 USD/L**, que se publica como **0,551**.

Ese valor está a solo 0,00002 del límite de redondeo (0,5515), así que redondear cualquier valor intermedio antes de multiplicar lo mueve de cifra:

| Valores usados en el cálculo | Efecto mezcla | Publicado |
|---|---:|---:|
| Proporciones y precios completos (lo que usa la cadena) | 0,5515 | **0,551** |
| Proporciones redondeadas a 3 decimales (42,6 %, 34,7 %, 22,7 %…) | 0,5527 | 0,553 |
| Precios redondeados a 2 decimales (2,53 / 4,66 / 8,28 USD/L) | 0,5516 | 0,552 |

El 0,552 de la sección E (línea 9) y de la figura 1 anterior es compatible con haber redondeado algún valor intermedio, por ejemplo los precios por tier a 2 decimales. Como no tenemos el cálculo original, no podemos saber cuál se usó.

**Qué hacer:** escribir 0,551, que es el valor exacto con los datos completos. Las cifras que dependen de él no cambian al redondearlas: 108 % del alza, USD 3,13 millones y CLP ≈ 2.960 millones. Para cualquier cálculo derivado, conviene partir de los valores completos de `fig2_mezcla_tier.csv`, no de las cifras redondeadas que aparecen en el informe.

## 3. Se pueden quitar los «[por confirmar]»

Estas cifras coinciden con los datos:
- `seccion_A.tex:20`: 11,2 %.
- `seccion_A.tex:37`: 4,47 y 5,03 USD/L.
- `seccion_C.tex:21`: 13.845 y 10.672 filas. Las 13.845 incluyen las 83 facturas de 2026 y las ventas nacionales; la métrica filtra exportación y 2025.
- `seccion_C.tex:27`: 96 filas. Son 81 del maestro de costos más 15 pares de la añada 2021 creados con costo imputado por (tier, añada).

Para quitar la marca, cambiar `\providecommand{\porconfirmar}` por `\renewcommand{\porconfirmar}[1]{#1}`, como indica el comentario en `seccion_C.tex:3`.

## 4. Hallazgos nuevos que E podría usar

- **El efecto precio (−0,035 USD/L) casi no es precio.** Separado por celda tier × mercado, se compone de:
  - −0,006 USD/L de precio dentro de un mismo mercado y tier;
  - −0,033 USD/L de mezcla de mercados dentro de cada tier;
  - −0,002 USD/L de término cruzado.

  Las listas prácticamente no se movieron. Detalle en `output/tablas/descomposicion_precio_mercado.csv`.
- **S8 (`anexo_bitacora.tex:24`) tiene cifras para respaldarse.**
  - Brasil, el mercado de control del hemisferio sur, pasa de 22,7 % a 31,5 % de Gran Reserva, igual que los mercados del norte.
  - La participación mensual de Gran Reserva sube de 19,8 % en enero a 35,9 % en noviembre.

  Serie en `output/tablas/mensual.csv`.
- Las sensibilidades a) a e) están en `output/tablas/sensibilidades.csv`. En todas, la mezcla explica más del 100 % del alza en USD:
  - a) magnum de 18 L o de 4,5 L: 108 %;
  - b) sin merma: 108 %;
  - d) a precio de lista: 102 %.
