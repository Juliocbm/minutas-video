# Minuta · Revisión de lanzamiento de Mesa Lista

> **Ejemplo ficticio.** Proyecto, personas y datos inventados para mostrar lo que produce el plugin. Claude redacta minuta.json a partir de la transcripción y las capturas; minuta.md se genera de ahí con `minutas.py minuta`.

**Fecha:** 12 de noviembre de 2026, 10:00 · videollamada.  
**Fuente:** grabación, transcripción importada con hablantes y capturas ([transcripción ilustrada](transcripcion-ilustrada.html)). Los minutos son de la grabación.

**Participantes**
- Producto: Ana Torres (dirige la revisión).
- Desarrollo: Luis Méndez (backend).
- Diseño: Sofía Ramírez.

**Objetivo:** revisar la beta y decidir la fecha de lanzamiento de la app de reservas.

---

## Acuerdos

| Tema | Acuerdo | Min. | Captura |
|---|---|---|---|
| Error de SMS | Reintentar el envío una vez a los 30 s; si vuelve a fallar, mandar la confirmación por correo. | [02:42](transcripcion-ilustrada.html#t162), [03:00](transcripcion-ilustrada.html#t180) | [0003](capturas/0003_00-02-08.jpg) |
| Pantalla de reserva | Subir el botón "Confirmar reserva" debajo del selector de personas y dejarlo fijo. Es solo un cambio de interfaz; no toca la API. | [03:25](transcripcion-ilustrada.html#t205), [03:55](transcripcion-ilustrada.html#t235) | [0004](capturas/0004_00-03-25.jpg) |
| Lanzamiento | **27 de noviembre**, condicionado a que el reintento de SMS esté listo el 18. Si no está, se mueve una semana. | [04:45](transcripcion-ilustrada.html#t285), [05:06](transcripcion-ilustrada.html#t306) | [0005](capturas/0005_00-04-45.jpg) |
| Seguimiento | Revisión de estado el 19 de noviembre. | [05:20](transcripcion-ilustrada.html#t320), [05:30](transcripcion-ilustrada.html#t330) | — |

**Lanzamiento.** Cómo se llegó al acuerdo:
- Luis preguntó qué pasaría si el reintento no estaba listo; Ana prefirió mover la fecha antes que lanzar con clientes sin confirmación.

## Temas tratados

### Métricas de la beta (00:58 a 02:00)
- Las reservas semanales subieron de 120 a 410 en seis semanas ([00:58](transcripcion-ilustrada.html#t58) · [0002](capturas/0002_00-00-58.jpg)).
- La cancelación bajó del 15 % al 12 % ([01:22](transcripcion-ilustrada.html#t82)).
- **Duda abierta:** Se atribuye la baja al recordatorio de un día antes, pero **no se ha medido por separado** — Ana ([01:22](transcripcion-ilustrada.html#t82)).
- **Propuesta:** Medirlo antes de cambiar nada; quedó como pendiente de Ana — Sofía ([01:36](transcripcion-ilustrada.html#t96)).

### Error en la confirmación por SMS (02:08 a 03:10)
- 38 de 1 240 envíos fallaron en la última semana (3.1 %): el proveedor no responde en 10 s ([02:08](transcripcion-ilustrada.html#t128) · [0003](capturas/0003_00-02-08.jpg)).
- Impacto: quien no recibe el SMS cree que no reservó y llama al restaurante — Luis ([02:08](transcripcion-ilustrada.html#t128)).

## Pendientes

| # | Pendiente | Responsable | Fecha | Min. |
|---|---|---|---|---|
| 1 | Reintento de SMS y respaldo por correo | Luis Méndez | 18/11 | [03:00](transcripcion-ilustrada.html#t180) |
| 2 | Botón de confirmar fijo debajo de "Personas" | Sofía Ramírez | viernes 13/11 | [04:08](transcripcion-ilustrada.html#t248), [04:20](transcripcion-ilustrada.html#t260) |
| 3 | Medir el efecto del recordatorio en la cancelación | Ana Torres | — | [01:50](transcripcion-ilustrada.html#t110) |
| 4 | Revisión de estado para confirmar el lanzamiento | Todos | 19/11 | [05:30](transcripcion-ilustrada.html#t330) |

---

*Evidencia: 20 de 20 citas coinciden con la transcripción o con el texto de la captura.*
