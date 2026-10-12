# Cobertura y calidad de datos

Generado por `src/limpiar.py` (vía `python run.py`). No editar a mano.

Base: 13.983 filas de `ventas`. Las reglas de la etapa *crudo* (formatos y duplicados) se miden sobre las 13.983 filas crudas; las demás, sobre las 13.845 que quedan tras deduplicar (las que entran a `fact_venta`). El % de litros usa |cajas corregidas| × litros por caja. La última columna cuenta las filas dentro del universo de la métrica (exportación, factura 2025: 10.672 filas).

## Reglas sobre las ventas

| Regla | Hallazgo | Acción | Filas | % filas | % litros | Filas en universo |
|---|---|---|---:|---:|---:|---:|
| C | Fecha en formato d-mes-aaaa | parseada | 3.534 | 25,27 % | 25,94 % | 2.729 |
| C | Fecha en formato aaaa-mm-dd | parseada | 3.507 | 25,08 % | 24,84 % | 2.690 |
| C | Fecha en formato dd/mm/aaaa | parseada | 3.479 | 24,88 % | 24,81 % | 2.651 |
| C | Fecha en formato dd-mm-aa | parseada | 3.463 | 24,77 % | 24,41 % | 2.602 |
| C | Fecha inválida o no reconocida | excluida | 0 | 0,00 % | 0,00 % | 0 |
| C | Columna mes distinta del mes de la fecha | se ignora; mes y semestre salen de la fecha | 981 | 7,02 % | 7,35 % | 699 |
| C | dd/mm/aaaa con día ≤ 12 (ambigua; 121 calzarían con la columna mes leídas como mm/dd) | se lee como dd/mm | 1.387 | 9,92 % | 9,79 % | 1.049 |
| C | Columna zona distinta de la zona del mercado | se ignora; zona sale de mercados | 907 | 6,49 % | 6,34 % | 707 |
| C | Mercado con zona inexistente (zona_id 8, Corea del Sur) | zona = Asia | 1.059 | 7,57 % | 7,22 % | 1.045 |
| 2 | Precio exportación: sin $, coma | USD con punto o coma decimal | 6.533 | 46,72 % | 45,14 % | 6.435 |
| 2 | Precio exportación: sin $, punto | USD con punto o coma decimal | 4.304 | 30,78 % | 29,82 % | 4.237 |
| 2 | Precio nacional: con $, punto | CLP con punto de miles | 1.007 | 7,20 % | 7,96 % | 0 |
| 2 | Precio nacional: sin $, entero | CLP con punto de miles | 1.084 | 7,75 % | 9,04 % | 0 |
| 2 | Precio nacional: sin $, punto | CLP con punto de miles | 1.055 | 7,54 % | 8,03 % | 0 |
| 2 | Monto neto con $ | se quita el símbolo | 1.089 | 7,79 % | 8,54 % | 0 |
| 2 | Descuento entero (8 = 8 %) | llevado a fracción | 2.214 | 15,83 % | 16,16 % | 1.756 |
| 2 | Descuento con % (8%) | llevado a fracción | 2.122 | 15,18 % | 15,43 % | 1.709 |
| 2 | Descuento fracción con coma (0,08) | llevado a fracción | 2.095 | 14,98 % | 14,84 % | 1.657 |
| 2 | Precio ambiguo o fuera del rango de su moneda | revisar (no se excluye) | 0 | 0,00 % | 0,00 % | 0 |
| 3 | Moneda registrada distinta de la del mercado | revisar (no se corrige) | 0 | 0,00 % | 0,00 % | 0 |
| 3 | Moneda vacía | imputada por mercado (Chile CLP, resto USD) | 698 | 4,99 % | 4,81 % | 542 |
| 1 | Duplicado idéntico en crudo | se elimina la segunda | 41 | 0,29 % | 0,25 % | 0 |
| 1 | Duplicado idéntico solo tras normalizar formatos | se elimina la segunda | 96 | 0,69 % | 0,72 % | 0 |
| 1 | Duplicado en conflicto (venta 408996: ninguna fila cuadra: se conserva la primera y la regla 5 recalcula el neto) | se elimina la otra fila | 1 | 0,01 % | 0,01 % | 0 |
| 8 | Venta de exportación sin embarque | sin incoterm | 0 | 0,00 % | 0,00 % | 0 |
| 8 | Venta nacional con embarque | revisar | 0 | 0,00 % | 0,00 % | 0 |
| 4 | Cajas cargadas en botellas (venta = 12 × cajas del embarque) | cajas ÷ 12 | 111 | 0,80 % | 0,75 % | 111 |
| 4 | Cajas cargadas en botellas (venta = 10 × cajas del embarque) | cajas ÷ 10 | 40 | 0,29 % | 0,27 % | 40 |
| 4 | Merma con cajas positivas en el embarque | se mantiene el signo de la venta | 88 | 0,64 % | 0,59 % | 88 |
| 4 | Cajas distintas del embarque sin factor 12 o 10 | revisar (no se corrige) | 0 | 0,00 % | 0,00 % | 0 |
| 9 | Litros = cajas × 9,0 (formato 12x750) | litros por caja del maestro | 12.681 | 91,59 % | 91,71 % | 9.773 |
| 9 | Litros = cajas × 9,0 (formato 6x1500, magnum) | litros por caja del maestro | 1.164 | 8,41 % | 8,29 % | 899 |
| C | Costo faltante en el maestro (par ausente o N/A) | imputado por (tier, añada) | 2.334 | 16,86 % | 16,41 % | 1.852 |
| 5 | Monto neto descuadrado: registrado igual al bruto (sin descuento) | recalculado | 23 | 0,17 % | 0,17 % | 17 |
| 5 | Monto neto descuadrado: otras diferencias | recalculado | 734 | 5,30 % | 7,33 % | 538 |
| 6 | Merma (cajas negativas) | se incluye; costo con |cajas| | 110 | 0,79 % | 0,75 % | 88 |
| 7 | Factura de 2026 | en la estrella; fuera de la métrica | 83 | 0,60 % | 0,57 % | 0 |
| alcance | Venta nacional (Chile) | en la estrella; fuera de la métrica | 3.113 | 22,48 % | 24,98 % | 0 |
| 10 | Dólar de la factura: último día hábil previo | tipo de cambio asignado | 4.377 | 31,61 % | 31,51 % | 3.405 |
| 10 | Dólar de la factura: 1 de enero = 2 de enero | tipo de cambio asignado | 42 | 0,30 % | 0,31 % | 34 |
| 10 | Dólar de la factura: posterior al último dólar publicado: último valor | tipo de cambio asignado | 0 | 0,00 % | 0,00 % | 0 |
| 10 | Dólar de la factura: sin dólar | queda sin dólar | 0 | 0,00 % | 0,00 % | 0 |
| 10 | Dólar de la cobranza (factura + 60 días sur / + 90 norte): último día hábil previo | tipo de cambio de la sensibilidad c | 4.476 | 32,33 % | 32,55 % | 3.450 |
| 10 | Dólar de la cobranza (factura + 60 días sur / + 90 norte): 1 de enero = 2 de enero | tipo de cambio de la sensibilidad c | 40 | 0,29 % | 0,29 % | 28 |
| 10 | Dólar de la cobranza (factura + 60 días sur / + 90 norte): posterior al último dólar publicado: último valor | tipo de cambio de la sensibilidad c | 0 | 0,00 % | 0,00 % | 0 |
| 10 | Dólar de la cobranza (factura + 60 días sur / + 90 norte): sin dólar | queda sin dólar | 0 | 0,00 % | 0,00 % | 0 |

