# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Arma la transcripción ilustrada: cada captura junto a lo que se dijo mientras estuvo visible.
Sin capturas (audio o modo ninguna) genera la transcripción sola, con hablantes si los hay.

Uso: uv run armar_html.py <salida> [--titulo "..."] [--nota "..."] [--incrustar]
  --incrustar  mete las imágenes dentro del HTML (un solo archivo portátil, más pesado).
               Sin esta opción, el HTML necesita la carpeta capturas/ al lado.
Lee transcripcion.json, capturas.json y glosario.json de <salida>; escribe transcripcion-ilustrada.html.
"""
import argparse
import base64
import bisect
import html
from pathlib import Path

from comun import agrupar, configurar_consola, hms, leer_capturas, leer_json, leer_transcripcion

COLORES = ["#2f5fd0", "#b0452a", "#1f8a5b", "#8a3fb5", "#b8860b", "#0f7c8c", "#c2377a", "#5b6b2f"]
COLORES_OSCURO = ["#8fb0ff", "#ff9a7a", "#6fd3a3", "#d0a0ff", "#f0c35a", "#6fd0de", "#ff8fc3", "#b8c97a"]

ESTILO = """
:root { --bg:#f6f6f4; --panel:#ffffff; --tx:#1d1d1f; --mut:#6b6b70; --ln:#e2e2de; --acc:#2f5fd0; color-scheme: light; %CL% }
@media (prefers-color-scheme: dark) {
  :root { --bg:#141416; --panel:#1d1d20; --tx:#e8e8ea; --mut:#9a9aa2; --ln:#2c2c31; --acc:#8fb0ff; color-scheme: dark; %CO% }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--tx); font: 16px/1.6 system-ui, "Segoe UI", sans-serif; }
header, main { max-width: 1440px; margin: 0 auto; padding-inline: 24px; }
main.solo { max-width: 860px; }
header { padding-block: 32px 12px; }
h1 { font-size: 1.5rem; margin: 0 0 6px; }
.meta { color: var(--mut); font-size: .9rem; margin: 0 0 4px; }
.nota { font-size: .9rem; margin: 8px 0 0; padding: 8px 12px; border-left: 3px solid var(--acc); background: var(--panel); }
nav { position: sticky; top: 0; z-index: 1; background: var(--bg); border-bottom: 1px solid var(--ln);
      padding: 6px 24px; overflow-x: auto; white-space: nowrap; }
nav a { display: inline-block; padding: 6px 8px; border-radius: 6px; color: var(--mut); text-decoration: none;
        font: 12px/1 ui-monospace, Consolas, monospace; }
nav a:hover { background: var(--panel); color: var(--acc); }
main { padding-block: 8px 64px; }
section { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 28px;
          padding-block: 24px; border-bottom: 1px solid var(--ln); scroll-margin-top: 44px; }
.img { position: sticky; top: 52px; align-self: start; }
.img img { display: block; width: 100%; height: auto; border: 1px solid var(--ln); border-radius: 6px; }
.tiempo { font: 600 13px/1.4 ui-monospace, Consolas, monospace; color: var(--acc); margin: 0 0 10px; }
.tiempo span { color: var(--mut); font-weight: 400; }
p { margin: 0 0 12px; }
p small { color: var(--mut); font: 11px ui-monospace, Consolas, monospace; margin-right: 6px; }
p b { margin-right: 4px; }
.vacio { color: var(--mut); font-style: italic; }
@media (max-width: 900px) { section { grid-template-columns: 1fr; } .img { position: static; } }
"""


def parrafos_html(segmentos, color_de):
    e = html.escape
    salida = []
    for grupo in agrupar(segmentos, pausa=2.0, max_palabras=70):
        texto = e(" ".join(s["texto"] for s in grupo))
        quien = grupo[0].get("hablante")
        nombre = f'<b style="color:var({color_de[quien]})">{e(quien)}:</b>' if quien else ""
        salida.append(f"<p><small>{hms(grupo[0]['inicio'])}</small>{nombre}{texto}</p>")
    return salida


def src_imagen(salida, archivo, incrustar):
    if not incrustar:
        return html.escape(archivo)
    datos = base64.b64encode((salida / archivo).read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{datos}"


def main():
    configurar_consola()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("salida")
    p.add_argument("--titulo")
    p.add_argument("--nota", default="")
    p.add_argument("--incrustar", action="store_true")
    a = p.parse_args()

    salida = Path(a.salida)
    meta, segmentos = leer_transcripcion(salida)
    _, capturas = leer_capturas(salida)
    titulo = a.titulo or f"Transcripción · {Path(meta.get('archivo', salida.name)).stem}"
    duracion = meta.get("duracion") or max((s["fin"] for s in segmentos), default=0)

    hablantes = meta.get("hablantes", [])
    color_de = {h: f"--h{i % len(COLORES)}" for i, h in enumerate(hablantes)}
    claros = " ".join(f"--h{i}:{c};" for i, c in enumerate(COLORES))
    oscuros = " ".join(f"--h{i}:{c};" for i, c in enumerate(COLORES_OSCURO))
    estilo = ESTILO.replace("%CL%", claros).replace("%CO%", oscuros)

    fuente = "importada" if meta.get("fuente") == "importada" else f"automática (Whisper {meta.get('modelo', '')}), sin corregir"
    detalles = [f"Duración {hms(duracion)}", f"{len(segmentos)} segmentos", f"transcripción {fuente}"]
    if capturas:
        detalles.insert(1, f"{len(capturas)} capturas de pantalla")
    if hablantes:
        detalles.append(f"hablantes: {', '.join(hablantes)}")

    e = html.escape
    partes = [
        '<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{e(titulo)}</title>\n<style>{estilo}</style>\n</head>\n<body>",
        f"<header><h1>{e(titulo)}</h1><p class=\"meta\">{e(' · '.join(detalles))}</p>",
    ]
    # La nota del glosario (glosario.json, si lo generó minutas.py) va sola: no hay que repetirla en --nota.
    nota_glosario = (leer_json(salida / "glosario.json", {}) or {}).get("nota", "")
    for nota in (a.nota, nota_glosario):
        if nota:
            partes.append(f'<p class="nota">{e(nota)}</p>')
    partes.append("</header>")

    if not capturas:
        partes.append('<main class="solo">')
        partes += parrafos_html(segmentos, color_de) or ['<p class="vacio">Sin texto.</p>']
        partes.append("</main>")
    else:
        partes.append("<nav>")
        partes += [f'<a href="#c{c["n"]:04}">{hms(c["desde"])}</a>' for c in capturas]
        partes.append("</nav>\n<main>")
        inicios = [c["desde"] for c in capturas]
        por_captura = [[] for _ in capturas]
        for s in segmentos:
            por_captura[max(bisect.bisect_right(inicios, s["inicio"]) - 1, 0)].append(s)
        for i, c in enumerate(capturas):
            hasta = capturas[i + 1]["desde"] if i + 1 < len(capturas) else duracion
            partes.append(f'<section id="c{c["n"]:04}">')
            img = (f'<img src="{src_imagen(salida, c["archivo"], a.incrustar)}" '
                   f'alt="Captura {c["n"]:04} en {hms(c["desde"])}" loading="lazy">')
            if not a.incrustar:  # incrustada no hay archivo al cual enlazar
                img = f'<a href="{e(c["archivo"])}" target="_blank">{img}</a>'
            partes.append(f'<div class="img">{img}</div>')
            partes.append(f'<div><p class="tiempo">{hms(c["desde"])} – {hms(hasta)} <span>· captura {c["n"]:04}</span></p>')
            partes += parrafos_html(por_captura[i], color_de) or ['<p class="vacio">Sin diálogo mientras esta pantalla estuvo visible.</p>']
            partes.append("</div></section>")
        partes.append("</main>")

    partes.append("</body>\n</html>\n")
    destino = salida / "transcripcion-ilustrada.html"
    destino.write_text("\n".join(partes), encoding="utf-8")
    print(f"HTML: {destino}")


if __name__ == "__main__":
    main()
