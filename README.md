<p align="center">
  <img src="assets/logo.svg" alt="GeoRoute" height="80" />
</p>

<h1 align="center">GeoRoute</h1>

<p align="center">
  <strong>AI-Powered Tactical Route Planning System</strong><br>
  <em>Version 2.0</em>
</p>

<p align="center">
  <a href="#features">Features</a> &bull;
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#usage">Usage</a> &bull;
  <a href="#architecture">Architecture</a> &bull;
  <a href="#api-reference">API Reference</a> &bull;
  <a href="#configuration">Configuration</a> &bull;
  <a href="docs/MANUAL.md">Full Manual</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0-blue" alt="Version 2.0" />
  <img src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/react-18-61dafb?logo=react&logoColor=white" alt="React" />
  <img src="https://img.shields.io/badge/gemini-3_Pro-4285F4?logo=google&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/nginx-reverse_proxy-009639?logo=nginx&logoColor=white" alt="nginx" />
</p>

---

GeoRoute is a tactical route planning system that uses Google's Gemini AI to generate, evaluate, and simulate infantry movement routes on satellite imagery. It draws routes directly on real-world satellite maps, performs cover analysis against enemy positions, and produces detailed tactical reports with scoring and recommendations.

## What's New in Version 2.0

- **NGINX Reverse Proxy** -- Production-ready with rate limiting, compression, and security headers
- **Vertex AI Support** -- Higher quotas and reliability for production workloads
- **Load Balancing** -- Scale backend replicas for concurrent users
- **Unified Configuration** -- Single docker-compose.yml for all environments
- **Error Sanitization** -- User-friendly error messages without exposing internals

## Features

### Route Generation
- **AI-Drawn Routes** -- Gemini 3 Pro draws 2 tactical routes directly on satellite imagery (primary + stealth)
- **Obstacle Avoidance** -- Routes curve around buildings, follow walls, and use natural cover
- **Multi-Layer Scoring** -- Each route is scored on time-to-target, stealth, and survival probability
- **Color-Coded Risk** -- Route segments are colored blue (safe) through red (critical) based on threat proximity

### Tactical Simulation
- **Enemy Vision Cones** -- Place enemies (sniper, rifleman, observer) with realistic fields of view
- **Cover Analysis** -- AI analyzes each route segment for cover status: exposed, covered, partial, or clear
- **Flanking Detection** -- Mathematical calculation of approach angle relative to enemy facing direction
- **Strategy Scoring** -- Multi-dimensional scores (stealth, safety, terrain usage, flanking) with verdict system

### Route Evaluation
- **Draw Your Own Route** -- Click waypoints on the map to plan custom movement paths
- **AI Position Suggestions** -- Gemini recommends overwatch, cover, rally, danger, and medic positions
- **Squad Composition** -- Configure riflemen, snipers, support gunners, and medics for tailored analysis
- **Segment Risk Analysis** -- Each segment assessed for risk level with specific suggestions

### Interactive Map
- **ESRI Satellite Imagery** -- High-resolution satellite base map
- **Drag-and-Drop Units** -- Place and reposition soldiers and enemies by clicking or dragging
- **NATO APP-6 Symbols** -- Military-standard unit markers
- **Gulf Region Optimized** -- Pre-configured for GCC countries (Saudi Arabia, UAE, Kuwait, Bahrain, Qatar, Oman)

