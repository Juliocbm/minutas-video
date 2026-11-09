# Plantilla: contexto para otra sesión de Claude

Sirve cuando el usuario quiere pegarle lo discutido en la reunión a otra sesión de Claude, normalmente la que implementa lo que se habló.

Ese lector es un agente:
- Ya tiene su propio contexto: un análisis, un plan, código.
- Necesita saber qué cambia, con precisión, y poder verificarlo.
- No necesita la crónica de la reunión.

**Antes de escribir:**
- **Verifica en el código o en los documentos** cada nombre de campo, tabla o ruta que menciones. Un nombre inventado le hace más daño que ayuda.
- **Separa lo dicho de lo inferido.** Lo dicho en la reunión lleva su minuto. Lo verificado lleva ruta y línea. Lo que tú deduces se marca como inferencia.
- **Busca contradicciones.** Si el usuario mencionó documentos de esa sesión (análisis, plan, historia de usuario), contrástalos con lo acordado. Las contradicciones son lo más valioso del paquete.
- **No pongas datos reales que inviten a una acción irreversible.** Si un ejemplo lleva un folio o un identificador, usa uno ilustrativo; el real podría terminar en una prueba contra un sistema productivo.

---

```markdown
# Contexto: <reunión> (<fecha>)

Para la sesión que <qué hace esa sesión>.
- **Fuente:** <grabación de qué, duración>. Evidencia en `<ruta a la carpeta de salida>` (`minuta.md`, `transcripcion-ilustrada.html`, `transcripcion.srt`, `capturas/`). Los tiempos (mm:ss) son del video.
- **Participantes:** <nombres y rol de cada uno: quién decide qué>.

## 1. Conclusiones: qué cambia
1. **<Cambio>:** <definición exacta>. <Minuto o cita breve que lo respalda>.

## 2. Definiciones acordadas
<Tabla de valores, reglas o contratos acordados, con su fundamento.>

## 3. Hallazgos
- <Verificado en código: `ruta/archivo.ext:línea`>.
- <Ambigüedades o riesgos que quedaron y cómo confirmarlos>.
- <Inferencias, marcadas como tales>.

## 4. Diferencias con los documentos de esa sesión
| Documento | Dice | Debe decir |
|---|---|---|

Sin cambios, porque la reunión lo confirma: <lista breve>.

## 5. Pendientes externos
| # | Pendiente | Responsable |
|---|---|---|
```

Cierra recordando que los cambios a sus documentos los decide el usuario. La otra sesión no debe reescribirlos por su cuenta.
