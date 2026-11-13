# Cobertura y calidad de los datos de ventas

Este archivo responde qué pasó con cada una de las ventas registradas por la viña: cuántas se descartaron, cuántas se corrigieron y por qué. Los datos vienen de la tabla `ventas` de `origen_vina.sqlite`, cruzada con el maestro de costos (`origen_costos_productos.csv`), los embarques (`origen_embarques.json`) y el dólar observado de mindicador.cl. Lo genera `src/limpiar.py` al correr `python run.py`; no se edita a mano.

## Resumen

- De las 13.983 ventas registradas, solo 221 (1,58 %) se descartaron por problemas de datos: 138 duplicados y 83 facturas fechadas en 2026, fuera del período analizado.
- Otras 3.090 ventas (22,10 %) quedan fuera por alcance, no por calidad: son ventas nacionales y la pregunta es sobre exportación. El universo de la métrica son 10.672 ventas de exportación facturadas en 2025 (76,32 % de las registradas).
- Ninguna venta se descartó por formato: las fechas venían escritas de 4 maneras y los precios y montos con y sin «$» y con distintos separadores, pero todas se pudieron leer.
- Dentro del universo, los errores se corrigieron sin descartar filas: 555 montos netos recalculados, 151 ventas cargadas en botellas convertidas a cajas, 542 monedas vacías asignadas por mercado y 1.852 costos imputados según su tier y añada.
- El archivo de embarques solo es confiable para las cajas: en 6.897 de 10.732 líneas (64 %) el mercado no coincide con el de la venta, y en 3.223 (30 %) el embarque es anterior a la factura. Por eso no se usan su fecha ni su mercado.

## Cómo leer las tablas

- **Tema**: el tipo de problema o de regla.
- **Hallazgo**: qué se encontró en los datos.
- **Qué se hizo**: la acción aplicada. Solo los duplicados se eliminan; el resto de las filas se conserva, corregida si hace falta.
- **Filas**: cuántas ventas afecta. Las reglas de lectura de formatos y de duplicados se miden sobre las 13.983 ventas tal como vienen; las demás, sobre las 13.845 que quedan después de quitar los duplicados (las que entran al modelo, tabla `fact_venta`).
- **% de filas** y **% de litros**: el peso de esas ventas sobre el total, en número de filas y en litros (cajas corregidas × 9 litros por caja, en valor absoluto).
- **En el universo**: cuántas de esas filas forman parte del universo de la métrica (exportación, factura de 2025; 10.672 ventas).
- Un valor 0 en una verificación significa que el control no encontró ningún caso.

## 1. Ventas excluidas de la métrica

| Motivo | Ventas | % de las registradas | % de los litros |
|---|---:|---:|---:|
| Duplicados | 138 | 0,99 % | 0,98 % |
| Facturas de 2026 (fuera del período) | 83 | 0,59 % | 0,57 % |
| **Subtotal: problemas de datos** | 221 | 1,58 % | 1,55 % |
| Fuera del alcance: ventas nacionales de 2025 | 3.090 | 22,10 % | 24,58 % |
| **Total excluido de la métrica** | 3.311 | 23,68 % | 26,13 % |

Universo de la métrica: **10.672 ventas** (76,32 % de las registradas). Las facturas de 2026 y las ventas nacionales no se borran: quedan en el modelo (`fact_venta`, 13.845 filas) y solo se filtran al calcular la métrica.

### Detalle de las filas excluidas

| Tema | Hallazgo | Qué se hizo | Filas | % de filas | % de litros | En el universo |
|---|---|---|---:|---:|---:|---:|
| Duplicados | Venta repetida, idéntica tal como viene | se elimina la copia | 41 | 0,29 % | 0,25 % | 0 |
| Duplicados | Venta repetida, idéntica tras unificar formatos | se elimina la copia | 96 | 0,69 % | 0,72 % | 0 |
| Duplicados | Venta repetida con montos distintos (venta 408996: ninguna fila cuadra: se conserva la primera y su monto neto se recalcula) | se elimina la otra fila | 1 | 0,01 % | 0,01 % | 0 |
| Período | Factura de 2026 | queda en el modelo; fuera de la métrica | 83 | 0,60 % | 0,57 % | 0 |
| Fuera del alcance: ventas nacionales | Venta en Chile, facturada en pesos | queda en el modelo; fuera de la métrica | 3.113 | 22,48 % | 24,98 % | 0 |

