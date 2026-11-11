#!/usr/bin/env python3
"""Gera a imagem original da página inicial: um coupé inventado (não é nenhum modelo real), de perfil,
num espaço escuro com luz baixa, nos tons da GARC (azul-marinho e prateado), com espaço livre em cima,
à esquerda, para a frase.

Uso: python3 ferramentas/foto/gerar_inicio.py [SAIDA.jpg]
Depois: python3 ferramentas/foto/preparar.py SAIDA.jpg  (gera os tamanhos para o site)

Precisa do Playwright com Chrome (para desenhar o SVG) e do Pillow (para o grão de fotografia).
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageFilter

L, A = 2560, 1600          # tamanho da imagem
CHAO = 1240                # linha do chão
R_PNEU, R_JANTE, R_CAVA = 100, 72, 113
RODAS = (1230, 2120)       # centro das rodas traseira e dianteira
Y_RODA = CHAO - R_PNEU
BASE = 1185                # fundo da carroçaria


def carrocaria():
    """Silhueta de perfil (frente à direita). As cavas das rodas desenham-se por cima, à parte."""
    return (f"M950 {BASE} L2380 1180 "
            "C2410 1172 2418 1112 2400 1080 "            # frente
            "C2330 1045 2140 1008 1900 995 "             # capô
            "C1815 975 1730 912 1640 880 "               # para-brisas
            "C1545 856 1430 866 1355 900 "               # tejadilho
            "C1250 950 1115 985 1010 1003 "              # traseira descaída
            "C962 1012 936 1030 930 1060 "
            "C926 1110 930 1160 950 1185 Z")


def roda(cx):
    import math
    raios = "".join(
        f'<line x1="{19 * math.cos(a):.1f}" y1="{19 * math.sin(a):.1f}" x2="{66 * math.cos(a):.1f}" y2="{66 * math.sin(a):.1f}"/>'
        for a in [i * 2 * math.pi / 5 - math.pi / 2 for i in range(5)])
    return f"""<g transform="translate({cx} {Y_RODA})">
      <circle r="{R_PNEU}" fill="#040507"/>
      <circle r="{R_JANTE}" fill="#10151B"/>
      <circle r="52" fill="#0A0D11"/>
      <g stroke="#1F2731" stroke-width="16" stroke-linecap="round">{raios}</g>
      <circle r="{R_JANTE}" fill="none" stroke="#06080B" stroke-width="5"/>
      <path d="M-58 -40 A{R_JANTE - 3} {R_JANTE - 3} 0 0 1 58 -40" fill="none" stroke="#C3CCD6" stroke-opacity=".35" stroke-width="2"/>
      <circle r="10" fill="#1A2029"/>
    </g>"""


def svg():
    corpo = carrocaria()
    linha_topo = ("M2400 1080 C2330 1045 2140 1008 1900 995 C1815 975 1730 912 1640 880 "
                  "C1545 856 1430 866 1355 900 C1250 950 1115 985 1010 1003 C962 1012 936 1030 930 1060")
    janela = ("M1860 1000 C1795 968 1722 922 1645 896 C1560 878 1470 884 1405 905 "
              "C1360 921 1322 946 1292 980 C1480 987 1680 994 1860 1000 Z")
    ombro = "M1760 1050 C1550 1050 1330 1046 1150 1024"
    cavas = "".join(f'<circle cx="{cx}" cy="{Y_RODA}" r="{R_CAVA}" fill="#020305"/>' for cx in RODAS)
    carro = f"""
    <path d="{corpo}" fill="url(#chapa)"/>
    <g clip-path="url(#acima-base)">{cavas}</g>
    {roda(RODAS[0])}{roda(RODAS[1])}
    <path d="{janela}" fill="url(#vidro)"/>
    <path d="M1620 902 C1540 918 1460 946 1400 972" stroke="#B4C3D4" stroke-opacity=".14" stroke-width="12" fill="none" filter="url(#d4)"/>
    <path d="{linha_topo}" fill="none" stroke="url(#luz-topo)" stroke-width="10" stroke-opacity=".45" filter="url(#d6)"/>
    <path d="{linha_topo}" fill="none" stroke="url(#luz-topo)" stroke-width="2.2"/>
    <path d="{ombro}" fill="none" stroke="url(#luz-ombro)" stroke-width="2" filter="url(#brilho)"/>
    {"".join(f'<path d="M{cx - 108} {Y_RODA - 34} A118 118 0 0 1 {cx + 108} {Y_RODA - 34}" fill="none" stroke="#C9D2DC" stroke-opacity=".18" stroke-width="3" filter="url(#d4)"/>' for cx in RODAS)}
    <path d="M1300 1172 C1600 1168 1900 1166 2000 1166" stroke="#AFC0D4" stroke-opacity=".12" stroke-width="3" fill="none" filter="url(#d4)"/>
    <path d="M2318 1086 C2350 1082 2378 1088 2398 1098" stroke="#E8F0FF" stroke-width="5" stroke-linecap="round" fill="none" filter="url(#farol)"/>
    <path d="M936 1046 C952 1040 975 1037 1000 1036" stroke="#8A1A24" stroke-opacity=".9" stroke-width="4" stroke-linecap="round" fill="none" filter="url(#brilho)"/>
    """
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{L}" height="{A}" viewBox="0 0 {L} {A}">
  <defs>
    <radialGradient id="fundo" cx="1660" cy="980" r="1250" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#173A6C"/><stop offset=".38" stop-color="#0A1D3A"/>
      <stop offset=".75" stop-color="#040B17"/><stop offset="1" stop-color="#010307"/>
    </radialGradient>
    <linearGradient id="chao" x1="0" y1="{CHAO - 60}" x2="0" y2="{A}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#010307" stop-opacity="0"/><stop offset=".35" stop-color="#010307" stop-opacity=".55"/>
      <stop offset="1" stop-color="#010307" stop-opacity=".95"/>
    </linearGradient>
    <linearGradient id="chapa" x1="0" y1="850" x2="0" y2="1190" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#1A222C"/><stop offset=".35" stop-color="#0B0F14"/>
      <stop offset=".75" stop-color="#07090C"/><stop offset="1" stop-color="#0E1D36"/>
    </linearGradient>
    <linearGradient id="vidro" x1="0" y1="880" x2="0" y2="1010" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#121A24"/><stop offset="1" stop-color="#040609"/>
    </linearGradient>
    <linearGradient id="luz-topo" x1="930" y1="0" x2="2400" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#EDF2F8" stop-opacity="0"/><stop offset=".3" stop-color="#EDF2F8" stop-opacity=".55"/>
      <stop offset=".5" stop-color="#EDF2F8" stop-opacity="1"/><stop offset=".72" stop-color="#EDF2F8" stop-opacity=".7"/>
      <stop offset="1" stop-color="#EDF2F8" stop-opacity=".08"/>
    </linearGradient>
    <linearGradient id="luz-ombro" x1="1150" y1="0" x2="1760" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#D5DDE7" stop-opacity=".05"/><stop offset=".25" stop-color="#D5DDE7" stop-opacity=".6"/>
      <stop offset="1" stop-color="#D5DDE7" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="desvanecer" x1="0" y1="{CHAO}" x2="0" y2="{CHAO + 300}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#fff" stop-opacity=".8"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </linearGradient>
    <mask id="reflexo"><rect x="0" y="{CHAO}" width="{L}" height="{A - CHAO}" fill="url(#desvanecer)"/></mask>
    <clipPath id="acima-base"><rect x="0" y="0" width="{L}" height="{BASE}"/></clipPath>
    <filter id="d4" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="4"/></filter>
    <filter id="d6" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
    <filter id="d14" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="14"/></filter>
    <filter id="brilho" x="-10%" y="-50%" width="120%" height="200%">
      <feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="farol" x="-50%" y="-300%" width="200%" height="700%">
      <feGaussianBlur stdDeviation="9" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect width="{L}" height="{A}" fill="url(#fundo)"/>
  <rect y="{CHAO - 60}" width="{L}" height="{A - CHAO + 60}" fill="url(#chao)"/>
  <g mask="url(#reflexo)" opacity=".22" filter="url(#d4)">
    <g transform="translate(0 {2 * CHAO}) scale(1 -1)">{carro}</g>
  </g>
  <ellipse cx="1670" cy="{CHAO + 2}" rx="820" ry="22" fill="#000" opacity=".8" filter="url(#d14)"/>
  <rect x="1050" y="{CHAO + 10}" width="1300" height="6" fill="#9FB3CC" opacity=".06" filter="url(#d14)"/>
  {carro}
</svg>"""


def gerar(saida: Path):
    from playwright.sync_api import sync_playwright
    svg_ficheiro = saida.with_suffix(".svg")
    svg_ficheiro.write_text(svg(), encoding="utf-8")
    png = saida.with_suffix(".png")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/google-chrome")
        pagina = browser.new_page(viewport={"width": L, "height": A})
        pagina.goto(svg_ficheiro.resolve().as_uri())
        pagina.screenshot(path=str(png))
        browser.close()
    # Grão fino, como numa fotografia com pouca luz
    imagem = Image.open(png).convert("RGB")
    random.seed(2001)
    ruido = Image.effect_noise((L, A), 18).filter(ImageFilter.GaussianBlur(0.6)).convert("RGB")
    imagem = Image.blend(imagem, ruido, 0.035)
    imagem.save(saida, quality=94)
    print(f"{saida}  {imagem.width}x{imagem.height}")


if __name__ == "__main__":
    gerar(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/garc-inicio.jpg"))
