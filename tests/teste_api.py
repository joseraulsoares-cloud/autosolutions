"""Testes de integração da API da área de cliente (servidor local com MariaDB)."""
import os
import re
import sys
import threading
from pathlib import Path

import requests

B = "http://127.0.0.1:8790"
RES = []


def check(cond, msg):
    RES.append(bool(cond))
    print(("OK     " if cond else "FALHA  ") + msg)


def sessao():
    s = requests.Session()
    s.headers.update({"Origin": B})
    return s


def emails():
    return requests.get(B + "/api/dev/emails").json()["emails"]


def ultimo_email(para, prefixo):
    for e in emails():
        if e["para"] == para and e["assunto"].startswith(prefixo):
            return e
    return None


def nif(base8):
    d = [int(c) for c in base8]
    soma = sum(n * (9 - i) for i, n in enumerate(d))
    r = soma % 11
    return base8 + str(0 if r < 2 else 11 - r)


def entrar(s, email):
    r = s.post(B + "/api/entrar/codigo", json={"email": email})
    assert r.status_code == 200, r.text
    e = ultimo_email(email, "Código de acesso")
    codigo = re.search(r"(\d{6})", e["assunto"]).group(1)
    r = s.post(B + "/api/entrar/verificar", json={"email": email, "codigo": codigo})
    return r


# ---------------------------------------------------------------- base
r = requests.get(B + "/api/sessao")
check(r.status_code == 200 and r.json()["email"] is None, "sem sessão: /api/sessao responde sem email")
r = requests.post(B + "/api/registo", json={}, headers={"Origin": "https://mal.example"})
check(r.status_code == 403, "POST com origem de outro site é recusado (403)")
r = requests.post(B + "/api/registo", json={})
check(r.status_code == 403, "POST sem cabeçalho Origin é recusado (403)")
r = requests.put(B + "/api/conta", json={}, headers={"Origin": B})
check(r.status_code == 405, "métodos fora de GET/POST respondem 405")

# ---------------------------------------------------------------- registo
NIF_A, NIF_B = nif("50000000"), nif("51000000")
reg = {"nome": "Oficina A, Lda", "nif": "123456788", "responsavel": "Ana A", "email": "a@teste.pt",
       "telefone": "912 345 678", "whatsapp": "", "entrega": "email", "termos": True}
r = sessao().post(B + "/api/registo", json=reg)
check(r.status_code == 400 and "NIF" in r.json()["erro"], "registo com NIF inválido é recusado")
reg["nif"] = NIF_A
r = sessao().post(B + "/api/registo", json=dict(reg, termos=False))
check(r.status_code == 400, "registo sem aceitar os termos é recusado")
r = sessao().post(B + "/api/registo", json=reg)
check(r.status_code == 201, "registo da oficina A aceite (201)")
r = sessao().post(B + "/api/registo", json=reg)
check(r.status_code == 409, "registo repetido com o mesmo email: 409")
r = sessao().post(B + "/api/registo", json=dict(reg, email="b@teste.pt", nome="Oficina B", nif=NIF_B, entrega="whatsapp", whatsapp="923 456 789"))
check(r.status_code == 201, "registo da oficina B aceite")
check(ultimo_email("admin@teste.pt", "Novo registo: Oficina B") is not None, "administrador avisado por email do novo registo")

# ---------------------------------------------------------------- entrada
s_pend = sessao()
r = s_pend.post(B + "/api/entrar/codigo", json={"email": "a@teste.pt"})
check(r.status_code == 200 and ultimo_email("a@teste.pt", "A sua conta aguarda aprovação"), "conta pendente: não recebe código, recebe aviso de aprovação pendente")
r = s_pend.post(B + "/api/entrar/verificar", json={"email": "a@teste.pt", "codigo": "123456"})
check(r.status_code == 400, "conta pendente não consegue entrar")

adm = sessao()
r = entrar(adm, "admin@teste.pt")
check(r.status_code == 200 and r.json()["admin"] is True, "administrador entra com o código do email")
check("garc_sessao" in adm.cookies and "httponly" in r.headers.get("Set-Cookie", "").lower(), "cookie de sessão HttpOnly criado")

# ---------------------------------------------------------------- aprovação
r = adm.get(B + "/api/admin/oficinas?filtro=pendente")
pend = {o["email"]: o for o in r.json()["oficinas"]}
check(set(pend) == {"a@teste.pt", "b@teste.pt"}, "painel lista as duas oficinas por aprovar")
for em in ("a@teste.pt", "b@teste.pt"):
    r = adm.post(B + f"/api/admin/oficinas/{pend[em]['id']}/estado", json={"estado": "aprovada"})
    check(r.status_code == 200 and r.json()["oficina"]["estado"] == "aprovada", f"oficina {em} aprovada")
check(ultimo_email("a@teste.pt", "A sua conta foi aprovada") is not None, "oficina avisada por email da aprovação")
ID_A, ID_B = pend["a@teste.pt"]["id"], pend["b@teste.pt"]["id"]

sa = sessao()
r = entrar(sa, "a@teste.pt")
check(r.status_code == 200 and r.json()["oficina"]["nome"] == "Oficina A, Lda" and r.json()["saldo"] == 0, "oficina A entra, saldo 0")
sb = sessao()
check(entrar(sb, "b@teste.pt").status_code == 200, "oficina B entra")

r = sa.get(B + "/api/admin/oficinas?filtro=todas")
check(r.status_code == 403, "oficina não acede à API de administração (403)")

# ---------------------------------------------------------------- saldo e pedidos
# Modelo: no envio descontam-se 5 tokens; o administrador define o custo final depois de analisar a ECU.
def saldo_a():
    return sa.get(B + "/api/saldo").json()["saldo"]


pedido = {"viatura": "Volkswagen Golf VII", "matricula": "aa 00aa", "motor": "2.0 TDI", "ano": "2017", "ecu": "Bosch EDC17C64",
          "ferramenta": "KESS3", "metodo": "OBD", "modulos": ["STAGE 1/2"], "observacoes": "", "entrega": "email",
          "whatsapp": "", "declaracao": False, "cuidados": True, "tamanho": 100000}
