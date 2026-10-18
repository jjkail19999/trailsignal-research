#!/bin/sh
set -eu

python -m pip install --no-cache-dir -r /app/requirements.txt
exec streamlit run /app/app.py \
  --server.address=0.0.0.0 \
  --server.port="${PORT:-8080}" \
  --server.headless=true \
  --browser.gatherUsageStats=false

