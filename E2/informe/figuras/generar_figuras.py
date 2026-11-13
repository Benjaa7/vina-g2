"""Figuras y diccionario del informe de la E2 (secciones B y C), generados desde el código.

- modelo_estrella.pdf: el diagrama de la E1 (E1/src/diagrama_modelo.py) dibujado con el esquema de la E2.
- arquitectura.pdf y linaje.pdf: desde arquitectura.dot y linaje.dot (Graphviz).
- ../anexo_C_diccionario.tex: el diccionario de datos (E1/src/generar_diccionario.py) con el esquema de la E2.

Uso, desde cualquier carpeta:  python E2/informe/figuras/generar_figuras.py   (requiere matplotlib y Graphviz)
"""
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
E2 = AQUI.parents[1]
# primero el esquema de la E2, después el script de dibujo de la E1
sys.path[:0] = [str(E2 / "src" / "lib"), str(E2.parent / "E1" / "src")]
import diagrama_modelo  # noqa: E402

diagrama_modelo.SALIDA = AQUI
diagrama_modelo.main()

import generar_diccionario  # noqa: E402

generar_diccionario.SALIDA = AQUI.parent / "anexo_C_diccionario.tex"
generar_diccionario.main()
dic = generar_diccionario.SALIDA.read_text(encoding="utf-8").split("\n", 1)
generar_diccionario.SALIDA.write_text("% Generado por E2/informe/figuras/generar_figuras.py desde E2/src/lib/esquema.py. "
                                      "No editar a mano.\n" + dic[1], encoding="utf-8")

for nombre in ("arquitectura", "linaje"):
    subprocess.run(["dot", "-Tpdf", str(AQUI / f"{nombre}.dot"), "-o", str(AQUI / f"{nombre}.pdf")], check=True)
    subprocess.run(["dot", "-Tpng", "-Gdpi=200", str(AQUI / f"{nombre}.dot"), "-o", str(AQUI / f"{nombre}.png")],
                   check=True)
    print("Diagrama guardado:", AQUI / f"{nombre}.pdf")