## 2. Correcciones aplicadas (la fila se conserva con el valor corregido)

| Tema | Hallazgo | Qué se hizo | Filas | % de filas | % de litros | En el universo |
|---|---|---|---:|---:|---:|---:|
| Zona de Corea del Sur | Mercado con zona inexistente (zona_id 8) | se asigna la zona Asia | 1.059 | 7,57 % | 7,22 % | 1.045 |
| Moneda vacía | La venta no trae moneda | se asigna por mercado (Chile CLP, resto USD) | 698 | 4,99 % | 4,81 % | 542 |
| Cajas cargadas como botellas | La venta registra 12 veces las cajas del embarque | cajas ÷ 12 | 111 | 0,80 % | 0,75 % | 111 |
| Cajas cargadas como botellas | La venta registra 10 veces las cajas del embarque | cajas ÷ 10 | 40 | 0,29 % | 0,27 % | 40 |
| Costo faltante | El maestro no trae costo para ese producto y añada | se imputa el costo de su tier y añada | 2.334 | 16,86 % | 16,41 % | 1.852 |
| Monto neto descuadrado | El monto registrado es el bruto (no resta el descuento) | se recalcula como cajas × precio × (1 − descuento) | 23 | 0,17 % | 0,17 % | 17 |
| Monto neto descuadrado | El monto difiere en más de 0,5 % por otras causas | se recalcula como cajas × precio × (1 − descuento) | 734 | 5,30 % | 7,33 % | 538 |
| Merma | Línea con cajas negativas (vino descartado) | se incluye; el costo se cuenta con las cajas en valor absoluto | 110 | 0,79 % | 0,75 % | 88 |

## 3. Detalle técnico y verificaciones

### 3.1 Formatos leídos (no cambian ningún valor)

| Tema | Hallazgo | Qué se hizo | Filas | % de filas | % de litros | En el universo |
|---|---|---|---:|---:|---:|---:|
| Formato de fechas | Fecha escrita como d-mes-aaaa | leída en su formato | 3.534 | 25,27 % | 25,94 % | 2.729 |
| Formato de fechas | Fecha escrita como aaaa-mm-dd | leída en su formato | 3.507 | 25,08 % | 24,84 % | 2.690 |
| Formato de fechas | Fecha escrita como dd/mm/aaaa | leída en su formato | 3.479 | 24,88 % | 24,81 % | 2.651 |
| Formato de fechas | Fecha escrita como dd-mm-aa | leída en su formato | 3.463 | 24,77 % | 24,41 % | 2.602 |
| Formato de precio unitario | Precio exportación: sin $, coma | USD con punto o coma decimal | 6.533 | 46,72 % | 45,14 % | 6.435 |
| Formato de precio unitario | Precio exportación: sin $, punto | USD con punto o coma decimal | 4.304 | 30,78 % | 29,82 % | 4.237 |
| Formato de precio unitario | Precio nacional: con $, punto | CLP con punto de miles | 1.007 | 7,20 % | 7,96 % | 0 |
| Formato de precio unitario | Precio nacional: sin $, entero | CLP con punto de miles | 1.084 | 7,75 % | 9,04 % | 0 |
| Formato de precio unitario | Precio nacional: sin $, punto | CLP con punto de miles | 1.055 | 7,54 % | 8,03 % | 0 |
| Formato de monto neto | Monto neto con $ | se quita el símbolo | 1.089 | 7,79 % | 8,54 % | 0 |
| Formato de descuento | Descuento entero (8 = 8 %) | llevado a fracción | 2.214 | 15,83 % | 16,16 % | 1.756 |
| Formato de descuento | Descuento con % (8%) | llevado a fracción | 2.122 | 15,18 % | 15,43 % | 1.709 |
| Formato de descuento | Descuento fracción con coma (0,08) | llevado a fracción | 2.095 | 14,98 % | 14,84 % | 1.657 |
| Conversión a litros | Formato 12x750: litros = cajas × 9,0 | litros por caja del maestro de costos | 12.681 | 91,59 % | 91,71 % | 9.773 |
| Conversión a litros | Formato 6x1500 (magnum): litros = cajas × 9,0 | litros por caja del maestro de costos | 1.164 | 8,41 % | 8,29 % | 899 |

