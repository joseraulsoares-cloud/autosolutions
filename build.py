#!/usr/bin/env python3
"""Gera o site estático da GARC.

    python3 build.py

Saídas:
  site/     versão de produção (a que vai para o alojamento)
  preview/  pré-visualização para revisão (formulários sem envio, aviso de campos por preencher)
"""
import html
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

COMPANY = "GARC – Soluções Técnicas"
FIRMA = "GARC – Soluções Técnicas, Unipessoal Lda"
YEAR = "2026"
UPDATED = ("2026-11-01", "1 de novembro de 2026")
MAX_MB = 25

# Dados da empresa. O que ficar vazio aparece a amarelo no site e é listado no fim da geração.
DADOS = {
    "morada": "",           # morada completa da sede, ex.: "Rua ..., n.º ..., 4410-... Arcozelo, Vila Nova de Gaia"
    "telefone": "",         # ex.: "+351 912 345 678"
    "whatsapp": True,       # o mesmo número atende WhatsApp
    "email": "",            # email da empresa (contactos e privacidade)
    "horario": "",          # ex.: "Segunda a sexta, 9h00–18h00"
    "redes": [],            # ex.: [("Facebook", "https://www.facebook.com/..."), ("Instagram", "https://www.instagram.com/...")]
    "nipc": "",
    "conservatoria": "",    # ex.: "Vila Nova de Gaia"
    "prazo_pedidos": "",    # conservação de pedidos sem seguimento, ex.: "12 meses"
    "prazo_ficheiros": "",  # conservação dos ficheiros de centralina
    "condicoes": "",        # preços, pagamento e prazos (página Termos)
}

PREVIEW = False  # definido por build()
MISSING = []     # campos por preencher encontrados na geração


def esc(text):
    return html.escape(text, quote=True)


def ph(text):
    """Texto por preencher (destacado a amarelo)."""
    if text not in MISSING:
        MISSING.append(text)
    return f'<span class="ph">[{esc(text)}]</span>'


def val(key, label):
    value = DADOS.get(key)
    return esc(value) if value else ph(label)


def url(page, anchor=""):
    """Ligação interna: ficheiro .html na pré-visualização, endereço limpo no site publicado."""
    if PREVIEW:
        return f"{page}.html{anchor}"
    return ("/" if page == "index" else f"/{page}") + anchor


def asset(path):
    return path if PREVIEW else f"/{path}"


def morada_html(sep):
    if DADOS["morada"]:
        return esc(DADOS["morada"])
    return f"{ph('rua e código postal')}{sep}Arcozelo, Vila Nova de Gaia"


def email_html():
    email = DADOS["email"]
    return f'<a href="mailto:{esc(email)}">{esc(email)}</a>' if email else ph("email da empresa")


def telefone_html():
    tel = DADOS["telefone"]
    if not tel:
        return ph("telefone")
    digits = re.sub(r"\D", "", tel)
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 9:  # número português sem indicativo
        digits = "351" + digits
    out = f'<a href="tel:+{digits}">{esc(tel)}</a>'
    if DADOS["whatsapp"]:
        out += f'<br><a href="https://wa.me/{digits}" target="_blank" rel="noopener">Falar no WhatsApp</a>'
    return out


def redes_html():
    redes = DADOS["redes"]
    if not redes:
        return ph("redes sociais")
    return "<br>".join(
        f'<a href="{esc(link)}" target="_blank" rel="noopener">{esc(nome)}</a>' for nome, link in redes
    )


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
]

EMISSIONS_NOTICE = (
    "Os módulos de desativação de sistemas de emissões destinam-se a veículos de competição "
    "ou a uso fora da via pública. Ao pedir um destes módulos, o cliente declara essa finalidade "
    "e assume a responsabilidade pela utilização do ficheiro."
)

# ---------------------------------------------------------------- moldura comum

NAV = [
    ("index", "", "Início", "inicio"),
    ("servicos", "", "Serviços", "servicos"),
    ("loja", "", "Loja", "loja"),
    ("noticias", "", "Notícias", "noticias"),
    ("index", "#sobre", "Sobre", "sobre"),
    (None, "#contacto", "Contacto", "contacto"),
]


