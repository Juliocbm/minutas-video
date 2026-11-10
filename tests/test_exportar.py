"""Exportaciones de la minuta desde minuta.md: bloques, CSV de pendientes, PDF y Word."""
import csv
import shutil
import zipfile

import pytest

import exportar
from conftest import EJEMPLO


@pytest.fixture
def salida(tmp_path):
    destino = tmp_path / "ejemplo"
    destino.mkdir()
    shutil.copy(EJEMPLO / "minuta.md", destino / "minuta.md")
    return destino


def leer_csv(ruta):
    crudo = ruta.read_bytes()
    assert crudo.startswith(b"\xef\xbb\xbf")  # BOM: Excel respeta los acentos
    return list(csv.reader(crudo.decode("utf-8-sig").splitlines()))


def test_bloques_e_inline():
    md = "# Título\n\n> Aviso\n\n**Fecha:** hoy  \n**Fuente:** x\n\n| A | B |\n|---|---|\n| 1 \\| 2 | [x](y) |\n\n- uno\n- dos\n\n---\n"
    bs = exportar.bloques(md)
    assert [b["tipo"] for b in bs] == ["h1", "cita", "p", "tabla", "lista", "hr"]
    assert bs[2]["lineas"] == ["**Fecha:** hoy", "**Fuente:** x"]
    assert bs[3]["filas"] == [["A", "B"], ["1 | 2", "[x](y)"]]
    assert exportar.inline("**27 de noviembre**, ver `x` *(inferido)* [enlace](a.html)") == [
        ("27 de noviembre", {"b"}), (", ver ", set()), ("x", {"code"}), (" ", set()), ("(inferido)", {"i"}), (" enlace", set())]


def test_csv_con_la_tabla_de_pendientes(salida, capsys):
    assert exportar.comando(salida, ["csv"], None) == 0
    filas = leer_csv(salida / "pendientes.csv")
    assert filas[0] == ["#", "Pendiente", "Responsable", "Fecha", "Min."]
    assert filas[1] == ["1", "Reintento de SMS y respaldo por correo", "Luis Méndez", "18/11", "03:00"]  # sin enlaces
    assert len(filas) == 5 and "✓ CSV" in capsys.readouterr().out


def test_pendientes_de_la_minuta_corta_y_notas_bajo_la_tabla():
    corta = "# Minuta · X\n\n## Pendientes\n- Medir el recordatorio · Ana · 18/11\n- Revisar el botón · Sofía\n\n*Nota*\n"
    assert exportar.pendientes(corta) == [["#", "Pendiente", "Responsable", "Fecha"],
                                          ["1", "Medir el recordatorio", "Ana", "18/11"], ["2", "Revisar el botón", "Sofía", ""]]
    con_notas = "## Pendientes\n\n| # | Pendiente |\n|---|---|\n| 1 | A |\n\n- una nota, no un pendiente\n\n## Otra\n| x |\n"
    assert exportar.pendientes(con_notas) == [["#", "Pendiente"], ["1", "A"]]
    assert exportar.pendientes("## Pendientes\n\nNinguno.\n") == []
    assert exportar.pendientes("## Acuerdos\n- a\n") is None


def test_sin_seccion_de_pendientes_el_csv_falla_y_los_demas_siguen(salida, capsys):
    (salida / "minuta.md").write_text("# Minuta · X\n\n## Acuerdos\n- uno\n", encoding="utf-8")
    assert exportar.comando(salida, ["csv"], None) == 1
    assert "Pendientes" in capsys.readouterr().out and not (salida / "pendientes.csv").exists()


def test_sin_minuta_no_se_exporta(tmp_path, capsys):
    assert exportar.comando(tmp_path, ["csv"], None) == 2
    assert "minuta.md" in capsys.readouterr().out


@pytest.mark.skipif(exportar.navegador() is None, reason="sin Edge ni Chrome")
def test_pdf_con_el_navegador(salida):
    assert exportar.comando(salida, ["pdf"], None) == 0
    assert (salida / "minuta.pdf").read_bytes()[:5] == b"%PDF-"


def test_word_sin_enlaces_locales(correr_script, salida):
    r = correr_script("exportar_docx.py", salida)
    assert r.returncode == 0, r.stdout + r.stderr
    with zipfile.ZipFile(salida / "minuta.docx") as z:
        documento = z.read("word/document.xml").decode("utf-8")
    assert "Reintento de SMS y respaldo por correo" in documento and "transcripcion-ilustrada" not in documento
