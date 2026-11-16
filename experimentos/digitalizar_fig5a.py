"""Extrai as curvas da figura 5a do artigo do FaasCache a partir do PDF vetorial.

Uso: python3 digitalizar_fig5a.py faascache-asplos21.pdf
Gera analise/fig5a_digitalizada.json (curvas) e analise/fig5a_comparacao.json
(artigo x esta execução x artefato nos tamanhos da grade). Requer pdftocairo (poppler).
A figura 5a está na página 9, no grupo source-45 do SVG gerado pelo pdftocairo.
Calibração pelas marcas dos eixos: x 20 GB = 45,49 e 80 GB = 144,91;
y 0,0% = 82,30 e 2,0% = 20,66 (coordenadas locais do grupo).
"""
import csv
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
COLORS = {"rgb(0%, 0%, 0%)": "GD", "rgb(17.259216%, 62.693787%, 17.259216%)": "TTL",
          "rgb(83.984375%, 15.281677%, 15.696716%)": "LRU", "rgb(100%, 49.804688%, 5.488586%)": "HIST",
          "rgb(58.006287%, 40.380859%, 74.021912%)": "SIZE",
          "rgb(54.881287%, 33.714294%, 29.417419%)": "LND", "rgb(0%, 75%, 75%)": "FREQ"}
X0, XS = 45.49 - 20 * 1.657, 1.657      # posição de 0 GB e pontos por GB
Y0, YS = 82.30, 30.82                   # posição de 0% e pontos por ponto percentual


def extract(pdf):
    with tempfile.TemporaryDirectory() as tmp:
        svg = os.path.join(tmp, "p9.svg")
        subprocess.run(["pdftocairo", "-svg", "-f", "9", "-l", "9", pdf, svg], check=True)
        s = open(svg).read()
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'id="(source-\d+)"', s)]
    k = [i for i, (_, sid) in enumerate(starts) if sid == "source-45"][0]
    blk = s[starts[k][0]:starts[k + 1][0]]
    curves = {}
    for m in re.finditer(r"<path ([^>]*)/>", blk):
        a = m.group(1)
        sw = re.search(r'stroke-width="([^"]+)"', a)
        if not sw or float(sw.group(1)) < 5:
            continue
        A, _, _, D, E, F = map(float, re.search(r'transform="matrix\(([^)]+)\)"', a).group(1).split(","))
        pts = re.findall(r"[ML] ([-\d.]+) ([-\d.]+)", re.search(r' d="([^"]+)"', a).group(1))
        if len(pts) < 3:
            continue
        name = COLORS.get(re.search(r'stroke="([^"]+)"', a).group(1))
        curves[name] = [((A * float(x) + E - X0) / XS, (Y0 - (D * float(y) + F)) / YS) for x, y in pts]
    return curves


def interp(curve, x):
    c = sorted(curve)
    x = min(max(x, c[0][0]), c[-1][0])
    for (x0, y0), (x1, y1) in zip(c, c[1:]):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)


if __name__ == "__main__":
    curves = extract(sys.argv[1])
    json.dump(curves, open(os.path.join(HERE, "analise/fig5a_digitalizada.json"), "w"))
    rows = {(r["policy"], int(r["mem"])): r for r in csv.DictReader(open(os.path.join(HERE, "analise/resultados.csv")))}
    out = []
    for m in sorted({m for (p, m) in rows if p == "GD" and m >= 10000}):
        td, gd = interp(curves["TTL"], m / 1024), interp(curves["GD"], m / 1024)
        tr, ta = float(rows["TTL", m]["run_inc_pct"]), float(rows["TTL", m]["art_inc_pct"])
        ga, gp = float(rows["GD", m]["art_inc_pct"]), float(rows["GD", m]["run_inc_pct"])
        out.append(dict(mem=m, ttl_artigo=td, ttl_nosso=tr, gd_artigo=gd, gd_artefato=ga, gd_publicado=gp,
                        razao_artigo=td / gd, razao_artefato=ta / ga, razao_publicado=tr / gp))
    json.dump(out, open(os.path.join(HERE, "analise/fig5a_comparacao.json"), "w"), indent=1)
    print("dif. máx. TTL artigo x esta execução:", max(abs(r["ttl_artigo"] - r["ttl_nosso"]) for r in out))
    print("dif. máx. GD artigo x artefato:", max(abs(r["gd_artigo"] - r["gd_artefato"]) for r in out))
