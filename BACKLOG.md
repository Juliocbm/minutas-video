# Backlog y roadmap

Pendientes del plugin, agrupados por versión. Al terminar uno, se borra de aquí y se anota en el [CHANGELOG](CHANGELOG.md).

## 0.3.1 · Lo que se ve y se comparte

Sale de `minuta.json`, que ya existe desde la 0.3.0.

- **Transcripción ilustrada 2.0.** Reproductor del video: clic en una frase y salta a ese momento. Búsqueda con MiniSearch, filtro por hablante y enlaces `#t=` desde la minuta.
- **Word, PDF, CSV y calendario** generados desde `minuta.json`: pandoc o docxtpl, Edge en modo headless, icalendar (VEVENT) y CSV en `utf-8-sig`.

## 0.4 · Quién dijo qué

- **Separar hablantes.** pyannote.audio con el modelo community-1 en GPU, recibiendo el audio que ya decodifica PyAV. Respaldo en CPU con sherpa-onnx. Cada palabra se asigna a un hablante con las marcas de tiempo por palabra de faster-whisper. Requiere una cuenta de Hugging Face y aceptar las condiciones del modelo; el token va en `userConfig` como dato sensible. El error de hablantes se mide contra el `.vtt` que exporta Teams.
- **Ajustes de calidad de Whisper.** Marcas de tiempo por palabra, `hallucination_silence_threshold` y tramos de baja confianza marcados en el HTML. Solo si las pruebas muestran mejora.
- **Plantillas por tipo de reunión:** general, requisitos con proveedor, seguimiento, daily, retrospectiva, entrevista, capacitación. Cada proyecto puede agregar las suyas.

## 0.5 · Especialistas

- **Agentes:**
  - verificador de la minuta, con lectura independiente de cada acuerdo contra la transcripción;
  - analista visual de todas las capturas;
  - contrastador de documentos;
  - lector por tramos para reuniones de más de ~90 min.
- **Publicar con los conectores del usuario:** Jira, Confluence, GitHub, Notion o Drive, sin duplicar al repetir.
- **Guías paso a paso** a partir de grabaciones de demostraciones.
- **Entregables por audiencia:** resumen ejecutivo y correo de seguimiento.

## 0.6 · Memoria

- **Biblioteca de reuniones** en SQLite FTS5, con una skill `consultar-reuniones` y un panel en HTML.
- **Series:** seguimiento de pendientes entre reuniones de la misma serie.
- **Modo confidencial:** ocultar datos sensibles en las salidas para compartir.

## 1.0

- **Probar en macOS y Linux.** Hasta ahora solo se ha probado en Windows 11 con GPU NVIDIA. En Mac, la vía para transcribir rápido sería mlx-whisper.

## Bajo demanda

Estos esperan una señal concreta para entrar.

- **Calibrar el modo cámara** con grabaciones reales de juntas presenciales. Hoy sus umbrales son una estimación.
- **Perfiles de voz por proyecto**, para sugerir nombres de hablantes en juntas recurrentes. Depende de la 0.4.
- **Recortar la pantalla compartida** en videollamadas. Primero hay que medir cuántas capturas falsas generan las cámaras.
- **Motores de transcripción alternos:** Canary, Parakeet o VibeVoice. Solo si superan a large-v3 en juntas propias.
- **Más formatos de entrada:** el `.docx` que exporta Teams, el Google Doc de Meet y el TIMELINE de Zoom. Hoy ya se importa el `.vtt`; entran con un caso real.
- **Barra en la status line.** Un comando de status line que lea `progreso.json`. Los hitos al 25, 50 y 75 % y `minutas.py seguir` ya cubren el avance.
- **OCR en GPU** (onnxruntime-gpu con las librerías CUDA que ya usa Whisper). Hoy son unos 4 s por captura en CPU, en paralelo con la transcripción; entra si alarga de forma notable el proceso.
- **Orden de lectura del OCR por columnas.** En pantallas con dos columnas (un correo junto a un PDF), las líneas se mezclan.
- **Panel propio en Claude Code (mod).** Solo si la status line y los hitos se quedan cortos.
- **Transcripción en la nube.** Pospuesta: el audio saldría del equipo.
