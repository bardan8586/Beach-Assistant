# 🏗️ PHASE 1: BACKEND ARCHITECTURE PLAN

## 📋 Overview

Building a **FastAPI** backend (Python) to:
1. Receive real-time data from AI pipeline
2. Store swimmer tracking data in MongoDB
3. Expose REST APIs and WebSocket endpoints
4. Support multiple cameras/beaches (scalable)

**Tech Choice Rationale:**
- **FastAPI** → Same language as AI (Python), excellent WebSocket support, auto-docs
- **MongoDB** → Flexible schema for tracking data, good for time-series data
- **Motor** → Async MongoDB driver for FastAPI
- **WebSockets** → Built-in FastAPI support for real-time updates

---

## 📁 Backend Folder Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Configuration (MongoDB URI, env vars)
│   ├── database.py                # MongoDB connection setup
│   │
│   ├── models/                    # Pydantic models (request/response schemas)
│   │   ├── __init__.py
│   │   ├── swimmer.py             # Swimmer data model
│   │   ├── heatmap.py             # Heatmap data model
│   │   ├── alert.py               # Alert model (future)
│   │   └── camera.py              # Camera metadata model
│   │
│   ├── routes/                    # API route handlers
│   │   ├── __init__.py
│   │   ├── swimmers.py            # GET /api/swimmers
│   │   ├── heatmap.py             # GET /api/heatmap
│   │   ├── alerts.py              # GET /api/alerts (future)
│   │   ├── cameras.py             # GET /api/cameras
│   │   └── websocket.py           # WebSocket /ws endpoint
│   │
│   ├── services/                  # Business logic layer
│   │   ├── __init__.py
│   │   ├── swimmer_service.py     # Process swimmer data from AI
│   │   ├── heatmap_service.py     # Process heatmap data
│   │   └── websocket_service.py   # Broadcast updates to connected clients
│   │
│   ├── repositories/              # Database access layer
│   │   ├── __init__.py
│   │   ├── swimmer_repository.py  # CRUD for swimmers
│   │   ├── heatmap_repository.py  # CRUD for heatmap
│   │   └── alert_repository.py    # CRUD for alerts
│   │
│   └── utils/                     # Helper functions
│       ├── __init__.py
│       └── logger.py              # Logging configuration
│
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Docker container
└── .env.example                   # Environment variables template
```

---

## 🗄️ MongoDB Collections (Database Schema)

### 1. **swimmers** Collection
```javascript
{
  _id: ObjectId,
  camera_id: "cam_001",
  track_id: 5,
  bbox: {
    x1: 100,
    y1: 200,
    x2: 150,
    y2: 300
  },
  confidence: 0.95,
  first_seen: ISODate("2025-12-30T12:00:00Z"),
  last_seen: ISODate("2025-12-30T12:05:30Z"),
  status: "active",  // active, inactive, alerted
  created_at: ISODate("2025-12-30T12:00:00Z"),
  updated_at: ISODate("2025-12-30T12:05:30Z")
}
```

**Purpose:** Store current and historical swimmer tracking data

**Indexes:**
- `camera_id` + `track_id` (compound, unique)
- `status`
- `last_seen` (for cleanup of old tracks)

---

### 2. **heatmaps** Collection
```javascript
{
  _id: ObjectId,
  camera_id: "cam_001",
  timestamp: ISODate("2025-12-30T12:00:00Z"),
  data: {
    width: 640,
    height: 360,
    values: [[0.1, 0.5, ...], [0.2, 0.3, ...]]  // 2D array or base64 image
  },
  metadata: {
    decay: 0.98,
    gauss_sigma: 12
  },
  created_at: ISODate("2025-12-30T12:00:00Z")
}
```

**Purpose:** Store heatmap snapshots (latest only, or periodic snapshots)

**Indexes:**
- `camera_id` + `timestamp` (compound)
- TTL index on `created_at` (auto-delete old heatmaps after 24 hours)

---

### 3. **alerts** Collection (Future)
```javascript
{
  _id: ObjectId,
  camera_id: "cam_001",
  track_id: 5,
  alert_type: "stationary",  // stationary, erratic, zone_violation
  severity: "critical",       // low, medium, high, critical
  risk_score: 85,
  timestamp: ISODate("2025-12-30T12:05:00Z"),
  snapshot_url: "/data/alerts/alert_001.jpg",
  status: "active",           // active, acknowledged, resolved
  acknowledged_by: null,
  acknowledged_at: null,
  resolved_at: null,
  created_at: ISODate("2025-12-30T12:05:00Z")
}
```

**Purpose:** Store risk alerts for lifeguard action

**Indexes:**
- `camera_id`
- `status`
- `severity`
- `timestamp`

---

### 4. **cameras** Collection
```javascript
{
  _id: ObjectId,
  camera_id: "cam_001",
  name: "North Beach Camera",
  location: {
    beach: "Santa Monica Beach",
    coordinates: { lat: 34.02, lng: -118.48 }
  },
  status: "active",           // active, inactive, maintenance
  rtsp_url: "rtsp://...",     // (encrypted/secured)
  created_at: ISODate("2025-12-30T10:00:00Z"),
  updated_at: ISODate("2025-12-30T12:00:00Z")
}
```

**Purpose:** Manage camera metadata (for multi-camera support)

**Indexes:**
- `camera_id` (unique)
- `status`

---

## 🔌 REST API Endpoints

### **GET /api/swimmers**
**Description:** Get current active swimmers

**Query Parameters:**
- `camera_id` (optional) - Filter by camera
- `status` (optional) - Filter by status (active, inactive)
- `limit` (optional) - Max results (default: 100)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "track_id": 5,
      "camera_id": "cam_001",
      "bbox": { "x1": 100, "y1": 200, "x2": 150, "y2": 300 },
      "confidence": 0.95,
      "first_seen": "2025-12-30T12:00:00Z",
      "last_seen": "2025-12-30T12:05:30Z",
      "status": "active"
    }
  ],
  "count": 1
}
```

