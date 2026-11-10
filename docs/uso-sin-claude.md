# Usar los scripts sin Claude

Las piezas mecánicas funcionan solas desde la terminal: transcripción, capturas, glosario y transcripción ilustrada (y, si los pides, hablantes y texto de las capturas). Solo necesitas [uv](https://docs.astral.sh/uv/getting-started/installation/). Lo que no obtienes sin Claude es la redacción de la minuta, porque esa es la parte de análisis; si la escribes tú en `minuta.json`, el comando `minuta` la verifica y genera el Markdown.

## Todo en un comando

```bash
cd skills/procesar-reunion/scripts

uv run --script minutas.py procesar "reunion.mkv"
```

- Detecta la GPU y elige el modelo; transcribe y extrae capturas en paralelo, con barras de progreso; si los pides, después separa a los hablantes y lee el texto de las capturas, uno a la vez; arma la transcripción ilustrada.
- La salida queda en `reunion_minuta/`, junto a la grabación (`--salida` para otra carpeta).
- Si se interrumpe o cambias una opción, vuelve a correr el mismo comando: solo se rehace lo necesario.
- Acepta varias grabaciones o una carpeta, y las procesa una tras otra. Útil para dejar un lote corriendo y pedirle después a Claude solo las minutas.

Opciones frecuentes:

| Opción | Para qué |
|---|---|
| `--preset rapido` | `rapido`, `estandar`, `completo` o `audio` (ver [configuración](../skills/procesar-reunion/references/configuracion.md)) |
| `--transcripcion "reunion.vtt"` | Importar la transcripción de Teams o Zoom (con nombres) en lugar de Whisper |
| `--idioma auto` | Detectar el idioma (por defecto `es`) |
| `--modelo medium` | Otro modelo de Whisper (`large-v3`, `large-v3-turbo`, `medium`, `small`…) |
| `--pista 1` | Elegir la pista de audio, si la grabación tiene varias |
| `--capturas ninguna` | `pantalla`, `camara` o `ninguna` |
| `--ocr` | Leer el texto de las capturas (unos 4 s por captura, en CPU) |
| `--separar-hablantes` · `--hablantes 4` | Separar quién habla (unos 5 min por media hora de audio, en CPU); cuántas personas, si se sabe |
| `--nota "…"` · `--titulo "…"` · `--incrustar` | Para la transcripción ilustrada |
| `--solo html` · `--forzar transcripcion` | Correr solo algunos pasos, o rehacer uno aunque esté al día |
| `--plan` | Ver en JSON qué haría y con qué configuración, sin correr nada |

Otros comandos:

```bash
uv run --script minutas.py seguir "reunion_minuta"   # barra de progreso de un proceso en curso
uv run --script minutas.py config                     # configuración efectiva y de dónde sale cada valor
uv run --script minutas.py glosario "reunion_minuta"  # vuelve a buscar los términos del glosario
uv run --script minutas.py nombres "reunion_minuta" "Hablante 1=Ana Torres"   # nombre para un hablante
uv run --script minutas.py minuta "reunion_minuta"    # opcional: valida minuta.json, verifica las citas y genera minuta.md
uv run --script minutas.py exportar "reunion_minuta"  # minuta.pdf, minuta.docx y pendientes.csv (o solo los que indiques)
```

## Paso a paso

Cada paso también es un script que se puede correr solo:

```bash
uv run --script entorno.py                                                     # ¿GPU? ¿qué modelo? (no instala nada)
uv run --with nvidia-cublas-cu12 --with "nvidia-cudnn-cu12>=9,<10" --script transcribir.py "reunion.mkv" --salida "reunion_minuta"
uv run --script transcribir.py "reunion.mkv" --salida "reunion_minuta" --modelo medium --dispositivo cpu   # sin GPU
uv run --script importar_transcripcion.py "reunion.vtt" --salida "reunion_minuta"
uv run --script separar_hablantes.py "reunion.mkv" --salida "reunion_minuta" --hablantes 4   # quién habla (CPU)
uv run --script extraer_capturas.py "reunion.mkv" --salida "reunion_minuta" --modo pantalla
uv run --script ocr_capturas.py "reunion_minuta"                               # texto de las capturas
uv run --script armar_html.py "reunion_minuta" --titulo "Revisión semanal"
uv run --script hojas_contacto.py capturas "reunion_minuta"                    # hojas de 12 miniaturas
uv run --script hojas_contacto.py tiempos "reunion.mkv" --destino "reunion_minuta/_revision" 120 340
```

Cada script tiene `--help` con todas sus opciones. La primera ejecución tarda más porque uv descarga Python y las dependencias, y Whisper descarga el modelo. Luego todo queda en caché.
