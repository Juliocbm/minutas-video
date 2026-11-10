# Formato de las salidas

Todo queda en una carpeta, por defecto `<carpeta de la grabación>/<nombre>_minuta/`. En [`ejemplo/`](ejemplo/) hay una completa, generada a partir de una reunión ficticia. Todo lo genera `minutas.py`, salvo `minuta.json` y el contexto, que los redacta Claude.

## `transcripcion.json`

Formato intermedio. Lo producen tanto `transcribir.py` como `importar_transcripcion.py`, y de él se derivan el `.txt`, el `.srt` y el HTML.

```json
{
  "meta": {
    "fuente": "whisper",
    "archivo": "C:\\Grabaciones\\revision.mkv",
    "duracion": 2079.4,
    "modelo": "large-v3",
    "dispositivo": "cuda",
    "idioma": "es",
    "pista": 0,
    "pistas_disponibles": 1,
    "generado": "2026-11-09T14:31:05",
    "hablantes": [],
    "segmentos": 804
  },
  "segmentos": [
    { "inicio": 3.1, "fin": 9.4, "texto": "Buenos días…", "hablante": null }
  ]
}
```

- `fuente` vale `whisper` o `importada`. Con `importada` no aparecen `modelo`, `dispositivo`, `idioma` ni `pista`.
- `hablante` es `null` con Whisper. Con una transcripción importada trae el nombre que venía en el archivo.
- Los tiempos están en segundos desde el inicio de la grabación.

## `transcripcion.txt`

Junta los segmentos consecutivos del mismo hablante en párrafos. Corta cuando hay una pausa de más de 1.5 s o el párrafo pasa de unas 60 palabras.

```
[00:00:03] Ana Torres: Buenos días. Gracias por conectarse; …
[00:00:19] Luis Méndez: Perfecto. Yo traigo los números…
```

Sin hablantes, cada línea empieza solo con el tiempo.

## `transcripcion.srt`

Un subtítulo por segmento, con el prefijo `Nombre:` cuando hay hablante. Se puede abrir junto al video en VLC o en cualquier reproductor.

## `capturas.json` y `capturas/`

```json
{
  "meta": { "modo": "pantalla", "umbral_cambio": 0.04, "umbral_estable": 0.01, "duracion": 2079.4, "truncado": false },
  "capturas": [
    { "n": 12, "archivo": "capturas/0012_00-03-40.jpg", "t": 220.0, "desde": 215.0, "motivo": "estable", "cambio": 0.075 },
    { "n": 15, "archivo": "capturas/0015_00-04-30.jpg", "t": 270.0, "desde": 268.0, "motivo": "estable", "cambio": 0.31, "igual_a": 12 }
  ]
}
```

- `desde` es el momento en que empezó el cambio. `t` es el momento en que se tomó la captura, ya con la pantalla estable. El HTML asigna a cada captura lo que se dijo desde su `desde` hasta el `desde` de la siguiente.
- `motivo` vale `inicio`, `estable` o `forzada` (la pantalla no se estabilizó y se capturó igual).
- `cambio` es la fracción de la imagen que cambió respecto a la captura anterior.
- `truncado: true` indica que se alcanzó el tope de `--max`.
- `igual_a` aparece cuando la pantalla volvió a una de las últimas 10 capturas distintas (similitud estructural de 0.97 o más). La imagen se guarda igual, pero las hojas de miniaturas la omiten y el OCR reutiliza el texto de la original.

## `ocr.json` y `capturas.txt`

El texto de cada captura, leído con RapidOCR (modelo PP-OCRv6 multilingüe, en CPU). Se omite con `--no-ocr`.

```json
{
  "meta": { "motor": "RapidOCR 3.10.0 (PP-OCRv6, CPU)", "idioma": "es", "capturas": 58, "segundos": 262.4 },
  "capturas": [
    { "n": 12, "archivo": "capturas/0012_00-03-40.jpg", "desde": 215.0, "lineas": ["Request", "Campo", "Tipo", "…"], "confianza": 0.974 },
    { "n": 15, "archivo": "capturas/0015_00-04-30.jpg", "desde": 268.0, "igual_a": 12, "lineas": ["…"], "confianza": 0.974 }
  ]
}
```

- Las líneas van de arriba abajo. En pantallas con varias columnas, el orden puede mezclarlas.
- Se quitan las líneas sin al menos dos letras o dígitos (íconos, viñetas) y, si la reunión no es en chino, japonés o coreano, los caracteres de esos alfabetos que el modelo a veces confunde con íconos.
- Si una captura no se pudo leer, trae `error` en lugar de `lineas`.

`capturas.txt` es la versión para leer: por captura, solo las líneas que no estaban en la anterior. En una reunión real de 35 minutos, eso dejó 1 553 de 5 152 líneas.

```
[00:03:35] captura 0012 · capturas/0012_00-03-40.jpg · 100 líneas, 35 nuevas
Request
…

[00:04:28] captura 0015 · igual a la captura 0012
```

## `glosario.json`

Solo existe si el proyecto o el usuario tienen `glosario.toml` o `participantes.toml`. La transcripción no se modifica: aquí se anota dónde aparece cada cosa.

```json
{
  "terminos": [
    { "termino": "NEXO", "veces_bien_escrito": 3,
      "variantes": [ { "forma": "Nexus", "veces": 12, "ejemplos": [ { "t": 65.2, "texto": "…lo que nos mandó Nexus ayer…" } ] } ] }
  ],
  "personas": [
    { "nombre": "Ana Ruiz", "rol": "Líder técnica", "organizacion": "", "menciones": 4, "ejemplos": [ { "t": 12.0, "forma": "Anita", "texto": "…" } ] }
  ],
  "nota": "Términos que la transcripción automática escribe mal: «Nexus» es NEXO."
}
```

