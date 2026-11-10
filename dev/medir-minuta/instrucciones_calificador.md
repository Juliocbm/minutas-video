# Calificar dos minutas de la misma reunión

Tienes dos minutas, A y B, escritas a partir de la misma grabación ({reunion}). No sabes quién las hizo ni con qué
herramienta, y no importa.

Archivos (en esta carpeta):
- `hechos.md`: lista de hechos que una buena minuta debería recoger, más trampas (afirmaciones incorrectas).
- `transcripcion.txt`: transcripción automática de la reunión; es la fuente de verdad sobre lo que se dijo. Whisper
  deforma nombres de personas y sistemas: no castigues la ortografía de un nombre dudoso, sí los hechos equivocados.
- `capturas/`: las pantallas de la reunión, si las hay. Lo que una minuta saque de la pantalla (nombres completos,
  títulos de documentos, campos de un formulario) verifícalo ahí; si no puedes, márcalo como "no verificable", no
  como inventado.
- `minuta_A.md`, `minuta_B.md`: las minutas.

## Qué hacer

1. Para cada hecho de `hechos.md` (todos los IDs de la lista) y cada minuta: `ok` (lo recoge bien), `parcial`,
   `omitido` o `mal` (lo dice de forma incorrecta). Cita en una línea dónde lo dice la minuta.
2. Trampas (T1, T2…): ¿alguna minuta afirma la trampa como conclusión? (`cae` / `no cae`). Mencionar la confusión
   inicial y luego la corrección NO es caer.
3. Afirmaciones sin respaldo: recorre cada minuta completa y lista lo que afirma y la transcripción no respalda o
   contradice (cifras, acuerdos, responsables, atribuciones de quién dijo qué). Clasifica cada una: `grave` (cambia
   un acuerdo, un responsable o un dato técnico), `menor`, o `no verificable` (pantalla).
4. Atribuciones: ¿cuántas veces cada minuta pone una frase o compromiso en boca de la persona equivocada? Usa solo
   casos que la transcripción permita decidir.
5. Utilidad: en 3-5 líneas, ¿con cuál minuta preferirías trabajar para {proposito}, y por qué? Considera exactitud
   primero, después claridad y facilidad para encontrar los acuerdos y lo que hará cada quien.

## Entrega

Escribe `resultado.json` en esta carpeta:

```json
{"hechos": {"A1": {"A": "ok", "B": "omitido", "nota": "..."}},
 "trampas": {"T1": {"A": "no cae", "B": "no cae"}},
 "sin_respaldo": {"A": [{"texto": "...", "tipo": "grave|menor|no verificable", "por_que": "..."}], "B": []},
 "atribuciones_erroneas": {"A": [], "B": []},
 "utilidad": "..."}
```

y responde con un resumen corto: conteos por minuta (ok / parcial / omitido / mal, trampas, graves, menores,
atribuciones erróneas) y tu preferencia.
