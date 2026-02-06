# GeoRoute Project Manual

**Version 1.0** | **Last Updated: February 2026**

This document is the complete reference for the GeoRoute tactical route planning system. It covers installation, configuration, usage, architecture, API specifications, and customization.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Configuration Reference](#3-configuration-reference)
4. [User Guide](#4-user-guide)
5. [System Architecture](#5-system-architecture)
6. [API Reference](#6-api-reference)
7. [Data Models](#7-data-models)
8. [AI Prompts & Customization](#8-ai-prompts--customization)
9. [Frontend Architecture](#9-frontend-architecture)
10. [Backend Architecture](#10-backend-architecture)
11. [Troubleshooting](#11-troubleshooting)
12. [Extending the System](#12-extending-the-system)

---

## 1. Introduction

### 1.1 What is GeoRoute?

GeoRoute is an AI-powered tactical route planning system designed for infantry movement analysis. It combines:

- **Satellite Imagery**: Real-world ESRI World Imagery tiles
- **AI Analysis**: Google Gemini 3 Pro for visual route generation and analysis
- **Tactical Simulation**: Enemy vision cones, cover analysis, flanking detection
- **Interactive Mapping**: Leaflet-based map with NATO military symbols

### 1.2 Core Capabilities

| Capability | Description |
|------------|-------------|
| **Route Generation** | AI draws tactical routes directly on satellite imagery |
| **Route Evaluation** | Analyze user-drawn routes with position suggestions |
| **Tactical Simulation** | Vision cone analysis with cover detection |
| **Scoring System** | Multi-dimensional tactical scoring (0-100) |
| **Verdict System** | EXCELLENT / GOOD / ACCEPTABLE / RISKY classifications |

### 1.3 Geographic Scope

The system is restricted to the **Gulf Cooperation Council (GCC) region**:
- Saudi Arabia
- United Arab Emirates
- Kuwait
- Bahrain
- Qatar
- Oman

Coordinates outside this region (latitude 12-32°N, longitude 34-60°E) are rejected.

---

## 2. Installation

### 2.1 Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | 2.0+ | Multi-container orchestration |
| Google Cloud Account | - | API access |
| Git | 2.0+ | Clone repository |

### 2.2 API Keys Required

#### Google Maps API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select existing
3. Enable these APIs:
   - **Maps Elevation API**
   - **Maps Static API**
4. Create an API key with these APIs enabled

#### Gemini API Key (Option 1: AI Studio)
1. Go to [AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Key format: `AIzaSy...` (starts with "AIzaSy")

#### Vertex AI (Option 2: Enterprise)
See [Section 2.5 Vertex AI Setup](#25-vertex-ai-setup).

### 2.3 Basic Installation

```bash
# Clone the repository
git clone https://github.com/0aub/GeoRoute.git
cd GeoRoute

# Create environment file
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use any text editor
```

### 2.4 Environment Variables

Create a `.env` file with these variables:

```bash
# =============================================================================
# SERVER CONFIGURATION
# =============================================================================

# Backend API port (required)
BACKEND_PORT=8001

# Backend bind address
BACKEND_HOST=0.0.0.0

# Frontend port
UI_PORT=8080

# CORS origins (comma-separated)
# For development:
CORS_ORIGINS=http://localhost:8080
# For production:
# CORS_ORIGINS=http://your-domain.com,https://your-domain.com

# API URL for frontend to reach backend
VITE_API_URL=http://localhost:8001

# =============================================================================
# GOOGLE APIS (REQUIRED)
# =============================================================================

# Google Cloud Project ID
GOOGLE_CLOUD_PROJECT=your-project-id

# Google Maps API Key (needs Elevation + Static Maps APIs)
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# =============================================================================
# AI SERVICE - Choose ONE option
# =============================================================================

# OPTION 1: AI Studio (simpler, free tier available)
GEMINI_API_KEY=your-gemini-api-key

# OPTION 2: Vertex AI (higher quotas, requires billing)
# USE_VERTEX_AI=true
# VERTEX_LOCATION=us-central1
```

### 2.5 Vertex AI Setup

Vertex AI provides higher rate limits and is required for production workloads.

#### Step 1: Create Service Account
```bash
# In Google Cloud Console or gcloud CLI:
gcloud iam service-accounts create georoute-sa \
  --display-name="GeoRoute Service Account"
```

#### Step 2: Grant Permissions
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:georoute-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

#### Step 3: Download JSON Key
```bash
gcloud iam service-accounts keys create service-account.json \
  --iam-account=georoute-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

#### Step 4: Place Key File
Move `service-account.json` to the GeoRoute root directory:
```
GeoRoute/
├── service-account.json   <-- Here
├── docker-compose.yml
├── .env
└── ...
```

#### Step 5: Configure Environment
```bash
# In .env:
USE_VERTEX_AI=true
VERTEX_LOCATION=us-central1
GOOGLE_CLOUD_PROJECT=your-project-id

# GEMINI_API_KEY can be left empty or removed
```

### 2.6 Running the System

```bash
# Start all services
docker compose up --build

# Or run in background
docker compose up --build -d

# View logs
docker compose logs -f
```

### 2.7 Accessing the Application

| Service | URL | Description |
|---------|-----|-------------|
| **UI** | http://localhost:8080 | Main application interface |
| **API** | http://localhost:8001 | Backend REST API |
| **Health** | http://localhost:8001/api/health | Health check endpoint |

### 2.8 Stopping the System

```bash
# Stop and remove containers
docker compose down

# Stop, remove containers, and delete volumes
docker compose down -v
```

---

## 3. Configuration Reference

### 3.1 Application Configuration (config.yaml)

The file `georoute/config.yaml` contains all application settings and AI prompts.

#### Route Generation Settings

```yaml
route_generation:
  # Method for generating routes
  # Currently only "gemini_image" is supported
  method: "gemini_image"

  # Number of routes to generate (1-3)
  # 2 is recommended: balanced + stealth
  num_routes: 2
```

#### AI Model Selection

```yaml
gemini:
  # Model for drawing routes on satellite images
  # Requires image generation capability
  image_model: "gemini-3-pro-image-preview"

  # Model for text-based analysis and scoring
  text_model: "gemini-2.5-flash"

  # Model for vision-based tactical analysis
  # Used for simulation and route evaluation
  analysis_model: "gemini-3-flash-preview"
```

#### Marker Appearance

```yaml
markers:
  size: 6  # Marker radius in pixels
  start_color: [0, 100, 255]    # RGB: Blue for soldiers
  end_color: [255, 50, 50]      # RGB: Red for enemies
  outline_color: [255, 255, 255] # RGB: White outline
  outline_width: 2
```

#### Geographic Restrictions

```yaml
geo:
  gcc_bounds:
    north: 32.0   # Northern boundary (latitude)
    south: 12.0   # Southern boundary (latitude)
    east: 60.0    # Eastern boundary (longitude)
    west: 34.0    # Western boundary (longitude)
```

### 3.2 Enemy Vision Specifications

These are hardcoded in the frontend (`useMission.ts`) and backend (`balanced_tactical_pipeline.py`):

| Enemy Type | Range | Angle | Color |
|------------|-------|-------|-------|
| Sniper | 500m | 30° | Red |
| Rifleman | 100m | 60° | Red |
| Observer | 400m | 45° | Red |

### 3.3 Scoring Thresholds

Defined in `config.yaml` under `tactical_simulation_prompt`:

| Verdict | Score Range | Requirements |
|---------|-------------|--------------|
| EXCELLENT | 8.5 - 10.0 | 90%+ covered, rear flanking, zero exposed |
| GOOD | 6.5 - 8.4 | 75%+ covered, good flanking, max 1 exposed |
| ACCEPTABLE | 4.5 - 6.4 | 50-75% covered, some tactical thought |
| RISKY | 0 - 4.4 | <50% covered OR critical exposure OR frontal |

### 3.4 Docker Compose Configuration

The `docker-compose.yml` defines two services:

#### Backend Service (georoute-backend)

```yaml
georoute-backend:
  build:
    context: ./georoute
    dockerfile: Dockerfile
  ports:
    - "${BACKEND_PORT}:${BACKEND_PORT}"
  environment:
    - BACKEND_PORT=${BACKEND_PORT}
    - BACKEND_HOST=${BACKEND_HOST}
    - GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}
    - GEMINI_API_KEY=${GEMINI_API_KEY}
    - GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
    - CORS_ORIGINS=${CORS_ORIGINS}
    - RELOAD=true
    - USE_VERTEX_AI=${USE_VERTEX_AI:-false}
    - VERTEX_LOCATION=${VERTEX_LOCATION:-us-central1}
    - GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json
  volumes:
    - ./georoute:/app/georoute:ro  # Hot reload
    - ./service-account.json:/app/service-account.json:ro
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:${BACKEND_PORT}/api/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

#### Frontend Service (georoute-ui)

```yaml
georoute-ui:
  build:
    context: ./ui
    dockerfile: Dockerfile
  ports:
    - "${UI_PORT}:8080"
  environment:
    - VITE_API_URL=${VITE_API_URL}
  volumes:
    - ./ui/src:/app/src  # Hot reload
  depends_on:
    georoute-backend:
      condition: service_healthy
```

---

## 4. User Guide

### 4.1 Interface Overview

The application has three main areas:

1. **Map Area** (center): Interactive satellite map
2. **Sidebar** (left): Controls and settings
3. **Report Modal** (popup): Analysis results

### 4.2 Mode Selection

The sidebar has three mode tabs:

| Mode | Purpose |
|------|---------|
| **Route** | AI-generated tactical routes |
| **Draw** | Manual route drawing + evaluation |
| **Simulate** | Enemy vision cones + cover analysis |

### 4.3 Route Mode (AI Generation)

#### Step 1: Place Units
1. Click **"Place Soldier"** button
2. Click on the map to place a blue soldier marker
3. Click **"Place Enemy"** button
4. Click on the map to place a red enemy marker

**Requirements:**
- Zoom level must be 17 or higher
- Location must be within GCC region

#### Step 2: Generate Routes
1. Optionally enable **"Advanced Analytics"** for detailed report
2. Click **"Plan Tactical Attack"**
3. Wait for progress indicator (typically 30-90 seconds)

#### Step 3: View Results
- **Annotated Image**: Satellite image with drawn routes overlaid
- **Route Colors**: Orange (balanced), Green (stealth)
- **Risk Segments**: Blue (safe) → Red (critical)
- **Report**: Click sidebar report button to view analysis

### 4.4 Draw Mode (Route Evaluation)

#### Step 1: Draw Your Route
1. Switch to **Draw** mode
2. Click waypoints on the map to create your route
3. Drag waypoints to adjust positions
4. Route appears as dashed blue line

#### Step 2: Configure Squad
1. Expand **"Unit Composition"** panel
2. Set squad size (2-12)
3. Assign unit types: riflemen, snipers, support, medics

#### Step 3: Evaluate
1. Click **"Evaluate Route"**
2. AI analyzes route and suggests positions:
   - **Green circles**: Cover positions
   - **Yellow triangles**: Overwatch/sniper positions
   - **Orange squares**: Rally points
   - **Red X marks**: Danger zones
   - **White crosses**: Medic stations

### 4.5 Simulate Mode (Tactical Simulation)

#### Step 1: Place Enemies
1. Switch to **Simulate** mode
2. Select enemy type: Sniper, Rifleman, or Observer
3. Click map to place enemy
4. Vision cone appears based on enemy type and facing direction

#### Step 2: Rotate Enemies
- Click enemy marker → popup appears → click "Rotate +45°"
- Or drag the directional indicator

#### Step 3: Place Friendlies (Optional)
1. Select friendly type: Rifleman, Sniper, or Medic
2. Click map to place friendly unit

#### Step 4: Draw Movement Route
1. Click waypoints to draw the planned movement route
2. Segments are colored automatically:
   - **Amber**: In danger zone (before analysis)
   - **Green**: Clear of all vision cones

#### Step 5: Run Simulation
1. Click **"Run Simulation"**
2. AI analyzes each segment for actual cover status:
   - **Red**: Exposed (in cone, no cover)
   - **Amber**: Partial cover
   - **Green**: Covered (building/terrain blocks LOS)
   - **Blue**: Clear (outside all cones)

#### Step 6: View Report
Click **"View Report"** to see:
- Overall verdict and rating
- Tactical scores (radar chart)
- Cover breakdown (visual bar)
- Flanking analysis
- Weak spots with recommendations
- Movement timeline

### 4.6 Report Modal

The report modal has two tabs:

#### Current Analysis Tab
Shows the most recent analysis with:
- **Header**: Verdict badge + rating + quick stats
- **Tactical Scores**: Radar chart showing stealth/safety/terrain/flanking
- **Cover Breakdown**: Visual bar showing covered/exposed segments
- **Flanking Analysis**: Approach angle indicator
- **Annotated Map**: AI-marked satellite image
- **Weak Spots**: Risk locations with recommendations
- **Strong Points**: Good terrain usage locations
- **Recommendations**: Tactical advice

#### History Tab
- All previous analyses saved automatically
- Click entry to load that analysis
- Clear button to remove history

### 4.7 Map Controls

| Action | Method |
|--------|--------|
| Pan | Drag the map |
| Zoom | Scroll wheel or +/- buttons |
| Place unit | Click in placement mode |
| Move unit | Drag the marker |
| Rotate enemy | Click marker → Rotate button |
| Remove waypoint | Right-click or sidebar controls |
| Layer switch | Layer control (top-right) |

---

## 5. System Architecture

### 5.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENT BROWSER                              │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                     React + TypeScript UI                        │ │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌────────────────┐  │ │
│  │  │ Sidebar  │  │TacticalMap│ │  Report   │  │ PlanningLoader │  │ │
│  │  │ Controls │  │ (Leaflet) │ │   Modal   │  │  (Progress)    │  │ │
│  │  └──────────┘  └──────────┘  └───────────┘  └────────────────┘  │ │
│  │                      │                                            │ │
│  │              ┌───────▼───────┐                                    │ │
│  │              │   Zustand     │  Global state management           │ │
│  │              │   Store       │                                    │ │
│  │              └───────────────┘                                    │ │
│  │                      │                                            │ │
│  │              ┌───────▼───────┐                                    │ │
│  │              │   useApi.ts   │  HTTP + SSE handling               │ │
│  │              └───────────────┘                                    │ │
│  └─────────────────────│────────────────────────────────────────────┘ │
└─────────────────────────│────────────────────────────────────────────┘
                          │ HTTP / SSE
┌─────────────────────────▼────────────────────────────────────────────┐
│                        FastAPI Backend                                 │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                     API Layer (tactical.py)                       │  │
│  │  POST /api/plan-tactical-attack                                   │  │
│  │  POST /api/evaluate-route                                         │  │
│  │  POST /api/analyze-tactical-simulation                            │  │
│  │  GET  /api/progress/{request_id}  (SSE)                           │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │                                  │
│  ┌──────────────────────────────────▼───────────────────────────────┐  │
│  │              BalancedTacticalPipeline                             │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │  Stage 1: Acquire Imagery                                     │ │  │
│  │  │  - ESRI satellite tiles → stitched image                      │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │  Stage 2: AI Processing                                       │ │  │
│  │  │  - Gemini 3 Pro Image: Draw routes                            │ │  │
│  │  │  - Gemini 3 Flash: Analyze cover/flanking                     │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │  Stage 3: Score & Classify                                    │ │  │
│  │  │  - Multi-dimensional scoring                                  │ │  │
│  │  │  - Verdict determination                                      │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │  Stage 4: Return Response                                     │ │  │
│  │  │  - Annotated image + analysis JSON                            │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                          │
      ┌───────────────────┼───────────────────┐
      │                   │                   │
┌─────▼─────┐      ┌──────▼──────┐     ┌──────▼──────┐
│   ESRI    │      │   Google    │     │   Google    │
│  World    │      │   Gemini    │     │    Maps     │
│  Imagery  │      │   3 Pro/    │     │  Elevation  │
│   Tiles   │      │   Flash     │     │    API      │
└───────────┘      └─────────────┘     └─────────────┘
```

### 5.2 Request Flow

#### Route Generation Flow

```
User clicks "Plan Tactical Attack"
         │
         ▼
┌────────────────────────┐
│ Frontend: useApi.ts    │
│ - POST /api/plan...    │
│ - Start SSE listener   │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Backend: tactical.py   │
│ - Validate coordinates │
│ - Create request_id    │
│ - Start async pipeline │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Pipeline Stage 1:      │
│ - Calculate bounds     │
│ - Fetch ESRI tiles     │◄─── Progress: 5-20%
│ - Stitch into image    │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Pipeline Stage 2:      │
│ - Add start/end markers│
│ - Call Gemini 3 Pro    │◄─── Progress: 25-70%
│ - Get annotated image  │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Pipeline Stage 3:      │
│ - Route analysis       │
│ - Score calculation    │◄─── Progress: 75-85%
│ - Verdict assignment   │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Pipeline Stage 4:      │
│ - Build response JSON  │
│ - Optional: advanced   │◄─── Progress: 90-100%
│   tactical report      │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Frontend:              │
│ - Receive response     │
│ - Update Zustand store │
│ - Overlay image on map │
│ - Populate report      │
└────────────────────────┘
```

### 5.3 Data Flow

```
                    ┌─────────────────────────────────┐
                    │        User Input                │
                    │  - Unit positions                │
                    │  - Route waypoints               │
                    │  - Squad composition             │
                    └───────────────┬─────────────────┘
                                    │
                    ┌───────────────▼─────────────────┐
                    │      Request Validation          │
                    │  - Gulf region check             │
                    │  - Coordinate bounds             │
                    │  - Unit count validation         │
                    └───────────────┬─────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  ESRI Imagery   │     │   Gemini AI Models  │     │  Google Maps    │
│  - Tile fetch   │     │   - Image analysis  │     │  - Elevation    │
│  - Image stitch │     │   - Route drawing   │     │    data         │
└────────┬────────┘     │   - Cover analysis  │     └────────┬────────┘
         │              │   - Scoring         │              │
         │              └──────────┬──────────┘              │
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      Response Assembly       │
                    │  - Annotated image (base64)  │
                    │  - Analysis JSON             │
                    │  - Scores & verdicts         │
                    │  - Recommendations           │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      Frontend State          │
                    │  - Zustand store update      │
                    │  - Map overlay               │
                    │  - Report modal data         │
                    │  - History entry             │
                    └─────────────────────────────┘
```

---

## 6. API Reference

### 6.1 Health Check

**Endpoint:** `GET /api/health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-06T12:00:00Z"
}
```

### 6.2 Plan Tactical Attack

**Endpoint:** `POST /api/plan-tactical-attack`

**Request Body:**
```json
{
  "request_id": "optional-client-id",
  "soldiers": [
    {
      "lat": 24.7136,
      "lon": 46.6753,
      "is_friendly": true,
      "unit_id": "optional-unit-id"
    }
  ],
  "enemies": [
    {
      "lat": 24.7146,
      "lon": 46.6763,
      "is_friendly": false,
      "unit_id": "optional-unit-id"
    }
  ],
  "bounds": {
    "north": 24.716,
    "south": 24.712,
    "east": 46.678,
    "west": 46.674
  },
  "zoom": 17,
  "no_go_zones": null,
  "analysis_depth": "full",
  "advanced_analytics": false
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `request_id` | string | No | Client-provided ID for progress tracking |
| `soldiers` | array | Yes | List of friendly unit positions |
| `enemies` | array | Yes | List of enemy unit positions |
| `bounds` | object | Yes | Map bounds (north, south, east, west) |
| `zoom` | integer | No | Map zoom level (default: 14) |
| `no_go_zones` | array | No | Polygons to avoid (not implemented) |
| `analysis_depth` | string | No | "full" or "quick" |
| `advanced_analytics` | boolean | No | Enable detailed tactical report |

**Response:**
```json
{
  "request_id": "uuid-string",
  "timestamp": "2026-02-06T12:00:00Z",
  "soldiers_count": 1,
  "enemies_count": 1,
  "no_go_zones_count": 0,
  "routes": [
    {
      "route_id": 1,
      "name": "Balanced Approach",
      "description": "ORANGE route - Uses cover while maintaining reasonable speed.",
      "waypoints": [...],
      "segments": [...],
      "classification": {
        "gemini_evaluation": "risk",
        "gemini_reasoning": "...",
        "scores": {
          "time_to_target": 75,
          "stealth_score": 60,
          "survival_probability": 80,
          "overall_score": 72
        },
        "simulation": {
          "detected": false,
          "detection_probability": 0.35,
          "detection_points": [],
          "safe_percentage": 65
        },
        "final_verdict": "risk",
        "final_reasoning": "...",
        "confidence": 0.7
      },
      "total_distance_m": 450.5,
      "estimated_duration_seconds": 300,
      "elevation_gain_m": 0,
      "elevation_loss_m": 0
    }
  ],
  "recommended_route_id": 2,
  "mission_assessment": "1 of 2 routes viable. Proceed with caution.",
  "key_risks": [],
  "recommendations": [...],
  "tactical_analysis_report": null,
  "detection_debug": {
    "gemini_route_image": "base64-image-data",
    "gemini_route_bounds": {
      "north": 24.716,
      "south": 24.712,
      "east": 46.678,
      "west": 46.674
    }
  }
}
```

### 6.3 Evaluate User Route

**Endpoint:** `POST /api/evaluate-route`

**Request Body:**
```json
{
  "request_id": "optional-client-id",
  "waypoints": [
    { "lat": 24.7136, "lng": 46.6753 },
    { "lat": 24.7138, "lng": 46.6756 },
    { "lat": 24.7140, "lng": 46.6758 }
  ],
  "units": {
    "squad_size": 8,
    "riflemen": 4,
    "snipers": 2,
    "support": 1,
    "medics": 1
  },
  "bounds": {
    "north": 24.716,
    "south": 24.712,
    "east": 46.678,
    "west": 46.674
  }
}
```

**Response:**
```json
{
  "request_id": "uuid-string",
  "timestamp": "2026-02-06T12:00:00Z",
  "annotated_image": "base64-image-data",
  "annotated_image_bounds": {
    "north": 24.716,
    "south": 24.712,
    "east": 46.678,
    "west": 46.674
  },
  "positions": [
    {
      "position_type": "overwatch",
      "lat": 24.7138,
      "lng": 46.6755,
      "description": "Rooftop corner with view of approach",
      "for_unit": "sniper",
      "icon": "crosshair"
    }
  ],
  "segment_analysis": [
    {
      "segment_index": 0,
      "start_lat": 24.7136,
      "start_lng": 46.6753,
      "end_lat": 24.7138,
      "end_lng": 46.6756,
      "risk_level": "low",
      "description": "Good cover along building wall",
      "suggestions": ["Stay close to structure", "Move in pairs"]
    }
  ],
  "overall_assessment": "Route uses available cover effectively...",
  "route_distance_m": 125.5,
  "estimated_time_minutes": 1.8
}
```

### 6.4 Analyze Tactical Simulation

**Endpoint:** `POST /api/analyze-tactical-simulation`

**Request Body:**
```json
{
  "request_id": "optional-client-id",
  "enemies": [
    {
      "id": "enemy-1",
      "type": "sniper",
      "lat": 24.7146,
      "lng": 46.6763,
      "facing": 180
    },
    {
      "id": "enemy-2",
      "type": "rifleman",
      "lat": 24.7142,
      "lng": 46.6760,
      "facing": 270
    }
  ],
  "friendlies": [
    {
      "id": "friendly-1",
      "type": "rifleman",
      "lat": 24.7136,
      "lng": 46.6753
    }
  ],
  "route_waypoints": [
    { "lat": 24.7136, "lng": 46.6753 },
    { "lat": 24.7138, "lng": 46.6756 },
    { "lat": 24.7140, "lng": 46.6760 }
  ],
  "bounds": {
    "north": 24.716,
    "south": 24.712,
    "east": 46.678,
    "west": 46.674
  }
}
```

**Response:**
```json
{
  "request_id": "uuid-string",
  "timestamp": "2026-02-06T12:00:00Z",
  "annotated_image": "base64-image-data",
  "annotated_image_bounds": {...},
  "strategy_rating": 7.5,
  "verdict": "GOOD",
  "tactical_scores": {
    "stealth": 80,
    "safety": 75,
    "terrain_usage": 85,
    "flanking": 90,
    "overall": 82
  },
  "flanking_analysis": {
    "is_flanking": true,
    "approach_angle": 135,
    "bonus_awarded": 2.0,
    "description": "Strong flank - approaching from 135° off enemy facing. In enemy blind spot."
  },
  "segment_cover_analysis": [
    {
      "segment_index": 0,
      "in_vision_cone": false,
      "cover_status": "clear",
      "cover_type": null,
      "exposure_percentage": 0,
      "blocking_feature": null,
      "enemy_id": null,
      "explanation": "Segment outside all enemy vision cones"
    },
    {
      "segment_index": 1,
      "in_vision_cone": true,
      "cover_status": "covered",
      "cover_type": "building",
      "exposure_percentage": 0,
      "blocking_feature": "2-story concrete building",
      "enemy_id": "sniper_1",
      "explanation": "In sniper cone but building blocks line-of-sight completely"
    }
  ],
  "cover_breakdown": {
    "total_segments": 2,
    "exposed_count": 0,
    "covered_count": 1,
    "partial_count": 0,
    "clear_count": 1,
    "overall_cover_percentage": 100,
    "cover_types_used": ["building"]
  },
  "weak_spots": [
    {
      "location": "Segment 2 midpoint",
      "description": "Brief exposure when rounding corner",
      "severity": "medium",
      "recommendation": "Move quickly through this section"
    }
  ],
  "strong_points": [
    {
      "location": "Segments 1-2",
      "description": "Excellent use of building cover",
      "benefit": "Completely hidden from sniper"
    }
  ],
  "exposure_analysis": [],
  "terrain_assessment": "Urban terrain with 80% of approach behind hard cover",
  "overall_assessment": "Good tactical approach exploiting enemy blind spots and urban cover.",
  "recommendations": [
    "Maintain current flanking approach angle",
    "Move quickly through exposed section"
  ],
  "route_distance_m": 125.5,
  "estimated_time_minutes": 1.8
}
```

### 6.5 Progress Streaming (SSE)

**Endpoint:** `GET /api/progress/{request_id}`

**Response:** Server-Sent Events stream

**Event Format:**
```
event: progress
data: {"stage": "imagery", "progress": 15, "message": "Downloading satellite tiles..."}

event: progress
data: {"stage": "routes", "progress": 50, "message": "AI generating tactical routes..."}

event: progress
data: {"stage": "complete", "progress": 100, "message": "Tactical plan ready!"}
```

**Stages:**
1. `imagery` (0-25%): Fetching satellite imagery
2. `routes` or `analysis` (25-90%): AI processing
3. `report` (90-98%): Building tactical report
4. `complete` (100%): Done
5. `error`: Error occurred

---

## 7. Data Models

### 7.1 Unit Models

#### TacticalUnit (Backend)
```python
class TacticalUnit(BaseModel):
    lat: float          # Latitude position
    lon: float          # Longitude position
    is_friendly: bool   # True for friendly, False for enemy
    unit_id: str | None # Optional unique identifier
```

#### SimEnemyUnit (Backend)
```python
class SimEnemyUnit(BaseModel):
    id: str                                    # Unique identifier
    type: Literal["sniper", "rifleman", "observer"]
    lat: float
    lng: float
    facing: float  # 0-360 degrees, 0=North
```

### 7.2 Analysis Models

#### SegmentCoverAnalysis
```python
class SegmentCoverAnalysis(BaseModel):
    segment_index: int
    in_vision_cone: bool  # Geometrically in any enemy cone?
    cover_status: Literal["exposed", "covered", "partial", "clear"]
    cover_type: str | None  # "building", "vegetation", "terrain", "none"
    exposure_percentage: float  # 0-100
    blocking_feature: str | None  # What blocks LOS
    enemy_id: str | None  # Which enemy
    explanation: str  # Human-readable explanation
```

#### TacticalScores
```python
class TacticalScores(BaseModel):
    stealth: float       # 0-100: How hidden is the approach
    safety: float        # 0-100: Survival probability
    terrain_usage: float # 0-100: How well route uses cover
    flanking: float      # 0-100: Approach angle advantage
    overall: float       # 0-100: Weighted composite
```

#### FlankingAnalysis
```python
class FlankingAnalysis(BaseModel):
    is_flanking: bool      # Approaching from enemy blind spot?
    approach_angle: float  # 0-360 degrees from enemy facing
    bonus_awarded: float   # 0-3 rating points bonus
    description: str       # Explanation
```

#### CoverBreakdown
```python
class CoverBreakdown(BaseModel):
    total_segments: int
    exposed_count: int     # No cover, in cone
    covered_count: int     # Hard cover, in cone
    partial_count: int     # Partial cover
    clear_count: int       # Outside all cones
    overall_cover_percentage: float  # 0-100
    cover_types_used: list[str]
```

### 7.3 Response Models

See [API Reference](#6-api-reference) for complete response structures.

---

## 8. AI Prompts & Customization

### 8.1 Prompt Location

All AI prompts are in `georoute/config.yaml`:

| Prompt | Purpose |
|--------|---------|
| `route_prompt` | Instructions for Gemini to draw routes |
| `analysis_prompt` | Advanced tactical analysis |
| `route_evaluation_prompt` | User-drawn route analysis |
| `tactical_simulation_prompt` | Vision cone + cover analysis |

### 8.2 Route Drawing Prompt

Controls how Gemini draws routes on satellite imagery:

```yaml
route_prompt: |
  Edit this satellite image. Draw exactly 2 infantry foot patrol routes...

  DRAWING RULES:
  - Draw smooth, curved lines that follow natural walking paths
  - NEVER cross through buildings - always go AROUND them
  - Follow roads, sidewalks, alleys, and open ground
  ...
```

**Key customizable elements:**
- Number of routes
- Line colors (ORANGE, GREEN)
- Drawing style (curved vs angular)
- Obstacle avoidance rules

### 8.3 Tactical Simulation Prompt

Controls cover analysis and scoring:

```yaml
tactical_simulation_prompt: |
  Analyze this tactical scenario satellite image...

  CRITICAL ANALYSIS RULES:
  1. Buildings BLOCK enemy vision - routes BEHIND buildings are SAFE
  2. Trees/vegetation provide PARTIAL cover (50% concealment)
  3. Only mark as EXPOSED if in cone AND no obstacles blocking line-of-sight
  4. Approaching from enemy's BACK (>90° from facing) = FLANKING BONUS

  STRICT SCORING RULES:
  AUTOMATIC DEDUCTIONS:
  - ANY exposed segment in sniper cone: -2.0 points
  - ANY exposed segment in rifleman cone: -1.5 points
  ...
```

**Key customizable elements:**
- Cover detection rules
- Scoring deductions and bonuses
- Verdict thresholds
- JSON output format

### 8.4 Modifying Prompts

1. Edit `georoute/config.yaml`
2. Changes take effect on next API call (no restart needed)
3. Test with `docker compose logs -f georoute-backend`

**Tips:**
- Keep JSON output format consistent with backend models
- Test scoring changes with known scenarios
- Preserve required fields in JSON output

---

## 9. Frontend Architecture

### 9.1 Component Hierarchy

```
App.tsx
└── Index.tsx (Main page)
    ├── Sidebar.tsx
    │   ├── UnitPlacement.tsx
    │   ├── ActionButtons.tsx
    │   ├── SimulationControls.tsx
    │   ├── RouteDrawingControls.tsx
    │   ├── UnitCompositionPanel.tsx
    │   ├── TacticalRouteResults.tsx
    │   ├── EvaluationResults.tsx
    │   └── SimulationResults.tsx
    ├── TacticalMap.tsx
    │   └── ZoomIndicator.tsx
    ├── TacticalReportModal.tsx
    └── PlanningLoader.tsx
```

### 9.2 State Management (Zustand)

Global state is managed in `useMission.ts`:

```typescript
interface MissionState {
  // Mode
  mapMode: MapMode;  // 'idle' | 'place-soldier' | 'place-enemy' | 'draw-route' | ...

  // Units (Route mode)
  soldiers: TacticalUnit[];
  enemies: TacticalUnit[];

  // Routes
  tacticalRoutes: TacticalRoute[];
  planImages: Record<number, { image: string; bounds: Bounds }>;

  // Simulation state
  simEnemies: SimEnemy[];
  simFriendlies: SimFriendly[];
  drawnWaypoints: DrawnWaypoint[];
  simulationResult: TacticalSimulationResult | null;

  // History
  simulationHistory: SimulationHistoryEntry[];
  tacticalReportHistory: TacticalReportEntry[];

  // UI state
  isPlanning: boolean;
  reportModalOpen: boolean;

  // Actions
  addSoldier: (unit) => void;
  addSimEnemy: (lat, lng) => void;
  setSimulationResult: (result) => void;
  // ... many more
}
```

### 9.3 API Layer (useApi.ts)

HTTP and SSE handling:

```typescript
// POST with error handling
async function fetchWithError(url: string, options: RequestInit) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || error.message || `Request failed`);
  }
  return response;
}

// SSE progress streaming
function subscribeToProgress(requestId: string, onProgress: Function) {
  const eventSource = new EventSource(`${API_URL}/api/progress/${requestId}`);
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onProgress(data);
  };
  return () => eventSource.close();
}
```

### 9.4 Map Layer (TacticalMap.tsx)

Leaflet integration with layers:

| Layer | Purpose |
|-------|---------|
| `tileLayers.satellite` | ESRI World Imagery base |
| `unitMarkers` | Soldier/enemy markers |
| `simEnemyMarkers` | Simulation enemy markers |
| `simEnemyVisionCones` | Red vision cone polygons |
| `drawnRoutePolyline` | User-drawn route line |
| `planOverlays` | Gemini-generated route images |

---

## 10. Backend Architecture

### 10.1 Module Structure

```
georoute/
├── main.py                 # FastAPI app entry point
├── config.py               # Configuration loading
├── config.yaml             # All settings and prompts
├── api/
│   ├── routes.py           # Health check
│   └── tactical.py         # Main API endpoints
├── clients/
│   ├── esri_imagery.py     # Satellite tile fetching
│   ├── gemini_tactical.py  # Gemini AI client
│   └── google_maps.py      # Elevation API client
├── models/
│   └── tactical.py         # Pydantic data models
├── processing/
│   ├── balanced_tactical_pipeline.py      # Main orchestration
│   └── gemini_image_route_generator.py    # Route/analysis AI
└── utils/
    └── geo_validator.py    # Gulf region validation
```

### 10.2 Pipeline Classes

#### BalancedTacticalPipeline

Main orchestration class:

```python
class BalancedTacticalPipeline:
    def __init__(self, config):
        self.gmaps = GoogleMapsClient(config.google_maps_api_key)
        self.esri = ESRIImageryClient()
        self.gemini = TacticalGeminiClient(...)
        self.route_generator = GeminiImageRouteGenerator(...)

    async def plan_tactical_attack(self, request) -> TacticalPlanResponse:
        # 1. Validate coordinates
        # 2. Fetch satellite imagery
        # 3. Generate routes with Gemini
        # 4. Analyze and score
        # 5. Return response

    async def evaluate_user_route(self, request) -> RouteEvaluationResponse:
        # Similar flow for user-drawn routes

    async def analyze_tactical_simulation(self, request) -> TacticalSimulationResponse:
        # Draw vision cones, analyze cover, calculate flanking
```

#### GeminiImageRouteGenerator

Gemini AI interaction:

```python
class GeminiImageRouteGenerator:
    def __init__(self, api_key, use_vertex, project_id, location):
        # Initialize Gemini client (AI Studio or Vertex)

    async def generate_route(self, satellite_image_base64, ...) -> RouteResult:
        # Add markers, call Gemini 3 Pro Image, parse result

    async def analyze_tactical_simulation(self, annotated_image, prompt) -> dict:
        # Call Gemini 3 Flash for vision analysis
```

### 10.3 Error Handling

Errors are sanitized in `tactical.py`:

```python
def _sanitize_error(e: Exception) -> tuple[str, int]:
    """Convert exceptions to user-friendly messages with proper HTTP codes."""
    error_str = str(e).lower()

    if "resource_exhausted" in error_str or "quota" in error_str:
        return "AI service rate limit exceeded. Please wait and try again.", 429

    if "permission_denied" in error_str or "api key" in error_str:
        return "AI service authentication failed. Check API key.", 401

    if "model" in error_str and "not found" in error_str:
        return "AI model temporarily unavailable.", 503

    # ... more cases

    return "An error occurred during analysis.", 500
```

---

## 11. Troubleshooting

### 11.1 Common Issues

#### "Outside Gulf Region" Error
**Cause:** Coordinates are outside the GCC bounding box.
**Solution:** Ensure all coordinates are within:
- Latitude: 12°N to 32°N
- Longitude: 34°E to 60°E

#### "Zoom In Required" Popup
**Cause:** Map zoom level is below 17.
**Solution:** Zoom in to level 17 or higher before placing units.

#### No Routes Generated
**Causes:**
1. Invalid Gemini API key
2. Rate limit exceeded
3. Model unavailable

**Solutions:**
1. Check API key in `.env`
2. Wait 1-2 minutes and retry
3. Check `docker compose logs georoute-backend`

#### Blank/Missing Satellite Imagery
**Causes:**
1. ESRI service unavailable
2. Network timeout

**Solutions:**
1. Check internet connection
2. Retry after a few seconds
3. ESRI is generally very reliable

#### Container Won't Start
**Solutions:**
```bash
# Check logs
docker compose logs

# Rebuild from scratch
docker compose down
docker compose up --build
```

#### Port Already in Use
**Solution:** Change ports in `.env`:
```bash
BACKEND_PORT=8002
UI_PORT=8081
```

### 11.2 Log Analysis

```bash
# View all logs
docker compose logs -f

# Backend only
docker compose logs -f georoute-backend

# Frontend only
docker compose logs -f georoute-ui

# Search for errors
docker compose logs | grep -i error
```

### 11.3 Health Checks

```bash
# Check backend health
curl http://localhost:8001/api/health

# Check container status
docker compose ps

# Check resource usage
docker stats
```

---

## 12. Extending the System

### 12.1 Adding New Enemy Types

1. **Backend** (`models/tactical.py`):
```python
class SimEnemyType(str, Enum):
    SNIPER = "sniper"
    RIFLEMAN = "rifleman"
    OBSERVER = "observer"
    MACHINEGUNNER = "machinegunner"  # Add new type
```

2. **Backend** (`balanced_tactical_pipeline.py`):
```python
vision_specs = {
    'sniper': {'distance': 500, 'angle': 30},
    'rifleman': {'distance': 100, 'angle': 60},
    'observer': {'distance': 400, 'angle': 45},
    'machinegunner': {'distance': 300, 'angle': 90},  # Add specs
}
```

3. **Frontend** (`useMission.ts`):
```typescript
export const ENEMY_VISION_SPECS = {
  sniper: { distance: 500, angle: 30, color: '#ef4444' },
  rifleman: { distance: 100, angle: 60, color: '#ef4444' },
  observer: { distance: 400, angle: 45, color: '#ef4444' },
  machinegunner: { distance: 300, angle: 90, color: '#ef4444' },  // Add
};
```

4. **Frontend** (`TacticalMap.tsx`):
Add icon to `createSimEnemyIcon` function.

### 12.2 Adding New Scoring Metrics

1. **Backend** (`models/tactical.py`):
```python
class TacticalScores(BaseModel):
    stealth: float
    safety: float
    terrain_usage: float
    flanking: float
    speed: float  # Add new metric
    overall: float
```

2. **Backend** (`config.yaml`):
Update `tactical_simulation_prompt` to include new metric in JSON output.

3. **Frontend** (`useMission.ts`):
Update `TacticalScores` interface.

4. **Frontend** (`TacticalReportModal.tsx`):
Update `RadarChart` and `MiniGauge` components.

### 12.3 Adding New Analysis Modes

1. Create new endpoint in `tactical.py`
2. Add pipeline method in `balanced_tactical_pipeline.py`
3. Add request/response models in `models/tactical.py`
4. Create frontend components
5. Add state management in `useMission.ts`
6. Connect to sidebar controls

### 12.4 Changing AI Models

Edit `georoute/config.yaml`:
```yaml
gemini:
  image_model: "gemini-3-pro-image-preview"  # For drawing
  text_model: "gemini-2.5-flash"             # For text
  analysis_model: "gemini-3-flash-preview"   # For vision
```

No code changes required - models are loaded from config.

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Cover** | Physical obstruction that blocks line of sight |
| **Concealment** | Visual obstruction that hides but doesn't block fire |
| **Vision Cone** | Triangle representing enemy field of view |
| **Flanking** | Approaching from enemy's blind spot (>90° from facing) |
| **LOS** | Line of Sight |
| **SSE** | Server-Sent Events (real-time progress streaming) |
| **GCC** | Gulf Cooperation Council (regional restriction) |

## Appendix B: Keyboard Shortcuts

Currently, all interactions are mouse-based. No keyboard shortcuts are implemented.

## Appendix C: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 2026 | Initial release with route generation, evaluation, simulation |

---

*This manual is maintained alongside the GeoRoute codebase. For the latest version, see the repository.*
