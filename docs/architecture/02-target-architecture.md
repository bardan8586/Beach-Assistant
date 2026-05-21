# Target Architecture (Production-Oriented)

This document describes a **credible target** for Beach Assistant as an aquatic-safety computer-vision product — not a rewrite spec. Migrate incrementally from the [current architecture](./01-current-architecture.md).

**Design principles**

- Human-in-the-loop always; system = **decision support**, not autonomous rescue.
- Fail-safe: degraded modes (AI down → last frame + explicit banner), never silent green status.
- Explainable alerts: reason codes, confidence, factors — not black-box scores only.
- Edge-first option for latency; cloud for multi-site ops and model management.

---

## Target system context

```mermaid
C4Context
  title Beach Assistant — Target System Context

  Person(lg, "Lifeguard", "Tower / patrol")
  Person(sup, "Supervisor", "Multi-beach oversight")
  Person(admin, "Admin", "Cameras, models, users")

  System(ba, "Beach Assistant Platform", "Ingest, infer, alert, record")
  System_Ext(cams, "IP Cameras / NVR", "RTSP / ONVIF")
  System_Ext(id, "Identity Provider", "SSO optional")

  Rel(lg, ba, "Live dashboard, ack alerts")
  Rel(sup, ba, "Incident review, reports")
  Rel(admin, ba, "Configure beaches, thresholds")
  Rel(cams, ba, "Video streams")
  Rel(ba, id, "AuthN/Z")
```

---

## Target containers (microservices-lite)

Start with **logical services**; can remain one repo, multiple processes, then split repos later.

```mermaid
flowchart TB
  subgraph edge["Edge / Site (optional)"]
    ING[Stream Ingest<br/>GStreamer / FFmpeg]
    INF[Inference Worker<br/>GPU]
    BUF[Frame buffer + health]
  end

  subgraph cloud["Cloud / Central"]
    API[API Gateway<br/>FastAPI or BFF]
    EVT[Event Bus<br/>Redis Streams / NATS]
    RISK[Risk + Alert Service]
    INC[Incident Service]
    MDM[Model Registry]
  end

  subgraph data["Data plane"]
    PG[(PostgreSQL<br/>ops + incidents)]
    OBJ[(S3 / MinIO<br/>clips + snapshots)]
    TS[(Timescale / JSONL archive<br/>frame samples)]
    CACHE[(Redis<br/>live state)]
  end

  subgraph clients["Clients"]
    DASH[Lifeguard Dashboard<br/>React]
    ADMIN[Admin Console<br/>React]
  end

  ING --> INF
  INF -->|FrameResult events| EVT
  EVT --> RISK
  RISK --> API
  RISK --> INC
  API --> PG
  API --> CACHE
  INC --> OBJ
  INF --> MDM
  DASH --> API
  DASH -->|WebSocket / SSE| API
  ADMIN --> API
```

---

## Camera ingestion layer

```mermaid
flowchart LR
  CAM1[RTSP cam 1] --> ING
  CAM2[RTSP cam 2] --> ING
  UP[Uploaded file] --> ING
  ING[Ingest service]
  ING -->|normalized frames| Q[Frame queue]
  Q --> INF[Inference workers]
```

**Requirements**

- Per-camera health: FPS, last frame age, decode errors.
- Automatic reconnect with backoff.
- Per-beach calibration profile (shore line, zone polygons) stored in DB, not hard-coded.
- Optional edge box: Jetson / NUC runs ingest + inference; cloud only for UI + incidents.

---

## Inference & tracking services

| Service | Responsibility | Tech direction |
|---------|----------------|----------------|
| **Detection** | Person / swimmer classes | YOLOv8/11 fine-tuned per domain; versioned weights |
| **Tracking** | Stable track IDs | ByteTrack / BoT-SORT; re-ID on occlusion |
| **Scene** | Shore, horizon, static zones | CV + optional homography from calibration UI |
| **Behavior** | Motion, velocity, stationarity | Kalman + optical flow supplement |
| **Pose** | Distress cues | Staged on high-risk only (keep current pattern) |
| **Risk** | Multi-factor score | Configurable weights per beach |
| **Alert** | Hysteresis, dedup, escalation | Single alert service owns state machine |

