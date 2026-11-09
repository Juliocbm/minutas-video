---
name: procesar-reunion
description: Convierte la grabación de una reunión, junta, videollamada o conversación (video o solo audio, como mp4, mkv, mov, webm, m4a, mp3 o wav) en transcripción con tiempos (.txt y .srt), capturas de lo que se mostraba en pantalla, una transcripción ilustrada en HTML y una minuta con acuerdos y pendientes; opcionalmente, un resumen de contexto para pasárselo a otra sesión de Claude. El audio se transcribe en local con Whisper (GPU opcional) y los requisitos se instalan solos con uv. Úsala siempre que el usuario quiera transcribir o sacar el texto de un video o audio, saber qué se dijo o se acordó en una junta grabada (Teams, Zoom, Meet, OBS o presencial), hacer la minuta o el resumen de una reunión, o comparta la ruta de una grabación de una reunión, aunque no diga "minuta" ni "transcripción". También sirve para importar un .vtt o .srt de Teams o Zoom con los nombres de los participantes.
---

# Procesar reunión

Convierte una grabación en archivos que se pueden leer, buscar y compartir. Las salidas quedan en una carpeta:

| Archivo | Qué es |
|---|---|
| `transcripcion.txt` | Párrafos con `[hh:mm:ss]` y el nombre de quien habla cuando se conoce |
| `transcripcion.srt` | Subtítulos con tiempos (se abren junto al video en cualquier reproductor) |
| `transcripcion.json` | Formato intermedio que leen los scripts |
| `capturas/` + `capturas.json` | Una imagen cada vez que cambia lo que se ve en pantalla |
| `transcripcion-ilustrada.html` | Cada captura junto a lo que se dijo mientras estuvo visible |
| `minuta.md` | La redactas tú: acuerdos, temas y pendientes, con minuto y captura |
| `contexto-<tema>.md` | Opcional: paquete de contexto para otra sesión de Claude |

Los scripts están en `scripts/`, junto a este archivo. Llámalos con la ruta absoluta del directorio base de esta skill (Claude Code la indica al cargarla); abajo aparece como `<skill>`. Pon siempre las rutas entre comillas: los nombres de las grabaciones suelen tener espacios.

## 0. Acordar lo mínimo

Pregunta solo lo que no esté claro; no hagas un interrogatorio.

- **Grabación**: la ruta del archivo.
- **Carpeta de salida**: por defecto `<carpeta de la grabación>/<nombre de la grabación>_minuta/`.
- **Idioma**: español por defecto; `auto` si no se sabe.
- **¿Hay una transcripción existente con nombres?** Puede ser un .vtt o .srt exportado de Teams, Zoom o Meet. Si existe, úsala en lugar de Whisper. La plataforma recibe el audio de cada participante por separado y por eso sabe con certeza quién dijo cada frase; Whisper solo recibe el audio mezclado y no distingue voces.
- **Capturas**:
  - `pantalla`: grabaciones de pantalla y videollamadas. Es el modo por defecto cuando hay video.
  - `camara`: juntas presenciales grabadas con cámara. Es experimental y solo aporta si se ve un proyector o un pizarrón.
  - `ninguna`: para audio.
- **Entregables**: por defecto todo, menos el contexto para otra sesión, que se hace solo si lo pide.
- **Vocabulario**: si el proyecto actual tiene `.minutas-video/vocabulario.txt` (un término por línea), léelo antes del paso 4. Whisper confunde siglas y nombres propios: escribe una palabra común que suena parecido, por ejemplo "Sam" en lugar de una sigla de tres letras. Con esa lista los reconoces y los corriges en la minuta y en la nota del HTML. No se le pasa a Whisper: en pruebas, hacerlo provocó que repitiera la lista e inventara texto. Si la reunión trata de sistemas con nombres propios y el archivo no existe, ofrece crearlo.

La primera vez que aplique, menciona la privacidad:
- La transcripción se hace en la máquina.
- El texto y las capturas que revises en el paso 4 sí pasan por el modelo.
- La carpeta de salida contiene el contenido de la reunión: no debe quedar dentro de un repositorio público.

## 1. Entorno

1. Busca uv con `uv --version`. En Windows, si no aparece, la sesión puede tener un PATH anterior a la instalación. Busca en este orden y usa la ruta completa:
   - `%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe`
   - `%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_*\uv.exe`
   - `%USERPROFILE%\.local\bin\uv.exe`
