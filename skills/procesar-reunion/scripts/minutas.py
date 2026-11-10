# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""minutas-video: procesa grabaciones de punta a punta y lleva el registro de cada paso.

  minutas.py procesar <grabación|transcripción|carpeta> [...] [opciones]
      Transcripción (Whisper o importada), capturas, texto de las capturas (OCR), glosario y
      transcripción ilustrada. Lo que ya está hecho con los mismos parámetros no se repite: si algo
      falla o cambias una opción, vuelve a correr el mismo comando y solo se rehace lo necesario.
  minutas.py procesar <grabación> --plan
      Muestra en JSON qué haría y con qué configuración, sin correr nada.
  minutas.py seguir <salida>
      Barra de progreso en vivo de un proceso en curso (útil cuando lo lanzó Claude).
  minutas.py config [--proyecto DIR]
      Configuración efectiva, de dónde sale cada valor, presets y errores (JSON).
  minutas.py glosario <salida>
      Busca en la transcripción los términos del glosario y las menciones de participantes.
  minutas.py minuta <salida>
      Valida minuta.json, verifica cada cita contra la transcripción y el texto de las capturas, y
      genera minuta.md.

En una terminal muestra barras de progreso. Cuando la salida no es una terminal (por ejemplo, la
lanza Claude), imprime solo hitos: inicio y fin de cada paso, y avances del 25, 50 y 75 %.
Cada salida guarda reunion.json (manifiesto), progreso.json y _registro/ (bitácoras de cada paso).
Solo biblioteca estándar: cada paso pesado es otro script con sus propias dependencias.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import config as cfgmod
import glosario as glosmod
import minuta as minmod
from comun import PREFIJO_PROGRESO, VERSION, configurar_consola, escribir_json, hms, leer_json, leer_transcripcion
from entorno import recomendar

DIR = Path(__file__).resolve().parent
EXT_VIDEO = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v", ".wmv", ".flv", ".ts", ".mts"}
EXT_AUDIO = {".m4a", ".mp3", ".wav", ".ogg", ".opus", ".flac", ".aac", ".wma"}
EXT_TRANSCRIPCION = {".vtt", ".srt"}

PASOS = ("transcripcion", "capturas", "ocr", "glosario", "html")
NOMBRE = {"transcripcion": "transcripción", "capturas": "capturas", "ocr": "texto de las capturas",
          "glosario": "glosario", "html": "transcripción ilustrada"}
SALIDA_DE = {"transcripcion": "transcripcion.json", "capturas": "capturas.json", "ocr": "ocr.json",
             "glosario": "glosario.json", "html": "transcripcion-ilustrada.html"}
DEPENDE = {"transcripcion": (), "capturas": (), "ocr": ("capturas",), "glosario": ("transcripcion",),
           "html": ("transcripcion", "capturas", "ocr", "glosario")}
# Subir la versión de un paso hace que se rehaga en las reuniones ya procesadas.
VERSION_PASO = {"transcripcion": 1, "capturas": 2, "ocr": 1, "glosario": 1, "html": 2}
EXTERNOS = ("transcripcion", "capturas", "ocr")  # pasos que corren en su propio proceso, en paralelo
OPCIONALES = ("ocr",)  # si fallan, lo que depende de ellos se hace igual, sin su resultado
HITOS = (25, 50, 75)
# Opciones de la corrida que se recuerdan en reunion.json y se reaplican al reanudar esa reunión.
RECORDADAS = ("preset", "idioma", "modelo", "dispositivo", "capturas", "max_capturas", "umbral_cambio",
              "ocr", "pista", "transcripcion", "titulo", "nota", "incrustar")


# ───────────────────────── utilidades ─────────────────────────

def ahora():
    return datetime.now().isoformat(timespec="seconds")


def duracion_corta(seg):
    seg = int(round(seg))
    return hms(seg) if seg >= 3600 else f"{seg // 60}:{seg % 60:02}"


def faltan(seg):
    if not seg:
        return ""
    return f"faltan ~{round(seg / 60)} min" if seg >= 90 else f"faltan ~{max(5, round(seg / 5) * 5)} s"


def identidad(ruta):
    ruta = Path(ruta).resolve()
    st = ruta.stat()
    return {"ruta": str(ruta), "tamano": st.st_size, "modificado": st.st_mtime_ns}


def firma(*partes):
    texto = json.dumps(partes, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:16]


