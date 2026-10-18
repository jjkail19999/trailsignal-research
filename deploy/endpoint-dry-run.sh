#!/bin/sh
set -eu

NEBIUS_BIN="${NEBIUS_BIN:-$HOME/.nebius/bin/nebius}"
PROFILE="${NEBIUS_PROFILE:-hackathon-gtc}"
PROJECT="${NEBIUS_PROJECT_ID:?Set NEBIUS_PROJECT_ID before deploying}"
NEBIUS_SECRET_ID="${NEBIUS_SECRET_ID:?Set NEBIUS_SECRET_ID before deploying}"
TAVILY_SECRET_ID="${TAVILY_SECRET_ID:?Set TAVILY_SECRET_ID before deploying}"
APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

export AI_AGENT="${AI_AGENT:-codex}"

"$NEBIUS_BIN" ai endpoint create \
  -p "$PROFILE" \
  --parent-id "$PROJECT" \
  --name trialsignal-research \
  --image python:3.11-slim \
  --platform cpu-d3 \
  --preset 2vcpu-8gb \
  --disk-size 20Gi \
  --container-port 8080/http \
  --auth token \
  --on-demand \
  --working-dir /app \
  --container-command sh \
  --args /app/start.sh \
  --inject-file "$APP_DIR/app.py:/app/app.py" \
  --inject-file "$APP_DIR/core.py:/app/core.py" \
  --inject-file "$APP_DIR/requirements.txt:/app/requirements.txt" \
  --inject-file "$APP_DIR/deploy/start.sh:/app/start.sh" \
  --env PORT=8080 \
  --env NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/ \
  --env NEBIUS_MODEL=nvidia/Nemotron-3_5-Lightning \
  --env-secret NEBIUS_API_KEY="$NEBIUS_SECRET_ID" \
  --env-secret TAVILY_API_KEY="$TAVILY_SECRET_ID" \
  --dry-run

