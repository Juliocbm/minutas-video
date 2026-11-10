---
name: procesar-reunion
description: Convierte la grabación de una reunión, junta, videollamada o conversación (video o solo audio) en transcripción con tiempos, capturas de lo que se mostraba, transcripción ilustrada en HTML y una minuta con acuerdos y pendientes, cada uno con su minuto; opcionalmente, un resumen de contexto para otra sesión de Claude. Transcribe en local con Whisper (GPU opcional) y los requisitos se instalan solos con uv.
when_to_use: Úsala siempre que el usuario quiera transcribir o sacar el texto de un video o audio, saber qué se dijo o se acordó en una junta (grabada o con su transcripción exportada de Teams, Zoom o Meet), hacer la minuta o el resumen de una reunión, o comparta la ruta de una grabación (mp4, mkv, mov, webm, m4a, mp3, wav) o de una transcripción de reunión (.vtt, .srt), aunque no diga "minuta" ni "transcripción" y aunque pida algo rápido. Con la skill, cada acuerdo queda con su minuto y los archivos quedan guardados para verificar.
argument-hint: "[grabación] [--preset rapido|estandar|completo|audio]"
allowed-tools: Bash(uv run *) Bash(uv --version)
---

# Procesar reunión

Convierte una grabación en archivos que se pueden leer, buscar y compartir. Todo queda en una carpeta, por defecto `<carpeta de la grabación>/<nombre>_minuta/`:

| Archivo | Qué es | Lo genera |
|---|---|---|
| `transcripcion.txt` · `.srt` · `.json` | Texto con `[hh:mm:ss]` y hablante cuando se conoce | `minutas.py` |
| `capturas/` + `capturas.json` | Una imagen cada vez que cambia lo que se ve; las que repiten una pantalla anterior quedan marcadas | `minutas.py` |
| `glosario.json` | Dónde aparecen mal escritos los términos del glosario y quién es mencionado | `minutas.py` |
| `transcripcion-ilustrada.html` | Cada captura junto a lo que se dijo mientras estuvo visible, con búsqueda y un reproductor: clic en una frase para escucharla | `minutas.py` |
| `reunion.json` · `progreso.json` · `_registro/` | Registro de cada paso, avance y bitácoras | `minutas.py` |
| `minuta.md` | Acuerdos, temas y pendientes, cada uno con su minuto enlazado a la transcripción ilustrada | Tú |
| `minuta.pdf` · `minuta.docx` · `pendientes.csv` | La minuta para compartir y los pendientes para Excel o Jira | `minutas.py exportar`, si se pide |
| `contexto-<tema>.md` | Paquete de contexto para otra sesión de Claude | Tú, si se pide |
| `hablantes.json` · `capturas.txt` · `ocr.json` | Solo si se pidieron: quién habla (`--separar-hablantes`) y el texto de las capturas (`--ocr`) | `minutas.py` |

`minutas.py` hace todo lo mecánico y recuerda lo que ya hizo: si algo falla o cambia una opción, el mismo comando solo rehace lo necesario. Tu trabajo es acordar lo mínimo, lanzar el proceso, esperar, revisar y redactar.

Los scripts están en `${CLAUDE_SKILL_DIR}/scripts/`. Pon siempre entre comillas las rutas del usuario: los nombres de las grabaciones suelen tener espacios.

Argumentos de la invocación (puede estar vacío): $ARGUMENTS

## 1. Entorno

Corre los comandos de esta skill con la herramienta Bash, no con PowerShell: así coinciden con los permisos que la skill trae preaprobados.

1. Busca uv con `uv --version`. Si no aparece (en Windows, la sesión puede tener un PATH anterior a la instalación), búscalo con un solo comando y usa la ruta que salga en lugar de `uv`:
   ```
   ls "$LOCALAPPDATA"/Microsoft/WinGet/Links/uv.exe "$LOCALAPPDATA"/Microsoft/WinGet/Packages/astral-sh.uv_*/uv.exe "$USERPROFILE"/.local/bin/uv.exe ~/.local/bin/uv ~/.cargo/bin/uv 2>/dev/null
   ```
