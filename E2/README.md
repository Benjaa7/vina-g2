# Entrega 2 · Viña Vallehondo · Grupo 2

Misma pregunta de negocio que la E1: el precio promedio por litro de exportación subió 11,2 % entre el primer y el segundo semestre de 2025 (4,574 → 5,085 USD/L). ¿Fue por precio o por mezcla? En la E2 la cadena corre en **Databricks Free Edition**, con capas bronce, plata y oro en Unity Catalog, pruebas de calidad antes de publicar, una definición única de la métrica (metric view) y un tablero AI/BI.

## Cómo correrlo de cero (un solo paso)

1. Entrar a un workspace de Databricks Free Edition (sirve uno recién creado).
2. **Workspace → Create → Git folder** con la URL de este repositorio.
3. Abrir `E2/correr_e2` dentro de la carpeta Git y apretar **Run all**.

El notebook crea (o actualiza) el job `vallehondo_e2` con los ocho pasos de la cadena, lo ejecuta en cómputo serverless, muestra las pruebas de calidad y las cifras del informe y, al final, publica el tablero e imprime su enlace. No hay que instalar nada ni configurar credenciales: las fuentes van en el repositorio (`E2/datos/raw/`) y el código se lee desde la carpeta Git.

**Tiempo:** unos 6 minutos (5,5 el job y medio minuto publicar el tablero), medidos en una corrida de cero sobre un catálogo vacío. En una cuenta nueva la primera corrida tarda más: el 17 de noviembre, en un workspace recién creado con otra cuenta, el job esperó unos 6 minutos su primer cómputo serverless y la corrida completa demoró unos 14 (los pasos, 6,2 minutos).

**Si la ventana «Create Git folder» se queda cargando:** en esa misma prueba quedó girando más de 10 minutos sin crear la carpeta. La creamos con la misma URL desde la API (`POST /api/2.0/repos` con `{"url": "https://github.com/Benjaa7/vina-g2", "provider": "gitHub", "path": "/Users/<su correo>/vina-g2"}`), o con la CLI: `databricks repos create https://github.com/Benjaa7/vina-g2 gitHub --path /Users/<su correo>/vina-g2`. Después se sigue igual, desde el paso 3.

**Qué se espera ver al final:**

- Los ocho pasos en `SUCCESS`.
- 15 de 15 pruebas de calidad en `pasa`.
- Las cifras del informe: 4,574 y 5,085 USD/L, alza de 11,2 %, mezcla 107,9 % y precio −6,9 % del alza; en pesos, +10,1 % al dólar de la factura y +6,3 % al de la cobranza estimada; un punto de gran reserva vale 353 MM CLP de margen bruto al año.
- El enlace **Abrir el tablero publicado**. El tablero queda en la carpeta `vallehondo_e2` de quien corrió el notebook; la copia del repositorio no se modifica.

**Alternativa con la CLI** (desde la carpeta `E2/`): `databricks bundle deploy && databricks bundle run vallehondo_e2`. El bundle (`databricks.yml`) despliega el mismo job y el tablero.

### Parámetros opcionales del notebook

| Parámetro | Por defecto | Para qué |
|---|---|---|
| `catalogo` | `vallehondo` | catálogo de Unity Catalog donde se crean las capas |
| `probar_falla_api` | `no` | con `si`, la cadena llama a una URL inexistente de la API del dólar para comprobar que usa el respaldo con fecha y lo deja registrado |

Correr el notebook dos veces da el mismo oro: todas las tablas se recargan completas, y la prueba de idempotencia compara la corrida nueva con el oro ya publicado.

## La cadena

| Paso | Qué hace | Escribe en |
|---|---|---|
| `00_preparar` | crea catálogo, esquemas y volúmenes; copia las fuentes del repositorio al volumen de llegada con su huella (md5) | `bronce.llegada`, `ops.archivos_llegada` |
| `01_bronce` | SQLite, CSV y JSON tal como llegan, como tablas Delta, con la corrida y el archivo de origen | `bronce.*` |
| `02_dolar` | dólar observado desde la API de mindicador.cl; si falla, el respaldo con su fecha de descarga | `bronce.dolar_observado`, `ops.fuente_dolar` |
| `03_plata` | las reglas de limpieza de la E1; cada corrección queda marcada por fila | `plata.*`, `ops.reglas_limpieza` |
| `04_oro` | modelo estrella y tabla de escenarios, en borrador | `oro_borrador.*` |
| `05_pruebas` | 15 pruebas de calidad; si falla una bloqueante, el job se detiene y el oro publicado no cambia | `ops.dq_resultados` |
| `06_publicar` | publica el oro, la metric view `oro.mv_vallehondo` (definición única) y las vistas | `oro.*` |
| `07_cifras` | cada cifra del informe, leída de la definición única | `ops.cifras_informe`, volumen `ops.salidas` |

Cada paso deja su registro en `ops.run_log` (inicio, fin, estado, filas).

## Estructura

```
E2/
├── correr_e2.py            notebook de un solo paso: crea y corre el job, publica el tablero
├── databricks.yml          el mismo job y el tablero como bundle (alternativa con la CLI)
├── datos/raw/              las fuentes del caso y el respaldo del dólar (respaldo_dolar.json dice cuándo se descargó)
├── src/
│   ├── 00_preparar.py … 07_cifras.py    los ocho pasos del job (notebooks de Databricks)
│   └── lib/
│       ├── comun.py                     parámetros, escritura de tablas y registro de corridas y pruebas
│       ├── limpiar.py                   reglas de limpieza (las de la E1)
│       ├── integrar.py                  modelo estrella (el de la E1, con las columnas para los escenarios)
│       └── esquema.py                   definición de cada tabla y columna del modelo
├── tablero/
│   ├── generar_tablero.py              genera el tablero como código
│   └── vallehondo.lvdash.json          el tablero AI/BI (Databricks lo reconoce como tablero en la carpeta Git)
└── output/
    └── cifras.md                        cifras de la última corrida de desarrollo (la corrida real las escribe en el volumen ops.salidas)
```

## El tablero

Dos páginas:

- **Respuesta:** el alza del precio por litro en porcentaje, el precio de cada semestre, cuánto del alza explica la mezcla, la participación de gran reserva y el valor en pesos (MM CLP) de un punto de mezcla; un gráfico con lo que aportan mezcla, precio y cruzado junto al alza total; la participación y el precio de cada tier; y la lectura por mercado, que dice si es recomendación o hipótesis y por qué.
- **Definición y calidad:** una tabla que compara USD y las tres fechas del dólar lado a lado (precio por litro, alza y parte de la mezcla), el precio por tier y la gran reserva mes a mes leídos directo de la metric view, las fórmulas y las pruebas de la última corrida.

Los filtros permiten elegir la moneda y la fecha del dólar, las correcciones de datos, los litros por caja magnum y el mercado. Cada filtro siempre tiene un valor, así que una cifra nunca mezcla escenarios. El pie de cada página muestra la última actualización, las pruebas en verde, la fuente del dólar y el dueño del dato.

Para cambiar el tablero se edita `tablero/generar_tablero.py` y se corre `python tablero/generar_tablero.py`; no se edita el JSON a mano.
