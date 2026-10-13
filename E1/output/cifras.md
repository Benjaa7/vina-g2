# Cifras del informe

Este archivo lista cada cifra del informe del Grupo 2 (caso Viña Vallehondo, pregunta 2: el precio promedio por litro de exportación subió en 2025, ¿por alza de precios o por mayor proporción de Gran Reserva?), explica cómo se calcula y dice si el valor escrito en el informe coincide con los datos. Las cifras salen de las cuatro fuentes del caso (ERP de ventas, maestro de costos, embarques y dólar observado) después de la limpieza descrita en `cobertura.md`. Lo genera `src/metrica.py` al correr `python run.py`; no se edita a mano.

## Resumen

- El precio medio de exportación subió de 4,574 USD por litro en el 1.er semestre de 2025 (S1, enero a junio) a 5,085 en el 2.º semestre (S2, julio a diciembre), un alza de 11,2 %, mientras los litros exportados bajaron 1,5 %.
- El alza se explica por la mezcla, no por los precios: Gran Reserva pasó de 22,7 % a 32,5 % de los litros. El efecto mezcla aporta 0,551 USD/L (108 % del alza) y el efecto precio -0,035 USD/L. Con cualquiera de los cuatro métodos de descomposición, la mezcla explica entre 106,9 % y 107,9 % del alza.
- Los precios de lista bajaron levemente (entre -0,15 % y -0,19 % según el tier) y el descuento medio subió de 3,82 % a 4,40 %. Comparando el mismo tier en el mismo mercado, el precio por litro cambió apenas -0,006 USD/L.
- La conclusión no depende de cuántos litros rinda el magnum: con 18 o 4,5 litros por caja el precio anual sería 4,47 o 5,03 USD/L en vez de 4,83, y la mezcla sigue explicando más del 100 % del alza (tabla `tablas/sensibilidades.csv`).
- De las 148 cifras del informe que se pudieron contrastar con los datos, 134 coinciden. No coinciden: Efecto mezcla (método principal); Supuesto S3: diferencia si se usara el monto registrado, exportación; Supuesto S3: ídem, todos los canales de 2025; Supuesto S6: ingreso en pesos a fecha de embarque vs. a fecha de factura; Supuesto S6: ingreso en pesos a fecha de cobranza vs. a fecha de factura; Supuesto S12: ambiguas que coinciden con la columna mes leídas como mes/día; y 8 de los 10 valores de la figura 4. El detalle de qué corregir está en `discrepancias.md`.

## Cómo leer las tablas

- **Cifra**: qué se mide.
- **Valor**: el resultado que entrega la cadena con los datos actuales.
- **Cómo se calcula**: la definición en una línea.
- **Dónde aparece en el informe**: archivo y línea del `.tex` en `informe/` (sección A = `seccion_A.tex`, etc.; «Bitácora» = `anexo_bitacora.tex`). «Marcada por confirmar» indica que el informe la tiene pendiente de verificación. La sección D todavía no está en el repositorio, así que se cita sin número de línea.
- **¿Coincide?**: ✔ el valor del informe coincide con el de los datos al redondeo con que está escrito; ✘ no coincide (entre paréntesis, lo que dice el informe); – la cifra no aparece en el informe (es de apoyo, una sensibilidad o un hallazgo nuevo).

Términos: **1.er semestre** = facturas de enero a junio de 2025; **2.º semestre** = julio a diciembre. **Universo** = ventas de exportación facturadas en 2025 (10.672). **Tier** = Varietal, Reserva o Gran Reserva. **Magnum** = formato 6x1500 (6 botellas de 1,5 L). **pp** = puntos porcentuales. **Supuesto Sn** = fila n de la bitácora de supuestos del anexo (no confundir con los semestres). **Ingreso neto** = después de descuento. **Sensibilidad** = la misma cifra calculada con otra definición, para ver si la conclusión cambia.


## 1. Precio medio por litro de exportación (métrica principal)

