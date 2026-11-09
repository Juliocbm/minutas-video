"""Busca en la transcripción los términos del glosario y las menciones de los participantes.

No reescribe la transcripción: la deja fiel al audio y anota dónde aparece cada forma, para que
quien redacta la minuta corrija con evidencia. Escribe <salida>/glosario.json. Solo biblioteca estándar.
"""
import re
from datetime import datetime

MAX_EJEMPLOS = 5


def _patron(forma):
    return re.compile(rf"(?<!\w){re.escape(forma)}(?!\w)", re.IGNORECASE)


def _contexto(texto, inicio, fin, margen=45):
    a, b = max(0, inicio - margen), min(len(texto), fin + margen)
    return ("…" if a else "") + texto[a:b].strip() + ("…" if b < len(texto) else "")


def _ocurrencias(segmentos, forma, exacta=None):
    """Apariciones de `forma` (sin distinguir mayúsculas). Con `exacta`, descarta las que ya están
    escritas exactamente así (para no contar «NEXO» como variante de «NEXO»)."""
    patron = _patron(forma)
    encontradas = []
    for s in segmentos:
        for m in patron.finditer(s["texto"]):
            if exacta is not None and m.group(0) == exacta:
                continue
            encontradas.append({"t": s["inicio"], "texto": _contexto(s["texto"], m.start(), m.end())})
    return encontradas


def buscar(segmentos, terminos, personas):
    """terminos: {"NEXO": ["Nexus", ...]}; personas: [{"nombre", "rol", "organizacion", "alias"}]."""
    resultado_terminos = []
    for termino, variantes in sorted(terminos.items(), key=lambda kv: kv[0].lower()):
        correctas = _ocurrencias(segmentos, termino)
        hallazgos = []
        for v in variantes:
            occ = _ocurrencias(segmentos, v, exacta=termino if v.lower() == termino.lower() else None)
            if occ:
                hallazgos.append({"forma": v, "veces": len(occ), "ejemplos": occ[:MAX_EJEMPLOS]})
        resultado_terminos.append({
            "termino": termino,
            "veces_bien_escrito": len(correctas),
            "variantes": sorted(hallazgos, key=lambda h: -h["veces"]),
        })

    resultado_personas = []
    for p in personas:
        formas = {p["nombre"], *p.get("alias", [])}
        nombre_pila = p["nombre"].split()[0]
        if len(nombre_pila) >= 3:
            formas.add(nombre_pila)
        # De la forma más larga a la más corta: «Ana» dentro de «Ana Ruiz» no cuenta dos veces.
        formas = sorted(formas, key=len, reverse=True)
        menciones = []
        for s in segmentos:
            ocupados = []
            for forma in formas:
                for m in _patron(forma).finditer(s["texto"]):
                    if any(m.start() < fin and inicio < m.end() for inicio, fin in ocupados):
                        continue
                    ocupados.append((m.start(), m.end()))
                    menciones.append({"t": s["inicio"], "forma": forma,
                                      "texto": _contexto(s["texto"], m.start(), m.end())})
        menciones.sort(key=lambda m: m["t"])
        resultado_personas.append({
            "nombre": p["nombre"], "rol": p.get("rol", ""), "organizacion": p.get("organizacion", ""),
            "menciones": len(menciones), "ejemplos": menciones[:MAX_EJEMPLOS],
        })

    return {
        "meta": {"generado": datetime.now().isoformat(timespec="seconds"),
                 "terminos": len(terminos), "personas": len(personas)},
        "terminos": resultado_terminos,
        "personas": resultado_personas,
        "nota": nota(resultado_terminos),
    }


def nota(resultado_terminos):
    """Frase para el lector del HTML con las correcciones encontradas, o "" si no hubo."""
    partes = []
    for t in resultado_terminos:
        formas = [f"«{v['forma']}»" for v in t["variantes"]]
        if formas:
            partes.append(f"{' o '.join(formas)} es {t['termino']}")
    if not partes:
        return ""
    return "Términos que la transcripción automática escribe mal: " + "; ".join(partes) + "."
