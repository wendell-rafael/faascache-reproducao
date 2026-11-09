#!/bin/bash
# Roda (ou retoma) a reprodução em contêiner isolado, sem rede.
P="$(cd "$(dirname "$0")" && pwd)"
docker run --rm --name faascache-repro --network none --cap-drop ALL --security-opt no-new-privileges \
  --memory 16g --cpus 10 --pids-limit 256 --user "$(id -u):$(id -g)" -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$P/artefato/split:/artifact/split:ro" -v "$P/artefato/392-b.pckl:/artifact/392-b.pckl:ro" \
  -v "$P/artefato/392-pckls:/artifact/392-pckls:ro" -v "$P/reproducao.py:/reproducao.py:ro" \
  -v "$P/out:/out" -v "$P/resultados:/res" faascache-smoke python /reproducao.py