| Cifra | Valor | Cómo se calcula | Dónde aparece en el informe | ¿Coincide? |
|---|---:|---|---|---|
| Precio medio, 1.er semestre (ene-jun) | 4,574 USD/L | Ingreso neto en dólares ÷ litros; ventas de exportación facturadas entre enero y junio de 2025 | Sección A, línea 20; Sección E, línea 5; Figura 1 | ✔ |
| Precio medio, 2.º semestre (jul-dic) | 5,085 USD/L | Ídem, facturas entre julio y diciembre de 2025 | Sección A, línea 20; Sección E, línea 5; Figura 1 | ✔ |
| Variación del precio medio | 11,2 % | Precio del 2.º semestre ÷ precio del 1.er semestre − 1 | Sección A, línea 20 (marcada «por confirmar»); Sección E, línea 5 | ✔ |
| Precio medio anual 2025 | 4,83 USD/L | Ingreso neto en dólares ÷ litros, año completo | Sección A, línea 37; Bitácora, supuesto S1 | ✔ |
| Litros exportados, 1.er semestre | 5.763.411 L | Cajas (corregidas) × 9 litros por caja | Sección E, línea 5 | ✔ |
| Litros exportados, 2.º semestre | 5.674.554 L | Ídem | Sección E, líneas 5 y 9 | ✔ |
| Variación de los litros | -1,5 % | Litros del 2.º semestre ÷ litros del 1.er semestre − 1 | Sección E, línea 5 | ✔ |
| Ingreso neto, 1.er semestre | 26,36 M USD | Suma del monto neto (después de descuento) | Sección E, línea 5 | ✔ |
| Ingreso neto, 2.º semestre | 28,85 M USD | Ídem | Sección E, línea 5 | ✔ |
| Variación del ingreso neto | 9,5 % | Ingreso del 2.º semestre ÷ ingreso del 1.er semestre − 1 | Sección E, línea 5 | ✔ |

## 2. Mezcla por tier, precios de lista y descuento

| Cifra | Valor | Cómo se calcula | Dónde aparece en el informe | ¿Coincide? |
|---|---:|---|---|---|
| Varietal: participación en los litros, 1.er semestre | 42,6 % | Litros del tier ÷ litros totales exportados | Sección E, línea 7; Figura 2 | ✔ |
| Varietal: participación en los litros, 2.º semestre | 33,3 % | Ídem | Sección E, línea 7; Figura 2 | ✔ |
| Reserva: participación en los litros, 1.er semestre | 34,7 % | Litros del tier ÷ litros totales exportados | Figura 2 | ✔ |
| Reserva: participación en los litros, 2.º semestre | 34,2 % | Ídem | Figura 2 | ✔ |
| Gran Reserva: participación en los litros, 1.er semestre | 22,7 % | Litros del tier ÷ litros totales exportados | Sección A, línea 20; Sección E, línea 7; Figura 2 | ✔ |
| Gran Reserva: participación en los litros, 2.º semestre | 32,5 % | Ídem | Sección A, línea 20; Sección E, línea 7; Figura 2 | ✔ |
| Gran Reserva: cambio de participación | 9,8 pp | Participación del 2.º semestre − la del 1.er semestre (puntos porcentuales) | Sección E, línea 7 | ✔ |
| Varietal: cambio de participación | -9,3 pp | Ídem | Sección E, línea 7 | ✔ |
| Precio de lista Varietal, 1.er semestre | 23,65 USD/caja | Precio unitario antes de descuento, promedio ponderado por cajas | Figura 3 | ✔ |
| Precio de lista Varietal, 2.º semestre | 23,61 USD/caja | Ídem | Figura 3 | ✔ |
| Variación del precio de lista Varietal | -0,15 % | Lista del 2.º semestre ÷ lista del 1.er semestre − 1 | Sección A, línea 20; Sección E, línea 7 (rango «entre −0,15 % y −0,19 %») | ✔ |
| Precio de lista Reserva, 1.er semestre | 43,67 USD/caja | Precio unitario antes de descuento, promedio ponderado por cajas | Figura 3 | ✔ |
| Precio de lista Reserva, 2.º semestre | 43,60 USD/caja | Ídem | Figura 3 | ✔ |
| Variación del precio de lista Reserva | -0,16 % | Lista del 2.º semestre ÷ lista del 1.er semestre − 1 | Sección A, línea 20; Sección E, línea 7 (rango «entre −0,15 % y −0,19 %») | – |
| Precio de lista Gran Reserva, 1.er semestre | 77,30 USD/caja | Precio unitario antes de descuento, promedio ponderado por cajas | Figura 3 | ✔ |
| Precio de lista Gran Reserva, 2.º semestre | 77,15 USD/caja | Ídem | Figura 3 | ✔ |
| Variación del precio de lista Gran Reserva | -0,19 % | Lista del 2.º semestre ÷ lista del 1.er semestre − 1 | Sección A, línea 20; Sección E, línea 7 (rango «entre −0,15 % y −0,19 %») | ✔ |
| Descuento medio, 1.er semestre | 3,82 % | Descuento de cada venta, promedio ponderado por cajas | Sección A, línea 20; Sección E, línea 7 | ✔ |
| Descuento medio, 2.º semestre | 4,40 % | Ídem | Sección A, línea 20; Sección E, línea 7 | ✔ |

