# User-Drawn Route Evaluation - Implementation Plan

## Overview

Add a new mode where users draw their own route on the map, select unit composition, and receive AI-powered tactical evaluation with suggested positions.

---

## User Flow

```
1. User toggles to "Manual Route" mode
2. User clicks on map to draw polyline waypoints
3. User can edit/delete waypoints
4. User opens Unit Panel and selects:
   - Squad size
   - Unit types (riflemen, snipers, support, medic)
5. User clicks "Evaluate Route"
6. Backend:
   - Fetches satellite image with user's route drawn on it
   - Sends to Gemini for tactical analysis
   - Gemini returns annotated image + analysis JSON
7. Frontend displays:
   - Annotated satellite image overlay
   - Suggested positions as map markers
   - Text analysis in sidebar panel
```

---

## Phase 1: Frontend - Route Drawing

### 1.1 New State in useMission.ts

```typescript
// New state fields
interface MissionState {
  // ... existing fields ...

  // Route Drawing Mode
  routeMode: 'ai-generate' | 'manual-draw'

  // User-drawn route waypoints
  drawnWaypoints: Array<{ lat: number; lng: number }>

  // Unit composition
  unitComposition: {
    squadSize: number
    riflemen: number
    snipers: number
    support: number
    medics: number
  }

  // Evaluation results
  routeEvaluation: RouteEvaluationResult | null
  isEvaluating: boolean
}

// New actions
setRouteMode: (mode: 'ai-generate' | 'manual-draw') => void
addDrawnWaypoint: (lat: number, lng: number) => void
updateDrawnWaypoint: (index: number, lat: number, lng: number) => void
removeDrawnWaypoint: (index: number) => void
clearDrawnWaypoints: () => void
setUnitComposition: (units: UnitComposition) => void
setRouteEvaluation: (result: RouteEvaluationResult) => void
```

### 1.2 New Component: RouteDrawingControls.tsx

Location: `ui/src/components/sidebar/RouteDrawingControls.tsx`

```tsx
// Mode toggle (AI Generate vs Manual Draw)
// When in manual mode:
// - Instructions text
// - Waypoint count display
// - Undo last point button
// - Clear all button
```

### 1.3 New Component: UnitCompositionPanel.tsx

Location: `ui/src/components/sidebar/UnitCompositionPanel.tsx`

```tsx
// Squad size slider (2-12)
// Unit type selectors with icons:
// - Riflemen (rifle icon)
// - Snipers (crosshair icon)
// - Support/MG (shield icon)
// - Medics (plus icon)
// Total must not exceed squad size
```

### 1.4 Update TacticalMap.tsx

```tsx
// Add drawing layer (Leaflet.draw or custom)
// When routeMode === 'manual-draw':
// - Click adds waypoint marker
// - Connect waypoints with polyline
// - Waypoint markers are draggable
// - Right-click on marker to delete

// Waypoint marker style:
// - Small circle (6px radius)
// - White fill, dark border
// - Index number in center

// Route line style:
// - Dashed line
// - 3px width
// - User's chosen color or default blue
```

### 1.5 Update Sidebar.tsx

Add new sections:
1. Route Mode Toggle (above Unit Placement)
2. Unit Composition Panel (when manual mode + waypoints exist)
3. "Evaluate Route" button (replaces "Plan Attack" in manual mode)

---

## Phase 2: Backend - Evaluation Endpoint

### 2.1 New Models in models/tactical.py

```python
class UnitComposition(BaseModel):
    squad_size: int = Field(ge=2, le=12)
    riflemen: int = Field(ge=0)
    snipers: int = Field(ge=0)
    support: int = Field(ge=0)
    medics: int = Field(ge=0)

class RouteWaypoint(BaseModel):
    lat: float
    lng: float

class RouteEvaluationRequest(BaseModel):
    request_id: Optional[str] = None
    waypoints: List[RouteWaypoint]
    start_point: RouteWaypoint  # First waypoint
    end_point: RouteWaypoint    # Last waypoint
    units: UnitComposition
    bounds: dict

class SuggestedPosition(BaseModel):
    position_type: str  # 'overwatch', 'cover', 'rally', 'danger', 'medic'
    lat: float
    lng: float
    description: str
    for_unit: Optional[str] = None  # 'sniper', 'support', etc.
    icon: str  # Icon name for frontend

class SegmentAnalysis(BaseModel):
    segment_index: int
    risk_level: str  # 'low', 'medium', 'high'
    description: str
    suggestions: List[str]

class RouteEvaluationResponse(BaseModel):
    request_id: str
    annotated_image: str  # base64
    annotated_image_bounds: dict
    positions: List[SuggestedPosition]
    segment_analysis: List[SegmentAnalysis]
    overall_assessment: str
    route_distance_m: float
    estimated_time_minutes: float
```

### 2.2 New Endpoint in api/tactical.py

```python
@router.post("/api/evaluate-route", response_model=RouteEvaluationResponse)
async def evaluate_route(request: RouteEvaluationRequest):
    """
    Evaluate a user-drawn route and suggest tactical positions.
    """
    pass
```

### 2.3 New Method in GeminiImageRouteGenerator

```python
async def evaluate_user_route(
    self,
    satellite_image_base64: str,
    waypoints: List[dict],
    units: dict,
    bounds: dict
) -> dict:
    """
    Evaluate user-drawn route and suggest positions.

    1. Draw user's route on satellite image (dashed blue line)
    2. Send to Gemini with evaluation prompt
    3. Parse response for positions and analysis
    """
    pass
```