r = sa.post(B + "/api/pedidos", json=pedido)
check(r.status_code == 402 and r.json().get("saldo") == 0 and r.json().get("custo") == 5, "sem saldo: pedido recusado com 402 (mínimo 5, saldo 0)")

r = adm.post(B + f"/api/admin/oficinas/{ID_A}/tokens", json={"tokens": 10, "referencia": "FT 2026/1"})
check(r.status_code == 200 and r.json()["saldo"] == 10, "administrador carrega 10 tokens (saldo 10)")
check(ultimo_email("a@teste.pt", "Saldo carregado") is not None, "oficina avisada do carregamento")
r = adm.post(B + f"/api/admin/oficinas/{ID_A}/tokens", json={"tokens": -11})
check(r.status_code == 409, "acerto que deixaria o saldo negativo é recusado")

r = sa.post(B + "/api/pedidos", json=dict(pedido, modulos=["STAGE 1/2", "EGR OFF"]))
check(r.status_code == 400 and "declaração" in r.json()["erro"], "módulo de emissões sem declaração: recusado")
r = sa.post(B + "/api/pedidos", json=dict(pedido, modulos=["STAGE 1/2", "EGR OFF", "NAO EXISTE"], declaracao=True))
check(r.status_code == 400, "módulo desconhecido: recusado")
r = sa.post(B + "/api/pedidos", json=dict(pedido, matricula="  "))
check(r.status_code == 400 and "matrícula" in r.json()["erro"], "pedido sem matrícula: recusado")
r = sa.post(B + "/api/pedidos", json=dict(pedido, matricula="AA@00#AA"))
check(r.status_code == 400 and "matrícula" in r.json()["erro"], "matrícula com carateres inválidos: recusada")
r = sa.post(B + "/api/pedidos", json=dict(pedido, matricula="A" * 16))
check(r.status_code == 400, "matrícula com mais de 15 carateres: recusada")
for valor in (False, "sim", None):
    r = sa.post(B + "/api/pedidos", json=dict(pedido, cuidados=valor))
    check(r.status_code == 400 and "cuidados" in r.json()["erro"], f"sem confirmar os cuidados de leitura ({valor!r}): recusado")
check(saldo_a() == 10, "pedidos recusados não descontam tokens")
r = sa.post(B + "/api/pedidos", json=dict(pedido, modulos=["STAGE 1/2", "EGR OFF"], declaracao=True))
j = r.json().get("pedido", {})
check(r.status_code == 201 and r.json()["saldo"] == 5 and j["tokens"] == 5 and j["pagos"] == 5 and j["custo_definido"] is False,
      "pedido criado: descontados 5 tokens, custo final por definir, saldo 5")
check(j["cuidados_leitura"] is True, "a confirmação dos cuidados de leitura fica registada no pedido")
P1 = j["id"]
check(j["matricula"] == "AA-00-AA", "matrícula portuguesa normalizada: 'aa 00aa' fica AA-00-AA")

original = os.urandom(150_000)
r = sa.post(B + f"/api/pedidos/{P1}/original", files={"ficheiro": ("golf ori.bin", original, "application/octet-stream")})
check(r.status_code == 200 and r.json()["pedido"]["estado"] == "recebido", "ficheiro original recebido, estado 'recebido'")
check(r.json()["pedido"]["original_nome"] in ("golf_ori.bin", "golf ori.bin"), "nome do ficheiro limpo: " + r.json()["pedido"]["original_nome"])
e = ultimo_email("admin@teste.pt", f"Novo pedido n.º {P1}")
check(e is not None and "golf" in (e["anexos"] or ""), "administrador recebe o pedido por email com o original em anexo")
check(e is not None and "AA-00-AA" in e["assunto"] and "Matrícula: AA-00-AA" in e["texto"] and "Tokens descontados: 5" in e["texto"],
      "email do novo pedido indica a matrícula e os tokens descontados")
r = sa.post(B + f"/api/pedidos/{P1}/original", files={"ficheiro": ("outro.bin", b"x" * 10)})
check(r.status_code == 409, "segundo envio de ficheiro no mesmo pedido: 409")
r = sa.post(B + f"/api/pedidos/{P1}/cancelar", json={})
check(r.status_code == 409 and saldo_a() == 5, "depois de enviado o ficheiro, a oficina já não pode cancelar")

check(sb.get(B + f"/api/pedidos/{P1}").status_code == 404, "outra oficina não vê o pedido (404)")
check(sb.get(B + f"/api/pedidos/{P1}/original").status_code == 404, "outra oficina não descarrega o ficheiro (404)")
check(sa.get(B + f"/api/pedidos/{P1}/modificado").status_code == 409, "modificado indisponível antes de concluído (409)")
check(sa.post(B + f"/api/admin/pedidos/{P1}/custo", json={"tokens": 12}).status_code == 403, "oficina não define o custo (403)")

r = adm.get(B + "/api/admin/pedidos?filtro=tratar")
check(any(p["id"] == P1 for p in r.json()["pedidos"]), "pedido aparece em 'Por tratar'")
r = adm.get(B + f"/api/pedidos/{P1}/original")
check(r.status_code == 200 and r.content == original, "administrador descarrega o original (bytes iguais)")
r = adm.post(B + f"/api/admin/pedidos/{P1}/estado", json={"acao": "em_curso"})
check(r.status_code == 200 and r.json()["pedido"]["estado"] == "em_curso", "pedido passa a em curso")

# Custo final maior do que o saldo: o pedido fica à espera de saldo
r = adm.post(B + f"/api/admin/pedidos/{P1}/custo", json={"tokens": 4})
check(r.status_code == 400, "custo abaixo do mínimo (4): recusado")
r = adm.post(B + f"/api/admin/pedidos/{P1}/custo", json={"tokens": 12})
j = r.json()["pedido"]
check(r.status_code == 200 and j["estado"] == "a_aguardar_saldo" and j["falta"] == 7 and j["pagos"] == 5 and saldo_a() == 5,
      "custo final 12 com saldo 5: pedido à espera de saldo, faltam 7, nada descontado")
