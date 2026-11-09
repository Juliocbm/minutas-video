# Solución de problemas

## uv

**`uv` no se encuentra justo después de instalarlo (Windows).**
El proceso de Claude Code arrancó con el PATH anterior a la instalación. Busca el ejecutable y usa su ruta completa:
- `%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe`
- `%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_*\uv.exe`
- `%USERPROFILE%\.local\bin\uv.exe`

Al reiniciar el editor ya aparece en el PATH.

**winget responde "ya instalado" pero `uv` no aparece.** Es el mismo caso: búscalo en esas rutas.

**La primera ejecución tarda mucho.** uv descarga Python si hace falta y las dependencias de cada script. Las librerías CUDA pesan alrededor de 1.5 GB. Se guardan en caché y no se repiten.

## El proceso (`minutas.py`)

**Se interrumpió o falló a la mitad.** Vuelve a correr el mismo comando: lo que terminó con los mismos parámetros no se repite. `reunion.json` dice qué pasos están completos y `_registro/<paso>.log` trae el error completo.

**Quiero rehacer un paso aunque esté al día.** `--forzar transcripcion` (o `capturas`, `glosario`, `html`, `todo`). Lo que depende de ese paso se rehace solo.

**Quiero cambiar solo la nota o el título del HTML.** `--solo html --nota "…"`. La nota y el título se recuerdan en las siguientes corridas de esa reunión.

**Usé el .vtt de la plataforma y ahora quiero Whisper.** `--transcripcion whisper`. Las opciones que pasas por la línea de comandos se recuerdan para esa reunión; así se olvida el archivo importado.

**"Corrige la configuración antes de procesar".** Un archivo de `.minutas-video/` tiene un error. El mensaje dice cuál y qué clave; `minutas.py config` muestra todo.

**No veo el avance.** Cuando lo lanza Claude, la salida no es una terminal y solo hay hitos (25, 50 y 75 %). Para ver barras en vivo, corre en tu terminal `minutas.py seguir "<salida>"`.

## Transcripción

**`Could not locate cudnn_ops64_9.dll`, `cublas64_12.dll` o errores de CUDA al empezar.**
Faltan las librerías CUDA en el entorno. Corre con
`--with nvidia-cublas-cu12 --with "nvidia-cudnn-cu12>=9,<10"`, o usa `--dispositivo cpu`.

**El driver de NVIDIA es muy viejo.** Las librerías son de CUDA 12 y necesitan un driver reciente. Actualízalo o usa CPU.

**`CUDA out of memory`.** Usa un modelo más chico (`--modelo medium`) o cierra otros programas que usen la GPU.

**`mkl_malloc: failed to allocate memory` (o la transcripción va mucho más lenta de lo normal).**
Al equipo le falta memoria. Suele pasar con muchos programas abiertos o con dos transcripciones a la vez. No corras dos transcripciones en paralelo: extraer capturas junto con una transcripción sí está bien. Cierra programas o usa un modelo más chico.

**Sin GPU es muy lento.** Usa `--modelo medium` o `small`. large-v3 en CPU puede tardar varias veces la duración del audio.

**"hay varias pistas de audio".** Es típico de OBS: una pista para el micrófono y otra para el escritorio. Prueba unos minutos con cada `--pista N` para ver cuál trae la conversación completa.

**Siglas o nombres propios mal escritos.** Es normal. Anótalos con sus variantes en `.minutas-video/glosario.toml`: `minutas.py` las encuentra, guarda dónde aparecen en `glosario.json` y pone la nota de corrección en el HTML. No los pases a Whisper como `hotwords` o `initial_prompt`: en pruebas, eso hizo que repitiera la lista, inventara frases en otros idiomas y perdiera la mitad del contenido.

**Texto repetido o inventado en los silencios.** Ya se usa un filtro de voz (VAD). Si persiste, el audio probablemente tiene ruido de fondo o música. Revisa ese tramo en el video antes de citarlo.

**La descarga del modelo falla.** Los modelos vienen de Hugging Face y se guardan en `~/.cache/huggingface` (o en `HF_HOME`). Revisa la conexión o el proxy. El aviso "unauthenticated requests" es normal y no impide la descarga.

## Capturas

**Demasiadas capturas.** Pasa cuando el video tiene movimiento constante (cámara, demos con video). Sube `--umbral-cambio` (ej. 0.08), usa `--modo camara` o baja `--max`.

**Muy pocas capturas.** Ocurre con cambios sutiles, como scroll corto o resaltados. Baja `--umbral-cambio` (ej. 0.02). Un tramo largo sin capturas casi siempre es una pantalla fija: confírmalo con `hojas_contacto.py tiempos`.

**Algo animado genera capturas de más.** Un GIF en una firma de correo, por ejemplo. El chequeo de estabilidad suele filtrarlo; si no, sube un poco `--umbral-cambio`.

## Otros

**Acentos raros en la consola.** Los scripts fuerzan UTF-8 en su salida. Si los archivos se ven mal, ábrelos como UTF-8.

**macOS.** No hay CUDA: la transcripción corre en CPU. Usa `medium` o `small` para que sea ágil.
