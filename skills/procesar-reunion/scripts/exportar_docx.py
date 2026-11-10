# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "python-docx>=1.1",
# ]
# ///
"""Exporta la minuta a Word: <salida>/minuta.docx.

Uso: uv run exportar_docx.py <salida>

Sale de minuta.json (validada y verificada como en `minutas.py minuta`), sin enlaces a archivos
locales: los minutos y las capturas van como texto. Lo normal es correrlo con `minutas.py exportar`.
"""
import argparse
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Pt, RGBColor

from comun import configurar_consola
from exportar import bloques, inline, markdown_para_compartir, plano


def agregar_texto(parrafo, texto):
    for t, estilos in inline(texto):
        run = parrafo.add_run(t)
        run.bold = "b" in estilos or None
        run.italic = "i" in estilos or None
        if "code" in estilos:
            run.font.name = "Consolas"
            run.font.size = Pt(9.5)


def documento(markdown, titulo):
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    doc.core_properties.title = titulo
    doc.core_properties.author = "minutas-video"
    doc.core_properties.comments = ""
    for b in bloques(markdown):
        t = b["tipo"]
        if t in ("h1", "h2", "h3"):
            h = doc.add_heading(level={"h1": 0, "h2": 1, "h3": 2}[t])
            agregar_texto(h, b["texto"])
        elif t == "p":
            p = doc.add_paragraph()
            for i, linea in enumerate(b["lineas"]):
                if i:
                    p.add_run().add_break()
                agregar_texto(p, linea)
        elif t == "cita":
            p = doc.add_paragraph(style="Intense Quote")
            agregar_texto(p, b["texto"])
        elif t == "lista":
            for item in b["items"]:
                agregar_texto(doc.add_paragraph(style="List Bullet"), item)
        elif t == "tabla":
            filas = b["filas"]
            tabla = doc.add_table(rows=len(filas), cols=len(filas[0]))
            tabla.style = "Table Grid"
            tabla.alignment = WD_TABLE_ALIGNMENT.LEFT
            for i, fila in enumerate(filas):
                for j, valor in enumerate(fila):
                    celda = tabla.cell(i, j)
                    celda.text = ""
                    parrafo = celda.paragraphs[0]
                    if i == 0:
                        parrafo.add_run(plano(valor)).bold = True
                    else:
                        agregar_texto(parrafo, valor)
                    for run in parrafo.runs:
                        run.font.size = Pt(9.5)
            doc.add_paragraph()
        elif t == "hr":
            p = doc.add_paragraph()
            p.add_run("—" * 3).font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)
    return doc


def main():
    configurar_consola()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("salida")
    a = p.parse_args()
    salida = Path(a.salida)
    preparada = markdown_para_compartir(salida)
    if isinstance(preparada, dict):
        print("minuta.json tiene errores: " + "; ".join(preparada["errores"]))
        sys.exit(2)
    md, m, _ = preparada
    destino = salida / "minuta.docx"
    documento(md, f"Minuta · {m['titulo']}").save(destino)
    print(f"Word: {destino}")


if __name__ == "__main__":
    main()