### 2.4 Evaluation Prompt (config.yaml)

```yaml
route_evaluation_prompt: |
  Analyze this satellite image showing a proposed infantry patrol route.
  The BLUE DASHED LINE shows the user's planned route.

  Unit composition:
  - Squad size: {squad_size}
  - Riflemen: {riflemen}
  - Snipers: {snipers}
  - Support/MG: {support}
  - Medics: {medics}

  TASK: Evaluate the route and mark optimal positions on the image.

  DRAW ON THE IMAGE:
  1. GREEN CIRCLES - Cover positions (behind walls, in vegetation)
  2. YELLOW TRIANGLES - Overwatch/sniper positions (elevated, good sightlines)
  3. ORANGE SQUARES - Rally points (concealed meeting spots)
  4. RED X MARKS - Danger zones (exposed areas, chokepoints)
  5. WHITE CROSS - Suggested medic position (protected, accessible)

  Keep the original blue route line visible.

  Also provide analysis in this JSON format:
  {
    "segments": [
      {"index": 0, "risk": "low/medium/high", "description": "...", "suggestions": [...]}
    ],
    "positions": [
      {"type": "overwatch", "description": "...", "for_unit": "sniper"}
    ],
    "overall": "2-3 sentence assessment"
  }
```

---

## Phase 3: Results Display

### 3.1 New Component: EvaluationResults.tsx

Location: `ui/src/components/sidebar/EvaluationResults.tsx`

```tsx
// Displays after evaluation:
// - Overall assessment text
// - Route stats (distance, time)
// - Segment-by-segment analysis (collapsible)
// - Position legend with counts
// - "Clear" button to reset
```

### 3.2 Update TacticalMap.tsx for Evaluation Display

```tsx
// When routeEvaluation exists:
// - Show annotated satellite image as overlay
// - Add markers for suggested positions with custom icons:
//   - Overwatch: Yellow triangle
//   - Cover: Green circle
//   - Rally: Orange square
//   - Danger: Red X
//   - Medic: White cross
// - Clicking marker shows description tooltip
```

### 3.3 Position Icons

Create SVG icons for each position type:
- `/ui/public/icons/overwatch.svg`
- `/ui/public/icons/cover.svg`
- `/ui/public/icons/rally.svg`
- `/ui/public/icons/danger.svg`
- `/ui/public/icons/medic.svg`

---

## Phase 4: Loading & Polish

### 4.1 Update PlanningLoader.tsx

Add evaluation mode stages:
```tsx
const evaluationStages = [
  { icon: Satellite, label: "Capturing Area" },
  { icon: Pencil, label: "Analyzing Route" },
  { icon: MapPin, label: "Finding Positions" }
]
```

### 4.2 SSE Progress for Evaluation

New stages:
- 'imagery' (0-20%)
- 'drawing' (20-40%)
- 'analysis' (40-80%)
- 'positions' (80-95%)
- 'complete' (100%)

### 4.3 Error Handling

- No waypoints: Disable evaluate button
- Less than 2 waypoints: Show warning
- Invalid unit composition: Validation error
- Gemini failure: Graceful fallback message

---

## File Changes Summary

### New Files
```
ui/src/components/sidebar/RouteDrawingControls.tsx
ui/src/components/sidebar/UnitCompositionPanel.tsx
ui/src/components/sidebar/EvaluationResults.tsx
ui/public/icons/overwatch.svg
ui/public/icons/cover.svg
ui/public/icons/rally.svg
ui/public/icons/danger.svg
ui/public/icons/medic.svg
```

### Modified Files
```
ui/src/hooks/useMission.ts          - Add drawing state & actions
ui/src/hooks/useApi.ts              - Add evaluateRoute mutation
ui/src/types/index.ts               - Add new types
ui/src/components/map/TacticalMap.tsx - Add drawing layer
ui/src/components/sidebar/Sidebar.tsx - Add new sections
ui/src/components/tactical/PlanningLoader.tsx - Evaluation stages

georoute/config.yaml                - Add evaluation prompt
georoute/models/tactical.py         - Add new models
georoute/api/tactical.py            - Add evaluate endpoint
georoute/processing/gemini_image_route_generator.py - Add evaluation method
georoute/processing/balanced_tactical_pipeline.py - Add evaluation pipeline
```

---

## Implementation Order

1. **Backend First** (simpler to test)
   - Add models
   - Add endpoint stub
   - Add Gemini evaluation method
   - Test with Postman/curl

2. **Frontend State**
   - Add state to useMission
   - Add API hook

3. **Frontend Drawing**
   - Route mode toggle
   - Waypoint drawing on map
   - Polyline visualization

4. **Frontend Unit Panel**
   - Unit composition UI
   - Validation

5. **Integration**
   - Connect evaluate button to API
   - Display results

6. **Polish**
   - Loading states
   - Icons
   - Error handling
   - Mobile responsive

---

## Estimated Complexity

| Component | Complexity | Notes |
|-----------|------------|-------|
| Route drawing on map | Medium | Leaflet editing tools |
| Unit composition panel | Low | Form inputs |
| Backend evaluation | Medium | New Gemini prompt |
| Results display | Medium | Markers + overlay |
| State management | Low | Zustand additions |

---

## Questions to Resolve

1. Should the user be able to save/load routes?
2. Should we support route "templates" (common patterns)?
3. Should evaluation results be saved to history like current reports?
4. Should we allow multiple routes to be drawn and compared?