def tipo_de(ruta):
    ext = ruta.suffix.lower()
    if ext in EXT_TRANSCRIPCION:
        return "transcripcion"
    if ext in EXT_AUDIO:
        return "audio"
    return "video"  # PyAV decide; un archivo sin pista de video simplemente no tendrá capturas


def localizar_uv():
    candidatos = [os.environ.get("UV"), shutil.which("uv")]
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        candidatos += [local / "Microsoft" / "WinGet" / "Links" / "uv.exe",
                       *sorted(local.glob("Microsoft/WinGet/Packages/astral-sh.uv_*/uv.exe")),
                       Path.home() / ".local" / "bin" / "uv.exe"]
    else:
        candidatos += [Path.home() / ".local" / "bin" / "uv", Path.home() / ".cargo" / "bin" / "uv"]
    for c in candidatos:
        if c and Path(c).exists():
            return str(c)
    raise SystemExit("No se encontró uv. Instálalo: https://docs.astral.sh/uv/getting-started/installation/")


def lista_pasos(texto):
    nombres = [x.strip() for x in texto.split(",") if x.strip()]
    malos = [n for n in nombres if n not in PASOS and n != "todo"]
    if malos:
        raise argparse.ArgumentTypeError(f"pasos desconocidos: {', '.join(malos)}. Válidos: {', '.join(PASOS)}, todo.")
    return set(nombres)


def expandir(entradas):
    rutas = []
    for e in entradas:
        p = Path(e)
        if p.is_dir():
            halladas = sorted(x for x in p.iterdir() if x.is_file() and x.suffix.lower() in EXT_VIDEO | EXT_AUDIO)
            if not halladas:
                raise SystemExit(f"{p}: la carpeta no tiene grabaciones de video o audio.")
            rutas += halladas
        elif p.is_file():
            rutas.append(p)
        else:
            raise SystemExit(f"No existe: {p}")
    return [r.resolve() for r in rutas]


# ───────────────────────── plan ─────────────────────────

def explicitas(a):
    op = {}
    for clave in RECORDADAS:
        valor = getattr(a, clave, None)
        if valor is not None:
            op[clave] = valor
    if op.get("transcripcion") and op["transcripcion"] != "whisper":
        op["transcripcion"] = str(Path(op["transcripcion"]).resolve())
    return op


def corrida_desde(op):
    return {"preset": op.get("preset"), "idioma": op.get("idioma"),
            "transcripcion": {"modelo": op.get("modelo"), "dispositivo": op.get("dispositivo")},
            "capturas": {"modo": op.get("capturas"), "max": op.get("max_capturas"), "ocr": op.get("ocr")}}


def motivo_de(paso, previo, parametros, existe):
    if not previo:
        return "nuevo"
    if previo.get("estado") != "completo":
        return f"no terminó la vez anterior ({previo.get('estado')})"
    if not existe:
        return f"falta {SALIDA_DE[paso]}"
    cambios = [k for k in parametros if previo.get("parametros", {}).get(k) != parametros[k]]
    return ("cambió " + ", ".join(cambios)) if cambios else "cambió un paso anterior o la versión del plugin"


