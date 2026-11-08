"""Testes de integração da API da área de cliente (servidor local com MariaDB)."""
import os
import re
import sys
import threading

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
pedido = {"viatura": "Volkswagen Golf VII", "motor": "2.0 TDI", "ano": "2017", "ecu": "Bosch EDC17C64",
          "ferramenta": "KESS3", "metodo": "OBD", "modulos": ["STAGE 1/2"], "observacoes": "", "entrega": "email",
          "whatsapp": "", "declaracao": False, "tamanho": 100000}
r = sa.post(B + "/api/pedidos", json=pedido)
check(r.status_code == 402 and r.json().get("saldo") == 0 and r.json().get("custo") == 4, "sem saldo: pedido recusado com 402 (custo 4, saldo 0)")

r = adm.post(B + f"/api/admin/oficinas/{ID_A}/tokens", json={"tokens": 10, "referencia": "FT 2026/1"})
check(r.status_code == 200 and r.json()["saldo"] == 10, "administrador carrega 10 tokens (saldo 10)")
check(ultimo_email("a@teste.pt", "Saldo carregado") is not None, "oficina avisada do carregamento")
r = adm.post(B + f"/api/admin/oficinas/{ID_A}/tokens", json={"tokens": -11})
check(r.status_code == 409, "acerto que deixaria o saldo negativo é recusado")

r = sa.post(B + "/api/pedidos", json=dict(pedido, modulos=["STAGE 1/2", "EGR OFF"]))
check(r.status_code == 400 and "declaração" in r.json()["erro"], "módulo de emissões sem declaração: recusado")
r = sa.post(B + "/api/pedidos", json=dict(pedido, modulos=["STAGE 1/2", "EGR OFF", "NAO EXISTE"], declaracao=True))
check(r.status_code == 400, "módulo desconhecido: recusado")
r = sa.post(B + "/api/pedidos", json=dict(pedido, modulos=["STAGE 1/2", "EGR OFF"], declaracao=True))
check(r.status_code == 201 and r.json()["saldo"] == 5 and r.json()["pedido"]["tokens"] == 5, "pedido Stage 1 + EGR off criado: 5 tokens, saldo 5")
P1 = r.json()["pedido"]["id"]

original = os.urandom(150_000)
r = sa.post(B + f"/api/pedidos/{P1}/original", files={"ficheiro": ("golf ori.bin", original, "application/octet-stream")})
check(r.status_code == 200 and r.json()["pedido"]["estado"] == "recebido", "ficheiro original recebido, estado 'recebido'")
check(r.json()["pedido"]["original_nome"] == "golf_ori.bin" or r.json()["pedido"]["original_nome"] == "golf ori.bin", "nome do ficheiro limpo: " + r.json()["pedido"]["original_nome"])
e = ultimo_email("admin@teste.pt", f"Novo pedido n.º {P1}")
check(e is not None and "golf" in (e["anexos"] or ""), "administrador recebe o pedido por email com o original em anexo")
r = sa.post(B + f"/api/pedidos/{P1}/original", files={"ficheiro": ("outro.bin", b"x" * 10)})
check(r.status_code == 409, "segundo envio de ficheiro no mesmo pedido: 409")

check(sb.get(B + f"/api/pedidos/{P1}").status_code == 404, "outra oficina não vê o pedido (404)")
check(sb.get(B + f"/api/pedidos/{P1}/original").status_code == 404, "outra oficina não descarrega o ficheiro (404)")
check(sa.get(B + f"/api/pedidos/{P1}/modificado").status_code == 409, "modificado indisponível antes de concluído (409)")

r = adm.get(B + "/api/admin/pedidos?filtro=tratar")
check(any(p["id"] == P1 for p in r.json()["pedidos"]), "pedido aparece em 'Por tratar'")
r = adm.get(B + f"/api/pedidos/{P1}/original")
check(r.status_code == 200 and r.content == original, "administrador descarrega o original (bytes iguais)")
r = adm.post(B + f"/api/admin/pedidos/{P1}/estado", json={"acao": "concluir"})
check(r.status_code == 409, "concluir sem ficheiro modificado: 409")
r = adm.post(B + f"/api/admin/pedidos/{P1}/estado", json={"acao": "em_curso"})
check(r.status_code == 200 and r.json()["pedido"]["estado"] == "em_curso", "pedido passa a em curso")
modificado = os.urandom(150_000)
r = adm.post(B + f"/api/admin/pedidos/{P1}/modificado", files={"ficheiro": ("golf_stage1.bin", modificado)})
check(r.status_code == 200 and r.json()["pedido"]["modificado_nome"] == "golf_stage1.bin", "administrador carrega o ficheiro modificado")
r = adm.post(B + f"/api/admin/pedidos/{P1}/estado", json={"acao": "concluir", "nota": "Testar em estrada."})
check(r.status_code == 200 and r.json()["pedido"]["estado"] == "concluido", "pedido concluído")
e = ultimo_email("a@teste.pt", f"Ficheiro pronto: pedido n.º {P1}")
check(e is not None and "golf_stage1.bin" in (e["anexos"] or ""), "entrega por email: o ficheiro modificado segue em anexo")
r = sa.get(B + f"/api/pedidos/{P1}/modificado")
check(r.status_code == 200 and r.content == modificado and "attachment" in r.headers.get("Content-Disposition", ""), "oficina descarrega o ficheiro modificado (bytes iguais)")

