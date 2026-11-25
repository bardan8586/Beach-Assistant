# Beach Assistant

Computer-vision prototype that flags early beach-risk signals from surf life saving club camera footage. It detects people, keeps track IDs, scores risk, and shows the result on a React dashboard.

This is a decision-support tool. It does not replace a lifeguard.

## What is in the repo

| Piece | Path | Role |
|---|---|---|
| Detector | `ai/detector.py`, `ai/classes.py` | YOLOv8. Duplicate Roboflow labels collapse to drowning, out_of_water, swimming, person |
| Tracker | `ai/tracker.py` | Norfair, box IoU distance (ByteTrack-style IDs, no appearance embedding) |
| Pipeline | `ai/main.py` | Detect, track, risk, alerts, non-blocking ingest |
| API | `backend/` | FastAPI, WebSockets, optional MongoDB, JSONL playback |
| Dashboard | `frontend/` | React 19, Vite, TypeScript, Zustand, Tailwind |
| Train / eval | `ai/scripts/` | Remap labels, train, evaluate, benchmark latency |

The recorded training run is `ai/runs/detect/runs-mai600/roboflow_v2_yolov8n_e5/args.yaml`: YOLOv8n, 5 epochs, CPU, batch 8, the 7-name Roboflow set. The report lists validation precision 0.642, recall 0.572, mAP50 0.614, mAP50-95 0.321. Those weights (`best.pt`) and the images under `ai/datasets/` are gitignored, so this checkout cannot repeat that number. Do not treat the recorded table as a new measurement.

## Local run

```bash
# API
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Dashboard
cd frontend
npm install
npm run dev

# AI worker dependencies (the API spawns ai/main.py with this interpreter if ai/venv exists)
cd ai
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Open http://localhost:5173 . Upload an MP4. The API saves it, starts `ai/main.py`, and broadcasts `frame_result` messages on `/ws/feed`.

MongoDB is optional. If `MONGODB_URL` is down, the API logs a warning and keeps serving uploads, JSONL results, and WebSockets.

## Environment

Copy `.env.example`. The names that matter:

- Backend: `PORT`, `MONGODB_URL`, `ALLOWED_ORIGINS`, `MAX_UPLOAD_VIDEO_BYTES`, `BACKEND_URL`, `BEACH_DEFAULT_LAT`, `BEACH_DEFAULT_LON`, `BEACH_DEFAULT_LABEL`
- AI: `MODEL_NAME`, `FRAME_SKIP`, `INFERENCE_IMGSZ`, `HALF_PRECISION`, `ENABLE_POSE`, `CONF_THRESHOLD`, `TRACKER_IOU_THRESHOLD`, `SHOW_WINDOW`, `SEND_TO_BACKEND`
- Frontend (Vite, baked in at build time): `VITE_API_URL`, `VITE_WS_URL`

`ENABLE_POSE` defaults to false. The old default loaded a second pose model on CPU. Set it to `true` to turn that back on.

`TRACKER_IOU_THRESHOLD` is a Norfair distance (`1 - IoU`). The default is 0.70, so a match needs IoU of about 0.30. The previous 0.2 required IoU of 0.8, which dropped IDs between skipped frames.

## Train and evaluate

```bash
# Needs ROBOFLOW_API_KEY and a local dataset download
python ai/scripts/download_roboflow_dataset.py
python ai/scripts/prepare_dataset.py
python ai/scripts/train.py --device 0 --epochs 50 --batch 16   # GPU
python ai/scripts/evaluate.py --weights path/to/best.pt --data ai/datasets/roboflow-drowning-4cls/data.yaml
python ai/scripts/benchmark_inference.py
```

`prepare_dataset.py` rewrites the 7 duplicate names into 4 class ids. `train.py` uses a lower fine-tune learning rate and a cosine schedule. The recorded 5-epoch run spent 3 epochs in warmup at `lr0=0.01`, which is a poor fine-tune setup. A new mAP only exists after you run `evaluate.py` on real weights.

Latency measured on this workspace (Intel Xeon, CPU, public `yolov8n.pt`, 1280x720 random frames, 16 frames after warmup, not the fine-tuned beach weights): 18.2 ms/frame at imgsz 640 (54.9 FPS) and 10.0 ms/frame at imgsz 416. Adding the old headless `cv2.waitKey(100)` back onto the 640 timing drops that to 8.5 FPS. Batch 4 and ONNX were slower on this CPU (30.0 ms and 56.0 ms). The self-reported 2.2 FPS upload figure was not reproduced. Full table: `docs/evaluation/benchmark.md`.

## Tests

```bash
pip install pytest numpy requests pydantic pydantic-settings
python -m pytest tests -q

cd frontend && npm run lint && npx tsc -b --pretty false
```

## Deploy

The frontend stays on Vercel. The API image is `Dockerfile` (CPU torch, FastAPI, the AI worker). Host notes for Render, Railway, Fly.io, and Hugging Face Spaces, including the clicks and the variables, are in [docs/DEPLOY.md](docs/DEPLOY.md).

```bash
docker compose up --build   # API on :8000, Mongo on :27017. Large image. Not run in CI.
```

No hosting account is created from this repository.
