# Entrega 1 · Viña Vallehondo · Grupo 2

Pregunta de negocio que responde esta entrega (pregunta 2 del caso): el precio promedio por litro de exportación que subió en 2025, ¿se explica por alzas de precio o por una mayor proporción de gran reserva?

## Estructura

```
E1/
├── datos/raw/          las cuatro fuentes del caso
│   ├── origen_vina.sqlite            base comercial (ventas, clientes, mercados, zonas, cepas, monedas, vendedores)
│   ├── origen_costos_productos.csv   costos por producto y añada (latin-1, separador ;)
│   ├── origen_embarques.json         embarques de exportación
│   └── dolar_2025.json               respaldo de https://mindicador.cl/api/dolar/2025, descargado el 2 de octubre de 2026
├── src/                código
│   ├── esquema.py                    definición del modelo estrella (tablas, columnas, origen y regla)
│   ├── diagrama_modelo.py            dibuja el modelo estrella desde esquema.py
│   └── generar_diccionario.py        escribe el diccionario de datos del anexo desde esquema.py
├── output/figuras/     figuras generadas por el código
└── informe/            fuentes LaTeX del informe y anexos
    └── anexos/                       acta de la reunión del 4 de septiembre
```

## Requisitos

- Python 3.11 o superior.
- Dependencias: `pip install -r requirements.txt`

## Cómo reproducir

Todos los comandos se corren desde la carpeta `E1/`.

| Paso | Comando | Qué produce | Tiempo |
|---|---|---|---|
| Diagrama del modelo | `python src/diagrama_modelo.py` | `output/figuras/modelo_estrella.pdf` y `.png` | segundos |
| Diccionario de datos | `python src/generar_diccionario.py` | `informe/anexo_C_diccionario.tex` | segundos |

<!-- PENDIENTE (componente B): agregar el comando que corre la cadena completa (lectura de las cuatro
     fuentes, limpieza, construcción de la estrella, métrica y figuras), cuánto demora y qué cifras
     se espera ver al final. -->

## Fuentes

Los tres archivos de la viña son los entregados para el grupo 2 en el repositorio del curso. La cuarta fuente es la API del dólar observado de mindicador.cl. `datos/raw/dolar_2025.json` es un respaldo de esa API, para poder reproducir los resultados aunque no responda.