### 3.2 Tipo de cambio asignado

| Tema | Hallazgo | Qué se hizo | Filas | % de filas | % de litros | En el universo |
|---|---|---|---:|---:|---:|---:|
| Tipo de cambio | Dólar de la factura: último día hábil previo | tipo de cambio asignado | 4.377 | 31,61 % | 31,51 % | 3.405 |
| Tipo de cambio | Dólar de la factura: 1 de enero = 2 de enero | tipo de cambio asignado | 42 | 0,30 % | 0,31 % | 34 |
| Tipo de cambio | Dólar de la factura: posterior al último dólar publicado: último valor | tipo de cambio asignado | 0 | 0,00 % | 0,00 % | 0 |
| Tipo de cambio | Dólar de la factura: sin dólar | queda sin dólar | 0 | 0,00 % | 0,00 % | 0 |
| Tipo de cambio | Dólar de la cobranza (factura + 60 días sur / + 90 norte): último día hábil previo | tipo de cambio para la sensibilidad de cobranza | 4.476 | 32,33 % | 32,55 % | 3.450 |
| Tipo de cambio | Dólar de la cobranza (factura + 60 días sur / + 90 norte): 1 de enero = 2 de enero | tipo de cambio para la sensibilidad de cobranza | 40 | 0,29 % | 0,29 % | 28 |
| Tipo de cambio | Dólar de la cobranza (factura + 60 días sur / + 90 norte): posterior al último dólar publicado: último valor | tipo de cambio para la sensibilidad de cobranza | 0 | 0,00 % | 0,00 % | 0 |
| Tipo de cambio | Dólar de la cobranza (factura + 60 días sur / + 90 norte): sin dólar | queda sin dólar | 0 | 0,00 % | 0,00 % | 0 |

El dólar observado se toma del día de la factura. Los fines de semana y feriados usan el último día hábil previo, y el 1 de enero usa el 2 de enero, primer día publicado del año. La fecha de cobranza (factura + 60 días en el hemisferio sur, + 90 en el norte) solo se usa en una sensibilidad.

### 3.3 Verificaciones (controles; la mayoría no encontró problemas)

| Tema | Hallazgo | Qué se hizo | Filas | % de filas | % de litros | En el universo |
|---|---|---|---:|---:|---:|---:|
| Formato de fechas | Fecha inválida o no reconocida | se excluiría | 0 | 0,00 % | 0,00 % | 0 |
| Columna mes del ERP | La columna mes no coincide con el mes de la fecha | se ignora; mes y semestre salen de la fecha | 981 | 7,02 % | 7,35 % | 699 |
| Formato de fechas | Fecha dd/mm/aaaa con día ≤ 12 (ambigua; 121 calzarían con la columna mes leídas como mm/dd) | se lee como dd/mm | 1.387 | 9,92 % | 9,79 % | 1.049 |
| Columna zona del ERP | La columna zona no coincide con la zona del mercado | se ignora; la zona sale de la tabla mercados | 907 | 6,49 % | 6,34 % | 707 |
| Precio unitario | Precio ambiguo o fuera del rango de su moneda | revisar (no se excluye) | 0 | 0,00 % | 0,00 % | 0 |
| Moneda | Moneda registrada distinta de la del mercado | revisar (no se corrige) | 0 | 0,00 % | 0,00 % | 0 |
| Cruce con embarques | Venta de exportación sin embarque | queda sin incoterm | 0 | 0,00 % | 0,00 % | 0 |
| Cruce con embarques | Venta nacional con embarque | revisar | 0 | 0,00 % | 0,00 % | 0 |
| Cruce con embarques | Merma con cajas positivas en el embarque | se mantiene el signo de la venta | 88 | 0,64 % | 0,59 % | 88 |
| Cruce con embarques | Cajas distintas del embarque sin factor 12 o 10 | revisar (no se corrige) | 0 | 0,00 % | 0,00 % | 0 |

