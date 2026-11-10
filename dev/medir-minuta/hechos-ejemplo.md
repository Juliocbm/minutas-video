# Lista de hechos · Revisión de lanzamiento de Mesa Lista (ejemplo)

Ejemplo con la reunión ficticia de [`docs/ejemplo/`](../../docs/ejemplo/). Una lista real tiene de 30 a 40 hechos
para una reunión de 30-35 minutos.

Cómo se hace:
- Se saca SOLO de la transcripción (y de las pantallas), ANTES de ver las minutas: si no, la lista se parece a la
  minuta que leíste primero.
- Un hecho es algo que una buena minuta debe recoger: acuerdos con su responsable y fecha, cifras, decisiones,
  condiciones, quién dijo qué cuando importa.
- Anota los matices (lo que no fue firme, lo que se corrigió) y las atribuciones: ahí fallan las minutas.
- Las trampas son errores tentadores: la confusión inicial que luego se corrigió, una cifra parecida, la persona
  equivocada. Afirmarlas como conclusión es un error.

## A. Contexto y participantes
- A1. Es la revisión de lanzamiento de Mesa Lista, una app de reservas.
- A2. Participan Ana Torres (modera y decide), Luis Méndez y Sofía Ramírez.

## B. Métricas de la beta
- B1. En seis semanas de beta, las reservas pasaron de 120 a 410 por semana.
- B2. La cancelación bajó de más del 15 % a 12 %.
- B3. (matiz) Se cree que ayudó el recordatorio de un día antes, pero no se ha medido por separado.
- B4. Pendiente de Ana: medir el efecto del recordatorio antes de cambiar nada (lo propuso Sofía).

## C. Error de los SMS
- C1. Fallaron 38 de 1,240 envíos (3 %): el proveedor no responde en 10 segundos.
- C2. Quien no recibe el SMS cree que no reservó y llama al restaurante.
- C3. Acuerdo: reintentar una vez a los 30 segundos y, si vuelve a fallar, confirmar por correo.
- C4. Responsable: Luis, antes del 18.

## D. Pantalla de reserva
- D1. En teléfonos chicos el botón de confirmar queda debajo del pliegue.
- D2. Se sube justo debajo del selector de personas y queda fijo; es solo de interfaz, no toca la API (lo dice Luis).
- D3. Responsable: Sofía, para el viernes.

## E. Lanzamiento
- E1. El 27 de noviembre, si el reintento de SMS está listo el 18.
- E2. Si no está listo, el lanzamiento se mueve una semana.
- E3. Revisión del estado el 19 (lo propone Sofía).

## Trampas (afirmarlas es un ERROR)
- T1. El lanzamiento es el 18 (esa es la fecha del reintento).
- T2. El reintento es a los 10 segundos (10 s es lo que tarda el proveedor sin responder).
- T3. Atribuir a Luis el cambio del botón o a Sofía el reintento de SMS.
