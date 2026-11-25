# Deploy Beach Assistant

The dashboard stays on Vercel. The API is a Docker image that also runs the YOLO worker. Nothing in this repository creates a hosting account or uploads an image. The steps below are what to click after you have accounts.

Weights (`best.pt`) and the Roboflow images are not in git. `ai/models/yolov8n.onnx` is. Render's free service runs that file with ONNX Runtime and does not install torch. A local or GPU run still uses `yolov8n.pt` when `best.pt` is missing. Set `MODEL_URL` to a `.pt` or `.onnx` file to override either path. `MODEL_NAME` pointing at a missing file does not crash startup.

## What you set everywhere

| Variable | Where | Purpose |
|---|---|---|
| `VITE_API_URL` | Vercel | `https://` URL of the API, no trailing slash |
| `VITE_WS_URL` | Vercel | Same host with `wss://` |
| `ALLOWED_ORIGINS` | API host | One URL, a comma-separated list, or a JSON list. Include `https://beach-assistant-preview.vercel.app` |
| `MONGODB_URL` | API host | Optional. Empty or unset still serves video, JSONL results, and WebSockets. Mongo is only for swimmer/alert/camera documents |
| `ENABLE_POSE` | API host | `false` on CPU. `true` loads YOLOv8-Pose as well |
| `INFERENCE_IMGSZ` | API host | `640` matches training. `416` is faster |
| `FRAME_SKIP` | API host | `2` processes every other frame |
| `SHOW_WINDOW` | API host | Keep `false` on a server |
| `MODEL_URL` | API host | Optional. Direct URL of a `.pt` or `.onnx` file. Wins over the other model settings |
| `INFERENCE_BACKEND` | API host | `onnx` on Render free. Unset or `pytorch` keeps torch |
| `HF_MODEL_REPO` | API host | Optional. Hugging Face model repo id, for example `your-user/beach-assistant-weights` |
| `HF_MODEL_FILENAME` | API host | Optional. File inside that repo. Default `best.pt` |
| `HF_TOKEN` | API host, secret | Only if `HF_MODEL_REPO` is private. This is not the token used by the GitHub Action |
| `MODEL_NAME` | API host | Optional. `yolov8n.pt` or a path that exists in the image |
| `PORT` | API host | Hugging Face listens on 7860. Leave it unset there. Other hosts inject it |
| `BEACH_DEFAULT_LAT` / `BEACH_DEFAULT_LON` / `BEACH_DEFAULT_LABEL` | API host | Coastal panel location. Defaults to Bondi Beach |

MongoDB Atlas free tier is enough if you want the database. The API already tolerates a refused Mongo connection.

The torch image needs about 2 GB of RAM. Do not point the free Render service at `Dockerfile`. `Dockerfile.render` is the 512 MB path, and the measured peak is in the Render section below.

## Vercel (frontend, already the preview host)

1. Open the Vercel project that serves `https://beach-assistant-preview.vercel.app`.
2. Settings → Environment Variables.
3. Set `VITE_API_URL` to the public API origin, for example `https://beach-assistant-api.onrender.com`.
4. Set `VITE_WS_URL` to the same origin with `wss://`.
5. Deployments → Redeploy the production deployment so Vite bakes the variables into the build. Changing them later does nothing until the next build.
6. `frontend/vercel.json` is already a Vite SPA rewrite. Do not change the framework preset away from Vite.

## Render free (chosen host)

`render.yaml` is a Blueprint for a **free** web service. It builds `Dockerfile.render`, which installs `requirements-render.txt` only: ONNX Runtime, NumPy, OpenCV headless, Norfair, and FastAPI. That image does not install torch or ultralytics. The full torch image is still `Dockerfile` for a local or GPU machine.

The shipped weights are `ai/models/yolov8n.onnx` (COCO nano, fixed 640 input). Set `MODEL_URL` to a different `.onnx` file to override it. `INFERENCE_BACKEND=onnx` selects this path. Leave it as `pytorch` (or unset) to keep the torch path.

