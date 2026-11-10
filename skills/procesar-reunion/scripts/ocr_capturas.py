# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "rapidocr>=3.10",
#   "onnxruntime",
# ]
# ///
"""Lee el texto de cada captura (OCR): para buscarlo, citarlo y decidir qué capturas mirar.

Uso: uv run ocr_capturas.py <salida> [--idioma es]

Usa RapidOCR con el modelo multilingüe PP-OCRv6 que trae el propio paquete (no descarga modelos).
Corre en CPU: unos 4 s por captura de 1080p. Las capturas marcadas "igual_a" en capturas.json
reutilizan el texto de la original.

Escribe:
  <salida>/ocr.json      el texto de cada captura, línea por línea, con la confianza media
  <salida>/capturas.txt  por captura, solo las líneas que no estaban en la anterior (para leer rápido)
"""
import argparse
import importlib.metadata
import re
import time
from datetime import datetime
from pathlib import Path

from comun import Progreso, configurar_consola, escribir_json, hms, leer_capturas

# El modelo es multilingüe: en pantallas en español, los íconos a veces salen como caracteres chinos.
CJK = re.compile(r"[　-鿿가-힯＀-￯]")
IDIOMAS_CJK = {"zh", "ja", "ko", "ch", "chinese", "japanese", "korean"}


def limpiar(lineas, idioma):
    """Quita ruido: caracteres CJK si la reunión no es en esos idiomas y líneas sin al menos dos
    letras o dígitos (íconos, «×», «…», viñetas)."""
    limpias = []
    for texto in lineas:
        if idioma not in IDIOMAS_CJK:
            texto = CJK.sub("", texto)
        texto = " ".join(texto.split())
        if sum(ch.isalnum() for ch in texto) >= 2:
            limpias.append(texto)
    return limpias


def escribir_txt(destino, resultados):
    partes = [
        "Texto en pantalla de cada captura (OCR automático: puede confundir caracteres; confirma con la",
        "imagen los datos críticos, como números y folios). Por captura, solo las líneas nuevas respecto",
        "a la anterior; el texto completo está en ocr.json.",
        "",
    ]
    previas = set()
    for r in resultados:
        cabeza = f"[{hms(r['desde'])}] captura {r['n']:04}"
        lineas = r.get("lineas", [])
        if "error" in r:
            partes += [f"{cabeza} · no se pudo leer ({r['error']})", ""]
            continue
        if "igual_a" in r:
            partes += [f"{cabeza} · igual a la captura {r['igual_a']:04}", ""]
        else:
            nuevas = [x for x in lineas if x not in previas]
            if not lineas:
                partes += [f"{cabeza} · {r['archivo']} · sin texto", ""]
            elif not nuevas:
                partes += [f"{cabeza} · {r['archivo']} · sin texto nuevo ({len(lineas)} líneas iguales a la anterior)", ""]
            else:
                resumen = f"{len(lineas)} líneas" + (f", {len(nuevas)} nuevas" if len(nuevas) < len(lineas) else "")
                partes += [f"{cabeza} · {r['archivo']} · {resumen}", *nuevas, ""]
        previas = set(lineas)
    destino.write_text("\n".join(partes), encoding="utf-8")


def main():
    configurar_consola()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("salida")
    p.add_argument("--idioma", default="es", help="idioma de la reunión; solo sirve para filtrar ruido")
    a = p.parse_args()

    salida = Path(a.salida)
    for vieja in ("ocr.json", "capturas.txt"):  # si esta corrida falla, que no quede texto de otras capturas
        (salida / vieja).unlink(missing_ok=True)
    _, capturas = leer_capturas(salida)
    prog = Progreso("ocr", len(capturas))
    prog.fase("cargando el OCR")
    from rapidocr import RapidOCR  # tarda un par de segundos: después de anunciar la fase

    motor = RapidOCR(params={"Global.log_level": "error", "Global.use_cls": False})
    version = importlib.metadata.version("rapidocr")
    prog.fase("leyendo el texto de las capturas")

    t0 = time.time()
    resultados, por_n, total_lineas = [], {}, 0
    for i, c in enumerate(capturas, start=1):
        r = {"n": c["n"], "archivo": c["archivo"], "desde": c["desde"]}
        original = por_n.get(c.get("igual_a"))
        if original is not None and "error" not in original:
            r.update(igual_a=c["igual_a"], lineas=original["lineas"], confianza=original["confianza"])
        else:
            try:
                res = motor(str(salida / c["archivo"]))
                # Sin texto detectado, RapidOCR devuelve un resultado sin txts ni scores.
                textos = list(getattr(res, "txts", None) or [])
                confianzas = list(getattr(res, "scores", None) or [])
                r["lineas"] = limpiar(textos, a.idioma)
                r["confianza"] = round(sum(confianzas) / len(confianzas), 3) if confianzas else None
            except Exception as e:  # noqa: BLE001 — una imagen dañada no detiene las demás
                r["error"] = f"{type(e).__name__}: {e}"
        resultados.append(r)
        por_n[c["n"]] = r
        total_lineas += len(r.get("lineas", []))
        prog.avance(i, **{"líneas": total_lineas})

    escribir_json(salida / "ocr.json", {
        "meta": {"motor": f"RapidOCR {version} (PP-OCRv6, CPU)", "idioma": a.idioma,
                 "generado": datetime.now().isoformat(timespec="seconds"), "capturas": len(capturas),
                 "segundos": round(time.time() - t0, 1)},
        "capturas": resultados,
    })
    escribir_txt(salida / "capturas.txt", resultados)
    con_texto = sum(1 for r in resultados if r.get("lineas"))
    errores = sum(1 for r in resultados if "error" in r)
    print(f"listo en {time.time() - t0:.0f}s: {con_texto} de {len(capturas)} capturas con texto"
          + (f", {errores} no se pudieron leer" if errores else ""))


if __name__ == "__main__":
    main()
