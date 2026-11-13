#!/usr/bin/env python3
"""Gera o site estático da GARC.

    python3 build.py

Saídas:
  site/     versão de produção (a que vai para o alojamento)
  preview/  pré-visualização para revisão (formulários sem envio, aviso de campos por preencher)
"""
import html
import json
import re
import shutil
import unicodedata
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

COMPANY = "GARC – Soluções Técnicas"
FIRMA = "GARC – Soluções Técnicas, Unipessoal Lda"
MARCA = "GARC – AutoSolutions & Consulting"  # texto do logótipo
# Logótipo do cabeçalho em SVG (gerado por ferramentas/logo/compor.py): versão larga, com o lema,
# e versão curta para ecrãs estreitos. As cores vêm das variáveis --logo-* do styles.css.
LOGO_CABECALHO = (SRC / "logo-cabecalho.html").read_text(encoding="utf-8").strip()
YEAR = "2026"
UPDATED = ("2026-11-01", "1 de novembro de 2026")
MAX_MB = 25

# Dados da empresa. O que ficar vazio aparece a amarelo no site e é listado no fim da geração.
# A morada da sede e a conservatória aparecem só na identificação legal (rodapé, privacidade e termos),
# não nos contactos, porque o serviço é prestado online. O capital social não é mostrado, por decisão da empresa.
DADOS = {
    "whatsapp": "+351 913 027 543",  # contacto só por WhatsApp (mensagens); o site não mostra ligação para chamadas
    "email": "fileservice@autosolutions.pt",  # email da empresa (contactos, pedidos e privacidade)
    "nipc": "505743973",
    "desde": 2001,          # ano em que a empresa entrou no mercado; os anos contam-se até YEAR
    "foto_inicio": "fotos/inicio",  # imagem da página inicial: Pexels n.º 8664308 (licença e alterações em
                                    # ferramentas/foto/LICENCAS.md), limpa por limpar_inicio.py, com a frase
                                    # pintada por frase_parede.py e preparada por preparar.py; vazio = aparece a amarelo
    "foto_inicio_foco": "50% 52%",  # ponto da imagem que fica sempre à vista (object-position)
    "foto_inicio_foco_estreito": "50% 55%",  # o mesmo, em ecrãs ao alto (telemóvel); com recorte ao alto
                                             # (preparar.py --estreito), é a posição dentro do recorte
    "foto_inicio_frase": "imagem",  # onde fica a frase: "imagem" (pintada na parede da fotografia; o título
                                    # fica só para leitores de ecrã), "cima" ou "baixo" (texto sobre a imagem)
    "morada": "Rua do Morangal, n.º 205, Traseiras, Fração S, 4410-385 Vila Nova de Gaia",  # sede
    "conservatoria": "Vila Nova de Gaia",  # Conservatória do Registo Comercial onde a sociedade está matriculada
    "prazo_pedidos": "1 mês",    # conservação de pedidos sem seguimento
    "prazo_ficheiros": "1 mês",  # conservação dos ficheiros de centralina (apagados automaticamente)
    # horário, prazo de entrega, pagamentos, IVA e validade dos tokens: ver VALORES, mais abaixo
    "reembolso": "não é reembolsado; os tokens ficam em crédito na conta até ao fim da validade",
}

# Valores que o Raul altera no servidor, sem mexer no código: preços, prazo de entrega, horário e pagamentos.
# A origem é app/conteudos-iniciais/dados.txt; no servidor manda a cópia em garc-conteudos/dados.txt, lida no
# momento por app/conteudos.php (páginas em PHP e API). Aqui usam-se os valores de origem: na pré-visualização
# e como reserva das páginas em PHP. Os preços só aparecem na área de cliente, a contas aprovadas, vindos da API.
# O custo de cada pedido depende da ECU e é definido no painel depois de analisado o ficheiro.
CONTEUDOS_INICIAIS = ROOT / "app" / "conteudos-iniciais"


def ler_dados(texto):
    """Linhas «chave: valor»; ignora linhas vazias e notas (#). Igual a garc_ler_dados em app/conteudos.php."""
    dados = {}
    for linha in texto.lstrip("\ufeff").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or ":" not in linha:
            continue
        chave, valor = linha.split(":", 1)
        chave = chave.strip().lower()
        if re.fullmatch(r"[a-z_]+", chave):
            dados[chave] = valor.strip()
    return dados


VALORES = ler_dados((CONTEUDOS_INICIAIS / "dados.txt").read_text(encoding="utf-8"))
TOKEN_EUR = float(re.sub(r"[€\s]", "", VALORES["token"]).replace(",", "."))  # preço de 1 token, com IVA
TOKENS_MINIMO = int(re.match(r"\d+", VALORES["minimo"]).group())  # carregamento mínimo e tokens descontados no envio
EXEMPLOS_CARREGAMENTO = [int(x) for x in re.findall(r"\d+", VALORES["exemplos"])]  # quantidades na tabela de preços
SOB_CONSULTA = VALORES["sob_consulta"]
DADOS.update(horario=VALORES["horario"], entrega=VALORES["entrega"], mbway=VALORES["mbway"],
             stripe=VALORES["cartao"], paypal=VALORES["paypal"], iva=VALORES["iva"],
             validade_tokens=VALORES["validade"])

# PHP2Shell (CVE-2026-109618 e CVE-2026-109619, outubro de 2026): falhas críticas do PHP, exploradas sem
# autenticação, corrigidas só no 8.2.35, 8.3.36, 8.4.27 e 8.5.12. O alojamento só tem PHP 7.4, sem correção.
# Com SEM_PHP = True, o site publicado não corre PHP nenhum: as páginas são estáticas (com os valores de
# origem), o .htaccess recusa ficheiros .php e a área de cliente e o formulário de contacto ficam
# indisponíveis, com um aviso.
# 13/11/2026: o Raul decidiu abrir a área de cliente e o formulário de contacto com o PHP 7.4 do alojamento
# (a API corre a partir do 7.4), até haver PHP 8 corrigido. Para voltar a fechar: SEM_PHP = True e python3 build.py.
# A pré-visualização e os testes (python3 build.py --com-php PASTA) mostram sempre o site completo.
SEM_PHP = False

PREVIEW = False  # definido por build()
PAGINA_PHP = False  # definido por build() para cada página: True quando a página do site é gerada em PHP
MISSING = []     # campos por preencher encontrados na geração
OCULTOS = []     # opções que não aparecem no site enquanto o campo estiver vazio


def esc(text):
    return html.escape(text, quote=True)


def ph(text, report=None):
    """Texto por preencher (destacado a amarelo). `report` junta vários campos numa só linha do relatório."""
    label = report or text
    if label not in MISSING:
        MISSING.append(label)
    return f'<span class="ph">[{esc(text)}]</span>'


def val(key, label):
    value = DADOS.get(key)
    return esc(value) if value else ph(label)


def dado(chave, label):
    """Valor alterável no servidor (garc-conteudos/dados.txt): nas páginas em PHP é lido no momento, com o valor
    de origem como reserva; na pré-visualização aparece o valor de origem."""
    origem = {"horario": DADOS["horario"], "entrega": DADOS["entrega"], "validade": DADOS["validade_tokens"],
              "meios_txt": meios_txt()}[chave]
    if PREVIEW or not PAGINA_PHP:
        return esc(origem) if origem else ph(label)
    return f"<?= garc_v({php_str(chave)}, {php_str(origem)}) ?>"


def url(page, anchor=""):
    """Ligação interna: ficheiro .html na pré-visualização, endereço limpo no site publicado."""
    if PREVIEW:
        return f"{page}.html{anchor}"
    return ("/" if page == "index" else f"/{page}") + anchor


def contacto_url(assunto):
    """Ligação à página Contacto com o assunto já escrito no formulário (lido por assets/main.js)."""
    return url("contacto", "?assunto=" + quote(assunto))


def asset(path):
    return path if PREVIEW else f"/{path}"


def email_html():
    email = DADOS["email"]
    return f'<a href="mailto:{esc(email)}">{esc(email)}</a>' if email else ph("email da empresa")


def desde_html():
    """Há quanto tempo a empresa está no mercado, contado até ao ano de YEAR."""
    ano = DADOS.get("desde")
    if not ano:
        return ph("ano de entrada no mercado")
    return f"Desde {ano} ({int(YEAR) - int(ano)} anos)"


def paypal_url():
    return f"https://paypal.me/{DADOS['paypal']}" if DADOS["paypal"] else ""


def lista_txt(itens):
    """«A», «A ou B», «A, B ou C»."""
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " ou " + itens[-1]


def meios_pagamento():
    """Meios de pagamento com dados preenchidos; o cartão e o PayPal ficam ocultos até haver ligação."""
    meios = ["MB WAY"]
    for chave, nome, falta in (("stripe", "cartão", "pagamento por cartão: ligação do Stripe em «cartao», no dados.txt do servidor"),
                               ("paypal", "PayPal", "pagamento por PayPal: nome em «paypal», no dados.txt do servidor")):
        if DADOS[chave]:
            meios.append(nome)
        elif falta not in OCULTOS:
            OCULTOS.append(falta)
    return meios


def meios_txt():
    return lista_txt(meios_pagamento())


def plataformas_txt():
    """Frase da política de privacidade sobre as plataformas de pagamento. Os meios em uso mudam no servidor
    (dados.txt), por isso a frase vale para qualquer combinação."""
    return (" Se pagar por cartão ou por PayPal, o pagamento é feito na plataforma Stripe ou PayPal, que trata"
            " os dados do pagamento segundo as suas próprias políticas.")


def registo_html(inicio=False):
    """Matrícula no registo comercial (o número de matrícula é o NIPC). `inicio`: começa a frase."""
    return (f"{'M' if inicio else 'm'}atriculada na Conservatória do Registo Comercial de "
            f"{val('conservatoria', 'conservatória do registo comercial')} "
            f"com o número único de matrícula e de pessoa coletiva {val('nipc', 'NIPC')}")


def whatsapp_digitos():
    """Número com indicativo, só algarismos (ex.: 351913027543)."""
    digits = re.sub(r"\D", "", DADOS["whatsapp"])
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 9:  # número português sem indicativo
        digits = "351" + digits
    return digits


def whatsapp_url(texto="Olá! Tenho uma questão sobre os serviços da GARC."):
    return f"https://wa.me/{whatsapp_digitos()}?text={quote(texto)}"


def whatsapp_html():
    """Contacto por WhatsApp: o número abre a conversa; não há ligação para chamadas."""
    if not DADOS["whatsapp"]:
        return ph("número de WhatsApp")
    return (f'<a href="{esc(whatsapp_url())}" target="_blank" rel="noopener">{esc(DADOS["whatsapp"])}</a>'
            '<br><span class="small muted">Atendimento por mensagem, sem chamadas.</span>')