def header(active):
    items = []
    for page, anchor, label, key in NAV:
        href = url(page, anchor) if page else anchor
        cur = ' aria-current="page"' if key == active else ""
        items.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    cur = ' aria-current="page"' if active == "pedido" else ""
    items.append(f'<li class="nav-cta"><a href="{url("pedido")}"{cur}>Enviar ficheiro</a></li>')
    nav_items = "\n        ".join(items)
    return f"""<a class="skip" href="#conteudo">Saltar para o conteúdo</a>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="{url('index')}" aria-label="{esc(COMPANY)}, página inicial">
      <span class="brand-mark" aria-hidden="true"><span></span><span></span><span></span><span></span><span></span></span>
      <span class="brand-text"><span class="brand-name">GARC</span><span class="brand-sub">Soluções Técnicas</span></span>
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


def footer(preview):
    return f"""<footer class="site-footer" id="contacto">
  <div class="wrap footer-main">
    <div>
      <h2>Envie uma mensagem</h2>
      <form class="form" id="form-contacto"{form_attrs("/api/contacto", preview)}>
        <div class="grid-2">
          <div class="field"><label for="f-c-nome">Nome <span class="req" aria-hidden="true">*</span></label><input id="f-c-nome" name="nome" autocomplete="given-name" required></div>
          <div class="field"><label for="f-c-apelido">Apelido</label><input id="f-c-apelido" name="apelido" autocomplete="family-name"></div>
          <div class="field"><label for="f-c-email">Email <span class="req" aria-hidden="true">*</span></label><input id="f-c-email" name="email" type="email" autocomplete="email" required></div>
          <div class="field"><label for="f-c-telefone">Telefone</label><input id="f-c-telefone" name="telefone" type="tel" autocomplete="tel"></div>
        </div>
        <div class="field"><label for="f-c-assunto">Assunto</label><input id="f-c-assunto" name="assunto"></div>
        <div class="field"><label for="f-c-mensagem">Mensagem <span class="req" aria-hidden="true">*</span></label><textarea id="f-c-mensagem" name="mensagem" required></textarea></div>
        <div class="check"><input id="f-c-rgpd" name="privacidade" type="checkbox" value="sim" required><label for="f-c-rgpd">Li a <a href="{url('privacidade')}">política de privacidade</a>.</label></div>
        <div class="actions"><button class="btn btn-primary" type="submit">Enviar mensagem</button></div>
        <p class="status" role="status" aria-live="polite" hidden></p>
      </form>
    </div>
    <div>
      <h2>Contactos</h2>
      <dl class="contact-info">
        <div><dt>Morada</dt><dd>{morada_html('<br>')}</dd></div>
        <div><dt>{'Telefone e WhatsApp' if DADOS['whatsapp'] else 'Telefone'}</dt><dd>{telefone_html()}</dd></div>
        <div><dt>Email</dt><dd>{email_html()}</dd></div>
        <div><dt>Horário</dt><dd>{val('horario', 'dias e horas de atendimento')}</dd></div>
        <div><dt>Redes sociais</dt><dd>{redes_html()}</dd></div>
      </dl>
    </div>
  </div>
  <div class="footer-legal">
    <div class="wrap">
      <p>{esc(FIRMA)}. Sede: {morada_html(', ')}. NIPC {val('nipc', 'NIPC')}, matriculada na Conservatória do Registo Comercial de {val('conservatoria', 'conservatória')} sob o mesmo número.</p>
      <ul class="legal-links">
        <li><a class="lre" href="https://www.livroreclamacoes.pt/" target="_blank" rel="noopener">Livro de Reclamações Eletrónico</a></li>
        <li><a href="{url('privacidade')}">Política de privacidade</a></li>
        <li><a href="{url('termos')}">Termos de utilização</a></li>
      </ul>
      <p>© {YEAR} {esc(COMPANY)}</p>
    </div>
  </div>
