#!/bin/bash
# Avaliação de GD_C em contêiner isolado, sem rede. Retomável: pula JSON já gravado.
P="$(cd "$(dirname "$0")" && pwd)"
docker run --rm --name faascache-gdc --network none --cap-drop ALL --security-opt no-new-privileges \
  --memory 16g --cpus 10 --pids-limit 128 --user "$(id -u):$(id -g)" -e PYTHONDONTWRITEBYTECODE=1 -e WORKERS=10 \
  -e AVAL_MEMS=80000,70000,60000,50000,46000,40000,34000,30000,26000,22000,20000,18000,16000,14000,12000,7000,5000,1000 \
  -v "$P/artefato/split:/artifact/split:ro" -v "$P/artefato/392-b.pckl:/artifact/392-b.pckl:ro" \
  -v "$P/piloto_politicas.py:/piloto.py:ro" -v "$P/out_gd_c:/out" -v "$P/resultados_gd_c:/res" \
  faascache-smoke python /piloto.py