def whatsapp_flutuante():
    """Botão fixo no canto do ecrã para abrir uma conversa no WhatsApp."""
    if not DADOS["whatsapp"]:
        return ""
    return (f'<a class="wa-float" href="{esc(whatsapp_url())}" target="_blank" rel="noopener" '
            f'aria-label="Falar connosco pelo WhatsApp">'
            '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H11l-4.6 3.7a.6.6 0 0 1-1-.47V16H6.5A2.5 2.5 0 0 1 4 13.5z"/></svg>'
            '<span>WhatsApp</span></a>')


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ---------------------------------------------------------------- módulos

MODULES = {
    "STAGE 1/2": ("Stage 1/2", "Stage 1: recalibração do software com o motor de série (binário, pressão do turbo, injeção e limitadores). Stage 2: calibração feita para alterações físicas já montadas, como admissão, intercooler ou escape."),
    "TCU STAGE 1": ("TCU Stage 1", "Recalibração da caixa automática: limites de binário, pontos de passagem e pressões, de acordo com o novo binário do motor."),
    "POP & BANGS": ("Pop & bangs", "Estalos no escape em desaceleração, com intensidade e regime configuráveis. Para motores a gasolina."),
    "TORQUE MONITORING": ("Torque monitoring", "Ajuste da monitorização de binário, para que a centralina não entre em modo de emergência depois da reprogramação."),
    "SPORT DISPLAY CALIBRATION": ("Sport display", "Calibração das leituras do ecrã desportivo (potência, binário e pressão do turbo) para os valores depois da reprogramação."),
    "FLAPS OFF": ("Flaps off", "Desativação das borboletas de turbulência (swirl flaps) do coletor de admissão, sem erros na centralina."),
    "EXHAUST FLAP OFF": ("Exhaust flap off", "Desativação ou controlo da válvula de escape."),
    "TVA OFF": ("TVA off", "Desativação do atuador da borboleta de admissão (TVA) em motores diesel."),
    "MAF OFF": ("MAF off", "Funcionamento sem o medidor de massa de ar, com o ar admitido calculado por modelo."),
    "OIL PRESSURE FIX": ("Oil pressure fix", "Correção de erros relacionados com o controlo da pressão de óleo."),
    "HOT START FIX": ("Hot start fix", "Correção da calibração de arranque em motores com dificuldade em pegar a quente."),
    "START STOP OFF": ("Start-stop off", "Desativação permanente do sistema Start & Stop."),
    "DPF OFF": ("DPF off", "Desativação do filtro de partículas (DPF/FAP) na gestão do motor."),
    "EGR OFF": ("EGR off", "Desativação da recirculação dos gases de escape (EGR)."),
    "ADBLUE/SCR OFF": ("AdBlue/SCR off", "Desativação do sistema de redução catalítica seletiva (SCR/AdBlue)."),
    "LAMBDA/O2 OFF": ("Lambda/O2 off", "Desativação da monitorização das sondas lambda (O2)."),
    "CHECKSUM": ("Correção de checksum", "Correção do checksum de um ficheiro já modificado, para que a centralina o aceite na escrita."),
    "MAP REVIEW": ("Revisão de mapa", "Revisão de um ficheiro já modificado, por outro preparador ou pela oficina, à procura de erros nos mapas alterados."),
}

# (âncora, título, introdução, módulos, é de emissões)
GROUPS = [
    ("chiptuning", "Chiptuning", "Recalibração do software do motor e da caixa automática.",
     ["STAGE 1/2", "TCU STAGE 1", "POP & BANGS", "TORQUE MONITORING", "SPORT DISPLAY CALIBRATION"], False),
    ("admissao-escape", "Admissão e escape", "Gestão de componentes de admissão e escape na centralina.",
     ["FLAPS OFF", "EXHAUST FLAP OFF", "TVA OFF", "MAF OFF"], False),
    ("correcoes", "Correções", "Correções de calibração para problemas conhecidos.",
     ["OIL PRESSURE FIX", "HOT START FIX", "START STOP OFF"], False),
    ("emissoes", "Sistemas de emissões", None,
     ["DPF OFF", "EGR OFF", "ADBLUE/SCR OFF", "LAMBDA/O2 OFF"], True),
    ("verificacao", "Verificação de ficheiros",
     "Para ficheiros já modificados pela oficina ou por outro preparador, com custo à parte.",
     ["CHECKSUM", "MAP REVIEW"], False),
]

EMISSIONS_NOTICE = (
    "Os módulos de desativação de sistemas de emissões destinam-se a veículos de competição "
    "ou a uso fora da via pública. Ao pedir um destes módulos, o cliente declara essa finalidade "
    "e assume a responsabilidade pela utilização do ficheiro."
)

EMISSOES = {k for _a, _t, _i, keys, em in GROUPS if em for k in keys}

def tokens_txt(n):
    return f"{n} token" if abs(n) == 1 else f"{n} tokens"


def eur(valor):
    return f"{valor:,.2f}".replace(",", " ").replace(".", ",") + " €"


# ---------------------------------------------------------------- moldura comum

NAV = [
    ("index", "", "Início", "inicio"),
    ("servicos", "", "Serviços", "servicos"),
    ("noticias", "", "Notícias", "noticias"),
    ("sobre", "", "Sobre", "sobre"),
    ("contacto", "", "Contacto", "contacto"),
]


def header(active):
    items = []
    for page, anchor, label, key in NAV:
        href = url(page, anchor)
        cur = ' aria-current="page"' if key == active else ""
        items.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    cur = ' aria-current="page"' if active == "area-cliente" else ""
    items.append(f'<li class="nav-account"><a href="{url("area-cliente")}"{cur}>Área de cliente</a></li>')
    nav_items = "\n        ".join(items)
    return f"""<a class="skip" href="#conteudo">Saltar para o conteúdo</a>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="{url('index')}" aria-label="{esc(MARCA)}, página inicial">
      {LOGO_CABECALHO}
    </a>
    <nav class="nav" aria-label="Principal" data-open="false">
      <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="nav-list"><span class="nav-toggle-bars" aria-hidden="true"><span></span><span></span><span></span></span>Menu</button>
      <ul class="nav-list" id="nav-list">
        {nav_items}
      </ul>
    </nav>
  </div>
</header>"""


def form_attrs(endpoint, preview, multipart=False):
    if preview:
        return ""
    enc = ' enctype="multipart/form-data"' if multipart else ""
    return f' action="{endpoint}" method="post"{enc}'


def footer(inicio=False):
    """Rodapé de todas as páginas: só a parte legal. O acesso ao Livro de Reclamações Eletrónico tem de
    estar sempre visível. A identificação da empresa (sede e registo) não aparece na página inicial,
    que fica só com as ligações; os contactos estão na página Contacto (formulário)."""
    ident = "" if inicio else (f"\n      <p>{esc(FIRMA)}. Sede: {val('morada', 'morada da sede')}. "
                               f"{registo_html(inicio=True)}.</p>")
    return f"""<footer class="site-footer">
  <div class="footer-legal">
    <div class="wrap">{ident}
      <ul class="legal-links">
        <li><a class="lre" href="https://www.livroreclamacoes.pt/" target="_blank" rel="noopener">Livro de Reclamações Eletrónico</a></li>
        <li><a href="{url('privacidade')}">Política de privacidade</a></li>
        <li><a href="{url('termos')}">Termos de utilização</a></li>
      </ul>
      <p>© {YEAR} {esc(COMPANY)}</p>
    </div>
  </div>
</footer>"""


def head_tags(title, desc, preview, bare, noindex=False, scripts=()):
    tags = []
    if not bare:
        tags += ['<meta charset="utf-8">',
                 '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">']
    tags.append(f"<title>{esc(title)}</title>")
    if preview:
        tags += ['<meta name="claude:viewport-fit-sides" content="cover">',
                 '<meta name="garc-preview" content="1">']
    if noindex:
        tags.append('<meta name="robots" content="noindex">')
    tags += [
        f'<meta name="description" content="{esc(desc)}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        '<meta property="og:locale" content="pt_PT">',
        f'<link rel="icon" href="{asset("assets/favicon.ico")}" sizes="32x32">',
        f'<link rel="icon" href="{asset("assets/favicon.svg")}" type="image/svg+xml">',
        f'<link rel="apple-touch-icon" href="{asset("assets/apple-touch-icon.png")}">',
        f'<link rel="preload" href="{asset("assets/fonts/barlow-latin-400-normal.woff2")}" as="font" type="font/woff2" crossorigin>',
        f'<link rel="preload" href="{asset("assets/fonts/barlow-condensed-latin-700-normal.woff2")}" as="font" type="font/woff2" crossorigin>',
        f'<link rel="stylesheet" href="{asset("assets/styles.css")}">',
        f'<script src="{asset("assets/main.js")}" defer></script>',
    ]
    if scripts and preview:
        scripts = ["assets/demo.js", *scripts]
    tags += [f'<script src="{asset(s)}" defer></script>' for s in scripts]
    return "\n".join(tags)


def document(page, preview):
    # Na pré-visualização, a página principal é envolvida pelo próprio Artifact (sem doctype/head/body).
    bare = preview and page["file"] == "index.html"
    scripts = () if sem_php(preview) else page.get("scripts", ())
    head = head_tags(page["title"], page["desc"], preview, bare, page.get("noindex", False), scripts)
    body = "\n".join([
        header(page["nav"]),
        '<main id="conteudo">',
        catalogo_script() if scripts else "",
        page["body"](preview),
        "</main>",
        footer(inicio=page["file"] == "index.html"),
        whatsapp_flutuante() if page.get("whatsapp", True) else "",
    ])
    if bare:
        return f"{head}\n{body}\n"
    return f'<!doctype html>\n<html lang="pt-PT">\n<head>\n{head}\n</head>\n<body>\n{body}\n</body>\n</html>\n'


def page_head(title, lead=None, extra=""):
    lead_html = f'\n    <p class="lead">{lead}</p>' if lead else ""
    return f"""<section class="page-head">
  <div class="wrap">
    <h1>{title}</h1>{lead_html}{extra}
  </div>
</section>"""


# ---------------------------------------------------------------- página inicial

