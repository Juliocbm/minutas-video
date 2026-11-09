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
