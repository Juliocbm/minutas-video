# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

## [0.3.1] - 2026-11-09

Ver y compartir: la grabación dentro de la transcripción ilustrada y la minuta en PDF, Word y CSV.

### Añadido
- Transcripción ilustrada:
  - reproductor de la grabación: clic en una frase y salta a ese momento, la frase que suena se resalta y se sigue (hasta que haces scroll a mano), y los enlaces `#t285` de la minuta dejan la grabación en ese minuto. Enlaza la grabación con una ruta relativa, sin copiarla; Chrome y Edge reproducen los `.mkv` de OBS;
  - búsqueda en lo dicho y en el texto de las capturas, sin importar acentos ni mayúsculas, con las palabras resaltadas;
  - filtro por hablante cuando la transcripción los trae.
- `minutas.py exportar <salida> [pdf] [docx] [csv]`, desde `minuta.json` y sin enlaces a archivos locales:
  - `minuta.pdf`, impreso por Edge o Chrome en modo headless;
  - `minuta.docx`, con python-docx;
  - `pendientes.csv`, en UTF-8 con BOM para Excel, con responsable, fecha, minuto y cita de cada pendiente.

### Cambiado
- Las reuniones ya procesadas rehacen solo la transcripción ilustrada (un segundo) al volver a correr el comando.

## [0.3.0] - 2026-11-09

Evidencia: el texto de las pantallas y una minuta cuyas citas se verifican contra la grabación.

### Añadido
- Minuta estructurada: Claude escribe `minuta.json` (participantes, acuerdos, temas con sus puntos, preguntas abiertas, riesgos, pendientes y diferencias con documentos), y cada elemento lleva su evidencia: momento, cita textual y captura.
- `minutas.py minuta <salida>`:
  - valida `minuta.json`;
  - busca cada cita en la transcripción cerca de su momento, o en el texto de la captura citada, con tolerancia a muletillas omitidas, saltos con «…» y términos del glosario;
  - reporta las citas que están en otro minuto, que no son textuales o que no aparecen;
  - genera `minuta.md`, con cada minuto enlazado a la frase exacta de la transcripción ilustrada.
- Texto de las capturas (OCR) con RapidOCR 3.10, en CPU y con el modelo multilingüe PP-OCRv6 que trae el paquete (no descarga modelos). Queda en `ocr.json`. `capturas.txt` muestra, por captura, solo las líneas nuevas: en una reunión real de 35 minutos, el 30 % del texto. Arranca en cuanto terminan las capturas, mientras sigue la transcripción. `--no-ocr` o `ocr = false` lo apagan.
- Pantallas que vuelven: cada captura se compara (SSIM) con las últimas 10 distintas y, si es casi igual a una, queda marcada con `igual_a`. Conserva su imagen, pero las hojas de miniaturas la omiten y el OCR reutiliza el texto.
- Transcripción ilustrada:
  - el texto de cada captura, en un bloque desplegable que encuentra la búsqueda del navegador;
  - las capturas repetidas enlazan a la original;
  - un ancla por frase (`#t285`), que el navegador resalta al llegar.

### Cambiado
- `procesar-reunion` lee primero el texto de las capturas para decidir qué imágenes abrir, escribe `minuta.json` en lugar de `minuta.md` y corrige la minuta hasta que sus citas cuadran.
- Las reuniones procesadas con la 0.2 rehacen capturas, OCR y HTML al volver a correr el comando; la transcripción no se repite.

### Corregido
- Si se cambiaba a `--capturas ninguna`, la transcripción ilustrada seguía mostrando las capturas de la corrida anterior.
- Con muy pocas capturas, el aviso de avance decía «75 %» justo antes de terminar. Ya no se avisa un porcentaje si el paso llegó al 100 %.

## [0.2.0] - 2026-11-09

Cimientos: un proceso que se reanuda, configuración por proyecto, avance visible y pruebas.

### Añadido
- `minutas.py`, que orquesta todo lo mecánico con un solo comando:
  - transcripción (Whisper o importada), capturas, glosario y transcripción ilustrada, con la transcripción y las capturas en paralelo;
  - `reunion.json` por reunión, con lo que se hizo y con qué parámetros: si algo falla o cambia una opción, el mismo comando solo rehace lo necesario (`--solo` y `--forzar` para elegir pasos);
  - varias grabaciones o una carpeta en un solo comando, procesadas una tras otra;
  - `--plan`: qué haría y con qué configuración, en JSON, sin correr nada;
  - `seguir <salida>`: barra de progreso en vivo de un proceso que lanzó Claude.
