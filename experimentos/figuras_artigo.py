"""Gera as figuras 1 a 3 do artigo a partir de analise/resultados.csv (sem carregar .pckl).

Cobre os 20 tamanhos, de 1 a 80 GB (MB/1024, como nos scripts do artefato),
com fontes legíveis em uma coluna do formato ACM.
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "analise")
POLICIES = ["GD", "TTL", "LRU", "HIST", "SIZE", "LND", "FREQ"]
COLORS = {"GD": "#2a78d6", "TTL": "#eb6834", "LRU": "#1baf7a", "HIST": "#eda100",
          "SIZE": "#e87ba4", "LND": "#008300", "FREQ": "#6250d6"}
MARKERS = {"GD": "o", "TTL": "^", "LRU": "s", "HIST": "D", "SIZE": "v", "LND": "P", "FREQ": "X"}
INK, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#ffffff"
plt.rcParams.update({"font.size": 11})

rows = list(csv.DictReader(open(os.path.join(OUT, "resultados.csv"))))
for r in rows:
    r["mem"] = int(r["mem"])
by = {(r["policy"], r["mem"]): r for r in rows}
mems = sorted({r["mem"] for r in rows})
xs = [m / 1024 for m in mems]


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=11)


def panels(key, ylabel, fname, log):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True, facecolor=SURFACE)
    for ax, src, sub in zip(axes, ("run", "art"), ("Esta execução", "Artefato pré-computado")):
        style(ax)
        for p in POLICIES:
            ax.plot(xs, [float(by[p, m][f"{src}_{key}"]) for m in mems], color=COLORS[p],
                    marker=MARKERS[p], markersize=4, linewidth=2.2 if p == "GD" else 1.4, label=p)
        ax.set_title(sub, fontsize=12, color=INK, loc="left")
        ax.set_xlabel("Memória (GB)", color=MUTED, fontsize=11)
    axes[0].set_ylabel(ylabel, color=MUTED, fontsize=11)
    if log:
        axes[0].set_yscale("log")
    else:
        axes[0].set_ylim(0, None)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=7, frameon=False, fontsize=11)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(os.path.join(OUT, fname), dpi=200)
    plt.close(fig)


panels("cold_pct", "Cold starts (%, escala log)", "fig_cold_starts.png", True)
panels("inc_pct", "Aumento no tempo de execução (%)", "fig_tempo_execucao.png", False)

fig, ax = plt.subplots(figsize=(6, 4.2), facecolor=SURFACE)
style(ax)
series = [("GD publicado", "GD", "run_cold", "#2a78d6", "o", "-"),
          ("GD do artefato", "GD", "art_cold", INK, "o", "--"),
          ("TTL", "TTL", "run_cold", "#eb6834", "^", "-"),
          ("LRU", "LRU", "run_cold", "#1baf7a", "s", "-"),
          ("Variante exploratória", "GD_wall_own_cost", "run_cold", "#6250d6", "X", ":")]
for label, pol, key, c, mk, ls in series:
    ax.plot(xs, [int(by[pol, m][key]) for m in mems], color=c, marker=mk, markersize=4,
            linestyle=ls, linewidth=2, label=label)
ax.set_yscale("log")
ax.set_xlabel("Memória (GB)", color=MUTED, fontsize=12)
ax.set_ylabel("Número de cold starts (escala log)", color=MUTED, fontsize=12)
ax.legend(frameon=False, fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_gd_divergencia.png"), dpi=200)
plt.close(fig)
print("figuras geradas em", OUT)
