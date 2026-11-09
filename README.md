# minutas-video

Plugin de [Claude Code](https://docs.claude.com/en/docs/claude-code) que convierte la grabación de una reunión en archivos que se pueden leer, buscar y compartir:

- **Transcripción** con marcas de tiempo (`.txt` y `.srt`), hecha en tu máquina con [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
- **Capturas de pantalla** automáticas cada vez que cambia lo que se muestra.
- **Transcripción ilustrada** en HTML: cada captura junto a lo que se dijo mientras estuvo visible.
- **Minuta** con acuerdos, temas y pendientes, cada uno con su minuto y su captura. La redacta Claude cruzando lo dicho con lo que se veía.
- Opcional: un **paquete de contexto** para pegarle lo acordado a otra sesión de Claude.

Funciona con cualquier grabación: videollamadas (Teams, Zoom, Meet), grabaciones de pantalla (OBS), juntas presenciales o solo audio (notas de voz, grabadora). No depende de ninguna plataforma.

## Instalación

En Claude Code:

```
/plugin marketplace add Juliocbm/minutas-video
/plugin install minutas-video@minutas-video
```

## Uso

Pídeselo a Claude con tus palabras, por ejemplo:

> Procesa la junta que grabé en `C:\Grabaciones\2026-11-05 revisión.mkv` y hazme la minuta.

> Transcribe este audio y dime qué se acordó: `~/Descargas/llamada-proveedor.m4a`

La skill `procesar-reunion` se activa sola. También puedes invocarla como `/minutas-video:procesar-reunion`.

## Requisitos

No tienes que instalar nada a mano: la skill revisa tu equipo y, con tu permiso, instala [uv](https://docs.astral.sh/uv/), que se encarga de Python y de las dependencias de cada script en entornos aislados.

| | |
|---|---|
| **GPU NVIDIA** (opcional) | Transcripción rápida: unos 5 min por hora de audio con el modelo large-v3. Requiere un driver reciente; las librerías CUDA se instalan solas. |
| **Sin GPU** | Funciona en CPU con modelos más chicos (medium o small); tarda más o menos lo que dura el audio. |
| **Espacio** | ~3 GB para el modelo large-v3 y ~1.5 GB para las librerías CUDA, descargados una sola vez. |

Probado en Windows 11 con una GPU NVIDIA de laptop. Los scripts son multiplataforma, pero macOS y Linux aún no se han probado.

## Quién dijo qué

Whisper recibe el audio ya mezclado y no distingue voces. Hay dos caminos:

- **Si la plataforma generó una transcripción con nombres** (Teams, Zoom o Meet pueden exportar `.vtt`), dásela a Claude junto con el video. La skill la importa y la usa en lugar de Whisper, con los hablantes exactos.
- **La separación automática de voces** está en el [backlog](BACKLOG.md).

## Vocabulario del proyecto

Whisper confunde siglas y nombres propios. Crea `.minutas-video/vocabulario.txt` en tu proyecto, con un término por línea, y Claude lo usará para corregirlos en la minuta. La transcripción queda fiel al audio: forzar el vocabulario dentro de Whisper la degradaba.

```
# vocabulario.txt
Kubernetes
SAP
OKR
```

## Privacidad

- La transcripción y las capturas se generan en tu equipo.
- Para redactar la minuta, Claude lee la transcripción y algunas capturas, igual que lee cualquier archivo que le compartes.
- Las salidas contienen el contenido de la reunión: no las guardes dentro de un repositorio público.

## Usar los scripts sin Claude

Cada script declara sus dependencias y se puede ejecutar directo con uv (`uv run --script <script> --help`):

```
cd skills/procesar-reunion/scripts
uv run --script entorno.py
uv run --with nvidia-cublas-cu12 --with "nvidia-cudnn-cu12>=9,<10" --script transcribir.py "reunion.mkv" --salida "reunion_minuta"
uv run --script extraer_capturas.py "reunion.mkv" --salida "reunion_minuta"
uv run --script armar_html.py "reunion_minuta" --titulo "Revisión semanal"
```

## Licencia

[MIT](LICENSE)
