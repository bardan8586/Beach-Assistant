# 🚀 TEST THE APP NOW - Step by Step

## ✅ Everything is Fixed!

### **Step 1: Start Backend**
```bash
cd backend
python -m app.main
```

**Look for:**
- `🚀 Starting Beach Safety Monitor Backend...`
- `✓ MongoDB connected`
- `INFO:     Application startup complete.`
- Server running on `http://0.0.0.0:8000`

### **Step 2: Start Frontend (New Terminal)**
```bash
cd frontend
npm run dev
```

**Look for:**
- `VITE v7.x.x  ready in xxx ms`
- `➜  Local:   http://localhost:5173/`

### **Step 3: Open Browser**
1. Go to: **http://localhost:5173**
2. **Press F12** to open DevTools
3. Go to **Console** tab

### **Step 4: Check WebSocket Connection**
In browser console, you should see:
```
🔌 Connecting to WebSocket: ws://localhost:8000/ws/feed?camera_id=cam_001
✅ WebSocket connected successfully
📨 WebSocket message received: connected
```

**If you see errors:**
- Check backend is running
- Check backend logs for WebSocket errors
- Try refreshing the page

### **Step 5: Upload Video**
1. Click "📁 Select Video File" or drag & drop
2. Select a beach/swimming video
3. Watch the console for:
   ```
   📹 Setting camera ID: upload_xxxxx
   🚀 AI processing started
   📨 WebSocket message received: swimmers
   ✅ Updated X swimmers
   ```

### **Step 6: Watch Real-Time Updates**
You should see:
- ✅ Video playing in browser
- ✅ Bounding boxes appearing on swimmers
- ✅ Swimmer list table populating
- ✅ Statistics cards updating
- ✅ Track IDs showing on boxes

## 🐛 If Something Doesn't Work

### **WebSocket Not Connecting:**
1. Check backend terminal for errors
2. Check browser console for error details
3. Verify backend is on port 8000: `lsof -ti:8000`

### **No Bounding Boxes:**
1. Check if swimmers data is received (console logs)
2. Check if "Boxes" toggle is ON
3. Check debug panel (bottom-right button)
4. Verify canvas is drawing (check console for errors)

### **No Swimmer Data:**
1. Check if AI pipeline is running (backend logs)
2. Check if data is being sent to `/api/data/ingest`
3. Check WebSocket is broadcasting (backend logs)
4. Check camera_id matching (console logs)

## ✅ Success Indicators

**Backend Console:**
- `✅ WebSocket connection accepted for camera: ...`
- `✅ Sent X swimmers to backend (Frame X, Camera: ...)`
- `Ingested data: camera=..., swimmers=X`

**Browser Console:**
- `✅ WebSocket connected successfully`
- `📨 WebSocket message received: swimmers`
- `✅ Updated X swimmers for camera ...`

**Web Interface:**
- Connection status: **Connected** (green)
- Swimmer count > 0
- Bounding boxes visible
- Table populated

## 🎯 You're Ready!

Everything is fixed and connected. Upload a video and watch the magic happen! 🏖️✨
