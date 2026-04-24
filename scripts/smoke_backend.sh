#!/usr/bin/env bash
# Quick health checks for the Beach Assistant API (short curl timeouts).
# Usage:
#   ./scripts/smoke_backend.sh
#   BACKEND_URL=http://127.0.0.1:8008 ./scripts/smoke_backend.sh

set -euo pipefail

BASE="${BACKEND_URL:-http://127.0.0.1:8000}"
BASE="${BASE%/}"

echo "== Smoke: ${BASE} =="

body="$(curl -sS --max-time 5 "${BASE}/health" || true)"
if [[ "$body" == *"502 Bad Gateway"* ]] || [[ "$body" == *"<html"* ]]; then
  echo "FAIL: ${BASE}/health returned HTML (often nginx/docker on 8000, not FastAPI)."
  echo "      Start the API on a free port, e.g.: cd backend && PORT=8008 ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8008"
  echo "      Then: BACKEND_URL=http://127.0.0.1:8008 $0"
  exit 1
fi

echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('status')=='healthy', d" 2>/dev/null || {
  echo "FAIL: /health did not return JSON {status: healthy}. Body:"
  echo "$body"
  exit 1
}
echo "OK /health"

curl -sS --max-time 25 "${BASE}/api/video/preflight" | python3 -c "import json,sys; json.load(sys.stdin)" >/dev/null
echo "OK /api/video/preflight"

curl -sS --max-time 10 -X POST "${BASE}/api/data/ingest" \
  -H "Content-Type: application/json" \
  -d '{"video_id":"smoke","camera_id":"smoke_cam","frame_index":0,"timestamp_ms":0,"video_width":1280,"video_height":720,"swimmers":[]}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('success') is True, d"
echo "OK POST /api/data/ingest (minimal FrameResult)"

echo "== All smoke checks passed =="
