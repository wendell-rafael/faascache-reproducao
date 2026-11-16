#!/bin/bash
# Teste rápido em contêiner isolado, sem rede. Não altera resultados/.
set -euo pipefail
P="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/res" "$TMP/out"
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
  --memory 4g --cpus 2 --pids-limit 64 --user "$(id -u):$(id -g)" -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$P/artefato/split:/artifact/split:ro" -v "$P/artefato/392-b.pckl:/artifact/392-b.pckl:ro" \
  -v "$P/artefato/392-pckls:/artifact/392-pckls:ro" \
  -v "$P/reproducao.py:/app/reproducao.py:ro" -v "$P/smoke_test.py:/app/smoke_test.py:ro" \
  -v "$P/resultados:/ref:ro" -v "$TMP/out:/out" -v "$TMP/res:/res" \
  -w /app faascache-smoke python /app/smoke_test.py