```mermaid
stateDiagram-v2
  [*] --> Monitoring
  Monitoring --> Watch: risk 50-70 sustained
  Watch --> Alert: risk 70-90 or zone breach
  Alert --> Emergency: drowning cue / critical score
  Emergency --> Acknowledged: operator ack
  Acknowledged --> Resolved: cleared / safe
  Acknowledged --> FalsePositive: operator marks FP
  Resolved --> [*]
  FalsePositive --> [*]
```

---

## Frontend target (two apps or two modes)

```mermaid
flowchart TB
  subgraph live["Live Patrol Mode"]
    V[Multi-cam grid or primary + thumbnails]
    Q[Alert queue sorted by severity + time]
    M[Minimap / zone overlay]
  end

  subgraph review["Incident Review Mode"]
    T[Timeline scrubber]
    C[Clip export + audit log]
    R[Replay with frozen overlays]
  end

  subgraph admin["Admin"]
    CAM[Camera registry]
    CAL[Zone calibration tool]
    MOD[Model version + metrics]
  end
```

**UX rules**

- Video + alert queue always above fold.
- One audio policy; per-severity mute.
- Every alert: reason, factors, recommended action, confidence band.
- Tablet landscape layout; control-room dual-monitor layout.

---

## Fail-safe design

```mermaid
flowchart TD
  A[Frame received] --> B{Inference healthy?}
  B -->|no| DEG[Degraded mode UI]
  DEG --> LAST[Show last good frame + timestamp]
  DEG --> BANNER[Banner: AI offline — manual patrol]
  B -->|yes| C{Latency OK?}
  C -->|no| WARN[Stale data warning]
  C -->|yes| NORM[Normal overlays + alerts]
```

- No “API Online” without health checks (already improved in current app).
- Alert pipeline idempotent: dedupe by `(camera_id, track_id, reason, window)`.
- Incident actions append-only audit log.

---

## GPU / CPU strategy

| Deployment | Inference | API / UI |
|------------|-----------|----------|
| Local demo | CPU `yolov8n` or Apple MPS | localhost |
| Cloud demo | 1× T4/L4 GPU worker | Render/Railway + Atlas |
| Pilot site | Edge GPU (Jetson Orin) or 1× cloud GPU per 2–4 cams | VPC + TLS |
| Multi-site | GPU pool + queue depth metrics | Regional API |

---

## Observability (target)

- **Metrics:** frames/sec, inference ms, ingest errors, WS clients, alert rate, FP rate (operator-marked).
- **Logs:** structured JSON; correlation id per `video_id` / `camera_id`.
- **Tracing:** optional OpenTelemetry from ingest → WS broadcast.
- **Dashboards:** Grafana — not required for student demo, required for pilot.

---

## Security (target minimum)

- JWT or session auth; roles: `lifeguard`, `supervisor`, `admin`.
- RTSP credentials in secrets manager, never in frontend.
- Rate limits on upload; virus scan optional for uploads.
- PII: face blur option for stored clips (jurisdiction-dependent).

---

## Gap: current → target (summary)

```mermaid
flowchart LR
  subgraph now["Current"]
    N1[Monolithic ai/main.py]
    N2[JSONL playback]
    N3[Single-page App]
    N4[Optional Mongo]
  end

  subgraph target["Target"]
    T1[Ingest + inference workers]
    T2[Incident store + S3 clips]
    T3[Live + Review + Admin]
    T4[Postgres + Redis live state]
  end

  N1 -.->|split process| T1
  N2 -.->|retain + archive| T2
  N3 -.->|router + modes| T3
  N4 -.->|harden schema| T4
```

See [04-roadmap.md](./04-roadmap.md) for staged delivery.