2. Si no está instalado, pide permiso e instálalo:
   - Windows: `winget install --id astral-sh.uv -e`. Si no hay winget: `python -m pip install --user uv`.
   - macOS y Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`.
3. Corre `uv run --script "<skill>/scripts/entorno.py"`. Devuelve un JSON con la GPU, los modelos ya descargados y una `recomendacion` con el dispositivo, el modelo y los paquetes extra (`uv_with`).

Si es la primera vez, avisa que tardará más: uv descarga las dependencias (unos 1.5 GB más si hay GPU) y Whisper descarga el modelo (unos 3 GB para large-v3). Los usos siguientes arrancan en segundos.

## 2. Transcripción y capturas

Las dos tareas tardan minutos. Lánzalas a la vez y en segundo plano, y espera la notificación. La transcripción y las capturas pueden correr juntas; dos transcripciones a la vez no, porque agotan la memoria.

**Transcripción**, una de dos:
- **Con Whisper:**
  ```
  uv run [--with "<paquete>" por cada uno de uv_with] --script "<skill>/scripts/transcribir.py" "<grabación>" --salida "<salida>" --modelo <modelo> [--idioma es|auto]
  ```
  Si avisa que hay varias pistas de audio (OBS puede grabar el micrófono y el escritorio por separado), averigua cuál trae la conversación y repite con `--pista N`.
- **Con una transcripción existente:**
  ```
  uv run --script "<skill>/scripts/importar_transcripcion.py" "<archivo.vtt|.srt>" --salida "<salida>"
  ```

**Capturas** (solo si hay video):
```
uv run --script "<skill>/scripts/extraer_capturas.py" "<grabación>" --salida "<salida>" --modo pantalla|camara
```

Como referencia, en una laptop con GPU NVIDIA, un video de 35 min tardó unos 3 min en transcribirse y 1.5 min en sacar 58 capturas. Para errores, consulta `references/solucion-problemas.md`.

## 3. Transcripción ilustrada

```
uv run --script "<skill>/scripts/armar_html.py" "<salida>" --titulo "<tema · fecha>" --nota "<aviso para el lector>"
```

- En `--nota` pon que la transcripción es automática y qué términos salen mal escritos. Eso lo sabrás después del paso 4, así que regenera el HTML al final con la nota completa; tarda un segundo.
- `--incrustar` mete las imágenes dentro del HTML: queda un solo archivo, cómodo para compartir pero pesado (con 58 capturas pesó 13 MB). Sin esta opción, el HTML necesita la carpeta `capturas/` al lado.

## 4. Revisar

Aquí está el valor: cruzar lo que se dijo con lo que se veía. Sin este paso, la minuta sería solo un resumen de texto.

1. **Lee `transcripcion.txt` completo.** Si la reunión es larga, léelo por tramos y toma notas. Identifica los temas, las decisiones, las dudas y los términos que Whisper escribió mal.
2. **Genera las hojas de miniaturas** con `uv run --script "<skill>/scripts/hojas_contacto.py" capturas "<salida>"` y míralas. Cada hoja junta 12 capturas: das el panorama completo con poco contexto.
3. **Abre a tamaño completo solo las capturas que importan:** tablas, documentos, código, errores, chats, nombres de participantes. Cada imagen grande cuesta contexto; con 5 a 10 suele bastar.
4. **Revisa lo que no quedó capturado.** Si el audio se refiere a algo que no tiene captura ("como ven aquí…"), o hay un tramo largo sin capturas, mira cuadros puntuales:
   ```
   uv run --script "<skill>/scripts/hojas_contacto.py" tiempos "<grabación>" --destino "<salida>/_revision" <seg> <seg> ...
   ```
   Un tramo largo sin capturas suele ser una pantalla que no cambió, no un fallo.
5. **Identifica a los participantes:**
   - Con una transcripción importada, los nombres de los hablantes son confiables.
   - Con Whisper no hay hablantes. Deduce nombres solo con evidencia: se llaman por su nombre, aparecen en el mosaico de la videollamada o en el chat.
   - No atribuyas una frase a alguien sin evidencia. Si lo infieres, dilo.

## 5. Minuta

Lee `references/minuta.md` y sigue su estructura. Al redactarla:

- **Cada acuerdo o dato lleva su minuto (`mm:ss`)** y, si existe, el enlace a la captura (`capturas/0012_00-05-30.jpg`). Así quien la lea puede verificarlo en la transcripción ilustrada.
- **Distingue** acuerdo, propuesta, duda abierta e intención. Que alguien mencione una idea no la convierte en acuerdo.
- **Corrige en la minuta los términos mal transcritos** y lístalos al final, para que el lector entienda la transcripción original.
- **Contrasta con documentos relacionados.** Si el usuario menciona análisis, planes o código relacionados con la reunión, revísalos y agrega una sección "Diferencias con documentos" con rutas y líneas. Es de lo más valioso: una reunión suele cambiar decisiones que ya estaban escritas. Separa lo verificado de lo inferido.

Guárdala como `<salida>/minuta.md` y regenera el HTML con la nota final (paso 3).

## 6. Contexto para otra sesión (solo si lo pide)

Sirve cuando el usuario quiere pasarle lo discutido a otra sesión de Claude, por ejemplo la que implementa lo que se acordó. Usa `references/contexto-agente.md`. Escríbelo para un agente, no para una persona: definiciones exactas, rutas de código verificadas y qué cambia respecto a lo que esa sesión ya da por cierto.

Guárdalo como `<salida>/contexto-<tema>.md` y, si lo pide, cópialo al portapapeles:
- **Windows:** `powershell -NoProfile -STA -Command "Set-Clipboard -Value (Get-Content -LiteralPath '<ruta>' -Raw -Encoding UTF8)"`. Sin `-STA` el portapapeles queda vacío sin dar error.
- **macOS:** `pbcopy < "<ruta>"`.
- **Linux:** `xclip -selection clipboard < "<ruta>"` o `wl-copy < "<ruta>"`.

## 7. Entrega

- Lista los archivos con su ruta absoluta.
- Di qué tan confiable es la transcripción: si es automática, si tiene hablantes y qué términos corregiste.
- Menciona que `_revision/` tiene hojas de trabajo y se puede borrar.
- Si no hubo hablantes y el usuario necesita saber quién dijo qué, sugiere exportar la transcripción de la plataforma la próxima vez.
