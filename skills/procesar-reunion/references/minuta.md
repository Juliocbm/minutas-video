# Plantillas de minuta

Hay dos: la **completa** (presets `estandar`, `completo` y `audio`) y la **corta** (preset `rapido`), al final.

Guía para quien redacta (no se copia a la minuta):
- **Breve y verificable:** cada acuerdo o dato lleva su minuto y, si existe, su captura. El minuto enlaza a la frase de la transcripción ilustrada: `[05:30](transcripcion-ilustrada.html#t330)`, con los segundos del `[hh:mm:ss]` del párrafo (5 × 60 + 30). Sin transcripción ilustrada (preset `rapido`), el minuto va sin enlace.
- **Ajusta las secciones a la reunión.** Si los acuerdos son valores de parámetros, campos o reglas, la tabla funciona mejor. Si son decisiones de otro tipo, usa viñetas por tema.
- **Omite las secciones vacías,** salvo "Pendientes": escribe "Ninguno" si no hubo.
- **Lo inferido se marca como inferido.**

---

```markdown
# Minuta · <tema de la reunión>

**Fecha:** <fecha>, <hora aproximada> (<plataforma o lugar>).
**Fuente:** grabación, transcripción automática y capturas ([transcripción ilustrada](transcripcion-ilustrada.html)). Los minutos son del video.

**Participantes**
- <equipo u organización>: <nombre> (<rol, si se sabe>), <nombre>…
- <otro equipo>: …

**Objetivo:** <para qué se reunieron, en una o dos líneas>.

---

## Acuerdos

| Tema | Acuerdo | Min. | Captura |
|---|---|---|---|
| <tema> | <qué se decidió, con valores exactos> | [mm:ss](transcripcion-ilustrada.html#t<seg>) | [0012](capturas/0012_00-05-30.jpg) |

<Si un acuerdo tuvo discusión o cambió durante la reunión, explica en dos o tres viñetas cómo se llegó a él.>

## Temas tratados

### <Tema> (mm:ss a mm:ss)
- <punto, con quién lo planteó si se sabe> ([mm:ss](transcripcion-ilustrada.html#t<seg>))
- <duda abierta o propuesta, marcada como tal>

## Pendientes

| # | Pendiente | Responsable | Fecha |
|---|---|---|---|
| 1 | <acción concreta> | <persona o equipo> | <si se dijo> |

## Diferencias con documentos

<Solo si se contrastó con análisis, planes o código.>

| Documento | Dice | La reunión acordó |
|---|---|---|
| `ruta/archivo.md:56` | <lo escrito> | <lo nuevo> |

---

*Términos que la transcripción automática escribe mal: «X» es Y, «Z» es W.*
```

## Minuta corta

Para el preset `rapido`: quien la pidió quiere lo esencial en menos de una pantalla. Mismas reglas de evidencia (minuto en cada acuerdo, lo inferido marcado), sin temas tratados ni diferencias con documentos.

```markdown
# Minuta · <tema de la reunión>

**Fecha:** <fecha> (<plataforma o lugar>). **Participantes:** <nombres, si se saben>.

**En resumen:** <tres a cinco líneas: para qué se reunieron y qué salió>.

## Acuerdos
- <acuerdo, con valores exactos> (mm:ss)

## Pendientes
- <acción concreta> · <responsable> · <fecha, si se dijo>

*Transcripción automática; términos corregidos: «X» es Y.*
```
