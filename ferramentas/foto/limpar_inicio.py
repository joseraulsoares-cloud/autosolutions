#!/usr/bin/env python3
"""Limpa a fotografia da página inicial (Pexels 8664308): tira emblemas, a inscrição e a placa do modelo,
as matrículas e a marca das máquinas de soldar. A licença da Pexels não cobre marcas nem permite sugerir
que a marca do carro está associada à GARC.

Uso: python3 ferramentas/foto/limpar_inicio.py ORIGINAL.jpg LIMPA.jpg
Depois: python3 ferramentas/foto/frase_parede.py LIMPA.jpg COM_FRASE.jpg
        python3 ferramentas/foto/preparar.py COM_FRASE.jpg inicio --estreito 1480,0,4398,3648
(o recorte ao alto, 4:5, é o que aparece nos telemóveis; deixa margem à esquerda da frase)
As coordenadas são do original da Pexels (5472 x 3648 px).
"""
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from limpar import desfocar, preencher  # noqa: E402


def limpar(origem, destino):
    im = Image.open(origem).convert("RGB")
    desfocar(im, (4140, 2180, 4295, 2445), raio=18, escurecer=0.55)   # matrícula do carro
    desfocar(im, (135, 1962, 260, 2012), raio=10, escurecer=0.3)      # matrícula do carro azul
    preencher(im, (4068, 1672, 4192, 1748))                            # inscrição da marca na traseira
    preencher(im, (2198, 2343, 2288, 2433), circulo=True, margem=10, pena=6)   # emblema da roda de trás
    preencher(im, (1031, 2141, 1079, 2189), circulo=True, margem=8, pena=5)    # centro da roda da frente
    preencher(im, (1600, 2368, 1734, 2450))                            # placa lateral com o modelo
    preencher(im, (4262, 1622, 4394, 1706), amostra=(4290, 1600, 4370, 1616))  # marca da máquina de cima
    preencher(im, (4398, 2110, 4552, 2176), amostra=(4420, 2094, 4530, 2106))  # marca da máquina de baixo
    im.save(destino, quality=95)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    limpar(sys.argv[1], sys.argv[2])