- Avance visible:
  - en una terminal, barras con porcentaje y tiempo restante;
  - cuando lo lanza Claude, hitos al 25, 50 y 75 % en `_registro/hitos.log`, y Claude los resume en una línea;
  - `progreso.json` con el estado en vivo y bitácora completa de cada paso en `_registro/`.
- Presets: `rapido` (large-v3-turbo, sin capturas, minuta corta), `estandar`, `completo` (revisión de todas las capturas, contraste con documentos y contexto para otra sesión) y `audio`.
- Configuración por capas en TOML, de menor a mayor prioridad: plugin, preset, usuario (`~/.minutas-video/`), proyecto (`.minutas-video/`) y corrida. `minutas.py config` muestra de dónde sale cada valor; los errores detienen el proceso con el archivo y la clave.
- `glosario.toml`, con los términos del proyecto y sus variantes mal escritas. Las variantes se detectan solas, se anota dónde aparecen (`glosario.json`) y la nota de corrección entra sola en el HTML. La transcripción no se modifica.
- `participantes.toml`: nombre, rol, organización y apodos; se buscan sus menciones en la transcripción.
- Skill `configurar` (`/minutas-video:configurar`), que solo corre si la invocas: pregunta las preferencias, propone el glosario desde los documentos del proyecto y registra participantes.
- Plantilla de minuta corta para el preset `rapido`.
- Pruebas automáticas con pytest (importación, configuración, glosario, orquestador y detección de capturas con un video sintético) y tres casos para `claude plugin eval`.

### Cambiado
- `procesar-reunion`:
  - pregunta lo que falta en una sola ventana de opciones y no pregunta lo que ya se sabe;
  - sigue el avance y avisa en cada hito;
  - ajusta la profundidad de la revisión al preset.
- Frontmatter de la skill: disparadores en `when_to_use`, `argument-hint` y los `uv run` preaprobados durante la skill (menos solicitudes de permiso).
- `vocabulario.txt` se sigue leyendo, como glosario sin variantes, con un aviso para pasarlo a `glosario.toml`.

## [0.1.0] - 2026-11-09

### Añadido
- Skill `procesar-reunion`: convierte la grabación de una reunión (video o solo audio) en transcripción, capturas, transcripción ilustrada y minuta.
- `entorno.py`: detecta la GPU NVIDIA y los modelos descargados, y recomienda el dispositivo y el modelo.
- `transcribir.py`: transcripción local con faster-whisper, en GPU (CUDA) o CPU. Elige la pista de audio cuando hay varias.
- `importar_transcripcion.py`: importa `.vtt`/`.srt` con hablantes, ya sea con etiquetas `<v Nombre>` (Teams) o con prefijo `Nombre:` (Zoom).
- `extraer_capturas.py`: capturas por cambio de pantalla, con espera de estabilidad, en los modos `pantalla`, `camara` (experimental) y `ninguna`.
- `hojas_contacto.py`: hojas de 12 miniaturas para revisar muchas capturas con poco contexto.
- `armar_html.py`: transcripción ilustrada con tema claro y oscuro, hablantes en color y opción `--incrustar` para tener un solo archivo.
- Plantillas de minuta y de contexto para otra sesión de Claude, más una guía de solución de problemas.
- Dependencias declaradas dentro de cada script para uv: se instalan solas, en entornos aislados.
- Ejemplo completo con una reunión ficticia en `docs/ejemplo/`.

### Notas
- No se le pasa vocabulario a Whisper. En pruebas, `hotwords` hizo que repitiera la lista de términos, inventara frases en otros idiomas y perdiera la mitad del contenido. El vocabulario del proyecto se usa para corregir términos en la minuta.

[Sin publicar]: https://github.com/Juliocbm/minutas-video/compare/minutas-video--v0.3.1...HEAD
[0.3.1]: https://github.com/Juliocbm/minutas-video/compare/minutas-video--v0.3.0...minutas-video--v0.3.1
[0.3.0]: https://github.com/Juliocbm/minutas-video/compare/minutas-video--v0.2.0...minutas-video--v0.3.0
[0.2.0]: https://github.com/Juliocbm/minutas-video/compare/minutas-video--v0.1.0...minutas-video--v0.2.0
[0.1.0]: https://github.com/Juliocbm/minutas-video/releases/tag/minutas-video--v0.1.0