Measured on this workspace (Intel Xeon, ONNX Runtime 1.32, 1 thread, imgsz 640), not on Render's 0.1 CPU:

| Moment | Resident memory |
|---|---:|
| `GET /health` with Mongo unset | 98 MB |
| ONNX session after one 1280×720 frame | 175 MB in that process |
| Peak while the API stayed up and a 12-frame 960×540 clip was processed | **365 MB** |

Latency on that same host was **56 ms per frame** (8 frames after one warmup, 1280×720). Render's 0.1 CPU will be slower. 365 MB of 512 MB leaves about 147 MB. The free service sets `MAX_FRAME_WIDTH=960`, `FRAME_SKIP=2`, and `ORT_THREADS=1` so a large upload is downscaled before the network. The ONNX file itself is fixed at 640, so `INFERENCE_IMGSZ` does not shrink it.

### Blueprint clicks

1. https://dashboard.render.com → New → Blueprint.
2. Connect GitHub and this repository. Render reads `render.yaml`.
3. Confirm the service `beach-assistant-api` is plan **Free**, Docker, health check path `/health`.
4. The Blueprint already sets:
   - `ALLOWED_ORIGINS=https://beach-assistant-preview.vercel.app`
   - `ENABLE_POSE=false`
   - `SHOW_WINDOW=false`
   - `INFERENCE_BACKEND=onnx`
   - `MONGODB_URL` empty (optional; paste an Atlas URL later if you want it)
5. Apply the Blueprint and wait for the Docker build. The first boot after idle takes a few seconds because free instances spin down.
6. Open `https://<service>.onrender.com/health`. You want `"status": "healthy"` and `"model": "yolov8n.onnx"`. `"database": "disconnected"` is expected until you set `MONGODB_URL`.

### Vercel, after the Render URL exists

1. Vercel → the beach-assistant-preview project → Settings → Environment Variables.
2. `VITE_API_URL` = `https://<service>.onrender.com` (no trailing slash).
3. `VITE_WS_URL` = `wss://<service>.onrender.com`.
4. Redeploy the frontend so Vite bakes those values in. The dashboard should leave Offline after that build.

Free instances sleep. The first request after sleep is slow, and a WebSocket drops while the process is down. That is the free tier, not a failed health check.

## Railway

1. https://railway.app → New Project → Deploy from GitHub repo.
2. Railway reads `railway.toml` and builds `Dockerfile`.
3. Variables: `ALLOWED_ORIGINS`, optional `MONGODB_URL`, `ENABLE_POSE=false`, `SHOW_WINDOW=false`. Railway sets `PORT` itself.
4. Settings → Networking → Generate Domain.
5. Check `https://<domain>/health`, then set the Vercel variables to that domain (`https` and `wss`).
6. Railway's trial credit is enough to boot the image. Confirm the service has at least 2 GB RAM in the service settings before processing video.

## Fly.io

1. Install `flyctl` and `fly auth login` on your machine.
2. From the repo root: `fly launch --no-deploy --copy-config --config deploy/fly.toml`
3. `fly secrets set ALLOWED_ORIGINS="https://beach-assistant-preview.vercel.app" MONGODB_URL="mongodb+srv://..."`
4. `fly deploy --config deploy/fly.toml`
5. `fly status` and open the hostname `/health`.
6. Point Vercel at `https://<app>.fly.dev` and `wss://<app>.fly.dev`.

`deploy/fly.toml` asks for 2 GB shared CPU. Fly will not launch until you confirm the app name and payment method in their UI.

## Hugging Face Spaces (chosen host)

The Space files live in `deploy/huggingface/`. The GitHub README stays a normal project README. `deploy/huggingface/README.md` is what becomes the Space README (`sdk: docker`, `app_port: 7860`, `suggested_hardware: cpu-basic`). The sync script copies it to the Space root together with the root `Dockerfile`, `backend/`, and `ai/`.

