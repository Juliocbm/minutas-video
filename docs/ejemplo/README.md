# Ejemplo: reunión ficticia

Una reunión inventada, "Revisión de lanzamiento de Mesa Lista", con todas las salidas del plugin. Ninguna persona ni dato es real.

| Archivo | Qué es |
|---|---|
| `reunion-demo.vtt` | La entrada: transcripción con hablantes, en el formato que exporta Teams |
| `transcripcion.txt` · `.srt` · `.json` | La transcripción procesada |
| `capturas/` · `capturas.json` | Las cinco "pantallas" de la reunión |
| `capturas.txt` · `ocr.json` | El texto de cada pantalla, leído por OCR |
| `transcripcion-ilustrada.html` | Descárgalo junto con `capturas/` y ábrelo en el navegador; GitHub solo muestra su código |
| [`minuta.json`](minuta.json) | Lo que redacta Claude a partir de todo lo anterior: cada acuerdo y pendiente con su momento, su cita y su captura |
| [`minuta.md`](minuta.md) | La minuta que genera `minutas.py minuta` tras verificar las citas (aquí, 20 de 20) |

No hay video: las pantallas y el diálogo los genera [`dev/generar_demo.py`](../../dev/generar_demo.py). Para regenerar todo desde la raíz del repo:

```bash
uv run --script dev/generar_demo.py
uv run --script skills/procesar-reunion/scripts/importar_transcripcion.py docs/ejemplo/reunion-demo.vtt --salida docs/ejemplo
uv run --script skills/procesar-reunion/scripts/ocr_capturas.py docs/ejemplo
uv run --script skills/procesar-reunion/scripts/armar_html.py docs/ejemplo --titulo "Revisión de lanzamiento · Mesa Lista" --nota "Demostración con datos ficticios: transcripción importada de un .vtt con hablantes y pantallas generadas por dev/generar_demo.py."
uv run --script skills/procesar-reunion/scripts/minutas.py minuta docs/ejemplo
```
