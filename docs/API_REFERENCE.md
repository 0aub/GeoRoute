# GeoRoute Tactical Planning API Reference

Base URL: `http://localhost:9001`

---

## Tactical Planning Endpoints

### 1. Generate Tactical Attack Plan

**Endpoint**: `POST /api/plan-tactical-attack`

**Description**: Generates 3 tactical attack routes using 4-stage Gemini AI pipeline with multi-layer classification.

**Request Body**:
```json
{
  "soldiers": [
    {
      "lat": 36.1069,
      "lon": -112.1129,
      "unit_type": "rifleman",
      "is_friendly": true,
      "unit_id": "soldier-1"
    },
    {
      "lat": 36.1070,
      "lon": -112.1130,
      "unit_type": "sniper",
      "is_friendly": true,
      "unit_id": "soldier-2"
    }
  ],
  "enemies": [
    {
      "lat": 36.1089,
      "lon": -112.1149,
      "unit_type": "sentry",
      "is_friendly": false,
      "unit_id": "enemy-1"
    },
    {
      "lat": 36.1090,
      "lon": -112.1150,
      "unit_type": "patrol",
      "is_friendly": false,
      "unit_id": "enemy-2"
    }
  ],
  "bounds": {
    "north": 36.11,
    "south": 36.10,
    "east": -112.11,
    "west": -112.12
  },
  "zoom": 14
}
```

**Unit Types**:
- **Friendly**: `rifleman`, `sniper`, `heavy_weapons`, `medic`
- **Enemy**: `sentry`, `patrol`, `heavy_position`

**Response** (200 OK):
```json
{
  "request_id": "uuid-v4",
  "routes": [
    {
      "route_id": 1,
      "name": "Flanking Approach",
      "description": "Circle around enemy using forest cover",
      "waypoints": [
        {
          "lat": 36.1069,
          "lon": -112.1129,
          "elevation_m": 1500.0,
          "distance_from_start_m": 0.0,
          "terrain_type": "forest",
          "risk_level": "moderate",
          "reasoning": "200m from enemy patrol, partial tree cover",
          "tactical_note": "Good ambush position"
        }
      ],
      "segments": [
        {
          "segment_id": 0,
          "start_waypoint_idx": 0,
          "end_waypoint_idx": 1,
          "color": "yellow",
          "risk_level": "moderate",
          "distance_m": 150.0,
          "estimated_time_seconds": 100.0,
          "risk_factors": ["enemy patrol nearby"]
        }
      ],
      "classification": {
        "gemini_evaluation": "success",
        "gemini_reasoning": "High survival probability, good cover",
        "scores": {
          "time_to_target": 75.0,
          "stealth_score": 60.0,
          "survival_probability": 80.0,
          "overall_score": 70.0
        },
        "simulation": {
          "detected": false,
          "detection_probability": 0.15,
          "detection_points": [],
          "safe_percentage": 85.0
        },
        "final_verdict": "success",
        "final_reasoning": "Combined analysis shows success probability >70%",
        "confidence": 0.85
      },
      "total_distance_m": 1200.0,
      "estimated_duration_seconds": 800.0
    }
  ],
  "metadata": {
    "terrain_samples": 121,
    "zoom_level": 14,
    "has_satellite_image": true,
    "has_terrain_image": true
  }
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:9001/api/plan-tactical-attack \
  -H "Content-Type: application/json" \
  -d '{
    "soldiers": [
      {"lat": 36.1069, "lon": -112.1129, "unit_type": "rifleman", "is_friendly": true}
    ],
    "enemies": [
      {"lat": 36.1089, "lon": -112.1149, "unit_type": "sentry", "is_friendly": false}
    ],
    "bounds": {
      "north": 36.11,
      "south": 36.10,
      "east": -112.11,
      "west": -112.12
    },
    "zoom": 14
  }'
```

---

### 2. List Backlog Entries

**Endpoint**: `GET /api/backlog`

