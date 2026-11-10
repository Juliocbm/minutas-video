"""Exportaciones de la minuta: Markdown sin enlaces, bloques, CSV, PDF y Word."""
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
    for archivo in ("transcripcion.json", "capturas.json", "ocr.json", "minuta.json"):
        shutil.copy(EJEMPLO / archivo, destino / archivo)
    return destino


def test_el_markdown_para_compartir_no_enlaza_archivos_locales(salida):
    md, _, _ = exportar.markdown_para_compartir(salida)
    assert "](" not in md and "transcripcion-ilustrada.html" not in md
    assert "| 04:45, 05:06 | 0005 |" in md                    # en la tabla, la captura sin etiqueta
    assert "(00:58 · captura 0002)" in md                     # en el texto, con etiqueta


def test_bloques_e_inline():
    md = "# Título\n\n> Aviso\n\n**Fecha:** hoy  \n**Fuente:** x\n\n| A | B |\n|---|---|\n| 1 \\| 2 | [x](y) |\n\n- uno\n- dos\n\n---\n"
    bs = exportar.bloques(md)
    assert [b["tipo"] for b in bs] == ["h1", "cita", "p", "tabla", "lista", "hr"]
    assert bs[2]["lineas"] == ["**Fecha:** hoy", "**Fuente:** x"]
    assert bs[3]["filas"] == [["A", "B"], ["1 | 2", "[x](y)"]]
    assert exportar.inline("**27 de noviembre**, ver `x` *(inferido)* [enlace](a.html)") == [
        ("27 de noviembre", {"b"}), (", ver ", set()), ("x", {"code"}), (" ", set()), ("(inferido)", {"i"}), (" enlace", set())]


def test_csv_de_pendientes_para_excel(salida, capsys):
    assert exportar.comando(salida, ["csv"], None) == 0
    crudo = (salida / "pendientes.csv").read_bytes()
    assert crudo.startswith(b"\xef\xbb\xbf")  # BOM: Excel respeta los acentos
    filas = list(csv.reader(crudo.decode("utf-8-sig").splitlines()))
    assert filas[0] == ["#", "Pendiente", "Responsable", "Fecha", "Minuto", "Cita", "Inferido"]
    assert filas[1][:5] == ["1", "Reintento de SMS y respaldo por correo", "Luis Méndez", "18/11", "03:00"]
    assert len(filas) == 5 and "✓ CSV" in capsys.readouterr().out


@pytest.mark.skipif(exportar.navegador() is None, reason="sin Edge ni Chrome")
def test_pdf_con_el_navegador(salida):
    assert exportar.comando(salida, ["pdf"], None) == 0
    assert (salida / "minuta.pdf").read_bytes()[:5] == b"%PDF-"


def test_word(correr_script, salida):
    r = correr_script("exportar_docx.py", salida)
    assert r.returncode == 0, r.stdout + r.stderr
    with zipfile.ZipFile(salida / "minuta.docx") as z:
        documento = z.read("word/document.xml").decode("utf-8")
    assert "Reintento de SMS y respaldo por correo" in documento and "transcripcion-ilustrada" not in documento


def test_minuta_invalida_no_se_exporta(salida, capsys):
    (salida / "minuta.json").write_text('{"acuerdos": []}', encoding="utf-8")
    assert exportar.comando(salida, ["csv"], None) == 2
    assert "titulo: falta" in capsys.readouterr().out and not (salida / "pendientes.csv").exists()
