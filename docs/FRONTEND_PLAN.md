# 🎨 PHASE 2: FRONTEND ARCHITECTURE PLAN

## 📋 Overview

Building a **React** dashboard with:
1. Professional, clean UI (classic dashboard style)
2. Real-time swimmer tracking visualization
3. Heatmap overlay on video feed
4. Statistics and alerts panel
5. WebSocket integration for live updates

**Tech Stack:**
- **React 18** → Modern hooks, concurrent features
- **TypeScript** → Type safety
- **Tailwind CSS** → Clean, utility-first styling
- **React Query** → Data fetching and caching
- **Zustand** → Lightweight state management
- **WebSocket** → Real-time updates from backend

---

## 📁 Frontend Folder Structure

```
frontend/
├── public/
│   ├── index.html
│   └── favicon.ico
│
├── src/
│   ├── App.tsx                    # Main app component
│   ├── index.tsx                  # Entry point
│   ├── index.css                  # Global styles (Tailwind)
│   │
│   ├── components/                # Reusable UI components
│   │   ├── Layout/
│   │   │   ├── Header.tsx         # Top navigation bar
│   │   │   ├── Sidebar.tsx        # Left sidebar (camera selection)
│   │   │   └── Layout.tsx         # Main layout wrapper
│   │   │
│   │   ├── VideoFeed/
│   │   │   ├── VideoPlayer.tsx    # Live video display
│   │   │   ├── BoundingBox.tsx    # Swimmer bounding box overlay
│   │   │   └── VideoControls.tsx  # Play/pause/camera selector
│   │   │
│   │   ├── Heatmap/
│   │   │   ├── HeatmapOverlay.tsx # Heatmap visualization
│   │   │   └── HeatmapLegend.tsx  # Color scale legend
│   │   │
│   │   ├── Stats/
│   │   │   ├── SwimmerStats.tsx   # Swimmer count, avg time
│   │   │   ├── StatsCard.tsx      # Individual stat card
│   │   │   └── Charts.tsx         # Time-series charts
│   │   │
│   │   ├── Alerts/
│   │   │   ├── AlertsPanel.tsx    # Alert list sidebar
│   │   │   ├── AlertCard.tsx      # Individual alert card
│   │   │   └── AlertBadge.tsx     # Alert severity badge
│   │   │
│   │   └── Common/
│   │       ├── Loading.tsx        # Loading spinner
│   │       ├── ErrorBoundary.tsx  # Error handling
│   │       └── Card.tsx           # Generic card component
│   │
│   ├── pages/                     # Page components
│   │   ├── Dashboard.tsx          # Main dashboard page
│   │   ├── CameraView.tsx         # Single camera view
│   │   └── Settings.tsx           # Settings page (future)
│   │
│   ├── hooks/                     # Custom React hooks
│   │   ├── useWebSocket.ts        # WebSocket connection hook
│   │   ├── useSwimmers.ts         # Fetch swimmer data
│   │   ├── useHeatmap.ts          # Fetch heatmap data
│   │   └── useAlerts.ts           # Fetch alerts
│   │
│   ├── services/                  # API client services
│   │   ├── api.ts                 # Axios instance configuration
│   │   ├── swimmerService.ts      # Swimmer API calls
│   │   ├── heatmapService.ts      # Heatmap API calls
│   │   ├── alertService.ts        # Alert API calls
│   │   └── websocketService.ts    # WebSocket management
│   │
│   ├── store/                     # State management (Zustand)
│   │   ├── index.ts
│   │   ├── swimmerStore.ts        # Swimmer state
│   │   ├── alertStore.ts          # Alert state
│   │   └── uiStore.ts             # UI state (selected camera, etc)
│   │
│   ├── types/                     # TypeScript types
│   │   ├── swimmer.ts
│   │   ├── alert.ts
│   │   ├── camera.ts
│   │   └── heatmap.ts
│   │
│   └── utils/                     # Utility functions
│       ├── formatters.ts          # Date/time formatters
│       ├── constants.ts           # App constants
│       └── colors.ts              # Color utilities for bounding boxes
│
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
├── Dockerfile
└── .env.example
```

---

## 🎨 UI Layout Design

### **Dashboard Page Layout**

```
┌────────────────────────────────────────────────────────────┐
│  🏖️ Beach Safety Monitor          [Camera Selector] [●Live]│ ← Header
├────────────┬──────────────────────────────────┬────────────┤
│            │                                  │            │
│  Cameras   │      🎥 Live Video Feed          │  Alerts    │
│            │      with Bounding Boxes         │            │
│  ○ Cam 1   │      + Heatmap Overlay          │  🔴 Alert 1│
│  ● Cam 2   │                                  │  🟡 Alert 2│
│  ○ Cam 3   │                                  │            │
│            │                                  │            │
│            ├──────────────────────────────────┤            │
│            │  📊 Statistics Dashboard         │            │
│            │  ┌──────┐ ┌──────┐ ┌──────┐    │            │
│            │  │ 12   │ │ 3:45 │ │  5   │    │            │
│            │  │Active│ │ Avg  │ │Today │    │            │
│            │  └──────┘ └──────┘ └──────┘    │            │
└────────────┴──────────────────────────────────┴────────────┘
   Sidebar         Main Content Area            Right Panel
```

