# La minuta: `minuta.json`

La minuta se escribe como datos, no como texto libre: redacta `<salida>/minuta.json` y genera el Markdown con

```
uv run --script <scripts>/minutas.py minuta "<salida>"
```

El comando valida la estructura, busca cada cita en la transcripción (cerca del momento indicado) y en el texto de la captura citada, y escribe `minuta.md`. No edites `minuta.md` a mano: se regenera cada vez.

Guía para quien redacta:
- **Breve y verificable.** Cada acuerdo, punto, pregunta, riesgo y pendiente lleva su evidencia.
- **Distingue** acuerdo, propuesta, duda abierta e intención. Que alguien mencione una idea no la convierte en acuerdo.
- **Valores exactos** en el texto: «27 de noviembre», «30 s», «1 240 envíos». La cita conserva lo que se dijo («veintisiete de noviembre»).
- **Lo inferido se marca:** `"inferido": true`. Incluye a los participantes deducidos sin evidencia directa.
- **Omite lo vacío:** una sección sin elementos no se escribe. "Pendientes" aparece siempre ("Ninguno.").

## Evidencia

Cada elemento lleva `"evidencia": [ ... ]`, con uno o más objetos:

| Campo | Qué va | Ejemplo |
|---|---|---|
| `t` | El momento: el `[hh:mm:ss]` del párrafo en `transcripcion.txt`, o segundos | `"04:45"`, `"01:04:45"`, `285` |
| `cita` | Palabras **textuales** de la transcripción, de 6 a 20. Puede saltar un tramo con «…». Si la cita viene de la pantalla, cópiala de `capturas.txt` e indica la captura | `"lanzamos el veintisiete de noviembre"` |
| `captura` | Número de la captura donde se ve, si aplica | `5` |

- La cita se busca desde 30 s antes hasta 90 s después de `t`: usa el inicio del párrafo donde aparece.
- Copia la cita tal cual, con sus muletillas o sin ellas. Si corriges un término del glosario («Nexus» → «NEXO»), la verificación lo reconoce.
- Sin cita, la evidencia solo enlaza al momento (y a la captura) y no cuenta como verificada.

## Campos

| Campo | Tipo | Notas |
|---|---|---|
| `plantilla` | `"completa"` o `"corta"` | Según `config.efectiva.minuta`. La corta usa solo resumen, acuerdos y pendientes |
| `titulo` | texto | **Obligatorio.** El tema de la reunión |
| `fecha`, `hora`, `lugar` | texto | `"2026-11-12"` (se escribe «12 de noviembre de 2026»), `"10:00"`, `"Teams"`. Si la fecha no se conoce, omítela; no la deduzcas |
| `nota` | texto | Aviso al inicio, si hace falta |
| `objetivo` | texto | Para qué se reunieron, en una o dos líneas |
| `resumen` | texto | Tres a cinco líneas: qué salió. En la corta es lo primero que se lee |
| `participantes` | lista | `nombre` (obligatorio), `rol` (corto: «backend», «dirige la revisión»), `organizacion`, `inferido` |
| `acuerdos` | lista | `texto`, `tema`, `evidencia`, `discusion` (lista de textos: cómo se llegó, si hubo debate), `quien`, `inferido` |
| `temas` | lista | `titulo`, `desde`, `hasta` (tiempos) y `puntos` |
| `temas[].puntos` | lista | `texto`, `tipo` (`punto`, `dato`, `propuesta`, `duda`, `intencion`), `quien`, `evidencia`, `inferido` |
| `preguntas` | lista | Preguntas que quedaron abiertas: `texto`, `quien`, `evidencia` |
| `riesgos` | lista | `texto`, `quien`, `evidencia` |
| `pendientes` | lista | `texto` (acción concreta), `responsable`, `fecha` (si se dijo), `evidencia` |
| `diferencias` | lista | Contra documentos: `documento` (`ruta:línea`), `dice`, `acordado`, `evidencia`, `verificado` (`false` si no se leyó el documento) |
| `terminos` | lista | `forma` (como la escribió la transcripción) y `termino` (el correcto). Los del glosario encontrados se agregan solos |

Los textos admiten Markdown en línea (`**negritas**`, `código`).

## Ejemplo

```json
{
 "plantilla": "completa",
 "titulo": "Revisión de lanzamiento de Mesa Lista",
 "fecha": "2026-11-12", "hora": "10:00", "lugar": "videollamada",
 "objetivo": "revisar la beta y decidir la fecha de lanzamiento.",
 "participantes": [
  {"nombre": "Ana Torres", "rol": "dirige la revisión", "organizacion": "Producto"},
  {"nombre": "Luis Méndez", "rol": "backend", "organizacion": "Desarrollo"}
 ],
 "acuerdos": [
  {"tema": "Lanzamiento",
   "texto": "**27 de noviembre**, si el reintento de SMS está listo el 18. Si no, se mueve una semana.",
   "evidencia": [
    {"t": "04:45", "cita": "Si el reintento de SMS está listo el dieciocho, lanzamos el veintisiete de noviembre", "captura": 5},
    {"t": "05:06", "cita": "Movemos el lanzamiento una semana"}
   ]}
 ],
 "temas": [
  {"titulo": "Métricas de la beta", "desde": "00:58", "hasta": "02:00", "puntos": [
   {"tipo": "dato", "texto": "Las reservas semanales subieron de 120 a 410 en seis semanas.",
    "evidencia": [{"t": "00:58", "cita": "pasamos de ciento veinte a cuatrocientas diez reservas por semana", "captura": 2}]},
   {"tipo": "propuesta", "texto": "Medir el efecto del recordatorio antes de cambiar nada.", "quien": "Sofía",
    "evidencia": [{"t": "01:36", "cita": "Propongo medirlo antes de cambiar nada"}]}
  ]}
 ],
 "pendientes": [
  {"texto": "Reintento de SMS y respaldo por correo", "responsable": "Luis Méndez", "fecha": "18/11",
   "evidencia": [{"t": "03:00", "cita": "reintento y respaldo por correo, Luis, antes del dieciocho"}]}
 ]
}
```

El ejemplo completo, con la minuta que genera, está en `docs/ejemplo/` del repositorio del plugin.

## Lo que reporta el comando

```
minuta.json válida · 4 acuerdos, 2 temas, 4 pendientes
Evidencia: 17 de 19 citas verificadas contra la transcripción y las capturas.
Revisa en minuta.json:
  - acuerdos[2] «27 de noviembre…» · evidencia[0] 00:01:00: la cita está en 00:04:45, no cerca de 00:01:00.
  - pendientes[1] «Medir el efecto…» · evidencia[0] 00:01:36: la cita se parece (72 %) a lo dicho en 00:01:36, pero no es textual: cópiala tal cual de la transcripción.
→ <salida>/minuta.md
```

- **Código 0:** todo cuadra. **Código 1:** hay evidencia que revisar, y `minuta.md` se generó igual. **Código 2:** `minuta.json` no es válida (clave desconocida, campo faltante, tiempo mal escrito) y no se generó nada.
- Corrige lo que reporte y vuelve a correrlo. Si una cita no se puede hacer textual (la idea se dijo en varios momentos), quítala y deja solo `t`, o marca el elemento como inferido.
- El pie de `minuta.md` dice cuántas citas se verificaron: no lo escondas.
