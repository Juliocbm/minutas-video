# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Arma la transcripción ilustrada: cada captura junto a lo que se dijo mientras estuvo visible.
Sin capturas (audio o modo ninguna) genera la transcripción sola, con hablantes si los hay.

Uso: uv run armar_html.py <salida> [--titulo "..."] [--nota "..."] [--medio <grabación>]
                                   [--incrustar] [--sin-capturas] [--sin-ocr]
  --medio         la grabación: agrega un reproductor; clic en una frase salta a ese momento.
                  Se enlaza (ruta relativa a <salida>), no se copia: si se mueve, el reproductor avisa.
  --incrustar     mete las imágenes dentro del HTML (un solo archivo portátil, más pesado).
                  Sin esta opción, el HTML necesita la carpeta capturas/ al lado.
  --sin-capturas  ignora capturas.json (por ejemplo, si se cambió a --capturas ninguna).
  --sin-ocr       ignora ocr.json.
Lee transcripcion.json, capturas.json, ocr.json y glosario.json de <salida>; escribe transcripcion-ilustrada.html.

Cada frase lleva su segundo (data-t) y un ancla #t<segundo> (la primera que empieza en ese segundo):
minuta.md enlaza a ellas y, con reproductor, el enlace también lleva la grabación a ese momento.
La búsqueda (lo dicho y el texto de las capturas) y el filtro por hablante funcionan sin conexión.
"""
import argparse
import base64
import bisect
import html
import os
from pathlib import Path
from urllib.parse import quote

from comun import agrupar, ancla, configurar_consola, hms, leer_capturas, leer_json, leer_transcripcion

COLORES = ["#2f5fd0", "#b0452a", "#1f8a5b", "#8a3fb5", "#b8860b", "#0f7c8c", "#c2377a", "#5b6b2f"]
COLORES_OSCURO = ["#8fb0ff", "#ff9a7a", "#6fd3a3", "#d0a0ff", "#f0c35a", "#6fd0de", "#ff8fc3", "#b8c97a"]
EXT_AUDIO = {".m4a", ".mp3", ".wav", ".ogg", ".opus", ".flac", ".aac", ".wma"}

ESTILO = """
:root { --bg:#f6f6f4; --panel:#ffffff; --tx:#1d1d1f; --mut:#6b6b70; --ln:#e2e2de; --acc:#2f5fd0; --marca:#fff1a8;
        --actual:rgba(47,95,208,.14); color-scheme: light; %CL% }