2. Si no está instalado, pide permiso e instálalo:
   - Windows: `winget install --id astral-sh.uv -e`. Si no hay winget: `python -m pip install --user uv`.
   - macOS y Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

## 2. Plan

```
uv run --script ${CLAUDE_SKILL_DIR}/scripts/minutas.py procesar "<grabación>" --plan [opciones que ya conozcas]
```

No corre nada: devuelve un JSON con lo que haría.
- `config.efectiva`: preset, idioma, modelo, capturas, tipo de minuta (`minuta`), nivel de revisión (`revision`) y `entregables`. `config.origen` dice de dónde salió cada valor: `plugin`, `preset …`, `equipo`, `usuario`, `proyecto` o `corrida`.
- `config.errores`: si hay, muéstralos y corrígelos con el usuario antes de seguir (el archivo y la clave vienen en el mensaje).
- `config.glosario` y `config.participantes`: términos y personas configurados para el proyecto.
- `entradas[0].transcripcion_sugerida`: un `.vtt` o `.srt` con el mismo nombre que la grabación.
- `entradas[0].procesada_antes` y `acciones`: qué ya está hecho (`al_dia`) y qué se correría y por qué.
- `equipo.avisos`: por ejemplo, que el modelo se descargará la primera vez.

## 3. Acordar lo mínimo

No preguntes lo que ya se sabe: lo que el usuario dijo ("rápido", "solo el audio"), lo que vino en los argumentos y lo que fija la configuración (`origen` = `usuario`, `proyecto` o `corrida`).

Si queda algo por decidir, haz **una sola** ronda con la herramienta AskUserQuestion (hasta 4 preguntas), solo con las que apliquen:
- **Preset**, si nadie lo fijó. Opciones: los 4 de `config.presets`, con su descripción. Recomendado: `estandar` para video, `audio` para audio.
- **Transcripción de la plataforma**, si hay `transcripcion_sugerida`: "Usar el archivo de la plataforma (trae los nombres de quien habla)", recomendado, o "Transcribir con Whisper".
- **Entregables**, con selección múltiple, solo si el usuario insinuó algo distinto al preset: minuta, transcripción ilustrada, contexto para otra sesión.
- **Idioma**, solo si hay indicios de que la reunión no es en el idioma configurado.

Si nada falta, no preguntes: di en una línea qué vas a hacer ("Preset estándar: large-v3 en GPU, con capturas de pantalla") y sigue. Si AskUserQuestion no está disponible (sesión no interactiva), usa los valores del plan y dilo.

Por qué importa la transcripción de la plataforma: la plataforma recibe el audio de cada participante por separado y sabe con certeza quién dijo cada frase. Whisper recibe el audio mezclado y no distingue voces.

La primera vez que apliques esta skill en una conversación, menciona la privacidad:
- La transcripción y las capturas se generan en la máquina.
- El texto y las capturas que revises en el paso 5 sí pasan por el modelo.
- La carpeta de salida contiene el contenido de la reunión: no debe quedar dentro de un repositorio público.

## 4. Procesar

```
uv run --script ${CLAUDE_SKILL_DIR}/scripts/minutas.py procesar "<grabación>" [--preset <preset>] [--transcripcion "<archivo.vtt>"] [--idioma auto] [--pista N] [--salida "<carpeta>"]
```

