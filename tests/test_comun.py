import json

from comun import Progreso, agrupar, escribir_json, escribir_transcripcion, hms, leer_json, leer_transcripcion, ts_srt


def seg(inicio, fin, texto, hablante=None):
    return {"inicio": inicio, "fin": fin, "texto": texto, "hablante": hablante}


def test_formatos_de_tiempo():
    assert hms(3725) == "01:02:05"
    assert hms(65, "-") == "00-01-05"
    assert ts_srt(3661.5) == "01:01:01,500"


def test_agrupar_corta_por_hablante_y_por_pausa():
    grupos = agrupar([seg(0, 1, "a", "Ana"), seg(1.2, 2, "b", "Ana"), seg(2.1, 3, "c", "Luis"), seg(10, 11, "d", "Luis")])
    assert [[s["texto"] for s in g] for g in grupos] == [["a", "b"], ["c"], ["d"]]


def test_escribir_y_leer_la_transcripcion(tmp_path):
    escribir_transcripcion(tmp_path, [seg(1, 2, "Hola.", "Ana"), seg(2.5, 3, "  "), seg(3, 4, "Qué tal.", "Luis")], {"fuente": "prueba"})
    meta, segmentos = leer_transcripcion(tmp_path)
    assert meta["hablantes"] == ["Ana", "Luis"] and meta["segmentos"] == 2  # el vacío se descarta
    assert (tmp_path / "transcripcion.txt").read_text(encoding="utf-8").startswith("[00:00:01] Ana: Hola.")
    assert "00:00:03,000 --> 00:00:04,000\nLuis: Qué tal." in (tmp_path / "transcripcion.srt").read_text(encoding="utf-8")


def test_escribir_json_es_atomico(tmp_path):
    ruta = tmp_path / "x.json"
    escribir_json(ruta, {"a": "ñ"})
    assert leer_json(ruta) == {"a": "ñ"}
    assert not list(tmp_path.glob("*.tmp"))
    assert leer_json(tmp_path / "no-existe.json", {"defecto": 1}) == {"defecto": 1}


def test_progreso_para_el_orquestador(monkeypatch, capsys):
    monkeypatch.setenv("MINUTAS_PROGRESO", "1")
    p = Progreso("capturas", 100)
    p.fase("buscando")
    p.avance(10, capturas=3)
    p.avance(11, capturas=3)  # menos de un segundo después: no se emite
    lineas = capsys.readouterr().out.splitlines()
    assert len(lineas) == 2 and all(x.startswith("@progreso ") for x in lineas)
    assert json.loads(lineas[1][10:]) == {"paso": "capturas", "hecho": 10, "total": 100, "capturas": 3}


def test_progreso_legible_sin_orquestador(monkeypatch, capsys):
    monkeypatch.delenv("MINUTAS_PROGRESO", raising=False)
    p = Progreso("transcripcion", 900)
    p.avance(100)
    assert capsys.readouterr().out == ""
    p.avance(310)
    assert capsys.readouterr().out.strip().startswith("00:05:10 / 00:15:00")