## 3. Descomposición del alza: ¿precio o mezcla?

| Cifra | Valor | Cómo se calcula | Dónde aparece en el informe | ¿Coincide? |
|---|---:|---|---|---|
| Efecto precio (método principal) | -0,035 USD/L | Cambio del precio por litro de cada tier, ponderado por su participación en el 1.er semestre | Figura 1 | ✔ |
| Efecto mezcla (método principal) | 0,551 USD/L | Cambio de la participación de cada tier, valorado al precio por litro del 1.er semestre | Sección E, línea 9; Figura 1 | ✘ (el informe dice 0,552 USD/L) |
| Efecto cruzado (método principal) | -0,005 USD/L | Cambio de participación × cambio de precio (no se atribuye a uno solo) | Figura 1 | ✔ |
| Mezcla como % del alza (método principal) | 108 % | Efecto mezcla ÷ alza total del precio (más de 100 % porque el efecto precio es negativo) | Sección E, línea 5; Figura 1 | ✔ |
| Precio como % del alza (método principal) | -7 % | Efecto precio ÷ alza total del precio | Figura 1 | ✔ |
| Efecto mezcla, método simétrico de punto medio | 0,549 USD/L | Sensibilidad. Efecto precio -0,038 USD/L; la mezcla explica 107,4 % del alza | No aparece en el informe | – |
| Efecto mezcla, método secuencial, mezcla primero | 0,551 USD/L | Sensibilidad. Efecto precio -0,041 USD/L; la mezcla explica 107,9 % del alza | No aparece en el informe | – |
| Efecto mezcla, método secuencial, precio primero | 0,546 USD/L | Sensibilidad. Efecto precio -0,035 USD/L; la mezcla explica 106,9 % del alza | No aparece en el informe | – |
| Mezcla como % del alza: mínimo entre los 4 métodos | 106,9 % | Sensibilidad | No aparece en el informe | – |
| Mezcla como % del alza: máximo entre los 4 métodos | 107,9 % | Sensibilidad | No aparece en el informe | – |
| Precio dentro de un mismo mercado y tier | -0,006 USD/L | Parte del efecto precio que es cambio de precio real, comparando el mismo tier en el mismo mercado | No aparece en el informe | – |
| Mezcla de mercados dentro de cada tier | -0,033 USD/L | Parte del efecto precio que viene de vender más en mercados de menor precio | No aparece en el informe | – |
| Término cruzado por mercado y tier | -0,002 USD/L | Resto de la separación anterior; las tres partes suman el efecto precio más el cruzado | No aparece en el informe | – |

## 4. Caso de negocio

| Cifra | Valor | Cómo se calcula | Dónde aparece en el informe | ¿Coincide? |
|---|---:|---|---|---|
| Valor de la mezcla en el 2.º semestre | 3,13 M USD | Efecto mezcla (método principal) × litros del 2.º semestre | Sección E, línea 9 | ✔ |
| Ídem con el método simétrico | 3,115 M USD | Sensibilidad | No aparece en el informe | – |
| Tipo de cambio efectivo del 2.º semestre | 946,34 CLP/USD | Ingreso neto en pesos ÷ ingreso neto en dólares, con el dólar del día de cada factura | Sección E, línea 9 | ✔ |
| Valor de la mezcla en pesos | 2.961 M CLP | Valor en dólares × tipo de cambio efectivo del 2.º semestre | Sección E, línea 9 (la línea 11 lo redondea a 3.000) | ✔ |

## 5. Formato magnum y litros por caja