def planear(ruta, a, rec):
    tipo = tipo_de(ruta)
    salida = Path(a.salida).resolve() if a.salida else ruta.parent / f"{ruta.stem}_minuta"
    previo = leer_json(salida / "reunion.json", {}) or {}
    avisos = []
    otra = previo.get("entrada", {}).get("ruta")
    if otra and otra != str(ruta):
        avisos.append(f"La carpeta de salida ya tenía otra grabación ({otra}); se rehará todo.")
        previo = {}

    opciones = {**previo.get("opciones", {}), **explicitas(a)}
    if opciones.get("transcripcion") == "whisper":
        opciones.pop("transcripcion")
    cfg = cfgmod.cargar(a.proyecto, corrida_desde(opciones), rec["recomendacion"])
    ef = cfg["efectiva"]

    pasos = {}
    importada = Path(opciones["transcripcion"]) if opciones.get("transcripcion") else (ruta if tipo == "transcripcion" else None)
    if importada:
        pasos["transcripcion"] = {
            "script": "importar_transcripcion.py", "with": [],
            "args": [str(importada), "--salida", str(salida)],
            "parametros": {"modo": "importar", "archivo": identidad(importada)},
        }
    else:
        t = ef["transcripcion"]
        resuelto = t.get("dispositivo_resuelto", t["dispositivo"])
        args = [str(ruta), "--salida", str(salida), "--modelo", t["modelo"], "--idioma", ef["idioma"],
                "--dispositivo", t["dispositivo"]]
        if opciones.get("pista") is not None:
            args += ["--pista", str(opciones["pista"])]
        pasos["transcripcion"] = {
            "script": "transcribir.py", "args": args,
            "with": rec["recomendacion"]["uv_with"] if resuelto == "cuda" else [],
            "parametros": {"modo": "whisper", "archivo": identidad(ruta), "modelo": t["modelo"],
                           "idioma": ef["idioma"], "pista": opciones.get("pista")},
        }

    modo = ef["capturas"]["modo"] if tipo == "video" else "ninguna"
    if modo != "ninguna":
        args = [str(ruta), "--salida", str(salida), "--modo", modo, "--max", str(ef["capturas"]["max"])]
        if opciones.get("umbral_cambio"):
            args += ["--umbral-cambio", str(opciones["umbral_cambio"])]
        pasos["capturas"] = {
            "script": "extraer_capturas.py", "with": [], "args": args,
            "parametros": {"archivo": identidad(ruta), "modo": modo, "max": ef["capturas"]["max"],
                           "umbral_cambio": opciones.get("umbral_cambio")},
        }

    if "capturas" in pasos and ef["capturas"]["ocr"]:
        pasos["ocr"] = {"script": "ocr_capturas.py", "with": [], "args": [str(salida), "--idioma", ef["idioma"]],
                        "parametros": {"idioma": ef["idioma"]}}

    if cfg["glosario"] or cfg["participantes"]:
        pasos["glosario"] = {"interno": True,
                             "parametros": {"terminos": cfg["glosario"], "personas": cfg["participantes"]}}

    html = [str(salida)]
    if opciones.get("titulo"):
        html += ["--titulo", opciones["titulo"]]
    if opciones.get("nota"):
        html += ["--nota", opciones["nota"]]
    if opciones.get("incrustar"):
        html.append("--incrustar")
    # Si ya no hay capturas u OCR (cambió el modo), que el HTML no muestre los archivos que quedaron.
    if "capturas" not in pasos:
        html.append("--sin-capturas")
    if "ocr" not in pasos:
        html.append("--sin-ocr")
    pasos["html"] = {"script": "armar_html.py", "with": [], "args": html,
                     "parametros": {"titulo": opciones.get("titulo") or "", "nota": opciones.get("nota") or "",
                                    "incrustar": bool(opciones.get("incrustar")),
                                    "capturas": "capturas" in pasos, "ocr": "ocr" in pasos}}

    previos = previo.get("pasos", {})
    solo, forzar = a.solo or set(), a.forzar or set()
    firmas, acciones = {}, {}
    for paso in PASOS:
        if paso not in pasos:
            continue
        deps = [d for d in DEPENDE[paso] if d in pasos]
        f = firma(VERSION_PASO[paso], pasos[paso]["parametros"], [firmas.get(d) for d in deps])
        prev = previos.get(paso, {})
        existe = (salida / SALIDA_DE[paso]).exists()
        dep_corre = [d for d in deps if acciones[d]["accion"] == "correr"]
        if solo and paso not in solo:
            accion, motivo = "omitir", "no se pidió (--solo)"
            f = prev.get("firma")
        elif "todo" in forzar or paso in forzar:
            accion, motivo = "correr", "forzado"
        elif dep_corre:
            accion, motivo = "correr", "se rehace " + ", ".join(NOMBRE[d] for d in dep_corre)
        elif prev.get("estado") == "completo" and prev.get("firma") == f and existe:
            accion, motivo = "al_dia", "sin cambios"
        else:
            accion, motivo = "correr", motivo_de(paso, prev, pasos[paso]["parametros"], existe)
        firmas[paso] = f
        acciones[paso] = {"accion": accion, "motivo": motivo, "firma": f}

    if acciones["html"]["accion"] == "correr" and acciones["transcripcion"]["accion"] == "omitir" \
            and not (salida / SALIDA_DE["transcripcion"]).exists():
        raise SystemExit(f"{ruta.name}: no hay transcripción todavía; corre primero sin --solo.")

    sugeridas = []
    if tipo != "transcripcion" and not importada:
        sugeridas = sorted(str(p) for p in ruta.parent.iterdir()
                           if p.is_file() and p.stem == ruta.stem and p.suffix.lower() in EXT_TRANSCRIPCION)
    return {"entrada": str(ruta), "tipo": tipo, "salida": str(salida), "procesada_antes": bool(previos),
            "transcripcion_sugerida": sugeridas, "opciones": opciones, "config": cfg, "pasos": pasos,
            "acciones": acciones, "avisos": avisos + cfg["avisos"]}