@media (prefers-color-scheme: dark) {
  :root { --bg:#141416; --panel:#1d1d20; --tx:#e8e8ea; --mut:#9a9aa2; --ln:#2c2c31; --acc:#8fb0ff; --marca:#5a4b00;
          --actual:rgba(143,176,255,.2); color-scheme: dark; %CO% }
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
body { margin: 0; background: var(--bg); color: var(--tx); font: 16px/1.6 system-ui, "Segoe UI", sans-serif; }
header, main { max-width: 1440px; margin: 0 auto; padding-inline: 24px; }
main.solo { max-width: 860px; }
header { padding-block: 32px 12px; }
h1 { font-size: 1.5rem; margin: 0 0 6px; }
.meta { color: var(--mut); font-size: .9rem; margin: 0 0 4px; }
.nota { font-size: .9rem; margin: 8px 0 0; padding: 8px 12px; border-left: 3px solid var(--acc); background: var(--panel); }
nav { position: sticky; top: 0; z-index: 2; background: var(--bg); border-bottom: 1px solid var(--ln);
      padding: 6px 24px; display: flex; flex-wrap: wrap; gap: 6px 16px; align-items: center; }
.herramientas { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.herramientas input, .herramientas select, .herramientas button, #reproductor button {
  font: 13px system-ui, "Segoe UI", sans-serif; color: var(--tx); background: var(--panel);
  border: 1px solid var(--ln); border-radius: 6px; padding: 5px 8px; }
.herramientas input { width: min(300px, 60vw); }
.herramientas button, #reproductor button { cursor: pointer; min-width: 30px; }
#conteo { color: var(--mut); font-size: 12px; min-width: 7ch; }
.tiempos { flex: 1 1 300px; min-width: 0; overflow-x: auto; white-space: nowrap; }
.tiempos a { display: inline-block; padding: 6px 8px; border-radius: 6px; color: var(--mut); text-decoration: none;
             font: 12px/1 ui-monospace, Consolas, monospace; }
.tiempos a:hover { background: var(--panel); color: var(--acc); }
main { padding-block: 8px 64px; }
body.con-medio main { padding-bottom: 45vh; }
section { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 28px;
          padding-block: 24px; border-bottom: 1px solid var(--ln); scroll-margin-top: 56px; }
.img { position: sticky; top: 56px; align-self: start; }
.img img { display: block; width: 100%; height: auto; border: 1px solid var(--ln); border-radius: 6px; }
.tiempo { font: 600 13px/1.4 ui-monospace, Consolas, monospace; color: var(--acc); margin: 0 0 10px; }
.tiempo span { color: var(--mut); font-weight: 400; }
p { margin: 0 0 12px; }
p small { color: var(--mut); font: 11px ui-monospace, Consolas, monospace; margin-right: 6px; }
p b { margin-right: 4px; }
.vacio { color: var(--mut); font-style: italic; }
span[data-t] { scroll-margin-top: 72px; border-radius: 3px; }
span:target { background: var(--marca); }
body.con-medio span[data-t] { cursor: pointer; }
body.con-medio span[data-t]:hover { text-decoration: underline dotted var(--mut); }
span.actual { background: var(--actual); }
.coincide { background: var(--marca); }
.coincide-actual { outline: 2px solid var(--acc); outline-offset: 1px; }
::highlight(busqueda) { background: var(--marca); color: inherit; }
@supports selector(::highlight(x)) { .coincide { background: none; } }  /* se marcan solo las palabras */
details.ocr { margin: 0 0 14px; font-size: .85rem; color: var(--mut); }
details.ocr summary { cursor: pointer; }
details.ocr div { margin-top: 6px; padding: 8px 12px; background: var(--panel); border: 1px solid var(--ln);
                  border-radius: 6px; white-space: pre-line; font: 12px/1.5 ui-monospace, Consolas, monospace; }
#reproductor { position: fixed; z-index: 3; background: var(--panel); border: 1px solid var(--ln);
               border-radius: 8px; box-shadow: 0 6px 24px rgba(0,0,0,.18); overflow: hidden; }
