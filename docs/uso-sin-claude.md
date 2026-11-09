# Usar los scripts sin Claude

Las piezas mecánicas funcionan solas desde la terminal: transcripción, capturas y HTML. Solo necesitas [uv](https://docs.astral.sh/uv/getting-started/installation/). Lo que no obtienes sin Claude es la minuta, porque esa es la parte de análisis.

```bash
cd skills/procesar-reunion/scripts

# 1. ¿GPU? ¿Qué modelo? (no instala nada)
uv run --script entorno.py

# 2a. Transcribir con GPU NVIDIA (Windows/Linux)
uv run --with nvidia-cublas-cu12 --with "nvidia-cudnn-cu12>=9,<10" --script transcribir.py "reunion.mkv" --salida "reunion_minuta"

# 2b. … o en CPU
uv run --script transcribir.py "reunion.mkv" --salida "reunion_minuta" --modelo medium --dispositivo cpu

# 2c. … o importar una transcripción con nombres (Teams/Zoom)
uv run --script importar_transcripcion.py "reunion.vtt" --salida "reunion_minuta"

# 3. Capturas (solo con video)
uv run --script extraer_capturas.py "reunion.mkv" --salida "reunion_minuta" --modo pantalla

# 4. Transcripción ilustrada
uv run --script armar_html.py "reunion_minuta" --titulo "Revisión semanal"
```

Cada script tiene `--help` con todas sus opciones. La primera ejecución tarda más porque uv descarga Python y las dependencias, y Whisper descarga el modelo. Luego todo queda en caché.

## Opciones útiles

| Script | Opción | Para qué |
|---|---|---|
| `transcribir.py` | `--idioma auto` | Detectar el idioma (por defecto `es`) |
| | `--pista N` | Elegir la pista de audio, si la grabación tiene varias |
| | `--modelo small` | Más rápido y menos preciso (`tiny`, `base`, `small`, `medium`, `large-v3`) |
| `extraer_capturas.py` | `--modo camara` | Juntas presenciales: solo cambios grandes (experimental) |
| | `--umbral-cambio 0.08` | Menos capturas, si salen demasiadas |
| | `--max 100` | Tope de capturas |
| `armar_html.py` | `--incrustar` | Un solo archivo con las imágenes adentro |
| | `--nota "…"` | Aviso destacado al inicio (por ejemplo, términos mal transcritos) |
| `hojas_contacto.py` | `capturas <salida>` | Hojas de 12 miniaturas para revisar todo de un vistazo |
| | `tiempos <video> --destino <dir> 120 340` | Cuadros del video en segundos puntuales |
