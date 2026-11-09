# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Importa una transcripción existente (.vtt o .srt) al formato de procesar-reunion.

Sirve para transcripciones que ya traen el nombre de quien habla (Teams, Zoom, Meet, etc.):
  - WebVTT con etiquetas de voz:   <v Ana López>texto</v>      (Teams)
  - Prefijo "Nombre: texto"        en cada subtítulo            (Zoom y otros)
Si no hay hablantes, se importa solo el texto con sus tiempos.

Uso: uv run importar_transcripcion.py <archivo.vtt|.srt> --salida <carpeta>
Genera transcripcion.json, transcripcion.txt y transcripcion.srt.
"""
import argparse
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from comun import configurar_consola, escribir_transcripcion

TIEMPO = r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})"
LINEA_TIEMPO = re.compile(rf"{TIEMPO}\s*-->\s*{TIEMPO}")
VOZ = re.compile(r"<v(?:\.[^ >]+)?\s+([^>]+)>")
ETIQUETA = re.compile(r"</?[^>]+>")
PREFIJO = re.compile(r"^([^:\n]{2,40}):\s+(\S.*)$")


def segundos(h, m, s, ms):
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def leer_cues(texto):
    cues = []
    for bloque in re.split(r"\n\s*\n", texto.replace("\r\n", "\n").strip()):
        lineas = [l for l in bloque.split("\n") if l.strip()]
        idx = next((i for i, l in enumerate(lineas) if LINEA_TIEMPO.search(l)), None)
        if idx is None:
            continue  # cabecera WEBVTT, NOTE, STYLE...
        g = LINEA_TIEMPO.search(lineas[idx]).groups()
        cuerpo = " ".join(lineas[idx + 1:]).strip()
        voz = VOZ.search(cuerpo)
        hablante = voz.group(1).strip() if voz else None
        cuerpo = re.sub(r"\s+", " ", ETIQUETA.sub("", cuerpo)).strip()
        if cuerpo:
            cues.append({"inicio": round(segundos(*g[:4]), 2), "fin": round(segundos(*g[4:]), 2),
                         "texto": cuerpo, "hablante": hablante})
    return cues


def aplicar_prefijos(cues):
    """Detecta 'Nombre: texto' solo si es un patrón consistente (evita confundir 'Nota: ...')."""
    if any(c["hablante"] for c in cues):
        return cues
    coincidencias = [PREFIJO.match(c["texto"]) for c in cues]
    con_prefijo = [m for m in coincidencias if m]
    nombres = Counter(m.group(1).strip() for m in con_prefijo)
    if len(con_prefijo) < 0.5 * len(cues) or not 0 < len(nombres) <= 25:
        return cues
    for c, m in zip(cues, coincidencias):
        if m:
            c["hablante"], c["texto"] = m.group(1).strip(), m.group(2).strip()
    return cues


def main():
    configurar_consola()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("archivo")
    p.add_argument("--salida", required=True)
    a = p.parse_args()

    archivo = Path(a.archivo)
    cues = aplicar_prefijos(leer_cues(archivo.read_text(encoding="utf-8-sig")))
    if not cues:
        raise SystemExit(f"No se encontraron subtítulos con tiempos en {archivo.name}.")
    meta = {
        "fuente": "importada",
        "archivo": str(archivo.resolve()),
        "duracion": max(c["fin"] for c in cues),
        "generado": datetime.now().isoformat(timespec="seconds"),
    }
    salida = escribir_transcripcion(a.salida, cues, meta)
    hablantes = sorted({c["hablante"] for c in cues if c["hablante"]})
    print(f"{len(cues)} segmentos importados; hablantes: {', '.join(hablantes) or '(ninguno)'} -> {salida}")


if __name__ == "__main__":
    main()