#reproductor.video { bottom: 16px; right: 16px; width: min(400px, calc(100vw - 32px)); }
body.con-capturas #reproductor.video { right: auto; left: 16px; }
#reproductor.audio { left: 0; right: 0; bottom: 0; border-radius: 0; }
#reproductor .barra { display: flex; gap: 8px; align-items: center; padding: 6px 10px; font-size: 13px; color: var(--mut); }
#reproductor .barra .titulo { flex: 1; }
#reproductor video { display: block; width: 100%; background: #000; }
#reproductor audio { display: block; width: 100%; }
#reproductor.mini video { display: none; }
#sin-medio { margin: 0; padding: 8px 10px; font-size: 13px; }
@media (max-width: 900px) { section { grid-template-columns: 1fr; } .img { position: static; }
                            body.con-capturas #reproductor.video { left: auto; right: 16px; } }
"""

SCRIPT = r"""
(() => {
  const $ = id => document.getElementById(id);
  const frases = [...document.querySelectorAll('span[data-t]')];

  // ── Búsqueda: todas las palabras, sin acentos ni mayúsculas, en lo dicho y en el texto de las capturas.
  const norm = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const objetivos = [...frases, ...document.querySelectorAll('details.ocr > div')];
  const textos = objetivos.map(el => norm(el.textContent));
  const buscar = $('buscar'), conteo = $('conteo');
  let hallados = [], pos = -1, espera;
  const visible = el => { const p = el.closest('p'); return !p || !p.hidden; };
  // Rangos de cada palabra buscada dentro de un elemento (para ::highlight), sin tocar el HTML.
  function rangos(el, palabras) {
    const salida = [], recorrido = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let nodo; (nodo = recorrido.nextNode());) {
      let plano = '';
      const mapa = [];
      for (let i = 0; i < nodo.data.length; i++) for (const c of norm(nodo.data[i])) { plano += c; mapa.push(i); }
      for (const w of palabras) {
        for (let k = plano.indexOf(w); k >= 0; k = plano.indexOf(w, k + w.length)) {
          const r = new Range();
          r.setStart(nodo, mapa[k]);
          r.setEnd(nodo, mapa[k + w.length - 1] + 1);
          salida.push(r);
        }
      }
    }
    return salida;
  }
  function buscarAhora() {
    hallados.forEach(el => el.classList.remove('coincide', 'coincide-actual'));
    const palabras = norm(buscar.value).split(/\s+/).filter(Boolean);
    hallados = palabras.length ? objetivos.filter((el, i) => visible(el) && palabras.every(w => textos[i].includes(w))) : [];
    hallados.sort((a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) ? -1 : 1);
    hallados.forEach(el => el.classList.add('coincide'));
    if (window.CSS && CSS.highlights) CSS.highlights.set('busqueda', new Highlight(...hallados.flatMap(el => rangos(el, palabras))));
    pos = -1;
    conteo.textContent = !palabras.length ? '' : hallados.length ? '' : 'sin resultados';
    if (hallados.length) mover(1);
  }
  function mover(paso) {
    if (!hallados.length) return;
    if (hallados[pos]) hallados[pos].classList.remove('coincide-actual');
    pos = (pos + paso + hallados.length) % hallados.length;
    const el = hallados[pos], det = el.closest('details');
    if (det) det.open = true;
    el.classList.add('coincide-actual');
    el.scrollIntoView({block: 'center'});
    conteo.textContent = (pos + 1) + ' de ' + hallados.length;
  }
  buscar.addEventListener('input', () => { clearTimeout(espera); espera = setTimeout(buscarAhora, 200); });
  buscar.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); mover(e.shiftKey ? -1 : 1); } });
  $('anterior').addEventListener('click', () => mover(-1));
  $('siguiente').addEventListener('click', () => mover(1));

  // ── Filtro por hablante.
  const hablante = $('hablante');
  if (hablante) hablante.addEventListener('change', () => {
    document.querySelectorAll('p[data-hablante]').forEach(p => { p.hidden = !!hablante.value && p.dataset.hablante !== hablante.value; });
    if (buscar.value) buscarAhora();
  });

  // ── Reproductor: clic en una frase salta a ese momento; la frase que suena se resalta y se sigue.
  const medio = $('medio');
  if (!medio) return;
  document.body.classList.add('con-medio');
  const tiempos = frases.map(s => +s.dataset.t), seguir = $('seguir');
  const ir = (t, reproducir) => { medio.currentTime = t; if (reproducir) medio.play().catch(() => {}); };
  document.querySelector('main').addEventListener('click', e => {
    const s = e.target.closest('span[data-t]');
    if (s && !String(window.getSelection())) ir(+s.dataset.t, true);
  });
  let actual = null;
  medio.addEventListener('timeupdate', () => {
    let lo = 0, hi = tiempos.length;
    while (lo < hi) { const m = (lo + hi) >> 1; if (tiempos[m] <= medio.currentTime + 0.05) lo = m + 1; else hi = m; }
    const s = frases[Math.max(lo - 1, 0)];
    if (!s || s === actual) return;
    if (actual) actual.classList.remove('actual');
    s.classList.add('actual');
    actual = s;
    if (seguir.checked && !medio.paused && visible(s)) s.scrollIntoView({block: 'center', behavior: 'smooth'});
  });
  // Quien hace scroll a mano quiere leer otra cosa: se deja de seguir.
  ['wheel', 'touchmove'].forEach(ev => window.addEventListener(ev, () => { seguir.checked = false; }, {passive: true}));
  const desdeAncla = () => { const m = location.hash.match(/^#t(\d+)$/); if (m) ir(+m[1], false); };
  if (medio.readyState >= 1) desdeAncla(); else medio.addEventListener('loadedmetadata', desdeAncla, {once: true});
  window.addEventListener('hashchange', desdeAncla);
  medio.addEventListener('error', () => { $('sin-medio').hidden = false; medio.hidden = true; });
  const mini = $('mini');
  if (mini) mini.addEventListener('click', () => {
    const r = $('reproductor'), achicar = !r.classList.contains('mini');
    r.classList.toggle('mini', achicar);
    mini.textContent = achicar ? '▢' : '–';
    mini.title = achicar ? 'Mostrar el video' : 'Ocultar el video (sigue sonando)';
  });
})();
"""


def parrafos_html(segmentos, color_de, anclas):
    """Párrafos por hablante y pausa. Cada frase va en un <span> con su segundo (data-t) y, si está libre,
    el ancla de ese segundo."""
    e = html.escape
    salida = []
    for grupo in agrupar(segmentos, pausa=2.0, max_palabras=70):
        frases = []
        for s in grupo:
            a = ancla(s["inicio"])
            id_ = ""
            if a not in anclas:
                anclas.add(a)
                id_ = f' id="{a}"'
            frases.append(f'<span data-t="{s["inicio"]:.2f}"{id_}>{e(s["texto"])}</span>')
        quien = grupo[0].get("hablante")
        nombre = f'<b style="color:var({color_de[quien]})">{e(quien)}:</b>' if quien else ""
        atributo = f' data-hablante="{e(quien)}"' if quien else ""
        salida.append(f"<p{atributo}><small>{hms(grupo[0]['inicio'])}</small>{nombre}{' '.join(frases)}</p>")
    return salida


def texto_ocr(lineas):
    if not lineas:
        return ""
    n = len(lineas)
    return (f'<details class="ocr"><summary>Texto en pantalla ({n} {"línea" if n == 1 else "líneas"}, OCR)</summary>'
            f'<div>{html.escape(chr(10).join(lineas))}</div></details>')


def src_imagen(salida, archivo, incrustar):
    if not incrustar:
        return html.escape(archivo)
    datos = base64.b64encode((salida / archivo).read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{datos}"


def src_medio(salida, medio):
    """URL de la grabación relativa a la carpeta de salida (o absoluta si está en otra unidad)."""
    ruta = Path(medio).resolve()
    try:
        relativa = os.path.relpath(ruta, Path(salida).resolve())
    except ValueError:  # Windows: otra unidad
        return ruta.as_uri()
    return quote(relativa.replace(os.sep, "/"))


def reproductor_html(salida, medio):
    ruta = Path(medio)
    if not ruta.exists():
        print(f"AVISO: no existe {ruta}; la transcripción ilustrada queda sin reproductor.")
        return ""
    e = html.escape
    src = e(src_medio(salida, ruta))
    audio = ruta.suffix.lower() in EXT_AUDIO
    etiqueta = "audio" if audio else "video"
    mini = "" if audio else '<button type="button" id="mini" title="Ocultar el video (sigue sonando)">–</button>'
    return (f'<div id="reproductor" class="{etiqueta}"><div class="barra"><span class="titulo">Grabación · clic en una frase para escucharla</span>'
            f'<label><input type="checkbox" id="seguir" checked> Seguir</label>{mini}</div>'
            f'<{etiqueta} id="medio" controls preload="metadata" src="{src}"></{etiqueta}>'
            f'<p id="sin-medio" hidden>No se pudo abrir la grabación (<code>{e(ruta.name)}</code>). Si se movió, '
            "vuelve a generar la transcripción ilustrada; si es .mkv, ábrela en Edge o Chrome.</p></div>")


def herramientas_html(hablantes):
    e = html.escape
    partes = ['<div class="herramientas">',
              '<input type="search" id="buscar" placeholder="Buscar en lo dicho y en pantalla" aria-label="Buscar">',
              '<button type="button" id="anterior" title="Anterior (Mayús+Enter)" aria-label="Resultado anterior">‹</button>',
              '<button type="button" id="siguiente" title="Siguiente (Enter)" aria-label="Resultado siguiente">›</button>',
              '<span id="conteo" aria-live="polite"></span>']
    if len(hablantes) > 1:
        opciones = "".join(f'<option value="{e(h)}">{e(h)}</option>' for h in hablantes)
        partes.append(f'<select id="hablante" aria-label="Filtrar por hablante"><option value="">Todos los hablantes</option>{opciones}</select>')
    partes.append("</div>")
    return "".join(partes)


def main():
    configurar_consola()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("salida")
    p.add_argument("--titulo")
    p.add_argument("--nota", default="")
    p.add_argument("--medio", help="la grabación, para el reproductor")
    p.add_argument("--incrustar", action="store_true")
    p.add_argument("--sin-capturas", action="store_true")
    p.add_argument("--sin-ocr", action="store_true")
    a = p.parse_args()

    salida = Path(a.salida)
    meta, segmentos = leer_transcripcion(salida)
    capturas = [] if a.sin_capturas else leer_capturas(salida)[1]
    ocr = {} if a.sin_capturas or a.sin_ocr else {
        c["n"]: c.get("lineas", []) for c in (leer_json(salida / "ocr.json", {}) or {}).get("capturas", [])}
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
        iguales = sum(1 for c in capturas if "igual_a" in c)
        detalles.insert(1, f"{len(capturas)} capturas de pantalla" + (f" ({iguales} repetidas)" if iguales else ""))
        if ocr:
            detalles.insert(2, "texto de las capturas por OCR")
    if hablantes:
        detalles.append(f"hablantes: {', '.join(hablantes)}")

    e = html.escape
    clase = ' class="con-capturas"' if capturas else ""
    partes = [
        '<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{e(titulo)}</title>\n<style>{estilo}</style>\n</head>\n<body{clase}>",
        f"<header><h1>{e(titulo)}</h1><p class=\"meta\">{e(' · '.join(detalles))}</p>",
    ]
    # La nota del glosario (glosario.json, si lo generó minutas.py) va sola: no hay que repetirla en --nota.
    nota_glosario = (leer_json(salida / "glosario.json", {}) or {}).get("nota", "")
    for nota in (a.nota, nota_glosario):
        if nota:
            partes.append(f'<p class="nota">{e(nota)}</p>')
    partes.append("</header>")

    partes.append("<nav>" + herramientas_html(hablantes))
    if capturas:
        partes.append('<div class="tiempos">' + "".join(f'<a href="#c{c["n"]:04}">{hms(c["desde"])}</a>' for c in capturas) + "</div>")
    partes.append("</nav>")

    anclas = set()
    if not capturas:
        partes.append('<main class="solo">')
        partes += parrafos_html(segmentos, color_de, anclas) or ['<p class="vacio">Sin texto.</p>']
        partes.append("</main>")
    else:
        partes.append("<main>")
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
            igual = f' · igual a la <a href="#c{c["igual_a"]:04}">{c["igual_a"]:04}</a>' if "igual_a" in c else ""
            partes.append(f'<div><p class="tiempo">{hms(c["desde"])} – {hms(hasta)} <span>· captura {c["n"]:04}{igual}</span></p>')
            if not igual:
                partes.append(texto_ocr(ocr.get(c["n"])))
            partes += parrafos_html(por_captura[i], color_de, anclas) or ['<p class="vacio">Sin diálogo mientras esta pantalla estuvo visible.</p>']
            partes.append("</div></section>")
        partes.append("</main>")

    if a.medio:
        partes.append(reproductor_html(salida, a.medio))
    partes.append(f"<script>{SCRIPT}</script>")
    partes.append("</body>\n</html>\n")
    destino = salida / "transcripcion-ilustrada.html"
    destino.write_text("\n".join(partes), encoding="utf-8")
    print(f"HTML: {destino}")


if __name__ == "__main__":
    main()
