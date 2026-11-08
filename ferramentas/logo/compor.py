#!/usr/bin/env python3
"""Compõe os ficheiros do logótipo a partir das peças vetorizadas (pecas.json).

Uso: compor.py <pecas.json> <pasta de saída>

Gera:
- logo-garc.svg            logótipo completo (cores do logótipo), para usar no site e em documentos
- logo-cabecalho.html      SVG para o cabeçalho: peças definidas uma vez, versão larga (com o lema)
                           e versão curta (sem o lema); cores pelas variáveis CSS --logo-*
- favicon.svg, favicon.ico, apple-touch-icon.png
- previsoes/*.svg          versões com cores fixas, só para ver o resultado
"""
import io
import json
import pathlib
import re
import subprocess
import sys

from PIL import Image

pecas = json.loads(pathlib.Path(sys.argv[1]).read_text())
out = pathlib.Path(sys.argv[2])
(out / "previsoes").mkdir(parents=True, exist_ok=True)

CORES = {"azul": "#012559", "cinza": "#414548", "prata": "#9AA0A7"}


def caixa(blocos):
    xs0, ys0, xs1, ys1 = [], [], [], []
    for b in blocos:
        for p in pecas[b].values():
            xs0.append(p["x"]); ys0.append(p["y"]); xs1.append(p["x"] + p["w"]); ys1.append(p["y"] + p["h"])
    return min(xs0), min(ys0), max(xs1), max(ys1)


def caminhos(bloco, cor_de, origem):
    """Caminhos de um bloco, com a origem do bloco em (0, 0)."""
    ox, oy = origem
    partes = []
    for cor in ("prata", "cinza", "azul"):
        p = pecas[bloco].get(cor)
        if not p:
            continue
        tx, ty, sx, sy = map(float, re.findall(r"-?\d+(?:\.\d+)?", p["g"]))
        t = f"translate({p['x'] - ox + tx:g} {p['y'] - oy + ty:g}) scale({sx:g} {sy:g})"
        partes.append(f'<path {cor_de(cor)} transform="{t}" d="{p["d"]}"/>')
    return "".join(partes)


def hexa(cor):
    return f'fill="{CORES[cor]}"'


def var(cor):
    return f'style="fill:var(--logo-{cor})"'


def num(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------- logótipo completo
x0, y0, x1, y1 = caixa(["marca", "palavra", "lema"])
m = 60
completo = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {x1 - x0 + 2 * m} {y1 - y0 + 2 * m}" '
            f'role="img" aria-label="GARC – AutoSolutions &amp; Consulting">'
            f'<g transform="translate({m} {m})">'
            + "".join(f'<g transform="translate({caixa([b])[0] - x0} {caixa([b])[1] - y0})">'
                      f'{caminhos(b, hexa, caixa([b])[:2])}</g>' for b in ("marca", "palavra", "lema"))
            + "</g></svg>\n")
(out / "logo-garc.svg").write_text(completo)

# ---------------------------------------------------------------- cabeçalho (marca + texto, na horizontal)
mx0, my0, mx1, my1 = caixa(["marca"])
px0, py0, px1, py1 = caixa(["palavra"])
lx0, ly0, lx1, ly1 = caixa(["lema"])
tx0, ty0, tx1, ty1 = caixa(["palavra", "lema"])
MW, MH = mx1 - mx0, my1 - my0


def lockup(texto_blocos, alt_marca, folga):
    """Marca à esquerda com altura alt_marca; texto à direita, centrado na vertical."""
    bx0, by0, bx1, by1 = caixa(texto_blocos)
    th = by1 - by0
    s = alt_marca / MH
    mw = MW * s
    H = max(alt_marca, th)
    xt = mw + folga
    yt = (H - th) / 2
    ym = (H - alt_marca) / 2
    usos = [f'<use href="#lg-marca" transform="translate(0 {num(ym)}) scale({num(s)})"/>']
    for b in texto_blocos:
        cx0, cy0, _, _ = caixa([b])
        usos.append(f'<use href="#lg-{b}" transform="translate({num(xt + cx0 - bx0)} {num(yt + cy0 - by0)})"/>')
    return num(xt + (bx1 - bx0)), num(H), "".join(usos)


TH = ty1 - ty0          # altura do texto com lema
PH = py1 - py0          # altura da palavra GARC
largo_w, largo_h, largo_usos = lockup(["palavra", "lema"], TH * 1.12, TH * 0.17)
curto_w, curto_h, curto_usos = lockup(["palavra"], PH * 1.55, PH * 0.26)

defs = ("".join(f'<g id="lg-{b}">{caminhos(b, var, caixa([b])[:2])}</g>' for b in ("marca", "palavra", "lema")))
cabecalho = (
    '<svg class="brand-defs" width="0" height="0" aria-hidden="true" focusable="false"><defs>' + defs + "</defs></svg>"
    f'<svg class="brand-logo brand-logo-largo" viewBox="0 0 {largo_w} {largo_h}" aria-hidden="true" focusable="false">{largo_usos}</svg>'
    f'<svg class="brand-logo brand-logo-curto" viewBox="0 0 {curto_w} {curto_h}" aria-hidden="true" focusable="false">{curto_usos}</svg>'
)
(out / "logo-cabecalho.html").write_text(cabecalho + "\n")

# Versões com cores fixas, só para pré-visualizar
defs_hexa = "".join(f'<g id="lg-{b}">{caminhos(b, hexa, caixa([b])[:2])}</g>' for b in ("marca", "palavra", "lema"))
for nome, (w, h, usos) in {"largo": (largo_w, largo_h, largo_usos), "curto": (curto_w, curto_h, curto_usos)}.items():
    (out / "previsoes" / f"cabecalho-{nome}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}">'
        f'<defs>{defs_hexa}</defs>{usos.replace("href=", "xlink:href=")}</svg>\n')

# ---------------------------------------------------------------- ícones
lado = int(max(MW, MH) * 1.26)
s_ic = 1.0
ox = (lado - MW) / 2
oy = (lado - MH) / 2
favicon = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lado} {lado}">'
           f'<rect width="{lado}" height="{lado}" rx="{int(lado * 0.2)}" fill="#FFFFFF"/>'
           f'<g transform="translate({num(ox)} {num(oy)})">{caminhos("marca", hexa, (mx0, my0))}</g></svg>\n')
(out / "favicon.svg").write_text(favicon)


def png(svg_path, largura, destino):
    subprocess.run(["rsvg-convert", "-w", str(largura), "-o", str(destino), str(svg_path)], check=True)


png(out / "favicon.svg", 180, out / "apple-touch-icon.png")
imgs = []
for t in (16, 32, 48):
    png(out / "favicon.svg", t, out / f"favicon-{t}.png")
    imgs.append(Image.open(out / f"favicon-{t}.png").convert("RGBA"))
imgs[-1].save(out / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)], append_images=imgs[:-1])
for t in (16, 32, 48):
    (out / f"favicon-{t}.png").unlink()

png(out / "logo-garc.svg", 1200, out / "previsoes" / "logo-garc.png")
for nome in ("largo", "curto"):
    png(out / "previsoes" / f"cabecalho-{nome}.svg", 1200, out / "previsoes" / f"cabecalho-{nome}.png")

for f in sorted(out.glob("*")):
    if f.is_file():
        print(f"{f.name:24s} {f.stat().st_size:7d} bytes")
print("cabeçalho largo", largo_w, "x", largo_h, "| curto", curto_w, "x", curto_h)
