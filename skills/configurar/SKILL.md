---
name: configurar
description: Configura minutas-video para el proyecto actual o para todos los proyectos del usuario, con el preset por defecto, el idioma, las capturas, el glosario de términos que la transcripción escribe mal y la lista de participantes.
disable-model-invocation: true
argument-hint: "[proyecto|usuario]"
allowed-tools: Bash(uv run *)
---

# Configurar minutas-video

Deja lista la configuración para que `procesar-reunion` no tenga que preguntar lo mismo cada vez. El formato de cada archivo está en `${CLAUDE_PLUGIN_ROOT}/skills/procesar-reunion/references/configuracion.md`: léelo antes de escribir.

Argumentos de la invocación (puede estar vacío): $ARGUMENTS

## 1. Ver lo que hay

```
uv run --script ${CLAUDE_PLUGIN_ROOT}/skills/procesar-reunion/scripts/minutas.py config
```

Resume en pocas líneas qué está configurado, de dónde sale cada valor y si hay errores.

## 2. Preferencias

Haz una sola ronda con AskUserQuestion (si no está disponible, pregunta en texto):
- **Ámbito**, salvo que venga en los argumentos: "Este proyecto" (`<proyecto>/.minutas-video/`) o "Todos mis proyectos" (`~/.minutas-video/`).
- **Preset por defecto**: los 4 presets, con su descripción. Marca como recomendado el actual.
- **Idioma de las reuniones**: Español, Inglés o Detectar en cada grabación.
- **Capturas**: Pantalla (videollamadas y grabaciones de pantalla), Cámara (juntas presenciales, experimental) o Ninguna.

Escribe solo lo que cambia respecto a los valores del plugin, en `config.toml`. Si el archivo ya existe, conserva lo demás.

## 3. Glosario (solo en el ámbito de proyecto)

1. Propón términos: siglas, nombres de sistemas, clientes y productos que aparecen en el proyecto (`README`, `CLAUDE.md`, `docs/`, nombres de carpetas). Si hay minutas anteriores, su línea final "Términos que la transcripción automática escribe mal" trae variantes reales: inclúyelas.
2. Muestra la lista y pide que la confirme o la corrija en la conversación. No inventes variantes: anota solo las que el usuario conoce o las que ya aparecieron en una minuta.
3. Escribe `glosario.toml`. Si existe `vocabulario.txt` (formato anterior), pasa sus términos al glosario y ofrece borrarlo.

## 4. Participantes (opcional)

Pregunta si quiere registrar a quienes suelen estar en las reuniones (nombre, rol, organización, apodos). Escribe `participantes.toml`. Si el proyecto es un repositorio público, ofrece agregar `.minutas-video/participantes.toml` a su `.gitignore`.

## 5. Verificar

Corre otra vez `minutas.py config`. Si hay errores, corrígelos. Termina con un resumen de lo que quedó y dónde, y recuerda que puede editar los archivos a mano cuando quiera.