e = ultimo_email("a@teste.pt", f"Pedido n.º {P1}: falta saldo")
check(e is not None and "Faltam 7 tokens" in e["texto"] and "pelo menos 2 tokens" in e["texto"], "oficina avisada: faltam 7, carregar pelo menos 2")
r = adm.get(B + "/api/admin/pedidos?filtro=a_aguardar_saldo")
check(any(p["id"] == P1 for p in r.json()["pedidos"]), "pedido aparece no filtro 'Falta saldo'")
modificado = os.urandom(150_000)
r = adm.post(B + f"/api/admin/pedidos/{P1}/modificado", files={"ficheiro": ("golf_stage1.bin", modificado)})
check(r.status_code == 200 and r.json()["pedido"]["modificado_nome"] == "golf_stage1.bin", "ficheiro modificado carregado enquanto espera o saldo")
r = adm.post(B + f"/api/admin/pedidos/{P1}/estado", json={"acao": "concluir"})
check(r.status_code == 409 and "faltam 7" in r.json()["erro"], "não se conclui sem o custo final pago (409)")
j = sa.get(B + f"/api/pedidos/{P1}").json()["pedido"]
check(j["estado"] == "a_aguardar_saldo" and j["falta"] == 7, "a oficina vê o pedido à espera de saldo, com a falta")

# Carregar 2 tokens liquida a diferença e o pedido avança sozinho
r = adm.post(B + f"/api/admin/oficinas/{ID_A}/tokens", json={"tokens": 2, "referencia": "FT 2026/3"})
j = sa.get(B + f"/api/pedidos/{P1}").json()["pedido"]
check(r.status_code == 200 and j["estado"] == "em_curso" and j["pagos"] == 12 and j["falta"] == 0 and saldo_a() == 0,
      "carregamento de 2 tokens: diferença de 7 descontada, pedido em curso, saldo 0")
e = ultimo_email("a@teste.pt", "Saldo carregado: 2 tokens")
check(e is not None and f"Pedido n.º {P1}" in e["texto"] and "avançou" in e["texto"], "email do carregamento diz que o pedido avançou")

# Baixar o custo devolve a diferença
r = adm.post(B + f"/api/admin/pedidos/{P1}/custo", json={"tokens": 10})
j = r.json()["pedido"]
check(r.status_code == 200 and j["tokens"] == 10 and j["pagos"] == 10 and j["estado"] == "em_curso" and saldo_a() == 2,
      "custo baixado para 10: 2 tokens voltam ao saldo")
r = adm.post(B + f"/api/admin/pedidos/{P1}/estado", json={"acao": "concluir", "nota": "Testar em estrada."})
check(r.status_code == 200 and r.json()["pedido"]["estado"] == "concluido", "pedido concluído")
check(adm.post(B + f"/api/admin/pedidos/{P1}/custo", json={"tokens": 15}).status_code == 409, "custo de um pedido concluído não se altera (409)")
e = ultimo_email("a@teste.pt", f"Ficheiro pronto: pedido n.º {P1}")
check(e is not None and "golf_stage1.bin" in (e["anexos"] or ""), "entrega por email: o ficheiro modificado segue em anexo")
r = sa.get(B + f"/api/pedidos/{P1}/modificado")
check(r.status_code == 200 and r.content == modificado and "attachment" in r.headers.get("Content-Disposition", ""), "oficina descarrega o ficheiro modificado (bytes iguais)")

# Cancelamento antes do ficheiro: devolve os 5 tokens uma só vez
adm.post(B + f"/api/admin/oficinas/{ID_A}/tokens", json={"tokens": 10, "referencia": "FT 2026/4"})
r = sa.post(B + "/api/pedidos", json=dict(pedido, matricula="1234 bcd"))
P2 = r.json()["pedido"]["id"]
check(r.status_code == 201 and r.json()["saldo"] == 7, "novo pedido: descontados 5, saldo 7")
check(r.json()["pedido"]["matricula"] == "1234 BCD", "matrícula estrangeira aceite como está, em maiúsculas: 1234 BCD")
r = sa.post(B + f"/api/pedidos/{P2}/cancelar", json={})
check(r.status_code == 200 and r.json()["saldo"] == 12, "cancelado antes do ficheiro: 5 tokens devolvidos (saldo 12)")
r = sa.post(B + f"/api/pedidos/{P2}/cancelar", json={})
check(r.status_code == 409 and saldo_a() == 12, "segundo cancelamento recusado, sem devolução duplicada")

# Recusa pelo administrador: devolve todos os tokens pagos, uma só vez
r = sa.post(B + "/api/pedidos", json=pedido)
P3 = r.json()["pedido"]["id"]
sa.post(B + f"/api/pedidos/{P3}/original", files={"ficheiro": ("c.bin", b"abc" * 1000)})
r = adm.post(B + f"/api/admin/pedidos/{P3}/custo", json={"tokens": 8})
check(r.status_code == 200 and r.json()["pedido"]["pagos"] == 8 and saldo_a() == 4, "custo final 8 com saldo suficiente: diferença descontada logo (saldo 4)")
check(ultimo_email("a@teste.pt", f"Pedido n.º {P3}: custo final") is not None, "oficina avisada do custo final")
r = adm.post(B + f"/api/admin/pedidos/{P3}/estado", json={"acao": "recusar"})
check(r.status_code == 400, "recusar sem motivo: 400")
r = adm.post(B + f"/api/admin/pedidos/{P3}/estado", json={"acao": "recusar", "nota": "ECU sem suporte."})
check(r.status_code == 200 and r.json()["pedido"]["estado"] == "recusado" and saldo_a() == 12, "pedido recusado: os 8 tokens pagos voltam ao saldo (12)")
r = adm.post(B + f"/api/admin/pedidos/{P3}/estado", json={"acao": "recusar", "nota": "outra vez"})
check(r.status_code == 409 and saldo_a() == 12, "segunda recusa recusada, sem devolução duplicada")
check(ultimo_email("a@teste.pt", f"Pedido n.º {P3} recusado") is not None, "oficina avisada da recusa com o motivo")

# Concorrência: dois pedidos ao mesmo tempo com saldo 7 (só chega para um)
adm.post(B + f"/api/admin/oficinas/{ID_A}/tokens", json={"tokens": -5, "referencia": "Acerto de teste"})
resultados = []
def criar():
    resultados.append(sa.post(B + "/api/pedidos", json=pedido).status_code)
