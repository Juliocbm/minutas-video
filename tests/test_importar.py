from conftest import EJEMPLO
from importar_transcripcion import aplicar_prefijos, leer_cues

VTT_TEAMS = """WEBVTT

1a2b-3c
00:00:01.000 --> 00:00:04.500
<v Ana López>Buenos días a todos.</v>

00:00:05.000 --> 00:00:07.250
<v Luis Pérez>Hola, Ana.</v>
"""

SRT_ZOOM = """1
00:00:01,000 --> 00:00:03,000
Ana: Empezamos con la agenda.

2
00:00:03,500 --> 00:00:05,000
Luis: De acuerdo.
"""


def test_teams_toma_el_hablante_de_la_etiqueta_v():
    cues = leer_cues(VTT_TEAMS)
    assert [c["hablante"] for c in cues] == ["Ana López", "Luis Pérez"]
    assert cues[0] == {"inicio": 1.0, "fin": 4.5, "texto": "Buenos días a todos.", "hablante": "Ana López"}
    assert cues[1]["fin"] == 7.25


def test_zoom_toma_el_hablante_del_prefijo():
    cues = aplicar_prefijos(leer_cues(SRT_ZOOM))
    assert [(c["hablante"], c["texto"]) for c in cues] == [("Ana", "Empezamos con la agenda."), ("Luis", "De acuerdo.")]


def test_un_prefijo_suelto_no_se_toma_como_hablante():
    srt = SRT_ZOOM.replace("Ana: Empezamos", "Empezamos").replace("Luis: De", "De") + \
        "\n3\n00:00:06,000 --> 00:00:08,000\nNota: esto no es un hablante.\n"
    cues = aplicar_prefijos(leer_cues(srt))
    assert all(c["hablante"] is None for c in cues)
    assert cues[-1]["texto"] == "Nota: esto no es un hablante."


def test_reunion_de_ejemplo():
    cues = aplicar_prefijos(leer_cues((EJEMPLO / "reunion-demo.vtt").read_text(encoding="utf-8")))
    assert len(cues) == 25
    assert {c["hablante"] for c in cues} == {"Ana Torres", "Luis Méndez", "Sofía Ramírez"}