## Hallazgos en las otras fuentes

| Fuente | Hallazgo | Cantidad | Acción |
|---|---|---:|---|
| SQLite mercados | Corea del Sur: zona_id 8 no existe en zonas | 1 mercado | asignado a Asia |
| SQLite ventas | Filas iguales con distinto venta_id | 0 filas | ninguna acción |
| JSON embarques | embarque_id repetido | 30 embarques | 15 fantasmas eliminados (sin venta, puerto Valparaíso); 15 reales se conservan |
| JSON embarques | Líneas de los embarques fantasma | 15 líneas | eliminadas |
| JSON embarques | cajas como texto ("35") | 4.202 líneas | convertidas a entero |
| JSON embarques | fecha_embarque en 2 formatos (aaaa-mm-dd 1531, dd/mm/aaaa 1518) | 3.049 embarques | parseada; no se usa para la métrica |
| JSON embarques | Embarques con fecha en 2026 | 234 embarques | no se usa la fecha (regla 8) |
| JSON embarques | mercado_id del embarque distinto del de la venta | 6.897 líneas | no se usa el mercado (regla 8) |
| JSON embarques | Embarque con fecha anterior a la factura | 3.223 líneas | no se usa la fecha (regla 8) |
| JSON embarques | Factura 2025 con embarque en 2026 | 810 líneas | no se usa la fecha (regla 8) |
| CSV costos | Filas que no son datos (encabezado repetido y TOTAL) | 2 líneas | descartadas al leer |
| CSV costos | Costo en formatos 34.344,00 / 34.344 / 34344 | 80 filas | normalizado a número |
| CSV costos | Costo N/A | 1 filas | imputado por (tier, añada) |
| CSV costos | Cepa escrita con alias (20 grafías para 7 cepas) | 58 filas | conformada a cepas.cepa del ERP |
| CSV costos | activo como si/SI/Sí/1 | 81 filas | 81 verdaderos |
| CSV costos | litros_por_caja distinto de 9,0 | 0 filas | ninguna acción (regla 9) |
| CSV costos | Pares producto-añada ausentes del maestro | 15 pares | creados con costo por (tier, añada) |

