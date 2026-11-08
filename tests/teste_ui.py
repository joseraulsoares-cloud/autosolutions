"""Teste da área de cliente e do painel no browser, contra o servidor local."""
import asyncio
import os
import re
import sys

import requests
from playwright.async_api import async_playwright

B = "http://127.0.0.1:8790"
OUT = sys.argv[1]
RES = []


def check(cond, msg):
    RES.append(bool(cond))
    print(("OK     " if cond else "FALHA  ") + msg)


def codigo(email):
    for e in requests.get(B + "/api/dev/emails").json()["emails"]:
        if e["para"] == email and e["assunto"].startswith("Código de acesso"):
            return re.search(r"(\d{6})", e["assunto"]).group(1)


def preparar_oficina():
    """Oficina C registada, aprovada e com 12 tokens (pela API)."""
    s = requests.Session()
    s.headers["Origin"] = B
    base8 = "50300400"
    soma = sum(int(c) * (9 - i) for i, c in enumerate(base8))
    nif = base8 + str(0 if soma % 11 < 2 else 11 - soma % 11)
    r = s.post(B + "/api/registo", json={"nome": "Oficina Cê", "nif": nif, "responsavel": "Carla C", "email": "c@teste.pt",
                                         "telefone": "915 000 000", "entrega": "portal", "termos": True})
    assert r.status_code in (201, 409), r.text
    a = requests.Session()
    a.headers["Origin"] = B
    a.post(B + "/api/entrar/codigo", json={"email": "admin@teste.pt"})
    a.post(B + "/api/entrar/verificar", json={"email": "admin@teste.pt", "codigo": codigo("admin@teste.pt")})
    oid = [o for o in a.get(B + "/api/admin/oficinas?filtro=todas").json()["oficinas"] if o["email"] == "c@teste.pt"][0]["id"]
    a.post(B + f"/api/admin/oficinas/{oid}/estado", json={"estado": "aprovada"})
    a.post(B + f"/api/admin/oficinas/{oid}/tokens", json={"tokens": 12, "referencia": "FT 2026/9"})


async def entrar(pg, email):
    await pg.fill("#f-entrar-email input[name=email]", email)
    await pg.click("#f-entrar-email button[type=submit]")
    await pg.wait_for_selector("#f-entrar-codigo:not([hidden])")
    await pg.fill("#f-entrar-codigo input[name=codigo]", codigo(email))
    await pg.click("#f-entrar-codigo button[type=submit]")
    await pg.wait_for_selector("#v-painel:not([hidden])")