# Módulos do esquema da rede de bordo (vista de cima, frente à direita): x, y, nome, pormenor.
# Os módulos com y = 150 ficam sobre a linha principal da rede CAN; os outros ligam-se por um ramal.
REDE_BORDO = [
    (515, 150, "Motor e caixa", "ECU e TCU"),
    (480, 208, "ABS e ESP", "travões e estabilidade"),
    (420, 112, "Painel e conforto", "BCM"),
    (372, 100, "Ficha de diagnóstico", "OBD"),
    (326, 150, "Airbag", "SRS"),
]


def rede_bordo():
    """Esquema simplificado de um automóvel visto de cima, com os módulos ligados pela rede CAN."""
    tronco = [x for x, y, *_ in REDE_BORDO if y == 150]
    linhas = [f'<path class="rb-can" pathLength="1" d="M{min(tronco)} 150 H{max(tronco)}"/>']
    ramais = [(x, y) for x, y, *_ in REDE_BORDO if y != 150]
    linhas += [f'<path class="rb-can rb-ramal" style="--i: {i}" pathLength="1" d="M{x} 150 V{y}"/>'
               for i, (x, y) in enumerate(ramais)]
    nos = [f'<g transform="translate({x} {y})"><g class="rb-no"><circle r="14"/><text y="5.5">{n}</text></g></g>'
           for n, (x, y, *_) in enumerate(REDE_BORDO, 1)]
    legenda = "".join(f"<li><strong>{esc(nome)}</strong><span>{esc(pormenor)}</span></li>"
                      for *_, nome, pormenor in REDE_BORDO)
    legenda += '<li class="rb-legenda-can"><strong>Rede CAN</strong><span>liga os módulos entre si</span></li>'
    return f"""<figure class="rb">
      <svg class="rb-svg" viewBox="0 0 600 300" role="img" aria-labelledby="rb-titulo rb-desc">
        <title id="rb-titulo">Rede de bordo de um automóvel</title>
        <desc id="rb-desc">Esquema de um automóvel visto de cima, com os módulos numerados de 1 a 5 ligados pela rede CAN.</desc>
        <g class="rb-rodas"><rect x="94" y="37" width="66" height="19" rx="6"/><rect x="94" y="244" width="66" height="19" rx="6"/><rect x="440" y="37" width="66" height="19" rx="6"/><rect x="440" y="244" width="66" height="19" rx="6"/></g>
        <g class="rb-linha"><rect x="400" y="38" width="24" height="12" rx="5" transform="rotate(-10 412 44)"/><rect x="400" y="250" width="24" height="12" rx="5" transform="rotate(10 412 256)"/></g>
        <path class="rb-corpo" d="M40 150 C40 95 48 62 92 56 C180 48 380 46 470 50 C535 53 566 80 570 150 C566 220 535 247 470 250 C380 254 180 252 92 244 C48 238 40 205 40 150 Z"/>
        <path class="rb-vidro" d="M172 102 C176 88 192 82 216 80 L388 78 C418 80 440 90 450 104 L450 196 C440 210 418 220 388 222 L216 220 C192 218 176 212 172 198 Z M388 78 C397 108 397 192 388 222 M216 80 C208 108 208 192 216 220"/>
        <g class="rb-bancos"><rect x="300" y="92" width="52" height="44" rx="10"/><rect x="300" y="164" width="52" height="44" rx="10"/><rect x="228" y="92" width="44" height="116" rx="12"/></g>
        {"".join(linhas)}
        {"".join(nos)}
      </svg>
      <ol class="rb-legenda">{legenda}</ol>
      <figcaption>Esquema simplificado de um automóvel visto de cima. É nesta rede que trabalhamos.</figcaption>
    </figure>"""


# Áreas de serviço da página inicial. "estado": None (disponível) ou "Brevemente".
AREAS = [
    {
        "titulo": "Ficheiros de calibração",
        "texto": "Chiptuning, admissão e escape, correções e sistemas de emissões, por módulo, preparados para a viatura e a ECU de cada pedido. Também corrigimos o checksum e revemos ficheiros já modificados.",
        "modo": "Online, na área de cliente, com tokens.",
        "aviso": "Sistemas de emissões: uso exclusivo em competição ou fora da via pública",
        "ligacao": ("servicos", "Ver módulos"),
        "estado": None,
    },
    {
        "titulo": "Diagnóstico avançado",
        "texto": "Avarias intermitentes, falhas de comunicação entre módulos, sensores e atuadores, e sistemas de pós-tratamento.",
        "modo": "Por WhatsApp, com apoio durante a reparação.",
        "whatsapp": ("Olá! Preciso de ajuda com um diagnóstico:", "Pedir diagnóstico"),
        "estado": None,
    },
    {
        "titulo": "Airbags",
        "texto": "Reposição de módulos de airbag após acidente (crash data), depois de substituídos os componentes acionados.",
        "modo": "Por WhatsApp.",
        "whatsapp": ("Olá! Gostava de saber mais sobre a reposição de módulos de airbag.", "Perguntar pelo WhatsApp"),
        "estado": "Brevemente",
    },
    {
        "titulo": "Serviços na oficina",
        "texto": "Para oficinas da região: deslocação à oficina para diagnóstico e apoio técnico.",
        "modo": "Por marcação, pelo WhatsApp.",
        "whatsapp": ("Olá! Gostava de saber mais sobre os serviços na oficina.", "Perguntar pelo WhatsApp"),
        "estado": "Brevemente",
    },
]


def areas_html():
    itens = []
    for a in AREAS:
        estado = f'<span class="estado">{esc(a["estado"])}</span>' if a.get("estado") else ""
        aviso = f'\n        <span class="tag">{esc(a["aviso"])}</span>' if a.get("aviso") else ""
        if a.get("ligacao"):
            pagina, rotulo = a["ligacao"]
            acao = f'<a href="{url(pagina)}">{esc(rotulo)}</a>'
        elif a.get("whatsapp") and DADOS["whatsapp"]:
            texto, rotulo = a["whatsapp"]
            acao = f'<a href="{esc(whatsapp_url(texto))}" target="_blank" rel="noopener">{esc(rotulo)}</a>'
        else:
            acao = ""
        itens.append(f"""<li class="area">
        <div class="area-titulo"><h3>{esc(a["titulo"])}</h3>{estado}</div>
        <p>{esc(a["texto"])}</p>
        <p class="area-modo">{esc(a["modo"])}</p>{aviso}
        {acao}
      </li>""")
    return "\n      ".join(itens)


FOTO_LARGURAS = (1280, 1920, 2560)          # tamanhos gerados por ferramentas/foto/preparar.py
FOTO_LARGURAS_ESTREITO = (800, 1200, 1600)  # recorte ao alto (preparar.py --estreito), se existir
# A fotografia cobre a área toda (object-fit: cover): num ecrã mais estreito do que a imagem (3:2),
# a largura necessária é a altura x 1,5, não a largura do ecrã. Sem isto, o telemóvel escolhia
# o ficheiro mais pequeno e ampliava-o. No recorte ao alto (4:5), é a altura x 0,8.
FOTO_SIZES = "(max-aspect-ratio: 3/2) 150vh, 100vw"
FOTO_SIZES_ESTREITO = "(max-aspect-ratio: 4/5) 80vh, 100vw"
FOTO_MEDIA_ESTREITO = "(max-aspect-ratio: 1/1)"  # igual à regra de --foco-estreito em styles.css


def foto_inicio_html():
    """Fotografia da página inicial em vários tamanhos (WebP, com JPEG para browsers antigos).
    Em ecrãs ao alto usa o recorte NOME-estreito-*, quando existe."""
    base = DADOS["foto_inicio"]
    if not base:
        return f'<p class="abertura-falta">{ph("fotografia da página inicial")}</p>'
    def conjunto(nome, larguras, ext):
        return ", ".join(f"{asset(f'assets/{nome}-{w}.{ext}')} {w}w" for w in larguras)
    fontes = []
    if (SRC / "assets" / f"{base}-estreito-{FOTO_LARGURAS_ESTREITO[0]}.webp").exists():
        for tipo, ext in ((' type="image/webp"', "webp"), ("", "jpg")):
            fontes.append(f'<source media="{FOTO_MEDIA_ESTREITO}"{tipo} '
                          f'srcset="{conjunto(f"{base}-estreito", FOTO_LARGURAS_ESTREITO, ext)}" sizes="{FOTO_SIZES_ESTREITO}">')
    fontes.append(f'<source type="image/webp" srcset="{conjunto(base, FOTO_LARGURAS, "webp")}" sizes="{FOTO_SIZES}">')
    foco = esc(DADOS["foto_inicio_foco"])
    foco_estreito = esc(DADOS.get("foto_inicio_foco_estreito") or DADOS["foto_inicio_foco"])
    return f"""<picture class="abertura-foto">
    {(chr(10) + "    ").join(fontes)}
    <img src="{asset(f'assets/{base}-1920.jpg')}" srcset="{conjunto(base, FOTO_LARGURAS, 'jpg')}" sizes="{FOTO_SIZES}" alt="" fetchpriority="high" style="--foco: {foco}; --foco-estreito: {foco_estreito}">
  </picture>"""


def body_index(preview):
    """Página inicial: uma fotografia em ecrã inteiro e uma frase. O resto está nos separadores da barra."""
    frase = DADOS.get("foto_inicio_frase")
    if frase not in ("imagem", "cima", "baixo"):
        frase = "baixo"
    # Com a frase pintada na fotografia, o título continua no HTML (leitores de ecrã, motores de busca),
    # mas não aparece por cima da imagem. Sem fotografia, aparece sempre.
    oculto = ' class="sr-only"' if frase == "imagem" and DADOS["foto_inicio"] else ""
    return f"""<section class="abertura" data-frase="{frase}" aria-labelledby="abertura-titulo">
  {foto_inicio_html()}
  <div class="wrap">
    <h1 id="abertura-titulo"{oculto}>O automóvel fala.<br> Nós ouvimos.</h1>
  </div>
</section>"""


# Reservado: secções que saíram da página inicial (rede de bordo e áreas de serviço).
# Ficam aqui para serem reaproveitadas quando se definirem as outras páginas.
def seccoes_reservadas():
    desde = f"No mercado desde {DADOS['desde']}." if DADOS.get("desde") else ""
    return f"""{rede_bordo()}
<ul class="areas">{areas_html()}</ul>
<p class="hero-nota">{desde}</p>"""


# ---------------------------------------------------------------- sobre e contacto

