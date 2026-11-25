# Beach Assistant API + AI worker.
# One process serves FastAPI and spawns ai/main.py for uploaded clips.
# CPU torch is installed on purpose. A CUDA image is larger than free-tier hosts allow.
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /tmp/backend-requirements.txt
COPY ai/requirements-server.txt /tmp/ai-requirements.txt

# Install the CPU wheel first so a later ultralytics install does not pull CUDA torch.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r /tmp/backend-requirements.txt \
    && pip install --no-cache-dir -r /tmp/ai-requirements.txt

COPY backend /app/backend
COPY ai /app/ai

ENV PYTHONUNBUFFERED=1 \
    ENABLE_POSE=false \
    SHOW_WINDOW=false \
    FRAME_SKIP=2 \
    INFERENCE_IMGSZ=640 \
    MONGODB_URL=mongodb://localhost:27017 \
    PORT=8000

WORKDIR /app/backend
EXPOSE 8000

# Hosts such as Render and Railway inject PORT.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
