"""Análise da reprodução: gera CSV, resumo e figuras em /analise.

Métricas iguais às dos scripts do artefato (compute_policy_results.py e plot_*_across_mem.py):
- cold_pct = misses / (misses + hits), sem contar requisições descartadas;
- inc_pct = wted_increase, média por função do aumento de tempo, ponderada por acessos.
"""
import csv
import glob
import json
import pickle
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/artifact/split")

TOTAL = 1348162
# Rótulo na rodada -> nome no artigo.
POLICIES = [("GD", "GD"), ("TTL", "TTL"), ("LRU", "LRU"), ("HIST", "HIST"),
            ("SIZE", "SIZE"), ("LND_rw", "LND"), ("FREQ", "FREQ")]
COLORS = {"GD": "#2a78d6", "TTL": "#eb6834", "LRU": "#1baf7a", "HIST": "#eda100",
          "SIZE": "#e87ba4", "LND": "#008300", "FREQ": "#6250d6"}
MARKERS = {"GD": "o", "TTL": "^", "LRU": "s", "HIST": "D", "SIZE": "v", "LND": "P", "FREQ": "X"}
INK, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"


def metrics(stats, lambdas):
    acc = sum(v["misses"] + v["hits"] for v in stats.values())
    miss = sum(v["misses"] for v in stats.values())
    inc = 0.0
    for k, v in stats.items():
        n = v["misses"] + v["hits"]
        trun, twarm = lambdas[k][2], lambdas[k][3]
        if trun - twarm != 0 and n:
            inc += twarm * v["misses"] / (n * (trun - twarm)) * n / acc
    return dict(cold_pct=100 * miss / acc, inc_pct=100 * inc)


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=9)