---

## 🧩 Component Specifications

### **1. VideoPlayer.tsx**

**Purpose:** Display live video feed with swimmer bounding boxes

**Props:**
```typescript
interface VideoPlayerProps {
  cameraId: string;
  swimmers: Swimmer[];
  showHeatmap: boolean;
}
```

**Features:**
- Canvas overlay for bounding boxes
- Real-time rendering (60 FPS)
- Auto-resize to container
- Click on swimmer to highlight

**Implementation Notes:**
```typescript
// Uses HTML5 Canvas to draw bounding boxes
// Updates canvas on swimmers state change
// Renders video via <img> tag updated from WebSocket (MJPEG) or HLS
```

---

### **2. HeatmapOverlay.tsx**

**Purpose:** Overlay heatmap on video feed

**Props:**
```typescript
interface HeatmapOverlayProps {
  cameraId: string;
  opacity: number;  // 0-1
}
```

**Features:**
- Fetch heatmap image from API
- Blend with video using CSS opacity
- Toggle on/off
- Real-time updates

---

### **3. SwimmerStats.tsx**

**Purpose:** Display swimmer statistics

**Props:**
```typescript
interface SwimmerStatsProps {
  swimmers: Swimmer[];
}
```

**Displays:**
- Active swimmer count
- Average time in water
- Peak activity time
- Total swimmers today

**Layout:**
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│     12      │  │    3:45     │  │      5      │
│   Active    │  │  Avg Time   │  │    Today    │
│  Swimmers   │  │  In Water   │  │   Alerts    │
└─────────────┘  └─────────────┘  └─────────────┘
```

---

### **4. AlertsPanel.tsx**

**Purpose:** Display real-time alerts

**Props:**
```typescript
interface AlertsPanelProps {
  alerts: Alert[];
  onAlertClick: (alertId: string) => void;
}
```

**Features:**
- Scrollable list of alerts
- Color-coded by severity (red, yellow, gray)
- Click to zoom to swimmer
- Auto-dismiss old alerts
- New alert animation

**Alert Card Layout:**
```
┌────────────────────────────┐
│ 🔴 CRITICAL                │
│ Swimmer #5 - Stationary    │
│ 2 minutes ago              │
│ [View] [Acknowledge]       │
└────────────────────────────┘
```

---

## 📡 WebSocket Integration

### **useWebSocket.ts Hook**

```typescript
interface WebSocketMessage {
  type: 'update' | 'alert' | 'heatmap' | 'status';
  camera_id: string;
  timestamp: string;
  data: any;
}

function useWebSocket(cameraId: string) {
  const [swimmers, setSwimmers] = useState<Swimmer[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/feed?camera_id=${cameraId}`);
    
    ws.onopen = () => setIsConnected(true);
    
    ws.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      switch (message.type) {
        case 'update':
          setSwimmers(message.data.swimmers);
          break;
        case 'alert':
          // Trigger alert notification
          break;
        case 'heatmap':
          // Trigger heatmap refresh
          break;
      }
    };
    
    ws.onerror = (error) => console.error('WebSocket error:', error);
    ws.onclose = () => setIsConnected(false);
    
    return () => ws.close();
  }, [cameraId]);
  
  return { swimmers, isConnected };
}
```

---

## 🎨 Tailwind CSS Styling Guide

### **Color Scheme (Professional, Clean)**

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',  // Main blue
          600: '#2563eb',
          700: '#1d4ed8',
        },
        danger: {
          500: '#ef4444',  // Red for critical alerts
          600: '#dc2626',
        },
        warning: {
          500: '#f59e0b',  // Yellow for warnings
        },
        success: {
          500: '#10b981',  // Green for normal
        },
        neutral: {
          100: '#f3f4f6',
          200: '#e5e7eb',
          800: '#1f2937',
          900: '#111827',
        }
      }
    }
  }
}
```

### **Component Styling Examples**

**Card:**
```tsx
<div className="bg-white rounded-lg shadow-md p-6 border border-neutral-200">
  {/* Content */}
</div>
```

**Stat Card:**
```tsx
<div className="bg-gradient-to-br from-primary-50 to-primary-100 rounded-lg p-4">
  <div className="text-3xl font-bold text-primary-700">12</div>
  <div className="text-sm text-neutral-600">Active Swimmers</div>
</div>
```

**Alert Badge:**
```tsx
<span className={`
  px-2 py-1 rounded-full text-xs font-semibold
  ${severity === 'critical' ? 'bg-danger-500 text-white' : ''}
  ${severity === 'warning' ? 'bg-warning-500 text-white' : ''}
`}>
  {severity.toUpperCase()}
