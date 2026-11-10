# Backlog y roadmap

Pendientes del plugin, agrupados por versión. Al terminar uno, se borra de aquí y se anota en el [CHANGELOG](CHANGELOG.md).

## 0.4 · Quién dijo qué

- **Separar hablantes, sin cuentas por defecto.** El resultado es "Hablante 1, Hablante 2…"; los nombres se siguen deduciendo con evidencia, y el `.vtt` de la plataforma, cuando existe, sigue siendo mejor.
  - **Por defecto, sherpa-onnx:** el modelo de segmentación de pyannote 3.0 convertido (MIT) y un modelo de voces (3D-Speaker, NeMo o WeSpeaker), descargados de GitHub sin registro. Corre en CPU y recibe el audio que ya decodifica PyAV.
  - **Opcional, pyannote community-1:** para quien quiera más precisión. Sus modelos en Hugging Face piden cuenta, aceptar condiciones y token (verificado el 2026-11-09), así que cada usuario lo activa a propósito: el token va en `userConfig` como dato sensible.
  - **Decidir con datos.** Antes de implementar la opción de pyannote, comparar las dos rutas contra el `.vtt` de Teams de una reunión real (error de hablantes y tiempo). Si sherpa-onnx queda cerca, pyannote no entra. Hace falta una grabación con su `.vtt`.
  - Cada palabra se asigna a un hablante con las marcas de tiempo por palabra de faster-whisper.
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
- **Calendario (.ics)** con los pendientes que tienen fecha y las reuniones de seguimiento. Requiere que `minuta.json` registre fechas completas (`2026-11-18`), no «18/11».
- **Más exportaciones:** acuerdos en CSV, resumen ejecutivo o correo de seguimiento (ver 0.5).
- **Barra en la status line.** Un comando de status line que lea `progreso.json`. Los hitos al 25, 50 y 75 % y `minutas.py seguir` ya cubren el avance.
- **OCR en GPU** (onnxruntime-gpu con las librerías CUDA que ya usa Whisper). Hoy son unos 4 s por captura en CPU, en paralelo con la transcripción; entra si alarga de forma notable el proceso.
- **Orden de lectura del OCR por columnas.** En pantallas con dos columnas (un correo junto a un PDF), las líneas se mezclan.
- **Panel propio en Claude Code (mod).** Solo si la status line y los hitos se quedan cortos.
- **Transcripción en la nube.** Pospuesta: el audio saldría del equipo.