ts = [threading.Thread(target=criar) for _ in range(2)]
[t.start() for t in ts]
[t.join() for t in ts]
check(sorted(resultados) == [201, 402] and saldo_a() == 2, f"dois pedidos em simultâneo: só um passa {sorted(resultados)}, saldo 2")

# Limites de ficheiro
r = sa.get(B + "/api/pedidos").json()["pedidos"]
P4 = [p for p in r if p["estado"] == "a_aguardar_ficheiro"][0]["id"]
r = sa.post(B + f"/api/pedidos/{P4}/original", files={"ficheiro": ("vazio.bin", b"")})
check(r.status_code == 400, "ficheiro vazio: 400")
r = sa.post(B + f"/api/pedidos/{P4}/original", files={"ficheiro": ("grande.bin", b"0" * (26 * 1024 * 1024))})
check(r.status_code == 413, "ficheiro com mais de 25 MB: 413 (" + r.json()["erro"][:60] + ")")

# Entrega por WhatsApp; concluir sem definir o custo aceita os 5 tokens pagos
adm.post(B + f"/api/admin/oficinas/{ID_B}/tokens", json={"tokens": 5, "referencia": "FT 2026/2"})
r = sb.post(B + "/api/pedidos", json=dict(pedido, modulos=["DPF OFF"], declaracao=True, entrega="whatsapp", whatsapp=""))
PB = r.json()["pedido"]["id"]
check(r.status_code == 201 and r.json()["pedido"]["whatsapp"] == "923 456 789", "pedido com entrega por WhatsApp usa o número da conta")
sb.post(B + f"/api/pedidos/{PB}/original", files={"ficheiro": ("clio.bin", b"1" * 5000)})
adm.post(B + f"/api/admin/pedidos/{PB}/modificado", files={"ficheiro": ("clio_mod.bin", b"2" * 5000)})
r = adm.post(B + f"/api/admin/pedidos/{PB}/estado", json={"acao": "concluir"})
j = r.json()["pedido"]
url = j.get("whatsapp_url") or ""
check(url.startswith("https://wa.me/351923456789?text="), "concluído por WhatsApp: ligação wa.me com o número e a mensagem")
check(j["custo_definido"] is True and j["tokens"] == 5, "concluir sem definir o custo: fica o custo de 5 tokens já pago")

# Prazos de conservação (1 mês). Precisa de acesso direto à base de dados de teste, para recuar as datas:
# GARC_TESTE_SQL="mysql garc_teste" e GARC_TESTE_FICHEIROS=<pasta dos ficheiros da configuração de teste>.
SQL = os.environ.get("GARC_TESTE_SQL")
PASTA = os.environ.get("GARC_TESTE_FICHEIROS")
if SQL and PASTA:
    import shlex
    import subprocess
    subprocess.run(shlex.split(SQL) + ["-e",
        f"UPDATE pedidos SET fechado_em = UTC_TIMESTAMP() - INTERVAL 40 DAY WHERE id = {P1};"
        f"UPDATE pedidos SET criado_em = UTC_TIMESTAMP() - INTERVAL 40 DAY WHERE id = {P4};"], check=True)
    marca = os.path.join(PASTA, ".limpeza")
    if os.path.exists(marca):
        os.remove(marca)
    antes = saldo_a()
    check(adm.get(B + "/api/admin/resumo").status_code == 200, "painel aberto: corre a limpeza dos prazos")
    j = sa.get(B + f"/api/pedidos/{P1}").json()["pedido"]
    restantes = [f for _, _, fs in os.walk(os.path.join(PASTA, "pedidos", str(P1))) for f in fs]
    check(j["ficheiros_apagados"] is True and restantes == [], "um mês depois de fechado, os ficheiros do pedido são apagados do disco")
    check(sa.get(B + f"/api/pedidos/{P1}/modificado").status_code == 410, "descarregar um ficheiro já apagado: 410")
    j4 = sa.get(B + f"/api/pedidos/{P4}").json()["pedido"]
    check(j4["estado"] == "cancelado" and saldo_a() == antes + 5, "pedido sem ficheiro há um mês: cancelado e os 5 tokens devolvidos")
else:
    print("(prazos de conservação não testados: definir GARC_TESTE_SQL e GARC_TESTE_FICHEIROS)")

# Códigos de acesso: tentativas e limite de pedidos
sx = sessao()
sx.post(B + "/api/entrar/codigo", json={"email": "b@teste.pt"})
codigo = re.search(r"(\d{6})", ultimo_email("b@teste.pt", "Código de acesso")["assunto"]).group(1)
errado = "000000" if codigo != "000000" else "111111"
for _ in range(5):
    sx.post(B + "/api/entrar/verificar", json={"email": "b@teste.pt", "codigo": errado})
r = sx.post(B + "/api/entrar/verificar", json={"email": "b@teste.pt", "codigo": codigo})
check(r.status_code == 400, "depois de 5 tentativas erradas, o código certo já não entra")
r2 = sx.post(B + "/api/entrar/codigo", json={"email": "b@teste.pt"})
r3 = sx.post(B + "/api/entrar/codigo", json={"email": "b@teste.pt"})
r4 = sx.post(B + "/api/entrar/codigo", json={"email": "b@teste.pt"})
check([r2.status_code, r3.status_code, r4.status_code] == [200, 200, 429], "três códigos em 15 minutos; o quarto pedido recebe 429")
r = sessao().post(B + "/api/entrar/codigo", json={"email": "ninguem@teste.pt"})
check(r.status_code == 200, "email sem conta recebe a mesma resposta (não revela contas)")

# Suspensão termina as sessões
r = adm.post(B + f"/api/admin/oficinas/{ID_B}/estado", json={"estado": "suspensa"})
check(r.status_code == 200 and sb.get(B + "/api/sessao").json()["email"] is None, "conta suspensa: sessão da oficina terminada")

