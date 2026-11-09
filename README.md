<p align="center">
  <img src="assets/logo.svg" width="120" alt="minutas-video">
</p>

<h1 align="center">minutas-video</h1>

<p align="center">
  <b>De la grabación de una reunión a una minuta que se puede verificar.</b><br>
  Transcripción local con Whisper · capturas de lo que se mostraba · transcripción ilustrada · minuta con acuerdos y pendientes
</p>

<p align="center">
  <a href="CHANGELOG.md"><img alt="Versión" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FJuliocbm%2Fminutas-video%2Fmain%2F.claude-plugin%2Fplugin.json&query=%24.version&label=versi%C3%B3n&color=0d9488"></a>
  <a href="LICENSE"><img alt="Licencia MIT" src="https://img.shields.io/github/license/Juliocbm/minutas-video?label=licencia&color=blue"></a>
  <a href="https://docs.claude.com/en/docs/claude-code"><img alt="Plugin de Claude Code" src="https://img.shields.io/badge/Claude%20Code-plugin-D97757?logo=claude&logoColor=white"></a>
  <a href="https://www.python.org/"><img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white"></a>
  <a href="https://docs.astral.sh/uv/"><img alt="uv" src="https://img.shields.io/badge/dependencias-uv-DE5FE9?logo=uv&logoColor=white"></a>
  <a href="https://github.com/SYSTRAN/faster-whisper"><img alt="faster-whisper" src="https://img.shields.io/badge/transcripci%C3%B3n-faster--whisper-0A7E8C"></a>
  <a href="#requisitos"><img alt="GPU NVIDIA opcional" src="https://img.shields.io/badge/GPU-NVIDIA%20opcional-76B900?logo=nvidia&logoColor=white"></a>
  <a href="#requisitos"><img alt="Probado en Windows 11" src="https://img.shields.io/badge/probado%20en-Windows%2011-0078D4"></a>
  <a href="https://github.com/Juliocbm/minutas-video/commits/main"><img alt="Último commit" src="https://img.shields.io/github/last-commit/Juliocbm/minutas-video?label=%C3%BAltimo%20commit"></a>
  <a href="https://github.com/Juliocbm/minutas-video/stargazers"><img alt="Estrellas" src="https://img.shields.io/github/stars/Juliocbm/minutas-video?style=social"></a>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/demo-oscuro.png">
    <img src="assets/demo-claro.png" width="900" alt="Transcripción ilustrada: cada captura de pantalla junto a lo que se dijo mientras estuvo visible">
  </picture>
  <br>
  <sub>Transcripción ilustrada de la <a href="docs/ejemplo/">reunión de ejemplo</a> (datos ficticios) · <a href="docs/ejemplo/minuta.md">su minuta</a></sub>
</p>

---

## ¿Qué hace?

Le pasas a Claude la grabación de una junta y te devuelve:

- **La transcripción** con marcas de tiempo (`.txt` y `.srt`), hecha en tu máquina.
- **Capturas** automáticas cada vez que cambia lo que se muestra en pantalla.
- **Una transcripción ilustrada** en HTML: cada captura junto a lo que se dijo mientras estuvo visible. Así "como ven aquí…" vuelve a tener sentido.
- **Una minuta** con acuerdos, temas y pendientes, cada uno con su minuto y su captura. Si le das documentos relacionados, señala qué cambió la reunión respecto a lo escrito.
- Opcional: **un paquete de contexto** para pegarle lo acordado a otra sesión de Claude, por ejemplo la que implementa lo que se decidió.

Funciona con cualquier grabación: videollamadas (Teams, Zoom, Meet), grabaciones de pantalla (OBS), juntas presenciales o solo audio. No depende de ninguna plataforma.

## Instalación

En Claude Code:

```
/plugin marketplace add Juliocbm/minutas-video
/plugin install minutas-video@minutas-video
```

