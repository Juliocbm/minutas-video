# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "faster-whisper>=1.2.1,<2",
#   "av>=12",
#   "numpy",
# ]
# ///
"""Transcribe el audio de un video o archivo de audio con faster-whisper, en local.

Uso (GPU NVIDIA en Windows/Linux):
  uv run --with nvidia-cublas-cu12 --with "nvidia-cudnn-cu12>=9,<10" transcribir.py <archivo> --salida <carpeta>
Uso (CPU):
  uv run transcribir.py <archivo> --salida <carpeta> --modelo medium --dispositivo cpu

Opciones: --modelo (large-v3), --idioma (es | auto | en ...), --dispositivo (auto | cuda | cpu),
          --pista <n.º de pista de audio>.
Genera transcripcion.json, transcripcion.txt y transcripcion.srt en la carpeta de salida.

No se le pasa vocabulario a Whisper: en pruebas, `hotwords` hizo que repitiera la lista de términos,
inventara texto y perdiera la mitad del contenido. Los términos propios se corrigen al redactar la minuta.
"""
import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from comun import Progreso, configurar_consola, escribir_transcripcion, hms
from entorno import modelos_descargados


def registrar_dlls_cuda():
    """En Windows, ctranslate2 debe ver las DLL de cuBLAS/cuDNN que trae pip (--with nvidia-...)."""
    if os.name != "nt":
        return
    try:
        import nvidia
    except ImportError:
        return
    for base in nvidia.__path__:
        for bin_dir in Path(base).glob("*/bin"):
            os.add_dll_directory(str(bin_dir))
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")


def pistas_audio(ruta):
    import av
    with av.open(str(ruta)) as c:
        return [
            {"indice": i, "titulo": s.metadata.get("title"), "idioma": s.metadata.get("language"),
             "canales": s.codec_context.channels, "codec": s.codec_context.name}
            for i, s in enumerate(c.streams.audio)
        ]


def decodificar_audio(ruta, pista=0, sr=16000):
    """Audio 16 kHz mono float32. Se decodifica aquí (no con faster_whisper.decode_audio) porque
    faster-whisper 1.2.1 pasa a av.open un parámetro que PyAV 19 ya no acepta."""
    import av
    import numpy as np

    resampler = av.AudioResampler(format="s16", layout="mono", rate=sr)
    trozos = []
    with av.open(str(ruta)) as c:
        for frame in c.decode(c.streams.audio[pista]):
            for f in resampler.resample(frame):
                trozos.append(f.to_ndarray().reshape(-1))
        for f in resampler.resample(None):
            trozos.append(f.to_ndarray().reshape(-1))
    if not trozos:
        raise SystemExit("La pista de audio está vacía.")
    return np.concatenate(trozos).astype(np.float32) / 32768.0


def cargar_modelo(nombre, dispositivo):
    from faster_whisper import WhisperModel
    if dispositivo in ("auto", "cuda"):
        try:
            modelo = WhisperModel(nombre, device="cuda", compute_type="float16")
            return modelo, "cuda"
        except Exception as e:
            if dispositivo == "cuda":
                raise
            print(f"CUDA no disponible ({e}); se usa CPU.", flush=True)
    return WhisperModel(nombre, device="cpu", compute_type="int8"), "cpu"


def main():
    configurar_consola()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("archivo")
    p.add_argument("--salida", required=True)
    p.add_argument("--modelo", default="large-v3")
    p.add_argument("--idioma", default="es")
    p.add_argument("--dispositivo", default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--pista", type=int)
    a = p.parse_args()

    archivo = Path(a.archivo)
    pistas = pistas_audio(archivo)
    if not pistas:
        raise SystemExit(f"{archivo.name} no tiene pistas de audio.")
    if a.pista is None and len(pistas) > 1:
        print("AVISO: hay varias pistas de audio; se usa la 0. Elige otra con --pista:", flush=True)
        for t in pistas:
            print(f"  pista {t['indice']}: {t['titulo'] or '(sin título)'} · {t['canales']} canales · {t['codec']}", flush=True)
    pista = a.pista or 0
    if pista >= len(pistas):
        raise SystemExit(f"La pista {pista} no existe; hay {len(pistas)} (0 a {len(pistas) - 1}).")

    prog = Progreso("transcripcion")
    registrar_dlls_cuda()
    t0 = time.time()
    descarga = "" if a.modelo in modelos_descargados() else " (la primera vez se descarga)"
    prog.fase(f"cargando el modelo {a.modelo}{descarga}")
    modelo, dispositivo = cargar_modelo(a.modelo, a.dispositivo)
    print(f"modelo {a.modelo} en {dispositivo}, cargado en {time.time() - t0:.0f}s", flush=True)

    t1 = time.time()
    prog.fase("decodificando el audio")
    audio = decodificar_audio(archivo, pista)
    duracion = len(audio) / 16000
    prog.total = duracion
    print(f"audio decodificado: {hms(duracion)} en {time.time() - t1:.0f}s", flush=True)
    prog.fase(f"transcribiendo en {dispositivo}")

    segs, info = modelo.transcribe(
        audio,
        language=None if a.idioma == "auto" else a.idioma,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=False,
    )

    segmentos, t2 = [], time.time()
    for s in segs:
        segmentos.append({"inicio": round(s.start, 2), "fin": round(s.end, 2), "texto": s.text.strip(), "hablante": None})
        prog.avance(s.end, segmentos=len(segmentos))

    meta = {
        "fuente": "whisper",
        "archivo": str(archivo.resolve()),
        "duracion": round(duracion, 1),
        "modelo": a.modelo,
        "dispositivo": dispositivo,
        "idioma": info.language,
        "pista": pista,
        "pistas_disponibles": len(pistas),
        "generado": datetime.now().isoformat(timespec="seconds"),
    }
    salida = escribir_transcripcion(a.salida, segmentos, meta)
    print(f"listo en {time.time() - t2:.0f}s: {len(segmentos)} segmentos -> {salida}", flush=True)


if __name__ == "__main__":
    main()
