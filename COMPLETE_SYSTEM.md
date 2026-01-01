# 🏖️ Complete Beach Safety Monitor System

## ✅ System Overview

**Complete workflow: Upload Video → AI Processing → Real-time Tracking Display**

The system now supports:
1. **Video Upload** - Users upload beach videos via web interface
2. **AI Processing** - Backend triggers AI pipeline to process video
3. **Real-time Tracking** - Swimmer detection, tracking IDs, bounding boxes
4. **Live Dashboard** - All data displayed in real-time with professional UI

---

## 🎯 What the System Does

### For Lifeguards:
- Upload any beach/swimming video
- See real-time swimmer detection with:
  - **Track IDs** (unique ID per swimmer)
  - **Bounding boxes** (visual tracking)
  - **Confidence scores** (detection accuracy)
  - **Time in view** (how long each swimmer has been tracked)
  - **Position data** (X, Y coordinates)
- Monitor multiple swimmers simultaneously
- Professional dashboard with all tracking data

### Technical Features:
- **YOLOv8** person detection
- **ByteTrack** multi-object tracking
- **Real-time WebSocket** updates
- **MongoDB** data storage
- **Professional UI** with detailed statistics

---

## 🚀 How to Use

### 1. Start Backend
```bash
cd backend
python -m app.main
```
Backend runs at: `http://localhost:8000`

### 2. Start Frontend
```bash
cd frontend
npm run dev
```
Frontend runs at: `http://localhost:5173`

### 3. Upload & Process Video

1. **Open web interface**: `http://localhost:5173`
2. **Upload video**: Drag & drop or click to select beach video
3. **Automatic processing**: 
   - Video uploads to backend
   - AI pipeline starts automatically
   - Real-time tracking begins
4. **Watch results**:
   - Video plays with bounding boxes
   - Swimmer table shows all tracked people
   - Statistics update in real-time
   - All data visible in dashboard

---

## 📊 Dashboard Features

### Top Statistics Cards:
- **Active Swimmers** - Current count
- **Average Confidence** - Detection accuracy
- **Average Time in View** - Per swimmer
- **Total Tracked Time** - Combined duration

### Video Player:
- Uploaded video display
- Real-time bounding boxes with track IDs
- Toggle boxes/heatmap
- Swimmer count overlay

### Swimmer Data Table:
Shows ALL tracking data:
- **Track ID** (with color indicator)
- **Position** (X, Y coordinates)
- **Confidence** (progress bar + %)
- **Time in View** (calculated duration)
- **Status** (active/inactive)

### System Status Panel:
- Backend API status
- WebSocket connection
- AI Pipeline status
- Video processing status

### Debug Panel:
- Click "🔍 Debug Data" (bottom-right)
- See all incoming data
- Connection status
- Raw JSON data

---

## 🔄 Data Flow

```
1. User uploads video (Frontend)
   ↓
2. Video saved to backend/uploads/ (Backend)
   ↓
3. Backend triggers AI pipeline (Backend)
   ↓
4. AI processes video frame-by-frame (AI Pipeline)
   ↓
5. Each frame's detections sent to backend (AI → Backend)
   ↓
6. Backend stores in MongoDB & broadcasts via WebSocket (Backend)
   ↓
7. Frontend receives real-time updates (WebSocket)
   ↓
8. Dashboard displays all tracking data (Frontend)
```

---

## 📁 Project Structure

```
Beach Assistant/
├── ai/                    # AI Pipeline
│   ├── main.py           # Main processing script
│   ├── detector.py       # YOLOv8 person detection
│   ├── tracker.py        # ByteTrack multi-object tracking
│   ├── video_input.py    # Video stream handling
│   ├── heatmap.py        # Activity heatmap
│   └── filter.py         # Detection filters
│
├── backend/               # FastAPI Backend
│   ├── app/
│   │   ├── routes/
│   │   │   ├── video.py      # Video upload & processing
│   │   │   ├── ingest.py     # AI data ingestion
│   │   │   ├── swimmers.py   # Swimmer API
│   │   │   └── websocket.py  # Real-time updates
│   │   ├── services/     # Business logic
│   │   ├── repositories/ # Database access
│   │   └── models/       # Data models
│   └── uploads/          # Uploaded videos (created automatically)
│
└── frontend/             # React Frontend
    ├── src/
    │   ├── App.tsx       # Main dashboard
    │   ├── components/
    │   │   ├── VideoUpload/VideoUploader.tsx
    │   │   ├── VideoFeed/VideoPlayer.tsx
    │   │   ├── Swimmers/SwimmerList.tsx
    │   │   └── Stats/DetailedStats.tsx
    │   ├── services/     # API clients
    │   └── store/        # State management
```

---

## 🎨 UI Features

### Professional Dashboard:
- Clean, modern design
- Gradient statistics cards
- Organized data tables
- Real-time updates
- Connection status indicators
- Debug panel for troubleshooting

### All Data Visible:
- Every tracked swimmer shown
- Complete position information
- Confidence scores
- Time tracking
- Status indicators

---

## 🔧 Configuration

### Backend Environment Variables:
```env
MONGODB_URL=mongodb+srv://...
DATABASE_NAME=beach_safety
BACKEND_URL=http://localhost:8000
DEBUG=True
```

### AI Pipeline Environment Variables:
```env
BACKEND_URL=http://localhost:8000
CAMERA_ID=upload_xxxxx  # Auto-generated
SEND_TO_BACKEND=true
```

---

## 🐛 Troubleshooting

### Video not processing?
- Check backend logs for errors
- Verify AI pipeline script exists at `ai/main.py`
- Check Python path (uses `python3` or `python`)

### No tracking data showing?
- Check WebSocket connection (green indicator)
- Verify AI pipeline is running
- Check browser console for errors
- Use Debug Panel to see incoming data

### Backend errors?
- Check MongoDB connection
- Verify uploads directory exists
- Check file permissions

---

## 🎯 Next Steps (Future)

1. **Live Camera Integration** - Connect RTSP cameras
2. **Behavior Analysis** - Detect abnormal behaviors
3. **Alert System** - Trigger alerts on risks
4. **Historical Data** - View past tracking sessions
5. **Multi-camera Support** - Monitor multiple beaches

---

## ✅ Current Status

**System is fully functional!**

- ✅ Video upload working
- ✅ AI processing working
- ✅ Real-time tracking working
- ✅ Dashboard displaying all data
- ✅ Professional UI complete
- ✅ All tracking data visible

**Ready for lifeguard use!** 🏖️👮‍♂️

