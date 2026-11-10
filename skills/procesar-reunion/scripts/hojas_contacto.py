# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "av>=12",
#   "pillow>=10.1",
# ]
# ///
"""Hojas de miniaturas para revisar muchas imágenes con poco contexto (12 por hoja, con su número y tiempo).

  uv run hojas_contacto.py capturas <salida> [--destino <carpeta>]
      Hojas de las capturas de <salida>/capturas, sin las que repiten una pantalla anterior
      ("igual_a" en capturas.json). Por defecto escribe en <salida>/_revision/.
  uv run hojas_contacto.py tiempos <video> --destino <carpeta> <seg> [<seg> ...]
      Hoja con cuadros del video en esos segundos (para revisar tramos sin capturas).

Imprime la ruta de cada hoja generada.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from comun import configurar_consola, hms, leer_capturas

COLS, FILAS, TW, TH = 3, 4, 640, 360


def hojas(items, destino, prefijo):
    fuente = ImageFont.load_default(size=26)
    destino.mkdir(parents=True, exist_ok=True)
    por_hoja = COLS * FILAS
    for h in range(0, len(items), por_hoja):
        grupo = items[h:h + por_hoja]
        filas = (len(grupo) + COLS - 1) // COLS
        lienzo = Image.new("RGB", (COLS * TW, filas * TH), "white")
        d = ImageDraw.Draw(lienzo)
        for i, (etiqueta, img) in enumerate(grupo):
            x, y = (i % COLS) * TW, (i // COLS) * TH
            lienzo.paste(img.convert("RGB").resize((TW, TH)), (x, y))
            d.rectangle([x, y, x + 280, y + 34], fill="black")
            d.text((x + 6, y + 3), etiqueta, fill="yellow", font=fuente)
            d.rectangle([x, y, x + TW - 1, y + TH - 1], outline="red", width=2)
        ruta = destino / f"{prefijo}_{h // por_hoja + 1:02}.jpg"
        lienzo.save(ruta, quality=80)
        print(ruta)


def main():
    configurar_consola()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="modo", required=True)
    pc = sub.add_parser("capturas")
    pc.add_argument("salida")
    pc.add_argument("--destino")
    pt = sub.add_parser("tiempos")
    pt.add_argument("video")
    pt.add_argument("--destino", required=True)
    pt.add_argument("segundos", nargs="+", type=float)
    a = p.parse_args()

    if a.modo == "capturas":
        salida = Path(a.salida)
        caps = sorted((salida / "capturas").glob("*.jpg"))
        if not caps:
            raise SystemExit("No hay capturas.")
        repetidas = {Path(c["archivo"]).name for c in leer_capturas(salida)[1] if "igual_a" in c}
        if repetidas:
            caps = [c for c in caps if c.name not in repetidas]
            print(f"Se omiten {len(repetidas)} capturas que repiten una pantalla anterior.")
        items = [(f"{c.stem[:4]}  {c.stem[5:].replace('-', ':')}", Image.open(c)) for c in caps]
        hojas(items, Path(a.destino) if a.destino else salida / "_revision", "hoja")
    else:
        import av
        items = []
        with av.open(a.video) as c:
            s = c.streams.video[0]
            for t in sorted(a.segundos):
                c.seek(int(t / s.time_base), stream=s, backward=True)
                for frame in c.decode(s):
                    if frame.time is not None and frame.time >= t:
                        items.append((f"video {hms(frame.time)}", frame.to_image()))
                        break
        hojas(items, Path(a.destino), "tiempos")


if __name__ == "__main__":
    main()
