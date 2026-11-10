# /// script
# requires-python = ">=3.10"
# dependencies = ["sherpa-onnx>=2,<3", "av>=12", "numpy", "scipy"]
# ///
"""Mide la separación de hablantes contra el corpus AMI, como lo publica pyannote.

Uso:
  uv run --script dev/medir_hablantes.py <carpeta con NNN.wav y NNN.rttm> [--voces a,b] [--umbrales 0.5,0.6] [--conocidos]

Audio: <reunión>.Mix-Headset.wav del espejo de AMI (https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/).
Referencia: only_words/rttms/test/<reunión>.rttm de https://github.com/pyannote/AMI-diarization-setup.
Métrica: error de diarización (DER) por cuadros de 10 ms, sin margen de tolerancia y contando el habla
encimada, con la asignación óptima de hablantes: el mismo protocolo con el que pyannote publica
17.0 % (community-1) y 18.8 % (3.1) en AMI (IHM).
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "procesar-reunion" / "scripts"))
from separar_hablantes import UMBRAL, VOCES, absorber_menores, diarizar, modelos  # noqa: E402
from transcribir import decodificar_audio  # noqa: E402

PASO = 0.01


def leer_rttm(ruta):
    turnos = []
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        c = linea.split()
        if c and c[0] == "SPEAKER":
            inicio, dur = float(c[3]), float(c[4])
            turnos.append((inicio, inicio + dur, c[7]))
    return turnos


def matriz(turnos, n_cuadros):
    etiquetas = sorted({h for _, _, h in turnos}, key=str)
    m = np.zeros((len(etiquetas), n_cuadros), dtype=bool)
    for a, b, h in turnos:
        m[etiquetas.index(h), int(round(a / PASO)):int(round(b / PASO))] = True
    return m


def der(referencia, hipotesis):
    fin = max(b for _, b, _ in referencia + hipotesis)
    n = int(np.ceil(fin / PASO)) + 1
    R, H = matriz(referencia, n), matriz(hipotesis, n)
    total = R.sum()
    # Asignación óptima hipótesis → referencia por tiempo compartido.
    compartido = (R[:, None, :] & H[None, :, :]).sum(axis=2) if len(H) else np.zeros((len(R), 0))
    filas, cols = linear_sum_assignment(-compartido) if len(H) else ([], [])
    aciertos = sum(compartido[f, c] for f, c in zip(filas, cols))
    nr, nh = R.sum(axis=0), H.sum(axis=0)
    perdido = np.maximum(nr - nh, 0).sum()
    falso = np.maximum(nh - nr, 0).sum()
    confusion = np.minimum(nr, nh).sum() - aciertos
    return {"der": (perdido + falso + confusion) / total, "perdido": perdido / total, "falso": falso / total,
            "confusion": confusion / total, "hablantes_ref": len(R), "hablantes_hip": len(H)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("carpeta")
    p.add_argument("--voces", default=",".join(VOCES))
    p.add_argument("--umbrales", default=str(UMBRAL))
    p.add_argument("--conocidos", action="store_true", help="también con el número real de hablantes")
    p.add_argument("--reuniones", help="solo estas (separadas por coma)")
    a = p.parse_args()

    reuniones = sorted(Path(a.carpeta).glob("*.rttm"))
    if a.reuniones:
        reuniones = [r for r in reuniones if r.stem in a.reuniones.split(",")]
    audios = {r.stem: decodificar_audio(r.with_suffix(".wav")) for r in reuniones}
    refs = {r.stem: leer_rttm(r) for r in reuniones}
    horas = sum(len(x) for x in audios.values()) / 16000 / 3600
    print(f"{len(reuniones)} reuniones, {horas:.2f} h de audio\n")
    print(f"{'voces':45} {'umbral':>7} {'DER':>6} {'perdido':>8} {'falso':>6} {'confus.':>8} {'hablantes':>10} {'x tiempo real':>14}")
    for voz in a.voces.split(","):
        seg, ruta_voz = modelos(voz)
        configuraciones = [(float(u), 0) for u in a.umbrales.split(",") if u] + ([(None, -1)] if a.conocidos else [])
        for umbral, conocido in configuraciones:
            variantes = {"": [], "+abs": []}  # +abs: con absorber_menores (lo que hace el plugin sin --hablantes)
            t0 = time.time()
            for nombre, audio in audios.items():
                n = len({h for _, _, h in refs[nombre]}) if conocido else 0
                crudos = [(s, e, str(h)) for s, e, h in diarizar(audio, seg, ruta_voz, n, umbral or UMBRAL)]
                peso = sum(b - x for x, b, _ in refs[nombre])
                variantes[""].append((der(refs[nombre], crudos), peso))
                if not conocido:
                    variantes["+abs"].append((der(refs[nombre], absorber_menores(crudos)), peso))
            velocidad = horas * 3600 / (time.time() - t0)
            for sufijo, resultados in variantes.items():
                if not resultados:
                    continue
                ref_total = sum(p for _, p in resultados)
                perdido, falso, confusion = (sum(r[k] * p for r, p in resultados) / ref_total
                                             for k in ("perdido", "falso", "confusion"))
                hablantes = " ".join(f"{r['hablantes_hip']}/{r['hablantes_ref']}" for r, _ in resultados)
                etiqueta = ("conocidos" if conocido else f"{umbral:.2f}") + sufijo
                print(f"{voz:45} {etiqueta:>9} {perdido + falso + confusion:6.1%} {perdido:8.1%} {falso:6.1%} "
                      f"{confusion:8.1%} {hablantes:>12} {velocidad:13.0f}x", flush=True)


if __name__ == "__main__":
    main()
