# MAI600 Assessment 3 – Beach Safety AI: Progress Report

**Project:** Beach Safety Monitor – AI Swimmer Detection System  
**Assessment:** MAI600 Assessment 3 (Group)  
**Purpose:** Clear status of completed work and remaining tasks for the final report

---

## Executive Summary

Beach Assistant is a **real-world computer vision application** for lifeguard decision support. It uses **YOLOv8** (CNN-based detection + pose) for person detection and tracking, combined with scene analysis, risk scoring, and alerts. A full-stack deployment (FastAPI + React + MongoDB) is in place, with real-time video processing and a web UI.

**Status:** Core system implemented and deployed. For the assignment, we still need formal dataset handling, custom/fine-tuned training, standard ML evaluation, and the written report.

---

## 1. Problem Formulation and Dataset Handling

### 1.1 What Is Done

| Item | Status | Description |
|------|--------|-------------|
| **Problem statement** | ✅ Done | Real-world beach safety: detect swimmers, track IDs, classify zones (Safe/Caution/Danger), assess drowning risk, and generate alerts for lifeguards |
| **Dataset sourcing** | ⚠️ Partial | Test videos in `tests/data/` (e.g. `Video_Generation_of_Beach_Swimming.mp4`, `vecteezy_group-of-people-swimming-on-the-open-sea_28424802.mov`). Source and licensing not yet documented |
| **Data format** | ✅ Done | Pipeline accepts video (MP4, AVI, MOV, MKV) and RTSP streams; frame extraction via OpenCV |
| **Preprocessing pipeline** | ⚠️ Partial | Frame extraction, resizing, detection filtering (size/position). No formal augmentation or normalisation pipeline documented |

### 1.2 What Needs to Be Done

- [ ] **Dataset documentation**
  - List all videos used (file names, sources, licensing)
  - Describe train/validation/test split (if fine-tuning)
  - Add any relevant public datasets (e.g. swimming/pool/beach datasets)
- [ ] **Preprocessing documentation**
  - Normalisation (pixel scaling, mean/std)
  - Augmentation (flip, brightness, contrast)
  - Handling of missing frames or corrupt data
- [ ] **Class imbalance**
  - Analyse distribution (people vs background, crowded vs sparse)
  - Document handling or mitigation strategy

---

## 2. Model Design and Implementation

### 2.1 What Is Done

| Component | Status | Description |
|-----------|--------|-------------|
| **YOLOv8 object detection** | ✅ Done | Person detection via Ultralytics YOLOv8. Default: fine-tuned `best.pt` (Roboflow drowning dataset) when present; else `yolov8s.pt`. Supports custom 7-class model (Drowning/Swimming/Out of Water/person). |
| **YOLOv8-Pose** | ✅ Done | Pose estimation for drowning-related behaviour (`yolov8n-pose.pt`) |
| **Multi-object tracking** | ✅ Done | ByteTrack-style tracking via Norfair; persistent track IDs |
| **Scene analysis** | ✅ Done | Shore line and horizon detection (`scene_analyzer.py`); water zones |
| **Water zone mapping** | ✅ Done | Safe/Caution/Danger zones from shore line (`water_analyzer.py`) |
| **Behaviour analysis** | ✅ Done | Motion, trajectory, velocity (`behavior_analyzer.py`); patterns (stationary, erratic, rapid) |
| **Risk engine** | ✅ Done | Multi-factor risk score (0–100) (`risk_engine.py`); factors: stationary, danger zone, erratic, rapid away, time in water |
| **Pose-based analysis** | ✅ Done | Pose → swimming action classification (`pose_analyzer.py`); drowning-related states |
| **Alert engine** | ✅ Done | Alert generation with hysteresis and throttling (`alert_engine.py`) |
| **Heatmap** | ✅ Done | Spatial activity heatmap (`heatmap.py`) |
| **Roboflow option** | ✅ Done | Detector can use Roboflow API instead of local YOLO |

**Architecture choice:** CNN (YOLOv8) for detection and pose, justified by real-time object detection needs and availability of pre-trained person/pose models.

### 2.2 What Needs to Be Done

- [ ] **Explicit architecture justification**
  - Why YOLOv8 vs other detectors (e.g. Faster R-CNN, DETR)
  - Why ByteTrack for tracking
- [x] **Custom training / fine-tuning** ✅ Done
  - Fine-tuned YOLOv8n on Roboflow drowning dataset (5 epochs); weights in `ai/runs/detect/runs-mai600/roboflow_v2_yolov8n_e5/weights/best.pt`. Pipeline now uses this model by default when present.
- [ ] **Diagram**
  - High-level model architecture (detector → tracker → risk/alert)

---

## 3. Training and Evaluation

### 3.1 What Is Done

| Item | Status | Description |
|------|--------|-------------|
| **Inference pipeline** | ✅ Done | Full inference flow: video → detection → tracking → risk → ingest |
| **Configuration** | ✅ Done | Confidence threshold, IOU, frame skip, multi-scale detection via env vars |
| **Tracking log** | ✅ Done | Per-frame tracking data logged to `tracking_log.csv` |
| **Real-time metrics** | ⚠️ Partial | FPS, latency, detection counts in logs. Standard ML metrics from training run (below). |
| **Fine-tuned training run** | ✅ Done | 5-epoch run on Roboflow dataset; mAP50 ≈ 61%, mAP50-95 ≈ 32%; results in `ai/runs/detect/runs-mai600/roboflow_v2_yolov8n_e5/`. |

### 3.2 What Needs to Be Done

- [x] **Custom training** ✅ Done – YOLOv8n fine-tuned on Roboflow; pipeline wired to use `best.pt` by default.
- [ ] **Formal evaluation**
  - Detection: mAP, precision, recall, F1
  - Tracking: MOT metrics if applicable
