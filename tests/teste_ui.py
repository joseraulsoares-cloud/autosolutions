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
    return a, oid


async def entrar(pg, email):
    await pg.fill("#f-entrar-email input[name=email]", email)
    await pg.click("#f-entrar-email button[type=submit]")
    await pg.wait_for_selector("#f-entrar-codigo:not([hidden])")
    await pg.fill("#f-entrar-codigo input[name=codigo]", codigo(email))
    await pg.click("#f-entrar-codigo button[type=submit]")
    await pg.wait_for_selector("#v-painel:not([hidden])")


async def main():
    adm, oid = preparar_oficina()
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
        check(await pg.locator(".nav-list a", has_text="Preços").count() == 0, "a barra pública já não tem Preços")
        await pg.click(".tabs a[data-tab=precos]")
        await pg.wait_for_selector("[data-panel=precos]:not([hidden])")
        celulas = [" ".join(t.split()) for t in await pg.locator("[data-panel=precos] .price-table tr th, [data-panel=precos] .price-table tr td").all_text_contents()]
        check(celulas == ["1 token", "6,00 €"] and await pg.locator("[data-panel=precos] .price-table tr").count() == 1,
              "separador Preços mostra só o preço de 1 token, vindo da API: " + " | ".join(celulas))
        passos = [" ".join(t.split()) for t in await pg.locator("[data-panel=precos] .custo-passos li").all_text_contents()]
        check(len(passos) == 5 and passos[0] == "No envio do ficheiro descontam-se 5 tokens do saldo, correspondentes ao serviço mínimo."
              and passos[2].startswith("Se não for possível") and passos[4].startswith("Depois de enviado"),
              "«Quanto custa cada pedido» tem os 5 passos pela ordem pedida")
        novo = [" ".join(t.split()) for t in await pg.locator("[data-panel=novo] .custo-passos li").all_text_contents()]
        titulos = [t.strip() for t in await pg.locator("[data-panel=novo] .aside h2").all_text_contents()]
        check(novo == passos and titulos == ["Quanto custa cada pedido", "Sob consulta", "Prazo de entrega"],
              "Novo pedido mostra a mesma informação do separador Preços: " + " · ".join(titulos))
        await pg.screenshot(path=os.path.join(OUT, "ui-precos.png"), full_page=True)
        check((await pg.text_content("[data-panel=precos] [data-preco=token_txt]")).strip() == "6,00 €", "1 token = 6,00 € no separador Preços")
        await pg.click(".tabs a[data-tab=saldo]")
        pagamentos = await pg.text_content("#p-pagamentos")
        check("MB WAY" in pagamentos and "paypal.me/jraulsoares" in pagamentos, "Saldo mostra os dados de pagamento (MB WAY e PayPal)")
        await pg.click(".tabs a[data-tab=novo]")
        await pg.wait_for_selector("[data-panel=novo]:not([hidden])")

        await pg.fill("#f-viatura", "Seat Leon III")
        await pg.fill("#f-matricula", "aa-00-aa")
        await pg.fill("#f-motor", "1.6 TDI 110 cv")
        await pg.fill("#f-ano", "2016")
        await pg.fill("#f-ecu", "Bosch EDC17C64")
        await pg.select_option("#f-metodo", "OBD")
        # Grupo «Serviços por ficheiro», antes de «Outros pedidos»; os outros grupos ficam como estavam
        grupos = [t.strip() for t in await pg.locator("#form-pedido .module-group h3").all_text_contents()]
        check(grupos == ["Chiptuning", "Admissão e escape", "Correções", "Sistemas de emissões", "Serviços por ficheiro", "Outros pedidos"],
              f"formulário: grupo «Serviços por ficheiro» antes de «Outros pedidos» {grupos}")
        por_ficheiro = pg.locator("#form-pedido .module-group", has=pg.locator("h3", has_text="Serviços por ficheiro"))
        nomes = [t.strip() for t in await por_ficheiro.locator("label").all_text_contents()]
        check(len(nomes) == 7 and nomes[2] == "Recuperação de software e reposição ORI" and nomes[4] == "Reset de airbag após reparação"
              and "«Outros pedidos»" in await por_ficheiro.locator("p").text_content(),
              f"«Serviços por ficheiro» com 7 serviços e a indicação das reparações com envio do módulo ({len(nomes)})")
        # Outros pedidos: a descrição só aparece (e só é obrigatória) com o pedido personalizado marcado
        check(await pg.is_hidden("#f-personalizado-wrap"), "pedido personalizado: a descrição começa escondida")
        await pg.check("#m-personalizado")
        check(await pg.is_visible("#f-personalizado-wrap") and await pg.get_attribute("#f-personalizado", "required") is not None
              and await pg.is_hidden("#decl-wrap"), "ao marcar o personalizado, aparece a descrição, obrigatória, sem declaração")
        await pg.check("#f-personalizado-emissoes")
        check(await pg.is_visible("#decl-wrap") and await pg.get_attribute("#f-declaracao", "required") is not None,
              "personalizado que envolve emissões pede a declaração")
        await pg.screenshot(path=os.path.join(OUT, "ui-personalizado.png"), full_page=True)
        await pg.uncheck("#m-personalizado")
        check(await pg.is_hidden("#f-personalizado-wrap") and await pg.is_hidden("#decl-wrap")
              and await pg.get_attribute("#f-personalizado", "required") is None, "ao desmarcar, a descrição e a declaração saem")
        await pg.check("#m-stage-1-2")
        await pg.check("#m-dpf-off")
        check(await pg.is_visible("#decl-wrap"), "módulo de emissões mostra a declaração")
        check((await pg.text_content("#f-total")).strip() == "5 tokens", "desconto no envio: 5 tokens")
        check((await pg.text_content("#f-enviar")).strip() == "Enviar pedido (5 tokens)", "botão indica os 5 tokens do envio")
        await pg.check("#f-declaracao")
        await pg.set_input_files("#f-ficheiro", leitura)
        cuidados = await pg.locator("#form-pedido li").all_text_contents()
        check(len(cuidados) == 6 and cuidados[0].startswith("Guarde sempre o original"), "o formulário mostra os 6 cuidados de leitura")
        check(await pg.evaluate("!document.getElementById('form-pedido').checkValidity() && "
                                "document.getElementById('f-cuidados').validity.valueMissing"),
              "sem o visto nos cuidados de leitura, o pedido não avança")
        await pg.check("#f-cuidados")
        await pg.screenshot(path=os.path.join(OUT, "ui-novo-pedido.png"), full_page=True)
        await pg.click("#f-enviar")
        await pg.wait_for_function("location.hash === '#pedidos'")
        await pg.wait_for_selector(".order")
        aviso = await pg.text_content("#p-aviso")
        check("enviado" in aviso, "aviso de pedido enviado: " + aviso.strip()[:60])
        check((await pg.text_content("#p-saldo")).strip() == "7", "saldo desce para 7")
        cartao = await pg.text_content(".order")
        check("Recebido" in cartao and "AA-00-AA" in cartao, "pedido na lista como Recebido, com a matrícula")
        check("provisório" in cartao, "custo provisório até à análise da ECU")
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
        texto = await ap.text_content("#a-pedido")
        check("Declaração" in texto and "AA-00-AA" in texto, "painel mostra a declaração de emissões e a matrícula")
        check("provisório" in texto, "painel indica que o custo final ainda não foi definido")

        # Custo final de 15 com saldo 7: fica à espera de saldo
        await ap.fill("#a-custo", "15")
        await ap.click("#a-pedido [data-custo]")
        await ap.wait_for_selector("#a-pedido .pill[data-kind=warn]")
        check("Falta saldo" in await ap.text_content("#a-pedido .pill") and await ap.query_selector("#a-pedido [data-acao=concluir]") is None,
              "custo 15 com saldo 7: pedido à espera de saldo, sem botão de concluir")
        await ap.screenshot(path=os.path.join(OUT, "ui-admin-falta-saldo.png"), full_page=True)

        # A oficina vê a falta de saldo. A página já estava aberta e mudar só o # não a recarrega: sem o reload,
        # o cartão podia ser lido antes de chegarem os dados novos (falhava às vezes com o PHP 7.4, mais lento).
        await pg.goto(B + "/area-cliente#pedidos")
        await pg.reload(wait_until="networkidle")
        await pg.wait_for_selector(".order")
        cartao = await pg.text_content(".order")
        check("Falta saldo" in cartao and "Faltam 10 tokens" in cartao, "oficina vê o pedido à espera de saldo: faltam 10 tokens")

        # Carregar 3 tokens (saldo 10) liquida a diferença e o pedido avança
        adm.post(B + f"/api/admin/oficinas/{oid}/tokens", json={"tokens": 3, "referencia": "FT 2026/10"})
        await ap.reload(wait_until="networkidle")
        await ap.wait_for_selector("#a-pedido h2")
        check("Em curso" in await ap.text_content("#a-pedido .pill"), "depois do carregamento, o pedido passa a em curso")
        await ap.set_input_files("#a-pedido input[data-modificado]", modificado)
        await ap.wait_for_selector("#a-pedido [data-acao=concluir]")
        await ap.fill("#a-nota", "Ficheiro testado em banco.")
        await ap.click("#a-pedido [data-acao=concluir]")
        await ap.wait_for_selector("#a-pedido .pill[data-kind=ok]")
        check("concluído" in (await ap.text_content("#a-pedido .status")).lower(), "pedido concluído no painel")
        await ap.screenshot(path=os.path.join(OUT, "ui-admin.png"), full_page=True)

        # ---------------- De volta à oficina (a página já estava em #pedidos: recarregar para ver o estado novo)
        await pg.reload(wait_until="networkidle")
        await pg.wait_for_selector(".order a[data-download]")
        async with pg.expect_download() as dl:
            await pg.click(".order a[data-download]")
        d = await dl.value
        caminho = await d.path()
        check(open(caminho, "rb").read() == open(modificado, "rb").read(), "oficina descarrega o ficheiro modificado no browser")
        check("15 tokens" in await pg.text_content(".order") and (await pg.text_content("#p-saldo")).strip() == "0",
              "pedido concluído com o custo final de 15 tokens; saldo 0")

        # Sem saldo para o mínimo: o envio fica bloqueado
        await pg.click('a[data-tab="novo"]')
        await pg.wait_for_selector("#f-resumo")
        estado = await pg.get_attribute("#f-resumo", "data-estado")
        check(estado == "falta" and await pg.is_disabled("#f-enviar") and "pelo menos 5 tokens" in await pg.text_content("#f-resumo-msg"),
              "saldo 0: envio bloqueado, com aviso de que precisa de pelo menos 5 tokens")

        # ---------------- Editar os dados da oficina no painel (a oficina vê-os na Conta)
        await ap.goto(B + f"/admin#oficina-{oid}", wait_until="networkidle")
        await ap.wait_for_selector("#a-oficina [data-editar]")
        check(await ap.is_hidden("#a-form-dados"), "ficha da oficina: o formulário de edição começa fechado")
        await ap.click("#a-oficina [data-editar]")
        check(await ap.is_visible("#a-form-dados") and await ap.input_value("#a-d-nome") == "Oficina Cê"
              and await ap.input_value("#a-d-email") == "c@teste.pt" and await ap.is_checked("#a-d-entrega-portal"),
              "Editar dados abre o formulário com os dados atuais")
        await ap.fill("#a-d-nome", "Nome a descartar")
        await ap.click("#a-form-dados [data-cancelar-dados]")
        check(await ap.is_hidden("#a-form-dados"), "Cancelar fecha o formulário")
        await ap.click("#a-oficina [data-editar]")
        check(await ap.input_value("#a-d-nome") == "Oficina Cê", "depois de cancelar, o formulário volta aos dados guardados")
        n_erros = len(erros)
        await ap.fill("#a-d-nif", "123456788")
        await ap.click("#a-form-dados button[type=submit]")
        await ap.wait_for_selector("#a-form-dados .status:not([hidden])")
        check("NIF" in await ap.text_content("#a-form-dados .status") and await ap.is_visible("#a-form-dados"),
              "NIF inválido: o erro aparece no formulário, que fica aberto")
        # A resposta 400 esperada fica registada na consola do browser; não é um erro da página.
        erros[n_erros:] = [x for x in erros[n_erros:] if "status of 400" not in x]
        await ap.click("#a-form-dados [data-cancelar-dados]")
        await ap.click("#a-oficina [data-editar]")
        await ap.fill("#a-d-nome", "Oficina Cê Renovada")
        await ap.fill("#a-d-responsavel", "Carla Costa")
        await ap.fill("#a-d-whatsapp", "936 000 000")
        await ap.check("#a-d-entrega-whatsapp")
        await ap.screenshot(path=os.path.join(OUT, "ui-admin-editar.png"), full_page=True)
        await ap.click("#a-form-dados button[type=submit]")
        await ap.wait_for_selector("#a-oficina > .status:not([hidden])")
        ficha = await ap.text_content("#a-oficina .kv")
        check("Dados guardados" in await ap.text_content("#a-oficina > .status")
              and (await ap.text_content("#a-oficina h2")).strip() == "Oficina Cê Renovada"
              and "Carla Costa" in ficha and "936 000 000" in ficha and "Entrega preferidaWhatsApp" in ficha,
              "dados guardados: a ficha mostra o nome, o responsável, o WhatsApp e a entrega novos")
        check(await ap.is_hidden("#a-form-dados"), "depois de guardar, o formulário fecha")
        # A página da oficina já estava aberta: só um novo carregamento vai buscar os dados à sessão.
        await pg.goto(B + "/area-cliente#conta")
        await pg.reload(wait_until="networkidle")
        await pg.wait_for_selector("[data-panel=conta]:not([hidden]) #p-conta-dados dd")
        conta = await pg.text_content("#p-conta-dados")
        check("Oficina Cê Renovada" in conta and "Carla Costa" in conta and await pg.input_value("#c-whatsapp") == "936 000 000"
              and await pg.is_checked("#c-entrega-whatsapp"), "a oficina vê os dados novos na Conta, sem ter de voltar a entrar")
        actel = await b.new_context(viewport={"width": 390, "height": 844})
        await actel.add_cookies(await actx.cookies())
        apt = await actel.new_page()
        await apt.goto(B + f"/admin#oficina-{oid}", wait_until="networkidle")
        await apt.click("#a-oficina [data-editar]")
        larg = await apt.evaluate("document.documentElement.scrollWidth - innerWidth")
        check(await apt.is_visible("#a-form-dados") and larg <= 0, f"telemóvel: formulário de edição sem deslocamento horizontal ({larg})")
        await apt.screenshot(path=os.path.join(OUT, "ui-admin-editar-telemovel.png"), full_page=True)
        await actel.close()

        # ---------------- Apagar conta no painel
        aviso = (await ap.text_content("#a-aviso-apagar")).strip()
        check(not await ap.is_disabled("#a-oficina [data-apagar]") and aviso.startswith("Apagar a conta apaga também 1 pedido, os ficheiros e o extrato"),
              "oficina C (saldo 0, pedido concluído): pode ser apagada e o aviso diz o que se perde")
        s = requests.Session()
        s.headers["Origin"] = B
        base8 = "50700800"
        soma = sum(int(c) * (9 - i) for i, c in enumerate(base8))
        nif_z = base8 + str(0 if soma % 11 < 2 else 11 - soma % 11)
        s.post(B + "/api/registo", json={"nome": "Oficina Zê", "nif": nif_z, "responsavel": "Zé Z", "email": "z@teste.pt",
                                         "telefone": "917 000 000", "entrega": "portal", "termos": True})
        zid = [o for o in adm.get(B + "/api/admin/oficinas?filtro=todas").json()["oficinas"] if o["email"] == "z@teste.pt"][0]["id"]
        adm.post(B + f"/api/admin/oficinas/{zid}/estado", json={"estado": "aprovada"})
        adm.post(B + f"/api/admin/oficinas/{zid}/tokens", json={"tokens": 3, "referencia": "teste"})
        await ap.goto(B + f"/admin#oficina-{zid}", wait_until="networkidle")
        await ap.wait_for_selector("#a-oficina [data-apagar]")
        check(await ap.is_disabled("#a-oficina [data-apagar]") and "carregamento de -3" in await ap.text_content("#a-aviso-apagar"),
              "com 3 tokens de saldo: Apagar conta desativado, com a indicação do acerto (-3)")
        adm.post(B + f"/api/admin/oficinas/{zid}/tokens", json={"tokens": -3, "referencia": "Acerto"})
        await ap.reload(wait_until="networkidle")
        await ap.wait_for_selector("#a-oficina [data-apagar]:not([disabled])")
        await ap.click("#a-oficina [data-apagar]")
        check((await ap.text_content("#a-oficina [data-apagar]")).strip() == "Confirmar: apagar tudo", "primeiro clique pede confirmação")
        await ap.screenshot(path=os.path.join(OUT, "ui-admin-apagar.png"), full_page=True)
        await ap.click("#a-oficina [data-apagar]")
        await ap.wait_for_selector("#a-oficina > .status[data-kind=ok]")
        check((await ap.text_content("#a-oficina > .status")).strip() == "Conta de Oficina Zê apagada, com o extrato."
              and ap.url.endswith("#oficinas"), "segundo clique apaga a conta; o painel confirma e sai da ficha")
        check(adm.get(B + f"/api/admin/oficinas/{zid}").status_code == 404, "a conta apagada já não existe no servidor")

        # ---------------- Página Serviços: um tema de cada vez, com endereço próprio
        sctx = await b.new_context(viewport={"width": 1280, "height": 900})
        sp = await sctx.new_page()
        sp.on("console", lambda m: erros.append("serviços: " + m.text) if m.type == "error" else None)
        sp.on("pageerror", lambda e: erros.append("serviços: " + str(e)))
        await sp.goto(B + "/servicos", wait_until="networkidle")
        visiveis = await sp.eval_on_selector_all("[data-tema]", "ps => ps.filter(p => !p.hidden).map(p => p.id)")
        check(visiveis == ["chiptuning"] and await sp.locator("[data-tema-link]").count() == 12
              and await sp.get_attribute("[data-tema-link][href='#chiptuning']", "aria-current") == "true",
              f"Serviços: 12 temas na lista e só o primeiro à vista ({visiveis})")
        check((await sp.text_content("[data-contador]")).strip() == "1 de 12" and not await sp.is_visible("[data-anterior]")
              and await sp.get_attribute("[data-seguinte]", "aria-label") == "Seguinte: Admissão e escape",
              "contador 1 de 12, sem Anterior no primeiro tema e Seguinte para Admissão e escape")
        check("Horário de atendimento: 8h30–17h00" in await sp.text_content(".svc-intro") and await sp.locator("text=Uso exclusivo").count() == 0,
              "horário do dados.txt na abertura e sem o aviso de competição")
        await sp.screenshot(path=os.path.join(OUT, "ui-servicos.png"), full_page=True)
        await sp.click("[data-seguinte]")
        check(sp.url.endswith("/servicos#admissao-escape") and await sp.is_visible("#admissao-escape") and await sp.is_hidden("#chiptuning")
              and (await sp.text_content("[data-contador]")).strip() == "2 de 12"
              and await sp.evaluate("document.activeElement.id") == "admissao-escape-titulo",
              "Seguinte: tema 2, com endereço próprio e o foco no título")
        await sp.click("[data-tema-link][href='#ecu']")
        check(sp.url.endswith("#ecu") and await sp.is_visible("#ecu") and (await sp.text_content("[data-contador]")).strip() == "5 de 12"
              and await sp.get_attribute("[data-tema-link][href='#ecu']", "aria-current") == "true", "lista: ECU abre o tema 5 de 12")
        colunas = await sp.eval_on_selector_all("#ecu .svc-colunas li", "ls => [...new Set(ls.map(l => Math.round(l.getBoundingClientRect().left)))].length")
        check(colunas == 2, f"lista comprida (10 itens) em duas colunas no computador ({colunas})")
        await sp.screenshot(path=os.path.join(OUT, "ui-servicos-ecu.png"))
        await sp.go_back()
        await sp.wait_for_function("location.hash === '#admissao-escape'")
        check(await sp.is_visible("#admissao-escape") and await sp.is_hidden("#ecu"), "Retroceder do browser volta ao tema anterior")
        sp2 = await sctx.new_page()  # página nova: o endereço com tema é aberto de raiz, como numa ligação
        sp2.on("pageerror", lambda e: erros.append("serviços: " + str(e)))
        await sp2.goto(B + "/servicos#profissionais", wait_until="networkidle")
        await sp2.wait_for_timeout(150)
        topo = await sp2.evaluate("document.getElementById('profissionais').getBoundingClientRect().top")
        check(await sp2.is_visible("#profissionais") and not await sp2.is_visible("[data-seguinte]")
              and (await sp2.text_content("[data-contador]")).strip() == "12 de 12" and 0 <= topo < 300,
              f"endereço /servicos#profissionais abre o último tema, à vista e sem Seguinte (topo a {topo:.0f} px)")
        await sctx.close()

        # Telemóvel: lista dos temas em cima, conteúdo numa só coluna
        stel = await b.new_context(viewport={"width": 390, "height": 844}, color_scheme="dark")
        st = await stel.new_page()
        await st.goto(B + "/servicos#ecu", wait_until="networkidle")
        await st.wait_for_timeout(100)
        geo = await st.evaluate("""() => {
            const lista = document.querySelector('.temas-lista').getBoundingClientRect();
            const tema = document.getElementById('ecu').getBoundingClientRect();
            const xs = [...document.querySelectorAll('#ecu .svc-colunas li')].map(l => Math.round(l.getBoundingClientRect().left));
            return {acima: lista.bottom <= tema.top, colunas: new Set(xs).size, larg: document.documentElement.scrollWidth - innerWidth};
        }""")
        check(geo["acima"] and geo["colunas"] == 1 and geo["larg"] <= 0 and await st.is_visible("#ecu"),
              f"telemóvel: lista em cima, listas numa coluna e sem deslocamento horizontal {geo}")
        await st.evaluate("window.scrollTo(0, 0)")
        await st.screenshot(path=os.path.join(OUT, "ui-servicos-telemovel.png"), full_page=True)
        await stel.close()

        # Sem JavaScript: todos os temas seguidos e a lista como índice
        snj = await b.new_context(viewport={"width": 1280, "height": 900}, java_script_enabled=False)
        sn = await snj.new_page()
        await sn.goto(B + "/servicos")
        n_vis = await sn.locator("[data-tema]:visible").count()
        check(n_vis == 12 and not await sn.is_visible("[data-temas-passos]"), f"sem JavaScript: os 12 temas seguidos, sem Anterior/Seguinte ({n_vis})")
        await snj.close()

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
sys.exit(0 if RES and all(RES) else 1)