# Cancelamento antes do ficheiro: devolve os tokens uma só vez
r = sa.post(B + "/api/pedidos", json=pedido)
P2 = r.json()["pedido"]["id"]
check(r.status_code == 201 and r.json()["saldo"] == 1, "novo pedido de 4 tokens: saldo 1")
r = sa.post(B + f"/api/pedidos/{P2}/cancelar", json={})
check(r.status_code == 200 and r.json()["saldo"] == 5, "cancelado antes do ficheiro: tokens devolvidos (saldo 5)")
r = sa.post(B + f"/api/pedidos/{P2}/cancelar", json={})
check(r.status_code == 409 and sa.get(B + "/api/saldo").json()["saldo"] == 5, "segundo cancelamento recusado, sem devolução duplicada")

# Recusa pelo administrador: devolve os tokens uma só vez
r = sa.post(B + "/api/pedidos", json=pedido)
P3 = r.json()["pedido"]["id"]
sa.post(B + f"/api/pedidos/{P3}/original", files={"ficheiro": ("c.bin", b"abc" * 1000)})
r = adm.post(B + f"/api/admin/pedidos/{P3}/estado", json={"acao": "recusar"})
check(r.status_code == 400, "recusar sem motivo: 400")
r = adm.post(B + f"/api/admin/pedidos/{P3}/estado", json={"acao": "recusar", "nota": "ECU sem suporte."})
check(r.status_code == 200 and r.json()["pedido"]["estado"] == "recusado", "pedido recusado com motivo")
r = adm.post(B + f"/api/admin/pedidos/{P3}/estado", json={"acao": "recusar", "nota": "outra vez"})
check(r.status_code == 409 and sa.get(B + "/api/saldo").json()["saldo"] == 5, "segunda recusa recusada; saldo volta a 5, sem duplicar")
check(ultimo_email("a@teste.pt", f"Pedido n.º {P3} recusado") is not None, "oficina avisada da recusa com o motivo")

# Concorrência: dois pedidos de 4 tokens ao mesmo tempo com saldo 5
resultados = []
def criar():
    resultados.append(sa.post(B + "/api/pedidos", json=pedido).status_code)
ts = [threading.Thread(target=criar) for _ in range(2)]
[t.start() for t in ts]
[t.join() for t in ts]
check(sorted(resultados) == [201, 402] and sa.get(B + "/api/saldo").json()["saldo"] == 1, f"dois pedidos em simultâneo: só um passa {sorted(resultados)}, saldo 1")

# Limites de ficheiro
r = sa.get(B + "/api/pedidos").json()["pedidos"]
P4 = [p for p in r if p["estado"] == "a_aguardar_ficheiro"][0]["id"]
r = sa.post(B + f"/api/pedidos/{P4}/original", files={"ficheiro": ("vazio.bin", b"")})
check(r.status_code == 400, "ficheiro vazio: 400")
r = sa.post(B + f"/api/pedidos/{P4}/original", files={"ficheiro": ("grande.bin", b"0" * (26 * 1024 * 1024))})
check(r.status_code == 413, "ficheiro com mais de 25 MB: 413 (" + r.json()["erro"][:60] + ")")

# Entrega por WhatsApp
adm.post(B + f"/api/admin/oficinas/{ID_B}/tokens", json={"tokens": 5, "referencia": "FT 2026/2"})
r = sb.post(B + "/api/pedidos", json=dict(pedido, modulos=["DPF OFF"], declaracao=True, entrega="whatsapp", whatsapp=""))
PB = r.json()["pedido"]["id"]
check(r.status_code == 201 and r.json()["pedido"]["whatsapp"] == "923 456 789", "pedido com entrega por WhatsApp usa o número da conta")
sb.post(B + f"/api/pedidos/{PB}/original", files={"ficheiro": ("clio.bin", b"1" * 5000)})
adm.post(B + f"/api/admin/pedidos/{PB}/modificado", files={"ficheiro": ("clio_mod.bin", b"2" * 5000)})
r = adm.post(B + f"/api/admin/pedidos/{PB}/estado", json={"acao": "concluir"})
url = r.json()["pedido"].get("whatsapp_url") or ""
check(url.startswith("https://wa.me/351923456789?text="), "concluído por WhatsApp: ligação wa.me com o número e a mensagem")

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

# Saída
r = sa.post(B + "/api/sessao/sair", json={})
check(r.status_code == 200 and sa.get(B + "/api/sessao").json()["email"] is None, "sair termina a sessão")

# Extrato coerente com o saldo
movs = adm.get(B + f"/api/admin/oficinas/{ID_A}").json()
check(sum(m["tokens"] for m in movs["movimentos"]) == movs["saldo"], f"extrato soma o saldo ({movs['saldo']} tokens)")

print(f"\n{sum(RES)}/{len(RES)} verificações passaram")
sys.exit(0 if all(RES) else 1)