def body_sobre(preview):
    """Página «Sobre»: só informação sobre a empresa, sem botões. Texto aprovado para já; o Raul vai revê-lo."""
    return page_head("Sobre a GARC") + f"""
<section class="section">
  <div class="wrap about">
    <div class="about-text">
      <p>A GARC está no mercado desde {DADOS['desde']} e dedica-se hoje à eletrónica automóvel: ficheiros de calibração, diagnóstico avançado e apoio técnico a oficinas.</p>
      <p>Conhecemos o motor e a eletrónica por dentro, da teoria à bancada. Quem nos envia uma leitura fala diretamente com quem a vai trabalhar, sem intermediários.</p>
      <p>Cada ficheiro é feito para aquela viatura, aquela ECU e aquela leitura, e é verificado antes de seguir. Ganhar potência não pode custar o motor nem a caixa: trabalhamos dentro dos limites mecânicos de cada conjunto.</p>
      <p>Resposta rápida, trabalho explicado e apoio até o carro sair da oficina.</p>
      <p class="assinatura">Engenharia ao serviço da oficina.</p>
    </div>
    <dl class="spec">
      <div><dt>Empresa</dt><dd>{esc(FIRMA)}</dd></div>
      <div><dt>No mercado</dt><dd>{desde_html()}</dd></div>
      <div><dt>Entrega</dt><dd>{dado('entrega', 'prazo de entrega dos ficheiros')}</dd></div>
      <div><dt>Clientes</dt><dd>Oficinas e profissionais do setor automóvel</dd></div>
      <div><dt>Leituras</dt><dd>OBD, bancada e boot</dd></div>
    </dl>
  </div>
</section>"""


def body_contacto(preview):
    """Página «Contacto»: só o formulário, sem WhatsApp nem horário (o horário está em Serviços).
    O envio é feito por assets/main.js para /api/contacto. O assunto pode vir no endereço
    (contacto?assunto=…), como no botão «Pedir diagnóstico» da página Serviços."""
    if sem_php(preview):
        return page_head("Contacto", "Escreva-nos por email. Respondemos com a maior brevidade.") + f"""
<section class="section">
  <div class="wrap">
    <p class="note">O formulário de contacto está temporariamente indisponível, enquanto o servidor recebe uma atualização de segurança. Escreva-nos para {email_html()}.</p>
  </div>
</section>"""
    # Se o envio falhar (servidor em baixo, limite de mensagens), a mensagem de erro indica o email.
    alternativa = f' data-email="{esc(DADOS["email"])}"' if DADOS["email"] else ""
    return page_head("Contacto", "Envie uma mensagem pelo formulário. Respondemos por email.") + f"""
<section class="section">
  <div class="wrap">
    <form class="form contacto-form" id="form-contacto"{form_attrs("/api/contacto", preview)}{alternativa}>
      <div class="grid-2">
        <div class="field"><label for="f-c-nome">Nome <span class="req" aria-hidden="true">*</span></label><input id="f-c-nome" name="nome" autocomplete="given-name" required></div>
        <div class="field"><label for="f-c-apelido">Apelido</label><input id="f-c-apelido" name="apelido" autocomplete="family-name"></div>
        <div class="field"><label for="f-c-email">Email <span class="req" aria-hidden="true">*</span></label><input id="f-c-email" name="email" type="email" autocomplete="email" required></div>
        <div class="field"><label for="f-c-telefone">Telefone</label><input id="f-c-telefone" name="telefone" type="tel" autocomplete="tel"></div>
      </div>
      <div class="field"><label for="f-c-assunto">Assunto</label><input id="f-c-assunto" name="assunto"></div>
      <div class="field"><label for="f-c-mensagem">Mensagem <span class="req" aria-hidden="true">*</span></label><textarea id="f-c-mensagem" name="mensagem" required></textarea></div>
      <div class="check"><input id="f-c-rgpd" name="privacidade" type="checkbox" value="sim" required><label for="f-c-rgpd">Li a <a href="{url('privacidade')}">política de privacidade</a>.</label></div>
      <div class="hp" aria-hidden="true"><label for="f-c-site">Não preencher</label><input id="f-c-site" name="website" tabindex="-1" autocomplete="off"></div>
      <div class="actions"><button class="btn btn-primary" type="submit">Enviar mensagem</button></div>
      <p class="status" role="status" aria-live="polite" hidden></p>
    </form>
  </div>
</section>"""


# ---------------------------------------------------------------- serviços

def body_servicos(preview):
    sub = "".join(f'<a href="#{a}">{t}</a>' for a, t, *_ in GROUPS) + '<a href="#diagnostico">Diagnóstico avançado</a>'
    # O horário de atendimento aparece só nesta página; Preços e Termos remetem para aqui.
    horario = f'\n    <p class="horario">Horário de atendimento: <strong>{dado("horario", "dias e horas de atendimento")}</strong></p>'
    parts = [page_head(
        "Serviços",
        "Ficheiros por módulo, preparados para a viatura e a ECU de cada pedido, e diagnóstico avançado para oficinas.",
        f'{horario}\n    <nav class="subnav" aria-label="Secções desta página">{sub}</nav>',
    )]
    for anchor, title, intro, keys, emissions in GROUPS:
        items = "\n        ".join(
            f"<div><dt>{esc(MODULES[k][0])}</dt><dd>{esc(MODULES[k][1])}</dd></div>" for k in keys
        )
        intro_html = f'<p class="muted">{intro}</p>' if intro else ""
        notice = (
            f'\n    <div class="notice" role="note"><strong>Uso exclusivo em competição ou fora da via pública.</strong>'
            f"<p>{EMISSIONS_NOTICE}</p></div>"
            if emissions else ""
        )
        parts.append(f"""<section class="section svc-section" id="{anchor}">
  <div class="wrap">
    <div class="section-head"><h2>{title}</h2>{intro_html}</div>{notice}
    <dl class="mod-list">
        {items}
    </dl>
  </div>
</section>""")
    parts.append(f"""<section class="section svc-section" id="diagnostico">
  <div class="wrap stack">
    <div class="section-head"><h2>Diagnóstico avançado</h2><p class="lead">Para as avarias que pedem mais do que uma leitura de erros.</p></div>
    <ul class="checklist">
      <li>Avarias intermitentes e falhas de comunicação entre módulos</li>
      <li>Sistemas de pós-tratamento: EGR, DPF e SCR</li>
      <li>Sensores e atuadores, com análise de valores reais</li>
      <li>Apoio técnico à oficina durante a reparação</li>
    </ul>
    <div class="actions">
      <a class="btn btn-primary" href="{esc(contacto_url('Diagnóstico avançado'))}">Pedir diagnóstico</a>
      <a class="btn btn-secondary" href="{url('area-cliente', '#novo')}">Enviar ficheiro</a>
    </div>
  </div>
</section>""")
    return "\n\n".join(parts)


# ---------------------------------------------------------------- pedido de ficheiro

def field(fid, name, label, required=False, kind="text", placeholder="", extra=""):
    req_mark = ' <span class="req" aria-hidden="true">*</span>' if required else ""
    req_attr = " required" if required else ""
    ph_attr = f' placeholder="{esc(placeholder)}"' if placeholder else ""
    return (f'<div class="field"><label for="{fid}">{label}{req_mark}</label>'
            f'<input id="{fid}" name="{name}" type="{kind}"{ph_attr}{req_attr}{extra}></div>')


def form_novo_pedido():
    """Formulário de novo pedido da área de cliente. O envio é feito por assets/portal.js."""
    groups_html = []
    for anchor, title, _intro, keys, emissions in GROUPS:
        checks = []
        for k in keys:
            mid = "m-" + slug(k)
            em = " data-emissions" if emissions else ""
            checks.append(
                f'<div class="check mod"><input type="checkbox" id="{mid}" name="modulos" value="{esc(k)}"{em}>'
                f'<label for="{mid}"><span>{esc(MODULES[k][0])}</span></label></div>'
            )
        note = '<p class="small">Uso exclusivo em competição ou fora da via pública.</p>' if emissions else ""
        cls = "module-group emissions" if emissions else "module-group"
        groups_html.append(f'<div class="{cls}"><h3>{title}</h3>{note}{"".join(checks)}</div>')
    modules = "\n          ".join(groups_html)

    vehicle = "\n          ".join([
        field("f-viatura", "viatura", "Marca e modelo", True, placeholder="ex.: Volkswagen Golf VII"),
        field("f-matricula", "matricula", "Matrícula", True, placeholder="ex.: AA-00-AA",
              extra=' maxlength="15" autocomplete="off" autocapitalize="characters" spellcheck="false"'),
        field("f-motor", "motor", "Motor", placeholder="ex.: 2.0 TDI 150 cv"),
        field("f-ano", "ano", "Ano", placeholder="ex.: 2017",
              extra=' inputmode="numeric" pattern="[0-9]{4}" maxlength="4" title="Ano com 4 dígitos"'),
        field("f-ecu", "ecu", "ECU", True, placeholder="ex.: Bosch EDC17C64"),
        field("f-ferramenta", "ferramenta", "Ferramenta de leitura", placeholder="ex.: KESS3, Autotuner, Flex"),
        '<div class="field"><label for="f-metodo">Método de leitura</label><select id="f-metodo" name="metodo">'
        '<option value="">Escolher</option><option>OBD</option><option>Bancada</option><option>Boot</option><option>Outro</option>'
        "</select></div>",
    ])
    return f"""<div class="pedido">
    <form class="form" id="form-pedido">
      <p class="hint">Os campos com <span class="req">*</span> são obrigatórios.</p>
      <fieldset class="fieldset">
        <legend>Viatura e centralina</legend>
        <div class="grid-2">
          {vehicle}
        </div>
      </fieldset>
      <fieldset class="fieldset">
        <legend>Módulos pretendidos <span class="req" aria-hidden="true">*</span></legend>
        <div class="modules">
          {modules}
        </div>
        <div class="declaration" id="decl-wrap" hidden>
          <div class="check"><input type="checkbox" id="f-declaracao" name="declaracao_emissoes" value="sim"><label for="f-declaracao">Declaro que os módulos de sistemas de emissões se destinam a um veículo de competição ou a uso fora da via pública.</label></div>
        </div>
      </fieldset>
      <fieldset class="fieldset">
        <legend>Ficheiro e observações</legend>
        <div class="field"><label for="f-ficheiro">Ficheiro original <span class="req" aria-hidden="true">*</span></label><input id="f-ficheiro" name="ficheiro" type="file" required aria-describedby="f-ficheiro-hint"><p class="hint" id="f-ficheiro-hint">Envie o ficheiro tal como a ferramenta o gravou, sem alterações. Para correção de checksum ou revisão de mapa, envie o ficheiro modificado e, se tiver o original, junte os dois num .zip. Máximo {MAX_MB} MB.</p></div>
        <div class="field"><label for="f-mensagem">Observações</label><textarea id="f-mensagem" name="observacoes" maxlength="2000" placeholder="Sintomas, peças alteradas, códigos de erro…"></textarea></div>
      </fieldset>
      <fieldset class="fieldset">
        <legend>Entrega do ficheiro modificado</legend>
        {entrega_radios("f-entrega")}
        <div class="field" id="f-whatsapp-wrap" hidden><label for="f-whatsapp">Número de WhatsApp</label><input id="f-whatsapp" name="whatsapp" type="tel" autocomplete="tel" placeholder="ex.: 912 345 678"></div>
        <p class="hint">O ficheiro fica sempre disponível em Pedidos.</p>
      </fieldset>
      <div class="resumo" id="f-resumo" data-estado="vazio" aria-live="polite">
        <div><span class="small muted">Desconto no envio</span><strong id="f-total">–</strong></div>
        <div><span class="small muted">Saldo atual</span><strong id="f-saldo-atual">–</strong></div>
        <p class="resumo-msg" id="f-resumo-msg">Escolha os módulos pretendidos.</p>
        <p class="small muted resumo-nota">O custo final depende da ECU. Se for maior, avisamos e a diferença é descontada do saldo.</p>
      </div>
      <div class="actions"><button class="btn btn-primary" type="submit" id="f-enviar">Enviar pedido</button></div>
      <div class="progress" id="f-progresso" hidden><div class="progress-bar"><span id="f-progresso-barra"></span></div><p class="small" id="f-progresso-txt"></p></div>
      <p class="status" role="status" aria-live="polite" hidden></p>
    </form>
    <aside class="aside">
      <div class="aside-block">
        <h2>Antes de enviar</h2>
        <ul class="checklist">
          <li>Guarde o ficheiro original em mais de um sítio.</li>
          <li>Mantenha a tensão estável durante a leitura, com carregador ou estabilizador ligado.</li>
          <li>Indique a ferramenta e o método usados.</li>
          <li>Se a viatura tem avarias registadas, refira-as nas observações.</li>
        </ul>
      </div>
      <div class="aside-block">
        <h2>Depois do envio</h2>
        <ol class="aside-steps">
          <li>Descontam-se <span data-preco="minimo_txt"></span> do saldo. Depois de enviado o ficheiro, o pedido já não pode ser cancelado.</li>
          <li>Analisamos a ECU e confirmamos o custo final. Se for maior, a diferença é descontada do saldo; se o saldo não chegar, o pedido espera pelo carregamento.</li>
          <li>Entregamos o ficheiro pela via que escolheu, normalmente em menos de 2 horas. Fica também disponível em Pedidos durante {esc(DADOS['prazo_ficheiros'])}.</li>
          <li>Se não for possível fazer o ficheiro, recusamos o pedido e os tokens voltam ao saldo.</li>
        </ol>
      </div>
    </aside>
  </div>"""


