# Formato de las salidas

Todo queda en una carpeta, por defecto `<carpeta de la grabación>/<nombre>_minuta/`. En [`ejemplo/`](ejemplo/) hay una completa, generada a partir de una reunión ficticia.

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

## `transcripcion-ilustrada.html`

- Un solo archivo con tema claro y oscuro automático.
- Con capturas: cada sección pone la imagen a la izquierda y lo dicho a la derecha, con una barra de tiempos para saltar.
- Sin capturas: solo la transcripción.
- Necesita la carpeta `capturas/` al lado, salvo que se genere con `--incrustar`.

## `minuta.md` y `contexto-<tema>.md`

Los redacta Claude con las plantillas de `skills/procesar-reunion/references/`. Ver el [ejemplo de minuta](ejemplo/minuta.md).
