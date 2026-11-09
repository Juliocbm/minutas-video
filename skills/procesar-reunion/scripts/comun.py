"""Utilidades compartidas por los scripts de procesar-reunion (solo biblioteca estándar).

Formato intermedio: <salida>/transcripcion.json
{
  "meta": {...},
  "segmentos": [{"inicio": 12.3, "fin": 15.0, "texto": "...", "hablante": "Nombre" | null}, ...]
}
De ahí se derivan transcripcion.txt y transcripcion.srt, venga el texto de Whisper o de un .vtt/.srt importado.
"""
import json
import os
import sys
import time
from pathlib import Path

VERSION = "0.2.0"
PAUSA_PARRAFO = 1.5   # s de silencio que cortan un párrafo en el .txt
MAX_PALABRAS = 60     # palabras por párrafo en el .txt antes de cortar
PREFIJO_PROGRESO = "@progreso "


class Progreso:
    """Avance de un paso largo (transcripción, capturas).

    Con MINUTAS_PROGRESO=1, que pone minutas.py, imprime líneas '@progreso {json}'. El orquestador las
    convierte en barras, hitos y progreso.json. Sin esa variable, el script corre solo e imprime una
    línea legible cada 5 minutos de contenido.
    """

    def __init__(self, paso, total=0.0):
        self.paso, self.total = paso, total
        self.maquina = os.environ.get("MINUTAS_PROGRESO") == "1"
        self._ultimo = 0.0
        self._siguiente_legible = 300.0
        self._t0 = time.time()

    def fase(self, texto):
        if self.maquina:
            self._emitir({"fase": texto})
        else:
            print(texto, flush=True)

    def avance(self, hecho, **detalle):
        if self.maquina:
            ahora = time.time()
            if ahora - self._ultimo >= 1.0:
                self._ultimo = ahora
                self._emitir({"hecho": round(hecho, 1), "total": round(self.total, 1), **detalle})
        elif hecho >= self._siguiente_legible:
            self._siguiente_legible += 300
            extra = "  ".join(f"{k}={v}" for k, v in detalle.items())
            print(f"  {hms(hecho)} / {hms(self.total)}  {extra}  ({time.time() - self._t0:.0f}s)", flush=True)

    def _emitir(self, datos):
        print(PREFIJO_PROGRESO + json.dumps({"paso": self.paso, **datos}, ensure_ascii=False), flush=True)


def leer_json(ruta, defecto=None):
    ruta = Path(ruta)
    if not ruta.exists():
        return defecto
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def escribir_json(ruta, datos):
    """Escribe a un temporal y lo renombra: quien lee el archivo a la mitad nunca ve un JSON cortado."""
    ruta = Path(ruta)
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    for intento in range(5):
        try:
            os.replace(tmp, ruta)
            return
        except PermissionError:  # Windows: otro proceso lo tiene abierto en este instante
            time.sleep(0.1 * (intento + 1))
    os.replace(tmp, ruta)


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