### 3.4 Hallazgos en las otras fuentes

| Fuente | Hallazgo | Cantidad | Qué se hizo |
|---|---|---:|---|
| SQLite mercados | Corea del Sur: zona_id 8 no existe en zonas | 1 mercado | asignado a Asia |
| SQLite ventas | Filas iguales con distinto venta_id | 0 filas | ninguna acción |
| JSON embarques | embarque_id repetido | 30 embarques | 15 fantasmas eliminados (sin venta, puerto Valparaíso); 15 reales se conservan |
| JSON embarques | Líneas de los embarques fantasma | 15 líneas | eliminadas |
| JSON embarques | cajas como texto ("35") | 4.202 líneas | convertidas a entero |
| JSON embarques | fecha_embarque en 2 formatos (aaaa-mm-dd 1531, dd/mm/aaaa 1518) | 3.049 embarques | parseada; no se usa para la métrica |
| JSON embarques | Embarques con fecha en 2026 | 234 embarques | no se usa la fecha del embarque |
| JSON embarques | mercado_id del embarque distinto del de la venta | 6.897 líneas | no se usa el mercado del embarque |
| JSON embarques | Embarque con fecha anterior a la factura | 3.223 líneas | no se usa la fecha del embarque |
| JSON embarques | Factura 2025 con embarque en 2026 | 810 líneas | no se usa la fecha del embarque |
| CSV costos | Filas que no son datos (encabezado repetido y TOTAL) | 2 líneas | descartadas al leer |
| CSV costos | Costo en formatos 34.344,00 / 34.344 / 34344 | 80 filas | normalizado a número |
| CSV costos | Costo N/A | 1 filas | imputado por (tier, añada) |
| CSV costos | Cepa escrita con alias (20 grafías para 7 cepas) | 58 filas | conformada a cepas.cepa del ERP |
| CSV costos | activo como si/SI/Sí/1 | 81 filas | 81 verdaderos |
| CSV costos | litros_por_caja distinto de 9,0 | 0 filas | ninguna acción |
| CSV costos | Pares producto-añada ausentes del maestro | 15 pares | creados con costo por (tier, añada) |

### 3.5 Precio unitario por zona: ¿se pueden confundir pesos con dólares?

| Zona | Mínimo | Máximo | Filas |
|---|---:|---:|---:|
| Asia | 22,70 | 80,32 | 3.101 |
| Europa | 22,70 | 80,32 | 3.543 |
| LatAm | 22,70 | 80,32 | 2.144 |
| Nacional | 20.428,00 | 72.290,00 | 3.146 |
| Norteamérica | 22,70 | 80,32 | 2.049 |

Los rangos no se solapan: la zona Nacional está en pesos (CLP) y el resto en dólares (USD). Por eso basta el canal para saber si el punto de un precio separa miles («38.467» pesos) o decimales («45.06» dólares).

### 3.6 ¿Hay un patrón en las ventas sin moneda?

| Corte | % de ventas sin moneda (mínimo – máximo entre grupos) |
|---|---|
| Mercado | 3,8 – 5,9 % |
| Vendedor | 4,7 – 5,3 % |
| Cliente | 2,8 – 6,9 % |
| Mes de la factura | 3,7 – 6,8 % |

La tasa es pareja en todos los cortes: ningún mercado, vendedor, cliente ni mes concentra las ventas sin moneda, así que asignarla por mercado no introduce sesgo.