| Cifra | Valor | Cómo se calcula | Dónde aparece en el informe | ¿Coincide? |
|---|---:|---|---|---|
| Magnum: participación en el volumen | 8,07 % | Litros de formato 6x1500 ÷ litros totales exportados | Verificación pedida por el equipo | ✔ |
| Magnum: participación en el ingreso | 13,76 % | Ingreso neto de formato 6x1500 ÷ ingreso neto total | Verificación pedida por el equipo | ✔ |
| Magnum: precio de lista por caja | 77,26 USD/caja | Precio antes de descuento, ponderado por cajas | Sección A, línea 35 | ✔ |
| Gran Reserva estándar (12x750): precio de lista por caja | 77,20 USD/caja | Ídem | Sección A, línea 35 | ✔ |
| Magnum: ingreso neto por caja | 74,05 USD/caja | Ingreso neto ÷ cajas | Aclaración para la sección A, línea 35 | – |
| Gran Reserva estándar: ingreso neto por caja | 74,08 USD/caja | Ídem | Aclaración para la sección A, línea 35 | – |
| Precio anual si el magnum rindiera 18 litros por caja | 4,47 USD/L | Sensibilidad: solo cambian los litros del formato 6x1500 | Sección A, línea 37 (marcada «por confirmar»); Bitácora, supuesto S1 | ✔ |
| Precio anual si el magnum rindiera 4,5 litros por caja | 5,03 USD/L | Ídem | Sección A, línea 37 (marcada «por confirmar»); Bitácora, supuesto S1 | ✔ |
| Diferencia con 18 litros | -7,5 % | Contra el precio anual con 9 litros | Bitácora, supuesto S1 | ✔ |
| Diferencia con 4,5 litros | 4,2 % | Contra el precio anual con 9 litros | Bitácora, supuesto S1 | ✔ |

## 6. Universo y cobertura de datos

| Cifra | Valor | Cómo se calcula | Dónde aparece en el informe | ¿Coincide? |
|---|---:|---|---|---|
| Ventas registradas | 13.983 | Filas de la tabla ventas del ERP | Sección F, línea 3 | ✔ |
| Filas del modelo (tabla fact_venta) | 13.845 | Ventas sin duplicados; incluye las de 2026 y las nacionales | Sección C, línea 21 (marcada «por confirmar») | ✔ |
| Universo de la métrica | 10.672 | Ventas de exportación facturadas en 2025 | Sección C, línea 21 (marcada «por confirmar»); Sección F, línea 5 | ✔ |
| Filas de la dimensión producto | 96 | 24 productos × 4 añadas | Sección C, línea 27 (marcada «por confirmar») | ✔ |
| Duplicados eliminados | 138 | Misma venta registrada dos veces | Sección F, línea 3 | ✔ |
| Facturas de 2026 excluidas | 83 | Fuera del período analizado | Sección F, línea 3 | ✔ |
| Excluidas por problemas de datos | 221 | Duplicados + facturas de 2026 | Sección F, línea 3 | ✔ |
| Excluidas por problemas de datos, % | 1,6 % | Sobre las ventas registradas | Sección F, línea 3 | ✔ |
| Ventas nacionales de 2025 (fuera del alcance) | 3.090 | La pregunta es sobre exportación | Sección F, línea 3 | ✔ |
| Montos netos recalculados (universo) | 555 | El monto registrado difería más de 0,5 % de cajas × precio × (1 − descuento) | Sección F, línea 5 | ✔ |
| Ventas cargadas en botellas (universo) | 151 | Cajas divididas por 12 o 10 según el embarque | Sección F, línea 5 | ✔ |
| Monedas vacías asignadas (todas las ventas registradas) | 698 | Se asigna por mercado | Sección F, línea 5 | ✔ |
| Monedas vacías asignadas (universo) | 542 | Ídem, solo dentro del universo (la sección F mezcla ambas bases) | Sección F, línea 5 | – |
| Costos imputados (universo) | 1.852 | El maestro no traía costo para ese producto y añada | Sección F, línea 5 | ✔ |

## 7. Bitácora de supuestos (anexo)

