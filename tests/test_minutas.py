"""Pruebas de punta a punta del orquestador con la reunión de ejemplo (importa un .vtt: sin Whisper)."""
import json
import shutil

from conftest import EJEMPLO, pantalla_con_texto, video_de_pantallas
from minutas import EXTERNOS, puede_arrancar

SALIDA = "reunion-demo_minuta"


def simular(duraciones):
    """El bucle de minutas.ejecutar con duraciones ficticias: devuelve [inicio, fin] de cada paso."""
    pendientes = [p for p in EXTERNOS if p in duraciones]
    en_curso, tiempos, t = {}, {}, 0.0
    while pendientes or en_curso:
        for paso in list(pendientes):
            if puede_arrancar(paso, pendientes, en_curso):
                pendientes.remove(paso)
                en_curso[paso] = t + duraciones[paso]
                tiempos[paso] = [t, None]
        t = min(en_curso.values())
        for paso, fin in list(en_curso.items()):
            if fin <= t:
                tiempos[paso][1] = fin
                del en_curso[paso]
    return tiempos


def test_los_pasos_pesados_corren_de_uno_en_uno():
    t = simular({"transcripcion": 3.5, "hablantes": 3.7, "capturas": 2, "ocr": 5})
    assert t["transcripcion"][0] == t["capturas"][0] == 0  # las capturas acompañan a la transcripción
    assert t["hablantes"][0] == t["transcripcion"][1]      # los hablantes, al terminar la transcripción
    assert t["ocr"][0] == t["hablantes"][1]                # y el OCR después: nunca dos pesados a la vez


def test_el_ocr_no_espera_pasos_que_no_corren():
    assert simular({"capturas": 2, "ocr": 5})["ocr"][0] == 2  # transcripción importada
    assert simular({"transcripcion": 3.5, "capturas": 2, "ocr": 5})["ocr"][0] == 3.5  # sin separar hablantes


def test_procesa_y_reanuda_sin_repetir(correr_script, demo_vtt, tmp_path):
    r = correr_script("minutas.py", "procesar", demo_vtt.name)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "✓ transcripción: listo" in r.stdout and "✓ transcripción ilustrada: listo" in r.stdout
    salida = tmp_path / SALIDA
    for archivo in ("transcripcion.json", "transcripcion.txt", "transcripcion.srt", "transcripcion-ilustrada.html",
                    "reunion.json", "progreso.json", "_registro/hitos.log"):
        assert (salida / archivo).exists(), archivo
    manifiesto = json.loads((salida / "reunion.json").read_text(encoding="utf-8"))
    assert {p: d["estado"] for p, d in manifiesto["pasos"].items()} == {"transcripcion": "completo", "html": "completo"}
    assert json.loads((salida / "progreso.json").read_text(encoding="utf-8"))["estado"] == "completo"

    r = correr_script("minutas.py", "procesar", demo_vtt.name)
    assert r.stdout.count("al día") == 2 and "✓" not in r.stdout


def test_la_nota_se_recuerda(correr_script, demo_vtt, tmp_path):
    correr_script("minutas.py", "procesar", demo_vtt.name)
    r = correr_script("minutas.py", "procesar", demo_vtt.name, "--solo", "html", "--nota", "Nota de prueba")
    assert "✓ transcripción ilustrada" in r.stdout and "✓ transcripción:" not in r.stdout
    r = correr_script("minutas.py", "procesar", demo_vtt.name)
    assert r.stdout.count("al día") == 2
    assert "Nota de prueba" in (tmp_path / SALIDA / "transcripcion-ilustrada.html").read_text(encoding="utf-8")


def test_forzar_rehace_lo_que_depende(correr_script, demo_vtt):
    correr_script("minutas.py", "procesar", demo_vtt.name)
    r = correr_script("minutas.py", "procesar", demo_vtt.name, "--forzar", "transcripcion")
    assert "✓ transcripción: listo" in r.stdout and "✓ transcripción ilustrada: listo" in r.stdout


def test_glosario_del_proyecto_llega_al_html(correr_script, demo_vtt, tmp_path):
    (tmp_path / ".minutas-video").mkdir()
    (tmp_path / ".minutas-video" / "glosario.toml").write_text('[terminos]\nSMS = ["mensaje de texto"]\n', encoding="utf-8")
    (tmp_path / ".minutas-video" / "participantes.toml").write_text('[[persona]]\nnombre = "Luis Méndez"\n', encoding="utf-8")
    r = correr_script("minutas.py", "procesar", demo_vtt.name)
    assert "✓ glosario: listo" in r.stdout, r.stdout + r.stderr
    glos = json.loads((tmp_path / SALIDA / "glosario.json").read_text(encoding="utf-8"))
    assert glos["terminos"][0]["termino"] == "SMS" and glos["personas"][0]["nombre"] == "Luis Méndez"

    # Si se quita el glosario, su nota deja de aparecer y el HTML se rehace.
    for archivo in (tmp_path / ".minutas-video").iterdir():
        archivo.unlink()
    r = correr_script("minutas.py", "procesar", demo_vtt.name)
    assert not (tmp_path / SALIDA / "glosario.json").exists()
    assert "✓ transcripción ilustrada: listo" in r.stdout


