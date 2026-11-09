# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

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

[Sin publicar]: https://github.com/Juliocbm/minutas-video/compare/minutas-video--v0.1.0...HEAD
[0.1.0]: https://github.com/Juliocbm/minutas-video/releases/tag/minutas-video--v0.1.0
