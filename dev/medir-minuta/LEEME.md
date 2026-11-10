# Medir la minuta de punta a punta

Herramientas para comparar la minuta de dos versiones del plugin con la misma reunión real, como pide la regla del
[BACKLOG](../../BACKLOG.md): sesión limpia, calificación a ciegas contra una lista de hechos, más el tiempo y el
costo de cada una. Así se midió la 0.5.0 (ver el [CHANGELOG](../../CHANGELOG.md)).

Solo usan la biblioteca estándar de Python y Claude Code. Cada corrida es una sesión real del modelo: con una reunión
de 35 minutos, unos 15 minutos y 2.5-3.5 USD por versión.

| Archivo | Para qué |
|---|---|
| `correr.py` | Procesa la reunión con cada versión, en sesiones limpias, y anota tiempo y costo |
| `sesion_viva.py` | Una sesión de `claude -p` que no se cierra al primer turno (la usa `correr.py`) |
| `revisar_sesion.py` | Costo por turno, archivos leídos e imágenes que abrió Claude |
| `preparar_calificacion.py` | Sortea las dos minutas como A y B y arma la carpeta del calificador |
| `instrucciones_calificador.md` | Lo que lee el calificador (la reunión y el propósito se llenan solos) |
| `hechos-ejemplo.md` | Cómo se escribe la lista de hechos, con la reunión ficticia |

## Pasos

Todo lo que se genere va en una carpeta **fuera del repositorio**: son reuniones reales. Los scripts se niegan a
escribir dentro.

1. **Las versiones.** Una carpeta con el plugin completo por versión. La publicada sale de su etiqueta:

   ```bash
   git worktree add ../mv-0.5.0 minutas-video--v0.5.0
   ```

2. **La lista de hechos**, antes de ver cualquier minuta: 30-40 hechos y algunas trampas, con el formato de
   [`hechos-ejemplo.md`](hechos-ejemplo.md). Sale de la transcripción; si no la tienes, procesa primero la reunión
   y escribe la lista sin abrir `minuta.md`.

3. **Correr las dos versiones.** La nueva primero (la primera corre con el disco frío):

   ```bash
   python dev/medir-minuta/correr.py --video "D:/reuniones/junta.mp4" --trabajo ../medicion/junta \
       --version nueva=. --version 0.5.0=../mv-0.5.0
   ```

   Al terminar muestra minutos, costo y turnos de cada versión. El equipo debe quedarse encendido, con la tapa
   abierta: el script evita la suspensión por inactividad, pero no la de la tapa.

4. **Revisar cada sesión:**

   ```bash
   python dev/medir-minuta/revisar_sesion.py ../medicion/junta/nueva/run/sesion.jsonl
   ```

   Si una versión cuesta más, aquí se ve en qué turno. Si no abrió imágenes, perdió lo que solo estaba en pantalla.

5. **Calificar a ciegas:**

   ```bash
   python dev/medir-minuta/preparar_calificacion.py \
       --minuta nueva=../medicion/junta/nueva/run/junta_minuta/minuta.md \
       --minuta 0.5.0=../medicion/junta/0.5.0/run/junta_minuta/minuta.md \
       --hechos ../medicion/junta/hechos.md --salida-reunion ../medicion/junta/0.5.0/run/junta_minuta \
       --destino ../medicion/junta/calificar \
       --reunion "la daily de 31 minutos de un equipo de desarrollo" --proposito "darle seguimiento al equipo"
   ```

   En Claude Code, pídele a un subagente que lea `calificar/instrucciones_calificador.md` y haga lo que pide, sin
   decirle qué versión es cuál. Una segunda ronda con otro subagente sirve para ver si los calificadores coinciden.
   La clave queda en `clave-calificar.txt`, fuera de la carpeta del calificador.

6. **Decidir.** Primero la exactitud (errores graves, atribuciones, omisiones), después el tiempo y el costo. Una
   versión que no gana en exactitud no justifica tardar o costar más.

## Por qué así

- **`claude -p` normal no sirve:** termina en cuanto Claude responde y mata los procesos en segundo plano, como la
  transcripción. `sesion_viva.py` deja la entrada abierta para que la sesión reciba el aviso de que terminó.
- **Se desactiva el plugin instalado** mientras corre: si no, la sesión ve dos versiones de la skill.
- **La ruta completa del video:** con solo el nombre, la sesión lo buscó en el disco y tomó otro archivo.
- **Medir la minuta final, no las piezas:** el OCR y la separación de hablantes mejoraban su parte medida por
  separado, y la minuta no mejoró.