- Lánzalo **en segundo plano** y espera la notificación de que terminó. Transcribe y extrae las capturas a la vez. Nunca lances dos procesos con transcripción a la vez, porque agotan la memoria.
- La separación de hablantes (`--separar-hablantes`) y el texto de las capturas (`--ocr`) vienen apagados: medidos con reuniones reales, no mejoraron la minuta y suman unos 9 minutos. Úsalos solo si el usuario los pide.
- Con varias grabaciones, pásalas todas en un solo comando (o una carpeta): se procesan una tras otra.
- **No sigas el avance** (ni con Monitor ni leyendo `progreso.json` o las bitácoras): cada aviso despierta la sesión y gasta tokens sin cambiar nada. Espera solo la notificación de que terminó.
- Dile al usuario que puede ver una barra de progreso en vivo en su propia terminal con `uv run --script "<ruta absoluta de minutas.py>" seguir "<salida>"`.
- Mientras corre, si el usuario mencionó documentos relacionados, léelos ya: los necesitarás en el paso 6.
- Al terminar, la última línea es `LISTO` o `TERMINÓ CON ERRORES`. Si hubo un error, lee `<salida>/_registro/<paso>.log` y `references/solucion-problemas.md`, corrige y vuelve a correr el mismo comando: lo que ya terminó no se repite.
- Si el proceso tardó más de unos 5 minutos y tienes la herramienta PushNotification, manda un aviso corto: "Transcripción lista: <nombre>".
- Si se espera que tarde mucho (CPU con una grabación larga), sugiere correr el mismo comando en su terminal, donde verá las barras, y avisarte al terminar.

Como referencia, en una laptop con GPU NVIDIA, 35 minutos de video tardan unos 5 minutos en procesarse, con las capturas en paralelo. La primera vez tarda más: uv descarga las dependencias (unos 1.5 GB más si hay GPU) y Whisper descarga el modelo (unos 3 GB para large-v3).

## 5. Revisar

Aquí está el valor: cruzar lo que se dijo con lo que se veía. Ajusta la profundidad a `config.efectiva.revision`.

1. **Lee `transcripcion.txt` completo.** Si es larga, léela por tramos y toma notas. Identifica temas, decisiones, dudas y términos mal escritos.
2. **Lee `glosario.json`** si existe: qué variantes mal escritas aparecieron, con su minuto, y las menciones de cada participante. Úsalo para corregir términos y para saber quién estaba y con qué rol (`config.participantes`).
3. **Capturas** (si hay):
   - `ligera`: solo si el texto se refiere a algo que se ve ("como ven aquí…").
   - `normal`: genera las hojas de miniaturas con `uv run --script ${CLAUDE_SKILL_DIR}/scripts/hojas_contacto.py capturas "<salida>"` y míralas; abre a tamaño completo solo las que importan (tablas, documentos, código, errores, chats, nombres de participantes). Con 5 a 10 suele bastar. Las hojas omiten las capturas que repiten una pantalla anterior.
   - `exhaustiva`: todas las hojas, y a tamaño completo cada captura con texto o datos relevantes.
   - Si existe `capturas.txt` (se pidió `--ocr`), úsalo para copiar valores exactos o buscar un término, **no en lugar de mirar las hojas**: el texto no dice quién habla en la videollamada, qué está resaltado ni cómo se organiza la pantalla.
4. **Revisa lo que no quedó capturado.** Si el audio se refiere a algo sin captura, o hay un tramo largo sin capturas, mira cuadros puntuales:
   ```
   uv run --script ${CLAUDE_SKILL_DIR}/scripts/hojas_contacto.py tiempos "<grabación>" --destino "<salida>/_revision" <seg> <seg> ...
   ```
   Un tramo largo sin capturas suele ser una pantalla que no cambió, no un fallo.
5. **Identifica a los participantes:**
   - Con una transcripción importada, los nombres de los hablantes son confiables.
   - Con Whisper no hay hablantes. Deduce nombres solo con evidencia: se llaman por su nombre, aparecen en el mosaico de la videollamada o en el chat, o la videollamada resalta a quien habla.
   - Si se pidió `--separar-hablantes`, la transcripción trae «Hablante 1», «Hablante 2»…: puede juntar dos voces parecidas o partir a una persona en dos. Ponles nombre solo con evidencia: `uv run --script ${CLAUDE_SKILL_DIR}/scripts/minutas.py nombres "<salida>" "Hablante 1=Ana Torres"`.
   - No atribuyas una frase a alguien sin evidencia. Si lo infieres, dilo.

## 6. Minuta