</footer>"""


def head_tags(title, desc, preview, bare, noindex=False):
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
        f'<link rel="icon" href="{asset("assets/favicon.svg")}" type="image/svg+xml">',
        f'<link rel="preload" href="{asset("assets/fonts/barlow-latin-400-normal.woff2")}" as="font" type="font/woff2" crossorigin>',
        f'<link rel="preload" href="{asset("assets/fonts/barlow-condensed-latin-700-normal.woff2")}" as="font" type="font/woff2" crossorigin>',
        f'<link rel="stylesheet" href="{asset("assets/styles.css")}">',
        f'<script src="{asset("assets/main.js")}" defer></script>',
    ]
    return "\n".join(tags)


def document(page, preview):
    # Na pré-visualização, a página principal é envolvida pelo próprio Artifact (sem doctype/head/body).
    bare = preview and page["file"] == "index.html"
    head = head_tags(page["title"], page["desc"], preview, bare, page.get("noindex", False))
    body = "\n".join([
        header(page["nav"]),
        '<main id="conteudo">',
        page["body"](preview),
        "</main>",
        footer(preview),
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

def calibration_map():
    rpm = [1000, 1500, 2000, 2500, 3000, 3500, 4000]
    # pedal (%), binário de série (Nm), fator do Stage 1 (exemplo)
    rows = [
        (20, [60, 70, 75, 75, 70, 65, 60], 1.00),
        (40, [120, 140, 150, 150, 145, 135, 120], 1.05),
        (60, [180, 215, 230, 230, 220, 205, 185], 1.10),
        (80, [230, 280, 300, 300, 290, 270, 245], 1.15),
        (100, [250, 320, 340, 340, 330, 305, 275], 1.18),
    ]

    def bucket(v):
        return 1 if v < 100 else 2 if v < 180 else 3 if v < 260 else 4 if v < 330 else 5

    head_cells = "".join(f'<th scope="col">{r}</th>' for r in rpm)
    body_rows = []
    stock_max = 0
    for pedal, values, factor in rows:
        cells = []
        for v in values:
            t = int(v * factor + 0.5)
            stock_max = max(stock_max, v)
            cells.append(f'<td class="h{bucket(v)}" data-s="{v}" data-t="{t}">{v}</td>')
        body_rows.append(f'<tr><th scope="row">{pedal}%</th>{"".join(cells)}</tr>')
    rows_html = "\n          ".join(body_rows)
    legend = [("h1", "&lt; 100"), ("h2", "100–179"), ("h3", "180–259"), ("h4", "260–329"), ("h5", "≥ 330")]
    legend_html = "".join(f'<span style="--sw: var(--{k}-bg)">{label}</span>' for k, label in legend)
    return f"""<figure class="map" data-map aria-labelledby="map-title">
      <div class="map-head">
        <div>
          <p class="map-title" id="map-title">Binário pedido</p>
          <p class="map-axis">Nm por posição do pedal e regime do motor</p>
        </div>
        <div class="seg" role="group" aria-label="Calibração mostrada">
          <button type="button" data-variant="s" aria-pressed="true">Série</button>
          <button type="button" data-variant="t" aria-pressed="false">Stage 1</button>
        </div>
      </div>
      <div class="map-scroll">
        <table>
          <caption class="sr-only">Binário pedido, em Nm, por posição do pedal (linhas) e regime do motor em rpm (colunas). Exemplo ilustrativo.</caption>
          <thead><tr><th scope="col">Pedal / rpm</th>{head_cells}</tr></thead>
          <tbody>
          {rows_html}
          </tbody>
        </table>
      </div>
      <div class="map-foot">
        <div>
          <p class="small muted">Binário máximo</p>
          <p class="readout" data-readout aria-live="polite">{stock_max} Nm</p>
        </div>
        <div class="legend" aria-label="Escala de cores, em Nm">{legend_html}</div>
      </div>
      <figcaption>Exemplo ilustrativo de um diesel 2.0, de série e com Stage 1. Os valores reais dependem do motor e da ECU.</figcaption>
    </figure>"""


def body_index(preview):
    svc_rows = [
        ("Chiptuning", "Stage 1 e 2, caixa automática, pop &amp; bangs e ajustes de monitorização.", "chiptuning", ""),
        ("Admissão e escape", "Flaps, válvula de escape, borboleta de admissão (TVA) e medidor de massa de ar.", "admissao-escape", ""),
        ("Correções", "Pressão de óleo, arranque a quente e Start &amp; Stop.", "correcoes", ""),
        ("Sistemas de emissões", "DPF, EGR, AdBlue/SCR e sondas lambda.", "emissoes",
         '<span class="tag">Uso exclusivo em competição ou fora da via pública</span>'),
        ("Diagnóstico avançado", "Avarias intermitentes, pós-tratamento, sensores, atuadores e comunicação entre módulos.", "diagnostico", ""),
    ]
    rows = []
    for title, text, anchor, extra in svc_rows:
        rows.append(
            f'<li class="svc-row"><h3>{title}</h3><div><p>{text}</p>{extra}</div>'
            f'<a href="{url("servicos", "#" + anchor)}">Ver detalhes<span class="sr-only"> de {title}</span></a></li>'
        )
    svc_html = "\n      ".join(rows)
    return f"""<section class="hero">
  <div class="wrap">
    <div class="hero-text">
      <h1>Ficheiros de calibração e diagnóstico avançado para oficinas</h1>
      <p class="lead">Envie a leitura da centralina, indique o que precisa e receba o ficheiro pronto a escrever. Do outro lado está um engenheiro que conhece o motor e a eletrónica.</p>
      <div class="actions">
        <a class="btn btn-primary" href="{url('pedido')}">Enviar ficheiro</a>
        <a class="btn btn-secondary" href="{url('servicos')}">Ver serviços</a>
      </div>
    </div>
    {calibration_map()}
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <h2>Como funciona</h2>
    </div>
    <ol class="steps">
      <li><h3>Leia a centralina</h3><p>Por OBD, bancada ou boot. Guarde sempre o ficheiro original.</p></li>
      <li><h3>Envie o pedido</h3><p>Preencha os dados da viatura, escolha os módulos e anexe a leitura.</p></li>
      <li><h3>Receba o ficheiro</h3><p>Confirmamos o que é possível para essa ECU e enviamos o ficheiro modificado.</p></li>
      <li><h3>Escreva e teste</h3><p>Com apoio técnico, se for preciso.</p></li>
    </ol>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <h2>Serviços</h2>
      <p class="lead">Ficheiros por módulo, preparados para a viatura e a ECU de cada pedido, e diagnóstico para as avarias que pedem mais do que uma leitura de erros.</p>
    </div>
    <ul class="svc-list">
      {svc_html}
    </ul>
  </div>
