"""Diagnóstico de HIST: testa hipóteses sobre o código que gerou o artefato.

Cada variante altera um ponto da política HIST. Teste que pode falhar: a variante só
explica a divergência se coincidir com o artefato por função. Grava um JSON em /res.
"""
import heapq
import json
import multiprocessing as mp
import os
import pickle
import shutil
import sys
import time
from math import floor, isnan, sqrt

import numpy as np

sys.path.insert(0, "/artifact/split")
from Container import Container
from LambdaScheduler import LambdaScheduler

MEM = int(os.environ.get("MEM", 1000))
DEFAULT = dict(cond="ge", order="prewarm_first", head="published", tail="published",
               margin=(1.1, 0.9), cv="var", remove=True, heapify=True)
VARIANTS = {
    "base": {},
    "cond_le": dict(cond="le"),
    "cond_le_once": dict(cond="le_once"),
    "sem_prewarm": dict(cond="none"),
    "track_first": dict(order="track_first"),
    "head_i": dict(head="i"),
    "tail_i": dict(tail="i"),
    "sem_margem": dict(margin=(1.0, 1.0)),
    "cv_std": dict(cv="std"),
    "sem_remocao": dict(remove=False),
    "sem_heapify": dict(heapify=False),
}
VARIANTS.update(json.loads(os.environ.get("EXTRA", "{}")))


class Sched(LambdaScheduler):
    opt = None

    def WriteMemLog(self, *a, **k):
        pass

    def WritePureCacheHist(self, *a, **k):
        pass

    def _find_precentile(self, cdf, percent, head=False):
        for i, value in enumerate(cdf):
            if percent < value:
                if head:
                    return i if self.opt["head"] == "i" else max(0, i - 1)
                return i if self.opt["tail"] == "i" else min(i + 1, len(cdf))
        return len(cdf)

    def track_activation(self, d):
        o = self.opt
        t = self.wall_time
        if d.kind in self.last_seen:
            IAT = t - self.last_seen[d.kind]
        self.last_seen[d.kind] = t
        self.warmed.discard(d.kind)
        if d.kind not in self.IT_histogram:
            self.rep[d.kind] = d
            self.IT_histogram[d.kind] = np.zeros(240)
            self.wellford[d.kind] = (0, 0, 0)
            self.histTTL[d.kind] = 2 * 60 * 60 * 1000
            self.histPrewarm[d.kind] = 0
            return
        minute = floor(IAT / (60 * 1000))
        if minute >= 240:
            return
        self.wellford[d.kind] = self.well_update(self.wellford[d.kind], minute)
        self.IT_histogram[d.kind][minute] += 1
        mean, variance, _ = self.well_finalize(self.wellford[d.kind])
        ttl, pre = 2 * 60 * 60 * 1000, 0
        if not isnan(mean):
            data = self.IT_histogram[d.kind]
            cdf = np.cumsum(data / data.sum())
            head = self._find_precentile(cdf, 0.05, head=True)
            tail = self._find_precentile(cdf, 0.99)
            disp = (sqrt(variance) / mean if o["cv"] == "std" else variance / mean) if mean else 0
            if mean == 0 or disp <= 2:
                ttl = tail * 60 * 1000 * o["margin"][0]
                pre = head * 60 * 1000 * o["margin"][1]
        self.histTTL[d.kind] = ttl
        self.histPrewarm[d.kind] = pre

    def PreWarmContainers(self):
        cond = self.opt["cond"]
        if cond == "none":
            return
        now = self.wall_time
        for kind, pre in list(self.histPrewarm.items()):
            if pre == 0:
                continue
            due = pre + self.last_seen[kind]
            if cond == "ge":
                go = due >= now
            elif cond == "le":
                go = due <= now
            else:
                go = due <= now and kind not in self.warmed
            if go:
                self.warmed.add(kind)
                self.AddToPool(c=Container(self.rep[kind]), prewarm=True, at_time=min(due, now))

    def cleanup_finished(self):
        t = self.wall_time
        finished = [c for c, (_, fin) in self.running_c.items() if t >= fin]
        for c in finished:
            del self.running_c[c]
            if self.opt["remove"] and self.histPrewarm.get(c.metadata.kind, 0) != 0:
                self.RemoveFromPool(c, "HIST-prewarm")
        if self.opt["heapify"]:
            heapq.heapify(self.ContainerPool)
        return len(finished)

    def runActivation(self, d, t=0):
        if self.opt["order"] == "prewarm_first":
            return super().runActivation(d, t)
        # Mesmo fluxo do publicado, com track_activation antes de PreWarmContainers.
        self.wall_time = t
        self.cleanup_finished()
        self.track_activation(d)
        self.PreWarmContainers()
        pre, trk, clean = self.PreWarmContainers, self.track_activation, self.cleanup_finished
        self.PreWarmContainers = lambda: None
        self.track_activation = lambda _d: None
        self.cleanup_finished = lambda: 0
        try:
            return super().runActivation(d, t)
        finally:
            self.PreWarmContainers, self.track_activation, self.cleanup_finished = pre, trk, clean


def run(name):
    path = f"/res/{name}-{MEM}.json"
    if os.path.exists(path):
        return f"ja existe {name}"
    logdir = f"/out/{name}-{MEM}"
    os.makedirs(logdir, exist_ok=True)
    with open("/artifact/392-b.pckl", "rb") as f:
        _, trace = pickle.load(f)
    L = Sched("HIST", MEM, 392, "b", logdir)
    L.opt = {**DEFAULT, **VARIANTS[name]}
    L.warmed = set()
    t0 = time.time()
    for d, t in trace:
        L.runActivation(d, t)
    L.PerformanceLog.flush()
    stats = L.miss_stats()
    with open(f"/artifact/392-pckls/HIST-392-{MEM}-b.pckl", "rb") as f:
        ref = pickle.load(f)
    keys = set(stats) | set(ref[2])
    zero = dict(misses=0, hits=0)
    diff = [k for k in keys if stats.get(k, zero) != ref[2].get(k, zero)]
    row = dict(name=name, mem=MEM, opt=L.opt, elapsed_s=round(time.time() - t0),
               misses=sum(v["misses"] for v in stats.values()),
               art_misses=sum(v["misses"] for v in ref[2].values()),
               dropped=sum(L.capacity_misses.values()), art_dropped=sum(ref[4].values()),
               evictions=sum(L.evdict.values()), art_evictions=sum(ref[1].values()),
               funcs_diff=len(diff), funcs=len(keys),
               l1_misses=sum(abs(stats.get(k, zero)["misses"] - ref[2].get(k, zero)["misses"]) for k in keys),
               identical=not diff, per_function=stats)
    with open(path + ".tmp", "w") as f:
        json.dump(row, f)
    os.replace(path + ".tmp", path)
    shutil.rmtree(logdir, ignore_errors=True)
    return f"{name} {row['elapsed_s']}s misses={row['misses']}/{row['art_misses']} dif={row['funcs_diff']}/{row['funcs']} l1={row['l1_misses']} evic={row['evictions']}/{row['art_evictions']}"


def safe(name):
    try:
        return run(name)
    except Exception as e:
        return f"ERRO {name}: {e!r}"


if __name__ == "__main__":
    names = os.environ.get("ONLY", ",".join(VARIANTS)).split(",")
    with mp.Pool(int(os.environ.get("WORKERS", 10))) as pool:
        for line in pool.imap_unordered(safe, names):
            print(line, flush=True)
