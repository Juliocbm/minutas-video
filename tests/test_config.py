import pytest

import config

REC_GPU = {"modelo": "large-v3", "dispositivo": "cuda"}


@pytest.fixture
def capas(tmp_path, monkeypatch):
    usuario = tmp_path / "usuario"
    usuario.mkdir()
    monkeypatch.setenv("MINUTAS_HOME", str(usuario))
    proyecto = tmp_path / "proyecto"
    (proyecto / ".minutas-video").mkdir(parents=True)

    def escribir(donde, archivo, texto):
        base = usuario if donde == "usuario" else proyecto / ".minutas-video"
        (base / archivo).write_text(texto, encoding="utf-8")
    return proyecto, escribir


def test_sin_archivos_usa_el_preset_estandar_y_el_equipo(capas):
    proyecto, _ = capas
    cfg = config.cargar(proyecto, None, REC_GPU)
    ef = cfg["efectiva"]
    assert ef["preset"] == "estandar" and ef["idioma"] == "es"
    assert ef["capturas"]["modo"] == "pantalla" and cfg["origen"]["capturas.modo"] == "preset estandar"
    assert ef["transcripcion"]["modelo"] == "large-v3" and cfg["origen"]["transcripcion.modelo"] == "equipo"
    assert ef["transcripcion"]["dispositivo_resuelto"] == "cuda"
    assert cfg["errores"] == []


def test_el_proyecto_manda_sobre_el_usuario(capas):
    proyecto, escribir = capas
    escribir("usuario", "config.toml", 'preset = "completo"\nidioma = "en"\n')
    escribir("proyecto", "config.toml", 'preset = "rapido"\n')
    cfg = config.cargar(proyecto, None, REC_GPU)
    assert cfg["efectiva"]["preset"] == "rapido" and cfg["origen"]["preset"] == "proyecto"
    assert cfg["efectiva"]["idioma"] == "en" and cfg["origen"]["idioma"] == "usuario"
    assert cfg["efectiva"]["transcripcion"]["modelo"] == "large-v3-turbo"
    assert cfg["efectiva"]["minuta"] == "corta"


def test_un_valor_fijado_manda_sobre_el_preset(capas):
    proyecto, escribir = capas
    escribir("usuario", "config.toml", '[transcripcion]\nmodelo = "medium"\n')
    cfg = config.cargar(proyecto, {"preset": "rapido"}, REC_GPU)
    assert cfg["efectiva"]["transcripcion"]["modelo"] == "medium"


def test_la_corrida_manda_sobre_todo(capas):
    proyecto, escribir = capas
    escribir("proyecto", "config.toml", '[capturas]\nmodo = "camara"\n')
    cfg = config.cargar(proyecto, {"capturas": {"modo": "ninguna", "max": None}}, REC_GPU)
    assert cfg["efectiva"]["capturas"] == {"modo": "ninguna", "max": 200}
    assert cfg["origen"]["capturas.modo"] == "corrida"


def test_errores_claros(capas):
    proyecto, escribir = capas
    escribir("proyecto", "config.toml", 'preset = "turbo"\nmodelo = "x"\n[capturas]\nmax = "mucho"\n')
    errores = config.cargar(proyecto)["errores"]
    assert any("preset" in e and "turbo" in e for e in errores)
    assert any("clave desconocida «modelo»" in e for e in errores)
    assert any("capturas.max" in e and "entero" in e for e in errores)


def test_toml_roto(capas):
    proyecto, escribir = capas
    escribir("proyecto", "config.toml", "preset = \n")
    assert "no es TOML válido" in config.cargar(proyecto)["errores"][0]


def test_glosario_participantes_y_vocabulario_viejo(capas):
    proyecto, escribir = capas
    escribir("usuario", "glosario.toml", '[terminos]\nOKR = []\n')
    escribir("proyecto", "glosario.toml", '[terminos]\nNEXO = ["Nexus", "NEXO"]\n"Mesa Lista" = "mesalista"\n')
    escribir("proyecto", "vocabulario.txt", "SAP\nNEXO  # ya está en el glosario\n")
    escribir("proyecto", "participantes.toml",
             '[[persona]]\nnombre = "Ana Ruiz"\nrol = "Líder"\nalias = ["Anita"]\n\n[[persona]]\nrol = "sin nombre"\n')
    cfg = config.cargar(proyecto)
    assert cfg["glosario"] == {"OKR": [], "NEXO": ["Nexus"], "Mesa Lista": ["mesalista"], "SAP": []}
    assert cfg["participantes"] == [{"nombre": "Ana Ruiz", "rol": "Líder", "organizacion": "", "alias": ["Anita"]}]
    assert any("necesita nombre" in e for e in cfg["errores"])
    assert any("vocabulario.txt" in a for a in cfg["avisos"])


def test_busca_la_carpeta_del_proyecto_hacia_arriba(capas):
    proyecto, _ = capas
    profunda = proyecto / "docs" / "juntas"
    profunda.mkdir(parents=True)
    assert config.buscar_proyecto(profunda) == (proyecto / ".minutas-video").resolve()