| Cifra | Valor | Cómo se calcula | Dónde aparece en el informe | ¿Coincide? |
|---|---:|---|---|---|
| Supuesto S3: diferencia si se usara el monto registrado, exportación | 2.095,7 M CLP | Monto neto registrado − monto neto corregido, en pesos, dentro del universo | Bitácora, supuesto S3 | ✘ (el informe dice 2.782,0 M CLP) |
| Supuesto S3: ídem, todos los canales de 2025 | 855,2 M CLP | Ídem, facturas de 2025 de exportación y nacionales | Bitácora, supuesto S3 | ✘ (el informe dice 2.782,0 M CLP) |
| Supuesto S3: ventas cuyo monto cuadra a ±0,5 % | 94,5 % | Sobre las 13.845 filas del modelo | Bitácora, supuesto S3 (dice «95 %») | ✔ |
| Supuesto S4: ventas sin moneda | 5,0 % | Sobre las ventas registradas | Bitácora, supuesto S4 | ✔ |
| Supuesto S5: ventas con costo imputado | 17,4 % | Dentro del universo | Bitácora, supuesto S5 | ✔ |
| Supuesto S6: ingreso en pesos a fecha de embarque vs. a fecha de factura | -0,91 % | Diferencia del ingreso total en pesos; la fecha de embarque no es confiable | Bitácora, supuesto S6 | ✘ (el informe dice -0,69 %) |
| Supuesto S6: ingreso en pesos a fecha de cobranza vs. a fecha de factura | -2,14 % | Cobranza = factura + 60 días (hemisferio sur) o + 90 (norte); dólar observado 2025 y 2026 | Bitácora, supuesto S6 | ✘ (el informe dice -1,44 %) |
| Supuesto S7: margen bruto (sin reversar el costo de la merma) | 47,25 % | 1 − costo total ÷ ingreso neto en pesos, dentro del universo | Bitácora, supuesto S7 | ✔ |
| Supuesto S7: margen si se reversara el costo de la merma | 48,05 % | Ídem, restando el costo de las líneas negativas | Bitácora, supuesto S7 | ✔ |
| Supuesto S7: diferencia de costo | 419 M CLP | Costo con cajas en valor absoluto − costo con signo | Bitácora, supuesto S7 | ✔ |
| Supuesto S8: Brasil, Gran Reserva en los litros, 1.er semestre | 22,7 % | Mercado de control del hemisferio sur | Bitácora, supuesto S8 | – |
| Supuesto S8: Brasil, Gran Reserva en los litros, 2.º semestre | 31,5 % | Ídem | Bitácora, supuesto S8 | – |
| Supuesto S8: Gran Reserva en los litros, mes más bajo | 19,8 % | Enero (serie completa en tablas/mensual.csv) | Bitácora, supuesto S8 | – |
| Supuesto S8: Gran Reserva en los litros, mes más alto | 35,9 % | Noviembre | Bitácora, supuesto S8 | – |
| Supuesto S12: fechas dd/mm/aaaa ambiguas (día ≤ 12) | 1.387 | Ventas registradas cuya fecha se podría leer como día/mes o mes/día | Bitácora, supuesto S12 | – |
| Supuesto S12: ambiguas que coinciden con la columna mes leídas como día/mes | 1.281 |  | Bitácora, supuesto S12 | ✔ |
| Supuesto S12: ambiguas que coinciden con la columna mes leídas como mes/día | 121 |  | Bitácora, supuesto S12 (dice «7 casos») | ✘ (el informe dice 7) |
| Supuesto S12: ventas cuya columna mes no coincide con la fecha | 981 | En todos los formatos, también en fechas sin ambigüedad | Bitácora, supuesto S12 | – |

## 8. Figura 4: Gran Reserva por mercado

