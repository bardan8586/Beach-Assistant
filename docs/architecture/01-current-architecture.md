# Current Architecture (As-Built)

Beach Assistant is a **decision-support prototype**: computer vision on beach/pool video, risk heuristics, and a web dashboard for lifeguard-style operators. It does **not** replace human supervision.

---

## System context

```mermaid
C4Context
  title Beach Assistant — System Context (Current)

  Person(lifeguard, "Lifeguard / Operator", "Uploads video or watches live feed")
  System(ba, "Beach Assistant", "Detect, track, score risk, show alerts")
  System_Ext(mongo, "MongoDB Atlas", "Swimmers, alerts, cameras (optional)")
  System_Ext(meteo, "Open-Meteo", "Coastal weather proxy")

  Rel(lifeguard, ba, "Uses dashboard, acknowledges alerts")
  Rel(ba, mongo, "Persists swimmers/alerts when DB up")
  Rel(ba, meteo, "GET coastal conditions")
```

---

## Container view (what runs where)

```mermaid
flowchart TB
  subgraph client["Operator machine"]
    FE["React 19 + Vite + TS<br/>frontend/src/App.tsx"]
  end

  subgraph server["Application host (typically one machine)"]
    API["FastAPI<br/>backend/app/main.py"]
    WS["WebSocketService<br/>/ws/feed"]
    STORE["ResultsStorage JSONL<br/>backend/uploads/{video_id}/"]
    SUB["AI subprocess<br/>ai/main.py via video.py Popen"]
  end

  subgraph data["External / optional"]
    MONGO[(MongoDB Atlas)]
    FILES[(Local video files)]
  end

  FE -->|REST /api/*| API
  FE -->|WS frame_result| WS
  API --> STORE
  API --> MONGO
  SUB -->|POST /api/data/ingest| API
  SUB --> FILES
  API -->|spawn| SUB
  WS --> FE
```

---

## Repository layout (major modules)

| Area | Path | Role |
|------|------|------|
| **AI pipeline** | `ai/main.py` | Frame loop: detect → track → analyze → risk → alert → ingest |
| **Detection** | `ai/detector.py`, `ai/config.py` | YOLOv8 / Roboflow; fine-tuned `best.pt` default |
| **Tracking** | `ai/tracker.py`, `ai/advanced_tracker.py` | Norfair / ByteTrack-style IDs |
| **Scene & zones** | `ai/scene_analyzer.py`, `ai/water_analyzer.py` | Shore line, horizon, SAFE/CAUTION/DANGER |
| **Risk & alerts** | `ai/risk_engine.py`, `ai/alert_engine.py` | Score 0–100; WATCH/ALERT/EMERGENCY with hysteresis |
| **Pose (staged)** | `ai/pose_analyzer.py` | YOLOv8-Pose on high-risk tracks only |
| **Backend API** | `backend/app/routes/*.py` | REST + WS |
| **Ingest** | `backend/app/routes/ingest.py` | FrameResult → JSONL + WS + Mongo swimmers |
| **Video ops** | `backend/app/routes/video.py` | Upload, spawn AI, status, playback results |
| **Models** | `backend/app/models/frame_result.py` | Master schema AI ↔ backend ↔ frontend |
| **Frontend** | `frontend/src/App.tsx` | Single-page ops dashboard |
| **Video UI** | `frontend/src/components/VideoFeed/VideoPlayer.tsx` | Canvas overlays synced to `<video>` |
| **Alerts UI** | `frontend/src/components/Lifeguard/PriorityDashboard.tsx` | Top-3 queue |
| **Realtime** | `frontend/src/hooks/useWebSocket.ts` | `ws://host/ws/feed?camera_id=` |

---

## Current data flow (upload → dashboard)

Primary path today is **uploaded MP4/MOV**, not tower RTSP.

```mermaid
sequenceDiagram
  autonumber
  actor Op as Operator
  participant FE as React App
  participant API as FastAPI
  participant AI as ai/main.py
  participant WS as WebSocket
  participant Disk as uploads/ + results.jsonl

  Op->>FE: Select video file
  FE->>API: POST /api/video/upload
  API->>Disk: Save video + metadata.json
  API-->>FE: video_id, camera_id hint

  FE->>FE: setSelectedCamera(upload_{id})
  FE->>WS: Reconnect ?camera_id=upload_*

  FE->>API: POST /api/video/process/{video_id}
  API->>AI: Popen(main.py, env VIDEO_ID, CAMERA_ID, SEND_TO_BACKEND)
  Note over API,AI: stdout/stderr drained in thread (no pipe deadlock)

  loop Each processed frame
    AI->>AI: YOLO → track → risk → alert_engine
    AI->>API: POST /api/data/ingest (FrameResult JSON)
    API->>Disk: append results.jsonl
    API->>WS: broadcast type=frame_result
    WS->>FE: { type, camera_id, data: FrameResult }
    FE->>FE: Update swimmers, alerts, frameResults buffer
    FE->>FE: VideoPlayer canvas draw bboxes
  end

  AI-->>API: Process exit
  FE->>API: GET /api/video/status → completed
  FE->>API: GET /api/video/{id}/results (optional full replay load)
```

