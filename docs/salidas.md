# Formato de las salidas

Todo queda en una carpeta, por defecto `<carpeta de la grabación>/<nombre>_minuta/`. En [`ejemplo/`](ejemplo/) hay una completa, generada a partir de una reunión ficticia. Todo lo genera `minutas.py`, salvo la minuta y el contexto, que los redacta Claude.

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
    { "n": 12, "archivo": "capturas/0012_00-03-40.jpg", "t": 220.0, "desde": 215.0, "motivo": "estable", "cambio": 0.075 }
  ]
}
```

- `desde` es el momento en que empezó el cambio. `t` es el momento en que se tomó la captura, ya con la pantalla estable. El HTML asigna a cada captura lo que se dijo desde su `desde` hasta el `desde` de la siguiente.
- `motivo` vale `inicio`, `estable` o `forzada` (la pantalla no se estabilizó y se capturó igual).
- `cambio` es la fracción de la imagen que cambió respecto a la captura anterior.
- `truncado: true` indica que se alcanzó el tope de `--max`.

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

`nota` aparece sola en la transcripción ilustrada.

## `reunion.json`

El manifiesto de la reunión: con qué se procesó y qué pasos están hechos. Permite reanudar sin repetir trabajo.

```json
{
  "plugin": "0.2.0",
  "entrada": { "tipo": "video", "ruta": "C:\\Grabaciones\\revision.mkv", "tamano": 734003200, "modificado": 1762380191000000000 },
  "preset": "estandar",
  "config": { "preset": "estandar", "idioma": "es", "transcripcion": { "modelo": "large-v3" }, "capturas": { "modo": "pantalla" } },
  "opciones": { "nota": "Transcripción automática sin corregir." },
  "pasos": {
    "transcripcion": { "estado": "completo", "firma": "38160791be3c8d27", "duracion_s": 181.4, "resumen": "804 segmentos · 00:34:39 de audio" },
    "capturas": { "estado": "completo", "firma": "…", "duracion_s": 94.0, "resumen": "58 capturas" },
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
- Con capturas: cada sección pone la imagen a la izquierda y lo dicho a la derecha, con una barra de tiempos para saltar.
- Sin capturas: solo la transcripción.
- Necesita la carpeta `capturas/` al lado, salvo que se genere con `--incrustar`.

## `minuta.md` y `contexto-<tema>.md`

Los redacta Claude con las plantillas de `skills/procesar-reunion/references/`. Ver el [ejemplo de minuta](ejemplo/minuta.md).