### Reports & History
- **Comprehensive Reports** -- Verdict badge, radar scores, cover breakdown, flanking analysis, weak spots, recommendations
- **Report History** -- All analyses saved and accessible from the history tab
- **Real-Time Progress** -- Server-Sent Events stream stage updates during analysis

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- API Keys:
  - [Google Maps API](https://console.cloud.google.com/apis/credentials) (Elevation API, Static API)
  - [Vertex AI](https://console.cloud.google.com/vertex-ai) (recommended) or [Gemini API](https://aistudio.google.com/app/apikey)

### Setup

```bash
git clone https://github.com/0aub/GeoRoute.git
cd GeoRoute

cp .env.example .env
# Edit .env with your API keys
```

### Run

```bash
docker compose up -d --build
```

### Access

| Service | URL |
|---------|-----|
| **Application** | http://localhost |
| **API Health** | http://localhost/api/health |

> Access via **port 80** (nginx). Direct service ports (9001, 8080) are for development only.

---

## Production Deployment

### Vertex AI Setup (Recommended)

Vertex AI provides higher quotas and better reliability for production:

1. Enable Vertex AI API in [Google Cloud Console](https://console.cloud.google.com/vertex-ai)
2. Create a service account with `roles/aiplatform.user` permission
3. Download JSON key and save as `service-account.json` in project root
4. Configure `.env`:

```bash
USE_VERTEX_AI=true
VERTEX_LOCATION=us-central1
GOOGLE_CLOUD_PROJECT=your-project-id
```

### Load Balancing

Scale backend replicas for concurrent users:

```bash
# Scale to 3 backend instances
docker compose up -d --scale georoute-backend=3
```

NGINX automatically load balances using least-connections algorithm.

### Server Deployment

```bash
# On your server
git clone https://github.com/0aub/GeoRoute.git
cd GeoRoute

cp .env.example .env
# Edit .env with your settings

# Copy service account credentials
scp service-account.json user@server:~/GeoRoute/

# Start with nginx (port 80)
docker compose up -d --build
```

Update `.env` for your domain:
```bash
NGINX_PORT=80
CORS_ORIGINS=http://your-domain.com
```

---

## Usage

### 1. AI Route Generation

1. Click the map to place a **soldier** (blue) and an **enemy** (red)
2. Click **Plan Tactical Attack**
3. View generated routes with risk-colored segments, scores, and tactical analysis

### 2. Manual Route Evaluation

1. Switch to **Draw** mode
2. Click waypoints on the map to draw your planned route
3. Configure your squad composition (riflemen, snipers, support, medics)
4. Click **Evaluate Route**
5. View AI-suggested tactical positions and segment-by-segment risk analysis

### 3. Tactical Simulation

1. Switch to **Simulate** mode
2. Place **enemies** with type (sniper/rifleman/observer) and facing direction
3. Place **friendly** units
4. Draw your movement route
5. Click **Run Simulation**
6. View vision cone analysis, cover status per segment, flanking bonus, and overall verdict

### Map Controls

| Action | How |
|--------|-----|
| Place unit | Select mode in sidebar, then click map |
| Move unit | Drag the marker |
| Remove unit | Right-click or use sidebar controls |
| Draw route | Select draw mode, click waypoints |
| Zoom requirement | Zoom level 17+ required for unit placement |

---

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │            NGINX (Port 80)           │
                    │   Rate Limiting • Compression • SSL  │
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │  Backend API #1   │  │  Backend API #2   │  │  Backend API #N   │
   │   (FastAPI)       │  │   (FastAPI)       │  │   (Scaled)        │
   └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
            │                     │                     │
            └─────────────────────┼─────────────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
            ▼                     ▼                     ▼
   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
   │   Gemini AI   │      │     ESRI      │      │ Google Maps  │
   │  (Vertex AI)  │      │   Imagery     │      │  Elevation   │
   └──────────────┘      └──────────────┘      └──────────────┘
```

**Pipeline Flow:**

1. **Acquire Imagery** -- Fetch satellite tiles from ESRI and stitch into a single image
2. **Generate/Annotate** -- Gemini draws routes or analyzes user-drawn routes on the image
3. **Score & Classify** -- Multi-layer evaluation: risk scores, detection simulation, final verdict
4. **Report** -- Structured JSON response with tactical analysis and annotated image

### AI Models Used

| Model | Purpose |
|-------|---------|
| `gemini-3-pro-image-preview` | Drawing routes on satellite images |
| `gemini-2.5-flash` | Text-based analysis and scoring |
| `gemini-3-flash-preview` | Vision-based tactical analysis (simulation & evaluation) |

---

## API Reference

All endpoints are accessed through **http://localhost/api/...**

### POST `/api/plan-tactical-attack`

Generate tactical routes between soldier and enemy positions.

**Request:**
```json
{
  "soldiers": [{ "lat": 24.7136, "lon": 46.6753 }],
  "enemies": [{ "lat": 24.7146, "lon": 46.6763 }],
  "bounds": { "north": 24.716, "south": 24.712, "east": 46.678, "west": 46.674 },
  "zoom": 17,
  "advanced_analytics": false
}
```

**Response:** Routes with waypoints, risk-colored segments, scores, and optional AI tactical report.

### POST `/api/evaluate-route`

Evaluate a user-drawn route and suggest tactical positions.

**Request:**
```json
{
  "waypoints": [
    { "lat": 24.7136, "lng": 46.6753 },
    { "lat": 24.7140, "lng": 46.6758 }
  ],
  "unit_composition": { "squad_size": 8, "riflemen": 4, "snipers": 2, "support": 1, "medics": 1 },
  "bounds": { "north": 24.716, "south": 24.712, "east": 46.678, "west": 46.674 },
  "zoom": 17
}
```

**Response:** Annotated image, suggested positions (overwatch, cover, rally, danger, medic), and segment risk analysis.

### POST `/api/analyze-tactical-simulation`

Analyze a tactical scenario with enemy vision cones and cover.

**Request:**
```json
{
  "enemies": [
    { "lat": 24.7146, "lng": 46.6763, "type": "sniper", "facing": 180 }
  ],
  "friendlies": [
    { "lat": 24.7136, "lng": 46.6753, "type": "rifleman" }
  ],
  "route_waypoints": [
    { "lat": 24.7136, "lng": 46.6753 },
    { "lat": 24.7140, "lng": 46.6758 }
  ],
  "bounds": { "north": 24.716, "south": 24.712, "east": 46.678, "west": 46.674 },
  "zoom": 17
}
```

**Response:**
```json
{
  "annotated_image": "base64...",
  "strategy_rating": 7.5,
  "verdict": "GOOD",
  "tactical_scores": { "stealth": 80, "safety": 75, "terrain_usage": 85, "flanking": 90, "overall": 82 },
  "flanking_analysis": { "is_flanking": true, "approach_angle": 135, "bonus_awarded": 2.0, "description": "..." },
  "segment_cover_analysis": [...],
  "cover_breakdown": { "total_segments": 5, "exposed_count": 1, "covered_count": 3, "partial_count": 1, "clear_count": 0, "overall_cover_percentage": 80 },
  "weak_spots": [...],
  "strong_points": [...],
  "recommendations": [...]
}
```

### GET `/api/progress/{request_id}`

Server-Sent Events stream for real-time progress during analysis.

**Event format:**
```json
{ "stage": "imagery", "progress": 25, "message": "Acquiring satellite imagery..." }
```

Stages: `imagery` -> `routes`/`analysis` -> `report` -> `complete`

### GET `/api/health`

Health check endpoint.

---

## Configuration

### Environment Variables (`.env`)

```bash
# =============================================================================
# SERVER CONFIGURATION
# =============================================================================
NGINX_PORT=80              # Main entry point (nginx)
BACKEND_PORT=9001          # Backend API (internal)
UI_PORT=8080               # Frontend (internal)
CORS_ORIGINS=http://localhost
VITE_API_URL=              # Leave empty for nginx proxy mode

# =============================================================================
# GOOGLE CLOUD (REQUIRED)
# =============================================================================
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# =============================================================================
# AI SERVICE - Vertex AI (Recommended)
# =============================================================================
USE_VERTEX_AI=true
VERTEX_LOCATION=us-central1
# Requires service-account.json in project root

# =============================================================================
# AI SERVICE - Alternative: AI Studio
# =============================================================================
# USE_VERTEX_AI=false
# GEMINI_API_KEY=your-gemini-api-key
```

### NGINX Configuration

NGINX provides:
- **Rate Limiting**: 10 req/s per IP for API, 30 req/s for general
- **Load Balancing**: Least-connections algorithm across backend replicas
- **Compression**: Gzip for text, JSON, JavaScript, CSS
- **Timeouts**: 3 minutes for AI operations, 24 hours for SSE
- **Security Headers**: X-Frame-Options, X-Content-Type-Options, etc.

Configuration file: `nginx/nginx.conf`

### Application Config (`georoute/config.yaml`)

```yaml
# Route generation method and count
route_generation:
  method: "gemini_image"
  num_routes: 2

# AI model selection
gemini:
  image_model: "gemini-3-pro-image-preview"
  text_model: "gemini-2.5-flash"
  analysis_model: "gemini-3-flash-preview"

# Map marker appearance
markers:
  size: 6
  start_color: [0, 100, 255]  # Blue
  end_color: [255, 50, 50]    # Red

# Geographic restriction (GCC bounding box)
geo:
  gcc_bounds:
    north: 32.0
    south: 12.0
    east: 60.0
    west: 34.0
```

The config file also contains fully customizable AI prompts for route generation, tactical analysis, route evaluation, and tactical simulation.

### Enemy Vision Specs

| Type | Range | Angle | Threat Level |
|------|-------|-------|--------------|
| Sniper | 500m | 30° | High -- long-range precision |
| Rifleman | 100m | 60° | Medium -- close-range, wider field |
| Observer | 400m | 45° | Medium -- alerts other enemies |

### Verdict Scoring

| Verdict | Rating | Criteria |
|---------|--------|----------|
| EXCELLENT | 8.5 - 10 | 90%+ covered, rear flanking, zero exposed segments |
| GOOD | 6.5 - 8.4 | 75%+ covered, good flanking, max 1 exposed segment |
| ACCEPTABLE | 4.5 - 6.4 | 50-75% covered, some tactical thought |
| RISKY | 0 - 4.4 | <50% covered or critical exposure or frontal approach |

---

## Project Structure

```
GeoRoute/
├── georoute/                          # Backend (FastAPI + Python)
│   ├── api/
│   │   ├── routes.py                  # Health check endpoint
│   │   └── tactical.py                # Plan, evaluate, simulate endpoints
│   ├── clients/
│   │   ├── esri_imagery.py            # Satellite tile fetching
│   │   ├── gemini_tactical.py         # Gemini AI pipeline
│   │   └── google_maps.py             # Elevation API
│   ├── models/
│   │   └── tactical.py                # Pydantic request/response models
│   ├── processing/
│   │   ├── balanced_tactical_pipeline.py   # Main orchestration pipeline
│   │   └── gemini_image_route_generator.py # Route drawing & analysis
│   ├── utils/
│   │   └── geo_validator.py           # Gulf region coordinate validation
│   ├── config.py                      # Config loader
│   ├── config.yaml                    # All prompts, models, settings
│   ├── main.py                        # App entry point
│   ├── Dockerfile
│   └── requirements.txt
│
├── ui/                                # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── components/
│   │   │   ├── map/
│   │   │   │   ├── TacticalMap.tsx     # Leaflet map with all overlays
│   │   │   │   └── ZoomIndicator.tsx
│   │   │   ├── sidebar/
│   │   │   │   ├── Sidebar.tsx         # Main sidebar with mode tabs
│   │   │   │   └── ...                 # Unit, action, and control components
│   │   │   ├── tactical/
│   │   │   │   ├── TacticalReportModal.tsx  # Report viewer + history
│   │   │   │   └── PlanningLoader.tsx       # Progress overlay
│   │   │   └── ui/                    # shadcn/ui component library
│   │   ├── hooks/
│   │   │   ├── useMission.ts          # Zustand global state store
│   │   │   └── useApi.ts             # API calls + SSE progress
│   │   ├── pages/
│   │   │   └── Index.tsx              # Main application page
│   │   └── types/
│   │       └── index.ts              # TypeScript type definitions
│   └── Dockerfile
│
├── nginx/
│   └── nginx.conf                     # Reverse proxy configuration
│
├── docs/
│   ├── MANUAL.md                      # Comprehensive user manual
│   └── MANUAL.tex                     # LaTeX version with TikZ diagrams
│
├── docker-compose.yml                 # Unified configuration (nginx + services)
├── .env.example                       # Environment template
└── service-account.json               # Vertex AI credentials (not in repo)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Reverse Proxy** | NGINX (Alpine) with rate limiting and load balancing |
| **Backend** | FastAPI, Python 3.11, Pydantic, Uvicorn |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS |
| **State** | Zustand (client), TanStack Query (server) |
| **Maps** | Leaflet + React-Leaflet, ESRI World Imagery |
| **UI Components** | shadcn/ui (Radix UI primitives) |
| **AI** | Google Gemini 3 Pro (Vertex AI), Gemini 3 Flash, Gemini 2.5 Flash |
| **Image Processing** | Pillow (Python) |
| **Containers** | Docker Compose (Python 3.11-slim + Node 20-Alpine + NGINX Alpine) |

---

## Development

### Hot Reload

Both services support hot reload without rebuilding containers:

- **Backend**: `georoute/` is mounted as a read-only volume. Set `RELOAD=true` in `.env`.
- **Frontend**: `ui/src/` is mounted directly. Vite HMR reflects changes instantly.

### Running Tests

```bash
# Backend integration tests
cd tests && ./test_routes_api.sh

# Frontend tests
cd ui && npm test
```

### Logs

```bash
# All services
docker compose logs -f

# Backend only (all replicas)
docker compose logs -f georoute-backend

# Specific replica
docker logs -f georoute-georoute-backend-1

# NGINX access logs
docker compose logs -f nginx
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Outside Gulf Region" error | System is restricted to GCC countries. Ensure coordinates are within bounds. |
| "Zoom In Required" popup | Zoom to level 17+ before placing units. |
| No routes generated | Check Gemini/Vertex AI credentials. Check backend logs. |
| Backend disconnected | Access via **http://localhost** (nginx), not port 9000. |
| Container won't start | Run `docker compose logs` to see error details. |
| Rate limit exceeded | Wait 60 seconds, or request higher Vertex AI quota. |
| Port 80 in use | Change `NGINX_PORT` in `.env`. |

---

## Documentation

For comprehensive documentation, see the **[Project Manual](docs/MANUAL.md)** which covers:

- Complete installation and Vertex AI setup
- NGINX configuration and load balancing
- Detailed user guide for all modes
- Full API reference with all fields
- System architecture deep-dive
- AI prompt customization
- Extending the system with new features

---

*Copyright (c) 2026 - Proprietary Software*
