# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Revisa la máquina y recomienda cómo transcribir (GPU o CPU, modelo, paquetes extra para uv).

Uso: uv run entorno.py
Imprime un JSON. No instala nada.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from comun import configurar_consola

PAQUETES_CUDA = ["nvidia-cublas-cu12", "nvidia-cudnn-cu12>=9,<10"]


def gpu_nvidia():
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        r = subprocess.run(
            [exe, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    nombre, memoria, driver = [x.strip() for x in r.stdout.strip().splitlines()[0].split(",")]
    return {"nombre": nombre, "memoria": memoria, "driver": driver}


def modelos_descargados():
    base = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    if not base.is_dir():
        return []
    return sorted(
        p.name.split("--")[-1].replace("faster-whisper-", "")
        for p in base.glob("models--*--faster-whisper-*")
        if any(p.glob("snapshots/*/model.bin"))
    )


def recomendar():
    """Revisa el equipo y devuelve el diagnóstico con la recomendación (lo usa también minutas.py)."""
    gpu = gpu_nvidia()
    sistema = platform.system()
    cuda_por_pip = sistema in ("Windows", "Linux")
    libre_gb = round(shutil.disk_usage(Path.home()).free / 1024**3, 1)

    if gpu and cuda_por_pip:
        recomendacion = {
            "dispositivo": "cuda",
            "modelo": "large-v3",
            "uv_with": PAQUETES_CUDA,
            "nota": "GPU NVIDIA: con large-v3, unos 5 min por hora de audio en una GPU de laptop.",
        }
    else:
        recomendacion = {
            "dispositivo": "cpu",
            "modelo": "medium",
            "uv_with": [],
            "nota": "Sin GPU NVIDIA usable: medium en CPU tarda del orden de la duración del audio; "
                    "small es más rápido con menos precisión; large-v3 en CPU puede tardar varias veces la duración.",
        }

    descargados = modelos_descargados()
    return {
        "sistema": f"{sistema} {platform.release()} ({platform.machine()})",
        "python": sys.version.split()[0],
        "gpu_nvidia": gpu,
        "modelos_whisper_descargados": descargados,
        "espacio_libre_gb": libre_gb,
        "recomendacion": recomendacion,
        "avisos": [a for a in [
            "Poco espacio libre: large-v3 ocupa ~3 GB y las librerías CUDA ~1.5 GB." if libre_gb < 8 else None,
            "Primera vez con este modelo: se descargará de Hugging Face." if recomendacion["modelo"] not in descargados else None,
        ] if a],
    }


def main():
    configurar_consola()
    print(json.dumps(recomendar(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