| Cifra | Valor | Cómo se calcula | Dónde aparece en el informe | ¿Coincide? |
|---|---:|---|---|---|
| Corea del Sur: Gran Reserva en los litros, año 2025 | 25,3 % | 1.er semestre 21,7 % → 2.º semestre 29,4 % | Figura 4 (versión anterior) | ✘ (el informe dice 28,1 %) |
| China: Gran Reserva en los litros, año 2025 | 27,0 % | 1.er semestre 23,4 % → 2.º semestre 30,9 % | Figura 4 (versión anterior) | ✔ |
| Brasil: Gran Reserva en los litros, año 2025 | 26,6 % | 1.er semestre 22,7 % → 2.º semestre 31,5 % | Figura 4 (versión anterior) | ✘ (el informe dice 27,8 %) |
| México: Gran Reserva en los litros, año 2025 | 27,2 % | 1.er semestre 23,1 % → 2.º semestre 31,7 % | Figura 4 (versión anterior) | ✘ (el informe dice 28,5 %) |
| Estados Unidos: Gran Reserva en los litros, año 2025 | 27,1 % | 1.er semestre 21,1 % → 2.º semestre 32,6 % | Figura 4 (versión anterior) | ✘ (el informe dice 26,5 %) |
| Países Bajos: Gran Reserva en los litros, año 2025 | 29,2 % | 1.er semestre 23,1 % → 2.º semestre 33,2 % | Figura 4 (versión anterior) | ✔ |
| Alemania: Gran Reserva en los litros, año 2025 | 27,9 % | 1.er semestre 23,3 % → 2.º semestre 33,2 % | Figura 4 (versión anterior) | ✘ (el informe dice 25,8 %) |
| Canadá: Gran Reserva en los litros, año 2025 | 28,3 % | 1.er semestre 23,7 % → 2.º semestre 33,3 % | Figura 4 (versión anterior) | ✘ (el informe dice 27,4 %) |
| Reino Unido: Gran Reserva en los litros, año 2025 | 27,4 % | 1.er semestre 22,0 % → 2.º semestre 33,3 % | Figura 4 (versión anterior) | ✘ (el informe dice 25,3 %) |
| Japón: Gran Reserva en los litros, año 2025 | 29,2 % | 1.er semestre 23,0 % → 2.º semestre 35,3 % | Figura 4 (versión anterior) | ✘ (el informe dice 26,2 %) |

## 9. Sección D: métrica y sensibilidad

