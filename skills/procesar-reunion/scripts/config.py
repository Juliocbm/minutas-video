"""Configuración de minutas-video: valores del plugin, presets y archivos del usuario y del proyecto.

Capas, de menor a mayor prioridad (cada una sobrescribe a la anterior):
  1. Valores del plugin (DEFECTOS) y del preset elegido.
  2. Usuario:  ~/.minutas-video/config.toml   (o $MINUTAS_HOME/config.toml)
  3. Proyecto: <proyecto>/.minutas-video/config.toml   (se busca desde la carpeta actual hacia arriba)
  4. Lo que se pida en la corrida (opciones de minutas.py).
Un valor fijado en un archivo manda sobre el preset: el preset solo llena lo que nadie fijó.

Además se leen, del usuario y del proyecto:
  glosario.toml       [terminos]  Término = ["variante mal escrita", ...]
  participantes.toml  [[persona]] nombre, rol, organizacion, alias
  vocabulario.txt     formato de la 0.1 (un término por línea); se lee como glosario sin variantes.

Requiere Python 3.11+ (tomllib). Solo biblioteca estándar.
"""
import copy
import os
import tomllib
from pathlib import Path

CARPETA = ".minutas-video"

PRESETS = {
    "rapido": {
        "descripcion": "Solo lo esencial: transcripción rápida, sin capturas y una minuta corta.",
        "modelo": "large-v3-turbo", "capturas": "ninguna", "hablantes": False, "minuta": "corta", "revision": "ligera",
        "entregables": ["minuta"],
    },
    "estandar": {
        "descripcion": "Minuta completa y transcripción ilustrada con capturas de pantalla.",
        "modelo": "", "capturas": "pantalla", "hablantes": True, "minuta": "completa", "revision": "normal",
        "entregables": ["minuta", "html"],
    },
    "completo": {
        "descripcion": "Como estándar, más revisión de todas las capturas, contraste con documentos "
                       "y contexto para otra sesión de Claude.",
        "modelo": "", "capturas": "pantalla", "hablantes": True, "minuta": "completa", "revision": "exhaustiva",
        "entregables": ["minuta", "html", "contexto"],
    },
    "audio": {
        "descripcion": "Grabaciones sin video o cuando lo que se ve no importa: minuta completa, sin capturas.",
        "modelo": "", "capturas": "ninguna", "hablantes": True, "minuta": "completa", "revision": "normal",
        "entregables": ["minuta", "html"],
    },
}

DEFECTOS = {
    "preset": "estandar",
    "idioma": "es",
    "transcripcion": {"modelo": "", "dispositivo": "auto"},
    "capturas": {"modo": "", "max": 200, "ocr": True},
    # separar: None = lo decide el preset. numero: cuántas personas hablan (0 = no se sabe).
    "hablantes": {"separar": None, "numero": 0},
}

# Esquema: clave -> (tipo, valores permitidos o None). Las tablas anidadas son dicts.
ESQUEMA = {
    "preset": (str, set(PRESETS)),
    "idioma": (str, None),
    "transcripcion": {"modelo": (str, None), "dispositivo": (str, {"auto", "cuda", "cpu"})},
    "capturas": {"modo": (str, {"", "pantalla", "camara", "ninguna"}), "max": (int, None), "ocr": (bool, None)},
    "hablantes": {"separar": (bool, None), "numero": (int, None)},
}


def dir_usuario():
    return Path(os.environ.get("MINUTAS_HOME") or Path.home() / CARPETA)


def buscar_proyecto(desde=None):
    """Primera carpeta .minutas-video desde `desde` hacia arriba, sin pasar del directorio personal."""
    actual = Path(desde or Path.cwd()).resolve()
    casa = Path.home().resolve()
    usuario = dir_usuario().resolve()
    for carpeta in (actual, *actual.parents):
        if carpeta == casa:  # ~/.minutas-video es la configuración del usuario, no la de un proyecto
            break
        candidata = carpeta / CARPETA
        if candidata.is_dir() and candidata.resolve() != usuario:
            return candidata
    return None