`nota` aparece sola en la transcripción ilustrada. `minutas.py minuta` usa las variantes encontradas para reconocer una cita que dice «NEXO» donde la transcripción dice «Nexus».

## `reunion.json`

El manifiesto de la reunión: con qué se procesó y qué pasos están hechos. Permite reanudar sin repetir trabajo.

```json
{
  "plugin": "0.3.0",
  "entrada": { "tipo": "video", "ruta": "C:\\Grabaciones\\revision.mkv", "tamano": 734003200, "modificado": 1762380191000000000 },
  "preset": "estandar",
  "config": { "preset": "estandar", "idioma": "es", "transcripcion": { "modelo": "large-v3" }, "capturas": { "modo": "pantalla" } },
  "opciones": { "nota": "Transcripción automática sin corregir." },
  "pasos": {
    "transcripcion": { "estado": "completo", "firma": "38160791be3c8d27", "duracion_s": 181.4, "resumen": "804 segmentos · 00:34:39 de audio" },
    "capturas": { "estado": "completo", "firma": "…", "duracion_s": 94.0, "resumen": "58 capturas (3 repiten una pantalla anterior)" },
    "ocr": { "estado": "completo", "firma": "…", "duracion_s": 262.4, "resumen": "58 de 58 capturas con texto" },
    "html": { "estado": "completo", "firma": "…" }
  }
}
```

- `estado` vale `completo`, `error`, `en_curso` o `interrumpido`.
- `opciones` guarda lo que se pasó por la línea de comandos: se reaplica en las siguientes corridas de esa reunión.

## `progreso.json` y `_registro/`

- `progreso.json` tiene el avance en vivo: estado general y, por paso, `pct`, `restante_s`, `fase` y `detalle`. Lo lee `minutas.py seguir` y sirve para cualquier otra vista de progreso.
- `_registro/hitos.log` tiene las líneas importantes con hora: inicio, 25, 50 y 75 %, fin o error de cada paso. Es lo que Claude sigue mientras procesa.
- `_registro/<paso>.log` es la salida completa de cada script, con el comando que se corrió. Ahí está el detalle de un error.

## `transcripcion-ilustrada.html`

- Un solo archivo con tema claro y oscuro automático.
- Arriba, una barra para buscar en lo dicho y en el texto de las capturas (todas las palabras, sin importar acentos ni mayúsculas; Enter y Mayús+Enter recorren los resultados) y, si hay varios hablantes, un filtro por hablante.
- Con grabación, un reproductor fijo: clic en una frase y la grabación salta a ese momento; la frase que suena se resalta y se sigue hasta que haces scroll a mano. La grabación se enlaza con una ruta relativa, no se copia. Los enlaces `#t285` de la minuta también la dejan en ese momento.
- Con capturas: cada sección pone la imagen a la izquierda y lo dicho a la derecha, con una barra de tiempos para saltar. Bajo el tiempo de cada sección, el texto de la captura en un bloque desplegable: la búsqueda del navegador (Ctrl+F) lo encuentra. Las capturas repetidas enlazan a la original.
- Sin capturas: solo la transcripción.
- Cada frase lleva su segundo (`data-t`) y un ancla (`#t285`): `minuta.md` enlaza ahí y el navegador la resalta.
- Necesita la carpeta `capturas/` al lado, salvo que se genere con `--incrustar`.

## `minuta.json` y `minuta.md`

Claude redacta `minuta.json`, la fuente única de la minuta: participantes, acuerdos, temas con sus puntos, preguntas abiertas, riesgos, pendientes y diferencias con documentos. Cada elemento lleva su evidencia: el momento, la cita textual y, si aplica, la captura.

```json
{
  "plantilla": "completa",
  "titulo": "Revisión de lanzamiento",
  "acuerdos": [
    { "tema": "Lanzamiento", "texto": "27 de noviembre, si el reintento de SMS está listo el 18.",
      "evidencia": [ { "t": "04:45", "cita": "lanzamos el veintisiete de noviembre", "captura": 5 } ] }
  ],
  "pendientes": [
    { "texto": "Reintento de SMS", "responsable": "Luis", "fecha": "18/11",
      "evidencia": [ { "t": "03:00", "cita": "reintento y respaldo por correo, Luis, antes del dieciocho" } ] }
  ]
}
```

`minutas.py minuta <salida>` la valida, busca cada cita en la transcripción (de 30 s antes a 90 s después del momento) y en el texto de la captura citada, y genera `minuta.md`. Reporta las citas que no cuadran (en otro minuto, reescritas, inexistentes) y el pie de la minuta dice cuántas se verificaron. El formato completo está en [references/minuta.md](../skills/procesar-reunion/references/minuta.md). Ver el [ejemplo](ejemplo/minuta.json) y [su minuta](ejemplo/minuta.md).

## `minuta.pdf`, `minuta.docx` y `pendientes.csv`

Los genera `minutas.py exportar <salida> [pdf] [docx] [csv]` desde `minuta.json`, solo si se piden. Tienen el contenido de `minuta.md` sin enlaces a archivos locales: quien los recibe no tiene la transcripción ilustrada, así que los minutos y las capturas van como texto.

- `minuta.pdf`: tamaño carta, impreso por Edge o Chrome en modo headless.
- `minuta.docx`: con estilos de Word (título, encabezados, tablas con cuadrícula), editable.
- `pendientes.csv`: UTF-8 con BOM y comas, una fila por pendiente con `#`, `Pendiente`, `Responsable`, `Fecha`, `Minuto`, `Cita` e `Inferido`.

## `contexto-<tema>.md`

Lo redacta Claude con la plantilla `skills/procesar-reunion/references/contexto-agente.md`.
