"""Reprodução por simulação do FaasCache (ASPLOS '21), trace de 392 funções.

Roda cada par (política, memória) e grava um JSON por simulação em /res. Simulações
já gravadas são ignoradas, então a rodada pode ser retomada depois de uma interrupção.
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

# Tamanhos com resultado pré-computado no artefato, para permitir comparação direta.
MEMS = [1000, 5000, 7000, 10000, 12000, 14000, 15000, 16000, 18000, 20000,
        22000, 26000, 30000, 34000, 40000, 46000, 50000, 60000, 70000, 80000]
WORKERS = 10

# label: (política do simulador, fórmula de prioridade, política de referência no artefato)
JOBS = {
    "GD": ("GD", None, "GD"),  # código publicado (Equação 1 do artigo)
    "TTL": ("TTL", None, "TTL"),
    "LRU": ("LRU", None, "LRU"),
    "FREQ": ("FREQ", None, "FREQ"),
    "SIZE": ("SIZE", None, "SIZE"),
    "HIST": ("HIST", None, "HIST"),
    "LND_rw": ("LND", "lnd_rw", "LND"),  # reproduz o artefato com custo R-W
    "GD_wall_own_cost": ("GD", "wall_own_cost", "GD"),  # exploratória: não reproduz o artefato
}


class Sched(LambdaScheduler):
    """Desliga logs que não influenciam decisões e permite trocar a fórmula de prioridade."""
    formula = None

    def WriteMemLog(self, *a, **k):
        pass

    def WritePureCacheHist(self, *a, **k):
        pass

    def calc_priority(self, c, update=False):
        if self.formula == "lnd_rw":
            return c.metadata.run_time - c.metadata.warm_time
        if self.formula == "wall_own_cost":
            return c.last_access_t + c.frequency * (c.metadata.run_time - c.metadata.warm_time)
        return super().calc_priority(c, update)


def totals(stats, dropped, evictions):
    return dict(misses=sum(v["misses"] for v in stats.values()),
                hits=sum(v["hits"] for v in stats.values()),
                dropped=sum(dropped.values()),
                evictions=sum(evictions.values()))


def run(job):
    label, mem = job
    path = f"/res/{label}-{mem}.json"
    if os.path.exists(path):
        return f"ja existe: {label} {mem}"
    policy, formula, ref_policy = JOBS[label]
    logdir = f"/out/{label}-{mem}"
    os.makedirs(logdir, exist_ok=True)
    with open("/artifact/392-b.pckl", "rb") as f:
        _, trace = pickle.load(f)
    L = Sched(policy, mem, 392, "b", logdir)
    L.formula = formula
    t0 = time.time()
    for d, t in trace:
        L.runActivation(d, t)
    L.PerformanceLog.flush()
    stats = L.miss_stats()
    row = dict(label=label, policy=policy, mem=mem, elapsed_s=round(time.time() - t0),
               per_function=stats, dropped_per_function=dict(L.capacity_misses),
               result=totals(stats, L.capacity_misses, L.evdict))
    ref_path = f"/artifact/392-pckls/{ref_policy}-392-{mem}-b.pckl"
    if os.path.exists(ref_path):
        with open(ref_path, "rb") as f:
            ref = pickle.load(f)
        row["artifact"] = totals(ref[2], ref[4], ref[1])
        row["identical_per_function"] = stats == ref[2]
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(row, f)
    os.replace(tmp, path)
    shutil.rmtree(logdir, ignore_errors=True)
    return f"{label} {mem} {row['elapsed_s']}s {row['result']}"


def safe_run(job):
    try:
        return run(job)
    except Exception as e:
        return f"ERRO {job}: {e!r}"


if __name__ == "__main__":
    jobs = [(label, mem) for mem in MEMS for label in JOBS]
    with mp.Pool(WORKERS) as pool:
        for line in pool.imap_unordered(safe_run, jobs):
            print(line, flush=True)
