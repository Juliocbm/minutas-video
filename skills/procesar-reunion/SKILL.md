---
name: procesar-reunion
description: Convierte la grabación de una reunión, junta, videollamada o conversación (video o solo audio) en transcripción con tiempos, capturas de lo que se mostraba con su texto, transcripción ilustrada en HTML y una minuta con acuerdos y pendientes, cada uno con su cita verificada contra la grabación; opcionalmente, un resumen de contexto para otra sesión de Claude. Transcribe en local con Whisper (GPU opcional) y los requisitos se instalan solos con uv.
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
| `capturas.txt` · `ocr.json` | Texto de cada captura (OCR). `capturas.txt` trae solo lo nuevo de cada una | `minutas.py` |
| `glosario.json` | Dónde aparecen mal escritos los términos del glosario y quién es mencionado | `minutas.py` |
| `transcripcion-ilustrada.html` | Cada captura junto a lo que se dijo mientras estuvo visible | `minutas.py` |
| `reunion.json` · `progreso.json` · `_registro/` | Registro de cada paso, avance y bitácoras | `minutas.py` |
| `minuta.json` | Acuerdos, temas y pendientes, cada uno con su evidencia (minuto, cita y captura) | Tú |
| `minuta.md` | La minuta para leer, con enlaces al momento exacto | `minutas.py minuta`, desde `minuta.json` |
| `contexto-<tema>.md` | Paquete de contexto para otra sesión de Claude | Tú, si se pide |

`minutas.py` hace todo lo mecánico y recuerda lo que ya hizo: si algo falla o cambia una opción, el mismo comando solo rehace lo necesario. Tu trabajo es acordar lo mínimo, lanzar el proceso, informar el avance, revisar y redactar.

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

- Lánzalo **en segundo plano** y espera la notificación de que terminó. Transcribe y extrae capturas en paralelo, y lee el texto de las capturas en cuanto terminan (unos 4 s por captura). Nunca lances dos procesos con transcripción a la vez, porque agotan la memoria.
- Con varias grabaciones, pásalas todas en un solo comando (o una carpeta): se procesan una tras otra.
- **Avance:** si tienes la herramienta Monitor, sigue `<salida>/_registro/hitos.log` (por ejemplo `tail -n +1 -F "<salida>/_registro/hitos.log"`). Cuando llegue un hito (`▸` 25, 50 y 75 %, `✓` paso terminado, `✗` error), escribe una línea corta al usuario: "Transcripción al 50 %, faltan ~2 min". No comentes otras líneas.
- Dile también que puede ver una barra de progreso en vivo en su propia terminal con `uv run --script "<ruta absoluta de minutas.py>" seguir "<salida>"`.
- Mientras corre, si el usuario mencionó documentos relacionados, léelos ya: los necesitarás en el paso 6.
- Al terminar, la última línea es `LISTO` o `TERMINÓ CON ERRORES`. Si hubo un error, lee `<salida>/_registro/<paso>.log` y `references/solucion-problemas.md`, corrige y vuelve a correr el mismo comando: lo que ya terminó no se repite.
- Si el proceso tardó más de unos 5 minutos y tienes la herramienta PushNotification, manda un aviso corto: "Transcripción lista: <nombre>".
- Si se espera que tarde mucho (CPU con una grabación larga), sugiere correr el mismo comando en su terminal, donde verá las barras, y avisarte al terminar.

Como referencia, en una laptop con GPU NVIDIA, 35 minutos de video tardan unos 3 minutos en transcribirse, y las capturas se extraen en paralelo. La primera vez tarda más: uv descarga las dependencias (unos 1.5 GB más si hay GPU) y Whisper descarga el modelo (unos 3 GB para large-v3).

## 5. Revisar

Aquí está el valor: cruzar lo que se dijo con lo que se veía. Ajusta la profundidad a `config.efectiva.revision`.

1. **Lee `transcripcion.txt` completo.** Si es larga, léela por tramos y toma notas. Identifica temas, decisiones, dudas y términos mal escritos.
2. **Lee `glosario.json`** si existe: qué variantes mal escritas aparecieron, con su minuto, y las menciones de cada participante. Úsalo para corregir términos y para saber quién estaba y con qué rol (`config.participantes`).
3. **Capturas** (si hay):
   - **Lee primero `capturas.txt`**: el texto de cada pantalla, solo lo nuevo respecto a la anterior. Te dice qué se mostró sin abrir imágenes, cuáles conviene abrir y los valores exactos para citar. El OCR puede confundir caracteres: confirma en la imagen los datos críticos (montos, folios, fechas). Si es muy largo, búscale los términos de la reunión en lugar de leerlo entero.
   - `ligera`: abre imágenes solo si el texto se refiere a algo que se ve ("como ven aquí…").
   - `normal`: genera las hojas de miniaturas con `uv run --script ${CLAUDE_SKILL_DIR}/scripts/hojas_contacto.py capturas "<salida>"` y míralas; abre a tamaño completo solo las que importan (tablas, documentos, código, errores, chats, nombres de participantes). Con 5 a 10 suele bastar. Las hojas omiten las capturas que repiten una pantalla anterior.
   - `exhaustiva`: todas las hojas, y a tamaño completo cada captura con texto o datos relevantes.
