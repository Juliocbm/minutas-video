"""Minuta estructurada: validación, verificación de la evidencia y Markdown, con la reunión de ejemplo."""
import copy
import json
import shutil

import pytest

import minuta
from conftest import EJEMPLO


@pytest.fixture
def salida(tmp_path):
    destino = tmp_path / "reunion_minuta"
    destino.mkdir()
    for archivo in ("transcripcion.json", "capturas.json", "ocr.json", "minuta.json"):
        shutil.copy(EJEMPLO / archivo, destino / archivo)
    return destino


def base(salida):
    return json.loads((salida / "minuta.json").read_text(encoding="utf-8"))


def minima(**secciones):
    """Minuta con solo lo que se prueba: las citas del ejemplo no se mezclan en los conteos."""
    return {"titulo": "Prueba", **secciones}


def con(salida, datos):
    (salida / "minuta.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return minuta.procesar(salida)


def acuerdo(texto, *evidencias, **extra):
    return {"texto": texto, "evidencia": list(evidencias), **extra}


def test_el_ejemplo_verifica_todas_sus_citas(salida, capsys):
    assert minuta.comando(salida) == 0
    assert "20 de 20 citas verificadas" in capsys.readouterr().out
    md = (salida / "minuta.md").read_text(encoding="utf-8")
    assert "[04:45](transcripcion-ilustrada.html#t285)" in md          # enlaza a la frase exacta
    assert "[0005](capturas/0005_00-04-45.jpg)" in md
    assert "**Fecha:** 12 de noviembre de 2026, 10:00 · videollamada." in md
    assert "transcripción importada con hablantes y capturas" in md
    assert "en seis semanas ([00:58](transcripcion-ilustrada.html#t58) · [0002](capturas/0002_00-00-58.jpg))." in md


def test_reporta_citas_fuera_de_lugar_parafraseadas_o_inventadas(salida):
    datos = minima()
    datos["acuerdos"] = [
        acuerdo("Fecha", {"t": "01:00", "cita": "lanzamos el veintisiete de noviembre"}),
        acuerdo("Paráfrasis", {"t": "04:45", "cita": "si el reintento está el dieciocho entonces salimos el veintisiete"}),
        acuerdo("Inventada", {"t": "02:00", "cita": "el presupuesto se duplica en enero"}),
        acuerdo("Fuera", {"t": "09:00", "cita": "Revisión el diecinueve"}),
        acuerdo("Captura", {"t": "02:42", "captura": 9}),
        acuerdo("Lejos", {"t": "05:30", "captura": 1}),
    ]
    r = con(salida, datos)
    assert r["estado"] == "revisar" and r["citas"] == 4 and r["verificadas"] == 0
    p = "\n".join(r["problemas"])
    assert "acuerdos[0]" in p and "la cita está en 00:04:45, no cerca de 00:01:00" in p
    assert "acuerdos[1]" in p and "no es textual" in p
    assert "acuerdos[2]" in p and "no aparece en la transcripción" in p
    assert "acuerdos[3]" in p and "fuera de la grabación" in p
    assert "no existe la captura 0009" in p
    assert "la captura 0001 estuvo en pantalla de 00:00:00 a 00:00:58" in p


def test_tolera_muletillas_omitidas_y_tramos_saltados(salida):
    datos = minima()
    datos["acuerdos"] = [
        acuerdo("Sin muletillas", {"t": "02:08", "cita": "de mil doscientos cuarenta envíos treinta y ocho fallaron el proveedor no responde"}),
        acuerdo("Con salto", {"t": "02:08", "cita": "De mil doscientos cuarenta envíos… llama al restaurante"}),
    ]
    r = con(salida, datos)
    assert r["verificadas"] == 2, r["problemas"]


def test_terminos_del_glosario_y_texto_de_la_captura(salida):
    # La transcripción dice «Mesa Lista»; si el glosario dice que eso es NEXO, una cita con «NEXO» cuenta.
    # (Sin el glosario, «lanzamiento de NEXO» contra «lanzamiento de Mesa Lista» no llega al 80 %.)
    (salida / "glosario.json").write_text(json.dumps({"terminos": [
        {"termino": "NEXO", "variantes": [{"forma": "Mesa Lista", "veces": 1}]}]}), encoding="utf-8")
    # El dato solo está en pantalla: la cita se busca en el texto de la captura.
    (salida / "ocr.json").write_text(json.dumps({"capturas": [
        {"n": 2, "lineas": ["Reservas por semana", "Cancelación 15 % → 12 %"]}]}, ensure_ascii=False), encoding="utf-8")
    datos = minima()
    datos["acuerdos"] = [
        acuerdo("Glosario", {"t": "00:03", "cita": "lanzamiento de NEXO"}),
        acuerdo("Pantalla", {"t": "01:00", "cita": "Cancelación 15 % → 12 %", "captura": 2}),
    ]
    r = con(salida, datos)
    assert r["verificadas"] == 2, r["problemas"]
    assert "«Mesa Lista» es NEXO" in (salida / "minuta.md").read_text(encoding="utf-8")
    (salida / "glosario.json").unlink()
    assert con(salida, datos)["verificadas"] == 1


def test_sin_evidencia_se_reporta_salvo_si_es_inferido(salida):
    datos = base(salida)
    datos["pendientes"] = [{"texto": "Algo sin respaldo"}, {"texto": "Deducido", "inferido": True}]
    r = con(salida, datos)
    problemas = [p for p in r["problemas"] if "pendientes" in p]
    assert len(problemas) == 1 and "pendientes[0]" in problemas[0] and "sin evidencia" in problemas[0]
    assert "Deducido *(inferido)*" in (salida / "minuta.md").read_text(encoding="utf-8")


def test_errores_de_estructura_no_generan_minuta(salida, capsys):
    datos = base(salida)
    datos["acuerdos"][0]["evidencias"] = datos["acuerdos"][0].pop("evidencia")
    datos["acuerdos"][1]["evidencia"][0]["t"] = "5 min"
    datos["plantilla"] = "larga"
    del datos["titulo"]
    con(salida, datos)
    (salida / "minuta.md").unlink(missing_ok=True)
    assert minuta.comando(salida) == 2
    salida_texto = capsys.readouterr().out
    assert "acuerdos[0].evidencias: clave desconocida" in salida_texto
    assert "acuerdos[1].evidencia[0].t: debe ser segundos o \"mm:ss\"" in salida_texto
    assert "plantilla: debe ser \"completa\" o \"corta\"" in salida_texto
    assert "titulo: falta." in salida_texto
    assert not (salida / "minuta.md").exists()


def test_json_roto_y_minuta_faltante(salida, capsys):
    (salida / "minuta.json").write_text("{ roto", encoding="utf-8")
    assert minuta.comando(salida) == 2 and "no es JSON válido" in capsys.readouterr().out
    (salida / "minuta.json").unlink()
    assert minuta.comando(salida) == 2 and "No existe" in capsys.readouterr().out


def test_plantilla_corta(salida):
    datos = copy.deepcopy(base(salida))
    datos.update(plantilla="corta", resumen="Se revisó la beta y se fijó el lanzamiento.", pendientes=[])
    r = con(salida, datos)
    assert r["estado"] == "ok", r["problemas"]
    md = (salida / "minuta.md").read_text(encoding="utf-8")
    assert "**En resumen:** Se revisó la beta" in md and "## Acuerdos" in md
    assert "Temas tratados" not in md and "Participantes:** Ana Torres, Luis Méndez, Sofía Ramírez." in md
    assert md.split("## Pendientes")[1].strip().startswith("Ninguno.")


def test_tiempos_en_segundos_o_texto():
    assert minuta.segundos(90) == 90 and minuta.segundos("01:30") == 90 and minuta.segundos("1:01:30") == 3690
    assert minuta.segundos("5 min") is None and minuta.segundos(True) is None and minuta.segundos(-1) is None


def test_con_solo_la_transcripcion_no_dice_grabacion(salida):
    (salida / "reunion.json").write_text(json.dumps({"entrada": {"tipo": "transcripcion"}}), encoding="utf-8")
    datos = minima(lugar="Teams (videollamada)", fecha="2026-11-08")
    con(salida, datos)
    md = (salida / "minuta.md").read_text(encoding="utf-8")
    assert "**Fecha:** 8 de noviembre de 2026 · Teams (videollamada)." in md
    assert "**Fuente:** transcripción importada con hablantes y capturas" in md
    assert "Los minutos son los de la transcripción." in md and "grabación" not in md