| Cifra | Valor | Cómo se calcula | Dónde aparece en el informe | ¿Coincide? |
|---|---:|---|---|---|
| Líneas de exportación de 2025 en la suma | 10.672 | Universo de la métrica | Sección D | ✔ |
| P, 1.er semestre | 4,574 USD/L | Σ monto neto USD ÷ Σ litros | Sección D | ✔ |
| P, 2.º semestre | 5,085 USD/L | Ídem | Sección D | ✔ |
| Alza de P | 0,511 USD/L | P del 2.º semestre − P del 1.er semestre | Sección D | ✔ |
| Alza de P, % | 11,2 % | P del 2.º semestre ÷ P del 1.er semestre − 1 | Sección D | ✔ |
| Varietal: proporción de litros (w), 1.er semestre | 42,6 % | Tabla «Datos de entrada» | Sección D | ✔ |
| Varietal: proporción de litros (w), 2.º semestre | 33,3 % | Ídem | Sección D | ✔ |
| Varietal: precio por litro (p), 1.er semestre | 2,528 USD/L | Σ monto neto USD ÷ Σ litros del tier | Sección D | ✔ |
| Varietal: precio por litro (p), 2.º semestre | 2,501 USD/L | Ídem | Sección D | ✔ |
| Reserva: proporción de litros (w), 1.er semestre | 34,7 % | Tabla «Datos de entrada» | Sección D | ✔ |
| Reserva: proporción de litros (w), 2.º semestre | 34,2 % | Ídem | Sección D | ✔ |
| Reserva: precio por litro (p), 1.er semestre | 4,659 USD/L | Σ monto neto USD ÷ Σ litros del tier | Sección D | ✔ |
| Reserva: precio por litro (p), 2.º semestre | 4,643 USD/L | Ídem | Sección D | ✔ |
| Gran Reserva: proporción de litros (w), 1.er semestre | 22,7 % | Tabla «Datos de entrada» | Sección D | ✔ |
| Gran Reserva: proporción de litros (w), 2.º semestre | 32,5 % | Ídem | Sección D | ✔ |
| Gran Reserva: precio por litro (p), 1.er semestre | 8,277 USD/L | Σ monto neto USD ÷ Σ litros del tier | Sección D | ✔ |
| Gran Reserva: precio por litro (p), 2.º semestre | 8,197 USD/L | Ídem | Sección D | ✔ |
| Tiers cuyo precio por litro bajó entre semestres | 3 | «Los tres precios por tier bajaron» | Sección D | ✔ |
| Varietal: aporte al efecto mezcla | -0,235 USD/L | (w del 2.º sem. − w del 1.er sem.) × p del 1.er sem.; tabla «Cálculo» | Sección D | ✔ |
| Varietal: aporte al efecto precio | -0,012 USD/L | w del 1.er sem. × (p del 2.º sem. − p del 1.er sem.) | Sección D | ✔ |
| Varietal: aporte al término cruzado | 0,003 USD/L | (cambio de w) × (cambio de p) | Sección D | ✔ |
| Reserva: aporte al efecto mezcla | -0,023 USD/L | (w del 2.º sem. − w del 1.er sem.) × p del 1.er sem.; tabla «Cálculo» | Sección D | ✔ |
| Reserva: aporte al efecto precio | -0,006 USD/L | w del 1.er sem. × (p del 2.º sem. − p del 1.er sem.) | Sección D | ✔ |
| Reserva: aporte al término cruzado | 0,000 USD/L | (cambio de w) × (cambio de p) | Sección D | ✔ |
| Gran Reserva: aporte al efecto mezcla | 0,809 USD/L | (w del 2.º sem. − w del 1.er sem.) × p del 1.er sem.; tabla «Cálculo» | Sección D | ✔ |
| Gran Reserva: aporte al efecto precio | -0,018 USD/L | w del 1.er sem. × (p del 2.º sem. − p del 1.er sem.) | Sección D | ✔ |
| Gran Reserva: aporte al término cruzado | -0,008 USD/L | (cambio de w) × (cambio de p) | Sección D | ✔ |
| Total: aporte al efecto mezcla | 0,551 USD/L | (w del 2.º sem. − w del 1.er sem.) × p del 1.er sem.; tabla «Cálculo» | Sección D | ✔ |
| Total: aporte al efecto precio | -0,035 USD/L | w del 1.er sem. × (p del 2.º sem. − p del 1.er sem.) | Sección D | ✔ |
| Total: aporte al término cruzado | -0,005 USD/L | (cambio de w) × (cambio de p) | Sección D | ✔ |
| Gran Reserva: puntos de proporción ganados | 9,8 pp | «9,8 puntos más» | Sección D | ✔ |
| Gran Reserva: lo que suma al precio medio | 0,81 USD/L | «suma 0,81 USD/L» | Sección D | ✔ |
| Varietal: puntos de proporción perdidos | 9,3 pp | «9,3 puntos menos» | Sección D | ✔ |
| Varietal: lo que resta al precio medio | 0,23 USD/L | «resta 0,23» | Sección D | ✔ |
| Columna de precio sumando los valores redondeados | -0,036 USD/L | Suma de los tres aportes ya redondeados a 3 decimales («suma −0,036 en vez de −0,035») | Sección D | ✔ |
| Mezcla, % del alza | 108 % | Tabla «Resultado» | Sección D | ✔ |
| Precio, % del alza | -7 % | Ídem | Sección D | ✔ |
| Cruzado, % del alza | -1 % | Ídem («apenas el 1 %») | Sección D | ✔ |
| Variación del precio de lista Varietal | -0,15 % | Extremo del rango «entre 0,15 % y 0,19 %» | Sección D | ✔ |
| Variación del precio de lista Gran Reserva | -0,19 % | Ídem | Sección D | ✔ |
| Descuento medio, 1.er semestre | 3,82 % | Ponderado por cajas | Sección D | ✔ |
| Descuento medio, 2.º semestre | 4,40 % | Ídem | Sección D | ✔ |
| Magnum vs Gran Reserva estándar: diferencia de precio de lista por caja | 0,07 USD/caja | «el precio por caja coincide»: 77,26 vs 77,20 | Sección D | – |
| Magnum vs Gran Reserva estándar: diferencia máxima de costo por caja (misma añada) | 0 CLP/caja | «el costo por caja coincide» | Sección D | ✔ |
| Magnum 9,0 L (adoptada): P del 1.er semestre | 4,574 USD/L | Análisis completo con esa definición | Sección D | ✔ |
| Magnum 9,0 L (adoptada): P del 2.º semestre | 5,085 USD/L | Ídem | Sección D | ✔ |
| Magnum 9,0 L (adoptada): alza del precio | 11,2 % | P₂ ÷ P₁ − 1 | Sección D | ✔ |
| Magnum 9,0 L (adoptada): mezcla, % del alza | 107,9 % | Descomposición principal con esa definición | Sección D | ✔ |
| Magnum 18,0 L: P del 1.er semestre | 4,287 USD/L | Análisis completo con esa definición | Sección D | ✔ |
| Magnum 18,0 L: P del 2.º semestre | 4,646 USD/L | Ídem | Sección D | ✔ |
| Magnum 18,0 L: alza del precio | 8,4 % | P₂ ÷ P₁ − 1 | Sección D | ✔ |
| Magnum 18,0 L: mezcla, % del alza | 108,2 % | Descomposición principal con esa definición | Sección D | ✔ |
| Magnum 4,5 L: P del 1.er semestre | 4,733 USD/L | Análisis completo con esa definición | Sección D | ✔ |
| Magnum 4,5 L: P del 2.º semestre | 5,337 USD/L | Ídem | Sección D | ✔ |
| Magnum 4,5 L: alza del precio | 12,8 % | P₂ ÷ P₁ − 1 | Sección D | ✔ |
| Magnum 4,5 L: mezcla, % del alza | 108,2 % | Descomposición principal con esa definición | Sección D | ✔ |
| Precio anual con magnum de 9 L | 4,83 USD/L | Definición adoptada | Sección D | ✔ |
| Precio anual con magnum de 18 L | 4,47 USD/L | Definición alternativa | Sección D | ✔ |
| Precio anual con magnum de 4,5 L | 5,03 USD/L | Definición alternativa | Sección D | ✔ |
| Cambio del precio anual con 18 L | -7,5 % | Contra 9 L («un 7,5 % menos») | Sección D | ✔ |
| Cambio del precio anual con 4,5 L | 4,2 % | Contra 9 L | Sección D | ✔ |
| Mezcla, % del alza: mínimo entre las tres definiciones | 108 % | «108 % con las tres definiciones» | Sección D | ✔ |
| Mezcla, % del alza: máximo entre las tres definiciones | 108 % | Ídem | Sección D | ✔ |
| Método de descomposición: mezcla, % del alza (mínimo) | 106,9 % | Cuatro métodos (base 1.er semestre, simétrico y dos secuenciales) | Sección D | ✔ |
| Método de descomposición: mezcla, % del alza (máximo) | 107,9 % | Ídem | Sección D | ✔ |
| Sin las cajas descartadas por merma (cadena de frío, fallas de suministro): mezcla, % del alza | 108,0 % | Se ignoran las líneas de merma | Sección D | ✔ |
| Con precio de lista: mezcla, % del alza | 101,7 % | Antes de descuento | Sección D | ✔ |
| Mezcla, % del alza: mínimo entre todas las alternativas en USD | 101,7 % | «en ninguna alternativa la mezcla baja del 100 %» | Sección D | – |
| Alza del precio en pesos, dólar de la fecha de factura | 10,1 % | CLP/L | Sección D | ✔ |
| Alza del precio en pesos, dólar de la fecha estimada de cobranza | 6,3 % | Factura + 60 días (sur) o + 90 (norte) | Sección D | ✔ |
| Alza del precio en dólares | 11,2 % | Para comparar con las dos anteriores | Sección D | ✔ |