def entrega_radios(prefix, name="entrega"):
    opcoes = [
        ("portal", "Na área de cliente, com aviso por email"),
        ("email", "Por email, com o ficheiro em anexo"),
        ("whatsapp", "Por WhatsApp"),
    ]
    itens = "".join(
        f'<div class="check"><input type="radio" id="{prefix}-{v}" name="{name}" value="{v}"{" checked" if v == "portal" else ""}>'
        f'<label for="{prefix}-{v}">{t}</label></div>'
        for v, t in opcoes
    )
    return f'<div class="choices">{itens}</div>'


def catalogo_dados():
    """Catálogo público (vai no HTML): sem preços. Os preços chegam à área de cliente pela API, só com sessão."""
    modulos = {k: {"nome": nome, "emissoes": k in EMISSOES} for k, (nome, _desc) in MODULES.items()}
    return {"modulos": modulos, "maxMb": MAX_MB}


def precos_origem():
    """Os mesmos campos que garc_precos() em app/conteudos.php, com os valores de origem (para demo.js)."""
    pagamentos = []
    if DADOS["mbway"]:
        pagamentos.append({"tipo": "mbway", "nome": "MB WAY", "valor": DADOS["mbway"]})
    if DADOS["stripe"]:
        pagamentos.append({"tipo": "cartao", "nome": "Cartão", "url": DADOS["stripe"]})
    if DADOS["paypal"]:
        pagamentos.append({"tipo": "paypal", "nome": "PayPal", "url": paypal_url(), "valor": paypal_url().removeprefix("https://")})
    return {
        "token": TOKEN_EUR, "token_txt": eur(TOKEN_EUR), "minimo": TOKENS_MINIMO, "minimo_txt": tokens_txt(TOKENS_MINIMO),
        "tabela": [{"tokens": n, "tokens_txt": tokens_txt(n), "preco_txt": eur(n * TOKEN_EUR)} for n in EXEMPLOS_CARREGAMENTO],
        "iva": DADOS["iva"], "validade": DADOS["validade_tokens"], "sob_consulta": SOB_CONSULTA,
        "entrega": DADOS["entrega"], "meios_txt": meios_txt(), "pagamentos": pagamentos,
    }


def catalogo_script():
    dados = catalogo_dados()
    dados["urls"] = {"admin": url("admin"), "areaCliente": url("area-cliente")}
    if PREVIEW:
        dados["precosDemo"] = precos_origem()
    texto = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/json" id="catalogo">{texto}</script>'


