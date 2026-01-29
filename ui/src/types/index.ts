// ============================================================================
// Core Types
// ============================================================================

export interface Coordinate {
  lat: number;
  lon: number;
}

export interface Bounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

export type MapMode = 'idle' | 'place-soldier' | 'place-enemy';

export interface NoGoZone {
  id: string;
  coordinates: Coordinate[];
}

// ============================================================================
// Tactical Planning Types
// ============================================================================

export interface TacticalUnit {
  unit_id: string;
  lat: number;
  lon: number;
  is_friendly: boolean;
  plan_id?: number;
  plan_unit_number?: number;
}

export type RiskLevel = 'safe' | 'moderate' | 'high' | 'critical';
export type RouteVerdict = 'success' | 'risk' | 'failed';

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
  color: string;
  risk_level: RiskLevel;
  distance_m: number;
  estimated_time_seconds: number;
  risk_factors: string[];
}

export interface RouteScores {
  time_to_target: number;
  stealth_score: number;
  survival_probability: number;
  overall_score: number;
}

export interface SimulationResult {
  detected: boolean;
  detection_probability: number;
  detection_points: [number, number][];
  safe_percentage: number;
}

export interface ClassificationResult {
  gemini_evaluation: RouteVerdict;
  gemini_reasoning: string;
  scores: RouteScores;
  simulation: SimulationResult;
  final_verdict: RouteVerdict;
  final_reasoning: string;
  confidence: number;
}

export interface TacticalRoute {
  route_id: number;
  name: string;
  description: string;
  color?: string;
  waypoints: DetailedWaypoint[];
  segments: RouteSegment[];
  classification: ClassificationResult;
  total_distance_m: number;
  estimated_duration_seconds: number;
}

// ============================================================================
// API Types
// ============================================================================

export interface TacticalPlanRequest {
  request_id: string;
  soldiers: TacticalUnit[];
  enemies: TacticalUnit[];
  bounds: Bounds;
  zoom: number;
  advanced_analytics?: boolean;
}

export interface TacticalPlanResponse {
  request_id: string;
  routes: TacticalRoute[];
  metadata: {
    terrain_samples: number;
    zoom_level: number;
    has_satellite_image: boolean;
    has_terrain_image: boolean;
  };
  tactical_analysis_report?: Record<string, unknown>;
  detection_debug?: {
    sam_visualization?: string;
    sam_visualization_bounds?: Bounds;
    gemini_route_image?: string;
    gemini_route_bounds?: Bounds;
  };
}

export interface HealthStatus {
  status: 'ok' | 'error';
  message?: string;
}
