"""Mede cópias por função em memória para GD e GD_C (mecanismo da Seção 4.4).

Amostra o pool a cada 50 invocações: contêineres, funções distintas e memória ocupada
por cópias além da primeira de cada função. Confere que os cold starts repetem os
resultados gravados (controle). Roda dentro do contêiner, via rodar_copias.sh.
"""
import json
import multiprocessing as mp
import os
import pickle
import sys
import time

import piloto_politicas as pp

MEMS = [int(m) for m in os.environ.get("MEMS", "20000,30000").split(",")]
EVERY = 50


def run(job):
    variant, mem = job
    with open("/artifact/392-b.pckl", "rb") as f:
        lambdas, trace = pickle.load(f)
    os.makedirs(f"/out/copias-{variant}-{mem}", exist_ok=True)
    L = pp.Sched("GD", mem, 392, "b", f"/out/copias-{variant}-{mem}")
    L.variant, L.decay = variant, {}
    n = cont = kinds = 0
    excess_mem = 0.0
    t0 = time.time()
    for i, (d, t) in enumerate(trace):
        L.runActivation(d, t)
        if i % EVERY == 0:
            pool = L.ContainerPool
            seen = set()
            ex = 0
            for c in pool:
                k = c.metadata.kind
                if k in seen:
                    ex += c.metadata.mem_size
                else:
                    seen.add(k)
            n += 1
            cont += len(pool)
            kinds += len(seen)
            excess_mem += ex
    stats = L.miss_stats()
    misses = sum(v["misses"] for v in stats.values())
    ref = (f"/ref/resultados/GD-{mem}.json" if variant == "GD"
           else f"/ref/resultados_gd_c/GD_C-{mem}.json")
    r = json.load(open(ref))
    ref_misses = r["result"]["misses"] if "result" in r else r["misses"]
    return dict(variant=variant, mem=mem, elapsed_s=round(time.time() - t0),
                samples=n, containers_mean=cont / n, functions_mean=kinds / n,
                copies_per_function=cont / kinds, excess_mem_mean_mb=excess_mem / n,
                excess_mem_pct=100 * excess_mem / n / mem,
                evictions=sum(L.evdict.values()), misses=misses,
                control_ok=misses == ref_misses)


if __name__ == "__main__":
    jobs = [(v, m) for m in MEMS for v in ("GD", "GD_C")]
    out = []
    with mp.Pool(len(jobs)) as pool:
        for row in pool.imap_unordered(run, jobs):
            print(json.dumps(row), flush=True)
            out.append(row)
    json.dump(sorted(out, key=lambda r: (r["mem"], r["variant"])),
              open("/res/copias.json", "w"), indent=1)
