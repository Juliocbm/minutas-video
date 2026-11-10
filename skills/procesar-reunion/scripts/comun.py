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

VERSION = "0.4.0"
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


def dir_modelos():
    """Caché de modelos descargados por el plugin (los de Whisper los guarda Hugging Face aparte).
    MINUTAS_MODELOS la cambia; por defecto %LOCALAPPDATA%\\minutas-video\\modelos o ~/.cache/minutas-video/modelos."""
    if os.environ.get("MINUTAS_MODELOS"):
        return Path(os.environ["MINUTAS_MODELOS"])
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "minutas-video" / "modelos"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "minutas-video" / "modelos"


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


def ancla(segundos):
    """Id HTML de la frase que empieza en ese segundo de la transcripción ilustrada (minuta.md enlaza a él)."""
    return f"t{int(segundos)}"


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
    escribir_derivados(salida, segmentos)
    return salida


def escribir_derivados(salida, segmentos):
    """transcripcion.txt (párrafos con [hh:mm:ss] y hablante) y transcripcion.srt."""
    salida = Path(salida)
    with open(salida / "transcripcion.txt", "w", encoding="utf-8") as f:
        for grupo in agrupar(segmentos):
            texto = " ".join(s["texto"].strip() for s in grupo)
            quien = f"{grupo[0]['hablante']}: " if grupo[0].get("hablante") else ""
            f.write(f"[{hms(grupo[0]['inicio'])}] {quien}{texto}\n")

    with open(salida / "transcripcion.srt", "w", encoding="utf-8") as f:
        for i, s in enumerate(segmentos, start=1):
            quien = f"{s['hablante']}: " if s.get("hablante") else ""
            f.write(f"{i}\n{ts_srt(s['inicio'])} --> {ts_srt(s['fin'])}\n{quien}{s['texto'].strip()}\n\n")


def asignar_hablantes(segmentos, turnos, nombres=None):
    """A cada segmento, el hablante con el que más se traslapa en el tiempo (o el del turno más cercano,
    a menos de 1 s, si cae en un hueco). `nombres` cambia «Hablante 1» por un nombre.
    Barrido en orden de inicio: cada turno entra una vez y sale cuando ya no puede traslaparse."""
    nombres = nombres or {}
    turnos = sorted(turnos, key=lambda t: t["inicio"])
    activos, j, salida = [], 0, []
    for s in sorted(segmentos, key=lambda x: x["inicio"]):
        while j < len(turnos) and turnos[j]["inicio"] < s["fin"]:
            activos.append(turnos[j])
            j += 1
        activos = [t for t in activos if t["fin"] > s["inicio"]]
        tiempo = {}
        for t in activos:
            juntos = min(s["fin"], t["fin"]) - max(s["inicio"], t["inicio"])
            if juntos > 0:
                tiempo[t["hablante"]] = tiempo.get(t["hablante"], 0) + juntos
        quien = max(tiempo, key=tiempo.get) if tiempo else None
        if quien is None and turnos:
            centro = (s["inicio"] + s["fin"]) / 2
            vecinos = turnos[max(0, j - 1):j + 1]
            distancia = lambda t: max(t["inicio"] - centro, centro - t["fin"], 0)  # noqa: E731
            cerca = min(vecinos, key=distancia) if vecinos else None
            if cerca and distancia(cerca) <= 1.0:
                quien = cerca["hablante"]
        salida.append({**s, "hablante": nombres.get(quien, quien) if quien else None})
    return salida


def leer_transcripcion(salida):
    """Metadatos y segmentos. Si la transcripción no trae hablantes y existe hablantes.json (separación
    automática), cada segmento recibe el suyo; meta["hablantes_origen"] lo indica."""
    salida = Path(salida)
    ruta = salida / "transcripcion.json"
    if not ruta.exists():
        raise SystemExit(f"No existe {ruta}. Corre primero transcribir.py o importar_transcripcion.py.")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    meta, segmentos = datos["meta"], datos["segmentos"]
    separacion = leer_json(salida / "hablantes.json") if not meta.get("hablantes") else None
    if separacion and separacion.get("turnos"):
        nombres = separacion.get("nombres") or {}
        segmentos = asignar_hablantes(segmentos, separacion["turnos"], nombres)
        vistos = []
        for s in segmentos:
            if s["hablante"] and s["hablante"] not in vistos:
                vistos.append(s["hablante"])
        meta = {**meta, "hablantes": vistos, "hablantes_origen": "separación automática"}
    return meta, segmentos


def reescribir_derivados(salida):
    """Rehace transcripcion.txt y .srt con los hablantes de la separación automática (o sin ellos)."""
    _, segmentos = leer_transcripcion(salida)
    escribir_derivados(salida, segmentos)


def leer_capturas(salida):
    ruta = Path(salida) / "capturas.json"
    if not ruta.exists():
        return {}, []
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return datos.get("meta", {}), datos.get("capturas", [])
