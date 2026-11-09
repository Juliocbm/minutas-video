from glosario import buscar


def seg(t, texto):
    return {"inicio": t, "fin": t + 2, "texto": texto, "hablante": None}


SEGMENTOS = [
    seg(10, "Lo que nos mandó Nexus ayer no cuadra."),
    seg(20, "Nexusmith revisó la interfaz de NEXO."),
    seg(30, "Según nexus, la factura se cancela en nexo."),
    seg(40, "Gracias, Anita. Ana Ruiz lo confirma."),
]


def test_cuenta_variantes_con_limites_de_palabra():
    r = buscar(SEGMENTOS, {"NEXO": ["Nexus", "nexo"]}, [])
    t = r["terminos"][0]
    assert t["veces_bien_escrito"] == 2           # «NEXO» y «nexo»: ambas son la palabra
    formas = {v["forma"]: v["veces"] for v in t["variantes"]}
    assert formas == {"Nexus": 2, "nexo": 1}          # «Nexusmith» no cuenta; «NEXO» exacto no es variante
    assert t["variantes"][0]["ejemplos"][0]["t"] == 10
    assert r["nota"] == "Términos que la transcripción automática escribe mal: «Nexus» o «nexo» es NEXO."


def test_sin_variantes_no_hay_nota():
    r = buscar(SEGMENTOS, {"OKR": []}, [])
    assert r["nota"] == "" and r["terminos"][0]["veces_bien_escrito"] == 0


def test_menciones_de_participantes_por_nombre_alias_y_nombre_de_pila():
    r = buscar(SEGMENTOS, {}, [{"nombre": "Ana Ruiz", "rol": "Líder", "organizacion": "", "alias": ["Anita"]}])
    p = r["personas"][0]
    assert p["menciones"] == 2                      # «Anita» y «Ana Ruiz»; el «Ana» de «Ana Ruiz» no cuenta aparte
    assert {e["forma"] for e in p["ejemplos"]} == {"Ana Ruiz", "Anita"}
