# Beach Safety AI Video Analysis System

🏖️ Real-time AI-powered video analysis for beach safety monitoring

## 🎯 MVP Goal
Zero-cost proof-of-concept to demonstrate:
- Live RTSP camera stream processing
- Real-time swimmer detection and tracking
- Automated alert system for abnormal behavior
- Live monitoring dashboard

## 📁 Project Structure

```
beach-assistant/
├── ai/          # AI Worker Service (YOLOv8 detection, tracking)
├── backend/     # FastAPI Backend (REST API, WebSocket, business logic)
├── frontend/    # React Dashboard (real-time UI)
├── docker/      # Docker Compose configurations
└── ARCHITECTURE.md  # Detailed system design
```

## 🚀 Quick Start (Coming Soon)

```bash
# 1. Clone and navigate
cd "Beach Assistant"

# 2. Start all services
docker-compose up

# 3. Open dashboard
open http://localhost:3000
```

## 💰 Cost
**$0.00** - 100% free and local for MVP

## 🛠️ Tech Stack
- **AI**: YOLOv8, OpenCV, ByteTrack
- **Backend**: FastAPI, SQLite, Redis
- **Frontend**: React, TypeScript, WebSocket
- **Deploy**: Docker Compose

## 📋 Status
🏗️ **In Development** - Setting up project structure

---

For detailed architecture, see [ARCHITECTURE.md](./ARCHITECTURE.md)