## Notas

- **Supuesto S3:** los CLP 2.782 millones de la bitácora no se reproducen con ninguna de las dos definiciones de la tabla 7. Quien escribió el supuesto debe aclarar qué sumó.
- **Efecto mezcla (sección E, línea 9; figura 1):** el valor es 0,5515 USD/L, que redondea a 0,551. Las cifras que se derivan de él (108 %, USD 3,13 millones, CLP ≈ 2.960 millones) sí coinciden.
- **Supuesto S6:** la fecha de embarque no es confiable (en 30 % de las ventas es anterior a la factura), así que la cifra se informa solo porque la bitácora la cita. Además, la versión anterior usaba el último dólar de 2025 para las fechas posteriores al 30 de diciembre de 2025; ahora se usa el dólar observado de 2026, y por eso cambia.
- **Figura 4:** ahora se genera desde `tablas/fig4_gran_reserva_mercado.csv` y muestra el 1.er y el 2.º semestre por mercado. Los valores escritos a mano en la versión anterior no salían de los datos.
- **Métodos de descomposición:** el principal es el de la sección E (base 1.er semestre, con término cruzado). Los otros tres (simétrico, mezcla primero y precio primero) dan la mezcla entre 0,546 y 0,551 USD/L; detalle en `tablas/descomposicion_metodos.csv`.
