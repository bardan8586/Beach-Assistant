# 🔧 WebSocket Debugging Guide

## ✅ Fixed Issues

### **1. Better Error Handling**
- Added detailed console logging
- Shows connection URL
- Shows readyState
- Shows close codes and reasons

### **2. Improved Connection Logic**
- Closes existing connections before reconnecting
- Handles connection errors gracefully
- Auto-reconnects only on unexpected disconnects

### **3. Backend WebSocket Fixes**
- Better error handling in receive loop
- Prevents blocking on receive errors

## 🔍 How to Debug

### **1. Check Browser Console:**
Open browser console (F12) and look for:
- `🔌 Connecting to WebSocket: ws://localhost:8000/ws/feed?camera_id=...`
- `✅ WebSocket connected successfully` (if working)
- `❌ WebSocket error event:` (if failing)

### **2. Check Backend Logs:**
Look for:
- `WebSocket connected: camera=...`
- `WebSocket disconnected: camera=...`
- Any error messages

### **3. Test WebSocket Manually:**
```bash
# Using wscat (install: npm install -g wscat)
wscat -c ws://localhost:8000/ws/feed?camera_id=cam_001

# Or using Python
python3 -c "
import asyncio
import websockets
async def test():
    async with websockets.connect('ws://localhost:8000/ws/feed?camera_id=cam_001') as ws:
        print('Connected!')
        msg = await ws.recv()
        print('Received:', msg)
asyncio.run(test())
"
```

## 🐛 Common Issues

### **Issue 1: Connection Refused**
**Symptom:** `WebSocket error: Event`
**Fix:** 
- Make sure backend is running: `cd backend && python -m app.main`
- Check port 8000 is not blocked
- Verify backend is listening: `lsof -ti:8000`

### **Issue 2: CORS Error**
**Symptom:** Connection fails with CORS error
**Fix:**
- Backend CORS is already configured
- WebSocket doesn't use CORS (different protocol)
- If still failing, check browser console

### **Issue 3: Wrong Camera ID**
**Symptom:** Connected but no data
**Fix:**
- Check camera_id in WebSocket URL matches the one AI pipeline uses
- Check console logs for camera_id matching

### **Issue 4: Backend Not Broadcasting**
**Symptom:** Connected but no messages
**Fix:**
- Check if AI pipeline is sending data to `/api/data/ingest`
- Check backend logs for "Ingested data" messages
- Verify WebSocket service is broadcasting

## ✅ Status Check

Run these commands to verify:

```bash
# 1. Check backend is running
curl http://localhost:8000/health

# 2. Check WebSocket endpoint exists
curl http://localhost:8000/docs
# Look for /ws/feed endpoint

# 3. Check frontend is connecting
# Open browser console and look for WebSocket logs
```

## 🚀 Next Steps

1. **Open browser console** (F12)
2. **Upload a video**
3. **Watch for WebSocket logs:**
   - Connection attempt
   - Connection success/failure
   - Messages received
4. **Check debug panel** for connection status

If still not working, share the console logs and I'll help debug further!