</span>
```

---

## 📊 Data Types (TypeScript)

### **types/swimmer.ts**
```typescript
export interface Swimmer {
  track_id: number;
  camera_id: string;
  bbox: BoundingBox;
  confidence: number;
  first_seen: string;  // ISO timestamp
  last_seen: string;
  status: 'active' | 'inactive' | 'alerted';
}

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}
```

### **types/alert.ts**
```typescript
export interface Alert {
  alert_id: string;
  camera_id: string;
  track_id: number;
  alert_type: 'stationary' | 'erratic' | 'zone_violation';
  severity: 'low' | 'medium' | 'high' | 'critical';
  risk_score: number;
  timestamp: string;
  status: 'active' | 'acknowledged' | 'resolved';
  snapshot_url?: string;
}
```

### **types/camera.ts**
```typescript
export interface Camera {
  camera_id: string;
  name: string;
  location: {
    beach: string;
    coordinates?: { lat: number; lng: number };
  };
  status: 'active' | 'inactive' | 'maintenance';
}
```

---

## 🔄 State Management (Zustand)

### **store/swimmerStore.ts**
```typescript
import create from 'zustand';

interface SwimmerStore {
  swimmers: Swimmer[];
  selectedSwimmerId: number | null;
  setSwimmers: (swimmers: Swimmer[]) => void;
  selectSwimmer: (id: number) => void;
  clearSelection: () => void;
}

export const useSwimmerStore = create<SwimmerStore>((set) => ({
  swimmers: [],
  selectedSwimmerId: null,
  setSwimmers: (swimmers) => set({ swimmers }),
  selectSwimmer: (id) => set({ selectedSwimmerId: id }),
  clearSelection: () => set({ selectedSwimmerId: null }),
}));
```

---

## 🛠️ Services Layer

### **services/swimmerService.ts**
```typescript
import axios from './api';

export const swimmerService = {
  // Get active swimmers for a camera
  getActiveSwimmers: async (cameraId: string): Promise<Swimmer[]> => {
    const response = await axios.get(`/swimmers?camera_id=${cameraId}&status=active`);
    return response.data.data;
  },
  
  // Get swimmer history
  getSwimmerHistory: async (cameraId: string, trackId: number): Promise<Swimmer[]> => {
    const response = await axios.get(`/swimmers/history?camera_id=${cameraId}&track_id=${trackId}`);
    return response.data.data;
  },
};
```

---

## 📦 Dependencies (package.json)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.2",
    "zustand": "^4.4.7",
    "@tanstack/react-query": "^5.14.0",
    "recharts": "^2.10.3"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "typescript": "^5.3.3",
    "vite": "^5.0.7",
    "tailwindcss": "^3.3.6",
    "postcss": "^8.4.32",
    "autoprefixer": "^10.4.16"
  }
}
```

---

## 🎯 Phase 2 Implementation Checklist

- [ ] Initialize React app with Vite + TypeScript
- [ ] Set up Tailwind CSS
- [ ] Create folder structure
- [ ] Define TypeScript types
- [ ] Build Layout components (Header, Sidebar)
- [ ] Create VideoPlayer component (placeholder)
- [ ] Create SwimmerStats components
- [ ] Create AlertsPanel components
- [ ] Set up Zustand stores
- [ ] Implement API services (axios)
- [ ] Add routing (React Router)
- [ ] Style with Tailwind (professional theme)
- [ ] Test with mock data

---

## 🔌 Phase 3 & 4 Preview

### **Phase 3: Integration with Backend**
- Connect API services to real backend
- Replace mock data with API calls
- Add error handling
- Loading states

### **Phase 4: Real-Time WebSocket**
- Implement useWebSocket hook
- Connect to backend WebSocket
- Real-time swimmer updates
- Real-time alert notifications
- Heatmap refresh on updates

---

## ✅ Key Design Principles

1. **Component Reusability**
   - Small, focused components
   - Props for customization
   - Common components in `/components/Common/`

2. **Type Safety**
   - TypeScript everywhere
   - Strict type checking
   - Interfaces for all data structures

3. **Performance**
   - React.memo for expensive components
   - useMemo/useCallback for optimization
   - Lazy loading for routes

4. **Clean Code**
   - Clear component names
   - Comments explaining data flow
   - Consistent naming conventions

5. **Responsive Design**
   - Works on desktop (primary)
   - Tablet support
   - Mobile view (basic)

---

## 🎨 UI/UX Priorities

1. **Clarity over Fancy**
   - No unnecessary animations
   - Clear labels and indicators
   - Professional color scheme

2. **Information Density**
   - Show important data first
   - Collapse less important info
   - Quick glanceability

3. **Real-Time Feedback**
   - Connection status indicator
   - Loading states
   - Error messages

4. **Actionable**
   - Click to view details
   - Quick acknowledge alerts
   - Easy camera switching

---

## ✋ WAITING FOR YOUR APPROVAL TO PROCEED

Both plans are ready:
- ✅ **Backend Plan** (BACKEND_PLAN.md)
- ✅ **Frontend Plan** (FRONTEND_PLAN.md)

**Ready to implement when you say GO!**

