# Databricks notebook source
# MAGIC %md
# MAGIC # Correr la E2 de cero · Viña Vallehondo, Grupo 2
# MAGIC **Un solo paso:** abre este notebook desde la copia del repositorio en tu workspace y aprieta **Run all**.
# MAGIC
# MAGIC Crea (o actualiza) el job `vallehondo_e2` con los ocho pasos de la cadena, lo ejecuta, espera a que termine
# MAGIC e imprime el resultado de las pruebas de calidad y las cifras del informe; al final publica el tablero y deja
# MAGIC su enlace. Tarda unos 6 minutos con cómputo serverless.
# MAGIC
# MAGIC | Paso | Qué hace | Capa |
# MAGIC |---|---|---|
# MAGIC | 00_preparar | catálogo, esquemas, volúmenes; copia las fuentes del repo al volumen de llegada | — |
# MAGIC | 01_bronce | SQLite, CSV y JSON tal como llegan, como tablas Delta | bronce |
# MAGIC | 02_dolar | API de mindicador.cl; si falla, respaldo con fecha | bronce |
# MAGIC | 03_plata | reglas de limpieza de la E1, cada corrección marcada por fila | plata |
# MAGIC | 04_oro | modelo estrella y tabla de escenarios, en borrador | oro_borrador |
# MAGIC | 05_pruebas | pruebas de calidad; si una bloqueante falla, el job se detiene | ops |
# MAGIC | 06_publicar | publica el oro, la metric view (definición única) y las vistas | oro |
# MAGIC | 07_cifras | cifras del informe desde la definición única | ops |
# MAGIC
# MAGIC Parámetros opcionales: `catalogo` (por defecto `vallehondo`) y `probar_falla_api` (`si` para correr con una
# MAGIC URL incorrecta de la API del dólar y comprobar que se usa el respaldo).

# COMMAND ----------

import os, json
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import jobs

dbutils.widgets.text("catalogo", "vallehondo")
dbutils.widgets.dropdown("probar_falla_api", "no", ["no", "si"])
CATALOGO = dbutils.widgets.get("catalogo").strip() or "vallehondo"
URL_DOLAR = ("https://mindicador.cl/api/no-existe/{anio}" if dbutils.widgets.get("probar_falla_api") == "si"
             else "https://mindicador.cl/api/dolar/{anio}")

w = WorkspaceClient()
AQUI = os.getcwd()                                   # /Workspace/.../vina-g2/E2
BASE = AQUI[len("/Workspace"):] if AQUI.startswith("/Workspace") else AQUI
PASOS = ["00_preparar", "01_bronce", "02_dolar", "03_plata", "04_oro", "05_pruebas", "06_publicar", "07_cifras"]
NOMBRE_JOB = "vallehondo_e2"

tareas = [jobs.Task(task_key=p,
                    notebook_task=jobs.NotebookTask(notebook_path=f"{BASE}/src/{p}", source=jobs.Source.WORKSPACE),
                    depends_on=[jobs.TaskDependency(task_key=PASOS[i - 1])] if i else None)
          for i, p in enumerate(PASOS)]
parametros = [jobs.JobParameterDefinition(name="catalogo", default=CATALOGO),
              jobs.JobParameterDefinition(name="run_id", default="{{job.run_id}}"),
              jobs.JobParameterDefinition(name="dir_raw", default=f"{AQUI}/datos/raw"),
              jobs.JobParameterDefinition(name="dir_lib", default=f"{AQUI}/src/lib"),
              jobs.JobParameterDefinition(name="url_dolar", default="https://mindicador.cl/api/dolar/{anio}")]
ajustes = jobs.JobSettings(name=NOMBRE_JOB, tasks=tareas, parameters=parametros, max_concurrent_runs=1,
                           description="Cadena de la E2 (Viña Vallehondo, Grupo 2): bronce → plata → oro, con pruebas antes de publicar.")
existente = [j for j in w.jobs.list(name=NOMBRE_JOB)]
if existente:
    job_id = existente[0].job_id
    w.jobs.reset(job_id=job_id, new_settings=ajustes)
