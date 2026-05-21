# Data Flow, Schemas & APIs

## Canonical schema: `FrameResult`

Defined in:

- `backend/app/models/frame_result.py` (Pydantic, source of truth server-side)
- `frontend/src/types/frameResult.ts` (TypeScript mirror)

```mermaid
classDiagram
  class FrameResult {
    +string video_id
    +string camera_id
    +int frame_index
    +int timestamp_ms
    +int video_width
    +int video_height
    +SwimmerData[] swimmers
    +SceneData scene
    +ProcessingMetrics metrics
    +AlertData[] alerts
    +datetime processed_at
    +string system_mode
  }

  class SwimmerData {
    +int track_id
    +BoundingBox bbox
    +float confidence
    +int risk_score
    +string risk_level
    +string behavior
    +string zone
  }

  class AlertData {
    +string alert_id
    +int swimmer_id
    +string level
    +string reason
    +float risk_score
    +bool acknowledged
  }

  FrameResult --> SwimmerData
  FrameResult --> AlertData
```

**Ingest rule (current):** always serialize with `frame_result.to_websocket_message()` before JSONL write and WebSocket broadcast.

---

## WebSocket protocol (current)

**URL:** `ws://{host}/ws/feed?camera_id={id}`  
**Subscribe:** `all` or `upload_{uuid_prefix}` or `cam_001`

### Server → client messages

| type | payload | Notes |
|------|---------|-------|
| `connected` | `{ camera_id, message }` | On connect |
| `frame_result` | `{ camera_id, data: FrameResult }` | Primary live path |
| `swimmers` | legacy | Older format; App still handles |
| `alert` | legacy | Per-alert broadcast (unused from ingest today) |

```mermaid
sequenceDiagram
  participant FE as Frontend
  participant WS as /ws/feed

  FE->>WS: connect ?camera_id=upload_abc
  WS-->>FE: { type: connected }
  loop Live processing
    WS-->>FE: { type: frame_result, data: {...} }
    Note over FE: Merge alerts without un-acking
    Note over FE: Sync canvas to video.currentTime
  end
```

### Recommended WebSocket improvements (target)

| Change | Why |
|--------|-----|
| `seq` monotonic per camera | Detect gaps / replay |
| `heartbeat` + server `pong` | Detect half-open connections |
| `alert_delta` events | Smaller payloads than full frame |
| `snapshot` on connect | Hydrate state after refresh |
| Version field `protocol: 2` | Safe upgrades |

---

## REST API improvements (target)

### Standard envelope

```json
{
  "success": true,
  "data": { },
  "error": null,
  "request_id": "uuid"
}
```

### Suggested resource map

| Resource | Current | Target |
|----------|---------|--------|
| Cameras | `/api/cameras` | + `health`, `calibration` |
| Streams | — | `POST /api/streams/{id}/start` |
| Live state | `/api/swimmers` (thin) | `/api/cameras/{id}/tracks` with risk fields |
| Alerts | `/api/alerts` | Unified with `AlertData`; `POST .../ack`, `.../resolve`, `.../false_positive` |
| Incidents | — | `/api/incidents` CRUD + timeline |
| Frames | `/api/video/{id}/results` | Paginated `?cursor=` + range |
| Models | — | `/api/models` versions + metrics |
| Health | `/health` | + `components: { db, redis, inference }` |

---

## Database design (target)

### Problem today

- **Two alert models:** `AlertData` (frame) vs `AlertInDB` (Mongo enums differ).
- **Swimmer records** missing `risk_score`, `zone`, `behavior` at persistence layer.
- **Frame history** only in JSONL per video, not queryable at scale.

### Proposed collections / tables

```mermaid
erDiagram
  BEACH ||--o{ CAMERA : has
  CAMERA ||--o{ CALIBRATION : has
  CAMERA ||--o{ TRACK : has
  TRACK ||--o{ TRACK_SAMPLE : optional
  TRACK ||--o{ ALERT : triggers
  ALERT ||--o{ ALERT_EVENT : audit
  INCIDENT ||--o{ INCIDENT_ACTION : contains
  INCIDENT }o--|| ALERT : may_include
  MODEL_RUN ||--o{ EVAL_METRIC : produces

  BEACH {
    uuid id PK
    string name
    float lat
    float lon
  }

  CAMERA {
    string camera_id PK
    uuid beach_id FK
    string rtsp_url_enc
    enum status
    datetime last_frame_at
  }

  CALIBRATION {
    uuid id PK
    string camera_id FK
    int shore_line_y
    json zone_polygons
    datetime valid_from
  }

  TRACK {
    string camera_id
    int track_id
    int last_risk_score
    string last_zone
    datetime first_seen
    datetime last_seen
  }

  ALERT {
    string alert_id PK
    string camera_id
    int track_id
    enum level
    enum reason_code
    enum status
    float risk_score
    json factors
    datetime triggered_at
  }

  INCIDENT {
    uuid id PK
    string camera_id
    datetime started_at
    datetime ended_at
    string severity_max
  }

  MODEL_RUN {
    uuid id PK
    string weights_uri
    string dataset_version
    datetime trained_at
  }
```

### Redis (live layer, target)

| Key pattern | Value | TTL |
|-------------|-------|-----|
| `cam:{id}:tracks` | Hash track_id → JSON snapshot | 30s refresh |
| `cam:{id}:alerts:active` | Sorted set by severity | 1h |
| `cam:{id}:frame:latest` | Last FrameResult | 10s |

---

## AI pipeline metrics (evaluation target)

| Metric | Use |
|--------|-----|
| Detection mAP@0.5 | Model quality on beach dataset |
| MOTA / IDF1 | Tracking stability |
| Alert precision/recall | Per reason code, hold-out videos |
| Time-to-alert | Latency from distress onset (simulated) |
| FP rate per hour | Operator-marked false positives |
| Zone accuracy | % swimmers with correct SAFE/CAUTION/DANGER |

Store runs in `MODEL_RUN` + dashboard in admin app.
