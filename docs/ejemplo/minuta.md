# Minuta · Revisión de lanzamiento de Mesa Lista

> **Ejemplo ficticio.** Proyecto, personas y datos inventados para mostrar lo que produce el plugin. La minuta es la parte que redacta Claude a partir de la transcripción y las capturas.

**Fecha:** 12 de noviembre de 2026, 10:00 (videollamada).
**Fuente:** grabación, transcripción importada con hablantes y capturas ([transcripción ilustrada](transcripcion-ilustrada.html)). Los minutos son del video.

**Participantes**
- Producto: Ana Torres, que dirige la revisión.
- Desarrollo: Luis Méndez (backend).
- Diseño: Sofía Ramírez.

**Objetivo:** revisar la beta y decidir la fecha de lanzamiento de la app de reservas.

---

## Acuerdos

| Tema | Acuerdo | Min. | Captura |
|---|---|---|---|
| Error de SMS | Reintentar el envío una vez a los 30 s; si vuelve a fallar, mandar la confirmación por correo. | 02:42 a 03:10 | [0003](capturas/0003_00-02-08.jpg) |
| Pantalla de reserva | Subir el botón "Confirmar reserva" debajo del selector de personas y dejarlo fijo. Es solo un cambio de interfaz; no toca la API. | 03:40 a 04:28 | [0004](capturas/0004_00-03-25.jpg) |
| Lanzamiento | **27 de noviembre**, condicionado a que el reintento de SMS esté listo el 18. Si no está, se mueve una semana. | 04:45 a 05:26 | [0005](capturas/0005_00-04-45.jpg) |
| Seguimiento | Revisión de estado el 19 de noviembre. | 05:20 a 05:40 | [0005](capturas/0005_00-04-45.jpg) |

## Temas tratados

### Métricas de la beta (00:58 a 02:00)
- Las reservas semanales subieron de 120 a 410 en seis semanas ([0002](capturas/0002_00-00-58.jpg)).
- La cancelación bajó del 15 % al 12 %.
- Ana lo atribuye al recordatorio de un día antes, pero **no se ha medido por separado**. Sofía propuso medirlo antes de cambiar nada; quedó como pendiente de Ana.

### Error en la confirmación por SMS (02:08 a 03:10)
- 38 de 1 240 envíos fallaron en la última semana (3.1 %). El proveedor no responde en 10 s ([0003](capturas/0003_00-02-08.jpg)).
- Impacto según Luis: quien no recibe el SMS cree que no reservó y llama al restaurante.

## Pendientes

| # | Pendiente | Responsable | Fecha |
|---|---|---|---|
| 1 | Reintento de SMS y respaldo por correo | Luis Méndez | 18/11 |
| 2 | Botón de confirmar fijo debajo de "Personas" | Sofía Ramírez | viernes 13/11 |
| 3 | Medir el efecto del recordatorio en la cancelación | Ana Torres | — |
| 4 | Revisión de estado para confirmar el lanzamiento | Todos | 19/11 |
