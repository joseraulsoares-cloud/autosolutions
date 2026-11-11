#!/usr/bin/env python3
"""Prepara a fotografia da página inicial para o site.

Uso: python3 ferramentas/foto/preparar.py ORIGEM.jpg [NOME] [--estreito X0,Y0,X1,Y1]

Gera src/assets/fotos/NOME-{1280,1920,2560}.webp e .jpg (NOME por omissão: "inicio"),
sem metadados (localização, máquina, etc.) e com a orientação já aplicada.

Com --estreito, gera também NOME-estreito-{800,1200,1600}.webp e .jpg, um recorte ao alto
(caixa em píxeis do original, de preferência na proporção 4:5) para telemóveis e ecrãs ao alto:
assim o telemóvel recebe só a parte que mostra, nítida, em vez de ampliar um pedaço da fotografia larga.
O build usa o recorte automaticamente quando os ficheiros existem.

Depois, em build.py, pôr DADOS["foto_inicio"] = "fotos/NOME" e correr python3 build.py.

Precisa do Pillow (pip install pillow).
"""
import sys
from pathlib import Path

from PIL import Image, ImageOps

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "src" / "assets" / "fotos"
LARGURAS = (1280, 1920, 2560)          # as mesmas de FOTO_LARGURAS em build.py
LARGURAS_ESTREITO = (800, 1200, 1600)  # as mesmas de FOTO_LARGURAS_ESTREITO em build.py


def gravar(imagem, nome, larguras):
    if imagem.width < larguras[-1]:
        print(f"Aviso: {nome} tem {imagem.width} px de largura; o ideal são {larguras[-1]} px ou mais.")
    for largura in larguras:
        alvo = imagem if imagem.width <= largura else imagem.resize(
            (largura, round(imagem.height * largura / imagem.width)), Image.LANCZOS)
        # WebP com qualidade alta: evita degraus nos degradês escuros
        for ext, opcoes in (("webp", {"quality": 90, "method": 6}),
                            ("jpg", {"quality": 82, "optimize": True, "progressive": True})):
            ficheiro = DESTINO / f"{nome}-{largura}.{ext}"
            alvo.save(ficheiro, **opcoes)  # sem exif=: os metadados não passam para o site
            print(f"{ficheiro.relative_to(RAIZ)}  {alvo.width}x{alvo.height}  {ficheiro.stat().st_size // 1024} KB")


def preparar(origem: Path, nome: str = "inicio", estreito=None):
    imagem = ImageOps.exif_transpose(Image.open(origem)).convert("RGB")
    DESTINO.mkdir(parents=True, exist_ok=True)
    gravar(imagem, nome, LARGURAS)
    if estreito:
        gravar(imagem.crop(estreito), f"{nome}-estreito", LARGURAS_ESTREITO)


if __name__ == "__main__":
    args = sys.argv[1:]
    caixa = None
    if "--estreito" in args:
        i = args.index("--estreito")
        caixa = tuple(int(v) for v in args[i + 1].split(","))
        del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    preparar(Path(args[0]), args[1] if len(args) > 1 else "inicio", caixa)
