"""Texto de las capturas (OCR) con láminas sintéticas."""
import json

import pytest

from conftest import pantalla_con_texto
from ocr_capturas import limpiar

Image = pytest.importorskip("PIL.Image")


def test_limpiar_quita_ruido_del_modelo_multilingue():
    assert limpiar(["石", "日1", "Reserva 品 8812", "×", "No", "  Total   5,800 "], "es") == ["Reserva 8812", "No", "Total 5,800"]
    assert limpiar(["日本語"], "ja") == ["日本語"]


def test_lee_el_texto_reutiliza_las_repetidas_y_resume_lo_nuevo(correr_script, tmp_path):
    salida = tmp_path / "salida"
    (salida / "capturas").mkdir(parents=True)
    laminas = [["Reserva 8812 confirmada", "Mesa para 4 personas"],
               ["Reserva 8812 confirmada", "Horario 20:30 sabado"]]
    capturas = []
    for n, lineas in enumerate(laminas, start=1):
        archivo = f"capturas/{n:04}_00-00-0{n}.jpg"
        Image.fromarray(pantalla_con_texto(lineas)).save(salida / archivo, quality=90)
        capturas.append({"n": n, "archivo": archivo, "t": n, "desde": n, "motivo": "estable", "cambio": 0.5})
    capturas.append({**capturas[0], "n": 3, "t": 3, "desde": 3, "igual_a": 1})
    (salida / "capturas.json").write_text(json.dumps({"meta": {}, "capturas": capturas}), encoding="utf-8")

    r = correr_script("ocr_capturas.py", salida, env={"MINUTAS_PROGRESO": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    ocr = json.loads((salida / "ocr.json").read_text(encoding="utf-8"))["capturas"]
    primera = ocr[0]["lineas"]
    assert any("Reserva 8812" in x for x in primera) and any("personas" in x for x in primera)
    assert ocr[2]["igual_a"] == 1 and ocr[2]["lineas"] == primera

    txt = (salida / "capturas.txt").read_text(encoding="utf-8")
    bloque_2 = txt.split("captura 0002")[1].split("captura 0003")[0]
    assert "Horario" in bloque_2 and "Reserva" not in bloque_2  # solo lo nuevo respecto a la anterior
    assert "captura 0003 · igual a la captura 0001" in txt
    avances = [json.loads(x[10:]) for x in r.stdout.splitlines() if x.startswith("@progreso ")]
    assert {"paso": "ocr", "fase": "leyendo el texto de las capturas"} in avances
