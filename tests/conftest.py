import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "skills" / "procesar-reunion" / "scripts"
EJEMPLO = RAIZ / "docs" / "ejemplo"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def uv():
    from minutas import localizar_uv
    return localizar_uv()


@pytest.fixture
def correr_script(uv, tmp_path):
    """Corre un script del plugin con uv, como lo haría Claude, con un usuario sin configuración."""
    def correr(script, *args, cwd=None, env=None):
        entorno = {**os.environ, "MINUTAS_HOME": str(tmp_path / "_usuario"), **(env or {})}
        return subprocess.run([uv, "run", "--script", str(SCRIPTS / script), *map(str, args)],
                              cwd=cwd or tmp_path, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=entorno)
    return correr


@pytest.fixture
def demo_vtt(tmp_path):
    destino = tmp_path / "reunion-demo.vtt"
    shutil.copy(EJEMPLO / "reunion-demo.vtt", destino)
    return destino


def video_de_pantallas(ruta, pantallas, fps=10, segundos=3):
    """Escribe un video mpeg4 que muestra cada imagen (arreglo RGB de numpy) durante `segundos`."""
    import av
    alto, ancho = pantallas[0].shape[:2]
    with av.open(str(ruta), "w") as c:
        s = c.add_stream("mpeg4", rate=fps)
        s.width, s.height, s.pix_fmt = ancho, alto, "yuv420p"
        s.bit_rate = 2_000_000
        for img in pantallas:
            for _ in range(fps * segundos):
                for paquete in s.encode(av.VideoFrame.from_ndarray(img, format="rgb24")):
                    c.mux(paquete)
        for paquete in s.encode():
            c.mux(paquete)


def pantalla_con_texto(lineas, ancho=960, alto=540, fondo=(250, 250, 250)):
    """Una "lámina" con texto grande, legible para el OCR."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (ancho, alto), fondo)
    d = ImageDraw.Draw(img)
    fuente = ImageFont.load_default(size=44)
    for i, linea in enumerate(lineas):
        d.text((50, 50 + i * 80), linea, font=fuente, fill=(20, 20, 20))
    return np.asarray(img)
