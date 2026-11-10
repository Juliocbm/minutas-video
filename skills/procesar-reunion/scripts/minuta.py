"""Minuta estructurada: valida minuta.json, verifica su evidencia y genera minuta.md.

minuta.json es la fuente única de la minuta. Quien la redacta (Claude) la escribe; minuta.md, y más
adelante las exportaciones, salen de ahí. Cada acuerdo, punto, pregunta, riesgo y pendiente lleva su
evidencia: el momento de la grabación, la cita textual y, si aplica, la captura.

La verificación busca cada cita en la transcripción cerca de ese momento y, si se indicó una captura,
en el texto de esa captura (ocr.json). No corrige nada: reporta lo que no cuadra para que quien
redacta lo arregle. Los términos del glosario se toman en cuenta: una cita puede decir «NEXO» donde
la transcripción dice «Nexus».

Formato de minuta.json: references/minuta.md. Solo biblioteca estándar.
"""
import bisect
import json
import re
import unicodedata
from collections import defaultdict
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

from comun import ancla, hms, leer_capturas, leer_json, leer_transcripcion

UMBRAL_CITA = 0.80       # parecido mínimo para dar una cita por verificada
UMBRAL_PARECIDA = 0.60   # por debajo, la cita "no aparece"; entre ambos, "se parece pero no es textual"
ANTES, DESPUES = 30, 90  # ventana alrededor del momento indicado: suele ser el inicio de un párrafo
LEJOS_CAPTURA = 120      # una captura citada a más de esto de su tiempo en pantalla se reporta
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]
TIPOS_PUNTO = {"punto": "", "dato": "", "propuesta": "Propuesta: ", "duda": "Duda abierta: ",
               "intencion": "Intención: "}
CON_EVIDENCIA = ("acuerdos", "preguntas", "riesgos", "pendientes")  # además, los puntos de cada tema

# ───────────────────────── esquema ─────────────────────────
# campo -> (tipo, requerido). Tipos: "texto", "bool", "entero", "tiempo", "plantilla", "tipo_punto",
# o una lista con el nombre del esquema de sus elementos.
EVIDENCIA = {"t": ("tiempo", True), "cita": ("texto", False), "captura": ("entero", False)}
BASE = {"texto": ("texto", True), "evidencia": (["evidencia"], False), "inferido": ("bool", False),
        "quien": ("texto", False)}
ESQUEMAS = {
    "raiz": {
        "version": ("entero", False), "plantilla": ("plantilla", False), "titulo": ("texto", True),
        "fecha": ("texto", False), "hora": ("texto", False), "lugar": ("texto", False),
        "nota": ("texto", False), "objetivo": ("texto", False), "resumen": ("texto", False),
        "participantes": (["participante"], False), "acuerdos": (["acuerdo"], False),
        "temas": (["tema"], False), "preguntas": (["elemento"], False), "riesgos": (["elemento"], False),
        "pendientes": (["pendiente"], False), "diferencias": (["diferencia"], False),
        "terminos": (["termino"], False),
    },
    "participante": {"nombre": ("texto", True), "rol": ("texto", False), "organizacion": ("texto", False),
                     "inferido": ("bool", False)},
    "evidencia": EVIDENCIA,
    "elemento": BASE,
    "acuerdo": {**BASE, "tema": ("texto", False), "discusion": (["texto"], False)},
    "punto": {**BASE, "tipo": ("tipo_punto", False)},
    "pendiente": {**BASE, "responsable": ("texto", False), "fecha": ("texto", False)},
    "tema": {"titulo": ("texto", True), "desde": ("tiempo", False), "hasta": ("tiempo", False),
             "puntos": (["punto"], False)},
    "diferencia": {"documento": ("texto", True), "dice": ("texto", True), "acordado": ("texto", True),
                   "evidencia": (["evidencia"], False), "verificado": ("bool", False)},
    "termino": {"forma": ("texto", True), "termino": ("texto", True)},
}
TIEMPO = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})(?:\.\d+)?$")


