"""Procesa la misma reunión con varias versiones del plugin, cada una en una sesión limpia.

Por cada versión deja una carpeta con solo una copia del video, pide la minuta con el mismo mensaje (con la ruta
completa del video) y espera a que exista minuta.md. Mientras corre, el plugin instalado queda desactivado para
que la sesión vea solo la versión de --plugin-dir; al final se reactiva.

Anota inicio, fin, segundos, costo y turnos en <trabajo>/tiempos.jsonl, y la sesión completa en
<trabajo>/<versión>/run/sesion.jsonl (revísala con revisar_sesion.py).

Una versión es una carpeta con el plugin completo, por ejemplo `git worktree add ../mv-0.5.0 minutas-video--v0.5.0`.
La primera versión corre con el disco frío: pon primero la nueva, para que la ventaja, si la hay, sea de la otra.

uso: python correr.py --video junta.mp4 --trabajo ../medicion/junta --version nueva=. --version 0.5.0=../mv-0.5.0
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[1]
PROMPT = "Hazme la minuta de esta reunión: {video}. Usa lo de siempre, no hace falta que me preguntes nada."


def fuera_del_repo(ruta):
    ruta = Path(ruta).resolve()
    if ruta == REPO or REPO in ruta.parents:
        sys.exit(f"{ruta} está dentro del repositorio: usa una carpeta fuera (tendrá el contenido de reuniones reales).")
    return ruta


def preparar(run, video):
    """Deja en `run` solo la copia del video (enlace duro si se puede: no ocupa espacio)."""
    run.mkdir(parents=True, exist_ok=True)
    copia = run / video.name
    for hijo in run.iterdir():
        if hijo != copia:
            shutil.rmtree(hijo) if hijo.is_dir() else hijo.unlink()
    if not copia.exists():
        try:
            os.link(video, copia)
        except OSError:
            shutil.copy2(video, copia)
    return copia


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--video", required=True, type=Path)
    a.add_argument("--trabajo", required=True, type=Path, help="carpeta de la medición, fuera del repositorio")
    a.add_argument("--version", required=True, action="append", metavar="NOMBRE=CARPETA_DEL_PLUGIN")
    a.add_argument("--prompt", default=PROMPT, help="mensaje para la sesión; {video} es la ruta de la copia")
    a.add_argument("--plugin-instalado", default="minutas-video@minutas-video",
                   help="plugin que se desactiva mientras corre ('' para no tocarlo)")
    a.add_argument("--timeout", type=float, default=4500)
    a.add_argument("--claude", help="ruta del ejecutable de Claude Code (por defecto, el del PATH)")
    args = a.parse_args()
    sys.stdout.reconfigure(errors="replace")

    video = args.video.resolve()
    if not video.is_file():
        sys.exit(f"No existe el video: {video}")
    trabajo = fuera_del_repo(args.trabajo)
    versiones = []
    for v in args.version:
        nombre, _, carpeta = v.partition("=")
        plugin = Path(carpeta).resolve()
        if not (plugin / ".claude-plugin" / "plugin.json").is_file():
            sys.exit(f"{plugin} no es la carpeta de un plugin (falta .claude-plugin/plugin.json)")
        versiones.append((nombre, plugin))

    claude = args.claude or os.environ.get("CLAUDE_BIN") or shutil.which("claude")
    if not claude:
        sys.exit("No encuentro el comando claude: pásalo con --claude o en la variable CLAUDE_BIN.")
    desactivado = False
    if args.plugin_instalado:
        r = subprocess.run([claude, "plugin", "disable", args.plugin_instalado], capture_output=True, text=True)
        desactivado = r.returncode == 0
        if not desactivado:
            print(f"aviso: no se desactivó {args.plugin_instalado} (¿no está instalado?): {r.stderr.strip()}")

    resumen = []
    try:
        for nombre, plugin in versiones:
            run = trabajo / nombre / "run"
            copia = preparar(run, video)
            minuta = run / f"{video.stem}_minuta" / "minuta.md"
            inicio = datetime.now().isoformat(timespec="seconds")
            print(f"{nombre}: procesando desde {inicio}…", flush=True)
            r = subprocess.run([sys.executable, str(AQUI / "sesion_viva.py"), "--cwd", str(run),
                                "--plugin-dir", str(plugin), "--log", str(run / "sesion.jsonl"),
                                "--prompt", args.prompt.format(video=copia), "--esperar-archivo", str(minuta),
                                "--timeout", str(args.timeout), "--claude", claude],
                               capture_output=True, text=True, encoding="utf-8",
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            try:
                resultado = json.loads(r.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                resultado = {"error": (r.stdout + r.stderr).strip()[-500:]}
            fila = {"version": nombre, "plugin": str(plugin), "inicio": inicio,
                    "fin": datetime.now().isoformat(timespec="seconds"), **resultado}
            with open(trabajo / "tiempos.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(fila, ensure_ascii=False) + "\n")
            resumen.append(fila)
            print(f"{nombre}: {resultado}", flush=True)
            time.sleep(5)
    finally:
        if desactivado:
            subprocess.run([claude, "plugin", "enable", args.plugin_instalado], capture_output=True)
            print(f"{args.plugin_instalado} reactivado")

    print("\nversión         minutos   costo USD  turnos  minuta")
    for f in resumen:
        seg = f.get("segundos_hasta_ultimo_turno")
        print(f"{f['version']:<15} {seg / 60 if seg else 0:7.1f}   {f.get('costo_usd') or 0:9.2f}  "
              f"{f.get('turnos', 0):6}  {'sí' if f.get('condicion') else 'NO'}")


if __name__ == "__main__":
    main()
