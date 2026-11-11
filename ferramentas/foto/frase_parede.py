#!/usr/bin/env python3
"""Pinta a frase «O automóvel fala. Nós ouvimos.» na parede da fotografia da página inicial,
a azul, em letra manuscrita, no espaço da parede entre a câmara de vigilância e o pneu,
e com a perspetiva da parede.

Uso: python3 ferramentas/foto/frase_parede.py LIMPA.jpg COM_FRASE.jpg
Ordem completa: limpar_inicio.py -> frase_parede.py -> preparar.py (comandos em limpar_inicio.py).

Perspetiva (medida na fotografia original, 5472 x 3648 px):
- as duas arestas da barra da prateleira, que é paralela à parede, encontram-se em (-31, 1943);
  a família de tubos do teto paralela à parede foge para cerca de (130, 1890). Daí o ponto de
  fuga das horizontais da parede, PONTO_FUGA = (60, 1915), quase à altura do centro (câmara
  praticamente sem inclinação, e as verticais da parede ficam verticais);
- as luminárias do teto são retângulos: as suas duas direções (a 90°) fogem para cerca de
  (130, 1890) e (5000, 1950), o que dá uma distância focal de cerca de 2450 px (grande angular).
A frase é desenhada num retângulo do plano da parede e projetada na imagem: sobe para a direita
como as linhas da parede (cerca de 18° a 21° naquele sítio) e fica um pouco menor à esquerda,
que está mais longe.

A letra é a Sacramento (fontes/, licença SIL OFL 1.1 em fontes/OFL-Sacramento.txt), desenhada pelo
Chrome (Playwright) e depois "pintada": bordas um pouco irregulares, névoa leve à volta, densidade
variável, cor que segue a luz da parede e a textura da parede por baixo da tinta.
O resultado é sempre igual (semente fixa).
"""
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from scipy.ndimage import gaussian_filter, map_coordinates

FONTE = Path(__file__).resolve().parent / "fontes" / "sacramento-latin-400-normal.woff2"
FRASE = "O automóvel fala. Nós ouvimos."

FOCAL = 2450.0                       # píxeis
CENTRO = np.array([2736.0, 1824.0])  # centro da imagem
PONTO_FUGA = np.array([60.0, 1915.0])

X_ESQUERDA = 2185     # início da frase, à direita da aresta da parede
Y_BASE = 1217         # base da frase nesse ponto: centrada na faixa livre entre a câmara e o pneu
LARGURA = 835         # largura na imagem; acaba antes da zona mais escura da parede, por cima dos pneus
AZUL = (17, 92, 214)  # azul forte, da família do azul do logótipo
OPACIDADE = 0.95
NEVOA = 0.14          # tinta pulverizada à volta das letras
SEMENTE = 7


def desenhar_mascara(destino: Path, tamanho=300, traco=9):
    """Frase a branco sobre fundo transparente, desenhada pelo Chrome (com a fonte e os seus acentos)."""
    html = f"""<!doctype html><meta charset=utf-8><style>
@font-face {{ font-family: f; src: url('{FONTE.as_uri()}'); }}
html, body {{ margin: 0; background: transparent; }}
#t {{ display: inline-block; padding: {tamanho * 0.4}px; font: {tamanho}px/0.9 f; color: #fff;
      -webkit-text-stroke: {traco}px #fff; white-space: nowrap; }}
</style><div id=t>{FRASE}</div>"""
    pagina = destino.with_suffix(".html")
    pagina.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/google-chrome")
        pg = browser.new_page(viewport={"width": 5000, "height": 1500})
        pg.goto(pagina.as_uri())
        pg.wait_for_timeout(500)
        pg.locator("#t").screenshot(path=str(destino), omit_background=True)
        browser.close()


