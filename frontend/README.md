# Beach Safety Monitor - Frontend

React + TypeScript dashboard for real-time beach safety monitoring.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Run Development Server

```bash
npm run dev
```

Frontend runs at: **http://localhost:5173**

---

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── components/      # React components
│   │   ├── Layout/      # Header, Sidebar
│   │   ├── VideoFeed/   # Live video player
│   │   ├── Stats/       # Statistics cards
│   │   ├── Alerts/      # Alert panel
│   │   └── Common/      # Reusable components
│   │
│   ├── hooks/           # Custom React hooks
│   ├── services/        # API client services
│   ├── store/           # Zustand state management
│   ├── types/           # TypeScript types
│   ├── utils/           # Utility functions
│   ├── pages/           # Page components
│   │
│   ├── App.tsx          # Main app component
│   └── index.css        # Tailwind CSS
│
├── package.json
├── tailwind.config.js
└── vite.config.ts
```

---

## 🎨 Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool & dev server
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **Zustand** - State management

---

## 📡 Backend Connection

Configure backend URL in `.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

## 🎯 Features (In Progress)

- ✅ Project setup with Vite + TypeScript
- ✅ Tailwind CSS configured
- ✅ TypeScript types defined
- ✅ Basic layout structure
- ⏳ Video feed component
- ⏳ Real-time WebSocket
- ⏳ Swimmer tracking display
- ⏳ Alerts panel
- ⏳ Statistics dashboard

---

## 📝 Development Status

**Phase 1:** Foundation ✅ Complete
- React + TypeScript + Vite
- Tailwind CSS
- Folder structure
- TypeScript types

**Phase 2:** Components (In Progress)
- Layout components
- Video feed
- Statistics cards
- Alerts panel

**Phase 3:** Integration (Upcoming)
- API services
- WebSocket
- State management
- Real-time updates

---

## 🔧 Available Scripts

```bash
npm run dev       # Start dev server
npm run build     # Build for production
npm run preview   # Preview production build
npm run lint      # Run ESLint
```

---

## 📚 Documentation

See `docs/FRONTEND_PLAN.md` for detailed architecture and implementation plan.
