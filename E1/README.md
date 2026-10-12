# Entrega 1 · Viña Vallehondo · Grupo 2

Pregunta de negocio que responde esta entrega (pregunta 2 del caso): el precio promedio por litro de exportación que subió en 2025, ¿se explica por alzas de precio o por una mayor proporción de gran reserva?

## Estructura

```
E1/
├── run.py              corre la cadena de datos completa (componente B)
├── datos/raw/          las cuatro fuentes del caso
│   ├── origen_vina.sqlite            base comercial (ventas, clientes, mercados, zonas, cepas, monedas, vendedores)
│   ├── origen_costos_productos.csv   costos por producto y añada (latin-1, separador ;)
│   ├── origen_embarques.json         embarques de exportación
│   ├── dolar_2025.json               respaldo de https://mindicador.cl/api/dolar/2025, descargado el 2 de octubre de 2026
│   └── dolar_2026.json               respaldo de https://mindicador.cl/api/dolar/2026, descargado el 12 de octubre de 2026
├── src/                código
│   ├── extraer.py                    lee las cuatro fuentes (API del dólar con respaldo local)
│   ├── limpiar.py                    reglas de calidad; escribe output/cobertura.md
│   ├── integrar.py                   construye la estrella y la tabla integrada
│   ├── metrica.py                    métrica, descomposición y sensibilidades; escribe output/cifras.md
│   ├── graficos.py                   figuras 1 a 4 de la sección E, desde output/tablas/
│   ├── esquema.py                    definición del modelo estrella (tablas, columnas, origen y regla)
│   ├── diagrama_modelo.py            dibuja el modelo estrella desde esquema.py
│   └── generar_diccionario.py        escribe el diccionario de datos del anexo desde esquema.py
├── output/             lo genera el código (no editar a mano), salvo discrepancias.md
│   ├── cifras.md                     cada cifra del informe, su definición y si coincide con el texto
│   ├── cobertura.md                  cada regla de limpieza con filas, % de filas y % de litros
│   ├── discrepancias.md              lo que hay que corregir en el informe (escrito a mano)
│   ├── tabla_integrada.csv           la estrella unida: una fila por línea de venta facturada
│   ├── estrella/                     fact_venta y dim_tiempo, dim_producto, dim_cliente, dim_mercado
│   ├── tablas/                       tablas que alimentan cada figura y las sensibilidades
│   └── figuras/                      figuras del informe
└── informe/            fuentes LaTeX del informe y anexos
    └── anexos/                       acta de la reunión del 4 de septiembre
```

## Requisitos

- Python 3.11 o superior (probado con 3.12 y 3.14).
- Dependencias con versión fija: `pip install -r requirements.txt` (pandas, numpy, matplotlib).
- Conexión a internet opcional: sin red se usan los respaldos del dólar.

## Cómo reproducir

Desde la carpeta `E1/`:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

`run.py` también funciona desde otra carpeta (`python ruta/a/E1/run.py`): todas las rutas se resuelven a partir de la ubicación del archivo.

**API del dólar:** mindicador.cl puede tardar (entre 8 y 30 segundos por año en nuestras pruebas). La cadena espera hasta 60 segundos por año; si la API no responde o falla, usa el respaldo `datos/raw/dolar_<año>.json` y los resultados son idénticos (se verificó byte a byte con ambas fuentes). Al final, el bloque `FUENTE DEL DÓLAR` dice qué se usó para cada año, por ejemplo `Dólar 2025: API mindicador.cl (OK)` o `Dólar 2025: API no respondió (...) → respaldo datos/raw/dolar_2025.json`.

**Tiempo:** alrededor de 1 minuto con la API (unos 20 s de proceso más la espera de la API) y unos 20 s sin red. Si la API no responde, la cadena espera hasta 60 s por año (2025 y 2026) antes de usar el respaldo, así que puede tardar hasta unos 2 minutos y 10 segundos; los resultados son idénticos.

**Qué se espera ver al final.** El bloque `VERIFICACIÓN` con las 8 cifras en `[OK]` y el proceso termina con código 0 (si alguna no calza, termina con código 1):

| Cifra | Valor esperado |
|---|---|
| Universo de la métrica (exportación, factura 2025) | 10.672 filas |
| Gran Reserva, % de los litros exportados, S1 → S2 | 22,7 % → 32,5 % |
| Precio medio de exportación, S1 → S2 | 4,574 → 5,085 USD/L |
| Precio medio anual | 4,83 USD/L |
| Magnum, % del volumen y de los ingresos | 8,07 % y 13,76 % |

### Qué genera la cadena

| Archivo en `output/` | Para qué sirve |
|---|---|
| `cifras.md` | Cada cifra del informe, cómo se calcula y si el valor escrito coincide con los datos (empieza con un resumen). |
| `cobertura.md` | Qué pasó con cada venta: cuántas se excluyeron, cuántas se corrigieron y por qué. |
| `tablas/*.csv` | Los datos detrás de cada figura y de cada sensibilidad (descomposición por método, por mercado, mensual). |
| `figuras/figura1..4` | Las figuras de la sección E, en PDF (para LaTeX) y PNG. |
| `tabla_integrada.csv` | Todas las ventas limpias en una sola tabla (13.845 filas); no se versiona, se regenera. |
| `estrella/*.csv` | El modelo dimensional: `fact_venta` y sus cuatro dimensiones; no se versiona, se regenera. |
| `discrepancias.md` | Lo que hay que corregir en el informe; es el único archivo de `output/` escrito a mano. |

### Otros comandos

| Paso | Comando | Qué produce |
|---|---|---|
| Solo las figuras (si `output/tablas/` ya existe) | `python src/graficos.py` | `output/figuras/figura1..4` |
| Diagrama del modelo | `python src/diagrama_modelo.py` | `output/figuras/modelo_estrella.pdf` y `.png` |
| Diccionario de datos | `python src/generar_diccionario.py` | `informe/anexo_C_diccionario.tex` |

`run.py` no corre los dos últimos, porque modifican archivos del informe que se mantienen a mano.

## Definiciones de la métrica

- **Precio medio por litro de exportación** = Σ monto neto en USD / Σ litros. Universo: ventas de exportación con fecha de factura en 2025, por semestre de la fecha de factura.
- **Litros** = cajas × 9,0 en ambos formatos (12×750 y 6×1500), según el maestro de costos.
- **Descomposición principal** (la de la sección E, por tier, con base S1): precio = Σ s₁·Δp, mezcla = Σ Δs·p₁, cruzado = Σ Δs·Δp. El método simétrico y los dos secuenciales se calculan como sensibilidad (`output/tablas/descomposicion_metodos.csv`).
- Las reglas de limpieza y cuántas filas afecta cada una están en `output/cobertura.md`.

## Fuentes

Los tres archivos de la viña son los entregados para el grupo 2 en el repositorio del curso. La cuarta fuente es la API del dólar observado de mindicador.cl. La cadena consulta `/api/dolar/2025` (facturas) y `/api/dolar/2026` (facturas de 2026 y fechas de cobranza que caen en 2026). `datos/raw/dolar_2025.json` y `dolar_2026.json` son respaldos de esa API, para poder reproducir los resultados aunque no responda.