def segundos(valor):
    """12.5, "05:30" o "01:05:30" → segundos; None si no es un tiempo."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor) if valor >= 0 else None
    if isinstance(valor, str):
        m = TIEMPO.match(valor.strip())
        if m:
            h, mi, s = m.groups()
            return int(h or 0) * 3600 + int(mi) * 60 + int(s)
    return None


def _valido(valor, tipo):
    if tipo == "texto":
        return isinstance(valor, str)
    if tipo == "bool":
        return isinstance(valor, bool)
    if tipo == "entero":
        return isinstance(valor, int) and not isinstance(valor, bool)
    if tipo == "tiempo":
        return segundos(valor) is not None
    if tipo == "plantilla":
        return valor in ("completa", "corta")
    if tipo == "tipo_punto":
        return valor in TIPOS_PUNTO
    raise ValueError(tipo)


ESPERADO = {"texto": "texto", "bool": "true o false", "entero": "un número entero",
            "tiempo": "segundos o \"mm:ss\"", "plantilla": "\"completa\" o \"corta\"",
            "tipo_punto": " o ".join(f'"{t}"' for t in TIPOS_PUNTO)}


def validar(datos, esquema="raiz", ruta=""):
    """Errores de estructura: claves desconocidas, faltantes o de tipo equivocado."""
    errores = []
    if not isinstance(datos, dict):
        return [f"{ruta or 'minuta.json'}: debe ser un objeto {{...}}."]
    campos = ESQUEMAS[esquema]
    for clave in datos:
        if clave not in campos:
            errores.append(f"{ruta}{clave}: clave desconocida. Válidas aquí: {', '.join(campos)}.")
    for clave, (tipo, requerido) in campos.items():
        nombre = f"{ruta}{clave}"
        if clave not in datos or datos[clave] in (None, ""):
            if requerido:
                errores.append(f"{nombre}: falta.")
            continue
        valor = datos[clave]
        if isinstance(tipo, list):
            if not isinstance(valor, list):
                errores.append(f"{nombre}: debe ser una lista [...].")
                continue
            for i, elemento in enumerate(valor):
                if tipo[0] == "texto":
                    if not isinstance(elemento, str):
                        errores.append(f"{nombre}[{i}]: debe ser texto.")
                else:
                    errores += validar(elemento, tipo[0], f"{nombre}[{i}].")
        elif not _valido(valor, tipo):
            errores.append(f"{nombre}: debe ser {ESPERADO[tipo]} (vino {json.dumps(valor, ensure_ascii=False)}).")
    return errores


# ───────────────────────── búsqueda de citas ─────────────────────────

def normalizar(texto):
    """Palabras sin acentos ni mayúsculas ni puntuación: «¿Lo lanzamos el 27?» → [lo, lanzamos, el, 27]."""
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.findall(r"[^\W_]+", t)


def reemplazar(texto, reemplazos):
    for patron, termino in reemplazos:
        texto = patron.sub(termino, texto)
    return texto


class Texto:
    """Palabras normalizadas de un texto, con el segundo en que empieza el segmento de cada una."""

    def __init__(self, fragmentos, reemplazos=()):
        self.palabras, self.tiempos = [], []
        for t, texto in fragmentos:
            for w in normalizar(reemplazar(texto, reemplazos)):
                self.palabras.append(w)
                self.tiempos.append(t)
        self.indice = defaultdict(list)
        for i, w in enumerate(self.palabras):
            self.indice[w].append(i)

    def buscar(self, cita, desde=None, hasta=None):
        """(parecido 0-1, segundo) de la mejor ventana para `cita`, opcionalmente entre dos tiempos."""
        frase = normalizar(cita)
        if not frase or not self.palabras:
            return 0.0, None
        lo = 0 if desde is None else bisect.bisect_left(self.tiempos, desde)
        hi = len(self.palabras) if hasta is None else bisect.bisect_right(self.tiempos, hasta)
        if lo >= hi:
            return 0.0, None
        k = len(frase)
        # Se tolera que la cita omita muletillas: ventanas del mismo largo y un 30 % más largas.
        largos = sorted({k, round(k * 1.3) + 1})
        claves = {w for w in frase if len(w) >= 4} or set(frase)
        inicios = set()
        for w in claves:
            for pos in self.indice.get(w, ()):
                inicios.update(range(max(lo, pos - largos[-1] + 1), min(pos, hi - 1) + 1))
        sm = SequenceMatcher(autojunk=False)
        sm.set_seq2(frase)
        mejor = (0.0, None)
        for i in sorted(inicios):
            for largo in largos:
                sm.set_seq1(self.palabras[i:min(i + largo, hi)])
                if sm.real_quick_ratio() <= mejor[0] or sm.quick_ratio() <= mejor[0]:
                    continue
                r = sm.ratio()
                if r > mejor[0]:
                    mejor = (r, self.tiempos[i])
        return mejor


def partes_cita(cita):
    """Una cita puede saltarse un tramo con «…»: cada parte se busca por separado."""
    return [p for p in re.split(r"\s*(?:…|\.\.\.)\s*", cita) if normalizar(p)]


def buscar_cita(texto, cita, desde=None, hasta=None):
    resultados = [texto.buscar(p, desde, hasta) for p in partes_cita(cita)]
    if not resultados:
        return 0.0, None
    return min(r for r, _ in resultados), resultados[0][1]


# ───────────────────────── verificación ─────────────────────────

class Contexto:
    def __init__(self, salida, minuta):
        self.salida = Path(salida)
        self.meta, self.segmentos = leer_transcripcion(salida)
        self.duracion = self.meta.get("duracion") or max((s["fin"] for s in self.segmentos), default=0)
        _, capturas = leer_capturas(salida)
        self.capturas = {c["n"]: c for c in capturas}
        inicios = [c["desde"] for c in capturas]
        self.visible = {c["n"]: (c["desde"], inicios[i + 1] if i + 1 < len(inicios) else self.duracion)
                        for i, c in enumerate(capturas)}
        ocr = (leer_json(self.salida / "ocr.json", {}) or {}).get("capturas", [])
        self.ocr = {c["n"]: c.get("lineas", []) for c in ocr}
        self.terminos = terminos_corregidos(salida, minuta)
        self.reemplazos = [(re.compile(rf"(?<!\w){re.escape(forma)}(?!\w)", re.IGNORECASE), termino)
                           for forma, termino in self.terminos]
        self.texto = Texto([(s["inicio"], s["texto"]) for s in self.segmentos], self.reemplazos)
        self._ocr_texto = {}
        self.segundos_ancla = sorted({int(s["inicio"]) for s in self.segmentos})
        # Si la entrada fue solo un .vtt/.srt, no hubo grabación: los minutos son los de la transcripción.
        entrada = (leer_json(self.salida / "reunion.json", {}) or {}).get("entrada", {})
        self.solo_transcripcion = entrada.get("tipo") == "transcripcion"

    def texto_captura(self, n):
        if n not in self._ocr_texto:
            lineas = self.ocr.get(n, [])
            self._ocr_texto[n] = Texto([(0, linea) for linea in lineas], self.reemplazos)
        return self._ocr_texto[n]


def terminos_corregidos(salida, minuta):
    """(forma mal escrita, término) del glosario encontradas en la transcripción y de minuta.json."""
    pares = []
    for t in (leer_json(Path(salida) / "glosario.json", {}) or {}).get("terminos", []):
        pares += [(v["forma"], t["termino"]) for v in t.get("variantes", [])]
    pares += [(t["forma"], t["termino"]) for t in minuta.get("terminos", []) or []]
    vistos, unicos = set(), []
    for forma, termino in pares:
        if forma.lower() not in vistos and forma.strip():
            vistos.add(forma.lower())
            unicos.append((forma, termino))
    return unicos


def verificar_evidencia(ev, ctx):
    """Estado de una evidencia: (verificada: bool | None, problema: str | None).
    None = no hay cita que verificar (solo momento o captura)."""
    t = segundos(ev["t"])
    if t > ctx.duracion + 2:
        return False, f"el momento {hms(t)} está fuera de la grabación (dura {hms(ctx.duracion)})"
    n = ev.get("captura")
    if n is not None:
        if n not in ctx.capturas:
            return False, f"no existe la captura {n:04}"
        desde, hasta = ctx.visible[n]
        if t < desde - LEJOS_CAPTURA or t > hasta + LEJOS_CAPTURA:
            return False, (f"la captura {n:04} estuvo en pantalla de {hms(desde)} a {hms(hasta)}, "
                           f"lejos de {hms(t)}")
    cita = (ev.get("cita") or "").strip()
    if not cita:
        return None, None
    cerca, donde = buscar_cita(ctx.texto, cita, t - ANTES, t + DESPUES)
    if cerca >= UMBRAL_CITA:
        return True, None
    if n is not None and ctx.ocr.get(n):
        en_pantalla, _ = buscar_cita(ctx.texto_captura(n), cita)
        if en_pantalla >= UMBRAL_CITA:
            return True, None
    lejos, donde_lejos = buscar_cita(ctx.texto, cita)
    if lejos >= UMBRAL_CITA:
        return False, f"la cita está en {hms(donde_lejos)}, no cerca de {hms(t)}"
    if cerca >= UMBRAL_PARECIDA:
        return False, (f"la cita se parece ({cerca:.0%}) a lo dicho en {hms(donde)}, pero no es textual: "
                       "cópiala tal cual de la transcripción")
    en_captura = n is not None and bool(ctx.ocr.get(n))
    return False, "la cita no aparece en la transcripción" + (" ni en el texto de la captura" if en_captura else "")


def elementos(minuta):
    """(ruta, elemento, requiere evidencia) de todo lo que puede llevar evidencia."""
    for seccion in CON_EVIDENCIA:
        for i, el in enumerate(minuta.get(seccion) or []):
            yield f"{seccion}[{i}]", el, True
    for i, tema in enumerate(minuta.get("temas") or []):
        for j, el in enumerate(tema.get("puntos") or []):
            yield f"temas[{i}].puntos[{j}]", el, True
    for i, el in enumerate(minuta.get("diferencias") or []):
        yield f"diferencias[{i}]", el, False


def verificar(minuta, ctx):
    """Problemas de evidencia y conteo de citas."""
    problemas, total, verificadas = [], 0, 0
    for ruta, el, requiere in elementos(minuta):
        etiqueta = el.get("texto") or el.get("documento") or ""
        etiqueta = f"{ruta} «{etiqueta[:50]}{'…' if len(etiqueta) > 50 else ''}»"
        evidencias = el.get("evidencia") or []
        if not evidencias and requiere and not el.get("inferido"):
            problemas.append(f"{etiqueta}: sin evidencia (agrega el momento y la cita, o márcalo \"inferido\": true).")
        for j, ev in enumerate(evidencias):
            ok, problema = verificar_evidencia(ev, ctx)
            if ev.get("cita"):
                total += 1
                verificadas += bool(ok)
            if problema:
                problemas.append(f"{etiqueta} · evidencia[{j}] {hms(segundos(ev['t']))}: {problema}.")
    return {"problemas": problemas, "citas": total, "verificadas": verificadas}


# ───────────────────────── Markdown ─────────────────────────

def con_cola(texto, cola):
    """Pone la cola (quién, referencias) antes del punto final: «Texto (05:30).», no «Texto. (05:30)»."""
    texto = texto.rstrip()
    if texto.endswith(".") and not texto.endswith("..."):
        return texto[:-1] + cola + "."
    if texto.endswith(("?", "!", "…", ":")):
        return texto + cola
    return texto + cola + "."


def celda(texto):
    return str(texto or "").replace("|", "\\|").replace("\n", " ").strip()


def tiempo_corto(seg, larga):
    return hms(seg) if larga else hms(seg)[3:]


def fecha_larga(fecha, hora):
    try:
        d = date.fromisoformat(fecha)
        texto = f"{d.day} de {MESES[d.month - 1]} de {d.year}"
    except (TypeError, ValueError):
        texto = fecha or ""
    return ", ".join(x for x in (texto, hora) if x)


class Render:
    """Markdown de la minuta. Con enlaces=False (para exportar y compartir), los minutos y las capturas
    van como texto: quien recibe el documento no tiene la transcripción ilustrada ni las capturas."""

    def __init__(self, minuta, ctx, resultado, enlaces=True):
        self.m, self.ctx, self.res, self.enlaces = minuta, ctx, resultado, enlaces
        self.larga = ctx.duracion >= 3600

    def enlace_tiempo(self, seg):
        if not self.enlaces:
            return tiempo_corto(seg, self.larga)
        anclas = self.ctx.segundos_ancla
        i = bisect.bisect_right(anclas, int(seg)) - 1
        destino = anclas[max(i, 0)] if anclas else int(seg)
        return f"[{tiempo_corto(seg, self.larga)}](transcripcion-ilustrada.html#{ancla(destino)})"

    def enlace_captura(self, n, etiqueta=False):
        c = self.ctx.capturas.get(n)
        if not self.enlaces:  # en una tabla la columna ya dice «Captura»
            return f"captura {n:04}" if etiqueta else f"{n:04}"
        return f"[{n:04}]({c['archivo']})" if c else f"{n:04}"

    def tiempos(self, el):
        vistos = sorted({segundos(ev["t"]) for ev in el.get("evidencia") or []})
        return ", ".join(self.enlace_tiempo(t) for t in vistos)

    def capturas(self, el, etiqueta=False):
        ns = sorted({ev["captura"] for ev in el.get("evidencia") or [] if ev.get("captura") is not None})
        return ", ".join(self.enlace_captura(n, etiqueta) for n in ns)

    def refs(self, el):
        partes = [x for x in (self.tiempos(el), self.capturas(el, etiqueta=True)) if x]
        texto = f" ({' · '.join(partes)})" if partes else ""
        return texto + (" *(inferido)*" if el.get("inferido") else "")

    def vineta(self, el, prefijo=""):
        quien = f" — {el['quien']}" if el.get("quien") else ""
        return f"- {prefijo}{con_cola(el['texto'], quien + self.refs(el))}"

    def hay_capturas(self, seccion):
        return any(ev.get("captura") is not None for el in self.m.get(seccion) or [] for ev in el.get("evidencia") or [])

    def encabezado(self):
        m = self.m
        lineas = [f"# Minuta · {m['titulo']}", ""]
        if m.get("nota"):
            lineas += [f"> {m['nota']}", ""]
        return lineas

    def fecha(self):
        f = fecha_larga(self.m.get("fecha"), self.m.get("hora"))
        if not f and not self.m.get("lugar"):
            return ""
        return "**Fecha:** " + " · ".join(x for x in (f, self.m.get("lugar")) if x) + "."

    def fuente(self):
        meta = self.ctx.meta
        if meta.get("fuente") == "importada":
            trans = "transcripción importada" + (" con hablantes" if meta.get("hablantes") else "")
        else:
            trans = "transcripción automática" + (f" (Whisper {meta['modelo']})" if meta.get("modelo") else "")
        solo = self.ctx.solo_transcripcion
        partes = ([] if solo else ["grabación"]) + [trans] + (["capturas"] if self.ctx.capturas else [])
        texto = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]
        minutos = "los de la transcripción" if solo else "de la grabación"
        ilustrada = " ([transcripción ilustrada](transcripcion-ilustrada.html))" if self.enlaces else ""
        return (f"**Fuente:** {texto}{ilustrada}. "
                f"Los minutos son {minutos}.")

    def participantes_lista(self):
        grupos = {}
        for p in self.m.get("participantes") or []:
            nombre = p["nombre"] + (f" ({p['rol']})" if p.get("rol") else "") + (" *(inferido)*" if p.get("inferido") else "")
            grupos.setdefault(p.get("organizacion") or "", []).append(nombre)
        return grupos

    def pie(self):
        lineas = []
        if self.ctx.terminos:
            pares = "; ".join(f"«{f}» es {t}" for f, t in self.ctx.terminos)
            lineas += [f"*Términos que la transcripción automática escribe mal: {pares}.*", ""]
        if self.res["citas"]:
            lineas += [f"*Evidencia: {self.res['verificadas']} de {self.res['citas']} citas coinciden con la "
                       "transcripción o con el texto de la captura.*", ""]
        return ["---", ""] + lineas if lineas else []

    def pendientes_tabla(self):
        pendientes = self.m.get("pendientes") or []
        if not pendientes:
            return ["Ninguno.", ""]
        lineas = ["| # | Pendiente | Responsable | Fecha | Min. |", "|---|---|---|---|---|"]
        for i, p in enumerate(pendientes, start=1):
            texto = celda(p["texto"]) + (" *(inferido)*" if p.get("inferido") else "")
            lineas.append(f"| {i} | {texto} | {celda(p.get('responsable')) or '—'} | {celda(p.get('fecha')) or '—'} "
                          f"| {self.tiempos(p) or '—'} |")
        return lineas + [""]

    def completa(self):
        m, L = self.m, self.encabezado()
        cabecera = [x for x in (self.fecha(), self.fuente()) if x]
        L += ["  \n".join(cabecera), ""]
        grupos = self.participantes_lista()
        if grupos:
            L += ["**Participantes**"]
            L += [f"- {org}: {', '.join(nombres)}." if org else f"- {', '.join(nombres)}." for org, nombres in grupos.items()]
            L.append("")
        if m.get("objetivo"):
            L += [f"**Objetivo:** {m['objetivo']}", ""]
        if m.get("resumen"):
            L += [f"**En resumen:** {m['resumen']}", ""]
        L += ["---", ""]

        acuerdos = m.get("acuerdos") or []
        if acuerdos:
            con_tema, con_captura = any(a.get("tema") for a in acuerdos), self.hay_capturas("acuerdos")
            columnas = (["Tema"] if con_tema else []) + ["Acuerdo", "Min."] + (["Captura"] if con_captura else [])
            L += ["## Acuerdos", "", "| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
            for a in acuerdos:
                fila = ([celda(a.get("tema"))] if con_tema else []) + \
                       [celda(a["texto"]) + (" *(inferido)*" if a.get("inferido") else ""), self.tiempos(a) or "—"] + \
                       ([self.capturas(a) or "—"] if con_captura else [])
                L.append("| " + " | ".join(fila) + " |")
            L.append("")
            for a in acuerdos:
                if a.get("discusion"):
                    L += [f"**{a.get('tema') or a['texto']}.** Cómo se llegó al acuerdo:"]
                    L += [f"- {x}" for x in a["discusion"]] + [""]

        temas = m.get("temas") or []
        if temas:
            L += ["## Temas tratados", ""]
            for tema in temas:
                rango = ""
                if tema.get("desde") is not None:
                    rango = f" ({tiempo_corto(segundos(tema['desde']), self.larga)}"
                    rango += f" a {tiempo_corto(segundos(tema['hasta']), self.larga)})" if tema.get("hasta") is not None else ")"
                L += [f"### {tema['titulo']}{rango}"]
                for pt in tema.get("puntos") or []:
                    prefijo = TIPOS_PUNTO[pt.get("tipo") or "punto"]
                    L.append(self.vineta(pt, f"**{prefijo.strip()}** " if prefijo else ""))
                L.append("")

        for seccion, titulo in (("preguntas", "Preguntas abiertas"), ("riesgos", "Riesgos")):
            if m.get(seccion):
                L += [f"## {titulo}", ""] + [self.vineta(x) for x in m[seccion]] + [""]

        L += ["## Pendientes", ""] + self.pendientes_tabla()

        diferencias = m.get("diferencias") or []
        if diferencias:
            L += ["## Diferencias con documentos", "", "| Documento | Dice | La reunión acordó | Min. |", "|---|---|---|---|"]
            for d in diferencias:
                doc = f"`{celda(d['documento'])}`" + ("" if d.get("verificado", True) else " *(sin verificar en el documento)*")
                L.append(f"| {doc} | {celda(d['dice'])} | {celda(d['acordado'])} | {self.tiempos(d) or '—'} |")
            L.append("")
        return L + self.pie()

    def corta(self):
        m, L = self.m, self.encabezado()
        nombres = [p["nombre"] for p in m.get("participantes") or []]
        cabecera = " ".join(x for x in (self.fecha(), f"**Participantes:** {', '.join(nombres)}." if nombres else "") if x)
        if cabecera:
            L += [cabecera, ""]
        if m.get("resumen"):
            L += [f"**En resumen:** {m['resumen']}", ""]
        acuerdos = m.get("acuerdos") or []
        L += ["## Acuerdos", ""]
        L += [f"- {con_cola(a['texto'], self.refs(a))}" for a in acuerdos] or ["Ninguno."]
        L += ["", "## Pendientes", ""]
        pendientes = []
        for p in m.get("pendientes") or []:
            partes = [p["texto"].rstrip(".")] + [x for x in (p.get("responsable"), p.get("fecha")) if x]
            pendientes.append(f"- {' · '.join(partes)}{self.refs(p)}")
        L += pendientes or ["Ninguno."]
        return L + [""] + self.pie()

    def markdown(self):
        lineas = self.corta() if self.m.get("plantilla") == "corta" else self.completa()
        while lineas and lineas[-1] == "":
            lineas.pop()
        return "\n".join(lineas) + "\n"


# ───────────────────────── comando ─────────────────────────

def preparar(salida):
    """Lee, valida y verifica minuta.json. Devuelve (minuta, ctx, resultado) o un dict de error con
    "estado" ("falta" o "invalida") y "errores"."""
    salida = Path(salida)
    ruta = salida / "minuta.json"
    if not ruta.exists():
        return {"estado": "falta", "errores": [f"No existe {ruta}. Escríbela primero (formato en references/minuta.md)."]}
    try:
        minuta = json.loads(ruta.read_text(encoding="utf-8-sig"))
    except ValueError as e:
        return {"estado": "invalida", "errores": [f"{ruta} no es JSON válido: {e}"]}
    errores = validar(minuta)
    if errores:
        return {"estado": "invalida", "errores": errores}
    ctx = Contexto(salida, minuta)
    return minuta, ctx, verificar(minuta, ctx)


def procesar(salida):
    """Valida, verifica y genera minuta.md. Devuelve un dict con el resultado (ver comando())."""
    salida = Path(salida)
    preparada = preparar(salida)
    if isinstance(preparada, dict):
        return preparada
    minuta, ctx, resultado = preparada
    destino = salida / "minuta.md"
    destino.write_text(Render(minuta, ctx, resultado).markdown(), encoding="utf-8")
    conteo = {s: len(minuta.get(s) or []) for s in ("acuerdos", "temas", "pendientes", "preguntas", "riesgos", "diferencias")}
    return {"estado": "revisar" if resultado["problemas"] else "ok", "errores": [], "destino": str(destino),
            "conteo": conteo, **resultado}


def comando(salida):
    """Para `minutas.py minuta`: imprime el reporte. Código 0 si todo cuadra, 1 si hay evidencia que
    revisar (minuta.md se genera igual) y 2 si minuta.json no es válida (no se genera nada)."""
    r = procesar(salida)
    if r["estado"] in ("falta", "invalida"):
        print("minuta.json tiene errores; corrígelos y vuelve a correr el comando:")
        for e in r["errores"]:
            print(f"  - {e}")
        return 2
    partes = [f"{n} {nombre}" for nombre, n in r["conteo"].items() if n]
    print(f"minuta.json válida · {', '.join(partes) or 'sin elementos'}")
    if r["citas"]:
        print(f"Evidencia: {r['verificadas']} de {r['citas']} citas verificadas contra la transcripción y las capturas.")
    if r["problemas"]:
        print("Revisa en minuta.json:")
        for p in r["problemas"]:
            print(f"  - {p}")
    print(f"→ {r['destino']}")
    return 1 if r["problemas"] else 0
