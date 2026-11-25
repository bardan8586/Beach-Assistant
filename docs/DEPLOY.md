# Deploy Beach Assistant

The dashboard stays on Vercel. The API is a Docker image that also runs the YOLO worker. Nothing in this repository creates a hosting account or uploads an image. The steps below are what to click after you have accounts.

Weights (`best.pt`) and the Roboflow images are not in git. A host will start, and `/health` will pass, but video analysis needs the weights on disk or `MODEL_NAME` pointing at a file you upload to the machine. Without them the worker falls back to `yolov8s.pt`, which Ultralytics downloads on first use and which only knows the COCO "person" class.

## What you set everywhere

| Variable | Where | Purpose |
|---|---|---|
| `VITE_API_URL` | Vercel | `https://` URL of the API, no trailing slash |
| `VITE_WS_URL` | Vercel | Same host with `wss://` |
| `ALLOWED_ORIGINS` | API host | Comma-separated. Include `https://beach-assistant-preview.vercel.app` and any other Vercel domain |
| `MONGODB_URL` | API host | Optional. Empty or unset still serves video, JSONL results, and WebSockets. Mongo is only for swimmer/alert/camera documents |
| `ENABLE_POSE` | API host | `false` on CPU. `true` loads YOLOv8-Pose as well |
| `INFERENCE_IMGSZ` | API host | `640` matches training. `416` is faster |
| `FRAME_SKIP` | API host | `2` processes every other frame |
| `SHOW_WINDOW` | API host | Keep `false` on a server |
| `MODEL_NAME` | API host | Path to `best.pt` inside the container, if you copied the weights in |
| `BEACH_DEFAULT_LAT` / `BEACH_DEFAULT_LON` / `BEACH_DEFAULT_LABEL` | API host | Coastal panel location. Defaults to Bondi Beach |

MongoDB Atlas free tier is enough if you want the database. The API already tolerates a refused Mongo connection.

YOLOv8n needs about 2 GB of RAM once torch is loaded. Render's free instance (512 MB) will be killed during inference. Use a 2 GB instance or larger.

## Vercel (frontend, already the preview host)

1. Open the Vercel project that serves `https://beach-assistant-preview.vercel.app`.
2. Settings → Environment Variables.
3. Set `VITE_API_URL` to the public API origin, for example `https://beach-assistant-api.onrender.com`.
4. Set `VITE_WS_URL` to the same origin with `wss://`.
5. Deployments → Redeploy the production deployment so Vite bakes the variables into the build. Changing them later does nothing until the next build.
6. `frontend/vercel.json` is already a Vite SPA rewrite. Do not change the framework preset away from Vite.

## Render

1. https://dashboard.render.com → New → Blueprint, or New → Web Service → Docker.
2. Connect this GitHub repository.
3. If you use the Blueprint, Render reads `render.yaml`. The plan there is `starter` (paid, enough RAM). Do not switch it to Free if you want video analysis.
4. Environment → set `MONGODB_URL` if you have Atlas, and set `ALLOWED_ORIGINS` to the Vercel origin. `render.yaml` already includes the preview origin; add a custom domain if you have one.
5. Create Web Service and wait for the Docker build. The first build downloads CPU torch and is slow.
6. Open `https://<service>.onrender.com/health`. You want `{"status":"healthy",...}`.
7. Put that origin into the Vercel variables above and redeploy the frontend.

Render free web services sleep. The first request after sleep can take half a minute, and the instance will not keep a model hot. That is a reason to use a plan that does not spin down if the camera feed is live.

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

## Hugging Face Spaces

1. New Space → Docker SDK → public or private.
2. The Space Dockerfile must be at the Space root. This repo's Dockerfile is already at the root, so you can push the same tree.
3. Space settings → hardware: CPU Basic (2 vCPU, 16 GB) is the smallest that can load torch and YOLO. The free CPU upgrade is often too small and will be OOM-killed. Do not pick a GPU unless you intend to pay for it.
4. Settings → Variables: `ENABLE_POSE=false`, `SHOW_WINDOW=false`, `ALLOWED_ORIGINS=https://beach-assistant-preview.vercel.app`.
5. The Space URL is `https://<user>-beach-assistant.hf.space`. WebSockets on Spaces work on the same host with `wss://`.
6. Put those two URLs into Vercel and redeploy.

## Local Docker check (optional, on your machine)

```bash
docker compose up --build
```

API on http://localhost:8000 , Mongo on localhost:27017. This build is large because of CPU torch. It was not built in the change that added the file.

## After it is up

1. `GET /health` returns healthy.
2. The Vercel dashboard banner says Clear or Standby, not Offline.
3. Upload a short MP4. The WebSocket chip should go Live, then Analyzing, then tracks should appear.
4. If processing exits immediately, the container log will say whether torch or ultralytics failed to import. The API runs a preflight before it marks a job as started.
