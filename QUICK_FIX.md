# 🚨 Quick Fix for WebSocket Connection

## Immediate Steps:

### **1. Check Backend is Running:**
```bash
# In terminal, check if backend is running:
lsof -ti:8000

# If not running, start it:
cd backend
python -m app.main
```

### **2. Check Browser Console:**
1. Open browser (http://localhost:5173)
2. Press **F12** to open DevTools
3. Go to **Console** tab
4. Look for WebSocket connection logs:
   - `🔌 Connecting to WebSocket: ws://localhost:8000/ws/feed?camera_id=...`
   - `✅ WebSocket connected successfully` (good!)
   - `❌ WebSocket error event:` (bad - shows the error)

### **3. Common Issues & Fixes:**

#### **Issue: "Connection refused"**
**Fix:** Backend not running
```bash
cd backend
python -m app.main
```

#### **Issue: "Failed to connect"**
**Fix:** Check backend logs for errors
- Look for WebSocket route registration
- Check if port 8000 is available

#### **Issue: Connected but no data**
**Fix:** Check camera_id matching
- Frontend camera_id must match AI pipeline camera_id
- Check console logs for camera_id values

### **4. Test WebSocket Manually:**

Open browser console and run:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/feed?camera_id=cam_001')
ws.onopen = () => console.log('✅ Connected!')
ws.onmessage = (e) => console.log('📨 Message:', e.data)
ws.onerror = (e) => console.error('❌ Error:', e)
ws.onclose = (e) => console.log('🔌 Closed:', e.code, e.reason)
```

If this works, the WebSocket endpoint is fine. If not, backend has an issue.

### **5. Verify Data Flow:**

1. **Upload video** → Should see "Processing..." status
2. **Check backend terminal** → Should see AI pipeline starting
3. **Check backend logs** → Should see "Ingested data" messages
4. **Check browser console** → Should see WebSocket messages

## 🔍 Debug Checklist:

- [ ] Backend running on port 8000?
- [ ] WebSocket route registered? (check /docs)
- [ ] Frontend connecting? (check console)
- [ ] Camera ID matching? (check logs)
- [ ] AI pipeline sending data? (check backend logs)
- [ ] WebSocket broadcasting? (check backend logs)

## 📝 Share These Logs:

If still not working, share:
1. Browser console logs (F12 → Console)
2. Backend terminal output
3. Any error messages

This will help identify the exact issue!