def _leer_toml(ruta, errores):
    try:
        with open(ruta, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        errores.append(f"{ruta}: no es TOML válido ({e}).")
    except OSError as e:
        errores.append(f"{ruta}: no se pudo leer ({e}).")
    return {}


def _validar(datos, esquema, ruta, errores, prefijo=""):
    limpio = {}
    for clave, valor in datos.items():
        nombre = f"{prefijo}{clave}"
        if clave not in esquema:
            errores.append(f"{ruta}: clave desconocida «{nombre}». Válidas: {', '.join(prefijo + k for k in esquema)}.")
            continue
        regla = esquema[clave]
        if isinstance(regla, dict):
            if not isinstance(valor, dict):
                errores.append(f"{ruta}: «{nombre}» debe ser una tabla [{nombre}].")
                continue
            limpio[clave] = _validar(valor, regla, ruta, errores, f"{nombre}.")
            continue
        tipo, permitidos = regla
        # bool es subclase de int: true no debe pasar por número, ni 1 por true.
        if not isinstance(valor, tipo) or (tipo is not bool and isinstance(valor, bool)):
            esperado = {str: "texto", int: "un número entero", bool: "true o false"}[tipo]
            errores.append(f"{ruta}: «{nombre}» debe ser {esperado}.")
            continue
        if permitidos is not None and valor not in permitidos:
            opciones = ", ".join(sorted(p or '""' for p in permitidos))
            errores.append(f"{ruta}: «{nombre}» = {valor!r} no es válido. Opciones: {opciones}.")
            continue
        limpio[clave] = valor
    return limpio


def _fusionar(base, encima, origen, origenes, prefijo=""):
    for clave, valor in encima.items():
        if isinstance(valor, dict):
            _fusionar(base.setdefault(clave, {}), valor, origen, origenes, f"{prefijo}{clave}.")
        elif valor is not None:
            base[clave] = valor
            origenes[f"{prefijo}{clave}"] = origen


def _origenes_iniciales(d, origen, prefijo=""):
    salida = {}
    for clave, valor in d.items():
        if isinstance(valor, dict):
            salida.update(_origenes_iniciales(valor, origen, f"{prefijo}{clave}."))
        else:
            salida[f"{prefijo}{clave}"] = origen
    return salida


def _leer_glosario(carpeta, errores, avisos):
    terminos = {}
    ruta = carpeta / "glosario.toml"
    if ruta.exists():
        datos = _leer_toml(ruta, errores)
        for clave in datos:
            if clave != "terminos":
                errores.append(f"{ruta}: clave desconocida «{clave}». Los términos van en la tabla [terminos].")
        for termino, variantes in (datos.get("terminos") or {}).items():
            if isinstance(variantes, str):
                variantes = [variantes]
            if not isinstance(variantes, list) or not all(isinstance(v, str) for v in variantes):
                errores.append(f"{ruta}: «{termino}» debe ser una lista de variantes, por ejemplo {termino} = [\"...\"].")
                continue
            terminos[termino] = [v for v in variantes if v.strip() and v != termino]
    vieja = carpeta / "vocabulario.txt"
    if vieja.exists():
        nuevos = 0
        for linea in vieja.read_text(encoding="utf-8-sig").splitlines():
            termino = linea.split("#", 1)[0].strip()
            if termino and termino not in terminos:
                terminos[termino] = []
                nuevos += 1
        if nuevos:
            avisos.append(f"{vieja}: formato de la 0.1. Conviene pasarlo a glosario.toml para anotar cómo lo escribe mal la transcripción.")
    return terminos


def _leer_participantes(carpeta, errores):
    personas = []
    ruta = carpeta / "participantes.toml"
    if not ruta.exists():
        return personas
    datos = _leer_toml(ruta, errores)
    for clave in datos:
        if clave != "persona":
            errores.append(f"{ruta}: clave desconocida «{clave}». Cada participante va en un bloque [[persona]].")
    for i, p in enumerate(datos.get("persona") or [], start=1):
        if not isinstance(p, dict) or not isinstance(p.get("nombre"), str) or not p["nombre"].strip():
            errores.append(f"{ruta}: la persona n.º {i} necesita nombre = \"...\".")
            continue
        desconocidas = set(p) - {"nombre", "rol", "organizacion", "alias"}
        if desconocidas:
            errores.append(f"{ruta}: {p['nombre']}: claves desconocidas {', '.join(sorted(desconocidas))}.")
        alias = p.get("alias") or []
        if isinstance(alias, str):
            alias = [alias]
        personas.append({
            "nombre": p["nombre"].strip(),
            "rol": p.get("rol", "") if isinstance(p.get("rol", ""), str) else "",
            "organizacion": p.get("organizacion", "") if isinstance(p.get("organizacion", ""), str) else "",
            "alias": [x for x in alias if isinstance(x, str) and x.strip()],
        })
    return personas


def cargar(proyecto=None, corrida=None, recomendacion=None):
    """Configuración efectiva. `corrida` tiene la forma de DEFECTOS (None = no fijado).
    `recomendacion` es la de entorno.recomendar()["recomendacion"]; llena el modelo y el dispositivo."""
    errores, avisos = [], []
    efectiva = copy.deepcopy(DEFECTOS)
    origen = _origenes_iniciales(efectiva, "plugin")

    usuario = dir_usuario()
    carpeta_proyecto = Path(proyecto) / CARPETA if proyecto else buscar_proyecto()
    if carpeta_proyecto is not None and not carpeta_proyecto.is_dir():
        carpeta_proyecto = None
    archivos = {
        "usuario": str(usuario / "config.toml"),
        "proyecto": str(carpeta_proyecto / "config.toml") if carpeta_proyecto else None,
    }

    for nombre, carpeta in (("usuario", usuario), ("proyecto", carpeta_proyecto)):
        if carpeta is None:
            continue
        ruta = carpeta / "config.toml"
        if ruta.exists():
            datos = _validar(_leer_toml(ruta, errores), ESQUEMA, ruta, errores)
            _fusionar(efectiva, datos, nombre, origen)
    if corrida:
        _fusionar(efectiva, corrida, "corrida", origen)

    nombre_preset = efectiva["preset"]
    preset = PRESETS.get(nombre_preset)
    if preset is None:
        errores.append(f"Preset desconocido «{nombre_preset}». Opciones: {', '.join(PRESETS)}.")
        nombre_preset, preset = "estandar", PRESETS["estandar"]
        efectiva["preset"] = nombre_preset
    if not efectiva["transcripcion"]["modelo"] and preset["modelo"]:
        efectiva["transcripcion"]["modelo"] = preset["modelo"]
        origen["transcripcion.modelo"] = f"preset {nombre_preset}"
    if not efectiva["capturas"]["modo"]:
        efectiva["capturas"]["modo"] = preset["capturas"]
        origen["capturas.modo"] = f"preset {nombre_preset}"
    if efectiva["hablantes"]["separar"] is None:
        efectiva["hablantes"]["separar"] = preset["hablantes"]
        origen["hablantes.separar"] = f"preset {nombre_preset}"
    if recomendacion:
        if not efectiva["transcripcion"]["modelo"]:
            efectiva["transcripcion"]["modelo"] = recomendacion["modelo"]
            origen["transcripcion.modelo"] = "equipo"
        if efectiva["transcripcion"]["dispositivo"] == "auto":
            efectiva["transcripcion"]["dispositivo_resuelto"] = recomendacion["dispositivo"]
    for clave in ("minuta", "revision", "entregables"):
        efectiva[clave] = copy.deepcopy(preset[clave])
        origen[clave] = f"preset {nombre_preset}"

    terminos, personas = {}, []
    for carpeta in (usuario, carpeta_proyecto):
        if carpeta is None:
            continue
        terminos.update(_leer_glosario(carpeta, errores, avisos))
        por_nombre = {p["nombre"]: p for p in personas}
        for p in _leer_participantes(carpeta, errores):
            por_nombre[p["nombre"]] = p
        personas = list(por_nombre.values())
        for archivo in ("glosario.toml", "participantes.toml", "vocabulario.txt"):
            if (carpeta / archivo).exists():
                archivos.setdefault("otros", []).append(str(carpeta / archivo))

    return {
        "efectiva": efectiva,
        "origen": origen,
        "archivos": archivos,
        "glosario": terminos,
        "participantes": personas,
        "presets": PRESETS,
        "errores": errores,
        "avisos": avisos,
    }
