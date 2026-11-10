"""Exporta la minuta para compartirla: PDF, Word (.docx) y CSV de pendientes.

Todo sale de minuta.json, validada y verificada igual que con `minutas.py minuta`. Los documentos van
sin enlaces a archivos locales: los minutos y las capturas se escriben como texto, porque quien recibe
el PDF o el Word no tiene la transcripción ilustrada.

- PDF: el Markdown de la minuta se convierte a HTML con estilos de impresión y lo imprime Edge o
  Chrome en modo headless (con un perfil temporal, para no chocar con el navegador abierto).
- Word: exportar_docx.py, con python-docx (tiene sus propias dependencias; lo corre uv).
- CSV: pendientes con responsable, fecha, minuto y cita, en UTF-8 con BOM para que Excel respete los
  acentos.

Solo biblioteca estándar. Lo usa `minutas.py exportar`.
"""
import csv
import html
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import minuta as minmod

FORMATOS = ("pdf", "docx", "csv")
ARCHIVO = {"pdf": "minuta.pdf", "docx": "minuta.docx", "csv": "pendientes.csv"}

# ───────────────────────── Markdown de la minuta → bloques ─────────────────────────
# Solo el subconjunto que genera minuta.py: títulos, párrafos (con saltos «  \n»), citas «> »,
# viñetas «- », tablas «| … |» y separadores «---».


def bloques(markdown):
    salida, parrafo = [], []

    def cerrar_parrafo():
        if parrafo:
            salida.append({"tipo": "p", "lineas": list(parrafo)})
            parrafo.clear()

    for linea in markdown.splitlines():
        texto = linea.rstrip()
        if not texto:
            cerrar_parrafo()
            continue
        m = re.match(r"^(#{1,3}) (.*)$", texto)
        if m:
            cerrar_parrafo()
            salida.append({"tipo": f"h{len(m.group(1))}", "texto": m.group(2)})
        elif texto == "---":
            cerrar_parrafo()
            salida.append({"tipo": "hr"})
        elif texto.startswith("> "):
            cerrar_parrafo()
            salida.append({"tipo": "cita", "texto": texto[2:]})
        elif texto.startswith("- "):
            cerrar_parrafo()
            if salida and salida[-1]["tipo"] == "lista":
                salida[-1]["items"].append(texto[2:])
            else:
                salida.append({"tipo": "lista", "items": [texto[2:]]})
        elif texto.startswith("|"):
            cerrar_parrafo()
            celdas = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", texto.strip())[1:-1]]
            if all(re.fullmatch(r"-{3,}", c) for c in celdas):
                continue  # la línea |---|---|
            if salida and salida[-1]["tipo"] == "tabla":
                salida[-1]["filas"].append(celdas)
            else:
                salida.append({"tipo": "tabla", "filas": [celdas]})
        else:
            parrafo.append(texto.strip())
    cerrar_parrafo()
    return salida


def inline(texto):
    """Partes de una línea: [(texto, {"b", "i", "code"}), …]. Los enlaces [x](y) quedan como x."""
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)
    partes = []
    for trozo in re.split(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)", texto):
        if not trozo:
            continue
        if trozo.startswith("**") and trozo.endswith("**") and len(trozo) > 4:
            partes.append((trozo[2:-2], {"b"}))
        elif trozo.startswith("`") and trozo.endswith("`") and len(trozo) > 2:
            partes.append((trozo[1:-1], {"code"}))
        elif trozo.startswith("*") and trozo.endswith("*") and len(trozo) > 2:
            partes.append((trozo[1:-1], {"i"}))
        else:
            partes.append((trozo, set()))
    return partes


def plano(texto):
    return "".join(t for t, _ in inline(texto))


# ───────────────────────── HTML para imprimir ─────────────────────────

ESTILO_PDF = """
@page { size: Letter; margin: 18mm 16mm; }
body { font: 10.5pt/1.45 "Segoe UI", system-ui, -apple-system, Arial, sans-serif; color: #1d1d1f; }
h1 { font-size: 18pt; margin: 0 0 10px; }
h2 { font-size: 13pt; margin: 18px 0 6px; padding-bottom: 3px; border-bottom: 1px solid #d9d9d4; }
h3 { font-size: 11pt; margin: 12px 0 4px; }
p, ul { margin: 0 0 8px; }
li { margin-bottom: 3px; }
blockquote { margin: 0 0 10px; padding: 6px 10px; border-left: 3px solid #2f5fd0; background: #f3f5fb; }
table { border-collapse: collapse; width: 100%; margin: 4px 0 10px; font-size: 9.5pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th, td { border: 1px solid #d9d9d4; padding: 4px 6px; text-align: left; vertical-align: top; }
th { background: #f1f1ee; }
hr { border: 0; border-top: 1px solid #d9d9d4; margin: 12px 0; }
code { font: 9pt Consolas, ui-monospace, monospace; }
"""


def _html_inline(texto):
    salida = []
    for t, estilos in inline(texto):
        t = html.escape(t)
        if "code" in estilos:
            t = f"<code>{t}</code>"
        if "b" in estilos:
            t = f"<strong>{t}</strong>"
        if "i" in estilos:
            t = f"<em>{t}</em>"
        salida.append(t)
    return "".join(salida)


