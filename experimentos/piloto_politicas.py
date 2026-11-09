"""Piloto de candidatas a nova política, sem ajuste de parâmetros.

Apenas para orientar a escolha. Os tamanhos usados aqui não podem servir de avaliação final.
- GD: controle, deve repetir resultados/GD-<mem>.json.
- GD_R: recência explícita, last_access_t + freq * custo * M / tamanho (M = memória média).
- GD_D: frequência com meia-vida de 1 h, mantida mesmo depois de o contêiner sair da memória.
- GD_C: frequência média entre clones, em vez da soma.
"""
import json
import multiprocessing as mp
import os
import pickle
import shutil
import sys
import time

sys.path.insert(0, "/artifact/split")
from LambdaScheduler import LambdaScheduler

MEMS = [10000, 15000]
HALF_LIFE_MS = 60 * 60 * 1000


class Sched(LambdaScheduler):
    variant = "GD"
    mean_mem = 1.0

    def WriteMemLog(self, *a, **k):
        pass

    def WritePureCacheHist(self, *a, **k):
        pass

    def runActivation(self, d, t=0):
        if self.variant == "GD_D":
            f, last = self.decay.get(d.kind, (0.0, t))
            self.decay[d.kind] = (f * 0.5 ** ((t - last) / HALF_LIFE_MS) + 1, t)
        return super().runActivation(d, t)

    def calc_priority(self, c, update=False):
        m = c.metadata
        cost = float(m.run_time - m.warm_time)
        clones = self.container_clones(c)
        freq = sum(x.frequency for x in clones)
        if self.variant == "GD_R":
            return c.last_access_t + freq * cost * self.mean_mem / m.mem_size
        if self.variant == "GD_D":
            return self.Clock + self.decay[m.kind][0] * cost / m.mem_size
        if self.variant == "GD_C":
            return self.Clock + freq / max(len(clones), 1) * cost / m.mem_size
        return super().calc_priority(c, update)


def metrics(stats, lambdas):
    acc = sum(v["misses"] + v["hits"] for v in stats.values())
    inc = 0.0
    for k, v in stats.items():
        n = v["misses"] + v["hits"]
        trun, twarm = lambdas[k][2], lambdas[k][3]
        if trun - twarm != 0 and n:
            inc += twarm * v["misses"] / ((trun - twarm) * acc)
    return 100 * sum(v["misses"] for v in stats.values()) / acc, 100 * inc


def run(job):
    variant, mem = job
    path = f"/res/{variant}-{mem}.json"
    if os.path.exists(path):
        return f"ja existe {variant} {mem}"
    logdir = f"/out/{variant}-{mem}"
    os.makedirs(logdir, exist_ok=True)
    with open("/artifact/392-b.pckl", "rb") as f:
        lambdas, trace = pickle.load(f)
    L = Sched("GD", mem, 392, "b", logdir)
    L.variant, L.decay = variant, {}
    L.mean_mem = sum(v[1] for v in lambdas.values()) / len(lambdas)
    t0 = time.time()
    for d, t in trace:
        L.runActivation(d, t)
    L.PerformanceLog.flush()
    stats = L.miss_stats()
    cold, inc = metrics(stats, lambdas)
    row = dict(variant=variant, mem=mem, elapsed_s=round(time.time() - t0),
               misses=sum(v["misses"] for v in stats.values()),
               dropped=sum(L.capacity_misses.values()), cold_pct=cold, inc_pct=inc,
               per_function=stats)
    with open(path + ".tmp", "w") as f:
        json.dump(row, f)
    os.replace(path + ".tmp", path)
    shutil.rmtree(logdir, ignore_errors=True)
    return f"{variant} {mem} {row['elapsed_s']}s misses={row['misses']} dropped={row['dropped']} cold={cold:.3f} inc={inc:.3f}"


def safe(job):
    try:
        return run(job)
    except Exception as e:
        return f"ERRO {job}: {e!r}"


if __name__ == "__main__":
    if os.environ.get("AVAL_MEMS"):  # avaliação final de GD_C, ver avaliacao_gd_c.md
        jobs = [("GD_C", int(m)) for m in os.environ["AVAL_MEMS"].split(",")]
    else:
        jobs = [("GD", 10000)] + [(v, m) for v in ("GD_R", "GD_D", "GD_C") for m in MEMS]
    with mp.Pool(int(os.environ.get("WORKERS", len(jobs)))) as pool:
        for line in pool.imap_unordered(safe, jobs):
            print(line, flush=True)
