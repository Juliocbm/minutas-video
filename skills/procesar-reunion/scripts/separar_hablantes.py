# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "sherpa-onnx>=2,<3",
#   "av>=12",
#   "numpy",
# ]
# ///
"""Separa a los hablantes de una grabación: quién habla en cada momento ("Hablante 1", "Hablante 2"…).

Uso: uv run separar_hablantes.py <grabación> --salida <carpeta> [--hablantes N] [--pista N] [--umbral U]
  --hablantes  cuántas personas hablan. Úsalo solo si sin él sale un número claramente equivocado:
               en las mediciones, forzarlo dio más error que dejar que el umbral decida.
  --umbral     sin --hablantes, decide cuándo dos voces son la misma persona (más alto, menos hablantes).

Usa sherpa-onnx en CPU: el modelo de segmentación de pyannote 3.0 (convertido, licencia MIT) y un
modelo de voces. Los dos se descargan de GitHub la primera vez, sin cuentas ni tokens, y quedan en la
caché del plugin (comun.dir_modelos()). No sabe nombres: los nombres se deducen con evidencia.

Escribe <salida>/hablantes.json con los turnos. minutas.py los asigna a las frases de la transcripción.
"""
import argparse
import os
import tarfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from comun import Progreso, configurar_consola, dir_modelos, escribir_json, hms
from transcribir import decodificar_audio, pistas_audio

GITHUB = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
SEGMENTACION = {
    "url": f"{GITHUB}/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2",
    "carpeta": "sherpa-onnx-pyannote-segmentation-3-0", "archivo": "model.onnx", "mb": 6,
}
# Medido con el corpus AMI (dev/medir_hablantes.py; DER sin margen, contando el habla encimada).
# Modelos de voces, reunión ES2004a con el número real de hablantes: TitaNet small 20.0 % y 9 veces más
# rápido que el tiempo real; ERes2Net 20.0 % a 5x; wespeaker ResNet34 31.2 %; CAM++ 55.4 %.
# Umbral, 4 reuniones (1.9 h) sin decir cuántos hablan y con absorber_menores: 1.00 → 23.1 %; 1.10 → 22.0 %;
# 1.20 junta a varias personas en una (40 % en dos reuniones). Se usa 1.00: un hablante de más se
# absorbe, dos personas fundidas no tienen arreglo. Dar el número real dio 31.7 %: no conviene forzarlo.
# Referencia: pyannote community-1 publica 17.0 % en AMI (IHM), sobre todo por detectar mejor el habla encimada.
VOCES = {
    "nemo_en_titanet_small": {"url": f"{GITHUB}/speaker-recongition-models/nemo_en_titanet_small.onnx", "mb": 40},
    "3dspeaker_speech_eres2net_sv_en_voxceleb_16k": {"url": f"{GITHUB}/speaker-recongition-models/3dspeaker_speech_eres2net_sv_en_voxceleb_16k.onnx", "mb": 27},
}
VOZ = "nemo_en_titanet_small"
UMBRAL = 1.0
MINIMO_S, MINIMO_FRAC = 15.0, 0.02  # sin --hablantes: menos que esto no es un hablante, es un fragmento
HILOS = max(1, min(8, os.cpu_count() or 1))  # sherpa-onnx usa 1 por defecto: varias veces más lento


def descargar(url, destino, prog=None, texto=""):
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".descarga")
    if prog:
        prog.fase(texto)
    with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
        while bloque := r.read(1 << 20):
            f.write(bloque)
    tmp.replace(destino)


def modelos(voz=VOZ, prog=None):
    """Rutas (segmentación, voces); los descarga la primera vez."""
    base = dir_modelos() / "sherpa-onnx"
    seg = base / SEGMENTACION["carpeta"] / SEGMENTACION["archivo"]
    if not seg.exists():
        paquete = base / "segmentacion.tar.bz2"
        descargar(SEGMENTACION["url"], paquete, prog, f"descargando el modelo de segmentación ({SEGMENTACION['mb']} MB, solo la primera vez)")
        with tarfile.open(paquete) as t:
            try:
                t.extractall(base, filter="data")
            except TypeError:  # Python sin el parámetro filter (anteriores a 3.10.12 / 3.11.4)
                t.extractall(base)
        paquete.unlink()
    datos = VOCES[voz]
    ruta_voz = base / f"{voz}.onnx"
    if not ruta_voz.exists():
        descargar(datos["url"], ruta_voz, prog, f"descargando el modelo de voces ({datos['mb']} MB, solo la primera vez)")
    return seg, ruta_voz


