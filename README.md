# GeoRoute - Military Tactical Route Planning

GPU-accelerated tactical route planning system using SAM (Segment Anything Model) for obstacle detection and A* pathfinding for optimal route generation.

## Features

- **SAM-Based Obstacle Detection**: Pixel-accurate building detection using Meta's Segment Anything Model
- **GPU Acceleration**: CUDA-enabled inference for 1-2 second detection times
- **A* Pathfinding**: High-resolution grid pathfinding avoiding obstacles
- **Tactical Analysis**: AI-powered risk assessment via Gemini
- **Real-time Visualization**: Interactive React UI with Leaflet maps
- **Gulf Region Optimized**: Configured for GCC countries with appropriate terrain data

## Architecture

```
Satellite Imagery → SAM Detection → Obstacle Grid → A* Pathfinding → Tactical Routes
                                                    ↓
                                          Gemini Risk Analysis
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- NVIDIA GPU with 8GB+ VRAM (recommended)
- API Keys:
  - Google Maps API (satellite imagery)
  - Gemini API (tactical analysis)

### Setup

1. **Clone and configure**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Build and run**:
   ```bash
   docker compose up --build
   ```

3. **Access**:
   - UI: http://localhost:8080
   - API: http://localhost:9001

## Configuration

Edit `georoute/config.yaml`:

```yaml
# SAM Configuration
sam:
  model_type: "vit_h"  # vit_h (best), vit_l, or vit_b (fastest)
  device: "cuda"       # cuda or cpu
  min_area: 100        # Minimum pixel area for buildings

# Obstacle Detection Method
obstacle_detection:
  method: "sam"  # "sam" (GPU) or "gemini" (API fallback)
```

## Project Structure

```
GeoRoute/
├── georoute/              # Backend (FastAPI)
│   ├── api/              # API endpoints
│   ├── clients/          # External service clients
│   ├── models/           # Pydantic models
│   ├── processing/       # Core algorithms
│   │   ├── sam_obstacle_detector.py      # SAM detection
│   │   ├── balanced_tactical_pipeline.py # Main pipeline
│   │   └── grid_pathfinder.py           # A* pathfinding
│   └── config.yaml       # Configuration
├── ui/                   # Frontend (React + TypeScript)
│   └── src/
│       ├── components/   # React components
│       ├── pages/        # Page components
│       └── types/        # TypeScript types
├── docs/                 # Documentation
├── tests/                # Test scripts
└── assets/               # Images and logos
```

## SAM vs Gemini Vision

| Feature | SAM (GPU) | Gemini Vision |
|---------|-----------|---------------|
| Accuracy | 75-85% IoU | ~68% |
| Precision | Pixel-level | 1000×1000 grid (~1m) |
| Speed | 1-2 seconds | 2-5 seconds |
| Rate Limits | None | 5/min, 25/day |
| Requirements | GPU (4GB+) | API key |

## Development

### Hot Reload
Code changes are automatically reflected (no rebuild needed):
- Backend: `georoute/` mounted as volume
- Frontend: `ui/src/` mounted as volume

### Testing
```bash
cd tests
./test_routes_api.sh  # API integration tests
```

### GPU Check
```bash
docker exec georoute-backend nvidia-smi
```

## API Endpoints

### POST `/api/plan-tactical-attack`
Plan tactical approach routes with obstacle avoidance.

**Request**:
```json
{
  "soldiers": [{"lat": 25.0, "lon": 55.0}],
  "enemies": [{"lat": 25.01, "lon": 55.01}],
  "bounds": {"north": 25.02, "south": 24.98, "east": 55.02, "west": 54.98},
  "zoom": 17
}
```

**Response**: Multiple tactical routes with risk scores, waypoints, and AI analysis.

## Documentation

- [SAM Research & Approach](docs/new%20research.md)
- [Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)
- [API Reference](docs/API_REFERENCE.md)
- [Routing Investigation](docs/ROUTING_INVESTIGATION.md)

## Troubleshooting

**Build Issues**:
- Slow downloads: Using PyTorch base image (pre-built)
- GPU not detected: Check `docker compose logs` and NVIDIA runtime

**SAM Errors**:
- Falls back to Gemini Vision automatically
- Check logs: `docker logs georoute-backend`

**Out of Memory**:
- Reduce `sam.model_type` from `vit_h` to `vit_b` in config.yaml
- Or set `sam.device: "cpu"` (slower but no GPU required)

## License

See [LICENSE](LICENSE) for details.

## Credits

- **SAM**: Meta AI - [Segment Anything](https://github.com/facebookresearch/segment-anything)
- **segment-geospatial**: Geospatial wrapper for SAM
- **FastAPI**: Modern Python web framework
- **React + Leaflet**: Interactive mapping UI