4. **Revisa lo que no quedó capturado.** Si el audio se refiere a algo sin captura, o hay un tramo largo sin capturas, mira cuadros puntuales:
   ```
   uv run --script ${CLAUDE_SKILL_DIR}/scripts/hojas_contacto.py tiempos "<grabación>" --destino "<salida>/_revision" <seg> <seg> ...
   ```
   Un tramo largo sin capturas suele ser una pantalla que no cambió, no un fallo.
5. **Identifica a los participantes:**
   - Con una transcripción importada, los nombres de los hablantes son confiables.
   - Con Whisper no hay hablantes. Deduce nombres solo con evidencia: se llaman por su nombre, aparecen en el mosaico de la videollamada o en el chat.
   - No atribuyas una frase a alguien sin evidencia. Si lo infieres, dilo.

## 6. Minuta

Lee `references/minuta.md` y escribe **`<salida>/minuta.json`**, no `minuta.md`. Usa `"plantilla": "completa"` o `"corta"` según `config.efectiva.minuta`. Al redactarla:

- **Cada acuerdo, punto, pregunta, riesgo y pendiente lleva evidencia:** el momento (`t`, el `[hh:mm:ss]` del párrafo), una **cita textual** copiada de la transcripción (o de `capturas.txt`, si está en pantalla) y la captura, si se ve. Así cualquiera puede comprobarlo, y el comando lo verifica.
- **Distingue** acuerdo, propuesta, duda abierta e intención (`tipo` de cada punto). Que alguien mencione una idea no la convierte en acuerdo.
- **Corrige los términos mal transcritos** en el texto y anótalos en `terminos` (los del glosario se agregan solos).
- **Contrasta con documentos relacionados.** Si el usuario mencionó análisis, planes o código relacionados con la reunión (o el preset es `completo`), revísalos y llena `diferencias` con rutas y líneas. Es de lo más valioso: una reunión suele cambiar decisiones que ya estaban escritas. Lo que no leíste lleva `"verificado": false`.

Después genera la minuta:

```
uv run --script ${CLAUDE_SKILL_DIR}/scripts/minutas.py minuta "<salida>"
```

Valida `minuta.json`, busca cada cita cerca de su momento (y en el texto de la captura citada) y escribe `minuta.md` con enlaces a la frase exacta de la transcripción ilustrada. Si reporta problemas (cita en otro minuto, cita que no es textual, captura que no corresponde), corrige `minuta.json` y vuélvelo a correr hasta que no queden. No edites `minuta.md` a mano: se regenera.

Si hay algo que el lector del HTML deba saber además de lo que ya pone el glosario (que se agrega solo), regenera la transcripción ilustrada con una nota. Tarda un segundo:

```
uv run --script ${CLAUDE_SKILL_DIR}/scripts/minutas.py procesar "<grabación>" --solo html --nota "<aviso para el lector>"
```

## 7. Contexto para otra sesión (si `entregables` lo incluye o el usuario lo pide)

Sirve para pasarle lo discutido a otra sesión de Claude, por ejemplo la que implementa lo acordado. Usa `references/contexto-agente.md`. Escríbelo para un agente, no para una persona: definiciones exactas, rutas de código verificadas y qué cambia respecto a lo que esa sesión ya da por cierto.

Guárdalo como `<salida>/contexto-<tema>.md` y, si lo pide, cópialo al portapapeles:
- **Windows:** `powershell -NoProfile -STA -Command "Set-Clipboard -Value (Get-Content -LiteralPath '<ruta>' -Raw -Encoding UTF8)"`. Sin `-STA` el portapapeles queda vacío sin dar error.
- **macOS:** `pbcopy < "<ruta>"`.
- **Linux:** `xclip -selection clipboard < "<ruta>"` o `wl-copy < "<ruta>"`.

## 8. Entrega

- Lista los archivos con su ruta absoluta.
- Di qué tan confiable es la transcripción: si es automática, si tiene hablantes y qué términos corregiste. Di cuántas citas se verificaron (la línea "Evidencia" del comando `minuta`).
- Menciona que `_revision/` y `_registro/` son de trabajo y se pueden borrar.
- Si corregiste términos que no estaban en el glosario, ofrece guardarlos en `.minutas-video/glosario.toml` del proyecto (formato en `references/configuracion.md`) para que la próxima vez se detecten solos. Para configurar todo con calma: `/minutas-video:configurar`.
- Si no hubo hablantes y el usuario necesita saber quién dijo qué, sugiere exportar la transcripción de la plataforma la próxima vez.
