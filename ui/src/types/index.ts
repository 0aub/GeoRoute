export interface Coordinate {
  lat: number;
  lon: number;
}

export interface Waypoint extends Coordinate {
  id: string;
  order: number;
}

export interface NoGoZone {
  id: string;
  coordinates: Coordinate[];
  name?: string;
}

export interface VehicleProfile {
  id: string;
  name: string;
  maxSlope: number;
  weight: number;
  weightUnit: string;
}

export interface RouteHazard {
  id: string;
  lat: number;
  lon: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  mitigation: string;
}

export interface ElevationPoint {
  distance: number;
  elevation: number;
  difficulty?: 'easy' | 'moderate' | 'difficult' | 'very_difficult';
}

export interface RouteResult {
  id: string;
  name: string;
  totalDistance: number;
  estimatedDuration: number;
  difficulty: 'easy' | 'moderate' | 'difficult' | 'very_difficult' | 'impassable';
  feasibilityScore: number;
  confidenceScore: number;
  keyChallenges: string[];
  recommendations: string[];
  coordinates: Coordinate[];
  hazards: RouteHazard[];
  elevationProfile: ElevationPoint[];
}

export interface PlanRouteRequest {
  start_lat: number;
  start_lon: number;
  end_lat: number;
  end_lon: number;
  vehicle_type: string;
  waypoints: Coordinate[];
  no_go_zones: NoGoZone[];
}

export interface QuickAssessRequest {
  lat: number;
  lon: number;
  radius_km: number;
}

export interface HealthStatus {
  status: 'ok' | 'error';
  apis: {
    google_maps: boolean;
    gemini: boolean;
    osrm: boolean;
    ors: boolean;
  };
}

export type MapMode = 'idle' | 'set-start' | 'set-end' | 'add-waypoint' | 'draw-no-go' | 'place-soldier' | 'place-enemy';

// ============================================================================
// Tactical Planning Types (Military Unit-Based System)
// ============================================================================

// Unit Types - Simplified to just Friendly/Enemy
export interface TacticalUnit {
  unit_id: string;
  lat: number;
  lon: number;
  is_friendly: boolean;
}

// Risk and Classification
export type RiskLevel = 'safe' | 'moderate' | 'high' | 'critical';
export type RouteVerdict = 'success' | 'risk' | 'failed';

// Waypoint and Segment Structures
export interface DetailedWaypoint {
  lat: number;
  lon: number;
  elevation_m: number;
  distance_from_start_m: number;
  terrain_type: string;
  risk_level: RiskLevel;
  reasoning: string;
  tactical_note?: string;
}

export interface RouteSegment {
  segment_id: number;
  start_waypoint_idx: number;
  end_waypoint_idx: number;
  color: string;  // 'blue' | 'yellow' | 'orange' | 'red'
  risk_level: RiskLevel;
  distance_m: number;
  estimated_time_seconds: number;
  risk_factors: string[];
}

// Scoring and Simulation
export interface RouteScores {
  time_to_target: number;        // 0-100
  stealth_score: number;          // 0-100
  survival_probability: number;   // 0-100
  overall_score: number;          // 0-100
}

export interface SimulationResult {
  detected: boolean;
  detection_probability: number;  // 0-1
  detection_points: [number, number][];
  safe_percentage: number;        // 0-100
}

export interface ClassificationResult {
  gemini_evaluation: RouteVerdict;
  gemini_reasoning: string;
  scores: RouteScores;
  simulation: SimulationResult;
  final_verdict: RouteVerdict;
  final_reasoning: string;
  confidence: number;  // 0-1
}

// Complete Tactical Route
export interface TacticalRoute {
  route_id: number;
  name: string;
  description: string;
  waypoints: DetailedWaypoint[];
  segments: RouteSegment[];
  classification: ClassificationResult;
  total_distance_m: number;
  estimated_duration_seconds: number;
}

// API Request/Response
export interface Bounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface TacticalPlanRequest {
  request_id: string;
  soldiers: TacticalUnit[];
  enemies: TacticalUnit[];
  bounds: Bounds;
  zoom: number;
}

export interface TacticalPlanResponse {
  request_id: string;
  routes: TacticalRoute[];  // Always 3 routes
  metadata: {
    terrain_samples: number;
    zoom_level: number;
    has_satellite_image: boolean;
    has_terrain_image: boolean;
  };
}

// Backlog/Audit Trail Types
export interface APICall {
  timestamp: string;
  service: string;
  endpoint: string;
  request_params: Record<string, any>;
  response_data: Record<string, any>;
}

export interface GeminiRequest {
  timestamp: string;
  stage: 'stage1_initial_routes' | 'stage2_refine_waypoints' | 'stage3_score_routes' | 'stage4_final_classification';
  prompt: string;
  response: string;
  image_included: boolean;
}

export interface BacklogEntry {
  request_id: string;
  timestamp: string;
  user_input: TacticalPlanRequest;
  api_calls: APICall[];
  gemini_pipeline: GeminiRequest[];  // 4 stages
  satellite_image?: string;  // base64
  terrain_image?: string;    // base64
  result: TacticalPlanResponse;
  total_duration_seconds: number;
}

export interface BacklogListResponse {
  entries: BacklogEntry[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}
