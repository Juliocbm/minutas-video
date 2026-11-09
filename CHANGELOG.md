# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

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

[Sin publicar]: https://github.com/Juliocbm/minutas-video/compare/minutas-video--v0.2.0...HEAD
[0.2.0]: https://github.com/Juliocbm/minutas-video/compare/minutas-video--v0.1.0...minutas-video--v0.2.0
[0.1.0]: https://github.com/Juliocbm/minutas-video/releases/tag/minutas-video--v0.1.0