def panels(rows, key, ylabel, path, title, log=False):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True, facecolor=SURFACE)
    for ax, source, sub in zip(axes, ("run", "art"), ("Esta execução", "Artefato pré-computado")):
        style(ax)
        for _, name in POLICIES:
            pts = sorted((r["mem"] / 1024, r[f"{source}_{key}"]) for r in rows
                         if r["policy"] == name and r["mem"] >= 10000)
            ax.plot(*zip(*pts), color=COLORS[name], marker=MARKERS[name], markersize=4,
                    linewidth=2 if name == "GD" else 1.4, label=name)
        ax.set_title(sub, fontsize=10, color=INK, loc="left")
        ax.set_xlabel("Memória (GB)", color=MUTED, fontsize=9)
    axes[0].set_ylabel(ylabel, color=MUTED, fontsize=9)
    if log:
        axes[0].set_yscale("log")
    else:
        axes[0].set_ylim(0, None)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=7, frameon=False, fontsize=9)
    fig.suptitle(title, fontsize=11, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.07, 1, 0.96))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main():
    with open("/artifact/392-b.pckl", "rb") as f:
        lambdas_trace, _ = pickle.load(f)
    if isinstance(lambdas_trace, dict):
        print("lambdas do trace: dict com", len(lambdas_trace), "funções")
    results = [json.load(open(p)) for p in glob.glob("/res/*.json")]
    by = {(r["label"], r["mem"]): r for r in results}
    mems = sorted({r["mem"] for r in results})
    rows, lambda_diff = [], 0
    for label, name in POLICIES + [("GD_wall_own_cost", "GD_wall_own_cost")]:
        ref_policy = "LND" if label == "LND_rw" else ("GD" if label.startswith("GD") else label)
        for mem in mems:
            r = by[label, mem]
            with open(f"/artifact/392-pckls/{ref_policy}-392-{mem}-b.pckl", "rb") as f:
                ref = pickle.load(f)
            lam = ref[3]
            lambda_diff += sum(tuple(lam[k][:4]) != tuple(lambdas_trace[k][:4])
                               for k in r["per_function"] if k in lam and k in lambdas_trace)
            run, art = metrics(r["per_function"], lambdas_trace), metrics(ref[2], lam)
            rows.append(dict(policy=name, mem=mem, run_cold=r["result"]["misses"],
                             art_cold=r["artifact"]["misses"], run_dropped=r["result"]["dropped"],
                             art_dropped=r["artifact"]["dropped"],
                             identical=r.get("identical_per_function"),
                             run_cold_pct=run["cold_pct"], art_cold_pct=art["cold_pct"],
                             run_inc_pct=run["inc_pct"], art_inc_pct=art["inc_pct"],
                             run_drop_pct=100 * r["result"]["dropped"] / TOTAL,
                             art_drop_pct=100 * r["artifact"]["dropped"] / TOTAL,
                             elapsed_s=r["elapsed_s"]))
    print("diferenças de lambdas entre trace e artefato:", lambda_diff)
    with open("/analise/resultados.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    panels(rows, "cold_pct", "% de cold starts (escala log)", "/analise/fig_cold_starts.png",
           "Cold starts por memória, 10 a 80 GB, trace de 392 funções", log=True)
    panels(rows, "inc_pct", "% de aumento no tempo de execução", "/analise/fig_tempo_execucao.png",
           "Aumento no tempo de execução por memória, 10 a 80 GB, trace de 392 funções")

    g = {(r["policy"], r["mem"]): r for r in rows}
    fig, ax = plt.subplots(figsize=(8, 4.4), facecolor=SURFACE)
    style(ax)
    series = [("GD publicado", "GD", "run_cold", "#2a78d6", "o", "-"),
              ("GD no artefato", "GD", "art_cold", "#2a78d6", "o", "--"),
              ("TTL", "TTL", "run_cold", "#eb6834", "^", "-"),
              ("LRU", "LRU", "run_cold", "#1baf7a", "s", "-"),
              ("GD_wall_own_cost (exploratória)", "GD_wall_own_cost", "run_cold", "#6250d6", "X", ":")]
    xs = [m / 1024 for m in mems if m >= 10000]
    for label, pol, key, c, mk, ls in series:
        ax.plot(xs, [g[pol, m][key] for m in mems if m >= 10000], color=c, marker=mk, markersize=4,
                linestyle=ls, linewidth=2, label=label)
    ax.set_yscale("log")
    ax.set_xlabel("Memória (GB)", color=MUTED, fontsize=9)
    ax.set_ylabel("Cold starts (escala log)", color=MUTED, fontsize=9)
    ax.set_title("GD: código publicado, artefato e referências", fontsize=11, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig("/analise/fig_gd_divergencia.png", dpi=200)
    plt.close(fig)

    summary = dict(lambda_diff=lambda_diff, elapsed_h=sum(r["elapsed_s"] for r in rows) / 3600)
    summary["identical_sizes"] = {p: sum(bool(g[p, m]["identical"]) for m in mems)
                                  for p in [n for _, n in POLICIES] + ["GD_wall_own_cost"]}
    summary["gd_ratio"] = {m: round(g["GD", m]["run_cold"] / g["GD", m]["art_cold"], 2) for m in mems}
    summary["hist_diff_pct"] = {m: round(100 * (g["HIST", m]["run_cold"] / g["HIST", m]["art_cold"] - 1), 1)
                                for m in mems}
    for src in ("run", "art"):
        summary[f"{src}_inc_ttl_over_gd"] = {m: round(g["TTL", m][f"{src}_inc_pct"] / g["GD", m][f"{src}_inc_pct"], 2)
                                             for m in mems}
        summary[f"{src}_cold_ttl_over_gd"] = {m: round(g["TTL", m][f"{src}_cold_pct"] / g["GD", m][f"{src}_cold_pct"], 2)
                                              for m in mems}
    summary["run_gd"] = {m: dict(cold=round(g["GD", m]["run_cold_pct"], 3), inc=round(g["GD", m]["run_inc_pct"], 3)) for m in mems}
    summary["art_gd"] = {m: dict(cold=round(g["GD", m]["art_cold_pct"], 3), inc=round(g["GD", m]["art_inc_pct"], 3)) for m in mems}
    summary["ttl"] = {m: dict(cold=round(g["TTL", m]["run_cold_pct"], 3), inc=round(g["TTL", m]["run_inc_pct"], 3)) for m in mems}
    summary["wall"] = {m: dict(cold=round(g["GD_wall_own_cost", m]["run_cold_pct"], 3), inc=round(g["GD_wall_own_cost", m]["run_inc_pct"], 3)) for m in mems}
    summary["lru"] = {m: dict(cold=round(g["LRU", m]["run_cold_pct"], 3), inc=round(g["LRU", m]["run_inc_pct"], 3)) for m in mems}
    for src in ("run", "art"):
        best = {}
        for m in mems:
            for key in ("cold_pct", "inc_pct"):
                best.setdefault(key, {})[m] = min((g[n, m][f"{src}_{key}"], n) for _, n in POLICIES)[1]
        summary[f"{src}_best"] = best
    with open("/analise/resumo.json", "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