def resumen_config(cfg):
    return {
        "efectiva": cfg["efectiva"], "origen": cfg["origen"], "archivos": cfg["archivos"],
        "glosario": sorted(cfg["glosario"]), "participantes": [p["nombre"] for p in cfg["participantes"]],
        "presets": {k: v["descripcion"] for k, v in cfg["presets"].items()},
        "errores": cfg["errores"], "avisos": cfg["avisos"],
    }


# ───────────────────────── pantalla ─────────────────────────

class Pantalla:
    """Barras en una terminal; hitos en texto cuando no hay terminal. Siempre escribe progreso.json
    y _registro/hitos.log (lo que Claude puede seguir con Monitor)."""

    def __init__(self, entrada, salida, tty):
        self.entrada, self.salida, self.tty = entrada, salida, tty
        self.lock = threading.RLock()
        self.pasos = {}
        self.dibujadas = 0
        self.estado = "en_curso"
        self.inicio = ahora()
        self._ultimo_json = self._ultimo_dibujo = 0.0
        self.ruta_progreso = salida / "progreso.json"
        self.ruta_hitos = salida / "_registro" / "hitos.log"
        self.ruta_hitos.write_text("", encoding="utf-8")

    def registrar(self, paso, estado, fase=""):
        with self.lock:
            self.pasos[paso] = {"estado": estado, "fase": fase, "pct": None, "restante": None,
                                "detalle": "", "base": None, "hitos": set()}
            self._guardar(forzar=True)
            self._dibujar(forzar=True)

    def terminar(self, paso, estado, detalle=None):
        with self.lock:
            if paso in self.pasos:
                self.pasos[paso]["estado"] = estado
                if estado == "completo":
                    self.pasos[paso]["pct"] = 100.0
                if detalle is not None:
                    self.pasos[paso]["detalle"] = detalle
                self.pasos[paso]["restante"] = None
            self._guardar(forzar=True)
            self._dibujar(forzar=True)

    def linea(self, texto, imprimir=True):
        with self.lock:
            self._limpiar()
            if imprimir:
                print(texto, flush=True)
            with open(self.ruta_hitos, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now():%H:%M:%S} {texto}\n")
            self._dibujar(forzar=True)

    def evento(self, paso, datos):
        hito = None
        with self.lock:
            p = self.pasos.get(paso)
            if p is None:
                return
            if "fase" in datos:
                p["fase"], p["base"] = datos["fase"], None
            if datos.get("total"):
                hecho, total = datos["hecho"], datos["total"]
                p["pct"] = min(100.0, 100.0 * hecho / total)
                t = time.time()
                if p["base"] is None:
                    p["base"] = (t, hecho)
                t0, h0 = p["base"]
                if hecho - h0 > 0.02 * total and t > t0:
                    velocidad = (hecho - h0) / (t - t0)
                    p["restante"] = (total - hecho) / velocidad if velocidad > 0 else None
                p["detalle"] = " · ".join(f"{v} {k}" for k, v in datos.items()
                                          if k not in ("paso", "hecho", "total", "fase"))
                for h in HITOS:
                    if p["pct"] >= h and h not in p["hitos"]:
                        p["hitos"].add(h)
                        hito = h if p["pct"] < 100 else None  # al 100 % ya llega el «✓ listo»
            self._guardar()
            self._dibujar()
        if hito:
            resto = faltan(p["restante"])
            self.linea(f"▸ {NOMBRE[paso]}: {hito} %" + (f" · {resto}" if resto else ""), imprimir=not self.tty)

    def latido(self):
        with self.lock:
            self._guardar()
            self._dibujar()

    def _guardar(self, forzar=False):
        if not forzar and time.time() - self._ultimo_json < 1.0:
            return
        self._ultimo_json = time.time()
        escribir_json(self.ruta_progreso, {
            "version": 1, "entrada": str(self.entrada), "salida": str(self.salida), "estado": self.estado,
            "inicio": self.inicio, "actualizado": ahora(),
            "pasos": {k: {"nombre": NOMBRE[k], "estado": v["estado"], "fase": v["fase"],
                          "pct": round(v["pct"], 1) if v["pct"] is not None else None,
                          "restante_s": round(v["restante"]) if v["restante"] else None,
                          "detalle": v["detalle"]} for k, v in self.pasos.items()},
        })

    def _limpiar(self):
        if self.tty and self.dibujadas:
            sys.stdout.write(f"\x1b[{self.dibujadas}F\x1b[J")
            self.dibujadas = 0

    def _dibujar(self, forzar=False):
        if not self.tty or (not forzar and time.time() - self._ultimo_dibujo < 0.25):
            return
        self._ultimo_dibujo = time.time()
        filas = [fila(NOMBRE[k], v) for k, v in self.pasos.items() if v["estado"] in ("en_curso", "pendiente")]
        self._limpiar()
        for f in filas:
            sys.stdout.write(f + "\n")
        sys.stdout.flush()
        self.dibujadas = len(filas)