</section>

<section class="section" id="sobre">
  <div class="wrap about">
    <div class="about-text">
      <h2>Sobre a GARC</h2>
      <p>A GARC – Soluções Técnicas presta serviços técnicos a oficinas: ficheiros de calibração, diagnóstico avançado e apoio em eletrónica automóvel.</p>
      <p>O trabalho assenta em engenharia, com formação em Engenharia Mecânica e mestrado em Eletrotecnia e Computadores. Cada ficheiro é preparado para a viatura, a ECU e a leitura indicadas no pedido.</p>
    </div>
    <dl class="spec">
      <div><dt>Empresa</dt><dd>{esc(FIRMA)}</dd></div>
      <div><dt>Sede</dt><dd>Arcozelo, Vila Nova de Gaia</dd></div>
      <div><dt>Clientes</dt><dd>Oficinas e profissionais do setor automóvel</dd></div>
      <div><dt>Leituras</dt><dd>OBD, bancada e boot</dd></div>
    </dl>
  </div>
</section>

<section class="band">
  <div class="wrap">
    <div class="band-text">
      <h2>Tem uma leitura pronta?</h2>
      <p>Envie-a com os dados da viatura. Respondemos com o que é possível fazer e o preço.</p>
    </div>
    <a class="btn btn-primary" href="{url('pedido')}">Enviar ficheiro</a>
  </div>
