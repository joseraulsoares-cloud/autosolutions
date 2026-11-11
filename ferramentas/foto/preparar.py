#!/usr/bin/env python3
"""Prepara a fotografia da página inicial para o site.

Uso: python3 ferramentas/foto/preparar.py ORIGEM.jpg [NOME]

Gera src/assets/fotos/NOME-{1280,1920,2560}.webp e .jpg (NOME por omissão: "inicio"),
sem metadados (localização, máquina, etc.) e com a orientação já aplicada.
Depois, em build.py, pôr DADOS["foto_inicio"] = "fotos/NOME" e correr python3 build.py.

Precisa do Pillow (pip install pillow).
"""
import sys
from pathlib import Path

from PIL import Image, ImageOps

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "src" / "assets" / "fotos"
LARGURAS = (1280, 1920, 2560)  # as mesmas de FOTO_LARGURAS em build.py


def preparar(origem: Path, nome: str = "inicio"):
    imagem = ImageOps.exif_transpose(Image.open(origem)).convert("RGB")
    if imagem.width < LARGURAS[-1]:
        print(f"Aviso: a fotografia tem {imagem.width} px de largura; o ideal são {LARGURAS[-1]} px ou mais.")
    DESTINO.mkdir(parents=True, exist_ok=True)
    for largura in LARGURAS:
        alvo = imagem if imagem.width <= largura else imagem.resize(
            (largura, round(imagem.height * largura / imagem.width)), Image.LANCZOS)
        for ext, opcoes in (("webp", {"quality": 80, "method": 6}),
                            ("jpg", {"quality": 82, "optimize": True, "progressive": True})):
            ficheiro = DESTINO / f"{nome}-{largura}.{ext}"
            alvo.save(ficheiro, **opcoes)  # sem exif=: os metadados não passam para o site
            print(f"{ficheiro.relative_to(RAIZ)}  {alvo.width}x{alvo.height}  {ficheiro.stat().st_size // 1024} KB")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    preparar(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "inicio")
