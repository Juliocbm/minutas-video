"""Utilidades compartidas por los scripts de procesar-reunion (solo biblioteca estándar).

Formato intermedio: <salida>/transcripcion.json
{
  "meta": {...},
  "segmentos": [{"inicio": 12.3, "fin": 15.0, "texto": "...", "hablante": "Nombre" | null}, ...]
}
De ahí se derivan transcripcion.txt y transcripcion.srt, venga el texto de Whisper o de un .vtt/.srt importado.
"""
import json
import sys
from pathlib import Path

PAUSA_PARRAFO = 1.5   # s de silencio que cortan un párrafo en el .txt
MAX_PALABRAS = 60     # palabras por párrafo en el .txt antes de cortar


def configurar_consola():
    """Evita UnicodeEncodeError al imprimir acentos cuando la salida va a un pipe en Windows."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def hms(segundos, sep=":"):
    s = int(segundos)
    return f"{s // 3600:02}{sep}{s % 3600 // 60:02}{sep}{s % 60:02}"


def ts_srt(segundos):
    ms = int(round(segundos * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def agrupar(segmentos, pausa=PAUSA_PARRAFO, max_palabras=MAX_PALABRAS):
    """Une segmentos consecutivos del mismo hablante en párrafos legibles."""
    grupos, actual, palabras = [], [], 0
    for seg in segmentos:
        if actual:
            previo = actual[-1]
            corta = (
                seg.get("hablante") != previo.get("hablante")
                or seg["inicio"] - previo["fin"] > pausa
                or palabras > max_palabras
            )
            if corta:
                grupos.append(actual)
                actual, palabras = [], 0
        actual.append(seg)
        palabras += len(seg["texto"].split())
    if actual:
        grupos.append(actual)
    return grupos


def escribir_transcripcion(salida, segmentos, meta):
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    segmentos = [s for s in segmentos if s["texto"].strip()]
    meta = dict(meta)
    meta["hablantes"] = sorted({s["hablante"] for s in segmentos if s.get("hablante")})
    meta["segmentos"] = len(segmentos)

    (salida / "transcripcion.json").write_text(
        json.dumps({"meta": meta, "segmentos": segmentos}, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    with open(salida / "transcripcion.txt", "w", encoding="utf-8") as f:
        for grupo in agrupar(segmentos):
            texto = " ".join(s["texto"].strip() for s in grupo)
            quien = f"{grupo[0]['hablante']}: " if grupo[0].get("hablante") else ""
            f.write(f"[{hms(grupo[0]['inicio'])}] {quien}{texto}\n")

    with open(salida / "transcripcion.srt", "w", encoding="utf-8") as f:
        for i, s in enumerate(segmentos, start=1):
            quien = f"{s['hablante']}: " if s.get("hablante") else ""
            f.write(f"{i}\n{ts_srt(s['inicio'])} --> {ts_srt(s['fin'])}\n{quien}{s['texto'].strip()}\n\n")
    return salida


def leer_transcripcion(salida):
    ruta = Path(salida) / "transcripcion.json"
    if not ruta.exists():
        raise SystemExit(f"No existe {ruta}. Corre primero transcribir.py o importar_transcripcion.py.")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return datos["meta"], datos["segmentos"]


def leer_capturas(salida):
    ruta = Path(salida) / "capturas.json"
    if not ruta.exists():
        return {}, []
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return datos.get("meta", {}), datos.get("capturas", [])