def cantos_na_parede(proporcao):
    """Cantos (inferior esquerdo, inferior direito, superior direito, superior esquerdo) na imagem de um
    retângulo do plano da parede com a proporção dada (largura/altura), com o canto inferior esquerdo
    em (X_ESQUERDA, Y_BASE) e a largura LARGURA na imagem."""
    d = np.array([*(PONTO_FUGA - CENTRO), FOCAL])
    d /= np.linalg.norm(d)                       # direção horizontal da parede (para longe, à esquerda)
    cima = np.array([0.0, -1.0, 0.0])
    cima -= cima.dot(d) * d
    cima /= np.linalg.norm(cima)
    direita = -d

    def projetar(P):
        return CENTRO + FOCAL * P[:2] / P[2]

    P0 = 10.0 * np.array([(X_ESQUERDA - CENTRO[0]) / FOCAL, (Y_BASE - CENTRO[1]) / FOCAL, 1.0])
    lo, hi = 0.0, 0.95 * P0[2] / -direita[2]     # sem passar para trás da câmara
    for _ in range(80):
        w = (lo + hi) / 2
        if projetar(P0 + w * direita)[0] - X_ESQUERDA < LARGURA:
            lo = w
        else:
            hi = w
    w, h = lo, lo / proporcao
    return np.array([projetar(P0), projetar(P0 + w * direita),
                     projetar(P0 + w * direita + h * cima), projetar(P0 + h * cima)])


def pintar(imagem: Image.Image, mascara: Image.Image) -> Image.Image:
    rng = np.random.default_rng(SEMENTE)
    m = mascara.getchannel("A")
    m = m.crop(m.getbbox())
    mw, mh = m.size
    cantos = cantos_na_parede(mw / mh)
    margem = 80
    x0, y0 = (np.floor(cantos.min(0)) - margem).astype(int)
    x1, y1 = (np.ceil(cantos.max(0)) + margem).astype(int)
    zona = np.asarray(imagem.crop((x0, y0, x1, y1))).astype(np.float32)
    h, w, _ = zona.shape
    H = cv2.getPerspectiveTransform(np.float32([[0, mh], [mw, mh], [mw, 0], [0, 0]]),
                                    np.float32(cantos - [x0, y0]))
    M = cv2.warpPerspective(np.asarray(m, np.float32) / 255, H, (w, h), flags=cv2.INTER_AREA)
    # bordas um pouco irregulares, como tinta em spray
    dy = gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), 3) * 5
    dx = gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), 3) * 5
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    M = map_coordinates(M, [yy + dy, xx + dx], order=1)
    nucleo = np.clip((gaussian_filter(M, 1.2) - 0.08) / 0.84, 0, 1)
    nevoa = gaussian_filter(M, 9) * NEVOA
    densidade = 0.88 + 0.12 * np.clip(gaussian_filter(rng.random((h, w)).astype(np.float32), 20) * 8 - 3.5, 0, 1)
    alfa = np.clip(nucleo * OPACIDADE * densidade + nevoa * (1 - nucleo), 0, 1)[..., None]
    # a tinta recebe a mesma luz que a parede e deixa ver a textura
    luz = gaussian_filter(zona.mean(axis=2), 35)[..., None]
    textura = zona - np.stack([gaussian_filter(zona[..., c], 2.5) for c in range(3)], axis=2)
    tinta = np.array(AZUL, np.float32) * np.clip(luz / 185, 0.3, 1.12) + textura * 0.6
    resultado = zona * (1 - alfa) + tinta * alfa
    final = imagem.copy()
    final.paste(Image.fromarray(np.clip(resultado, 0, 255).astype(np.uint8)), (int(x0), int(y0)))
    return final


def main(origem, destino):
    imagem = Image.open(origem).convert("RGB")
    with tempfile.TemporaryDirectory() as pasta:
        ficheiro = Path(pasta) / "frase.png"
        desenhar_mascara(ficheiro)
        mascara = Image.open(ficheiro)
        mascara.load()
    pintar(imagem, mascara).save(destino, quality=95)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
