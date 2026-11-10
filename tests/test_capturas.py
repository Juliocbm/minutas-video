"""Detección de capturas con videos sintéticos de "pantallas" de 3 segundos."""
import json

import pytest

from conftest import video_de_pantallas

av = pytest.importorskip("av")
np = pytest.importorskip("numpy")


def pantallas_de_bloques(orden):
    """Pantallas distintas por la posición de un bloque de color; `orden` repite índices (A→B→A)."""
    ancho, alto = 320, 180
    pantallas = []
    for i in orden:
        img = np.full((alto, ancho, 3), 235, dtype=np.uint8)
        x = 20 + i * 100
        img[30:150, x:x + 80] = (30, 60 + 60 * i, 200 - 60 * i)
        pantallas.append(img)
    return pantallas


def leer(salida):
    return json.loads((salida / "capturas.json").read_text(encoding="utf-8"))["capturas"]


def test_una_captura_por_pantalla_y_avance(correr_script, tmp_path):
    video = tmp_path / "pantallas.mp4"
    video_de_pantallas(video, pantallas_de_bloques([0, 1, 2]))
    r = correr_script("extraer_capturas.py", video, "--salida", tmp_path / "salida", env={"MINUTAS_PROGRESO": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    capturas = leer(tmp_path / "salida")
    assert [c["motivo"] for c in capturas] == ["inicio", "estable", "estable"]
    assert [round(c["desde"]) for c in capturas] == [0, 3, 6]
    assert all((tmp_path / "salida" / c["archivo"]).exists() for c in capturas)
    assert not any("igual_a" in c for c in capturas)
    avances = [json.loads(x[10:]) for x in r.stdout.splitlines() if x.startswith("@progreso ")]
    assert avances[0] == {"paso": "capturas", "fase": "buscando cambios de pantalla"}
    assert any("hecho" in a and a["total"] > 8 for a in avances)


def test_la_pantalla_que_vuelve_se_marca_y_conserva_su_imagen(correr_script, tmp_path):
    video = tmp_path / "vuelve.mp4"
    video_de_pantallas(video, pantallas_de_bloques([0, 1, 2, 0]))
    r = correr_script("extraer_capturas.py", video, "--salida", tmp_path / "salida")
    assert r.returncode == 0, r.stdout + r.stderr
    capturas = leer(tmp_path / "salida")
    assert [c.get("igual_a") for c in capturas] == [None, None, None, 1]
    assert (tmp_path / "salida" / capturas[3]["archivo"]).exists()
    assert "1 iguales a una anterior" in r.stdout


def test_audio_sin_video_no_tiene_capturas(correr_script, tmp_path):
    audio = tmp_path / "solo-audio.wav"
    with av.open(str(audio), "w") as c:
        s = c.add_stream("pcm_s16le", rate=16000, layout="mono")
        frame = av.AudioFrame.from_ndarray(np.zeros((1, 16000), dtype=np.int16), format="s16", layout="mono")
        frame.sample_rate = 16000
        for paquete in s.encode(frame):
            c.mux(paquete)
        for paquete in s.encode():
            c.mux(paquete)
    r = correr_script("extraer_capturas.py", audio, "--salida", tmp_path / "salida")
    assert r.returncode == 0, r.stdout + r.stderr
    assert leer(tmp_path / "salida") == []
