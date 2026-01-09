# Beach Safety Monitor - Backend API

FastAPI backend for real-time beach safety monitoring with AI integration.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure MongoDB Atlas

Create a `.env` file with your MongoDB connection:

```env
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=beach_safety
DEBUG=True
```

Get free MongoDB Atlas cluster at: https://cloud.mongodb.com/

### 3. Run Server

```bash
# From backend directory
python -m app.main

# Or with uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server runs at: **http://localhost:8000**

API documentation: **http://localhost:8000/docs**

---

## 📡 API Endpoints

### REST APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API health check |
| `/health` | GET | System health status |
| `/api/swimmers` | GET | Get active swimmers |
| `/api/data/ingest` | POST | Receive AI pipeline data |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `/ws/feed?camera_id=cam_001` | Real-time updates |

---

## 🏗️ Project Structure

```
backend/
├── app/
│   ├── models/          # Pydantic data models
│   │   ├── swimmer.py
│   │   ├── heatmap.py
│   │   ├── alert.py
│   │   └── camera.py
│   │
│   ├── repositories/    # Database access layer
│   │   ├── swimmer_repository.py
│   │   ├── heatmap_repository.py
│   │   ├── alert_repository.py
│   │   └── camera_repository.py
│   │
│   ├── services/        # Business logic
│   │   ├── swimmer_service.py
│   │   └── websocket_service.py
│   │
│   ├── routes/          # API endpoints
│   │   ├── swimmers.py
│   │   ├── ingest.py
│   │   └── websocket.py
│   │
│   ├── utils/           # Utilities
│   │   └── logger.py
│   │
│   ├── config.py        # Configuration
│   ├── database.py      # MongoDB connection
│   └── main.py          # FastAPI app
│
├── requirements.txt     # Dependencies
└── README.md           # This file
```

---

## 🔌 Integration with AI Pipeline

### Sending Data from AI to Backend

From your AI `main.py`, send data to the backend:

```python
import requests

# After processing each frame
response = requests.post(
    "http://localhost:8000/api/data/ingest",
    json={
        "camera_id": "cam_001",
        "timestamp": time.time(),
        "swimmers": [
            {
                "track_id": person.track_id,
                "bbox": {
                    "x1": person.bbox[0],
                    "y1": person.bbox[1],
                    "x2": person.bbox[2],
                    "y2": person.bbox[3]
                },
                "confidence": person.confidence
            }
            for person in tracked_people
        ]
    }
)
```

---

## 🧪 Testing

### Test API Health

```bash
curl http://localhost:8000/health
```

### Test Swimmer Endpoint

```bash
curl http://localhost:8000/api/swimmers?camera_id=cam_001
```

### Test WebSocket (with wscat)

```bash
npm install -g wscat
wscat -c ws://localhost:8000/ws/feed?camera_id=cam_001
```

---

## 📊 MongoDB Collections

### swimmers
```json
{
  "camera_id": "cam_001",
  "track_id": 5,
  "bbox": {"x1": 100, "y1": 200, "x2": 150, "y2": 300},
  "confidence": 0.95,
  "first_seen": "2025-12-30T12:00:00Z",
  "last_seen": "2025-12-30T12:05:30Z",
  "status": "active"
}
```

### heatmaps
```json
{
  "camera_id": "cam_001",
  "timestamp": "2025-12-30T12:00:00Z",
  "data": {...},
  "metadata": {"width": 640, "height": 360}
}
```

### alerts
```json
{
  "alert_id": "alert_abc123",
  "camera_id": "cam_001",
  "track_id": 5,
  "alert_type": "stationary",
  "severity": "critical",
  "risk_score": 85,
  "timestamp": "2025-12-30T12:05:00Z",
  "status": "active"
}
```

---

## 🔧 Configuration Options

Set in `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URL` | localhost | MongoDB connection string |
| `DATABASE_NAME` | beach_safety | Database name |
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 8000 | Server port |
| `DEBUG` | True | Debug mode |
| `SWIMMER_INACTIVE_THRESHOLD` | 10 | Seconds before marking inactive |
| `HEATMAP_RETENTION_HOURS` | 24 | Auto-delete old heatmaps |

---

## 📝 Development

### Code Style
- Comprehensive docstrings in all modules
- Type hints throughout
- Async/await for all I/O operations
- Repository pattern for database access

### Architecture
- **Models:** Pydantic schemas for validation
- **Repositories:** Database CRUD operations
- **Services:** Business logic
- **Routes:** HTTP/WebSocket endpoints

---

## 🐛 Troubleshooting

### MongoDB Connection Failed
- Check your `MONGODB_URL` in `.env`
- Verify MongoDB Atlas IP whitelist (allow 0.0.0.0/0 for testing)
- Confirm database user has read/write permissions

### Port Already in Use
```bash
# Change port in .env
PORT=8001

# Or kill existing process
lsof -ti:8000 | xargs kill -9
```

---

## ✅ Status

Backend is **100% complete** and ready for production use!

- ✅ MongoDB integration
- ✅ REST API endpoints
- ✅ WebSocket real-time updates
- ✅ Complete documentation
- ✅ Error handling
- ✅ Type safety with Pydantic