The image listens on `$PORT`, and the default is **7860**. Do not set `PORT=8000` on the Space.

### Settings to use

| Setting | Value |
|---|---|
| SDK | Docker |
| Hardware | CPU basic (`cpu-basic`: 2 vCPU, 16 GB RAM, no hourly charge) |
| Visibility | Public, unless you want the API private |
| `ALLOWED_ORIGINS` | `https://beach-assistant-preview.vercel.app` (variable; also the code default) |
| `ENABLE_POSE` | `false` |
| `SHOW_WINDOW` | `false` |
| `FRAME_SKIP` | `2` |
| `INFERENCE_IMGSZ` | `640` (set `416` if analysis is too slow) |
| `PORT` | leave unset |
| `MONGODB_URL` | leave unset unless you have Atlas. Unset still serves `/health`, uploads, and WebSockets |
| `MODEL_URL` or `HF_MODEL_REPO` | leave unset until you have beach weights. The worker uses `yolov8n.pt` |
| Secret `HF_TOKEN` on the Space | only for a private model repo |

Hugging Face currently requires a PRO plan (personal) or a Team/Enterprise org to **create** a Docker Space, even on CPU basic, which itself has no hourly price. A 402 from the Hub means that plan check, not a GPU charge. CPU basic still sleeps when idle.

### Create the Space and push this repo

1. https://huggingface.co/new-space → name `beach-assistant` → SDK **Docker** → hardware **CPU basic** → create.
2. Settings → Variables → add `ALLOWED_ORIGINS` = `https://beach-assistant-preview.vercel.app`. Add the other variables in the table if you want them explicit. Do not put the write token in a public variable.
3. Create a Hugging Face token with write access: https://huggingface.co/settings/tokens
4. From a checkout of this branch:

```bash
pip install "huggingface_hub>=0.23.0"
export HF_TOKEN=hf_your_write_token
python deploy/huggingface/sync_space.py YOUR_USER/beach-assistant
```

`YOUR_USER/beach-assistant` is the Space id. The script creates the Docker Space if it does not exist, then uploads the tree. The running app is `https://YOUR_USER-beach-assistant.hf.space`. Open `/health`.

### Same upload from GitHub Actions

1. GitHub repo → Settings → Secrets and variables → Actions → New repository secret.
2. Name: `HF_TOKEN`. Value: the same write token. This secret stays on GitHub. It is not uploaded into the Space.
3. Actions → **sync-huggingface-space** → Run workflow.
4. Input `space`: `YOUR_USER/beach-assistant`.
5. Wait until the Space status is Running, then open `https://YOUR_USER-beach-assistant.hf.space/health`.

### Point Vercel at the Space

1. Vercel → beach-assistant-preview → Settings → Environment Variables.
2. `VITE_API_URL` = `https://YOUR_USER-beach-assistant.hf.space`
3. `VITE_WS_URL` = `wss://YOUR_USER-beach-assistant.hf.space`
4. Redeploy the frontend. The dashboard banner should leave Offline after that build.

## Local Docker check (optional, on your machine)

```bash
docker compose up --build
```

`docker compose` publishes the API on http://localhost:8000 (`PORT=8000`). A plain `docker run -p 7860:7860` uses the image default, which is the Space port. The image was built locally. With no MongoDB running, `GET /health` returned `{"status":"healthy","database":"disconnected","model":"yolov8n.pt"}`. A request with `Origin: https://beach-assistant-preview.vercel.app` received that origin in `access-control-allow-origin`.

## After it is up

1. `GET /health` returns healthy.
2. The Vercel dashboard banner says Clear or Standby, not Offline.
3. Upload a short MP4. The WebSocket chip should go Live, then Analyzing, then tracks should appear.
4. If processing exits immediately, the container log will say whether torch or ultralytics failed to import. The API runs a preflight before it marks a job as started.
