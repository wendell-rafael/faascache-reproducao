"""Figura e tabela da avaliação de GD_C (ver avaliacao_gd_c.md). Roda fora do contêiner:
lê apenas JSON e CSV gerados por nós, sem arquivos .pckl."""
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PILOT = {10000, 15000}
INK, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
rows = {(r["policy"], int(r["mem"])): r for r in csv.DictReader(open("analise/resultados.csv"))}
mems = sorted({m for _, m in rows})


def gdc(m):
    d = "resultados_piloto" if m in PILOT else "resultados_gd_c"
    return json.load(open(f"{d}/GD_C-{m}.json"))


table = []
for m in mems:
    x = gdc(m)
    t = dict(mem_mb=m, amostra="piloto" if m in PILOT else "avaliacao",
             gdc_cold=x["cold_pct"], gdc_inc=x["inc_pct"], gdc_drop=x["dropped"])
    for p in ("GD", "TTL", "LRU"):
        t[f"{p.lower()}_cold"] = float(rows[p, m]["run_cold_pct"])
        t[f"{p.lower()}_inc"] = float(rows[p, m]["run_inc_pct"])
        t[f"{p.lower()}_drop"] = int(rows[p, m]["run_dropped"])
    t["art_cold"] = float(rows["GD", m]["art_cold_pct"])
    t["art_inc"] = float(rows["GD", m]["art_inc_pct"])
    t["ttl_sobre_gdc_inc"] = t["ttl_inc"] / t["gdc_inc"]
    table.append(t)
with open("analise/gd_c_tabela.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(table[0]))
    w.writeheader()
    w.writerows(table)

series = [("GD publicado", "gd", "#2a78d6", "o", "-"), ("GD_C", "gdc", "#6250d6", "X", "-"),
          ("TTL", "ttl", "#eb6834", "^", "-"), ("LRU", "lru", "#1baf7a", "s", "-"),
          ("GD do artefato", "art", "#2a78d6", "o", "--")]
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), facecolor=SURFACE)
for ax, key, ylabel, log in zip(axes, ("cold", "inc"),
                                ("% de cold starts (escala log)", "% de aumento no tempo de execução"),
                                (True, False)):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=9)
    for label, p, c, mk, ls in series:
        xs = [t["mem_mb"] / 1024 for t in table]  # mesma conversão das figuras do artefato
        ax.plot(xs, [t[f"{p}_{key}"] for t in table], color=c, marker=mk, markersize=4,
                linestyle=ls, linewidth=2.2 if p == "gdc" else 1.4, label=label)
    for t in table:
        if t["amostra"] == "piloto":
            ax.plot(t["mem_mb"] / 1024, t[f"gdc_{key}"], marker="o", markersize=11, markerfacecolor="none",
                    markeredgecolor=MUTED, linestyle="none")
    if log:
        ax.set_yscale("log")
    else:
        ax.set_ylim(0, None)
    ax.set_xlabel("Memória (GB)", color=MUTED, fontsize=9)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=9)
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=5, frameon=False, fontsize=9)
fig.suptitle("GD_C contra referências, trace de 392 funções (círculos: tamanhos do piloto, fora da avaliação)",
             fontsize=10.5, color=INK, x=0.01, ha="left")
fig.tight_layout(rect=(0, 0.07, 1, 0.96))
fig.savefig("analise/fig_gd_c.png", dpi=200)

ev = [t for t in table if t["amostra"] == "avaliacao"]
print("ttl/gdc inc min-max (15-80 avaliacao):", [(t["mem_mb"], round(t["ttl_sobre_gdc_inc"], 2)) for t in ev])
print("ttl/gd publicado e artefato 15GB:", rows["TTL", 15000]["run_inc_pct"], rows["GD", 15000]["run_inc_pct"], rows["GD", 15000]["art_inc_pct"])
print("drop% 1,5,7,10 GB TTL:", [round(float(rows["TTL", m]["run_drop_pct"]), 1) for m in (1000, 5000, 7000, 10000, 12000)])
