# Beach Safety AI Video Analysis System - MVP Architecture

## System Overview

A real-time AI-powered video analysis system that monitors beach cameras, detects swimmers, tracks their behavior, and triggers alerts for abnormal patterns that may indicate distress or danger.

**🎯 MVP CONSTRAINT: ZERO COST - 100% Free & Local**
- All services run locally via Docker (no cloud hosting costs)
- Local file storage (no AWS S3)
- Free open-source models (YOLOv8)
- Local database (PostgreSQL/SQLite)
- No paid APIs or services
- Goal: Proof-of-concept to demonstrate functionality

---

## 1. Folder Structure

```
beach-assistant/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                      # FastAPI application entry point
│   │   ├── config.py                    # Configuration management (env vars, settings)
│   │   ├── dependencies.py              # FastAPI dependency injection
│   │   │
│   │   ├── api/                         # REST API & WebSocket endpoints
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── cameras.py           # Camera CRUD endpoints
│   │   │   │   ├── alerts.py            # Alert management endpoints
│   │   │   │   ├── analytics.py         # Analytics & statistics endpoints
│   │   │   │   └── health.py            # Health check endpoints
│   │   │   └── websocket.py             # WebSocket handler for real-time updates
│   │   │
│   │   ├── core/                        # Core business logic
│   │   │   ├── __init__.py
│   │   │   ├── video_processor.py       # Video stream ingestion & frame management
│   │   │   ├── detector.py              # Object detection (swimmer detection)
│   │   │   ├── tracker.py               # Multi-object tracking (swimmer tracking)
│   │   │   ├── behavior_analyzer.py     # Behavior analysis & anomaly detection
│   │   │   ├── alert_manager.py         # Alert triggering & management logic
│   │   │   └── stream_manager.py        # Manages multiple camera streams
│   │   │
│   │   ├── models/                      # Data models & schemas
│   │   │   ├── __init__.py
│   │   │   ├── camera.py                # Camera configuration model
│   │   │   ├── detection.py             # Detection & bounding box models
│   │   │   ├── track.py                 # Track model (swimmer trajectory)
│   │   │   ├── alert.py                 # Alert model
│   │   │   └── analytics.py             # Analytics data models
│   │   │
│   │   ├── services/                    # External service integrations
│   │   │   ├── __init__.py
│   │   │   ├── notification_service.py  # Email/SMS/Push notifications
│   │   │   ├── storage_service.py       # Video/snapshot storage (S3, local)
│   │   │   └── websocket_service.py     # WebSocket broadcast service
│   │   │
│   │   ├── db/                          # Database layer
│   │   │   ├── __init__.py
│   │   │   ├── database.py              # Database connection & session
│   │   │   ├── repositories/            # Data access layer
│   │   │   │   ├── __init__.py
│   │   │   │   ├── camera_repository.py
│   │   │   │   ├── alert_repository.py
│   │   │   │   └── analytics_repository.py
│   │   │   └── migrations/              # Database migrations (Alembic)
│   │   │
│   │   └── utils/                       # Utility functions
│   │       ├── __init__.py
│   │       ├── logging.py               # Logging configuration
│   │       ├── rtsp_utils.py            # RTSP stream utilities
│   │       ├── image_utils.py           # Image processing utilities
│   │       └── metrics.py               # Performance metrics
│   │
│   ├── tests/                           # Backend tests
│   │   ├── __init__.py
│   │   ├── test_api/
│   │   ├── test_core/
│   │   └── test_services/
│   │
│   ├── requirements.txt                 # Python dependencies
│   ├── Dockerfile                       # Backend Docker image
│   └── .env.example                     # Environment variables template
│
├── ai-worker/                           # Separate AI processing service
│   ├── app/
│   │   ├── __init__.py
│   │   ├── worker.py                    # Main worker process
│   │   ├── config.py
│   │   │
│   │   ├── inference/                   # AI/ML inference engines
│   │   │   ├── __init__.py
│   │   │   ├── yolo_detector.py         # YOLO-based person detection
│   │   │   ├── pose_estimator.py        # Pose estimation (optional)
│   │   │   └── model_loader.py          # Model loading & caching
│   │   │
│   │   ├── tracking/                    # Tracking algorithms
│   │   │   ├── __init__.py
│   │   │   ├── byte_tracker.py          # ByteTrack or similar
│   │   │   └── kalman_filter.py         # Kalman filter for smoothing
│   │   │
│   │   └── analysis/                    # Behavior analysis
│   │       ├── __init__.py
│   │       ├── motion_analyzer.py       # Motion pattern analysis
│   │       ├── zone_analyzer.py         # Zone-based analysis
│   │       └── anomaly_detector.py      # Anomaly detection algorithms
│   │
│   ├── models/                          # Pre-trained model files
│   │   ├── yolov8n.pt
│   │   └── .gitkeep
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                            # React dashboard
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   │
│   ├── src/
│   │   ├── App.tsx                      # Main app component
│   │   ├── index.tsx                    # Entry point
│   │   │
│   │   ├── components/                  # Reusable UI components
│   │   │   ├── Layout/
│   │   │   │   ├── Navbar.tsx
│   │   │   │   └── Sidebar.tsx
│   │   │   ├── VideoFeed/
│   │   │   │   ├── VideoPlayer.tsx      # Live video display
│   │   │   │   ├── DetectionOverlay.tsx # Bounding box overlay
│   │   │   │   └── CameraGrid.tsx       # Multi-camera grid view
│   │   │   ├── Alerts/
│   │   │   │   ├── AlertList.tsx
│   │   │   │   ├── AlertCard.tsx
│   │   │   │   └── AlertNotification.tsx
│   │   │   └── Analytics/
│   │   │       ├── Dashboard.tsx
│   │   │       ├── StatsCard.tsx
│   │   │       └── Charts.tsx
│   │   │
│   │   ├── pages/                       # Page components
│   │   │   ├── HomePage.tsx
│   │   │   ├── LiveMonitorPage.tsx
│   │   │   ├── AlertsPage.tsx
│   │   │   ├── AnalyticsPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   │
│   │   ├── hooks/                       # Custom React hooks
│   │   │   ├── useWebSocket.ts          # WebSocket connection hook
│   │   │   ├── useCamera.ts             # Camera data hook
│   │   │   └── useAlerts.ts             # Alerts hook
│   │   │
│   │   ├── services/                    # API client services
│   │   │   ├── api.ts                   # Axios configuration
│   │   │   ├── cameraService.ts
│   │   │   ├── alertService.ts
│   │   │   └── analyticsService.ts
│   │   │
│   │   ├── store/                       # State management (Zustand/Redux)
│   │   │   ├── index.ts
│   │   │   ├── cameraStore.ts
│   │   │   ├── alertStore.ts
│   │   │   └── uiStore.ts
│   │   │
│   │   ├── types/                       # TypeScript types
│   │   │   ├── camera.ts
│   │   │   ├── alert.ts
│   │   │   ├── detection.ts
│   │   │   └── analytics.ts
│   │   │
│   │   └── utils/                       # Utility functions
│   │       ├── formatters.ts
│   │       └── constants.ts
│   │
│   ├── package.json
│   ├── tsconfig.json
│   ├── Dockerfile
│   └── .env.example
│
├── shared/                              # Shared configurations
│   ├── schemas/                         # Shared data schemas (JSON Schema)
│   └── proto/                           # Protocol buffers (if needed for performance)
│
├── docker-compose.yml                   # Multi-container orchestration
├── .env.example                         # Global environment variables
├── .gitignore
└── README.md
```