</section>"""


# ---------------------------------------------------------------- serviços

def body_servicos(preview):
    sub = "".join(f'<a href="#{a}">{t}</a>' for a, t, *_ in GROUPS) + '<a href="#diagnostico">Diagnóstico avançado</a>'
    parts = [page_head(
        "Serviços",
        "Ficheiros por módulo, preparados para a viatura e a ECU de cada pedido, e diagnóstico avançado para oficinas.",
        f'\n    <nav class="subnav" aria-label="Secções desta página">{sub}</nav>',
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
      <button class="btn btn-primary" type="button" data-subject="Diagnóstico avançado">Pedir diagnóstico</button>
      <a class="btn btn-secondary" href="{url('pedido')}">Enviar ficheiro</a>
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


def body_pedido(preview):
    groups_html = []
    for anchor, title, _intro, keys, emissions in GROUPS:
        checks = []
        for k in keys:
            mid = "m-" + slug(k)
            em = " data-emissions" if emissions else ""
            checks.append(
                f'<div class="check"><input type="checkbox" id="{mid}" name="modulos" value="{esc(k)}"{em}>'
                f'<label for="{mid}">{esc(MODULES[k][0])}</label></div>'
            )
        note = '<p class="small">Uso exclusivo em competição ou fora da via pública.</p>' if emissions else ""
        cls = "module-group emissions" if emissions else "module-group"
        groups_html.append(f'<div class="{cls}"><h3>{title}</h3>{note}{"".join(checks)}</div>')
    modules = "\n          ".join(groups_html)

    contact = "\n          ".join([
        field("f-nome", "nome", "Nome completo", True, extra=' autocomplete="name"'),
        field("f-oficina", "oficina", "Oficina ou empresa", extra=' autocomplete="organization"'),
        field("f-email", "email", "Email", True, "email", extra=' autocomplete="email"'),
        field("f-telefone", "telefone", "Telefone", True, "tel", extra=' autocomplete="tel"'),
    ])
    vehicle = "\n          ".join([
        field("f-viatura", "viatura", "Marca e modelo", True, placeholder="ex.: Volkswagen Golf VII"),
        field("f-motor", "motor", "Motor", placeholder="ex.: 2.0 TDI 150 cv"),
        field("f-ano", "ano", "Ano", placeholder="ex.: 2017",
              extra=' inputmode="numeric" pattern="[0-9]{4}" maxlength="4" title="Ano com 4 dígitos"'),
        field("f-ecu", "ecu", "ECU", True, placeholder="ex.: Bosch EDC17C64"),
        field("f-ferramenta", "ferramenta", "Ferramenta de leitura", placeholder="ex.: KESS3, Autotuner, Flex"),
        '<div class="field"><label for="f-metodo">Método de leitura</label><select id="f-metodo" name="metodo">'
        '<option value="">Escolher</option><option>OBD</option><option>Bancada</option><option>Boot</option><option>Outro</option>'
        "</select></div>",
    ])
    return page_head(
        "Pedido de ficheiro",
        "Preencha os dados da viatura, escolha os módulos e anexe a leitura original. Respondemos por email.",
    ) + f"""

<section class="section">
  <div class="wrap pedido">
    <form class="form" id="form-pedido"{form_attrs("/api/pedido", preview, multipart=True)}>
      <p class="hint">Os campos com <span class="req">*</span> são obrigatórios.</p>
      <fieldset class="fieldset">
        <legend>Contacto</legend>
        <div class="grid-2">
          {contact}
        </div>
      </fieldset>
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
        <div class="field"><label for="f-ficheiro">Ficheiro original <span class="req" aria-hidden="true">*</span></label><input id="f-ficheiro" name="ficheiro" type="file" required aria-describedby="f-ficheiro-hint"><p class="hint" id="f-ficheiro-hint">Envie o ficheiro tal como a ferramenta o gravou, sem alterações. Máximo {MAX_MB} MB.</p></div>
        <div class="field"><label for="f-mensagem">Observações</label><textarea id="f-mensagem" name="mensagem" placeholder="Sintomas, peças alteradas, códigos de erro…"></textarea></div>
      </fieldset>
      <div class="check"><input id="f-rgpd" name="privacidade" type="checkbox" value="sim" required><label for="f-rgpd">Li a <a href="{url('privacidade')}">política de privacidade</a>.</label></div>
      <div class="actions"><button class="btn btn-primary" type="submit">Enviar pedido</button></div>
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
          <li>Recebemos o pedido e o ficheiro.</li>
          <li>Confirmamos por email o que é possível para essa ECU e o preço.</li>
          <li>Enviamos o ficheiro modificado.</li>
        </ol>
      </div>
    </aside>
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
          <button class="btn btn-secondary" type="button" data-subject="Loja: produto {i}">Pedir informação</button>
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