# Conta e contacto
r = sa.post(B + "/api/conta", json={"telefone": "910 000 000", "whatsapp": "", "entrega": "portal"})
check(r.status_code == 200 and r.json()["oficina"]["entrega"] == "portal", "oficina altera telefone e entrega preferida")
r = sessao().post(B + "/api/contacto", data={"nome": "Carlos", "apelido": "Teste", "email": "carlos@teste.pt", "telefone": "",
                                              "assunto": "Dúvida\r\nBcc: x@mal.example", "mensagem": "Olá", "privacidade": "sim"})
e = ultimo_email("admin@teste.pt", "Contacto do site")
check(r.status_code == 200 and e is not None, "formulário de contacto entregue ao administrador")

# Dados da oficina: a oficina só altera telefone, WhatsApp e entrega; o resto só o administrador
r = sa.post(B + "/api/conta", json={"telefone": "910 000 001", "whatsapp": "", "entrega": "portal",
                                     "nome": "Outro nome", "nif": NIF_B, "responsavel": "Outra", "email": "x@teste.pt"})
j = r.json().get("oficina", {})
check(r.status_code == 200 and j.get("telefone") == "910 000 001" and j.get("nome") == "Oficina A, Lda" and j.get("nif") == NIF_A
      and j.get("responsavel") == "Ana A" and j.get("email") == "a@teste.pt",
      "na área de cliente, a oficina altera o telefone, mas não o nome, o NIF, o responsável nem o email")
o_a = adm.get(B + f"/api/admin/oficinas/{ID_A}").json()["oficina"]
atual = {k: o_a[k] or "" for k in ("nome", "nif", "responsavel", "email", "telefone", "whatsapp", "entrega")}
r = sa.post(B + f"/api/admin/oficinas/{ID_A}/dados", json=dict(atual, nome="Pirata"))
check(r.status_code == 403, "a oficina não usa a alteração de dados do painel (403)")
antes = [e["id"] for e in emails()]
r = adm.post(B + f"/api/admin/oficinas/{ID_A}/dados", json=atual)
check(r.status_code == 200 and r.json()["alterados"] == [] and [e["id"] for e in emails()] == antes,
      "dados iguais: nada muda e não sai nenhum email")
for alteracao, codigo_http, texto_erro, msg in [
    ({"nif": "123456788"}, 400, "NIF", "NIF inválido é recusado"),
    ({"nif": NIF_B}, 409, "NIF", "NIF de outra oficina: 409"),
    ({"email": "b@teste.pt"}, 409, "email", "email de outra oficina: 409"),
    ({"email": "ADMIN@teste.pt"}, 400, "administração", "email de administração não pode ficar numa oficina"),
    ({"email": "sem-arroba"}, 400, "email", "email inválido é recusado"),
    ({"nome": " "}, 400, "oficina", "nome vazio é recusado"),
    ({"telefone": ""}, 400, "telefone", "telefone vazio é recusado"),
    ({"entrega": "pombo"}, 400, "receber", "forma de entrega inválida é recusada"),
]:
    r = adm.post(B + f"/api/admin/oficinas/{ID_A}/dados", json=dict(atual, **alteracao))
    check(r.status_code == codigo_http and texto_erro in r.json().get("erro", ""), msg + f" ({r.status_code})")
r = adm.post(B + "/api/admin/oficinas/999999/dados", json=atual)
check(r.status_code == 404, "oficina inexistente: 404")
check(adm.get(B + f"/api/admin/oficinas/{ID_A}").json()["oficina"]["nome"] == "Oficina A, Lda", "alterações recusadas não mudam nada")

NIF_A2 = nif("50100000")
atual.update(nome="Oficina A Renovada, Lda", nif=NIF_A2, responsavel="Ana Antunes", whatsapp="930 000 000", entrega="whatsapp")
r = adm.post(B + f"/api/admin/oficinas/{ID_A}/dados", json=atual)
j = r.json()
check(r.status_code == 200 and j["oficina"]["nome"] == "Oficina A Renovada, Lda" and j["oficina"]["nif"] == NIF_A2
      and j["oficina"]["responsavel"] == "Ana Antunes" and j["oficina"]["whatsapp"] == "930 000 000" and j["oficina"]["entrega"] == "whatsapp"
      and j["alterados"] == ["nome", "nif", "responsavel", "whatsapp", "entrega"],
      "administrador altera o nome, o NIF, o responsável, o WhatsApp e a entrega")
e = ultimo_email("a@teste.pt", "Dados da conta atualizados")
check(e is not None and f"NIF: {NIF_A2}" in e["texto"] and "Entrega preferida: WhatsApp" in e["texto"] and "Telefone" not in e["texto"],
      "a oficina é avisada por email só com os dados alterados")
check(sa.get(B + "/api/sessao").json()["oficina"]["nome"] == "Oficina A Renovada, Lda", "sem mudança de email, a sessão continua e já mostra o nome novo")
lista = {o["id"]: o for o in adm.get(B + "/api/admin/oficinas?filtro=todas").json()["oficinas"]}
check(lista[ID_A]["nome"] == "Oficina A Renovada, Lda" and lista[ID_A]["nif"] == NIF_A2, "a lista de oficinas mostra o nome e o NIF novos")
r = adm.post(B + f"/api/admin/oficinas/{ID_A}/dados", json=dict(atual, whatsapp=""))
check(r.status_code == 200 and r.json()["oficina"]["whatsapp"] is None and r.json()["alterados"] == ["whatsapp"]
      and "WhatsApp: o mesmo do telefone" in ultimo_email("a@teste.pt", "Dados da conta atualizados")["texto"],
      "WhatsApp apagado: passa a usar o telefone")
atual["whatsapp"] = ""

# Mudança de email: o antigo deixa de entrar, as sessões terminam e os dois emails são avisados
r = adm.post(B + f"/api/admin/oficinas/{ID_A}/dados", json=dict(atual, email=" A2@Teste.pt "))
check(r.status_code == 200 and r.json()["oficina"]["email"] == "a2@teste.pt" and r.json()["alterados"] == ["email"],
      "email da oficina alterado (guardado em minúsculas)")