---

### **GET /api/heatmap**
**Description:** Get latest heatmap for a camera

**Query Parameters:**
- `camera_id` (required)

**Response:**
```json
{
  "success": true,
  "data": {
    "camera_id": "cam_001",
    "timestamp": "2025-12-30T12:00:00Z",
    "image_url": "/api/heatmap/cam_001/latest.png",
    "metadata": {
      "width": 640,
      "height": 360
    }
  }
}
```

---

### **GET /api/alerts**
**Description:** Get recent alerts

**Query Parameters:**
- `camera_id` (optional)
- `status` (optional) - active, acknowledged, resolved
- `severity` (optional) - low, medium, high, critical
- `limit` (optional) - default: 50

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "alert_id": "alert_001",
      "camera_id": "cam_001",
      "track_id": 5,
      "alert_type": "stationary",
      "severity": "critical",
      "risk_score": 85,
      "timestamp": "2025-12-30T12:05:00Z",
      "status": "active"
    }
  ],
  "count": 1
}
```

---

### **GET /api/cameras**
**Description:** Get all cameras

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "camera_id": "cam_001",
      "name": "North Beach Camera",
      "status": "active",
      "location": {
        "beach": "Santa Monica Beach"
      }
    }
  ],
  "count": 1
}
```

---

### **POST /api/data/ingest** (Internal Endpoint)
**Description:** Receive data from AI pipeline

**Request Body:**
```json
{
  "camera_id": "cam_001",
  "timestamp": "2025-12-30T12:00:00Z",
  "swimmers": [
    {
      "track_id": 5,
      "bbox": { "x1": 100, "y1": 200, "x2": 150, "y2": 300 },
      "confidence": 0.95
    }
  ],
  "heatmap": {
    "width": 640,
    "height": 360,
    "data": "base64_encoded_image"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Data ingested successfully"
}
```

---

## 🔄 WebSocket Endpoint

### **WS /ws/feed**
**Description:** Real-time updates for dashboard

**Connection URL:** `ws://localhost:8000/ws/feed?camera_id=cam_001`

**Message Format (Server → Client):**
```json
{
  "type": "update",
  "camera_id": "cam_001",
  "timestamp": "2025-12-30T12:00:00Z",
  "data": {
    "swimmers": [...],
    "swimmer_count": 5,
    "heatmap_updated": true
  }
}
```