**Description**: List all tactical planning requests with pagination.

**Query Parameters**:
- `limit` (optional, default: 50, max: 100) - Number of entries to return
- `offset` (optional, default: 0) - Number of entries to skip
- `since` (optional) - ISO 8601 timestamp, only return entries after this time

**Response** (200 OK):
```json
{
  "entries": [
    {
      "request_id": "uuid",
      "timestamp": "2026-01-20T18:30:00Z",
      "user_input": { /* TacticalPlanRequest */ },
      "api_calls": [ /* APICall[] */ ],
      "gemini_pipeline": [ /* GeminiRequest[] - 4 stages */ ],
      "satellite_image": "base64_encoded_image",
      "terrain_image": "base64_encoded_image",
      "result": { /* TacticalPlanResponse */ },
      "total_duration_seconds": 5.5
    }
  ],
  "pagination": {
    "total": 100,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

**cURL Example**:
```bash
# Get first 10 entries
curl http://localhost:9001/api/backlog?limit=10&offset=0

# Get entries from last hour
curl "http://localhost:9001/api/backlog?since=2026-01-20T20:00:00Z"
```

---

### 3. Get Backlog Entry by ID

**Endpoint**: `GET /api/backlog/{request_id}`

**Description**: Get complete audit trail for a specific tactical planning request.

**Path Parameters**:
- `request_id` - UUID of the request

**Response** (200 OK):
```json
{
  "request_id": "uuid",
  "timestamp": "2026-01-20T18:30:00Z",
  "user_input": {
    "soldiers": [ /* TacticalUnit[] */ ],
    "enemies": [ /* TacticalUnit[] */ ],
    "bounds": { /* Bounds */ },
    "zoom": 14
  },
  "api_calls": [
    {
      "timestamp": "2026-01-20T18:30:01Z",
      "service": "google_maps",
      "endpoint": "elevation",
      "request_params": { "locations": [[36.1, -112.1]] },
      "response_data": { "elevations_count": 121 }
    }
  ],
  "gemini_pipeline": [
    {
      "timestamp": "2026-01-20T18:30:02Z",
      "stage": "stage1_initial_routes",
      "prompt": "Generate 3 tactical routes...",
      "response": "{\"routes\": [...]}",
      "image_included": true
    }
  ],
  "satellite_image": "base64_encoded_png",
  "terrain_image": "base64_encoded_png",
  "result": {
    "request_id": "uuid",
    "routes": [ /* 3 TacticalRoute objects */ ],
    "metadata": {}
  },
  "total_duration_seconds": 5.5
}
```

**cURL Example**:
```bash
curl http://localhost:9001/api/backlog/550e8400-e29b-41d4-a716-446655440000
```

---

### 4. Get Backlog Images

**Endpoint**: `GET /api/backlog/{request_id}/images`

**Description**: Get satellite and terrain images for a specific request.

**Path Parameters**:
- `request_id` - UUID of the request

**Response** (200 OK):
```json
{
  "satellite_image": "base64_encoded_png_data",
  "terrain_image": "base64_encoded_png_data"
}
```

**cURL Example**:
```bash
curl http://localhost:9001/api/backlog/550e8400-e29b-41d4-a716-446655440000/images
```

---

### 5. Clear Backlog

**Endpoint**: `DELETE /api/backlog`

**Description**: Clear all backlog entries (for testing/debugging).

**Response** (204 No Content)

**cURL Example**:
```bash
curl -X DELETE http://localhost:9001/api/backlog
```

---

## Legacy Endpoints

### Get Vehicles

**Endpoint**: `GET /api/vehicles`

**Description**: List available vehicle profiles.

**Response** (200 OK):
```json
[
  {
    "id": "mrap",
    "name": "MRAP",
    "type": "armored",
    "max_slope_degrees": 30.0,
    "max_altitude_m": 3000.0,
    "min_road_width_m": 3.5,
    "capabilities": ["armor", "mine_resistant"],
    "vulnerabilities": ["urban_ambush"]
  }
]
```

---

## Classification Criteria

### Route Verdicts

**SUCCESS**:
- `overall_score >= 70` AND `survival_probability >= 75`
- High confidence in mission success

**RISK**:
- `overall_score 40-69` OR `survival_probability 50-74`
- Moderate risk, mission possible but casualties likely

**FAILED**:
- `overall_score < 40` OR `survival_probability < 50`
- High risk of failure or heavy casualties

### Risk Levels → Colors

- **safe** → 🟦 **blue**: >500m from enemies, good cover
- **moderate** → 🟨 **yellow**: 200-500m from enemies, some cover
- **high** → 🟧 **orange**: 100-200m from enemies, exposed terrain
- **critical** → 🟥 **red**: <100m from enemies, open terrain

### Score Calculation

**Overall Score** = `time_to_target * 0.2 + stealth_score * 0.4 + survival_probability * 0.4`

- **time_to_target** (0-100): Route speed/efficiency
- **stealth_score** (0-100): Concealment and detection avoidance
- **survival_probability** (0-100): Expected survival rate

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request format or validation error"
}
```