check(sa.get(B + "/api/sessao").json()["email"] is None, "a mudança de email termina a sessão aberta da oficina")
e_antigo = ultimo_email("a@teste.pt", "Email de acesso alterado")
check(e_antigo is not None and "a2@teste.pt" not in e_antigo["texto"], "o email antigo é avisado, sem revelar o email novo")
check(ultimo_email("a2@teste.pt", "Dados da conta atualizados") is not None, "o email novo recebe o aviso com os dados")
antes = [e["id"] for e in emails()]
r = sessao().post(B + "/api/entrar/codigo", json={"email": "a@teste.pt"})
check(r.status_code == 200 and not [e for e in emails() if e["id"] not in antes], "o email antigo já não recebe código de acesso")
s_a2 = sessao()
r = entrar(s_a2, "a2@teste.pt")
check(r.status_code == 200 and r.json()["oficina"]["id"] == ID_A, "a oficina entra com o email novo e mantém a mesma conta")
check(s_a2.get(B + "/api/saldo").json()["saldo"] == adm.get(B + f"/api/admin/oficinas/{ID_A}").json()["saldo"], "o saldo da conta mantém-se")

# Repõe o email da oficina A para os testes seguintes
r = adm.post(B + f"/api/admin/oficinas/{ID_A}/dados", json=dict(atual, email="a@teste.pt"))
check(r.status_code == 200 and s_a2.get(B + "/api/sessao").json()["email"] is None, "email reposto: a sessão com o email anterior termina")
check(entrar(sa, "a@teste.pt").status_code == 200, "a oficina volta a entrar com o email reposto")

# Saída
r = sa.post(B + "/api/sessao/sair", json={})
check(r.status_code == 200 and sa.get(B + "/api/sessao").json()["email"] is None, "sair termina a sessão")

# Extrato coerente com o saldo
movs = adm.get(B + f"/api/admin/oficinas/{ID_A}").json()
check(sum(m["tokens"] for m in movs["movimentos"]) == movs["saldo"], f"extrato soma o saldo ({movs['saldo']} tokens)")

def id_oficina(email):
    return [o for o in adm.get(B + "/api/admin/oficinas?filtro=todas").json()["oficinas"] if o["email"] == email][0]["id"]


# ---------------------------------------------------------------- pedido personalizado
check(sessao().post(B + "/api/registo", json=dict(reg, email="p@teste.pt", nome="Oficina P", nif=nif("56000000"))).status_code == 201,
      "registo da oficina P")
ID_P = id_oficina("p@teste.pt")
adm.post(B + f"/api/admin/oficinas/{ID_P}/estado", json={"estado": "aprovada"})
adm.post(B + f"/api/admin/oficinas/{ID_P}/tokens", json={"tokens": 15, "referencia": "FT P"})
sp = sessao()
entrar(sp, "p@teste.pt")
pers = dict(pedido, modulos=["PERSONALIZADO"], personalizado="", personalizado_emissoes=False)
r = sp.post(B + "/api/pedidos", json=pers)
check(r.status_code == 400 and "pedido personalizado" in r.json()["erro"], "pedido personalizado sem descrição é recusado")
r = sp.post(B + "/api/pedidos", json=dict(pers, personalizado="x" * 1001))
check(r.status_code == 400 and "1000" in r.json()["erro"], "descrição com mais de 1000 caracteres é recusada")
r = sp.post(B + "/api/pedidos", json=dict(pers, personalizado="  Desativar o código P0420 e ajustar o ralenti para 850 rpm.  "))
j = r.json().get("pedido", {})
check(r.status_code == 201 and j.get("modulos") == ["PERSONALIZADO"] and j.get("declaracao_emissoes") is False
      and j.get("personalizado") == "Desativar o código P0420 e ajustar o ralenti para 850 rpm.",
      "pedido personalizado aceite, com a descrição guardada e sem declaração de emissões")
PP1 = j.get("id")
r = sp.post(B + "/api/pedidos", json=dict(pers, personalizado="NOx off", personalizado_emissoes=True))
check(r.status_code == 400 and "declaração" in r.json()["erro"], "personalizado que envolve emissões exige a declaração")
r = sp.post(B + "/api/pedidos", json=dict(pers, personalizado="NOx off", personalizado_emissoes=True, declaracao=True))
check(r.status_code == 201 and r.json()["pedido"]["declaracao_emissoes"] is True, "com a declaração, o personalizado de emissões é aceite e fica registada")
r = sp.post(B + "/api/pedidos", json=dict(pedido, personalizado="ignorado", personalizado_emissoes=True))
check(r.status_code == 201 and r.json()["pedido"]["personalizado"] is None and r.json()["pedido"]["declaracao_emissoes"] is False,
      "sem o módulo personalizado, a descrição e a caixa de emissões são ignoradas")
sp.post(B + f"/api/pedidos/{PP1}/original", files={"ficheiro": ("p ori.bin", b"p" * 1024)})
e = ultimo_email("admin@teste.pt", f"Novo pedido n.º {PP1}")
check(e is not None and "Módulos: Pedido personalizado" in e["texto"]
      and "Pedido personalizado:\nDesativar o código P0420" in e["texto"], "o email do novo pedido traz a descrição do personalizado")
r = adm.get(B + f"/api/admin/pedidos/{PP1}")
check(r.status_code == 200 and r.json()["pedido"]["personalizado"].startswith("Desativar o código P0420"), "o painel recebe a descrição")
meus = {p["id"]: p for p in sp.get(B + "/api/pedidos").json()["pedidos"]}
check(meus[PP1]["personalizado"].startswith("Desativar"), "a oficina vê a descrição nos seus pedidos")

# ---------------------------------------------------------------- apagar conta


# Registo sem histórico (ex.: recusado): apaga-se logo e o email e o NIF ficam livres
NIF_E = nif("55000000")
reg_e = dict(reg, email="e@teste.pt", nome="Oficina E", nif=NIF_E)
check(sessao().post(B + "/api/registo", json=reg_e).status_code == 201, "registo da oficina E (sem histórico)")
ID_E = id_oficina("e@teste.pt")
adm.post(B + f"/api/admin/oficinas/{ID_E}/estado", json={"estado": "recusada"})
j = adm.get(B + f"/api/admin/oficinas/{ID_E}").json()
check(j["pedidos_total"] == 0 and j["pedidos_por_fechar"] == 0 and j["saldo"] == 0, "ficha indica 0 pedidos, nenhum por fechar e saldo 0")
s_of = sessao()
entrar(s_of, "a@teste.pt")
check(s_of.post(B + f"/api/admin/oficinas/{ID_E}/apagar", json={}).status_code == 403, "uma oficina não apaga contas (403)")
check(sessao().post(B + f"/api/admin/oficinas/{ID_E}/apagar", json={}).status_code == 401, "sem sessão também não (401)")
r = adm.post(B + f"/api/admin/oficinas/{ID_E}/apagar", json={})
check(r.status_code == 200 and r.json()["apagada"] == {"id": ID_E, "nome": "Oficina E", "pedidos": 0, "movimentos": 0},
      "conta sem histórico apagada")