def a_html(bs, titulo):
    partes = ['<!doctype html><html lang="es"><head><meta charset="utf-8">',
              f"<title>{html.escape(titulo)}</title><style>{ESTILO_PDF}</style></head><body>"]
    for b in bs:
        t = b["tipo"]
        if t in ("h1", "h2", "h3"):
            partes.append(f"<{t}>{_html_inline(b['texto'])}</{t}>")
        elif t == "p":
            partes.append("<p>" + "<br>".join(_html_inline(x) for x in b["lineas"]) + "</p>")
        elif t == "cita":
            partes.append(f"<blockquote>{_html_inline(b['texto'])}</blockquote>")
        elif t == "lista":
            partes.append("<ul>" + "".join(f"<li>{_html_inline(x)}</li>" for x in b["items"]) + "</ul>")
        elif t == "tabla":
            cabeza, *filas = b["filas"]
            partes.append("<table><thead><tr>" + "".join(f"<th>{_html_inline(c)}</th>" for c in cabeza) + "</tr></thead><tbody>")
            partes += ["<tr>" + "".join(f"<td>{_html_inline(c)}</td>" for c in f) + "</tr>" for f in filas]
            partes.append("</tbody></table>")
        elif t == "hr":
            partes.append("<hr>")
    partes.append("</body></html>")
    return "\n".join(partes)


def navegador():
    """Edge o Chrome (o Chromium) para imprimir a PDF; None si no hay."""
    candidatos = []
    if os.name == "nt":
        for base in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES"), os.environ.get("LOCALAPPDATA")):
            if base:
                candidatos += [Path(base) / "Microsoft/Edge/Application/msedge.exe",
                               Path(base) / "Google/Chrome/Application/chrome.exe"]
    else:
        candidatos += [Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
                       Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                       Path("/Applications/Chromium.app/Contents/MacOS/Chromium")]
    candidatos += [shutil.which(n) for n in ("msedge", "microsoft-edge", "google-chrome", "google-chrome-stable",
                                             "chromium", "chromium-browser", "chrome")]
    for c in candidatos:
        if c and Path(c).exists():
            return str(c)
    return None


def imprimir_pdf(html_texto, destino):
    nav = navegador()
    if not nav:
        raise RuntimeError("No se encontró Edge ni Chrome para imprimir el PDF.")
    destino = Path(destino).resolve()
    destino.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        pagina = Path(tmp) / "minuta.html"
        pagina.write_text(html_texto, encoding="utf-8")
        cmd = [nav, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
               f"--user-data-dir={Path(tmp) / 'perfil'}", "--no-pdf-header-footer", "--print-to-pdf-no-header",
               f"--print-to-pdf={destino}", pagina.as_uri()]
        subprocess.run(cmd, capture_output=True, timeout=120)
    if not destino.exists() or destino.stat().st_size == 0:
        raise RuntimeError(f"{Path(nav).name} no generó el PDF.")


# ───────────────────────── CSV ─────────────────────────

def escribir_csv(minuta, render, destino):
    with open(destino, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["#", "Pendiente", "Responsable", "Fecha", "Minuto", "Cita", "Inferido"])
        for i, p in enumerate(minuta.get("pendientes") or [], start=1):
            evidencia = p.get("evidencia") or []
            w.writerow([i, plano(p["texto"]), p.get("responsable", ""), p.get("fecha", ""), render.tiempos(p),
                        " | ".join(ev["cita"] for ev in evidencia if ev.get("cita")),
                        "sí" if p.get("inferido") else ""])


# ───────────────────────── comando ─────────────────────────

def markdown_para_compartir(salida):
    """(markdown sin enlaces, minuta, render) o un dict de error de minuta.preparar()."""
    preparada = minmod.preparar(salida)
    if isinstance(preparada, dict):
        return preparada
    m, ctx, resultado = preparada
    render = minmod.Render(m, ctx, resultado, enlaces=False)
    return render.markdown(), m, render


def comando(salida, formatos, correr_docx):
    """Para `minutas.py exportar`. `correr_docx(salida)` corre exportar_docx.py con uv y devuelve
    (código, salida). Código 0 si todo se exportó, 1 si algún formato falló, 2 si minuta.json no es válida."""
    salida = Path(salida)
    preparada = markdown_para_compartir(salida)
    if isinstance(preparada, dict):
        print("minuta.json tiene errores; corrígelos con `minutas.py minuta` antes de exportar:")
        for e in preparada["errores"]:
            print(f"  - {e}")
        return 2
    md, m, render = preparada
    res = render.res
    if res["problemas"]:
        print(f"Aviso: {len(res['problemas'])} problemas de evidencia sin corregir (ver `minutas.py minuta`); "
              f"el documento dice cuántas citas se verificaron.")
    fallos = 0
    for formato in formatos:
        destino = salida / ARCHIVO[formato]
        try:
            if formato == "csv":
                escribir_csv(m, render, destino)
            elif formato == "pdf":
                imprimir_pdf(a_html(bloques(md), f"Minuta · {m['titulo']}"), destino)
            else:
                codigo, texto = correr_docx(salida)
                if codigo != 0:
                    raise RuntimeError(texto.strip().splitlines()[-1] if texto.strip() else f"código {codigo}")
            print(f"✓ {formato.upper()}: {destino}")
        except Exception as e:  # noqa: BLE001 — un formato que falla no detiene a los demás
            fallos += 1
            print(f"✗ {formato.upper()}: {e}")
    return 1 if fallos else 0