Lee `references/minuta.md`. Usa la plantilla **completa** o la **corta** según `config.efectiva.minuta`. Al redactarla:

- **Cada acuerdo o dato lleva su minuto**, enlazado a la frase de la transcripción ilustrada (`[05:30](transcripcion-ilustrada.html#t330)`: los segundos del `[hh:mm:ss]` del párrafo) y, si existe, el enlace a la captura (`capturas/0012_00-05-30.jpg`). Así quien la lea puede verificarlo.
- **Distingue** acuerdo, propuesta, duda abierta e intención. Que alguien mencione una idea no la convierte en acuerdo.
- **Corrige los términos mal transcritos** y lístalos al final, para que el lector entienda la transcripción original.
- **Contrasta con documentos relacionados.** Si el usuario mencionó análisis, planes o código relacionados con la reunión (o el preset es `completo`), revísalos y agrega una sección "Diferencias con documentos" con rutas y líneas. Es de lo más valioso: una reunión suele cambiar decisiones que ya estaban escritas. Separa lo verificado de lo inferido.

Guárdala como `<salida>/minuta.md`. Después, si hay algo que el lector del HTML deba saber además de lo que ya pone el glosario (que se agrega solo), regenera la transcripción ilustrada con una nota. Tarda un segundo:

```
uv run --script ${CLAUDE_SKILL_DIR}/scripts/minutas.py procesar "<grabación>" --solo html --nota "<aviso para el lector>"
```

**Para compartir** (si el usuario pide la minuta en PDF o Word, o los pendientes en Excel o para Jira):

```
uv run --script ${CLAUDE_SKILL_DIR}/scripts/minutas.py exportar "<salida>" [pdf] [docx] [csv]
```

Sin formatos genera los tres desde `minuta.md`: `minuta.pdf` (lo imprime Edge o Chrome), `minuta.docx` y `pendientes.csv` (la tabla de pendientes, en UTF-8 con BOM: abre bien en Excel). Los documentos no enlazan a archivos locales: los minutos van como texto.

## 7. Contexto para otra sesión (si `entregables` lo incluye o el usuario lo pide)

Sirve para pasarle lo discutido a otra sesión de Claude, por ejemplo la que implementa lo acordado. Usa `references/contexto-agente.md`. Escríbelo para un agente, no para una persona: definiciones exactas, rutas de código verificadas y qué cambia respecto a lo que esa sesión ya da por cierto.

Guárdalo como `<salida>/contexto-<tema>.md` y, si lo pide, cópialo al portapapeles:
- **Windows:** `powershell -NoProfile -STA -Command "Set-Clipboard -Value (Get-Content -LiteralPath '<ruta>' -Raw -Encoding UTF8)"`. Sin `-STA` el portapapeles queda vacío sin dar error.
- **macOS:** `pbcopy < "<ruta>"`.
- **Linux:** `xclip -selection clipboard < "<ruta>"` o `wl-copy < "<ruta>"`.

## 8. Entrega

- Lista los archivos con su ruta absoluta. Menciona que en la transcripción ilustrada se puede buscar y, si hay grabación, hacer clic en una frase para escucharla (enlaza la grabación: si se mueve, el reproductor avisa).
- Si no los pidió, ofrece en una línea exportar la minuta a PDF, Word o CSV de pendientes.
- Di qué tan confiable es la transcripción: si es automática, si tiene hablantes y qué términos corregiste.
- Menciona que `_revision/` y `_registro/` son de trabajo y se pueden borrar.
- Si corregiste términos que no estaban en el glosario, ofrece guardarlos en `.minutas-video/glosario.toml` del proyecto (formato en `references/configuracion.md`) para que la próxima vez se detecten solos. Para configurar todo con calma: `/minutas-video:configurar`.
- Si no hubo hablantes y el usuario necesita saber quién dijo qué, sugiere exportar la transcripción de la plataforma la próxima vez (Teams, Zoom y Meet la generan con nombres). Si se usó `--separar-hablantes`, di qué nombres asignaste y con qué evidencia.
