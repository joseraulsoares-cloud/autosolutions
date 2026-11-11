"""Funções para tirar emblemas, marcas e matrículas de uma fotografia (preencher com a cor à volta ou desfocar)."""
import random
from PIL import Image, ImageDraw, ImageFilter, ImageStat


def _mascara(w, h, pena, circulo=False):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    (d.ellipse if circulo else d.rectangle)((pena, pena, w - pena, h - pena), fill=255)
    return m.filter(ImageFilter.GaussianBlur(pena / 1.5))


def preencher(im, caixa, margem=14, pena=8, circulo=False, amostra=None):
    x1, y1, x2, y2 = caixa
    if amostra:  # zona escolhida à mão com a cor certa
        cor = tuple(int(v) for v in ImageStat.Stat(im.crop(amostra)).median)
    else:
        aneis = [(x1 - margem, y1 - margem, x2 + margem, y1), (x1 - margem, y2, x2 + margem, y2 + margem),
                 (x1 - margem, y1, x1, y2), (x2, y1, x2 + margem, y2)]
        cores = [ImageStat.Stat(im.crop(a)).median for a in aneis]
        cor = tuple(sorted(c[i] for c in cores)[len(cores) // 2] for i in range(3))
    w, h = x2 - x1, y2 - y1
    remendo = Image.new("RGB", (w, h), cor)
    grao = Image.effect_noise((w, h), 10).convert("RGB")
    remendo = Image.blend(remendo, grao, 0.05)
    im.paste(remendo, (x1, y1), _mascara(w, h, pena, circulo))


def desfocar(im, caixa, raio=16, pena=6, escurecer=0.0):
    x1, y1, x2, y2 = caixa
    pad = raio * 3
    zona = im.crop((x1 - pad, y1 - pad, x2 + pad, y2 + pad)).filter(ImageFilter.GaussianBlur(raio))
    zona = zona.crop((pad, pad, pad + x2 - x1, pad + y2 - y1))
    if escurecer:
        zona = Image.blend(zona, Image.new("RGB", zona.size, (12, 12, 14)), escurecer)
    im.paste(zona, (x1, y1), _mascara(x2 - x1, y2 - y1, pena))