def diarizar(audio, seg, voz, hablantes=0, umbral=UMBRAL, al_avanzar=None):
    """Turnos [(inicio, fin, n.º de hablante)] de un audio 16 kHz mono float32."""
    import sherpa_onnx
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(seg)), num_threads=HILOS),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(voz), num_threads=HILOS),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=hablantes if hablantes > 0 else -1, threshold=umbral),
        min_duration_on=0.3,
        min_duration_off=0.5,
    )
    if not config.validate():
        raise SystemExit("Configuración de sherpa-onnx no válida (¿modelos incompletos? bórralos de la caché).")
    sd = sherpa_onnx.OfflineSpeakerDiarization(config)

    def callback(hecho, total):
        if al_avanzar:
            al_avanzar(hecho, total)
        return 0

    resultado = sd.process(audio, callback=callback).sort_by_start_time()
    return [(r.start, r.end, r.speaker) for r in resultado]


def absorber_menores(turnos, minimo_s=MINIMO_S, minimo_frac=MINIMO_FRAC):
    """Sin el número de hablantes, el agrupamiento parte a una persona en varios «hablantes» con muy
    poco tiempo. Los que suman menos de minimo_s segundos o menos de minimo_frac del habla se
    reasignan, turno por turno, al hablante del turno vecino más cercano en el tiempo."""
    total = sum(b - a for a, b, _ in turnos)
    tiempo = {}
    for a, b, h in turnos:
        tiempo[h] = tiempo.get(h, 0) + (b - a)
    menores = {h for h, t in tiempo.items() if t < minimo_s or t < minimo_frac * total}
    mayores = [(a, b, h) for a, b, h in turnos if h not in menores]
    if not menores or not mayores:
        return turnos
    salida = []
    for a, b, h in turnos:
        if h in menores:
            vecino = min(mayores, key=lambda t: max(t[0] - b, a - t[1], 0))
            h = vecino[2]
        salida.append((a, b, h))
    return salida


def etiquetar(turnos):
    """Numera a los hablantes por orden de aparición: el primero en hablar es «Hablante 1»."""
    orden = {}
    for _, _, h in turnos:
        orden.setdefault(h, len(orden) + 1)
    return [{"inicio": round(a, 2), "fin": round(b, 2), "hablante": f"Hablante {orden[h]}"} for a, b, h in turnos]


def main():
    configurar_consola()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("grabacion")
    p.add_argument("--salida", required=True)
    p.add_argument("--hablantes", type=int, default=0, help="cuántas personas hablan, si se sabe")
    p.add_argument("--pista", type=int, default=0)
    p.add_argument("--umbral", type=float, default=UMBRAL)
    p.add_argument("--voz", default=VOZ, choices=list(VOCES), help="modelo de voces")
    a = p.parse_args()

    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    prog = Progreso("hablantes")
    seg, voz = modelos(a.voz, prog)
    prog.fase("decodificando el audio")
    if a.pista >= len(pistas_audio(a.grabacion)):
        raise SystemExit(f"La grabación no tiene la pista de audio {a.pista}.")
    audio = decodificar_audio(a.grabacion, a.pista)
    duracion = len(audio) / 16000
    prog.fase("separando las voces")

    def al_avanzar(hecho, total):
        prog.total = total
        prog.avance(hecho)

    t0 = time.time()
    crudos = diarizar(audio, seg, voz, a.hablantes, a.umbral, al_avanzar)
    turnos = etiquetar(crudos if a.hablantes else absorber_menores(crudos))
    nombres = sorted({t["hablante"] for t in turnos}, key=lambda h: int(h.split()[1]))
    escribir_json(salida / "hablantes.json", {
        "meta": {"motor": "sherpa-onnx (pyannote segmentation 3.0)", "voz": a.voz, "umbral": a.umbral,
                 "hablantes_pedidos": a.hablantes or None, "hablantes": nombres, "duracion": round(duracion, 1),
                 "generado": datetime.now().isoformat(timespec="seconds"), "segundos": round(time.time() - t0, 1)},
        "turnos": turnos,
    })
    print(f"listo en {time.time() - t0:.0f}s: {len(nombres)} hablantes, {len(turnos)} turnos en {hms(duracion)}")


if __name__ == "__main__":
    main()
