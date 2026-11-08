#!/usr/bin/env python3
"""Vetoriza o logótipo da GARC (PNG 640x640, fundo branco) em camadas de cor com o potrace.

Uso: vetorizar.py <logo.png> <pasta de saída>

Saída: pecas.json com, para cada bloco (marca, palavra, lema) e cor (azul, cinza, prata),
o caminho SVG em unidades da imagem ampliada 4x e a posição do bloco.
"""
import json
import pathlib
import re
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

S = 4  # ampliação antes de vetorizar (curvas mais suaves)
D_AZUL, D_CINZA, D_PRATA = 223.0, 187.0, 96.0  # "escuridão" medida de cada cor (255 - luminância)

src = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

im = Image.open(src).convert("RGB")
W, H = im.size
up = np.asarray(im.resize((W * S, H * S), Image.LANCZOS)).astype(float)
lum = 0.299 * up[..., 0] + 0.587 * up[..., 1] + 0.114 * up[..., 2]
D = 255.0 - lum
BR = up[..., 2] - up[..., 0]
r = BR / np.maximum(D, 1.0)

# Azul: tom azulado (B-R proporcional à escuridão), com pelo menos 50% de cobertura.
azul = (r > 0.27) & (D >= 0.5 * D_AZUL)

# Cinzentos: separar por componentes ligados; cada componente fica com uma só cor,
# para que as orlas suavizadas do cinzento escuro não virem contornos de cinzento claro.
cinza_tudo = (r <= 0.27) & (D >= 40)
lab, n = ndimage.label(cinza_tudo, structure=np.ones((3, 3)))
perto_azul = ndimage.binary_dilation(azul, iterations=2 * S)
cinza = np.zeros_like(azul)
prata = np.zeros_like(azul)
idx = np.arange(1, n + 1)
areas = ndimage.sum(np.ones_like(D), lab, idx)
medD = ndimage.median(D, lab, idx)
toca = ndimage.maximum(perto_azul.astype(float), lab, idx)
relatorio = []
for i, area, md, t in zip(idx, areas, medD, toca):
    comp = lab == i
    if md >= 205:
        # Traço azul fino que perdeu a cor na compressão JPEG (mais escuro do que o cinzento).
        azul |= comp & (D >= 0.5 * D_AZUL)
        continue
    if t and area < 2000 * S * S:
        continue  # orla de compressão encostada ao azul
    if md >= (D_CINZA + D_PRATA) / 2:
        cinza |= comp & (D >= 0.5 * D_CINZA)
        cor = "cinza"
    else:
        if area < 400 * S * S:
            continue  # orlas soltas: o prateado só existe na faixa grande
        prata |= comp & (D >= 0.5 * D_PRATA)
        cor = "prata"
    ys, xs = np.where(comp)
    relatorio.append((cor, int(area), round(float(md)), xs.min() // S, ys.min() // S, xs.max() // S, ys.max() // S))

for linha in sorted(relatorio, key=lambda x: -x[1])[:4]:
    print("componente", linha)


def suavizar(mask):
    """Tira o serrilhado da compressão: desfoca a máscara e volta a cortar a 50%."""
    return ndimage.gaussian_filter(mask.astype(float), sigma=0.8 * S) >= 0.5


azul, cinza, prata = suavizar(azul), suavizar(cinza), suavizar(prata)

# Blocos na imagem original: marca (G, carro e formas cinzentas), palavra (GARC) e lema.
BLOCOS = {"marca": (0, 400), "palavra": (400, 505), "lema": (505, H)}
CAMADAS = {"azul": azul, "cinza": cinza, "prata": prata}

pecas = {}
for bloco, (y0, y1) in BLOCOS.items():
    for cor, mask in CAMADAS.items():
        m = mask[y0 * S:y1 * S]
        if m.sum() < 10:
            continue
        ys, xs = np.where(m)
        bx0, by0, bx1, by1 = xs.min() - 2, ys.min() - 2, xs.max() + 3, ys.max() + 3
        crop = m[by0:by1, bx0:bx1]
        pbm = out / f"{bloco}_{cor}.pbm"
        Image.fromarray(np.where(crop, 0, 255).astype(np.uint8)).convert("1").save(pbm)
        svg = out / f"{bloco}_{cor}.svg"
        subprocess.run(["potrace", "-b", "svg", "-t", str(8 * S), "-a", "1.0", "-O", "1.0", "-u", "1",
                        "--flat", "-o", str(svg), str(pbm)], check=True)
        texto = svg.read_text()
        d = " ".join(re.findall(r'<path d="([^"]+)"', texto)).replace("\n", " ")
        d = re.sub(r"\s+", " ", d).strip()
        g = re.search(r'<g transform="([^"]+)"', texto).group(1)
        pecas.setdefault(bloco, {})[cor] = {
            "d": d,
            "g": g,  # transformação do potrace (inverte o eixo y)
            "x": int(bx0),
            "y": int(by0 + y0 * S),
            "w": int(bx1 - bx0),
            "h": int(by1 - by0),
        }
        print(f"{bloco:8s} {cor:6s} caixa x{bx0 // S}-{bx1 // S} y{(by0 // S) + y0}-{(by1 // S) + y0}  {len(d)} carateres")

(out / "pecas.json").write_text(json.dumps(pecas))
print("ok:", out / "pecas.json")
