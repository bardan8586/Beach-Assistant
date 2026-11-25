---
title: Beach Assistant API
emoji: 🏖️
colorFrom: blue
colorTo: cyan
sdk: docker
app_port: 7860
suggested_hardware: cpu-basic
pinned: false
---

# Beach Assistant API

FastAPI backend and YOLOv8 worker for the Beach Assistant dashboard. The React app stays on Vercel. This Space is only the API.

`GET /health` returns `{"status":"healthy",...}` once the container is up. Video analysis uses `yolov8n.pt` until `MODEL_URL` or `HF_MODEL_REPO` points at beach weights.

Set `ALLOWED_ORIGINS` to `https://beach-assistant-preview.vercel.app` (already the default if the variable is left unset). Leave `PORT` unset so the process listens on 7860.
