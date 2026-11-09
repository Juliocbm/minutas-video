---
description: Con solo el .vtt de Teams (sin video), la skill importa la transcripción con hablantes y redacta la minuta completa.
tags: [minuta, vtt]
runs: 1
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash, AskUserQuestion]
---

Hazme la minuta de la junta de ayer. No tengo el video, solo la transcripción que exportó Teams: reunion-demo.vtt. Usa lo de siempre, no hace falta que me preguntes nada.

Input files: reunion-demo.vtt