async def main():
    preparar_oficina()
    leitura = os.path.join(OUT, "leitura_original.bin")
    with open(leitura, "wb") as f:
        f.write(os.urandom(64_000))
    modificado = os.path.join(OUT, "leitura_stage1.bin")
    with open(modificado, "wb") as f:
        f.write(os.urandom(64_000))

    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=os.environ.get("CHROME") or None, args=["--no-sandbox"])
        erros = []

        # ---------------- Oficina
        ctx = await b.new_context(viewport={"width": 1280, "height": 900})
        pg = await ctx.new_page()
        pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: erros.append(str(e)))
        await pg.goto(B + "/area-cliente#novo", wait_until="networkidle")
        check(await pg.is_visible("#v-entrar"), "sem sessão, a área de cliente mostra Entrar")
        await entrar(pg, "c@teste.pt")
        check(pg.url.endswith("#novo"), "depois de entrar, volta ao separador pedido (Novo pedido)")
        check((await pg.text_content("#p-saldo")).strip() == "12", "saldo de 12 tokens no topo")

        await pg.fill("#f-viatura", "Seat Leon III")
        await pg.fill("#f-matricula", "aa-00-aa")
        await pg.fill("#f-motor", "1.6 TDI 110 cv")
        await pg.fill("#f-ano", "2016")
        await pg.fill("#f-ecu", "Bosch EDC17C64")
        await pg.select_option("#f-metodo", "OBD")
        await pg.check("#m-stage-1-2")
        await pg.check("#m-dpf-off")
        check(await pg.is_visible("#decl-wrap"), "módulo de emissões mostra a declaração")
        check((await pg.text_content("#f-total")).strip() == "6 tokens", "total do pedido: 6 tokens")
        await pg.check("#m-adblue-scr-off")
        await pg.check("#m-pop-bangs")
        await pg.check("#m-tcu-stage-1")
        estado = await pg.get_attribute("#f-resumo", "data-estado")
        check(estado == "falta" and await pg.is_disabled("#f-enviar"), "custo de 14 tokens com saldo 12: envio bloqueado e aviso de saldo")
        await pg.uncheck("#m-adblue-scr-off")
        await pg.uncheck("#m-pop-bangs")
        await pg.uncheck("#m-tcu-stage-1")
        await pg.check("#f-declaracao")
        await pg.set_input_files("#f-ficheiro", leitura)
        await pg.screenshot(path=os.path.join(OUT, "ui-novo-pedido.png"), full_page=True)
        await pg.click("#f-enviar")
        await pg.wait_for_function("location.hash === '#pedidos'")
        await pg.wait_for_selector(".order")
        aviso = await pg.text_content("#p-aviso")
        check("enviado" in aviso, "aviso de pedido enviado: " + aviso.strip()[:60])
        check((await pg.text_content("#p-saldo")).strip() == "6", "saldo desce para 6")
        check("Recebido" in await pg.text_content(".order"), "pedido aparece na lista como Recebido")
        check("AA-00-AA" in await pg.text_content(".order"), "a lista de pedidos mostra a matrícula")
        await pg.click('a[data-tab="saldo"]')
        await pg.wait_for_selector(".ledger")
        check("FT 2026/9" in await pg.text_content(".ledger"), "extrato mostra o carregamento com a fatura")
        await pg.screenshot(path=os.path.join(OUT, "ui-saldo.png"), full_page=True)

        # ---------------- Administração
        actx = await b.new_context(viewport={"width": 1280, "height": 900})
        ap = await actx.new_page()
        ap.on("console", lambda m: erros.append("admin: " + m.text) if m.type == "error" else None)
        ap.on("pageerror", lambda e: erros.append("admin: " + str(e)))
        await ap.goto(B + "/admin", wait_until="networkidle")
        await entrar(ap, "admin@teste.pt")
        await ap.wait_for_selector("#a-pedidos .list-item")
        await ap.click("#a-pedidos .list-item:has-text('Seat Leon III')")
        await ap.wait_for_selector("#a-pedido h2")
        check("Declaração" in await ap.text_content("#a-pedido"), "painel mostra a declaração de emissões do pedido")
        check("AA-00-AA" in await ap.text_content("#a-pedido"), "painel mostra a matrícula do pedido")
        await ap.set_input_files("#a-pedido input[data-modificado]", modificado)
        await ap.wait_for_selector("#a-pedido [data-acao=concluir]")
        await ap.fill("#a-nota", "Ficheiro testado em banco.")
        await ap.click("#a-pedido [data-acao=concluir]")
        await ap.wait_for_selector("#a-pedido .pill[data-kind=ok]")
        check("concluído" in (await ap.text_content("#a-pedido .status")).lower(), "pedido concluído no painel")
        await ap.screenshot(path=os.path.join(OUT, "ui-admin.png"), full_page=True)

        # ---------------- De volta à oficina
        await pg.goto(B + "/area-cliente#pedidos", wait_until="networkidle")
        await pg.wait_for_selector(".order a[data-download]")
        async with pg.expect_download() as dl:
            await pg.click(".order a[data-download]")
        d = await dl.value
        caminho = await d.path()
        check(open(caminho, "rb").read() == open(modificado, "rb").read(), "oficina descarrega o ficheiro modificado no browser")

        # Telemóvel
        mctx = await b.new_context(viewport={"width": 390, "height": 844}, color_scheme="dark")
        await mctx.add_cookies(await ctx.cookies())
        mp = await mctx.new_page()
        await mp.goto(B + "/area-cliente#pedidos", wait_until="networkidle")
        await mp.wait_for_selector(".order")
        larg = await mp.evaluate("document.documentElement.scrollWidth - innerWidth")
        check(larg <= 0, f"telemóvel: sem deslocamento horizontal ({larg})")
        await mp.screenshot(path=os.path.join(OUT, "ui-telemovel.png"), full_page=True)

        check(not erros, "sem erros na consola: " + "; ".join(erros)[:200])
        await b.close()
    print(f"\n{sum(RES)}/{len(RES)} verificações passaram")


asyncio.run(main())