def php_str(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def catalogo_php():
    """Catálogo usado pela API em PHP: módulos, tokens mínimos por pedido e tamanho máximo dos ficheiros."""
    linhas = [
        f"        {php_str(k)} => ['nome' => {php_str(nome)}, 'emissoes' => {'true' if k in EMISSOES else 'false'}],"
        for k, (nome, _d) in MODULES.items()
    ]
    return ("<?php\n// Gerado por build.py a partir de MODULES e TOKENS_MINIMO. Não editar à mão.\n"
            f"return [\n    'max_mb' => {MAX_MB},\n    'minimo' => {TOKENS_MINIMO},\n    'modulos' => [\n"
            + "\n".join(linhas) + "\n    ],\n];\n")


# ---------------------------------------------------------------- preços (só na área de cliente)

def painel_precos():
    """Separador Preços da área de cliente. Os valores chegam pela API, só com sessão de conta aprovada
    (portal.js preenche os elementos com data-preco), e por isso não ficam no HTML da página."""
    wa = (f'<a href="{esc(whatsapp_url("Olá! Quero saber o custo de um ficheiro para esta ECU:"))}" target="_blank" rel="noopener">WhatsApp</a>'
          if DADOS["whatsapp"] else ph("número de WhatsApp"))
    return f"""<div class="saldo-grid">
          <div class="stack">
            <h3>Tokens</h3>
            <div class="table-wrap"><table class="price-table">
              <thead><tr><th scope="col">Carregamento</th><th scope="col">Preço</th></tr></thead>
              <tbody id="p-tabela-precos"></tbody>
            </table></div>
            <p class="small muted">1 token = <span data-preco="token_txt"></span>. Pode carregar qualquer quantidade a partir de <span data-preco="minimo_txt"></span>. <span data-preco="iva"></span>. Validade: <span data-preco="validade"></span>.</p>
          </div>
          <div class="stack">
            <h3>Quanto custa cada pedido</h3>
            <p>O custo depende da ECU e dos módulos pedidos.</p>
            <ol class="aside-steps">
              <li>No envio do ficheiro descontam-se <span data-preco="minimo_txt"></span> do saldo.</li>
              <li>Depois de analisarmos a ECU, confirmamos o custo final aqui e por email. Se for maior, a diferença é descontada do saldo. Se o saldo não chegar, o pedido fica à espera até carregar a diferença.</li>
              <li>Depois de enviado o ficheiro, o pedido não pode ser cancelado e os tokens não são devolvidos. Se não for possível fazer o ficheiro, recusamos o pedido e os tokens voltam ao saldo.</li>
            </ol>
            <h3>Sob consulta</h3>
            <p class="note"><span data-preco="sob_consulta"></span>: o custo é dado caso a caso. Fale connosco antes de enviar o ficheiro, por {wa} ou por email.</p>
            <h3>Prazo de entrega</h3>
            <p><span data-preco="entrega"></span>. O horário de atendimento está na página <a href="{url('servicos')}">Serviços</a>.</p>
          </div>
        </div>"""


# ---------------------------------------------------------------- área de cliente e administração

def auth_views(prefix, lado=True):
    lado_html = """
      <div class="auth-side">
        <h2>Ainda não tem conta?</h2>
        <p>A área de cliente é para oficinas e profissionais do setor automóvel. Depois do registo, aprovamos a conta e avisamos por email.</p>
        <div class="actions"><a class="btn btn-secondary" href="#registo">Criar conta</a></div>
      </div>""" if lado else ""
    return f"""<div class="auth" id="v-entrar" hidden>
      <div class="auth-card">
        <h2>Entrar</h2>
        <form class="form" id="f-entrar-email">
          <div class="field"><label for="{prefix}-email">Email da conta</label><input id="{prefix}-email" name="email" type="email" autocomplete="email" required></div>
          <p class="hint">Enviamos um código de acesso para este email. Não há palavra-passe.</p>
          <div class="actions"><button class="btn btn-primary" type="submit">Enviar código</button></div>
          <p class="status" role="status" aria-live="polite" hidden></p>
        </form>
        <form class="form" id="f-entrar-codigo" hidden>
          <p>Se <strong data-email-mostra></strong> tiver uma conta ativa, recebe um código de 6 dígitos, válido durante 10 minutos.</p>
          <div class="field"><label for="{prefix}-codigo">Código</label><input id="{prefix}-codigo" name="codigo" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{{6}}" maxlength="6" required></div>
          <div class="actions"><button class="btn btn-primary" type="submit">Entrar</button><button class="btn btn-secondary" type="button" data-outro-email>Usar outro email</button></div>
          <p class="status" role="status" aria-live="polite" hidden></p>
        </form>
      </div>{lado_html}
    </div>"""


def sem_php(preview):
    """True no site publicado enquanto o alojamento não tiver PHP corrigido (ver SEM_PHP)."""
    return SEM_PHP and not preview


def aviso_sem_php(titulo, texto):
    return page_head(titulo) + f"""
<section class="section">
  <div class="wrap">
    <p class="note">{texto}</p>
  </div>
</section>"""


def body_area_cliente(preview):
    if sem_php(preview):
        return aviso_sem_php("Área de cliente", "A área de cliente está temporariamente indisponível, enquanto o servidor "
                             f"recebe uma atualização de segurança. Entretanto, pode contactar-nos por WhatsApp ou para {email_html()}.")
    registo_campos = "\n            ".join([
        field("r-nome", "nome", "Oficina ou empresa", True, extra=' autocomplete="organization" maxlength="120"'),
        field("r-nif", "nif", "NIF", True, extra=' inputmode="numeric" maxlength="20"'),
        field("r-responsavel", "responsavel", "Nome do responsável", True, extra=' autocomplete="name" maxlength="120"'),
        field("r-email", "email", "Email", True, "email", extra=' autocomplete="email"'),
        field("r-telefone", "telefone", "Telefone", True, "tel", extra=' autocomplete="tel"'),
        field("r-whatsapp", "whatsapp", "WhatsApp, se for outro número", kind="tel"),
    ])
    return f"""<section class="page-head">
  <div class="wrap portal-top">
    <div class="portal-title">
      <h1>Área de cliente</h1>
      <p class="lead" id="p-sub">Envie ficheiros, acompanhe os pedidos e consulte o saldo de tokens.</p>
    </div>
    <div class="saldo-box" id="p-saldo-box" hidden>
      <span class="small muted">Saldo</span>
      <strong class="saldo-num" id="p-saldo">0</strong>
      <span class="small">tokens</span>
    </div>
  </div>
</section>

<section class="section portal">
  <div class="wrap">
    <p class="muted" id="p-carregar">A carregar…</p>
    {auth_views("e")}
    <div id="v-registo" hidden>
      <div class="auth">
        <div class="auth-card">
          <h2>Criar conta</h2>
          <form class="form" id="f-registo">
            <div class="grid-2">
            {registo_campos}
            </div>
            <fieldset class="fieldset">
              <legend>Entrega preferida dos ficheiros</legend>
              {entrega_radios("r-entrega")}
            </fieldset>
            <div class="hp" aria-hidden="true"><label for="r-site">Não preencher</label><input id="r-site" name="website" tabindex="-1" autocomplete="off"></div>
            <div class="check"><input id="r-termos" name="termos" type="checkbox" value="sim" required><label for="r-termos">Aceito os <a href="{url('termos')}">termos de utilização</a> e li a <a href="{url('privacidade')}">política de privacidade</a>.</label></div>
            <div class="actions"><button class="btn btn-primary" type="submit">Criar conta</button><a class="btn btn-secondary" href="#entrar">Já tenho conta</a></div>
            <p class="status" role="status" aria-live="polite" hidden></p>
          </form>
        </div>
        <div class="auth-side">
          <h2>Depois do registo</h2>
          <ol class="aside-steps">
            <li>Aprovamos a conta e avisamos por email.</li>
            <li>Entra com o email: enviamos um código de acesso.</li>
            <li>Carrega tokens e envia o primeiro pedido.</li>
          </ol>
        </div>
      </div>
    </div>
    <div id="v-painel" hidden>
      <nav class="tabs" aria-label="Secções da área de cliente">
        <a href="#pedidos" data-tab="pedidos">Pedidos</a>
        <a href="#novo" data-tab="novo">Novo pedido</a>
        <a href="#saldo" data-tab="saldo">Saldo</a>
        <a href="#precos" data-tab="precos">Preços</a>
        <a href="#conta" data-tab="conta">Conta</a>
        <button class="tab-out" type="button" data-sair>Sair</button>
      </nav>
      <div class="panel" data-panel="pedidos">
        <div class="panel-head"><h2>Pedidos</h2><a class="btn btn-primary" href="#novo">Novo pedido</a></div>
        <p class="status" id="p-aviso" role="status" aria-live="polite" hidden></p>
        <div class="orders" id="p-pedidos"></div>
      </div>
      <div class="panel" data-panel="novo" hidden>
        <div class="panel-head"><h2>Novo pedido</h2><a href="#precos">Ver preços</a></div>
        {form_novo_pedido()}
      </div>
      <div class="panel" data-panel="saldo" hidden>
        <div class="panel-head"><h2>Saldo</h2></div>
        <div class="saldo-grid">
          <div class="stack">
            <h3>Carregar saldo</h3>
            <ol class="aside-steps">
              <li>Escolha quantos tokens quer, a partir de <span data-preco="minimo_txt"></span>, e pague por <span data-preco="meios_txt"></span>.</li>
              <li>Na descrição do pagamento, indique o NIF da oficina.</li>
              <li>Depois de confirmarmos o pagamento, carregamos os tokens e enviamos a fatura por email.</li>
            </ol>
            <dl class="spec" id="p-pagamentos"></dl>
          </div>
          <div class="stack">
            <h3>Preços</h3>
            <p>1 token custa <strong data-preco="token_txt"></strong>. A tabela e as regras estão em <a href="#precos">Preços</a>.</p>
          </div>
        </div>
        <h3>Extrato</h3>
        <div id="p-extrato"></div>
      </div>
      <div class="panel" data-panel="precos" hidden>
        <div class="panel-head"><h2>Preços</h2></div>
        {painel_precos()}
      </div>
      <div class="panel" data-panel="conta" hidden>
        <div class="panel-head"><h2>Conta</h2></div>
        <div class="about">
          <dl class="spec" id="p-conta-dados"></dl>
          <form class="form" id="f-conta">
            {field("c-telefone", "telefone", "Telefone", True, "tel", extra=' autocomplete="tel"')}
            {field("c-whatsapp", "whatsapp", "WhatsApp", kind="tel")}
            <fieldset class="fieldset">
              <legend>Entrega preferida dos ficheiros</legend>
              {entrega_radios("c-entrega")}
            </fieldset>
            <p class="hint">Para alterar o nome, o NIF ou o email da conta, contacte-nos.</p>
            <div class="actions"><button class="btn btn-primary" type="submit">Guardar alterações</button></div>
            <p class="status" role="status" aria-live="polite" hidden></p>
          </form>
        </div>
      </div>
    </div>
  </div>
</section>"""


def body_admin(preview):
    if sem_php(preview):
        return aviso_sem_php("Administração", "O painel está temporariamente indisponível, enquanto o servidor não tiver o PHP 8 corrigido.")
    return f"""<section class="page-head">
  <div class="wrap"><h1>Administração</h1><p class="lead">Contas das oficinas, tokens e pedidos.</p></div>
</section>

<section class="section portal admin">
  <div class="wrap">
    <p class="muted" id="p-carregar">A carregar…</p>
    {auth_views("a", lado=False)}
    <div id="v-painel" hidden>
      <nav class="tabs" aria-label="Secções do painel">
        <a href="#pedidos" data-tab="pedidos">Pedidos <span class="count" id="a-n-pedidos"></span></a>
        <a href="#oficinas" data-tab="oficinas">Oficinas <span class="count" id="a-n-oficinas"></span></a>
        <button class="tab-out" type="button" data-sair>Sair</button>
      </nav>
      <div class="panel" data-panel="pedidos">
        <div class="filters" role="group" aria-label="Filtrar pedidos" id="a-filtro-pedidos">
          <button type="button" data-filtro="tratar" aria-pressed="true">Por tratar</button>
          <button type="button" data-filtro="a_aguardar_ficheiro" aria-pressed="false">À espera do ficheiro</button>
          <button type="button" data-filtro="a_aguardar_saldo" aria-pressed="false">Falta saldo</button>
          <button type="button" data-filtro="concluido" aria-pressed="false">Concluídos</button>
          <button type="button" data-filtro="fechado" aria-pressed="false">Recusados e cancelados</button>
          <button type="button" data-filtro="todos" aria-pressed="false">Todos</button>
        </div>
        <div class="split">
          <div class="list" id="a-pedidos"></div>
          <div class="detail" id="a-pedido" hidden></div>
        </div>
      </div>
      <div class="panel" data-panel="oficinas" hidden>
        <div class="filters" role="group" aria-label="Filtrar oficinas" id="a-filtro-oficinas">
          <button type="button" data-filtro="pendente" aria-pressed="true">Por aprovar</button>
          <button type="button" data-filtro="aprovada" aria-pressed="false">Aprovadas</button>
          <button type="button" data-filtro="todas" aria-pressed="false">Todas</button>
        </div>
        <div class="split">
          <div class="list" id="a-oficinas"></div>
          <div class="detail" id="a-oficina" hidden></div>
        </div>
      </div>
    </div>
  </div>
</section>"""


# ---------------------------------------------------------------- loja

def body_loja(preview):
    cards = []
    for i in range(1, 4):
        cards.append(f"""<article class="product">
        <div class="product-img" role="img" aria-label="Fotografia do produto por definir">{ph("fotografia")}</div>
        <div class="product-body">
          <h2>{ph(f"produto {i}")}</h2>
          <p class="muted">{ph("descrição curta")}</p>
          <p class="price">{ph("preço")}</p>
          <a class="btn btn-secondary" href="{esc(contacto_url(f'Loja: produto {i}'))}">Pedir informação</a>
        </div>
      </article>""")
    return page_head("Loja", "Produtos para oficinas. Peça informação sobre preço e disponibilidade.") + f"""

<section class="section">
  <div class="wrap">
    <div class="products">
      {"".join(cards)}
    </div>
  </div>
</section>"""


# ---------------------------------------------------------------- notícias

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]
LISTA_RE = re.compile(r"^[-*•]\s+")


def ler_noticia(texto, nome, alterado):
    """Igual a garc_ler_noticia em app/conteudos.php: cabeçalho (Título, Data) até à primeira linha vazia."""
    linhas = texto.lstrip("\ufeff").splitlines()
    titulo, data = "", None
    while linhas and linhas[0].strip():
        m_t = re.match(r"\s*t[ií]tulo\s*:(.*)$", linhas[0], re.I)
        m_d = re.match(r"\s*data\s*:(.*)$", linhas[0], re.I)
        if m_t:
            titulo = m_t.group(1).strip()
        elif m_d:
            t = m_d.group(1).strip()
            if (m := re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", t)):
                data = f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}"
            elif (m := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)):
                data = f"{int(m[1]):04d}-{int(m[2]):02d}-{int(m[3]):02d}"
        else:
            break
        linhas.pop(0)
    if not titulo:
        while linhas and not linhas[0].strip():
            linhas.pop(0)
        if not linhas:
            return None
        titulo = linhas.pop(0).strip()
    blocos = []
    for b in re.split(r"\n\s*\n", "\n".join(linhas).strip()):
        ls = [x.strip() for x in b.strip().split("\n")] if b.strip() else []
        if not ls:
            continue
        if all(LISTA_RE.match(x) for x in ls):
            blocos.append(("lista", [LISTA_RE.sub("", x).strip() for x in ls]))
        else:
            blocos.append(("paragrafo", ls))
    import datetime
    return {"titulo": titulo, "data": data or datetime.date.fromtimestamp(alterado).isoformat(),
            "ficheiro": nome, "blocos": blocos}


