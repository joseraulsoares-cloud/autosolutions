#!/usr/bin/env python3
"""Pinta a frase «O automóvel fala. Nós ouvimos.» na parede da fotografia da página inicial,
como letra manuscrita a tinta clara, no espaço da parede entre a câmara de vigilância e o pneu.

Uso: python3 ferramentas/foto/frase_parede.py LIMPA.jpg COM_FRASE.jpg
Ordem completa: limpar_inicio.py -> frase_parede.py -> preparar.py (comando em limpar_inicio.py).

A letra é a Sacramento (fontes/, licença SIL OFL 1.1 em fontes/OFL-Sacramento.txt), desenhada pelo
Chrome (Playwright) e depois "pintada": bordas um pouco irregulares, névoa leve à volta, densidade
variável, cor que segue a luz da parede e a textura da parede por baixo da tinta.
As coordenadas são do original da Pexels (5472 x 3648 px). O resultado é sempre igual (semente fixa).
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from scipy.ndimage import gaussian_filter, map_coordinates

FONTE = Path(__file__).resolve().parent / "fontes" / "sacramento-latin-400-normal.woff2"
LINHAS = ("O automóvel fala.", "Nós ouvimos.")
X_ESQUERDA = 2170        # onde começa a frase (à direita da aresta da parede)
Y_BASE = 1127            # ponto mais baixo da tinta (acima do pneu encostado à parede)
LARGURA = 660            # largura da frase; a altura acompanha (cabe entre a câmara e o pneu)
ANGULO = 2.5             # graus: a linha sobe ligeiramente para a direita, como escrita à mão
COR = (240, 236, 228)    # branco quente, como tinta e não como luz
OPACIDADE = 0.9
NEVOA = 0.16             # tinta pulverizada à volta das letras
SEMENTE = 7


def desenhar_mascara(destino: Path, tamanho=200, traco=5, entrelinha=0.9, recuo=0.6):
    """Frase a branco sobre fundo transparente, desenhada pelo Chrome (com a fonte e os seus acentos)."""
    html = f"""<!doctype html><meta charset=utf-8><style>
@font-face {{ font-family: f; src: url('{FONTE.as_uri()}'); }}
html, body {{ margin: 0; background: transparent; }}
#t {{ display: inline-block; padding: {tamanho * 0.4}px; font: {tamanho}px/{entrelinha} f; color: #fff;
      -webkit-text-stroke: {traco}px #fff; white-space: nowrap; }}
#t span {{ display: block; }} #t span + span {{ padding-left: {recuo}em; }}
</style><div id=t><span>{LINHAS[0]}</span><span>{LINHAS[1]}</span></div>"""
    pagina = destino.with_suffix(".html")
    pagina.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/google-chrome")
        pg = browser.new_page(viewport={"width": 4000, "height": 1500})
        pg.goto(pagina.as_uri())
        pg.wait_for_timeout(500)
        pg.locator("#t").screenshot(path=str(destino), omit_background=True)
        browser.close()


def pintar(imagem: Image.Image, mascara: Image.Image) -> Image.Image:
    rng = np.random.default_rng(SEMENTE)
    m = mascara.getchannel("A")
    m = m.crop(m.getbbox())
    m = m.resize((LARGURA, round(m.height * LARGURA / m.width)), Image.LANCZOS)
    m = m.rotate(ANGULO, resample=Image.BICUBIC, expand=True)
    y0 = int(Y_BASE - m.height)
    margem = 80
    caixa = (X_ESQUERDA - margem, y0 - margem, X_ESQUERDA + m.width + margem, y0 + m.height + margem)
    zona = np.asarray(imagem.crop(caixa)).astype(np.float32)
    h, w, _ = zona.shape
    M = np.zeros((h, w), np.float32)
    M[margem:margem + m.height, margem:margem + m.width] = np.asarray(m, np.float32) / 255
    # bordas um pouco irregulares, como tinta em spray
    dy = gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), 3) * 6
    dx = gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), 3) * 6
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    M = map_coordinates(M, [yy + dy, xx + dx], order=1)
    nucleo = np.clip((gaussian_filter(M, 1.3) - 0.08) / 0.84, 0, 1)
    nevoa = gaussian_filter(M, 10) * NEVOA
    densidade = 0.86 + 0.14 * np.clip(gaussian_filter(rng.random((h, w)).astype(np.float32), 20) * 8 - 3.5, 0, 1)
    alfa = np.clip(nucleo * OPACIDADE * densidade + nevoa * (1 - nucleo), 0, 1)[..., None]
    # a tinta recebe a mesma luz que a parede (mais escura na sombra) e deixa ver a textura
    luz = gaussian_filter(zona.mean(axis=2), 35)[..., None]
    textura = zona - np.stack([gaussian_filter(zona[..., c], 2.5) for c in range(3)], axis=2)
    tinta = np.array(COR, np.float32) * np.clip(0.62 + 0.38 * luz / 200, 0.45, 1.05) + textura * 0.7
    resultado = zona * (1 - alfa) + tinta * alfa
    final = imagem.copy()
    final.paste(Image.fromarray(np.clip(resultado, 0, 255).astype(np.uint8)), caixa[:2])
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