No hay que instalar nada más a mano: la primera vez, la skill revisa tu equipo y, con tu permiso, instala [uv](https://docs.astral.sh/uv/), que se encarga de Python y de las dependencias.

## Uso

Pídeselo a Claude con tus palabras:

> Procesa la junta que grabé en `C:\Grabaciones\2026-11-05 revisión.mkv` y hazme la minuta.

> Transcribe este audio y dime qué se acordó: `~/Descargas/llamada-proveedor.m4a`

> Aquí está el video y el .vtt que exportó Teams. Compara lo acordado con `docs/analisis.md`.

La skill `procesar-reunion` se activa sola. También puedes invocarla con `/minutas-video:procesar-reunion`.

## Entradas y salidas

| Entrada | |
|---|---|
| **Grabación** (obligatoria) | Video (mp4, mkv, mov, webm) o audio (m4a, mp3, wav) |
| Transcripción con nombres | `.vtt`/`.srt` exportado de Teams, Zoom o Meet: aporta quién dijo qué |
| Vocabulario del proyecto | `.minutas-video/vocabulario.txt`: siglas y nombres propios para corregir la minuta |
| Documentos relacionados | Análisis, planes o código para contrastar con lo acordado |

| Salida (en `<grabación>_minuta/`) | Lo genera |
|---|---|
| `transcripcion.txt` · `.srt` · `.json` | Whisper, en local |
| `capturas/` · `capturas.json` | Comparación de imágenes, en local |
| `transcripcion-ilustrada.html` | Script, en local |
| `minuta.md` · `contexto-<tema>.md` | Claude |

El detalle de cada formato está en [docs/salidas.md](docs/salidas.md).

## Cómo funciona

- **Whisper** (IA de voz) transcribe en tu GPU o CPU. No necesita internet una vez descargado el modelo.
- **Las capturas no usan IA:** se compara cada segundo del video con la última captura y se guarda cuando el cambio es grande y la imagen ya se estabilizó.
- **Claude** orquesta todo y redacta la minuta: lee la transcripción, revisa las capturas que importan, separa acuerdos de propuestas y contrasta con tus documentos.

Más detalle en [docs/arquitectura.md](docs/arquitectura.md). Los scripts también se pueden [usar sin Claude](docs/uso-sin-claude.md).

## Requisitos

| | |
|---|---|
| **Claude Code** | Para usarlo como plugin |
| **GPU NVIDIA** (opcional) | Unos 5 min por hora de audio con el modelo large-v3. Requiere un driver reciente; las librerías CUDA se instalan solas |
| **Sin GPU** | Funciona en CPU con modelos más chicos (medium o small) |
| **Espacio** | ~3 GB para el modelo large-v3 y ~1.5 GB para las librerías CUDA, descargados una vez |

Probado en Windows 11 con GPU NVIDIA. Los scripts son multiplataforma, pero macOS y Linux aún no se han probado ([backlog](BACKLOG.md)).

## Quién dijo qué

Whisper recibe el audio ya mezclado y no distingue voces. Si la plataforma generó una transcripción con nombres (Teams, Zoom y Meet pueden exportar `.vtt`), dásela junto con el video: la skill la importa con los hablantes exactos. La separación automática de voces está en el [backlog](BACKLOG.md).

## Vocabulario del proyecto

Whisper confunde siglas y nombres propios. Crea `.minutas-video/vocabulario.txt` en tu proyecto, con un término por línea, y Claude lo usará para corregirlos en la minuta:

```
Kubernetes
SAP
OKR
```

La transcripción queda fiel al audio: forzar el vocabulario dentro de Whisper la degradaba (ver [CHANGELOG](CHANGELOG.md)).

## Privacidad

- La transcripción y las capturas se generan en tu equipo.
- Para redactar la minuta, Claude lee la transcripción y algunas capturas, igual que cualquier archivo que le compartes.
- Las salidas contienen el contenido de la reunión: no las guardes en un repositorio público.

## Documentación

- [Arquitectura](docs/arquitectura.md): flujo, qué es IA y qué no, decisiones de diseño.
- [Formato de las salidas](docs/salidas.md).
- [Uso sin Claude](docs/uso-sin-claude.md).
- [Ejemplo completo](docs/ejemplo/): reunión ficticia con todas sus salidas.
- [Solución de problemas](skills/procesar-reunion/references/solucion-problemas.md).
- [CHANGELOG](CHANGELOG.md) · [Backlog](BACKLOG.md).

## Licencia

[MIT](LICENSE) © Juliocbm