---

## 2. Module Responsibilities

### Backend Service (FastAPI)

#### **app/main.py**
- Initialize FastAPI application
- Configure CORS, middleware
- Mount API routers
- Set up WebSocket endpoints
- Handle application lifecycle (startup/shutdown)

#### **app/api/v1/**
- **cameras.py**: CRUD operations for camera management (add, remove, update camera streams)
- **alerts.py**: Query alerts, acknowledge alerts, update alert status
- **analytics.py**: Retrieve statistics, generate reports, historical data
- **health.py**: System health checks, service status

#### **app/api/websocket.py**
- Manage WebSocket connections
- Broadcast real-time detections, tracks, and alerts to connected clients
- Handle client subscriptions (per-camera or global)

#### **app/core/**
- **stream_manager.py**: 
  - Manages multiple RTSP stream connections
  - Handles stream lifecycle (connect, reconnect, disconnect)
  - Frame buffering and distribution to AI workers
  
- **video_processor.py**: 
  - RTSP stream ingestion using OpenCV/FFmpeg
  - Frame extraction and preprocessing
  - Frame rate management (skip frames if needed)
  
- **detector.py**: 
  - Interface to AI worker for detection
  - Batching frames for efficient inference
  
- **tracker.py**: 
  - Assigns unique IDs to detected swimmers
  - Maintains track history (trajectory)
  - Handle track association across frames
  
