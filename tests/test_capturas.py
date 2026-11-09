"""Detección de capturas con un video sintético de tres "pantallas" de 3 segundos."""
import json

import pytest

av = pytest.importorskip("av")
np = pytest.importorskip("numpy")


def video_sintetico(ruta, fps=10, segundos_por_pantalla=3):
    ancho, alto = 320, 180
    pantallas = []
    for i in range(3):
        img = np.full((alto, ancho, 3), 235, dtype=np.uint8)
        x = 20 + i * 100
        img[30:150, x:x + 80] = (30, 60 + 60 * i, 200 - 60 * i)  # un bloque en otra posición
        pantallas.append(img)
    with av.open(str(ruta), "w") as c:
        s = c.add_stream("mpeg4", rate=fps)
        s.width, s.height, s.pix_fmt = ancho, alto, "yuv420p"
        for img in pantallas:
            for _ in range(fps * segundos_por_pantalla):
                for paquete in s.encode(av.VideoFrame.from_ndarray(img, format="rgb24")):
                    c.mux(paquete)
        for paquete in s.encode():
            c.mux(paquete)


def test_una_captura_por_pantalla_y_avance(correr_script, tmp_path):
    video = tmp_path / "pantallas.mp4"
    video_sintetico(video)
    r = correr_script("extraer_capturas.py", video, "--salida", tmp_path / "salida", env={"MINUTAS_PROGRESO": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    capturas = json.loads((tmp_path / "salida" / "capturas.json").read_text(encoding="utf-8"))["capturas"]
    assert [c["motivo"] for c in capturas] == ["inicio", "estable", "estable"]
    assert [round(c["desde"]) for c in capturas] == [0, 3, 6]
    assert all((tmp_path / "salida" / c["archivo"]).exists() for c in capturas)
    avances = [json.loads(x[10:]) for x in r.stdout.splitlines() if x.startswith("@progreso ")]
    assert avances[0] == {"paso": "capturas", "fase": "buscando cambios de pantalla"}
    assert any("hecho" in a and a["total"] > 8 for a in avances)


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
    assert json.loads((tmp_path / "salida" / "capturas.json").read_text(encoding="utf-8"))["capturas"] == []