def body_noticias(preview):
    iso, human = UPDATED
    return page_head("Notícias", "Notas técnicas para oficinas e novidades da GARC.") + f"""

<section class="section">
  <div class="wrap">
    <div class="articles">
      <article class="article" id="preparar-leitura">
        <time datetime="{iso}">{human}</time>
        <h2>Como preparar uma leitura antes de enviar o ficheiro</h2>
        <p>Um ficheiro só é tão bom como a leitura de onde parte. Estes cuidados evitam a maior parte dos problemas na escrita.</p>
        <ul>
          <li>Guarde sempre o original, em mais de um sítio, antes de qualquer escrita.</li>
          <li>Mantenha a tensão estável durante a leitura e a escrita, com um carregador ou estabilizador ligado à bateria.</li>
          <li>Quando a ferramenta o permite, faça a leitura completa (flash e EEPROM). Uma leitura parcial por OBD pode não chegar para todas as alterações.</li>
          <li>Anote as referências de hardware e de software da ECU, a ferramenta e o método usados (OBD, bancada ou boot).</li>
          <li>Envie o ficheiro tal como a ferramenta o gravou, sem mudar a extensão nem o alterar noutros programas.</li>
          <li>Se a viatura tem avarias registadas, indique quais. Um ficheiro não resolve uma avaria mecânica.</li>
        </ul>
      </article>
      <article class="article" id="stage-1-stage-2">
        <time datetime="{iso}">{human}</time>
        <h2>Stage 1 e Stage 2: o que muda</h2>
        <p>O Stage 1 é uma recalibração de software para o motor de série: ajustam-se binário, pressão do turbo, injeção e limitadores, com margens pensadas para os componentes originais.</p>
        <p>O Stage 2 parte do mesmo princípio, mas para um motor com alterações físicas já montadas, como admissão, intercooler ou escape. A calibração é feita para essas peças e não deve ser usada sem elas.</p>
        <p>Em ambos os casos, o resultado depende do estado mecânico do motor. Antes de reprogramar, convém confirmar que não há avarias registadas, fugas de ar nem componentes gastos, como a embraiagem, o turbo ou os injetores.</p>
      </article>
    </div>
  </div>
</section>"""


# ---------------------------------------------------------------- páginas legais

def body_privacidade(preview):
    _, human = UPDATED
    return page_head("Política de privacidade", extra=f'\n    <p class="muted">Última atualização: {human}</p>') + f"""

<section class="section">
  <div class="wrap prose">
    <h2>Responsável pelo tratamento</h2>
    <p>{esc(FIRMA)}, com sede em {morada_html(', ')}, NIPC {val('nipc', 'NIPC')}. Contacto para questões de privacidade: {email_html()}.</p>
    <h2>Dados recolhidos</h2>
    <p>Através dos formulários deste site: nome, oficina ou empresa, email, telefone, dados da viatura e da centralina, ficheiros enviados e a mensagem escrita. Os ficheiros de centralina podem conter o número de identificação da viatura (VIN).</p>
    <h2>Finalidades</h2>
    <p>Responder a pedidos de contacto e de ficheiro, preparar orçamentos, prestar o serviço pedido e cumprir obrigações legais, como a faturação.</p>
    <h2>Fundamento legal</h2>
    <p>Diligências pré-contratuais e execução do contrato (artigo 6.º, n.º 1, alínea b), do Regulamento Geral sobre a Proteção de Dados) e cumprimento de obrigações legais (alínea c) da mesma norma).</p>
    <h2>Prazos de conservação</h2>
    <ul>
      <li>Pedidos sem seguimento: {val('prazo_pedidos', 'prazo dos pedidos sem seguimento, ex.: 12 meses')}.</li>
      <li>Dados de clientes e de faturação: pelo prazo legal de conservação dos documentos contabilísticos.</li>
      <li>Ficheiros de centralina: {val('prazo_ficheiros', 'prazo dos ficheiros de centralina')}.</li>
    </ul>
    <h2>Destinatários</h2>
    <p>Os dados são acessíveis aos fornecedores que prestam à empresa os serviços de alojamento do site e de correio eletrónico, apenas para esse fim e ao abrigo de contrato. Alguns destes fornecedores podem tratar dados fora do Espaço Económico Europeu, com as garantias previstas no RGPD. A empresa não vende nem cede dados para fins de marketing.</p>
    <h2>Direitos dos titulares</h2>
    <p>Pode pedir o acesso, a retificação, o apagamento, a limitação ou a portabilidade dos seus dados, ou opor-se ao tratamento, através de {email_html()}. Pode também apresentar reclamação à Comissão Nacional de Proteção de Dados (<a href="https://www.cnpd.pt/" target="_blank" rel="noopener">www.cnpd.pt</a>).</p>
    <h2>Cookies</h2>
    <p>Este site não usa cookies de publicidade nem de estatística. Os tipos de letra estão alojados no próprio site.</p>
  </div>
</section>"""