## Verificación de la regla 2: precio unitario por zona

| Zona | Mínimo | Máximo | Filas |
|---|---:|---:|---:|
| Asia | 22,70 | 80,32 | 3.101 |
| Europa | 22,70 | 80,32 | 3.543 |
| LatAm | 22,70 | 80,32 | 2.144 |
| Nacional | 20.428,00 | 72.290,00 | 3.146 |
| Norteamérica | 22,70 | 80,32 | 2.049 |

Los rangos no se solapan (CLP en Nacional, USD en el resto), así que el canal basta para leer el separador.

## Regla 3: ¿hay patrón en la moneda vacía?

| Corte | % de filas con moneda vacía (mín – máx entre grupos) |
|---|---|
| mercado_id | 3,8 – 5,9 % |
| vendedor_id | 4,7 – 5,3 % |
| cliente_id | 2,8 – 6,9 % |
| mes_num | 3,7 – 6,8 % |

La tasa es pareja en todos los cortes: no hay un mercado, vendedor, cliente o mes que concentre los vacíos.

## Registros excluidos de la métrica

| Motivo | Filas | % de las filas crudas | % de litros |
|---|---:|---:|---:|
| Duplicados (regla 1) | 138 | 0,99 % | 0,98 % |
| Facturas de 2026 (regla 7) | 83 | 0,59 % | 0,57 % |
| **Subtotal calidad** | 221 | 1,58 % | 1,55 % |
| Ventas nacionales 2025 (alcance) | 3.090 | 22,10 % | 24,58 % |
| **Total excluido de la métrica** | 3.311 | 23,68 % | 26,13 % |

Universo de la métrica: 10.672 filas (76,32 % de las crudas). Ninguna fila se excluye por formato: todas las fechas, precios y montos se pudieron leer. En `fact_venta` quedan 13.845 filas (incluye 83 de 2026 y 3113 nacionales).