check(adm.get(B + f"/api/admin/oficinas/{ID_E}").status_code == 404, "a ficha apagada já não existe (404)")
check(adm.post(B + f"/api/admin/oficinas/{ID_E}/apagar", json={}).status_code == 404, "apagar outra vez: 404")
check(sessao().post(B + "/api/registo", json=reg_e).status_code == 201, "depois de apagada, o mesmo email e NIF podem registar-se de novo")

# Conta com pedidos, ficheiros e extrato: só se apaga com saldo 0 e sem pedidos por fechar
ID_E2 = id_oficina("e@teste.pt")
adm.post(B + f"/api/admin/oficinas/{ID_E2}/estado", json={"estado": "aprovada"})
adm.post(B + f"/api/admin/oficinas/{ID_E2}/tokens", json={"tokens": 12, "referencia": "FT teste"})
se = sessao()
check(entrar(se, "e@teste.pt").status_code == 200, "oficina E aprovada entra, com 12 tokens")
PE1 = se.post(B + "/api/pedidos", json=pedido).json()["pedido"]["id"]
se.post(B + f"/api/pedidos/{PE1}/original", files={"ficheiro": ("e ori.bin", b"o" * 2048)})
adm.post(B + f"/api/admin/pedidos/{PE1}/modificado", files={"ficheiro": ("e mod.bin", b"m" * 2048)})
adm.post(B + f"/api/admin/pedidos/{PE1}/estado", json={"acao": "concluir"})
PE2 = se.post(B + "/api/pedidos", json=pedido).json()["pedido"]["id"]
j = adm.get(B + f"/api/admin/oficinas/{ID_E2}").json()
check(j["pedidos_total"] == 2 and j["pedidos_por_fechar"] == 1 and j["saldo"] == 2, "ficha: 2 pedidos, 1 por fechar, saldo 2")
r = adm.post(B + f"/api/admin/oficinas/{ID_E2}/apagar", json={})
check(r.status_code == 409 and "saldo" in r.json()["erro"] and "-2" in r.json()["erro"], "com saldo: não apaga e indica o acerto (-2)")
adm.post(B + f"/api/admin/oficinas/{ID_E2}/tokens", json={"tokens": -2, "referencia": "Acerto para apagar"})
r = adm.post(B + f"/api/admin/oficinas/{ID_E2}/apagar", json={})
check(r.status_code == 409 and "1 pedido por fechar" in r.json()["erro"], "com um pedido por fechar: não apaga")
check(adm.get(B + f"/api/admin/pedidos/{PE1}").status_code == 200 and se.get(B + "/api/sessao").json()["email"] == "e@teste.pt",
      "as recusas não apagam nada nem terminam a sessão")
adm.post(B + f"/api/admin/pedidos/{PE2}/estado", json={"acao": "recusar", "nota": "Conta a fechar."})
adm.post(B + f"/api/admin/oficinas/{ID_E2}/tokens", json={"tokens": -5, "referencia": "Devolução acertada"})
r = adm.post(B + f"/api/admin/oficinas/{ID_E2}/apagar", json={})
a = r.json().get("apagada", {})
check(r.status_code == 200 and a.get("pedidos") == 2 and a.get("movimentos") == 6, f"conta com 2 pedidos e 6 movimentos apagada ({a})")
check(adm.get(B + f"/api/admin/pedidos/{PE1}").status_code == 404 and adm.get(B + f"/api/admin/pedidos/{PE2}").status_code == 404,
      "os pedidos da conta apagada já não existem")
check(se.get(B + "/api/sessao").json()["email"] is None, "a sessão da oficina apagada terminou")
antes = [e["id"] for e in emails()]
sessao().post(B + "/api/entrar/codigo", json={"email": "e@teste.pt"})
check(not [e for e in emails() if e["id"] not in antes], "o email da conta apagada não recebe código nem aviso")
if PASTA:
    check(not (Path(PASTA) / "pedidos" / str(PE1)).exists() and not (Path(PASTA) / "pedidos" / str(PE2)).exists(),
          "as pastas dos ficheiros dos pedidos foram apagadas")
check(adm.post(B + "/api/admin/oficinas/999999/apagar", json={}).status_code == 404, "oficina inexistente: 404")

# ---------------------------------------------------------------- limites por IP
# Em desenvolvimento só há limite quando o pedido indica um IP no cabeçalho X-Teste-IP.
def com_ip(ip):
    s = sessao()
    s.headers["X-Teste-IP"] = ip
    return s


s_ip = com_ip("203.0.113.10")
regs = [s_ip.post(B + "/api/registo", json=dict(reg, email=f"lim{i}@teste.pt", nome=f"Oficina L{i}", nif=nif(f"5200000{i}"))).status_code
        for i in range(5)]
r = s_ip.post(B + "/api/registo", json=dict(reg, email="lim9@teste.pt", nome="Oficina L9", nif=nif("52000009")))
check(regs == [201] * 5 and r.status_code == 429, f"registo: 5 por hora por IP, o sexto recebe 429 {regs + [r.status_code]}")
r = com_ip("203.0.113.11").post(B + "/api/registo", json=dict(reg, email="lim9@teste.pt", nome="Oficina L9", nif=nif("52000009")))
check(r.status_code == 201, "registo a partir de outro IP continua aceite")