def fila(nombre, v, ancho=24):
    pct, restante = v.get("pct"), v.get("restante") or v.get("restante_s")
    if pct is None:
        barra, texto = "·" * ancho, "    "
    else:
        n = int(ancho * pct / 100)
        barra, texto = "█" * n + "░" * (ancho - n), f"{pct:3.0f} %"
    extra = " · ".join(x for x in (v.get("fase"), faltan(restante)) if x)
    columnas = shutil.get_terminal_size((100, 20)).columns - 1
    return f"  {nombre:<24} {barra} {texto}  {extra}"[:columnas]


# ───────────────────────── ejecución ─────────────────────────

def lanzar(uv, paso, spec, pantalla, registro):
    cmd = [uv, "run"]
    for paquete in spec["with"]:
        cmd += ["--with", paquete]
    cmd += ["--script", str(DIR / spec["script"]), *spec["args"]]
    env = {**os.environ, "MINUTAS_PROGRESO": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    log = open(registro / f"{paso}.log", "w", encoding="utf-8")
    log.write("$ " + " ".join(cmd) + "\n")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", env=env, bufsize=1)
    ultimas = deque(maxlen=15)

    def leer():
        for linea in proc.stdout:
            linea = linea.rstrip("\n")
            if linea.startswith(PREFIJO_PROGRESO):
                try:
                    pantalla.evento(paso, json.loads(linea[len(PREFIJO_PROGRESO):]))
                except ValueError:
                    pass
            elif linea.strip():
                log.write(linea + "\n")
                log.flush()
                ultimas.append(linea)

    hilo = threading.Thread(target=leer, daemon=True)
    hilo.start()
    return {"proc": proc, "hilo": hilo, "log": log, "ultimas": ultimas, "inicio": time.time()}


def resumen_de(paso, salida):
    if paso == "transcripcion":
        meta = (leer_json(salida / "transcripcion.json", {}) or {}).get("meta", {})
        partes = [f"{meta.get('segmentos', 0)} segmentos", f"{hms(meta.get('duracion') or 0)} de audio"]
        if meta.get("hablantes"):
            partes.append("hablantes: " + ", ".join(meta["hablantes"]))
        return " · ".join(partes)
    if paso == "capturas":
        datos = leer_json(salida / "capturas.json", {}) or {}
        capturas = datos.get("capturas", [])
        iguales = sum(1 for c in capturas if "igual_a" in c)
        texto = f"{len(capturas)} {'captura' if len(capturas) == 1 else 'capturas'}"
        if iguales:
            texto += f" ({iguales} {'repite' if iguales == 1 else 'repiten'} una pantalla anterior)"
        return texto + (" · se alcanzó el tope" if datos.get("meta", {}).get("truncado") else "")
    if paso == "ocr":
        capturas = (leer_json(salida / "ocr.json", {}) or {}).get("capturas", [])
        con_texto = sum(1 for c in capturas if c.get("lineas"))
        return f"{con_texto} de {len(capturas)} {'captura' if len(capturas) == 1 else 'capturas'} con texto"
    if paso == "glosario":
        datos = leer_json(salida / "glosario.json", {}) or {}
        con_variantes = sum(1 for t in datos.get("terminos", []) if t["variantes"])
        menciones = sum(p["menciones"] for p in datos.get("personas", []))
        terminos = "término mal escrito" if con_variantes == 1 else "términos mal escritos"
        return f"{con_variantes} {terminos} · {menciones} {'mención' if menciones == 1 else 'menciones'} de participantes"
    return SALIDA_DE[paso]


def correr_glosario(salida, parametros):
    _, segmentos = leer_transcripcion(salida)
    escribir_json(salida / "glosario.json", glosmod.buscar(segmentos, parametros["terminos"], parametros["personas"]))


def ejecutar(plan, uv, tty):
    salida = Path(plan["salida"])
    registro = salida / "_registro"
    registro.mkdir(parents=True, exist_ok=True)
    ruta_manifiesto = salida / "reunion.json"
    manifiesto = leer_json(ruta_manifiesto, {}) or {}
    if manifiesto.get("entrada", {}).get("ruta") not in (None, plan["entrada"]):
        manifiesto = {}
    manifiesto.update({
        "version": 1, "plugin": VERSION,
        "entrada": {"tipo": plan["tipo"], **identidad(plan["entrada"])},
        "salida": str(salida), "preset": plan["config"]["efectiva"]["preset"],
        "config": plan["config"]["efectiva"], "opciones": plan["opciones"],
    })
    manifiesto.setdefault("pasos", {})
    if "glosario" not in plan["pasos"]:  # se quitó el glosario: que la nota vieja no siga en el HTML
        (salida / "glosario.json").unlink(missing_ok=True)
        manifiesto["pasos"].pop("glosario", None)
    for paso in ("capturas", "ocr"):  # ya no aplican: el HTML los ignora (--sin-capturas, --sin-ocr)
        if paso not in plan["pasos"]:
            manifiesto["pasos"].pop(paso, None)

    def guardar():
        manifiesto["actualizado"] = ahora()
        escribir_json(ruta_manifiesto, manifiesto)

    pantalla = Pantalla(Path(plan["entrada"]), salida, tty)
    pantalla.linea(f"minutas-video {VERSION} · {Path(plan['entrada']).name} → {salida}")
    for aviso in plan["avisos"]:
        pantalla.linea(f"! {aviso}")
    acciones = plan["acciones"]
    for paso, acc in acciones.items():
        if acc["accion"] == "al_dia":
            pantalla.linea(f"· {NOMBRE[paso]}: al día, no se repite")
    correr = [p for p in PASOS if acciones.get(p, {}).get("accion") == "correr"]
    for p in correr:
        pantalla.registrar(p, "pendiente", "en espera")

    fallidos = set()

    def cerrar(paso, ok, inicio, ultimas=()):
        spec, acc = plan["pasos"][paso], acciones[paso]
        segundos = time.time() - inicio
        registro_paso = {"firma": acc["firma"], "parametros": spec["parametros"], "fin": ahora(),
                         "duracion_s": round(segundos, 1)}
        if ok:
            resumen = resumen_de(paso, salida)
            manifiesto["pasos"][paso] = {"estado": "completo", **registro_paso, "resumen": resumen, "error": None}
            pantalla.terminar(paso, "completo", resumen)
            pantalla.linea(f"✓ {NOMBRE[paso]}: listo en {duracion_corta(segundos)} · {resumen}")
        else:
            fallidos.add(paso)
            mensaje = ultimas[-1] if ultimas else "sin mensaje"
            manifiesto["pasos"][paso] = {"estado": "error", **registro_paso, "resumen": None,
                                         "error": "\n".join(ultimas) or mensaje}
            pantalla.terminar(paso, "error")
            pantalla.linea(f"✗ {NOMBRE[paso]}: falló · {mensaje}")
            pantalla.linea(f"  bitácora: {registro / (paso + '.log')}")
        guardar()

    def bloqueado(paso):
        bloqueo = [d for d in DEPENDE[paso] if d in fallidos and d not in OPCIONALES]
        if bloqueo:
            pantalla.terminar(paso, "omitido")
            pantalla.linea(f"· {NOMBRE[paso]}: no se hizo porque falló {', '.join(NOMBRE[d] for d in bloqueo)}")
            fallidos.add(paso)
        return bool(bloqueo)

    procesos = {}
    try:
        # Transcripción y capturas arrancan juntas; el OCR, en cuanto terminan las capturas.
        pendientes = [p for p in EXTERNOS if p in correr]
        while pendientes or procesos:
            for paso in list(pendientes):
                if any(d in pendientes or d in procesos for d in DEPENDE[paso]):
                    continue
                pendientes.remove(paso)
                if bloqueado(paso):
                    continue
                pantalla.registrar(paso, "en_curso", "preparando el entorno (la primera vez instala dependencias)")
                manifiesto["pasos"][paso] = {"estado": "en_curso", "inicio": ahora()}
                procesos[paso] = lanzar(uv, paso, plan["pasos"][paso], pantalla, registro)
                guardar()
            for paso in list(procesos):
                p = procesos[paso]
                if p["proc"].poll() is not None:
                    p["hilo"].join()
                    p["log"].close()
                    cerrar(paso, p["proc"].returncode == 0, p["inicio"], list(p["ultimas"]))
                    del procesos[paso]
            pantalla.latido()
            time.sleep(0.2)

        for paso in ("glosario", "html"):
            if paso not in correr or bloqueado(paso):
                continue
            inicio = time.time()
            pantalla.registrar(paso, "en_curso", "generando")
            if paso == "glosario":
                try:
                    correr_glosario(salida, plan["pasos"][paso]["parametros"])
                    cerrar(paso, True, inicio)
                except Exception as e:  # noqa: BLE001 — se reporta y se sigue con el HTML
                    cerrar(paso, False, inicio, [f"{type(e).__name__}: {e}"])
            else:
                p = lanzar(uv, paso, plan["pasos"][paso], pantalla, registro)
                p["proc"].wait()
                p["hilo"].join()
                p["log"].close()
                cerrar(paso, p["proc"].returncode == 0, inicio, list(p["ultimas"]))
    except KeyboardInterrupt:
        for p in procesos.values():
            p["proc"].terminate()
        for paso, datos in manifiesto["pasos"].items():
            if datos.get("estado") == "en_curso":
                datos["estado"] = "interrumpido"
        guardar()
        pantalla.estado = "interrumpido"
        for paso, datos in list(pantalla.pasos.items()):
            if datos["estado"] in ("en_curso", "pendiente"):
                pantalla.terminar(paso, "interrumpido")
        pantalla.linea("Interrumpido. Vuelve a correr el mismo comando para continuar.")
        raise SystemExit(130)

    pantalla.estado = "error" if fallidos else "completo"
    pantalla.latido()
    pantalla._guardar(forzar=True)
    if fallidos:
        pantalla.linea(f"TERMINÓ CON ERRORES ({', '.join(NOMBRE[p] for p in PASOS if p in fallidos)}) · {salida}")
    else:
        pantalla.linea(f"LISTO · {salida}")
    return not fallidos


# ───────────────────────── seguir ─────────────────────────

def seguir(salida):
    ruta = Path(salida) / "progreso.json"
    datos = leer_json(ruta)
    if datos is None:
        raise SystemExit(f"No hay {ruta}: el proceso no ha empezado o la carpeta no es una salida de minutas-video.")
    tty = sys.stdout.isatty()
    if tty and os.name == "nt":
        os.system("")  # activa las secuencias ANSI en la consola de Windows
    dibujadas = 0
    while True:
        datos = leer_json(ruta, datos)
        filas = [f"{Path(datos['entrada']).name} · {datos['estado']}"]
        filas += [fila(v["nombre"], v) + ("" if v["estado"] in ("en_curso", "pendiente") else f"  [{v['estado']}]")
                  for v in datos["pasos"].values()]
        if not tty:
            print("\n".join(filas))
            return
        if dibujadas:
            sys.stdout.write(f"\x1b[{dibujadas}F\x1b[J")
        sys.stdout.write("\n".join(filas) + "\n")
        sys.stdout.flush()
        dibujadas = len(filas)
        if datos["estado"] != "en_curso":
            return
        quieto = time.time() - datetime.fromisoformat(datos["actualizado"]).timestamp()
        if quieto > 60:
            print(f"Sin noticias desde hace {int(quieto)} s: el proceso parece detenido.")
            return
        time.sleep(0.5)


# ───────────────────────── main ─────────────────────────

def main():
    configurar_consola()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="comando", required=True)

    pp = sub.add_parser("procesar", help="procesa una o varias grabaciones")
    pp.add_argument("entradas", nargs="+", help="grabaciones, transcripciones .vtt/.srt o carpetas")
    pp.add_argument("--salida", help="carpeta de salida (solo con una entrada); por defecto <nombre>_minuta/ junto a la grabación")
    pp.add_argument("--preset", choices=list(cfgmod.PRESETS))
    pp.add_argument("--idioma", help="es, en, auto...")
    pp.add_argument("--modelo", help="modelo de Whisper: large-v3, large-v3-turbo, medium, small...")
    pp.add_argument("--dispositivo", choices=["auto", "cuda", "cpu"])
    pp.add_argument("--capturas", choices=["pantalla", "camara", "ninguna"])
    pp.add_argument("--max-capturas", type=int)
    pp.add_argument("--umbral-cambio", type=float)
    pp.add_argument("--ocr", action=argparse.BooleanOptionalAction, default=None,
                    help="leer el texto de las capturas (por defecto, sí)")
    pp.add_argument("--pista", type=int, help="pista de audio, si la grabación tiene varias")
    pp.add_argument("--transcripcion", help=".vtt/.srt de la plataforma en lugar de Whisper; 'whisper' para volver a Whisper")
    pp.add_argument("--titulo")
    pp.add_argument("--nota", help="aviso al inicio de la transcripción ilustrada")
    pp.add_argument("--incrustar", action=argparse.BooleanOptionalAction, default=None,
                    help="imágenes dentro del HTML (un solo archivo)")
    pp.add_argument("--solo", type=lista_pasos, help="solo estos pasos, separados por coma")
    pp.add_argument("--forzar", type=lista_pasos, help="rehacer estos pasos aunque estén al día ('todo' para todos)")
    pp.add_argument("--proyecto", help="carpeta del proyecto para buscar .minutas-video/ (por defecto, la actual)")
    pp.add_argument("--plan", action="store_true", help="muestra qué haría, en JSON, sin correr nada")

    ps = sub.add_parser("seguir", help="barra de progreso de un proceso en curso")
    ps.add_argument("salida")

    pc = sub.add_parser("config", help="configuración efectiva en JSON")
    pc.add_argument("--proyecto")

    pg = sub.add_parser("glosario", help="busca los términos del glosario en una transcripción")
    pg.add_argument("salida")
    pg.add_argument("--proyecto")

    pm = sub.add_parser("minuta", help="valida minuta.json, verifica la evidencia y genera minuta.md")
    pm.add_argument("salida")

    a = p.parse_args()

    if a.comando == "seguir":
        seguir(a.salida)
        return

    if a.comando == "config":
        rec = recomendar()
        cfg = cfgmod.cargar(a.proyecto, None, rec["recomendacion"])
        print(json.dumps({"config": resumen_config(cfg), "equipo": rec}, ensure_ascii=False, indent=1))
        return

    if a.comando == "glosario":
        cfg = cfgmod.cargar(a.proyecto)
        if cfg["errores"]:
            raise SystemExit("Errores de configuración:\n- " + "\n- ".join(cfg["errores"]))
        salida = Path(a.salida)
        correr_glosario(salida, {"terminos": cfg["glosario"], "personas": cfg["participantes"]})
        datos = leer_json(salida / "glosario.json")
        print(datos["nota"] or "No se encontraron variantes mal escritas.")
        print(f"→ {salida / 'glosario.json'}")
        return

    if a.comando == "minuta":
        sys.exit(minmod.comando(Path(a.salida)))

    entradas = expandir(a.entradas)
    if len(entradas) > 1 and (a.salida or a.transcripcion):
        raise SystemExit("--salida y --transcripcion solo valen con una entrada.")
    rec = recomendar()
    planes = [planear(r, a, rec) for r in entradas]

    if a.plan:
        print(json.dumps({
            "entradas": [{k: pl[k] for k in ("entrada", "tipo", "salida", "procesada_antes", "transcripcion_sugerida",
                                              "opciones", "acciones", "avisos")} for pl in planes],
            "config": resumen_config(planes[0]["config"]),
            "equipo": {k: rec[k] for k in ("sistema", "gpu_nvidia", "modelos_whisper_descargados", "recomendacion", "avisos")},
        }, ensure_ascii=False, indent=1))
        return

    errores = planes[0]["config"]["errores"]
    if errores:
        raise SystemExit("Corrige la configuración antes de procesar:\n- " + "\n- ".join(errores))

    tty = sys.stdout.isatty()
    if tty and os.name == "nt":
        os.system("")
    uv = localizar_uv()
    resultados = [ejecutar(pl, uv, tty) for pl in planes]
    if len(planes) > 1:
        print(f"{sum(resultados)} de {len(planes)} grabaciones sin errores.")
    sys.exit(0 if all(resultados) else 1)


if __name__ == "__main__":
    main()