def texto_noticia(t):
    t = esc(t)
    def ligar(m):
        url_ = m.group(0).rstrip(".,;:!?)")
        return f'<a href="{url_}" target="_blank" rel="noopener">{url_}</a>' + m.group(0)[len(url_):]
    return re.sub(r"https?://[^\s<>\"']+", ligar, t)


def noticias_html_origem():
    """Notícias de origem (app/conteudos-iniciais/noticias), com o mesmo HTML de garc_noticias_html()."""
    lista = []
    for f in sorted((CONTEUDOS_INICIAIS / "noticias").glob("*.txt")):
        if f.name.startswith("_"):
            continue
        n = ler_noticia(f.read_text(encoding="utf-8"), f.name, f.stat().st_mtime)
        if n:
            lista.append(n)
    lista.sort(key=lambda n: n["ficheiro"])
    lista.sort(key=lambda n: n["data"], reverse=True)
    if not lista:
        return '<p class="muted">Ainda não há notícias.</p>'
    html_, usadas = "", set()
    for n in lista:
        base = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", n["titulo"]).encode("ascii", "ignore").decode().lower()).strip("-") or "noticia"
        ident, i = base, 2
        while ident in usadas:
            ident, i = f"{base}-{i}", i + 1
        usadas.add(ident)
        corpo = ""
        for tipo, itens in n["blocos"]:
            if tipo == "lista":
                corpo += "\n        <ul>" + "".join(f"\n          <li>{texto_noticia(x)}</li>" for x in itens) + "\n        </ul>"
            else:
                corpo += "\n        <p>" + "<br>".join(texto_noticia(x) for x in itens) + "</p>"
        a, m, d = (int(x) for x in n["data"].split("-"))
        html_ += (f'\n      <article class="article" id="{ident}">'
                  f'\n        <time datetime="{n["data"]}">{d} de {MESES[m - 1]} de {a}</time>'
                  f'\n        <h2>{esc(n["titulo"])}</h2>{corpo}\n      </article>')
    return '<div class="articles">' + html_ + "\n    </div>"


def body_noticias(preview):
    """Notícias: um ficheiro por notícia em garc-conteudos/noticias, no servidor, lidas no momento por
    app/conteudos.php. Na pré-visualização aparecem as notícias de origem (app/conteudos-iniciais/noticias)."""
    if PAGINA_PHP:
        lista = "<?= isset($garc_noticias) ? $garc_noticias : '<p class=\"muted\">Ainda não há notícias.</p>' ?>"
    else:
        lista = noticias_html_origem()
    return page_head("Notícias", "Notas técnicas para oficinas e novidades da GARC.") + f"""

<section class="section">
  <div class="wrap">
    {lista}
  </div>
</section>"""


# ---------------------------------------------------------------- páginas legais

def body_privacidade(preview):
    _, human = UPDATED
    return page_head("Política de privacidade", extra=f'\n    <p class="muted">Última atualização: {human}</p>') + f"""

<section class="section">
  <div class="wrap prose">
    <h2>Responsável pelo tratamento</h2>
    <p>{esc(FIRMA)}, NIPC {val('nipc', 'NIPC')}, com sede na {val('morada', 'morada da sede')}. Contacto para questões de privacidade: {email_html()}.</p>
    <h2>Dados recolhidos</h2>
    <p>No formulário de contacto: nome, email, telefone e a mensagem escrita.</p>
    <p>Na área de cliente: nome da oficina, NIF, nome do responsável, email, telefone e WhatsApp; dados das viaturas (incluindo a matrícula) e das centralinas; ficheiros enviados e entregues; movimentos de saldo; e registos de acesso (códigos de entrada e sessões). Os ficheiros de centralina podem conter o número de identificação da viatura (VIN).</p>
    <p>Para proteger os formulários contra abusos, o registo, o contacto e o pedido de código de entrada guardam durante 24 horas um código derivado do endereço IP, que não é usado para mais nada.</p>
    <h2>Finalidades</h2>
    <p>Gerir as contas das oficinas, responder a contactos, prestar o serviço pedido, gerir o saldo de tokens e cumprir obrigações legais, como a faturação.</p>
    <h2>Fundamento legal</h2>
    <p>Diligências pré-contratuais e execução do contrato (artigo 6.º, n.º 1, alínea b), do Regulamento Geral sobre a Proteção de Dados) e cumprimento de obrigações legais (alínea c) da mesma norma). A proteção dos formulários contra abusos assenta no interesse legítimo da empresa na segurança do site (alínea f) da mesma norma).</p>
    <h2>Prazos de conservação</h2>
    <ul>
      <li>Pedidos sem seguimento, em que o ficheiro não chegou a ser enviado: {val('prazo_pedidos', 'prazo dos pedidos sem seguimento')}. Depois são cancelados.</li>
      <li>Ficheiros de centralina, originais e modificados: {val('prazo_ficheiros', 'prazo dos ficheiros de centralina')} depois de o pedido ser concluído, recusado ou cancelado. Depois são apagados automaticamente.</li>
      <li>Dados de clientes, pedidos e faturação: pelo prazo legal de conservação dos documentos contabilísticos.</li>
    </ul>
    <h2>Destinatários</h2>
    <p>Os dados são acessíveis aos fornecedores que prestam à empresa os serviços de alojamento do site, armazenamento de ficheiros e envio de email, apenas para esse fim e ao abrigo de contrato.{plataformas_txt()} Alguns destes fornecedores podem tratar dados fora do Espaço Económico Europeu, com as garantias previstas no RGPD. A empresa não vende nem cede dados para fins de marketing.</p>
    <h2>Direitos dos titulares</h2>
    <p>Pode pedir o acesso, a retificação, o apagamento, a limitação ou a portabilidade dos seus dados, ou opor-se ao tratamento, através de {email_html()}. Pode também apresentar reclamação à Comissão Nacional de Proteção de Dados (<a href="https://www.cnpd.pt/" target="_blank" rel="noopener">www.cnpd.pt</a>).</p>
    <h2>Cookies</h2>
    <p>A área de cliente usa um cookie de sessão, necessário para manter a sessão iniciada. O site não usa cookies de publicidade nem de estatística. Os tipos de letra estão alojados no próprio site.</p>
  </div>
</section>"""


def body_termos(preview):
    _, human = UPDATED
    return page_head("Termos de utilização", extra=f'\n    <p class="muted">Última atualização: {human}</p>') + f"""

<section class="section">
  <div class="wrap prose">
    <h2>Identificação</h2>
    <p>Este site pertence à {esc(FIRMA)}, com sede na {val('morada', 'morada da sede')}, {registo_html()}. Contacto: {email_html()}.</p>
    <h2>Destinatários</h2>
    <p>Os serviços de ficheiros destinam-se a oficinas e a profissionais do setor automóvel.</p>
    <h2>Pedidos e ficheiros</h2>
    <p>Cada ficheiro é preparado para a viatura, a ECU e a leitura indicadas no pedido e não deve ser usado noutra viatura. O cliente é responsável pela leitura e pela escrita, por guardar o ficheiro original e por confirmar que a viatura está em bom estado mecânico.</p>
    <h2>Módulos de sistemas de emissões</h2>
    <p>Os módulos de desativação de sistemas de emissões (DPF, EGR, AdBlue/SCR e sondas lambda) destinam-se exclusivamente a veículos de competição ou a uso fora da via pública. Ao pedi-los, o cliente declara essa finalidade e assume a responsabilidade pela utilização do ficheiro.</p>
    <h2>Contas</h2>
    <p>A área de cliente é para oficinas e profissionais do setor automóvel. As contas são aprovadas pela empresa e o acesso faz-se com um código enviado para o email registado. A empresa pode suspender uma conta em caso de uso indevido.</p>
    <h2>Tokens e saldo</h2>
    <p>Os ficheiros pagam-se com tokens pré-pagos. O preço do token e o carregamento mínimo estão na área de cliente, em Preços, para as contas aprovadas. Os tokens são carregados na conta depois de confirmado o pagamento, e a fatura é enviada por email.</p>
    <p>No envio de um pedido desconta-se do saldo o número de tokens indicado na área de cliente. O custo final depende da ECU e é comunicado depois de analisado o ficheiro. Se for maior, a diferença é descontada do saldo; se o saldo não chegar, o pedido fica suspenso até a diferença ser carregada. Depois de enviado o ficheiro, o pedido não pode ser cancelado e os tokens não são devolvidos. Se a empresa recusar o pedido, os tokens voltam ao saldo.</p>
    <ul>
      <li>Validade dos tokens: {dado('validade', 'validade dos tokens')}.</li>
      <li>Saldo não usado: {val('reembolso', 'regra para o saldo não usado')}.</li>
      <li>Algumas unidades são sob consulta: o custo é dado caso a caso, antes do envio do ficheiro.</li>
    </ul>
    <h2>Preços, pagamento e prazos</h2>
    <p>Os preços estão na área de cliente, em Preços. O pagamento faz-se por {dado('meios_txt', 'meios de pagamento')}, sempre antes do envio dos ficheiros. Prazo normal de entrega: {dado('entrega', 'prazo de entrega dos ficheiros')}. O horário de atendimento está na página <a href="{url('servicos')}">Serviços</a>.</p>
    <h2>Responsabilidade</h2>
    <p>A empresa não responde por danos resultantes de leituras incorretas, de escrita interrompida, da utilização do ficheiro noutra viatura ou de avarias mecânicas preexistentes.</p>
    <h2>Reclamações</h2>
    <p>Está disponível o <a href="https://www.livroreclamacoes.pt/" target="_blank" rel="noopener">Livro de Reclamações Eletrónico</a>.</p>
    <h2>Lei aplicável</h2>
    <p>Estes termos regem-se pela lei portuguesa.</p>
  </div>
</section>"""


def body_404(preview):
    actions = (f'\n    <div class="actions"><a class="btn btn-primary" href="{url("index")}">Ir para o início</a>'
               f'<a class="btn btn-secondary" href="{url("area-cliente", "#novo")}">Enviar ficheiro</a></div>')
    return page_head("Página não encontrada", "O endereço pode estar errado ou a página já não existe.", actions)


# ---------------------------------------------------------------- montagem

