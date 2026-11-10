"""Transcripción ilustrada: reproductor, frases con su segundo, búsqueda y filtro por hablante."""
import json
import re
import shutil

import pytest

from conftest import EJEMPLO


@pytest.fixture
def salida(tmp_path):
    destino = tmp_path / "junta del lunes_minuta"
    destino.mkdir()
    for archivo in ("transcripcion.json", "capturas.json", "ocr.json"):
        shutil.copy(EJEMPLO / archivo, destino / archivo)
    shutil.copytree(EJEMPLO / "capturas", destino / "capturas")
    return destino


def html_de(salida):
    return (salida / "transcripcion-ilustrada.html").read_text(encoding="utf-8")


def test_reproductor_con_ruta_relativa_y_frases_con_su_segundo(correr_script, salida):
    video = salida.parent / "junta del lunes.mkv"
    video.write_bytes(b"")
    r = correr_script("armar_html.py", salida, "--medio", video)
    assert r.returncode == 0, r.stdout + r.stderr
    html = html_de(salida)
    assert '<video id="medio" controls preload="metadata" src="../junta%20del%20lunes.mkv">' in html
    segmentos = json.loads((salida / "transcripcion.json").read_text(encoding="utf-8"))["segmentos"]
    assert len(re.findall(r'<span data-t="', html)) == len(segmentos)
    assert '<span data-t="285.00" id="t285">' in html              # las anclas de la minuta siguen ahí
    assert 'id="buscar"' in html and 'Texto en pantalla' in html
    assert '<select id="hablante"' in html and html.count('<p data-hablante="Ana Torres">') > 3
    assert 'class="con-capturas"' in html


def test_audio_y_grabacion_que_no_existe(correr_script, salida):
    audio = salida.parent / "llamada.m4a"
    audio.write_bytes(b"")
    correr_script("armar_html.py", salida, "--medio", audio, "--sin-capturas")
    html = html_de(salida)
    assert '<audio id="medio"' in html and 'id="mini"' not in html and '<main class="solo">' in html

    r = correr_script("armar_html.py", salida, "--medio", salida.parent / "no-existe.mp4")
    assert "AVISO: no existe" in r.stdout and 'id="medio"' not in html_de(salida)
    assert 'id="buscar"' in html_de(salida)  # la búsqueda no depende del reproductor
