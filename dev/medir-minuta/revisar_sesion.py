"""Resume una sesión guardada por sesion_viva.py: costo de cada turno, archivos que leyó Claude e imágenes abiertas.

Las imágenes importan: en la 0.4, con el texto del OCR a la mano, Claude dejó de abrir las capturas y la minuta
perdió lo que solo se veía en pantalla. `--detalle` muestra además cada herramienta, texto y resultado en orden.

uso: python revisar_sesion.py sesion.jsonl [--detalle]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import PurePath

IMAGENES = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def eventos(ruta):
    with open(ruta, encoding="utf-8-sig") as f:
        for linea in f:
            try:
                yield json.loads(linea)
            except ValueError:
                continue


def detalle(evento):
    tipo = evento.get("type")
    if tipo == "assistant":
        for c in evento["message"]["content"]:
            if c["type"] == "tool_use":
                print("\nHERRAMIENTA", c["name"], json.dumps(c["input"], ensure_ascii=False)[:300])
            elif c["type"] == "text":
                print("\nTEXTO", c["text"][:900])
    elif tipo == "user" and isinstance(evento["message"]["content"], list):
        for c in evento["message"]["content"]:
            if c.get("type") == "tool_result":
                cont = c.get("content")
                texto = cont if isinstance(cont, str) else json.dumps(cont, ensure_ascii=False)
                print("  RESULTADO", texto[:300].replace("\n", " | "))
    elif tipo == "system" and evento.get("subtype") != "init":
        print("SISTEMA", json.dumps(evento, ensure_ascii=False)[:250])


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("sesion")
    a.add_argument("--detalle", action="store_true")
    args = a.parse_args()
    sys.stdout.reconfigure(errors="replace")  # el texto de la sesión puede traer caracteres que la consola no tiene

    anterior, n, lecturas = 0.0, 0, Counter()
    for evento in eventos(args.sesion):
        if args.detalle:
            detalle(evento)
        if evento.get("type") == "assistant":
            for c in evento["message"]["content"]:
                if c["type"] == "tool_use" and c["name"] == "Read":
                    lecturas[PurePath(c["input"].get("file_path", "").replace("\\", "/")).name] += 1
        if evento.get("type") == "result":
            n += 1
            costo = evento.get("total_cost_usd") or 0
            uso = evento.get("usage", {})
            print(f"turno {n:2}: +{costo - anterior:.3f} USD (acumulado {costo:.2f})  pasos={evento.get('num_turns')}"
                  f"  caché leída={uso.get('cache_read_input_tokens')}  salida={uso.get('output_tokens')}")
            anterior = costo

    imagenes = sorted(f for f in lecturas if f.lower().endswith(IMAGENES))
    print(f"\nimágenes abiertas: {len(imagenes)}  {', '.join(imagenes)}")
    print("lecturas más repetidas:", ", ".join(f"{f} ({k})" for f, k in lecturas.most_common(12)))


if __name__ == "__main__":
    main()