PAGES = [
    {"file": "index.html", "nav": "inicio", "title": COMPANY,
     "desc": "Eletrónica automóvel e diagnóstico para oficinas: ficheiros de calibração entregues em menos de 2 horas, diagnóstico avançado e apoio técnico. GARC – AutoSolutions & Consulting, desde 2001.",
     "body": body_index, "whatsapp": False},
    {"file": "servicos.html", "nav": "servicos", "title": f"Serviços | {COMPANY}",
     "desc": "Chiptuning, admissão e escape, correções, sistemas de emissões e diagnóstico avançado para oficinas.",
     "body": body_servicos, "php": True},
    {"file": "area-cliente.html", "nav": "area-cliente", "title": f"Área de cliente | {COMPANY}",
     "desc": "Envie ficheiros, acompanhe pedidos e consulte o saldo de tokens.",
     "body": body_area_cliente, "noindex": True, "scripts": ["assets/app.js", "assets/portal.js"]},
    {"file": "admin.html", "nav": "", "title": f"Administração | {COMPANY}",
     "desc": "Painel de administração da área de cliente.",
     "body": body_admin, "noindex": True, "scripts": ["assets/app.js", "assets/admin.js"], "whatsapp": False},
    # Loja oculta por agora: a página não é gerada nem aparece no menu. Para a mostrar, tirar "oculta"
    # e voltar a pôr ("loja", "", "Loja", "loja") em NAV.
    {"file": "loja.html", "nav": "loja", "title": f"Loja | {COMPANY}",
     "desc": "Produtos para oficinas da GARC – Soluções Técnicas.",
     "body": body_loja, "oculta": True},
    {"file": "noticias.html", "nav": "noticias", "title": f"Notícias | {COMPANY}",
     "desc": "Notas técnicas para oficinas e novidades da GARC – Soluções Técnicas.",
     "body": body_noticias, "php": True, "php_extra": "$garc_noticias = garc_noticias_html();"},
    {"file": "sobre.html", "nav": "sobre", "title": f"Sobre | {COMPANY}",
     "desc": "A GARC está no mercado desde 2001 e dedica-se à eletrónica automóvel: ficheiros de calibração, diagnóstico avançado e apoio técnico a oficinas.",
     "body": body_sobre, "whatsapp": False, "php": True},
    {"file": "contacto.html", "nav": "contacto", "title": f"Contacto | {COMPANY}",
     "desc": "Envie uma mensagem à GARC – Soluções Técnicas pelo formulário de contacto.",
     "body": body_contacto, "whatsapp": False},
    {"file": "privacidade.html", "nav": "", "title": f"Política de privacidade | {COMPANY}",
     "desc": "Política de privacidade da GARC – Soluções Técnicas.",
     "body": body_privacidade},
    {"file": "termos.html", "nav": "", "title": f"Termos de utilização | {COMPANY}",
     "desc": "Termos de utilização do site da GARC – Soluções Técnicas.",
     "body": body_termos, "php": True},
    {"file": "404.html", "nav": "", "title": f"Página não encontrada | {COMPANY}",
     "desc": "A página pedida não existe.",
     "body": body_404, "noindex": True, "site_only": True},
]

# Configuração do Apache no alojamento cPanel (ficheiro site/.htaccess)
DOMINIO = "www.autosolutions.pt"
HTACCESS = r"""# Gerado por build.py. Não editar à mão.
Options -Indexes -MultiViews
DirectoryIndex index.html index.php
ErrorDocument 404 /404.html

<IfModule mod_rewrite.c>
  RewriteEngine On

  # Endereço único: https://www.autosolutions.pt
  RewriteCond %{HTTP_HOST} ^autosolutions\.pt$ [NC]
  RewriteRule ^ https://www.autosolutions.pt%{REQUEST_URI} [R=301,L]
  RewriteCond %{HTTP_HOST} ^www\.autosolutions\.pt$ [NC]
  RewriteCond %{HTTPS} !=on
  RewriteRule ^ https://www.autosolutions.pt%{REQUEST_URI} [R=301,L]

  # Os preços passaram para a área de cliente (só para contas aprovadas)
  RewriteRule ^precos(\.html)?/?$ /area-cliente#precos [R=301,NE,L]

@@REGRAS_PHP@@
  # Endereços sem .html: /contacto mostra contacto.html
  RewriteCond %{REQUEST_FILENAME} !-f
  RewriteCond %{REQUEST_FILENAME} !-d
  RewriteCond %{REQUEST_FILENAME}.html -f
  RewriteRule ^(.+?)/?$ $1.html [L]
</IfModule>

<IfModule mod_headers.c>
  Header always set X-Content-Type-Options "nosniff"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header always set X-Frame-Options "DENY"
  Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
  <FilesMatch "\.woff2$">
    Header set Cache-Control "public, max-age=31536000, immutable"
  </FilesMatch>
</IfModule>

<IfModule mod_mime.c>
  AddType font/woff2 .woff2
  AddType image/svg+xml .svg
</IfModule>
@@BLOQUEIO_PHP@@"""

REGRAS_PHP = r"""  # Páginas em PHP (com valores alteráveis no servidor): /servicos mostra servicos.php, e o servicos.html
  # antigo, se ainda estiver no servidor, leva para /servicos
  RewriteCond %{DOCUMENT_ROOT}/$1.php -f
  RewriteRule ^(.+)\.html$ /$1 [R=301,L]
  RewriteCond %{REQUEST_FILENAME} !-f
  RewriteCond %{REQUEST_FILENAME} !-d
  RewriteCond %{REQUEST_FILENAME}.php -f
  RewriteRule ^(.+?)/?$ $1.php [L]
"""

# Modo sem PHP (SEM_PHP): nenhum ficheiro PHP corre, nem os que tenham ficado no servidor de versões anteriores.
BLOQUEIO_PHP = r"""
# Sem PHP até o alojamento ter PHP 8 corrigido (SEM_PHP em build.py)
<FilesMatch "\.(php[0-9]?|phtml|phar)$">
  <IfModule mod_authz_core.c>
    Require all denied
  </IfModule>
  <IfModule !mod_authz_core.c>
    Order allow,deny
    Deny from all
  </IfModule>
</FilesMatch>
"""


def htaccess():
    sem = SEM_PHP
    return (HTACCESS.replace("@@REGRAS_PHP@@", "" if sem else REGRAS_PHP)
            .replace("@@BLOQUEIO_PHP@@", BLOQUEIO_PHP if sem else ""))


# Início das páginas em PHP: carrega autosolutions-app/conteudos.php (valores de garc-conteudos/dados.txt e
# notícias). Se a aplicação faltar, o PHP for anterior a 7.1 ou houver qualquer erro, a página não falha:
# mostra os valores de origem gravados nela (e o erro fica no registo do PHP). Sem sintaxe de PHP 7 ou 8,
# para funcionar mesmo que o domínio fique com uma versão antiga do PHP.
def php_cabecalho(extra=""):
    extra = f"\n        {extra}" if extra else ""
    return f"""<?php
// Gerado por build.py. Não editar à mão.
$garc_dados = array();
$garc_noticias = null;
try {{
    $garc_app = getenv('GARC_APP');
    if (!$garc_app) {{
        $garc_app = dirname(__DIR__) . '/autosolutions-app';
    }}
    if (PHP_VERSION_ID >= 70100 && @is_file($garc_app . '/conteudos.php')) {{
        require_once $garc_app . '/conteudos.php';
        $garc_dados = garc_dados();{extra}
    }}
}} catch (Exception $e) {{
    error_log('GARC conteúdos: ' . $e->getMessage());
}} catch (Throwable $e) {{
    error_log('GARC conteúdos: ' . $e->getMessage());
}}
function garc_v($chave, $padrao)
{{
    global $garc_dados;
    $v = isset($garc_dados[$chave]) && is_scalar($garc_dados[$chave]) ? (string) $garc_dados[$chave] : '';
    return htmlspecialchars($v !== '' ? $v : $padrao, ENT_QUOTES, 'UTF-8');
}}
?>
"""


# Páginas que existiam em .html e deixaram de existir: o ficheiro antigo é substituído por um aviso que leva
# ao endereço certo, para não ficar conteúdo desatualizado (como preços) em public_html.
SUBSTITUIDAS = {"precos.html": "area-cliente#precos"}


def aviso_mudanca(destino):
    alvo = "/" + destino
    return f"""<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={esc(alvo)}">
<title>{esc(COMPANY)}</title>
</head>
<body>
<p><a href="{esc(alvo)}">Continuar</a></p>
</body>
</html>
"""


def build(out_dir, preview):
    global PREVIEW, PAGINA_PHP
    PREVIEW = preview
    MISSING.clear()
    OCULTOS.clear()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    # O modo de demonstração (demo.js) só existe na pré-visualização.
    shutil.copytree(SRC / "assets", out_dir / "assets", ignore=None if preview else shutil.ignore_patterns("demo.js"))
    for page in PAGES:
        if page.get("oculta") or (preview and page.get("site_only")):
            continue
        PAGINA_PHP = bool(page.get("php")) and not sem_php(preview) and not preview
        texto = document(page, preview)
        nome = page["file"]
        if PAGINA_PHP:
            nome = nome.removesuffix(".html") + ".php"
            texto = php_cabecalho(page.get("php_extra", "")) + texto
            # o .html antigo desta página, se ficar no servidor, passa a levar para o endereço certo
            (out_dir / page["file"]).write_text(aviso_mudanca(page["file"].removesuffix(".html")), encoding="utf-8")
        (out_dir / nome).write_text(texto, encoding="utf-8")
    PAGINA_PHP = False
    if not preview:
        for antigo, destino in SUBSTITUIDAS.items():
            (out_dir / antigo).write_text(aviso_mudanca(destino), encoding="utf-8")
        shutil.copytree(SRC / "api", out_dir / "api")
        shutil.copy(SRC / "assets" / "favicon.ico", out_dir / "favicon.ico")  # pedido por omissão dos browsers
        (out_dir / ".htaccess").write_text(htaccess(), encoding="utf-8")
        (ROOT / "app").mkdir(exist_ok=True)
        (ROOT / "app" / "catalogo.php").write_text(catalogo_php(), encoding="utf-8")
    return list(MISSING), list(OCULTOS)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "--com-php":
        # Site completo, com PHP (para os testes), numa pasta à parte; não mexe em site/ nem em preview/.
        SEM_PHP = False
        build(Path(sys.argv[2]), preview=False)
        print(f"Gerado com PHP: {sys.argv[2]}")
        sys.exit(0)
    build(ROOT / "preview", preview=True)
    missing, ocultos = build(ROOT / "site", preview=False)
    print("Gerado: site/ e preview/")
    if SEM_PHP:
        print("Modo sem PHP ativo (SEM_PHP): site estático, .php recusados, área de cliente e contacto com aviso.")
    if missing:
        print("Por preencher (aparece a amarelo no site):")
        for item in missing:
            print("  -", item)
    if ocultos:
        print("Oculto no site até ser preenchido:")
        for item in ocultos:
            print("  -", item)
