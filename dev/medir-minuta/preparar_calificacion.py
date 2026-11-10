"""Prepara la calificación a ciegas de dos minutas de la misma reunión.

Copia a --destino las dos minutas, sorteadas como minuta_A.md y minuta_B.md, más la lista de hechos, la
transcripción, las capturas y las instrucciones para el calificador (con la reunión y el propósito ya llenados). La
clave del sorteo queda FUERA de --destino, para que el calificador no la vea.

Los enlaces a la transcripción ilustrada se quitan (queda el minuto): delatarían qué versión escribió cada minuta.

uso: python preparar_calificacion.py --minuta nueva=RUTA/minuta.md --minuta 0.5.0=RUTA/minuta.md \
         --hechos hechos.md --salida-reunion RUTA/junta_minuta --destino ../medicion/junta/calificar \
         --reunion "una reunión de 35 minutos entre un equipo de desarrollo y un proveedor" \
         --proposito "implementar la integración"
"""
import argparse
import random
import re
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[1]
ENLACE_HTML = re.compile(r"\[([^\]]+)\]\(transcripcion-ilustrada\.html#t\d+\)")


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--minuta", required=True, action="append", metavar="NOMBRE=RUTA", help="dos veces")
    a.add_argument("--hechos", required=True, type=Path, help="lista de hechos (ver hechos-ejemplo.md)")
    a.add_argument("--salida-reunion", required=True, type=Path,
                   help="carpeta *_minuta de una de las corridas: de ahí salen transcripcion.txt y capturas/")
    a.add_argument("--transcripcion", type=Path,
                   help="otra transcripción (p. ej., sin los hablantes de la separación automática, para no favorecer a nadie)")
    a.add_argument("--destino", required=True, type=Path, help="carpeta que verá el calificador, fuera del repositorio")
    a.add_argument("--clave", type=Path, help="por defecto, clave-<destino>.txt junto a --destino")
    a.add_argument("--reunion", required=True, help='qué reunión es, p. ej. "la daily de 31 minutos de un equipo de desarrollo"')
    a.add_argument("--proposito", required=True, help='para qué se usará la minuta, p. ej. "darle seguimiento al equipo"')
    args = a.parse_args()

    if len(args.minuta) != 2:
        sys.exit("Se califican exactamente dos minutas: pasa --minuta dos veces.")
    destino = args.destino.resolve()
    if destino == REPO or REPO in destino.parents:
        sys.exit(f"{destino} está dentro del repositorio: usa una carpeta fuera.")
    if destino.exists() and any(destino.iterdir()):
        sys.exit(f"{destino} ya tiene archivos: usa una carpeta nueva.")
    clave = (args.clave or destino.parent / f"clave-{destino.name}.txt").resolve()
    if destino in clave.parents:
        sys.exit("La clave no puede quedar dentro de --destino: el calificador la vería.")
    transcripcion = args.transcripcion or args.salida_reunion / "transcripcion.txt"

    minutas = [m.partition("=")[::2] for m in args.minuta]
    random.SystemRandom().shuffle(minutas)
    destino.mkdir(parents=True, exist_ok=True)
    for letra, (_, ruta) in zip("AB", minutas):
        texto = Path(ruta).read_text(encoding="utf-8-sig")
        (destino / f"minuta_{letra}.md").write_text(ENLACE_HTML.sub(r"\1", texto), encoding="utf-8")
    shutil.copy2(args.hechos, destino / "hechos.md")
    shutil.copy2(transcripcion, destino / "transcripcion.txt")
    if (args.salida_reunion / "capturas").is_dir():
        shutil.copytree(args.salida_reunion / "capturas", destino / "capturas")
    plantilla = (AQUI / "instrucciones_calificador.md").read_text(encoding="utf-8")
    (destino / "instrucciones_calificador.md").write_text(
        plantilla.replace("{reunion}", args.reunion).replace("{proposito}", args.proposito), encoding="utf-8")
    clave.write_text("".join(f"{letra}={nombre}\n" for letra, (nombre, _) in zip("AB", minutas)), encoding="utf-8")

    print(f"Listo: {destino}\nClave del sorteo: {clave}\n")
    print("Pídele a un subagente que no sepa qué versión es cuál, por ejemplo:")
    print(f'  "Lee {destino / "instrucciones_calificador.md"} y haz exactamente lo que pide."')


if __name__ == "__main__":
    main()
