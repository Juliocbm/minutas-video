"""Separación de hablantes: asignación a las frases, nombres y plan del orquestador."""
import json

from comun import asignar_hablantes, escribir_transcripcion, leer_transcripcion


def seg(inicio, fin, texto="hola", hablante=None):
    return {"inicio": inicio, "fin": fin, "texto": texto, "hablante": hablante}


TURNOS = [{"inicio": 0.0, "fin": 5.0, "hablante": "Hablante 1"},
          {"inicio": 4.5, "fin": 12.0, "hablante": "Hablante 2"},
          {"inicio": 20.0, "fin": 25.0, "hablante": "Hablante 1"}]


def test_cada_frase_toma_al_hablante_con_mas_tiempo_en_comun():
    r = asignar_hablantes([seg(0.5, 4.0), seg(4.0, 9.0), seg(12.3, 13.0), seg(15.0, 16.0), seg(21.0, 22.0)], TURNOS)
    assert [s["hablante"] for s in r] == ["Hablante 1", "Hablante 2", "Hablante 2", None, "Hablante 1"]
    # 12.3-13.0 cae en un hueco a 0.3 s del turno anterior: se le asigna; 15-16 queda lejos de todo.


def test_los_nombres_reemplazan_las_etiquetas():
    r = asignar_hablantes([seg(1, 2), seg(6, 7)], TURNOS, {"Hablante 2": "Luis"})
    assert [s["hablante"] for s in r] == ["Hablante 1", "Luis"]


def test_leer_transcripcion_aplica_la_separacion_solo_si_no_hay_hablantes(tmp_path):
    escribir_transcripcion(tmp_path, [seg(0.5, 4.0, "uno"), seg(6.0, 9.0, "dos")], {"fuente": "whisper"})
    (tmp_path / "hablantes.json").write_text(json.dumps({"meta": {}, "turnos": TURNOS, "nombres": {"Hablante 1": "Ana"}}),
                                             encoding="utf-8")
    meta, segmentos = leer_transcripcion(tmp_path)
    assert [s["hablante"] for s in segmentos] == ["Ana", "Hablante 2"]
    assert meta["hablantes"] == ["Ana", "Hablante 2"] and meta["hablantes_origen"] == "separación automática"

    # Una transcripción importada con nombres no se toca.
    escribir_transcripcion(tmp_path, [seg(0.5, 4.0, "uno", "Sofía")], {"fuente": "importada"})
    assert leer_transcripcion(tmp_path)[1][0]["hablante"] == "Sofía"


def test_comando_nombres(correr_script, tmp_path):
    salida = tmp_path / "junta_minuta"
    escribir_transcripcion(salida, [seg(0.5, 4.0, "Buenos días"), seg(6.0, 9.0, "Hola")], {"fuente": "whisper"})
    (salida / "hablantes.json").write_text(json.dumps({"meta": {"hablantes": ["Hablante 1", "Hablante 2"]},
                                                       "turnos": TURNOS}), encoding="utf-8")
    r = correr_script("minutas.py", "nombres", salida, "Hablante 2=Luis Méndez")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Luis Méndez: Hola" in (salida / "transcripcion.txt").read_text(encoding="utf-8")
    assert json.loads((salida / "hablantes.json").read_text(encoding="utf-8"))["nombres"] == {"Hablante 2": "Luis Méndez"}
    r = correr_script("minutas.py", "nombres", salida, "Hablante 7=Nadie")
    assert r.returncode != 0 and "Hablante 1, Hablante 2" in r.stderr


def test_plan_separa_hablantes_solo_con_whisper(correr_script, demo_vtt, tmp_path):
    video = tmp_path / "junta.mp4"
    video.write_bytes(b"")  # el plan no abre el video

    def acciones(*args):
        return json.loads(correr_script("minutas.py", "procesar", *args, "--plan").stdout)["entradas"][0]["acciones"]

    assert "hablantes" in acciones(video.name)
    assert "hablantes" not in acciones(video.name, "--no-separar-hablantes")
    assert "hablantes" not in acciones(video.name, "--preset", "rapido")
    assert "hablantes" not in acciones(video.name, "--transcripcion", demo_vtt.name)  # el .vtt ya trae quién habla


def test_separa_las_voces_de_una_reunion_real(correr_script, tmp_path):
    """90 s de la reunión ES2004a de AMI (cuatro personas; ver tests/datos/LEEME.md)."""
    import importlib.util
    from conftest import RAIZ
    spec = importlib.util.spec_from_file_location("medir", RAIZ / "dev" / "medir_hablantes.py")
    datos = RAIZ / "tests" / "datos"
    r = correr_script("separar_hablantes.py", datos / "ami-ES2004a-945s.opus", "--salida", tmp_path, "--hablantes", 4)
    assert r.returncode == 0, r.stdout + r.stderr
    hablantes = json.loads((tmp_path / "hablantes.json").read_text(encoding="utf-8"))
    # Uno de los cuatro habla solo ~10 s en este tramo: puede quedar absorbido por otro.
    assert hablantes["meta"]["hablantes"][:3] == ["Hablante 1", "Hablante 2", "Hablante 3"]
    medir = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(medir)  # la métrica de dev/ (usa scipy, que está en el entorno de desarrollo)
    hip = [(t["inicio"], t["fin"], t["hablante"]) for t in hablantes["turnos"]]
    error = medir.der(medir.leer_rttm(datos / "ami-ES2004a-945s.rttm"), hip)
    # Con solo 90 s hay pocas muestras de cada voz: aquí da ~43 % de error, y el mismo tramo dentro de
    # la reunión completa ~20 %. La prueba vigila que la separación funcione, no su mejor caso.
    assert error["der"] < 0.55, error
