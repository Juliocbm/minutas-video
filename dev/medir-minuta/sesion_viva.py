"""Corre una sesión de `claude -p` que no se cierra al terminar el primer turno.

`claude -p` normal termina en cuanto Claude responde y mata los procesos que dejó en segundo plano (la skill lanza
ahí la transcripción). Aquí la entrada queda abierta (stream-json), como en una sesión interactiva: Claude recibe el
aviso de que el proceso terminó y sigue trabajando. La sesión se cierra cuando existe --esperar-archivo y lleva
--quieto segundos sin eventos, o al llegar a --timeout.

Al final imprime una línea JSON: motivo, segundos hasta el último turno, costo acumulado (USD) y turnos.

uso: python sesion_viva.py --cwd DIR --prompt TEXTO --log sesion.jsonl [--plugin-dir DIR]
                           [--esperar-archivo RUTA] [--quieto 120] [--timeout 4500] [--claude RUTA]
"""
import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import threading
import time

HERRAMIENTAS = "Read,Glob,Grep,Skill,Write,Edit,Bash"


def buscar_claude(indicado=None):
    ruta = indicado or os.environ.get("CLAUDE_BIN") or shutil.which("claude")
    if not ruta:
        sys.exit("No encuentro el comando claude: pásalo con --claude o en la variable CLAUDE_BIN.")
    return ruta


def no_suspender():
    """En Windows, que el equipo no se suspenda por inactividad mientras corre (cerrar la tapa sí lo suspende)."""
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--cwd", required=True, help="carpeta de trabajo de la sesión")
    a.add_argument("--prompt", required=True, help="mensaje del usuario")
    a.add_argument("--log", required=True, help="dónde guardar la sesión completa (stream-json)")
    a.add_argument("--plugin-dir", help="carpeta del plugin a probar")
    a.add_argument("--esperar-archivo", help="la sesión termina cuando existe este archivo (y lleva --quieto s sin eventos)")
    a.add_argument("--quieto", type=float, default=120)
    a.add_argument("--timeout", type=float, default=4500)
    a.add_argument("--herramientas", default=HERRAMIENTAS, help=f"--allowedTools de la sesión (por defecto {HERRAMIENTAS})")
    a.add_argument("--claude", help="ruta del ejecutable de Claude Code (por defecto, el del PATH)")
    args = a.parse_args()

    no_suspender()
    cmd = [buscar_claude(args.claude), "-p", "--input-format", "stream-json", "--output-format", "stream-json",
           "--verbose", "--allowedTools", args.herramientas]
    if args.plugin_dir:
        cmd += ["--plugin-dir", args.plugin_dir]

    estado = {"ultimo": time.time(), "resultados": 0, "costo": None, "turnos": 0, "fin_turno": None}
    t0 = time.time()
    p = subprocess.Popen(cmd, cwd=args.cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def leer():
        with open(args.log, "wb") as log:
            for linea in p.stdout:
                log.write(linea)
                log.flush()
                estado["ultimo"] = time.time()
                try:
                    evento = json.loads(linea)
                except ValueError:
                    continue
                if evento.get("type") == "result":  # uno por turno; total_cost_usd es el acumulado
                    estado["resultados"] += 1
                    estado["costo"] = evento.get("total_cost_usd")
                    estado["turnos"] += evento.get("num_turns") or 0
                    estado["fin_turno"] = time.time()

    def errores():
        with open(args.log + ".err", "wb") as f:
            for linea in p.stderr:
                f.write(linea)

    threading.Thread(target=leer, daemon=True).start()
    threading.Thread(target=errores, daemon=True).start()
    mensaje = {"type": "user", "message": {"role": "user", "content": args.prompt}}
    p.stdin.write((json.dumps(mensaje, ensure_ascii=False) + "\n").encode("utf-8"))
    p.stdin.flush()

    def cumplida():
        return bool(args.esperar_archivo) and os.path.exists(args.esperar_archivo)

    motivo = "timeout"
    while time.time() - t0 < args.timeout:
        time.sleep(2)
        if p.poll() is not None:
            motivo = f"salió sola (rc={p.returncode})"
            break
        if estado["resultados"] and cumplida() and time.time() - estado["ultimo"] > args.quieto:
            motivo = "condición cumplida"
            break

    if p.poll() is None:
        p.stdin.close()
        try:
            p.wait(timeout=60)
        except subprocess.TimeoutExpired:
            p.kill()
    fin = estado["fin_turno"] or time.time()
    print(json.dumps({"motivo": motivo, "segundos_hasta_ultimo_turno": round(fin - t0),
                      "segundos_total": round(time.time() - t0), "costo_usd": estado["costo"],
                      "turnos": estado["turnos"], "resultados": estado["resultados"], "condicion": cumplida()},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
