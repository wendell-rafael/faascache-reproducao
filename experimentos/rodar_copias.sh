#!/bin/bash
# Mede cópias por função (GD e GD_C) em contêiner isolado, sem rede.
set -euo pipefail
P="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$P/analise"
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
  --memory 12g --cpus 6 --pids-limit 64 --user "$(id -u):$(id -g)" -e PYTHONDONTWRITEBYTECODE=1 \
  -e MEMS="${MEMS:-20000,30000}" \
  -v "$P/artefato/split:/artifact/split:ro" -v "$P/artefato/392-b.pckl:/artifact/392-b.pckl:ro" \
  -v "$P/piloto_politicas.py:/app/piloto_politicas.py:ro" -v "$P/copias.py:/app/copias.py:ro" \
  -v "$P/resultados:/ref/resultados:ro" -v "$P/resultados_gd_c:/ref/resultados_gd_c:ro" \
  -v "$TMP:/out" -v "$P/analise:/res" \
  -w /app faascache-smoke python /app/copias.py
