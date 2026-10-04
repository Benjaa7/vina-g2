# -*- coding: utf-8 -*-
"""Definición del modelo dimensional (estrella) del Grupo 2, caso Viña Vallehondo.

Es la fuente única del modelo: de aquí salen el diagrama (diagrama_modelo.py),
el diccionario de datos del anexo (generar_diccionario.py) y, en el componente B,
los nombres de tablas y columnas con que se construye la estrella.

Cada columna es una tupla:
    (nombre, rol, aditividad, descripción, origen y regla, va_en_diagrama)

rol:        llave | degenerada | medida | contexto | indicador | atributo
aditividad: aditiva | no aditiva | — (no aplica)
"""

PROCESO = "La venta: cada vez que se factura una línea de vino."

GRANO = ("Una fila es una línea de venta facturada: un producto de una añada, "
         "vendido a un cliente en una fecha.")

TABLAS = {
    "fact_venta": {
        "tipo": "hecho",
        "titulo": "HECHO · Venta",
        "subtitulo": "transaccional",
        "descripcion": "Hecho transaccional. Una fila por línea de venta facturada.",
        "columnas": [
            ("venta_id", "degenerada", "—",
             "Número de la línea en el ERP.",
             "ventas.venta_id; deduplicado tras normalizar formatos", True),
            ("fecha_key", "llave", "—",
             "Fecha de factura.",
             "ventas.fecha, leída en sus 4 formatos", True),
            ("producto_anada_key", "llave", "—",
             "Producto y añada vendidos.",
             "ventas.producto_id + ventas.anada", True),
            ("cliente_key", "llave", "—",
             "Cliente que compra.",
             "ventas.cliente_id", True),
            ("mercado_key", "llave", "—",
             "Mercado de destino.",
             "ventas.mercado_id (coincide con clientes.mercado_id)", True),
            ("cajas", "medida", "aditiva",
             "Cajas vendidas; negativas si la línea es merma.",
             "ventas.cajas; si vienen en botellas (12 o 10 veces las cajas del "
             "embarque), se dividen por el factor", True),
            ("litros", "medida", "aditiva",
             "Litros vendidos.",
             "cajas × dim_producto.litros_por_caja", True),
            ("monto_bruto_clp", "medida", "aditiva",
             "Monto antes de descuento, en pesos.",
             "cajas × precio unitario; si la moneda es USD, × tipo_cambio", False),
            ("monto_bruto_usd", "medida", "aditiva",
             "Monto antes de descuento, en dólares.",
             "cajas × precio unitario; si la moneda es CLP, ÷ tipo_cambio", False),
            ("monto_neto_clp", "medida", "aditiva",
             "Ingreso neto de descuento, en pesos.",
             "cajas × precio unitario × (1 − descuento), convertido con "
             "tipo_cambio", True),
            ("monto_neto_usd", "medida", "aditiva",
             "Ingreso neto de descuento, en dólares.",
             "cajas × precio unitario × (1 − descuento), convertido con "
             "tipo_cambio", True),
            ("costo_total_clp", "medida", "aditiva",
             "Costo de producción de lo vendido, en pesos.",
             "|cajas| × dim_producto.costo_caja_clp; en la merma el costo "
             "no se reversa", True),
            ("tipo_cambio", "contexto", "no aditiva",
             "Dólar observado usado para convertir la línea.",
             "API mindicador.cl, fecha de factura; fines de semana y feriados "
             "con el último día hábil previo", True),
            ("es_merma", "indicador", "aditiva",
             "1 si la línea es merma (cajas negativas).",
             "cajas < 0; merma según la contraparte (4 sep)", False),
            ("monto_recalculado", "indicador", "aditiva",
             "1 si el monto registrado no cuadraba y se recalculó.",
             "|monto registrado − calculado| > 0,5 %", False),
            ("cajas_corregidas", "indicador", "aditiva",
             "1 si las cajas venían en botellas.",
             "cruce con origen_embarques.json", False),
            ("moneda_imputada", "indicador", "aditiva",
             "1 si la moneda venía vacía.",
             "ventas.moneda_id nulo; se imputa por mercado", False),
        ],
    },
    "dim_tiempo": {
        "tipo": "dimension",
        "titulo": "Tiempo",
        "subtitulo": "una fila por día",
        "descripcion": "Una fila por día calendario de 2025.",
        "columnas": [
            ("fecha_key", "llave", "—", "Llave AAAAMMDD.", "generada", False),
            ("fecha", "atributo", "—", "Fecha.", "calendario", True),
            ("dia_semana", "atributo", "—", "Lunes a domingo.", "calendario", False),
            ("semana", "atributo", "—", "Semana del año.", "calendario", False),
            ("mes", "atributo", "—", "Mes (número y nombre).", "calendario", True),
            ("trimestre", "atributo", "—", "Trimestre.", "calendario", True),
            ("semestre", "atributo", "—", "Primer o segundo semestre.", "calendario", True),
            ("anio", "atributo", "—", "Año.", "calendario", True),
            ("es_dia_habil", "atributo", "—",
             "1 si es día hábil.",
             "1 si la API del dólar publica valor ese día", True),
            ("es_feriado", "atributo", "—",
             "1 si es feriado.",
             "día de semana sin valor publicado en la API", False),
        ],
    },
    "dim_producto": {
        "tipo": "dimension",
        "titulo": "Producto",
        "subtitulo": "una fila por producto y añada",
        "descripcion": "Una fila por producto y añada (24 productos × 4 añadas = 96 filas).",
        "columnas": [
            ("producto_anada_key", "llave", "—", "Llave producto-añada.", "generada", False),
            ("producto", "atributo", "—", "Nombre del vino.",
             "origen_costos_productos.csv: producto", True),
            ("cepa", "atributo", "—",
             "Cepa, con el nombre oficial del catálogo del ERP.",
             "CSV: cepa, normalizada desde sus alias y conformada a "
             "origen_vina.sqlite: cepas.cepa; desempate en la bitácora", True),
            ("tipo_vino", "atributo", "—", "Tinto o blanco.",
             "origen_vina.sqlite: cepas.tipo", True),
            ("tier", "atributo", "—", "Varietal, Reserva o Gran Reserva.",
             "CSV: tier", True),
            ("formato", "atributo", "—", "12 × 750 ml o 6 × 1500 ml.",
             "CSV: formato", True),
            ("litros_por_caja", "atributo", "—",
             "Litros que rinde una caja: la definición de caja a litro.",
             "CSV: litros_por_caja (9,0 para ambos formatos)", True),
            ("anada", "atributo", "—", "Año de cosecha.", "CSV: anada", True),
            ("costo_caja_clp", "atributo", "—",
             "Costo unitario de producción por caja.",
             "CSV: costo_caja_clp; si falta, regla exacta (tier, añada)", True),
            ("costo_imputado", "atributo", "—",
             "1 si el costo se imputó por regla.", "generado", False),
            ("activo", "atributo", "—", "Si el producto sigue en catálogo.",
             "CSV: activo (si/SI/Sí/1 = verdadero)", False),
        ],
    },
    "dim_cliente": {
        "tipo": "dimension",
        "titulo": "Cliente",
        "subtitulo": "distribuidor o importador",
        "descripcion": "Una fila por cliente (distribuidor o importador).",
        "columnas": [
            ("cliente_key", "llave", "—", "Llave del cliente.", "generada", False),
            ("cliente_id", "atributo", "—", "Código del ERP.",
             "origen_vina.sqlite: clientes.cliente_id", True),
            ("nombre", "atributo", "—", "Razón social.",
             "clientes.nombre", True),
            ("tipo", "atributo", "—", "Distribuidor o importador.",
             "clientes.tipo", True),
        ],
    },
    "dim_mercado": {
        "tipo": "dimension",
        "titulo": "Mercado",
        "subtitulo": "geografía: país y zona",
        "descripcion": "Una fila por mercado de destino. País y zona son niveles de una misma jerarquía.",
        "columnas": [
            ("mercado_key", "llave", "—", "Llave del mercado.", "generada", False),
            ("pais", "atributo", "—", "País de destino.",
             "origen_vina.sqlite: mercados.pais", True),
            ("zona", "atributo", "—", "Zona comercial.",
             "mercados.zona_id → zonas.zona; zona 8 inexistente (Corea del "
             "Sur) se asigna a Asia", True),
            ("canal", "atributo", "—", "Nacional o Exportación.",
             "mercados.canal", True),
            ("hemisferio", "atributo", "—", "Norte o sur.",
             "derivado del país (Chile y Brasil: sur)", True),
            ("moneda_facturacion", "atributo", "—", "CLP o USD.",
             "monedas.moneda; en los datos la moneda queda determinada por el "
             "mercado (Chile CLP, resto USD); el ETL verifica que no haya "
             "excepciones", True),
        ],
    },
}

# Lo que quedó fuera del modelo y por qué (se usa en el informe y en el README).
FUERA_DEL_MODELO = [
    ("Embarque (origen_embarques.json)",
     "Es otro proceso de negocio, con su propio evento y su propio grano (un "
     "embarque agrupa varias líneas). Su vínculo con la venta no es confiable "
     "y la pregunta no lo necesita. En la cadena se usa para corregir las cajas "
     "cargadas en botellas, y queda como siguiente estrella en la matriz de bus."),
    ("Vendedor",
     "Redundante: los 5 vendedores corresponden uno a uno a las 5 zonas."),
    ("Columna zona de ventas",
     "Mal poblada; la zona se toma de mercados → zonas."),
    ("RUT del cliente",
     "No aporta a la pregunta; se excluye por minimización de datos personales."),
    ("Flete, seguro, despacho y aranceles",
     "No están en ninguna fuente."),
    ("Cobranza",
     "Es otro proceso y no hay fechas de pago, solo la política de 60 y 90 días."),
    ("Tramo de dólar a euro",
     "No es observable en las fuentes."),
    ("Precio unitario, descuento %, precio por litro y margen",
     "No son aditivos: se calculan como razón de sumas, no se guardan."),
]
