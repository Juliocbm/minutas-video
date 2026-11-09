# Backlog

Pendientes del plugin. Al cerrar uno, se borra de aquí.

## T1 · Separar voces (quién dijo qué) — siguiente fase

Whisper recibe el audio mezclado y no distingue hablantes. Si no hay una transcripción exportada de la plataforma, el texto queda sin nombres.

- **Herramienta:** `pyannote.audio`, diarización local que corre en la GPU.
- **Requisitos:** cuenta en Hugging Face, aceptar las condiciones del modelo de diarización y un token (`HF_TOKEN`).
- **Integración:**
  - Cruzar por tiempo los turnos de pyannote con los segmentos de `transcripcion.json` y llenar `hablante` con "Hablante 1/2/…".
  - Claude propone nombres por contexto (se llaman entre sí, mosaico de la videollamada) y el usuario los confirma.
  - `armar_html.py` y el `.txt` ya muestran hablantes cuando existen.
- **Expectativa realista:** funciona bien con audio limpio. Falla cuando hablan a la vez, cuando las voces se parecen o cuando un solo micrófono capta una sala.

## T2 · Calibrar el modo cámara con grabaciones reales

Los umbrales de `--modo camara` son una estimación: no se han probado con video de una junta presencial.

## T3 · Importar transcripciones .docx de Teams

Hoy se importan `.vtt` y `.srt`. Teams también exporta `.docx`.

## T4 · Probar en macOS y Linux

Solo se ha probado en Windows 11 con GPU NVIDIA.