def body_termos(preview):
    _, human = UPDATED
    return page_head("Termos de utilização", extra=f'\n    <p class="muted">Última atualização: {human}</p>') + f"""

<section class="section">
  <div class="wrap prose">
    <h2>Identificação</h2>
    <p>Este site pertence à {esc(FIRMA)}, com sede em {morada_html(', ')}, NIPC {val('nipc', 'NIPC')}.</p>
    <h2>Destinatários</h2>
    <p>Os serviços de ficheiros destinam-se a oficinas e a profissionais do setor automóvel.</p>
    <h2>Pedidos e ficheiros</h2>
    <p>Cada ficheiro é preparado para a viatura, a ECU e a leitura indicadas no pedido e não deve ser usado noutra viatura. O cliente é responsável pela leitura e pela escrita, por guardar o ficheiro original e por confirmar que a viatura está em bom estado mecânico.</p>
    <h2>Módulos de sistemas de emissões</h2>
    <p>Os módulos de desativação de sistemas de emissões (DPF, EGR, AdBlue/SCR e sondas lambda) destinam-se exclusivamente a veículos de competição ou a uso fora da via pública. Ao pedi-los, o cliente declara essa finalidade e assume a responsabilidade pela utilização do ficheiro.</p>
    <h2>Preços e pagamento</h2>
    <p>{val('condicoes', 'condições de preço, pagamento e prazos')}</p>
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
               f'<a class="btn btn-secondary" href="{url("pedido")}">Enviar ficheiro</a></div>')
    return page_head("Página não encontrada", "O endereço pode estar errado ou a página já não existe.", actions)


# ---------------------------------------------------------------- montagem

PAGES = [
    {"file": "index.html", "nav": "inicio", "title": COMPANY,
     "desc": "Ficheiros de calibração, chiptuning e diagnóstico avançado para oficinas. GARC – Soluções Técnicas, Arcozelo, Vila Nova de Gaia.",
     "body": body_index},
    {"file": "servicos.html", "nav": "servicos", "title": f"Serviços | {COMPANY}",
     "desc": "Chiptuning, admissão e escape, correções, sistemas de emissões e diagnóstico avançado para oficinas.",
     "body": body_servicos},
    {"file": "pedido.html", "nav": "pedido", "title": f"Pedido de ficheiro | {COMPANY}",
     "desc": "Envie a leitura da centralina com os dados da viatura e os módulos pretendidos.",
     "body": body_pedido},
    {"file": "loja.html", "nav": "loja", "title": f"Loja | {COMPANY}",
     "desc": "Produtos para oficinas da GARC – Soluções Técnicas.",
     "body": body_loja},
    {"file": "noticias.html", "nav": "noticias", "title": f"Notícias | {COMPANY}",
     "desc": "Notas técnicas para oficinas e novidades da GARC – Soluções Técnicas.",
     "body": body_noticias},
    {"file": "privacidade.html", "nav": "", "title": f"Política de privacidade | {COMPANY}",
     "desc": "Política de privacidade da GARC – Soluções Técnicas.",
     "body": body_privacidade},
    {"file": "termos.html", "nav": "", "title": f"Termos de utilização | {COMPANY}",
     "desc": "Termos de utilização do site da GARC – Soluções Técnicas.",
     "body": body_termos},
    {"file": "404.html", "nav": "", "title": f"Página não encontrada | {COMPANY}",
     "desc": "A página pedida não existe.",
     "body": body_404, "noindex": True, "site_only": True},
]

# Cabeçalhos HTTP do Cloudflare Pages (ficheiro site/_headers)
HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=()

/assets/fonts/*
  Cache-Control: public, max-age=31536000, immutable
"""


def build(out_dir, preview):
    global PREVIEW
    PREVIEW = preview
    MISSING.clear()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(SRC / "assets", out_dir / "assets")
    for page in PAGES:
        if preview and page.get("site_only"):
            continue
        (out_dir / page["file"]).write_text(document(page, preview), encoding="utf-8")
    if not preview:
        (out_dir / "_headers").write_text(HEADERS, encoding="utf-8")
    return list(MISSING)


if __name__ == "__main__":
    build(ROOT / "preview", preview=True)
    missing = build(ROOT / "site", preview=False)
    print("Gerado: site/ e preview/")
    if missing:
        print("Por preencher (aparece a amarelo no site):")
        for item in missing:
            print("  -", item)