else:
    job_id = w.jobs.create(**ajustes.as_shallow_dict()).job_id
print(f"Job {NOMBRE_JOB}: {job_id}")

# COMMAND ----------

import time
t0 = time.time()
corrida = w.jobs.run_now(job_id=job_id, job_parameters={"url_dolar": URL_DOLAR}).result()
print(f"Terminó en {time.time() - t0:.0f} s con estado {corrida.state.result_state}")
for t in corrida.tasks:
    print(f"  {t.task_key:12s} {t.state.result_state}")
RUN_ID = str(corrida.run_id)

# COMMAND ----------

display(spark.sql(f"""SELECT capa, prueba, severidad, resultado, filas_fallan, accion, detalle
                      FROM {CATALOGO}.ops.dq_resultados WHERE run_id = '{RUN_ID}' ORDER BY capa, prueba"""))

# COMMAND ----------

display(spark.sql(f"SELECT seccion, cifra, round(valor, 3) AS valor, unidad FROM {CATALOGO}.ops.cifras_informe"))
display(spark.sql(f"SELECT * FROM {CATALOGO}.oro.v_estado_corrida"))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Tablero
# MAGIC El tablero está versionado en el repositorio: `tablero/vallehondo.lvdash.json`, generado por
# MAGIC `tablero/generar_tablero.py`. Esta celda lo copia a la carpeta `vallehondo_e2` de quien corre el notebook (así la
# MAGIC copia del repositorio no se modifica), le asigna el SQL warehouse y el catálogo, lo publica e imprime el enlace.

# COMMAND ----------

import re

RUTA_TABLERO = f"{BASE}/tablero/vallehondo.lvdash.json"
almacenes = list(w.warehouses.list())
assert almacenes, "No hay SQL warehouse en el workspace (Free Edition trae uno: Serverless Starter Warehouse)."
WAREHOUSE = next((a.id for a in almacenes if "RUNNING" in str(a.state)), almacenes[0].id)

estado = w.api_client.do("GET", "/api/2.0/workspace/get-status", query={"path": RUTA_TABLERO})
assert estado.get("object_type") == "DASHBOARD", f"{RUTA_TABLERO} no se reconoció como tablero: {estado}"
fuente = w.api_client.do("GET", f"/api/2.0/lakeview/dashboards/{estado.get('resource_id') or estado['object_id']}")
serializado = re.sub(r'"catalog"\s*:\s*"[^"]*"', f'"catalog": "{CATALOGO}"', fuente["serialized_dashboard"])

NOMBRE_TABLERO = "Vallehondo · Precio por litro de exportación"
CARPETA = f"/Users/{w.current_user.me().user_name}/vallehondo_e2"
w.workspace.mkdirs(CARPETA)
try:
    previo = w.api_client.do("GET", "/api/2.0/workspace/get-status",
                             query={"path": f"{CARPETA}/{NOMBRE_TABLERO}.lvdash.json"})
except Exception:
    previo = None
if previo:
    TABLERO_ID = previo.get("resource_id") or str(previo["object_id"])
    w.api_client.do("PATCH", f"/api/2.0/lakeview/dashboards/{TABLERO_ID}",
                    body={"serialized_dashboard": serializado, "warehouse_id": WAREHOUSE})
else:
    TABLERO_ID = w.api_client.do("POST", "/api/2.0/lakeview/dashboards",
                                 body={"display_name": NOMBRE_TABLERO, "parent_path": CARPETA,
                                       "serialized_dashboard": serializado, "warehouse_id": WAREHOUSE})["dashboard_id"]
w.api_client.do("POST", f"/api/2.0/lakeview/dashboards/{TABLERO_ID}/published",
                body={"embed_credentials": True, "warehouse_id": WAREHOUSE})
URL_TABLERO = f"{w.config.host.rstrip('/')}/dashboardsv3/{TABLERO_ID}/published"
print(URL_TABLERO)
displayHTML(f'<p style="font-size:16px"><a href="{URL_TABLERO}" target="_blank">Abrir el tablero publicado</a></p>')
