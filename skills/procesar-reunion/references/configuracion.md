# Configuración de minutas-video

Todo es opcional: sin archivos, el plugin usa el preset `estandar` y el modelo que mejor corra en el equipo.

## Dónde va

| Capa | Carpeta | Para qué |
|---|---|---|
| Usuario | `~/.minutas-video/` | Preferencias para todos tus proyectos |
| Proyecto | `<proyecto>/.minutas-video/` | Lo propio de un proyecto: glosario, participantes, preset |

Cada capa sobrescribe a la anterior, y lo que se pida en la corrida (opciones de `minutas.py`) sobrescribe a todas. Un valor fijado en un archivo manda sobre el preset: el preset solo llena lo que nadie fijó. La carpeta del proyecto se busca desde la carpeta actual hacia arriba.

Para ver la configuración efectiva y de dónde sale cada valor:

```
uv run --script <scripts>/minutas.py config
```

Los errores (clave desconocida, valor no válido, TOML roto) aparecen ahí con el archivo y la clave. `minutas.py procesar` no corre con errores de configuración.

## `config.toml`

```toml
preset = "estandar"          # rapido | estandar | completo | audio
idioma = "es"                # es, en, auto…

[transcripcion]
modelo = ""                  # vacío: el del preset o el recomendado para el equipo (large-v3 con GPU, medium sin GPU)
dispositivo = "auto"         # auto | cuda | cpu

[capturas]
modo = ""                    # vacío: el del preset. pantalla | camara | ninguna
max = 200                    # tope de capturas por grabación
ocr = false                  # leer el texto de cada captura (unos 4 s por captura, en CPU)

[hablantes]                  # separación automática, solo cuando transcribe Whisper
separar = false              # quién habla («Hablante 1»…), unos 5 min más por reunión
numero = 0                   # cuántas personas suelen hablar; 0 = no se sabe
```

`hablantes.numero` conviene en el proyecto solo si las reuniones son casi siempre de las mismas personas. En la corrida, `--hablantes N` manda sobre él.

## Presets

| Preset | Transcripción | Hablantes | Capturas | Minuta | Revisión de capturas | Entregables |
|---|---|---|---|---|---|---|
| `rapido` | large-v3-turbo | No | No | Corta | Ligera | Minuta |
| `estandar` | Recomendado para el equipo | No | Pantalla | Completa | Normal | Minuta y transcripción ilustrada |
| `completo` | Recomendado para el equipo | No | Pantalla | Completa | Exhaustiva, y contraste con documentos | Además, contexto para otra sesión |
| `audio` | Recomendado para el equipo | No | No | Completa | — | Minuta y transcripción ilustrada |

"Hablantes" es la separación automática de quién habla, que solo corre cuando transcribe Whisper: una transcripción importada de la plataforma ya trae los nombres. Ningún preset la prende, ni el OCR: medidos contra la 0.1 con reuniones reales, no mejoraron la minuta y sumaban unos 9 minutos. Se prenden con `--separar-hablantes` y `--ocr`, o en `config.toml`.

## `glosario.toml`

Términos del proyecto y las formas en que la transcripción automática los escribe mal. `minutas.py` busca las variantes en la transcripción (sin reescribirla), guarda dónde aparecen en `glosario.json` y agrega la nota de corrección a la transcripción ilustrada.

```toml
[terminos]
NEXO = ["Nexus", "nexo"]
Kubernetes = ["cubernetes", "Cuberneti"]
OKR = []                     # sin variantes conocidas: igual sirve de referencia al redactar
"Mesa Lista" = ["mesalista"] # con espacios, entre comillas
```

- La búsqueda no distingue mayúsculas y respeta palabras completas: «Nexus» no coincide con «Nexusmith».
- Agrega variantes cuando las veas en una minuta: la próxima vez se detectan solas.
- No se le pasa a Whisper: en pruebas, darle vocabulario hizo que repitiera la lista e inventara texto.
- `vocabulario.txt` (un término por línea, formato de la 0.1) se sigue leyendo como términos sin variantes.

## `participantes.toml`

Quiénes suelen estar en las reuniones del proyecto. Sirve para nombrar a los participantes en la minuta y para encontrar sus menciones en la transcripción (por nombre completo, alias o nombre de pila).

```toml
[[persona]]
nombre = "Ana Ruiz"
rol = "Líder técnica"
organizacion = "Plataforma"
alias = ["Anita"]

[[persona]]
nombre = "Luis Méndez"
rol = "Backend"
```

Contiene nombres de personas: si el repositorio es público, agrega `.minutas-video/participantes.toml` a su `.gitignore`.