---

## AI pipeline (per frame)

```mermaid
flowchart LR
  IN[Frame source<br/>file or RTSP] --> DET[YOLO detect<br/>detector.py]
  DET --> FIL[filter.py]
  FIL --> TRK[PersonTracker<br/>tracker.py]
  TRK --> QUICK[Quick risk filter]
  QUICK --> POSE{High risk?}
  POSE -->|yes| POSE_A[pose_analyzer]
  POSE -->|no| BEH
  POSE_A --> BEH[behavior_analyzer]
  BEH --> RISK[risk_engine]
  RISK --> ALERT[alert_engine<br/>hysteresis + throttle]
  ALERT --> BUILD[Build FrameResult payload]
  BUILD --> INGEST[POST /api/data/ingest]
  TRK --> HEAT[heatmap.py<br/>not shown in web UI]
```

**Performance knobs:** `FRAME_SKIP` (default 2), optional `MULTI_SCALE_DETECTION`, pose only on high-risk subset.

---

## Frontend architecture (current)

```mermaid
flowchart TB
  subgraph state["State"]
    ZS[useAppStore<br/>swimmers, toggles, camera]
    LS[App.tsx local state<br/>alerts, frameResults, videoId]
  end

  subgraph io["I/O"]
    API_C[api.ts]
    VID[videoService.ts]
    PB[playbackService.ts]
    WS_H[useWebSocket.ts]
    AUD[audioAlertService.ts]
  end

  subgraph ui["UI priority order"]
    VID_P[VideoPlayer + canvas]
    ALERTS[PriorityDashboard]
    SWIM[SwimmerList sortable]
    COAST[CoastalConditionsPanel]
    STATS[DetailedStats]
  end

  WS_H --> LS
  API_C --> ZS
  LS --> VID_P
  LS --> ALERTS
  LS --> SWIM
  AUD --> ALERTS
```

**Not present:** React Router, auth, multi-camera grid, incident export, server-hosted video streaming (uses blob URL from upload).

---

## Backend API surface (current)

| Method | Path | Handler |
|--------|------|---------|
| GET | `/health` | `main.py` |
| GET | `/api/swimmers` | `routes/swimmers.py` |
| POST | `/api/data/ingest` | `routes/ingest.py` |
| GET/PATCH | `/api/alerts`, `/api/alerts/{id}` | `routes/alerts.py` |
| GET/POST/PATCH | `/api/cameras` | `routes/cameras.py` |
| POST | `/api/video/upload` | `routes/video.py` |
| POST | `/api/video/process/{id}` | `routes/video.py` |
| GET | `/api/video/status/{id}` | `routes/video.py` |
| GET | `/api/video/list` | `routes/video.py` |
| GET | `/api/video/{id}/results` | `routes/video.py` |
| GET | `/api/coastal/conditions` | `routes/coastal.py` |
| WS | `/ws/feed?camera_id=` | `routes/websocket.py` |

---

## Storage model (current)

```mermaid
erDiagram
  VIDEO_DIR ||--o{ FRAME_LINE : contains
  VIDEO_DIR {
    string video_id PK
    file video_mp4
    file metadata_json
    file results_jsonl
  }
  FRAME_LINE {
    int frame_index
    int timestamp_ms
    json swimmers
    json alerts
    json scene
  }

  MONGO_SWIMMER {
    string camera_id
    int track_id
    bbox x1y1x2y2
    datetime last_seen
  }

  MONGO_ALERT {
    string alert_id
    string camera_id
    int track_id
    enum severity
    enum status
  }
```

**Dual alert paths:** AI emits `AlertData` inside `FrameResult` (live UI). Mongo `Alert` model (`backend/app/models/alert.py`) uses different enums (`low/medium/high/critical`) — **not fully wired from ingest**.

---

## Deployment reality (current)

| Aspect | Current state |
|--------|-------------|
| Docker | Documented in `docs/ARCHITECTURE.md`; **no Dockerfile in repo** |
| CI/CD | None observed |
| Auth | None |
| TLS | Dev HTTP only |
| GPU | Optional local CUDA; subprocess uses `ai/venv` |
| Scaling | Single process; in-memory WS connection map |

---

## Known limitations (honest)

1. **Upload-first**, not production RTSP/WebRTC ingest.
2. **Monolithic AI** in one Python process spawned by API — not a separate inference service.
3. **Alerts** live primarily in WebSocket frames; Mongo alert persistence from ingest is incomplete.
4. **Swimmer DB records** lack risk/zone fields (ingest maps bbox only to `SwimmerCreate`).
5. **No automated tests** in CI; a few scripts under `tests/` and `test_playback_api.py`.
6. **Heatmap** computed in AI but not rendered in web UI.
7. **docs/ARCHITECTURE.md** at repo root describes aspirational PostgreSQL/Redis layout — **differs from as-built Mongo + JSONL**.

See [02-target-architecture.md](./02-target-architecture.md) for the intended evolution.
