#!/bin/bash
# Diagnóstico de HIST em contêiner isolado, sem rede. Variáveis: MEM, ONLY, WORKERS, EXTRA.
P="$(cd "$(dirname "$0")" && pwd)"
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
  --memory 16g --cpus 10 --pids-limit 256 --user "$(id -u):$(id -g)" -e PYTHONDONTWRITEBYTECODE=1 \
  -e MEM -e ONLY -e WORKERS -e EXTRA \
  -v "$P/artefato/split:/artifact/split:ro" -v "$P/artefato/392-b.pckl:/artifact/392-b.pckl:ro" \
  -v "$P/artefato/392-pckls:/artifact/392-pckls:ro" -v "$P/hist_variantes.py:/hist_variantes.py:ro" \
  -v "$P/out_hist:/out" -v "$P/resultados_hist:/res" faascache-smoke python /hist_variantes.py