### 404 Not Found
```json
{
  "detail": "Backlog entry not found: {request_id}"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Tactical planning failed: {error_message}"
}
```

---

## Testing the API

### 1. Health Check
```bash
curl http://localhost:9001/api/vehicles
```

### 2. Generate Tactical Plan
```bash
curl -X POST http://localhost:9001/api/plan-tactical-attack \
  -H "Content-Type: application/json" \
  -d @example_request.json
```

Where `example_request.json`:
```json
{
  "soldiers": [
    {"lat": 36.1069, "lon": -112.1129, "unit_type": "rifleman", "is_friendly": true},
    {"lat": 36.1070, "lon": -112.1130, "unit_type": "sniper", "is_friendly": true}
  ],
  "enemies": [
    {"lat": 36.1089, "lon": -112.1149, "unit_type": "sentry", "is_friendly": false}
  ],
  "bounds": {"north": 36.11, "south": 36.10, "east": -112.11, "west": -112.12},
  "zoom": 14
}
```

### 3. View Backlog
```bash
curl http://localhost:9001/api/backlog?limit=5
```

### 4. Get Specific Entry
```bash
# First, get a request_id from the backlog
curl http://localhost:9001/api/backlog | jq -r '.entries[0].request_id'

# Then fetch that entry
curl http://localhost:9001/api/backlog/{request_id}
```

---

## Example Coordinates (2km x 2km tactical areas)

### Grand Canyon Area
```json
{
  "soldiers": [{"lat": 36.1069, "lon": -112.1129, "unit_type": "rifleman", "is_friendly": true}],
  "enemies": [{"lat": 36.1089, "lon": -112.1149, "unit_type": "sentry", "is_friendly": false}],
  "bounds": {"north": 36.119, "south": 36.101, "east": -112.101, "west": -112.119}
}
```

### Urban Area (Example)
```json
{
  "soldiers": [{"lat": 40.7128, "lon": -74.0060, "unit_type": "rifleman", "is_friendly": true}],
  "enemies": [{"lat": 40.7148, "lon": -74.0080, "unit_type": "sentry", "is_friendly": false}],
  "bounds": {"north": 40.722, "south": 40.704, "east": -73.997, "west": -74.015}
}
```

---

## Rate Limits

- No rate limits currently enforced
- Each tactical planning request takes ~5-10 seconds
- Backlog stores up to 100 entries (oldest automatically removed)

---

## Notes

- All coordinates use WGS84 (lat/lon in decimal degrees)
- Images are base64-encoded PNG format
- Timestamps are ISO 8601 UTC
- Request IDs are UUIDv4
- Recommended zoom level: 11-15 for tactical planning
- Tactical area size: ~2km x 2km (0.018° x 0.018°)