def test_plan_en_json(correr_script, demo_vtt):
    r = correr_script("minutas.py", "procesar", demo_vtt.name, "--plan", "--preset", "rapido")
    plan = json.loads(r.stdout)
    entrada = plan["entradas"][0]
    assert entrada["tipo"] == "transcripcion" and entrada["procesada_antes"] is False
    assert entrada["acciones"]["transcripcion"] == {**entrada["acciones"]["transcripcion"], "accion": "correr", "motivo": "nuevo"}
    assert plan["config"]["efectiva"]["preset"] == "rapido" and plan["config"]["efectiva"]["minuta"] == "corta"
    assert set(plan["config"]["presets"]) == {"rapido", "estandar", "completo", "audio"}


def test_configuracion_invalida_no_procesa(correr_script, demo_vtt, tmp_path):
    (tmp_path / ".minutas-video").mkdir()
    (tmp_path / ".minutas-video" / "config.toml").write_text('preset = "turbo"\n', encoding="utf-8")
    r = correr_script("minutas.py", "procesar", demo_vtt.name)
    assert r.returncode != 0 and "Corrige la configuración" in r.stderr
    assert not (tmp_path / SALIDA).exists()


def test_seguir_sin_terminal_imprime_el_estado(correr_script, demo_vtt, tmp_path):
    correr_script("minutas.py", "procesar", demo_vtt.name)
    r = correr_script("minutas.py", "seguir", tmp_path / SALIDA)
    assert r.returncode == 0 and "reunion-demo.vtt · completo" in r.stdout


def test_video_con_transcripcion_importada_lee_el_texto_de_las_capturas(correr_script, demo_vtt, tmp_path):
    video = tmp_path / "reunion-demo.mp4"
    agenda = pantalla_con_texto(["Agenda de la revision", "Fecha de lanzamiento"])
    metricas = pantalla_con_texto(["Reservas por semana", "120 a 410"], fondo=(205, 225, 250))
    video_de_pantallas(video, [agenda, metricas, agenda])
    r = correr_script("minutas.py", "procesar", video.name, "--transcripcion", demo_vtt.name, "--ocr")
    assert r.returncode == 0, r.stdout + r.stderr
    for paso in ("transcripción", "capturas", "texto de las capturas", "transcripción ilustrada"):
        assert f"✓ {paso}: listo" in r.stdout, paso
    assert "3 capturas (1 repite una pantalla anterior)" in r.stdout
    salida = tmp_path / SALIDA
    assert "Reservas por semana" in (salida / "capturas.txt").read_text(encoding="utf-8")
    html = (salida / "transcripcion-ilustrada.html").read_text(encoding="utf-8")
    assert "Texto en pantalla" in html and 'igual a la <a href="#c0001">0001</a>' in html
    assert 'id="t3"' in html  # ancla de la primera frase, a la que enlaza minuta.md
    assert '<video id="medio" controls preload="metadata" src="../reunion-demo.mp4">' in html

    # Sin OCR, el HTML se rehace sin el texto de las capturas.
    r = correr_script("minutas.py", "procesar", video.name, "--no-ocr")
    assert "✓ transcripción ilustrada: listo" in r.stdout and "texto de las capturas" not in r.stdout
    assert "Texto en pantalla" not in (salida / "transcripcion-ilustrada.html").read_text(encoding="utf-8")


def test_plan_con_video_sin_ocr_ni_hablantes_salvo_que_se_pidan(correr_script, tmp_path):
    video = tmp_path / "junta.mp4"
    video.write_bytes(b"")  # el plan no abre el video
    acciones = json.loads(correr_script("minutas.py", "procesar", video.name, "--plan").stdout)["entradas"][0]["acciones"]
    assert {"transcripcion", "capturas", "html"} <= set(acciones) and not {"ocr", "hablantes"} & set(acciones)
    plan = json.loads(correr_script("minutas.py", "procesar", video.name, "--plan", "--ocr", "--separar-hablantes").stdout)
    assert {"ocr", "hablantes"} <= set(plan["entradas"][0]["acciones"])


def test_comando_minuta(correr_script, tmp_path):
    salida = tmp_path / "ejemplo"
    salida.mkdir()
    for archivo in ("transcripcion.json", "capturas.json", "ocr.json", "minuta.json"):
        shutil.copy(EJEMPLO / archivo, salida / archivo)
    r = correr_script("minutas.py", "minuta", salida)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "20 de 20 citas verificadas" in r.stdout and (salida / "minuta.md").exists()


def test_comando_exportar_csv_y_formato_desconocido(correr_script, tmp_path):
    salida = tmp_path / "ejemplo"
    salida.mkdir()
    shutil.copy(EJEMPLO / "minuta.md", salida / "minuta.md")
    r = correr_script("minutas.py", "exportar", salida, "csv")
    assert r.returncode == 0 and "✓ CSV" in r.stdout and (salida / "pendientes.csv").exists()
    r = correr_script("minutas.py", "exportar", salida, "ics")
    assert r.returncode != 0 and "Formatos desconocidos: ics" in r.stderr