- **behavior_analyzer.py**: 
  - Analyze swimmer trajectories
  - Detect abnormal patterns (stationary, erratic movement, zone violations)
  - Calculate risk scores
  
- **alert_manager.py**: 
  - Evaluate conditions for triggering alerts
  - Manage alert lifecycle (create, escalate, resolve)
  - Prevent duplicate alerts
  - Cooldown periods

#### **app/services/**
- **notification_service.py**: Browser notifications via WebSocket (FREE - no email/SMS for MVP)
- **storage_service.py**: Store alert snapshots to local filesystem (FREE - no S3)
- **websocket_service.py**: Centralized WebSocket broadcast logic

#### **app/db/**
- **database.py**: SQLAlchemy or MongoDB connection setup
- **repositories/**: Data access patterns for cameras, alerts, analytics

---

### AI Worker Service (Separate Python Service)

#### **app/worker.py**
- Consumes frames from message queue (RabbitMQ/Redis) or directly from backend
- Runs inference pipeline
- Returns detection results to backend

#### **inference/**
- **yolo_detector.py**: 
  - Load YOLOv8/YOLOv5 model
  - Perform person detection on frames
  - Filter detections (confidence threshold)
  
- **pose_estimator.py** (optional): 
  - Estimate body pose for drowning detection
  - Detect unusual poses (horizontal orientation in water)

#### **tracking/**
- **byte_tracker.py**: 
  - Implement ByteTrack or DeepSORT
  - Associate detections across frames
  - Maintain track state
  
- **kalman_filter.py**: 
  - Smooth trajectories
  - Predict positions for occluded tracks

#### **analysis/**
- **motion_analyzer.py**: 
  - Calculate velocity, acceleration
  - Detect stationary swimmers
  - Detect rapid movements
  
- **zone_analyzer.py**: 
  - Define safe/danger zones
  - Detect zone violations (swimming too far out)
  
- **anomaly_detector.py**: 
  - ML-based anomaly detection (isolation forest, autoencoders)
  - Rule-based anomaly detection (time in water, erratic patterns)

---

### Frontend Service (React)

#### **components/VideoFeed/**
- **VideoPlayer.tsx**: Display live video stream (WebRTC, HLS, or WebSocket-based MJPEG)
- **DetectionOverlay.tsx**: Render bounding boxes and track IDs on video
- **CameraGrid.tsx**: Multi-camera dashboard layout

#### **components/Alerts/**
- **AlertList.tsx**: Display active and historical alerts
- **AlertCard.tsx**: Individual alert with details, location, timestamp
- **AlertNotification.tsx**: Toast notifications for new alerts

#### **components/Analytics/**
- **Dashboard.tsx**: Overview statistics (active swimmers, alerts today, cameras online)
- **StatsCard.tsx**: Individual metric cards
- **Charts.tsx**: Time-series charts (swimmer count over time, alert trends)

#### **hooks/**
- **useWebSocket.ts**: 
  - Establish WebSocket connection
  - Handle reconnection logic
  - Subscribe to camera feeds
  - Parse incoming detection/alert messages
  
- **useCamera.ts**: Fetch camera list, camera status
- **useAlerts.ts**: Fetch alerts, acknowledge alerts

#### **services/**
- API client wrappers for backend REST endpoints
- Handle authentication tokens
- Error handling and retry logic

#### **store/**
- Global state management for cameras, alerts, detections, UI state
- Real-time state updates from WebSocket

---

## 3. High-Level Data Flow

### Stream Ingestion Flow

```
RTSP Camera → Backend (stream_manager) → video_processor 
    ↓
Extract frames @ 5-10 FPS
    ↓
Frame Queue (Redis/RabbitMQ or in-memory)
    ↓
AI Worker consumes frames
```

### Inference & Detection Flow

```
AI Worker receives frame
    ↓
YOLO Detector → Person detections (bounding boxes, confidence)
    ↓
ByteTracker → Assign/update track IDs
    ↓
Return {frame_id, detections[], tracks[]} to Backend
```

### Behavior Analysis & Alert Flow

```
Backend receives detections + tracks
    ↓
behavior_analyzer.py
    ↓
- Update track history (trajectory, time in frame)
- Calculate velocity, position changes
- Check anomaly conditions:
    * Stationary for > 30 seconds
    * Erratic movement pattern
    * Entered danger zone
    * Low pose confidence (potential drowning)
    ↓
alert_manager.py evaluates risk score
    ↓
If threshold exceeded → Create Alert
    ↓
- Save alert to database
- Capture snapshot (save to local disk)
- Broadcast alert via WebSocket (browser notification)
- Play audio alert in dashboard (optional)
```

### Real-Time Dashboard Flow

```
Frontend establishes WebSocket connection
    ↓
Subscribe to camera feeds
    ↓
Backend sends messages:
    - detections: {camera_id, frame_id, detections[], tracks[]}
    - alerts: {alert_id, camera_id, type, severity, ...}
    - analytics: {swimmer_count, camera_status, ...}
    ↓
Frontend updates UI in real-time:
    - Render bounding boxes on video
    - Update alert list
    - Update statistics
    - Show notifications
```

### API Request Flow (Non-real-time)

```
Frontend → REST API (GET /api/v1/cameras)
    ↓
Backend → camera_repository.get_all()
    ↓
Database query
    ↓
Return JSON response
    ↓
Frontend updates state
```

---

## 4. Key Architectural Decisions

### Separation of Concerns
- **Backend Service**: Orchestration, API, WebSocket, business logic
- **AI Worker Service**: CPU/GPU-intensive inference (can scale independently)
- **Frontend**: User interface only, no business logic

### Communication Patterns
- **Backend ↔ Frontend**: REST API (CRUD) + WebSocket (real-time updates)
- **Backend ↔ AI Worker**: Message queue (Redis/RabbitMQ) or gRPC for low latency
- **Backend ↔ Database**: SQLAlchemy ORM (PostgreSQL) or Motor (MongoDB)

### Scalability Strategy
- **Horizontal scaling**: Multiple AI worker instances for different cameras
- **Load balancing**: Distribute camera streams across workers
- **Caching**: Redis for track history, frame buffers
- **Database**: Partition by camera_id or time ranges

### Real-Time Performance
- **Frame rate throttling**: Process 5-10 FPS instead of full 30 FPS
- **Frame skipping**: Skip frames if processing queue backs up
- **Batch inference**: Process multiple frames in single GPU batch
- **Async processing**: Non-blocking I/O throughout backend

### Alert Logic
- **Risk scoring**: 0-100 score based on multiple factors
- **Thresholds**: Alert if score > 70 (critical), > 50 (warning)
- **Cooldown**: Prevent alert spam (e.g., 1 alert per track per 30 seconds)
- **Auto-resolution**: Alert resolves if swimmer exits frame or normal behavior resumes

---

## 5. Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Video Ingestion** | OpenCV (FREE) | RTSP stream processing |
| **AI Detection** | YOLOv8 (FREE) | Person detection |
| **Tracking** | ByteTrack (FREE) | Multi-object tracking |
| **Backend API** | FastAPI (FREE) | REST API & WebSocket server |
| **Real-time Comm** | WebSocket (FREE) | Push updates to frontend |
| **Message Queue** | Redis (FREE, local) | Backend ↔ AI Worker communication |
| **Database** | SQLite (FREE, zero-config) | Persistent storage |
| **Caching** | Redis (FREE, local) | Track history, session data |
| **Frontend** | React 18 (FREE) | Dashboard UI |
| **State Management** | Zustand (FREE) | Frontend state |
| **Charts** | Recharts (FREE) | Analytics visualization |
| **Video Display** | WebSocket MJPEG (FREE) | Live video streaming |
| **Containerization** | Docker Compose (FREE) | Local deployment |
| **Reverse Proxy** | Nginx (FREE, optional) | Load balancing |

---

## 6. MVP Phased Development

### Phase 1: Core Infrastructure (Week 1-2)
- Backend FastAPI setup with camera CRUD endpoints
- RTSP stream ingestion (single camera)
- AI worker with YOLO detection
- Basic WebSocket connection
- Simple React frontend with single video feed

### Phase 2: Tracking & Analysis (Week 3)
- Implement ByteTrack multi-object tracking
- Track history and trajectory storage
- Basic behavior analysis (stationary detection)
- Alert creation logic
- Alert display on frontend

### Phase 3: Real-Time Dashboard (Week 4)
- Multi-camera support
- Real-time detection overlay on video
- Alert notifications and list
- Analytics dashboard (swimmer count, alert trends)

### Phase 4: Polish & Optimization (Week 5)
- Performance optimization (batch inference, caching)
- Docker Compose setup
- Zone configuration UI
- Alert acknowledgment workflow
- Documentation

---

## 7. Data Models (Conceptual)

### Camera
```
{
  "id": "cam_001",
  "name": "North Beach Camera",
  "rtsp_url": "rtsp://...",
  "location": {"lat": 34.02, "lng": -118.48},
  "status": "active",
  "zones": [...],
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Detection
```
{
  "frame_id": 12345,
  "camera_id": "cam_001",
  "timestamp": "2025-01-01T12:00:00Z",
  "detections": [
    {
      "bbox": [x, y, w, h],
      "confidence": 0.95,
      "class": "person"
    }
  ]
}
```

### Track
```
{
  "track_id": "track_001",
  "camera_id": "cam_001",
  "first_seen": "2025-01-01T12:00:00Z",
  "last_seen": "2025-01-01T12:05:00Z",
  "trajectory": [[x1, y1, t1], [x2, y2, t2], ...],
  "status": "active",
  "risk_score": 35
}
```

### Alert
```
{
  "alert_id": "alert_001",
  "camera_id": "cam_001",
  "track_id": "track_001",
  "type": "stationary_swimmer",
  "severity": "critical",
  "timestamp": "2025-01-01T12:05:00Z",
  "location": {"x": 500, "y": 300},
  "snapshot_url": "/data/alerts/alert_001.jpg",  // LOCAL FILE PATH (FREE)
  "status": "active",
  "acknowledged_by": null,
  "resolved_at": null
}
```

---

## 8. Non-Functional Requirements

### Performance
- **Latency**: < 500ms from detection to dashboard update
- **Throughput**: Support 10+ camera streams simultaneously (MVP)
- **Frame processing**: 5-10 FPS per camera

### Reliability
- **Auto-reconnect**: RTSP streams reconnect on failure
- **Graceful degradation**: System continues if one camera fails
- **Alert persistence**: Alerts saved to database (not lost on restart)

### Security
- **Authentication**: JWT tokens for API access
- **HTTPS/WSS**: Encrypted communication
- **Camera credentials**: Stored encrypted in database
- **RBAC**: Role-based access control (admin, operator, viewer)

### Observability
- **Logging**: Structured logging (JSON) for all services
- **Metrics**: Prometheus metrics (frame rate, inference time, alert count)
- **Health checks**: All services expose /health endpoint
- **Monitoring**: Grafana dashboards for system metrics

---

## Next Steps

Once this architecture is approved, we can proceed with:

1. **Environment setup**: Initialize project structure, Docker Compose, dependencies
2. **Backend scaffolding**: FastAPI app, database models, repositories
3. **AI worker setup**: YOLO model loading, inference pipeline
4. **Frontend initialization**: React app, WebSocket integration
5. **Integration testing**: End-to-end flow with sample RTSP stream

This architecture is designed to be **modular**, **scalable**, and **maintainable** for an MVP while allowing for future enhancements such as:
- Advanced pose estimation for drowning detection
- Historical playback of incidents
- Mobile app for lifeguards
- Integration with emergency services
- AI model fine-tuning on beach-specific data

---

## 9. 💰 ZERO COST BREAKDOWN (MVP)

### What's FREE:
✅ **YOLOv8** - Free open-source model (no API costs)  
✅ **OpenCV** - Free video processing library  
✅ **FastAPI** - Free Python web framework  
✅ **React** - Free frontend framework  
✅ **SQLite** - Free embedded database (no hosting needed)  
✅ **Redis** - Free in-memory cache (Docker container)  
✅ **Docker** - Free containerization  
✅ **WebSockets** - Free real-time communication  
✅ **Local Storage** - Free disk space for snapshots  

### What We're NOT Using (to avoid costs):
❌ **Cloud hosting** (AWS, Azure, GCP) - Running locally  
❌ **S3** - Using local filesystem  
❌ **Cloud databases** - Using local SQLite  
❌ **Twilio/SendGrid** - Browser notifications only  
❌ **Paid AI APIs** - Using local YOLOv8  
❌ **Video CDN** - Direct WebSocket streaming  

### Hardware Requirements (Your Own):
- **Laptop/PC** with:
  - 8GB+ RAM (16GB recommended)
  - 4+ CPU cores
  - Optional: NVIDIA GPU (for faster inference, but CPU works)
  - 50GB+ disk space

### Demo Setup Cost: **$0.00** 🎉