**Message Types:**
- `update` - Regular swimmer position updates
- `alert` - New alert triggered
- `heatmap` - Heatmap updated
- `status` - Camera status change

---

## 🏗️ Service Layer Architecture

### **swimmer_service.py**
**Responsibilities:**
- Receive swimmer data from AI pipeline
- Update or create swimmer records in DB
- Mark inactive swimmers (not seen in last N seconds)
- Trigger WebSocket broadcast

**Key Functions:**
```python
async def process_swimmer_data(camera_id, swimmers_list, timestamp)
async def mark_inactive_swimmers(camera_id, current_timestamp)
async def get_active_swimmers(camera_id=None)
```

---

### **heatmap_service.py**
**Responsibilities:**
- Receive heatmap data from AI pipeline
- Store latest heatmap in DB (or file system)
- Generate heatmap image for API response
- Trigger WebSocket broadcast

**Key Functions:**
```python
async def process_heatmap_data(camera_id, heatmap_data, timestamp)
async def get_latest_heatmap(camera_id)
async def generate_heatmap_image(camera_id)
```

---

### **websocket_service.py**
**Responsibilities:**
- Manage active WebSocket connections
- Broadcast updates to connected clients
- Handle client subscriptions (per-camera filtering)

**Key Functions:**
```python
async def connect_client(websocket, camera_id)
async def disconnect_client(websocket)
async def broadcast_update(camera_id, data)
```

---

## 🔧 Configuration (`config.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "beach_safety"
    
    # API
    API_PREFIX: str = "/api"
    API_VERSION: str = "v1"
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    
    # Data retention
    SWIMMER_INACTIVE_THRESHOLD: int = 10  # seconds
    HEATMAP_RETENTION_HOURS: int = 24
    
    # CORS
    ALLOWED_ORIGINS: list = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
```

---

## 📦 Dependencies (`requirements.txt`)

```
# FastAPI & Server
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# MongoDB
motor==3.3.2              # Async MongoDB driver
pymongo==4.6.0

# Data validation
pydantic==2.5.0
pydantic-settings==2.1.0

# WebSocket
websockets==12.0

# Utilities
python-dotenv==1.0.0
```

---

## 🚀 Data Flow Summary

```
AI Pipeline (main.py)
    ↓
POST /api/data/ingest
    ↓
Backend Services Process Data
    ↓
MongoDB Collections Updated
    ↓
WebSocket Broadcast to Clients
    ↓
Frontend Dashboard Updates in Real-Time
```

---

## ✅ Phase 1 Implementation Checklist

- [ ] Create backend folder structure
- [ ] Set up MongoDB connection (`database.py`)
- [ ] Define Pydantic models (`models/`)
- [ ] Implement repositories (`repositories/`)
- [ ] Create service layer (`services/`)
- [ ] Build REST API routes (`routes/`)
- [ ] Add WebSocket endpoint (`routes/websocket.py`)
- [ ] Set up configuration (`config.py`)
- [ ] Write Dockerfile
- [ ] Add logging utilities
- [ ] Test API endpoints with Postman/curl

---

## 🎯 Key Design Principles

1. **Separation of Concerns**
   - Models → Data structures
   - Repositories → Database access
   - Services → Business logic
   - Routes → HTTP handlers

2. **Async/Await Throughout**
   - All database operations async
   - WebSocket connections async
   - Non-blocking I/O

3. **Type Safety**
   - Pydantic models for validation
   - Type hints in all functions

4. **Error Handling**
   - Try/except blocks in services
   - Meaningful error responses
   - Logging for debugging

5. **Scalability**
   - Multi-camera support built-in
   - Stateless API (can scale horizontally)
   - MongoDB indexes for performance

---

## ❓ Questions for Approval

1. **Is FastAPI + MongoDB acceptable?** (vs Node.js + Express)
2. **Should we store heatmap as image file or in MongoDB?**
3. **Do you want authentication/API keys for Phase 1?** (can add later)
4. **Any specific requirements for the ingest endpoint?**

---

## ✋ WAITING FOR YOUR APPROVAL TO PROCEED WITH IMPLEMENTATION

Once approved, I will:
1. Create the folder structure
2. Write all models, services, routes
3. Add comprehensive comments
4. Test all endpoints
5. Prepare for Phase 2 (Frontend)