dados_c = {"nome": "Robô", "apelido": "", "email": "r@teste.pt", "telefone": "", "assunto": "", "mensagem": "Olá", "privacidade": "sim"}
s_c = com_ip("203.0.113.20")
cs = [s_c.post(B + "/api/contacto", data=dados_c).status_code for _ in range(6)]
check(cs == [200] * 5 + [429], f"contacto: 5 por hora por IP, a sexta mensagem recebe 429 {cs}")
antes = [e["id"] for e in emails()]
r = com_ip("203.0.113.21").post(B + "/api/contacto", data=dict(dados_c, website="http://spam.example"))
check(r.status_code == 200 and [e["id"] for e in emails()] == antes, "contacto com o campo-armadilha preenchido: resposta normal, sem email")

s_k = com_ip("203.0.113.30")
ks = [s_k.post(B + "/api/entrar/codigo", json={"email": f"k{i}@teste.pt"}).status_code for i in range(11)]
check(ks == [200] * 10 + [429], f"códigos de entrada: 10 em 15 minutos por IP, o 11.º recebe 429 {ks}")

# ---------------------------------------------------------------- conteúdos alteráveis (garc-conteudos)
# Precisa da pasta usada pelo servidor de teste: GARC_TESTE_CONTEUDOS=<a mesma pasta de GARC_CONTEUDOS>.
CONT = os.environ.get("GARC_TESTE_CONTEUDOS")
r = requests.get(B + "/servicos")
check(r.status_code == 200 and "Horário de atendimento: <strong>8h30–17h00</strong>" in r.text, "Serviços mostra o horário do ficheiro de dados")
r = requests.get(B + "/precos", allow_redirects=False)
check(r.status_code == 301 and r.headers.get("Location") == "/area-cliente#precos", "/precos leva à área de cliente (301)")
r = requests.get(B + "/servicos.html", allow_redirects=False)
check(r.status_code == 301 and r.headers.get("Location") == "/servicos", "servicos.html antigo leva a /servicos (301)")
html_area = requests.get(B + "/area-cliente").text
check("6,00" not in html_area and "data-preco=\"token_txt\"" in html_area and '"minimo"' not in html_area,
      "a página da área de cliente não traz valores de preço no HTML")
check("precos" not in requests.get(B + "/api/sessao").json(), "sem sessão: a API não envia preços")
sm = sessao()
sm.post(B + "/api/registo", json=dict(reg, email="m@teste.pt", nome="Oficina M", nif=nif("54000000")))
pm = {o["email"]: o for o in adm.get(B + "/api/admin/oficinas?filtro=pendente").json()["oficinas"]}
adm.post(B + f"/api/admin/oficinas/{pm['m@teste.pt']['id']}/estado", json={"estado": "aprovada"})
r = entrar(sm, "m@teste.pt")
check(r.json().get("precos", {}).get("token_txt") == "6,00 €", "conta aprovada recebe os preços ao entrar")
pr = sm.get(B + "/api/sessao").json().get("precos", {})
check(pr.get("token_txt") == "6,00 €" and "tabela" not in pr, "e com a sessão: só o preço de 1 token, sem tabela de carregamentos")
check(adm.get(B + "/api/sessao").json().get("precos", {}).get("minimo") == 5, "o administrador recebe o mínimo em vigor")
if CONT:
    dados = Path(CONT) / "dados.txt"
    check(dados.is_file() and (Path(CONT) / "noticias" / "_como-escrever-uma-noticia.txt").is_file(),
          "a pasta garc-conteudos foi criada com os valores de origem e as instruções das notícias")
    original = dados.read_text(encoding="utf-8")
    alterado = (original.replace("token: 6,00", "token: 7,50").replace("minimo: 5", "minimo: 6")
                .replace("horario: 8h30–17h00", "horario: 9h00–18h00").replace("paypal: jraulsoares", "paypal:")
                .replace("cartao:", "cartao: https://buy.stripe.com/teste"))
    dados.write_text(alterado, encoding="utf-8")
    p = sm.get(B + "/api/sessao").json()["precos"]
    check(p["token_txt"] == "7,50 €" and p["minimo"] == 6,
          f"preço do token e mínimo alterados no ficheiro valem logo ({p['token_txt']}, {p['minimo']})")
    check([m["tipo"] for m in p["pagamentos"]] == ["mbway", "cartao"], "PayPal vazio deixa de aparecer; cartão aparece com a ligação")
    check("9h00–18h00" in requests.get(B + "/servicos").text, "horário alterado aparece em Serviços")
    check("MB WAY ou cartão" in requests.get(B + "/termos").text, "Termos mostram os meios de pagamento em vigor")
    r = sm.post(B + "/api/pedidos", json=pedido)
    check(r.status_code == 402 and r.json().get("custo") == 6, "o envio de pedidos usa o mínimo do ficheiro (6)")
    dados.write_text(alterado.replace("token: 7,50", "token: sete"), encoding="utf-8")
    check(sm.get(B + "/api/sessao").json()["precos"]["token_txt"] == "6,00 €", "valor inválido no ficheiro: usa o de origem")
    dados.write_text(original, encoding="utf-8")
    nd = Path(CONT) / "noticias"
    (nd / "zz-teste.txt").write_text("Título: Novidade de teste\nData: 31/12/2030\n\nTexto com https://www.autosolutions.pt.\n\n- um\n- dois\n", encoding="utf-8")
    (nd / "_rascunho.txt").write_text("Título: Rascunho escondido\nData: 01/01/2031\n\nNão publicar.\n", encoding="utf-8")
    t = requests.get(B + "/noticias").text
    check("Novidade de teste" in t and t.index("Novidade de teste") < t.index("Stage 1 e Stage 2"), "notícia nova aparece em primeiro")
    check("Rascunho escondido" not in t, "ficheiros começados por _ não aparecem")
    check('<a href="https://www.autosolutions.pt" target="_blank" rel="noopener">' in t and "<li>dois</li>" in t,
          "endereços ficam com ligação e as linhas com hífen ficam em lista")
    (nd / "zz-teste.txt").unlink()
    (nd / "_rascunho.txt").unlink()
else:
    print("(conteúdos: sem GARC_TESTE_CONTEUDOS, só as verificações sem alterar ficheiros)")

print(f"\n{sum(RES)}/{len(RES)} verificações passaram")
sys.exit(0 if all(RES) else 1)