- [ ] **Baseline comparison**
  - Compare YOLOv8 vs simpler detector or older architecture
- [ ] **Hyperparameter tuning**
  - Confidence, IOU, learning rate (if training), frame skip
  - Document method (grid/random/Bayesian)
- [ ] **Training practices**
  - Early stopping, learning rate schedule (if training)
- [ ] **Visualisations**
  - Training/validation loss curves
  - Confusion matrix
  - ROC curve (if binary classification)
  - Attention or feature maps (if available)

---

## 4. Deployment Strategy

### 4.1 What Is Done

| Item | Status | Description |
|------|--------|-------------|
| **Backend API** | ✅ Done | FastAPI backend on port 8000; CORS, health check |
| **Video upload** | ✅ Done | `POST /api/video/upload` – save video, metadata |
| **AI processing** | ✅ Done | `POST /api/video/process/{id}` – spawn AI subprocess with env vars |
| **Data ingest** | ✅ Done | `POST /api/data/ingest` – receive frame results from AI |
| **Results storage** | ✅ Done | Per-video JSONL results for playback |
| **WebSocket** | ✅ Done | Real-time broadcast of frame results |
| **Frontend** | ✅ Done | React + Vite; upload, processing status, video playback with overlays |
| **Database** | ✅ Done | MongoDB Atlas for swimmers, cameras, alerts |
| **AI preflight** | ✅ Done | `GET /api/video/preflight` – check AI env (cv2, torch, ultralytics) |
| **OpenCV window** | ✅ Done | Optional local OpenCV window via `show_window` |

**Architecture:** Frontend ↔ Backend ↔ MongoDB; AI pipeline runs as subprocess, posts to ingest, backend broadcasts via WebSocket.

### 4.2 What Needs to Be Done

- [ ] **Deployment plan**
  - Hardware: CPU vs GPU, RAM, disk
  - Latency targets and current performance
  - Scalability (concurrent videos, multiple cameras)
- [ ] **Monitoring**
  - Drift detection, model performance over time
- [ ] **Documentation**
  - Runbook: how to deploy, start services, troubleshoot

---

## 5. Ethical Consideration

### 5.1 What Is Done

| Item | Status | Description |
|------|--------|-------------|
| **Risk-aware design** | ✅ Done | Risk scoring and alerts intended to support lifeguards, not replace them |
| **Transparency** | ⚠️ Partial | Bounding boxes and zones visible in UI; decision logic partially documented |

### 5.2 What Needs to Be Done

- [ ] **Bias audit**
  - Demographic, lighting, camera angle, swimmer density
  - Failure modes (false positives/negatives) and when they occur
- [ ] **Mitigation**
  - Calibration, thresholds, human-in-the-loop
- [ ] **Privacy**
  - Public vs private beaches; data retention, anonymisation
- [ ] ** societal impact**
  - Benefits (safety, response time) vs risks (over-reliance, false alerts)

---

## 6. Report Quality and Presentation

### 6.1 What Is Done

- Project README with architecture, setup, usage
- Code comments and docstrings
- No formal assessment report yet

### 6.2 What Needs to Be Done

- [ ] **Full report** including:
  1. Problem statement
  2. Literature review (YOLO, tracking, drowning detection, etc.)
  3. Dataset description and preprocessing
  4. Methodology (architecture, training if any)
  5. Results (metrics, visualisations, comparisons)
  6. Deployment strategy
  7. Ethical considerations
  8. References (academic and technical)
- [ ] **Figures**
  - Architecture diagram, sample outputs, metrics plots
- [ ] **Presentation**
  - Proofread, consistent formatting, clear structure

---

## 7. Project Structure (Reference)

```
Beach Assistant/
├── ai/                      # AI pipeline
│   ├── main.py             # Main pipeline
│   ├── detector.py         # YOLOv8 + Roboflow
│   ├── tracker.py          # ByteTrack
│   ├── filter.py           # Detection filters
│   ├── water_analyzer.py   # Zones
│   ├── behavior_analyzer.py
│   ├── risk_engine.py
│   ├── scene_analyzer.py
│   ├── pose_analyzer.py
│   ├── alert_engine.py
│   ├── heatmap.py
│   ├── advanced_tracker.py
│   ├── temporal_analyzer.py
│   ├── beach_calibration.py
│   └── requirements.txt
├── backend/                 # FastAPI
│   └── app/
│       ├── routes/         # video, ingest, websocket, swimmers, etc.
│       ├── models/
│       ├── services/
│       └── utils/
├── frontend/               # React + Vite
│   └── src/
│       ├── components/
│       ├── services/
│       └── store/
├── tests/
│   └── data/               # Test videos
└── docs/
```

---

## 8. Suggested Task Split for Group Members

| Member | Suggested focus |
|--------|------------------|
| **Member 1** | Dataset documentation, preprocessing, data quality |
| **Member 2** | Model design section, architecture justification, fine-tuning (if done) |
| **Member 3** | Training and evaluation, metrics, visualisations, baseline comparison |
| **Member 4** | Deployment strategy, monitoring, runbook |
| **Member 5** | Ethical considerations, bias audit, mitigation |

**Shared:** Literature review, final report assembly, formatting.

---

## 9. Priority Order for Completion

1. **Dataset documentation** – needed for all later sections  
2. **Formal evaluation** – run metrics on current model, baseline comparison  
3. **Fine-tuning experiment** (if time allows) – small training run  
4. **Ethical section** – bias audit and mitigation  
5. **Deployment plan** – document current setup and scaling  
6. **Report draft** – integrate all sections and references  

---

*Last updated: Feb 2026*
