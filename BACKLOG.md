# Backlog y roadmap

Pendientes del plugin, agrupados por versión. Al terminar uno, se borra de aquí y se anota en el [CHANGELOG](CHANGELOG.md).

**Regla:** todo cambio que toque la minuta se mide de punta a punta antes de publicarse: la misma reunión real, en una sesión limpia, con la versión publicada y la nueva, calificadas a ciegas contra una lista de hechos, más el tiempo y el costo de cada una. Medir piezas sueltas no basta: así entraron el OCR y la separación de hablantes, que no mejoraron la minuta (ver la 0.5.0 en el CHANGELOG).

## 0.5.x · Seguimiento

- **Plantillas por tipo de reunión:** general, requisitos con proveedor, seguimiento, daily, retrospectiva, entrevista, capacitación. Cada proyecto puede agregar las suyas. En la daily medida, la minuta completa se alargó; una plantilla de daily (persona → ayer, hoy, bloqueos, indicaciones) podría ser más útil.
- **Ajustes de calidad de Whisper.** `hallucination_silence_threshold` y tramos de baja confianza marcados en el HTML. Solo si las pruebas muestran mejora.

## 0.6 · Especialistas

- **Agentes:**
  - verificador de la minuta, con lectura independiente de cada acuerdo contra la transcripción;
  - analista visual de todas las capturas;
  - contrastador de documentos;
  - lector por tramos para reuniones de más de ~90 min.
- **Publicar con los conectores del usuario:** Jira, Confluence, GitHub, Notion o Drive, sin duplicar al repetir.
- **Guías paso a paso** a partir de grabaciones de demostraciones.
- **Entregables por audiencia:** resumen ejecutivo y correo de seguimiento.

## 0.7 · Memoria

- **Biblioteca de reuniones** en SQLite FTS5, con una skill `consultar-reuniones` y un panel en HTML.
- **Series:** seguimiento de pendientes entre reuniones de la misma serie.
- **Modo confidencial:** ocultar datos sensibles en las salidas para compartir.

## 1.0

- **Probar en macOS y Linux.** Hasta ahora solo se ha probado en Windows 11 con GPU NVIDIA. En Mac, la vía para transcribir rápido sería mlx-whisper.

## Bajo demanda

Estos esperan una señal concreta para entrar.

- **Calibrar el modo cámara** con grabaciones reales de juntas presenciales. Hoy sus umbrales son una estimación.
- **Recortar la pantalla compartida** en videollamadas. Primero hay que medir cuántas capturas falsas generan las cámaras.
- **Motores de transcripción alternos:** Canary, Parakeet o VibeVoice. Solo si superan a large-v3 en juntas propias.
- **Más formatos de entrada:** el `.docx` que exporta Teams, el Google Doc de Meet y el TIMELINE de Zoom. Hoy ya se importa el `.vtt`; entran con un caso real.
- **Calendario (.ics)** con los pendientes que tienen fecha y las reuniones de seguimiento. Requiere fechas completas (`2026-11-18`), no «18/11».
- **Más exportaciones:** acuerdos en CSV, resumen ejecutivo o correo de seguimiento (ver 0.6).
- **Barra en la status line.** Un comando de status line que lea `progreso.json`. `minutas.py seguir` ya cubre el avance.
- **Panel propio en Claude Code (mod).** Solo si la status line y `seguir` se quedan cortos.
- **Transcripción en la nube.** Pospuesta: el audio saldría del equipo.
- **Opcionales (`--separar-hablantes`, `--ocr`, minuta verificada):** solo si alguien los usa y una medición de punta a punta muestra que mejoran la minuta.
  - Hablantes palabra por palabra, con las marcas de tiempo por palabra de faster-whisper (hoy cada frase va completa a un hablante).
  - pyannote como opción, si alguien acepta la cuenta de Hugging Face (17.0 % publicado contra 23.1 % de sherpa-onnx).
  - Perfiles de voz por proyecto, para sugerir nombres en juntas recurrentes.
  - OCR en GPU (hoy unos 4-5 s por captura en CPU) y orden de lectura por columnas.
  - Decidir si la minuta verificada se mejora (verificar también atribuciones) o se retira.
