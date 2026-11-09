# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "av>=12",
#   "numpy",
#   "pillow>=10.1",
# ]
# ///
"""Extrae capturas de un video cada vez que el contenido cambia de forma relevante.

Uso: uv run extraer_capturas.py <video> --salida <carpeta> [--modo pantalla|camara|ninguna] [--max 200]

Modos:
  pantalla  grabaciones de pantalla o videollamadas con pantalla compartida (por defecto).
            Captura cambios de ventana, scroll, documentos, errores.
  camara    juntas presenciales grabadas con cámara (experimental): solo cambios grandes y
            sostenidos (proyector, pizarrón), con varios segundos entre capturas.
  ninguna   no captura (útil para forzar transcripción sin imágenes).

Cómo decide: muestrea el video, compara una miniatura en gris contra la última captura y, si
cambió más del umbral, espera a que la imagen se estabilice para no capturar a media transición.
Un archivo de solo audio produce una lista vacía.

Genera <salida>/capturas/NNNN_HH-MM-SS.jpg y <salida>/capturas.json.
"""
import argparse
import json
import time
from pathlib import Path

import av
import numpy as np

from comun import configurar_consola, hms

ANCHO, ALTO = 192, 108
MODOS = {
    #            muestreo  dif_pixel  cambio  estable  max_espera  entre_forzadas  entre_capturas
    "pantalla": (1.0,      24,        0.04,   0.010,   6,          20,             0),
    "camara":   (2.0,      32,        0.30,   0.080,   10,         120,            30),
}


def miniatura(frame):
    return frame.reformat(width=ANCHO, height=ALTO, format="gray").to_ndarray().astype(np.int16)


def main():
    configurar_consola()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video")
    p.add_argument("--salida", required=True)
    p.add_argument("--modo", default="pantalla", choices=["pantalla", "camara", "ninguna"])
    p.add_argument("--max", type=int, default=200, help="tope de capturas")
    p.add_argument("--umbral-cambio", type=float, help="fracción de píxeles que deben cambiar")
    p.add_argument("--umbral-estable", type=float, help="cambio máximo entre muestras para considerar estable")
    a = p.parse_args()

    salida = Path(a.salida)
    dir_cap = salida / "capturas"
    dir_cap.mkdir(parents=True, exist_ok=True)
    for vieja in dir_cap.glob("*.jpg"):
        vieja.unlink()

    meta = {"modo": a.modo, "video": str(Path(a.video).resolve()), "truncado": False}
    capturas = []

    def guardar_json():
        (salida / "capturas.json").write_text(
            json.dumps({"meta": meta, "capturas": capturas}, ensure_ascii=False, indent=1), encoding="utf-8")

    if a.modo == "ninguna":
        guardar_json()
        print("modo ninguna: sin capturas")
        return

    muestreo, dif_pixel, cambio_min, estable_max, max_espera, entre_forzadas, entre_capturas = MODOS[a.modo]
    cambio_min = a.umbral_cambio or cambio_min
    estable_max = a.umbral_estable or estable_max
    meta.update({"umbral_cambio": cambio_min, "umbral_estable": estable_max})

    def fraccion(x, y):
        return float((np.abs(x - y) > dif_pixel).mean())

    t0 = time.time()
    with av.open(str(a.video)) as c:
        if not c.streams.video:
            guardar_json()
            print("el archivo no tiene video: sin capturas")
            return
        s = c.streams.video[0]
        s.thread_type = "AUTO"
        duracion = c.duration / 1_000_000 if c.duration else 0
        meta["duracion"] = round(duracion, 1)

        ultima = anterior = None
        cambio_desde = None
        t_ultima = t_forzada = -1e9
        siguiente, siguiente_aviso = 0.0, 300.0

        for frame in c.decode(s):
            t = frame.time
            if t is None or t < siguiente:
                continue
            siguiente = t + muestreo
            m = miniatura(frame)

            motivo, cambio = None, 0.0
            if ultima is None:
                motivo = "inicio"
            else:
                cambio = fraccion(ultima, m)
                if cambio > cambio_min:
                    cambio_desde = t if cambio_desde is None else cambio_desde
                    if t - t_ultima >= entre_capturas:
                        if anterior is not None and fraccion(anterior, m) < estable_max:
                            motivo = "estable"
                        elif t - cambio_desde >= max_espera and t - t_forzada >= entre_forzadas:
                            motivo = "forzada"
                else:
                    cambio_desde = None

            if motivo:
                if len(capturas) >= a.max:
                    meta["truncado"] = True
                    print(f"AVISO: se alcanzó el tope de {a.max} capturas en {hms(t)}; sube --max o --umbral-cambio.")
                    break
                n = len(capturas) + 1
                nombre = f"{n:04}_{hms(t, '-')}.jpg"
                frame.to_image().save(dir_cap / nombre, quality=85)
                capturas.append({
                    "n": n,
                    "archivo": f"capturas/{nombre}",
                    "t": round(t, 2),
                    "desde": round(t if cambio_desde is None else cambio_desde, 2),
                    "motivo": motivo,
                    "cambio": round(cambio, 3),
                })
                t_ultima = t
                if motivo == "forzada":
                    t_forzada = t
                ultima, cambio_desde = m, None
            anterior = m

            if t >= siguiente_aviso:
                siguiente_aviso += 300
                print(f"  {hms(t)} / {hms(duracion)}  capturas={len(capturas)}  ({time.time() - t0:.0f}s)", flush=True)

    guardar_json()
    forzadas = sum(1 for x in capturas if x["motivo"] == "forzada")
    print(f"listo en {time.time() - t0:.0f}s: {len(capturas)} capturas ({forzadas} forzadas)")


if __name__ == "__main__":
    main()
