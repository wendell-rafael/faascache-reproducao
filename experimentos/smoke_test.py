"""Teste rápido (cerca de 1 a 2 minutos): roda TTL e LRU a 1 GB e confere o resultado.

Passa se, para as duas políticas, (1) os cold starts por função coincidem com os
resultados pré-computados do artefato e (2) os totais coincidem com os JSON
gravados em resultados/. Roda dentro do contêiner, via smoke_test.sh.
"""
import json
import multiprocessing as mp
import sys

import reproducao

JOBS = [("TTL", 1000), ("LRU", 1000)]

if __name__ == "__main__":
    with mp.Pool(len(JOBS)) as pool:
        for line in pool.imap_unordered(reproducao.run, JOBS):
            print(line, flush=True)
    ok = True
    for label, mem in JOBS:
        got = json.load(open(f"/res/{label}-{mem}.json"))
        ref = json.load(open(f"/ref/{label}-{mem}.json"))
        same_artifact = got["identical_per_function"]
        same_saved = got["result"] == ref["result"]
        print(f"{label} {mem} MB: igual ao artefato por função={same_artifact}, "
              f"igual ao resultado gravado={same_saved}")
        ok = ok and same_artifact and same_saved
    print("SMOKE TEST OK" if ok else "SMOKE TEST FALHOU")
    sys.exit(0 if ok else 1)
