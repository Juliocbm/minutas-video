# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10.1"]
# ///
"""Genera la reunión ficticia de docs/ejemplo/ (pantallas, .vtt con hablantes y capturas.json).

Todo es inventado: el proyecto "Mesa Lista", las personas y los datos. Sirve para mostrar el
resultado del plugin sin publicar ninguna reunión real.

Uso (desde la raíz del repo):
  uv run --script dev/generar_demo.py
  uv run --script skills/procesar-reunion/scripts/importar_transcripcion.py docs/ejemplo/reunion-demo.vtt --salida docs/ejemplo
  uv run --script skills/procesar-reunion/scripts/armar_html.py docs/ejemplo --titulo "..." --nota "..."
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "docs" / "ejemplo"
W, H = 1920, 1080
FUENTES = Path("C:/Windows/Fonts")


def fuente(tam, tipo="normal"):
    archivo = {"normal": "segoeui.ttf", "negrita": "segoeuib.ttf", "semi": "seguisb.ttf", "mono": "consola.ttf"}[tipo]
    try:
        return ImageFont.truetype(str(FUENTES / archivo), tam)
    except OSError:
        return ImageFont.load_default(size=tam)


def lienzo(fondo="#f8fafc"):
    img = Image.new("RGB", (W, H), fondo)
    return img, ImageDraw.Draw(img)


def encabezado(d, titulo, subtitulo=None, color="#0f172a"):
    d.rectangle([0, 0, W, 12], fill="#0d9488")
    d.text((120, 110), titulo, font=fuente(76, "negrita"), fill=color)
    if subtitulo:
        d.text((124, 205), subtitulo, font=fuente(38), fill="#64748b")


def pie(d, texto="Equipo Mesa Lista · noviembre 2026"):
    d.text((120, H - 80), texto, font=fuente(26), fill="#94a3b8")


def pantalla_agenda():
    img, d = lienzo()
    encabezado(d, "Revisión de lanzamiento", "Mesa Lista · app de reservas para restaurantes")
    puntos = ["Métricas de la beta", "Error en la confirmación por SMS",
              "Diseño de la pantalla de reserva", "Fecha de lanzamiento"]
    for i, p in enumerate(puntos):
        y = 360 + i * 130
        d.ellipse([124, y, 196, y + 72], fill="#0d9488")
        d.text((160, y + 36), str(i + 1), font=fuente(40, "negrita"), fill="white", anchor="mm")
        d.text((236, y + 8), p, font=fuente(50, "semi"), fill="#1e293b")
    pie(d)
    return img


def pantalla_metricas():
    img, d = lienzo()
    encabezado(d, "Reservas por semana (beta)")
    valores = [120, 165, 210, 268, 342, 410]
    base, alto_max, x0 = 900, 520, 160
    d.line([x0 - 20, base, 1180, base], fill="#cbd5e1", width=3)
    for i, v in enumerate(valores):
        x = x0 + i * 170
        h = v / max(valores) * alto_max
        d.rounded_rectangle([x, base - h, x + 110, base], radius=10, fill="#14b8a6" if i < 5 else "#0f766e")
        d.text((x + 55, base - h - 40), str(v), font=fuente(34, "semi"), fill="#0f172a", anchor="mm")
        d.text((x + 55, base + 36), f"S{i + 1}", font=fuente(30), fill="#64748b", anchor="mm")
    d.rounded_rectangle([1300, 330, 1800, 620], radius=24, fill="white", outline="#e2e8f0", width=3)
    d.text((1340, 360), "Cancelación", font=fuente(36), fill="#64748b")
    d.text((1340, 420), "12 %", font=fuente(110, "negrita"), fill="#0f172a")
    d.text((1340, 560), "antes: 15 %", font=fuente(32), fill="#16a34a")
    pie(d)
    return img


def pantalla_logs():
    img, d = lienzo("#0b1220")
    d.rectangle([0, 0, W, 70], fill="#1e293b")
    for i, c in enumerate(["#f87171", "#fbbf24", "#4ade80"]):
        d.ellipse([30 + i * 40, 22, 56 + i * 40, 48], fill=c)
    d.text((170, 18), "logs · servicio-notificaciones", font=fuente(30), fill="#cbd5e1")
    lineas = [
        ("09:14:02  POST /api/reservas/8812/confirmar   200  sms enviado", "#94a3b8"),
        ("09:14:05  POST /api/reservas/8813/confirmar   500", "#94a3b8"),
        ("          SmsTimeoutError: el proveedor no respondió en 10 s", "#f87171"),
        ("09:15:41  POST /api/reservas/8814/confirmar   200  sms enviado", "#94a3b8"),
        ("09:17:09  POST /api/reservas/8815/confirmar   500", "#94a3b8"),
        ("          SmsTimeoutError: el proveedor no respondió en 10 s", "#f87171"),
        ("09:17:33  POST /api/reservas/8816/confirmar   200  sms enviado", "#94a3b8"),
    ]
    for i, (texto, color) in enumerate(lineas):
        d.text((70, 130 + i * 62), texto, font=fuente(34, "mono"), fill=color)
    d.rounded_rectangle([70, 640, 1300, 860], radius=18, fill="#3b0d0d", outline="#7f1d1d", width=3)
    d.text((110, 670), "Últimos 7 días", font=fuente(36), fill="#fca5a5")
    d.text((110, 730), "38 fallos de 1 240 envíos (3.1 %)", font=fuente(60, "negrita"), fill="#fee2e2")
    return img


def pantalla_diseno():
    img, d = lienzo()
    encabezado(d, "Pantalla de reserva")
    tx, ty, tw, th = 200, 270, 420, 780
    d.rounded_rectangle([tx, ty, tx + tw, ty + th + 60], radius=48, fill="#0f172a")
    d.rectangle([tx + 18, ty + 30, tx + tw - 18, ty + th], fill="white")
    d.text((tx + 50, ty + 70), "Nueva reserva", font=fuente(40, "negrita"), fill="#0f172a")
    for i, (etq, val) in enumerate([("Fecha", "sáb 14 nov"), ("Hora", "20:30"), ("Personas", "4")]):
        y = ty + 160 + i * 150
        d.text((tx + 50, y), etq, font=fuente(28), fill="#64748b")
        d.rounded_rectangle([tx + 50, y + 42, tx + tw - 50, y + 112], radius=14, outline="#cbd5e1", width=3)
        d.text((tx + 72, y + 54), val, font=fuente(34), fill="#0f172a")
    d.rounded_rectangle([tx + 50, ty + th - 40, tx + tw - 50, ty + th + 40], radius=16, fill="#0d9488")
    d.text((tx + tw / 2, ty + th), "Confirmar reserva", font=fuente(32, "semi"), fill="white", anchor="mm")
    d.rectangle([tx, ty + th, tx + tw, ty + th + 60], fill="#0f172a")  # el borde corta el botón
    d.line([tx - 40, ty + th, tx + tw + 40, ty + th], fill="#ef4444", width=4)
    d.text((tx + tw + 50, ty + th - 22), "pliegue", font=fuente(30, "semi"), fill="#ef4444")
    d.rounded_rectangle([900, 360, 1780, 640], radius=24, fill="#fef2f2", outline="#fecaca", width=3)
    d.text((950, 395), "Problema", font=fuente(36, "negrita"), fill="#b91c1c")
    d.text((950, 455), "En teléfonos de 5.5\" el botón queda", font=fuente(38), fill="#1e293b")
    d.text((950, 510), "debajo del pliegue y no se ve.", font=fuente(38), fill="#1e293b")
    d.rounded_rectangle([900, 690, 1780, 930], radius=24, fill="#f0fdfa", outline="#99f6e4", width=3)
    d.text((950, 725), "Propuesta", font=fuente(36, "negrita"), fill="#0f766e")
    d.text((950, 785), "Subirlo debajo de «Personas»", font=fuente(38), fill="#1e293b")
    d.text((950, 840), "y dejarlo fijo al hacer scroll.", font=fuente(38), fill="#1e293b")
    return img


def pantalla_plan():
    img, d = lienzo()
    encabezado(d, "Plan al lanzamiento")
    columnas = [
        ("Antes del 18/11", ["Reintento de SMS y respaldo por correo · Luis", "Botón de confirmar fijo · Sofía (viernes)"]),
        ("19/11", ["Revisión de estado del reintento"]),
        ("27/11", ["Lanzamiento, si el reintento está listo", "Si no: se mueve una semana"]),
    ]
    for i, (titulo, tarjetas) in enumerate(columnas):
        x = 120 + i * 580
        d.rounded_rectangle([x, 300, x + 540, 960], radius=24, fill="#f1f5f9")
        d.text((x + 36, 330), titulo, font=fuente(44, "negrita"), fill="#0f172a")
        for j, t in enumerate(tarjetas):
            y = 430 + j * 230
            d.rounded_rectangle([x + 30, y, x + 510, y + 190], radius=18, fill="white", outline="#e2e8f0", width=3)
            d.rectangle([x + 30, y, x + 42, y + 190], fill="#0d9488")
            palabras, renglon, renglones = t.split(), "", []
            for p in palabras:
                prueba = f"{renglon} {p}".strip()
                if d.textlength(prueba, font=fuente(34)) > 420:
                    renglones.append(renglon)
                    renglon = p
                else:
                    renglon = prueba
            renglones.append(renglon)
            for k, r in enumerate(renglones[:3]):
                d.text((x + 66, y + 30 + k * 48), r, font=fuente(34), fill="#1e293b")
    pie(d)
    return img


PANTALLAS = [(0, pantalla_agenda), (58, pantalla_metricas), (128, pantalla_logs), (205, pantalla_diseno), (285, pantalla_plan)]

DIALOGO = [
    (3, 9, "Ana Torres", "Buenos días. Gracias por conectarse; es la revisión de lanzamiento de Mesa Lista."),
    (9, 18, "Ana Torres", "Comparto la agenda: métricas de la beta, el error de los SMS, el diseño de la pantalla de reserva y la fecha de lanzamiento."),
    (19, 27, "Luis Méndez", "Perfecto. Yo traigo los números del error de confirmación, así que me toca el segundo punto."),
    (28, 36, "Sofía Ramírez", "Y yo tengo la propuesta del botón de confirmar, la que vimos el jueves."),
    (38, 46, "Ana Torres", "Bien. Empecemos con las métricas, que son buenas noticias."),
    (58, 70, "Ana Torres", "En seis semanas de beta pasamos de ciento veinte a cuatrocientas diez reservas por semana."),
    (70, 82, "Luis Méndez", "¿Y la cancelación? La semana pasada estaba arriba del quince por ciento."),
    (82, 96, "Ana Torres", "Bajó al doce. Creemos que ayudó el recordatorio de un día antes, pero no lo hemos medido por separado."),
    (96, 110, "Sofía Ramírez", "Propongo medirlo antes de cambiar nada, para no adivinar."),
    (110, 120, "Ana Torres", "De acuerdo, lo anoto como pendiente mío."),
    (128, 142, "Luis Méndez", "Va el error. De mil doscientos cuarenta envíos, treinta y ocho fallaron: el proveedor de SMS no responde en diez segundos y el cliente se queda sin confirmación."),
    (142, 156, "Luis Méndez", "Es el tres por ciento, pero quien no recibe el SMS cree que no reservó y llama al restaurante."),
    (156, 162, "Ana Torres", "¿Qué propones?"),
    (162, 180, "Luis Méndez", "Reintentar una vez a los treinta segundos y, si vuelve a fallar, mandar la confirmación por correo. Lo tengo listo antes del dieciocho."),
    (180, 190, "Ana Torres", "Hecho. Queda acordado: reintento y respaldo por correo, Luis, antes del dieciocho."),
    (205, 220, "Sofía Ramírez", "Esta es la pantalla de reserva. En teléfonos chicos el botón de confirmar queda debajo del pliegue y la gente no lo ve."),
    (220, 235, "Sofía Ramírez", "Mi propuesta es subirlo justo debajo del selector de personas y dejarlo fijo."),
    (235, 248, "Luis Méndez", "Por mí bien; es solo de la interfaz, no toca la API."),
    (248, 260, "Ana Torres", "Me gusta. Sofía, ¿lo puedes tener para la próxima versión de prueba?"),
    (260, 268, "Sofía Ramírez", "Sí, para el viernes."),
    (285, 300, "Ana Torres", "Último punto: la fecha. Si el reintento de SMS está listo el dieciocho, lanzamos el veintisiete de noviembre."),
    (300, 306, "Luis Méndez", "¿Y si no está listo?"),
    (306, 320, "Ana Torres", "Movemos el lanzamiento una semana. No quiero salir con clientes sin confirmación."),
    (320, 330, "Sofía Ramírez", "Entonces revisamos el estado el diecinueve, ¿les parece?"),
    (330, 340, "Ana Torres", "Perfecto. Revisión el diecinueve. Gracias a los dos."),
]


def vtt_tiempo(s):
    return f"{s // 3600:02}:{s % 3600 // 60:02}:{s % 60:02}.000"


def main():
    dir_cap = DESTINO / "capturas"
    dir_cap.mkdir(parents=True, exist_ok=True)
    capturas = []
    for n, (t, dibujar) in enumerate(PANTALLAS, start=1):
        nombre = f"{n:04}_{t // 3600:02}-{t % 3600 // 60:02}-{t % 60:02}.jpg"
        dibujar().save(dir_cap / nombre, quality=85)
        capturas.append({"n": n, "archivo": f"capturas/{nombre}", "t": t + 1, "desde": t,
                         "motivo": "inicio" if n == 1 else "estable", "cambio": 0.0 if n == 1 else 0.6})
    meta = {"modo": "pantalla", "video": "reunion-demo.mp4 (ficticio)", "truncado": False, "duracion": 345}
    (DESTINO / "capturas.json").write_text(json.dumps({"meta": meta, "capturas": capturas}, ensure_ascii=False, indent=1), encoding="utf-8")

    vtt = ["WEBVTT", ""]
    for i, (ini, fin, quien, texto) in enumerate(DIALOGO, start=1):
        vtt += [str(i), f"{vtt_tiempo(ini)} --> {vtt_tiempo(fin)}", f"<v {quien}>{texto}</v>", ""]
    (DESTINO / "reunion-demo.vtt").write_text("\n".join(vtt), encoding="utf-8")
    print(f"{len(capturas)} pantallas y {len(DIALOGO)} subtítulos en {DESTINO}")


if __name__ == "__main__":
    main()
