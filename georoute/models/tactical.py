"""Tactical military planning models."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class TacticalUnit(BaseModel):
    """A tactical unit (friendly or enemy) - simplified to just position."""
    lat: float = Field(description="Latitude position")
    lon: float = Field(description="Longitude position")
    is_friendly: bool = Field(description="True for friendly units, False for enemies")
    unit_id: Optional[str] = Field(default=None, description="Unique identifier")


class RiskLevel(str, Enum):
    """Risk level for route segments."""
    SAFE = "safe"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class RouteVerdict(str, Enum):
    """Final classification verdict for a route."""
    SUCCESS = "success"
    RISK = "risk"
    FAILED = "failed"


class DetailedWaypoint(BaseModel):
    """A detailed waypoint along a tactical route."""
    lat: float
    lon: float
    elevation_m: float
    distance_from_start_m: float
    terrain_type: str = Field(description="Terrain at this point")
    risk_level: RiskLevel
    reasoning: str = Field(description="Why this waypoint has this risk level")
    tactical_note: Optional[str] = Field(default=None, description="Tactical instruction")


class RouteSegment(BaseModel):
    """A colored segment of a route between waypoints."""
    segment_id: int
    start_waypoint_idx: int
    end_waypoint_idx: int
    color: str = Field(description="blue/yellow/orange/red based on risk")
    risk_level: RiskLevel
    distance_m: float
    estimated_time_seconds: float
    risk_factors: list[str] = Field(description="Why this segment is risky")


class RouteScores(BaseModel):
    """Scoring metrics for a tactical route."""
    time_to_target: float = Field(description="0-100, higher = faster", ge=0, le=100)
    stealth_score: float = Field(description="0-100, higher = more stealthy", ge=0, le=100)
    survival_probability: float = Field(description="0-100, higher = safer", ge=0, le=100)
    overall_score: float = Field(description="0-100, weighted average", ge=0, le=100)


class SimulationResult(BaseModel):
    """Enemy detection simulation result."""
    detected: bool = Field(description="Whether route crosses enemy detection zones")
    detection_probability: float = Field(description="0-1 probability of detection", ge=0, le=1)
    detection_points: list[tuple[float, float]] = Field(
        default_factory=list,
        description="Coordinates where detection is likely"
    )
    safe_percentage: float = Field(description="Percentage of route that's safe", ge=0, le=100)


class ClassificationResult(BaseModel):
    """Multi-layered classification result for a route."""
    # Layer 1: Gemini evaluation
    gemini_evaluation: RouteVerdict
    gemini_reasoning: str

    # Layer 2: Scoring system
    scores: RouteScores

    # Layer 3: Simulation
    simulation: SimulationResult

    # Final verdict (combines all layers)
    final_verdict: RouteVerdict
    final_reasoning: str = Field(description="Comprehensive explanation")
    confidence: float = Field(description="0-1 confidence in classification", ge=0, le=1)


class TacticalRoute(BaseModel):
    """One of the 3 generated tactical routes."""
    route_id: int = Field(description="1, 2, or 3")
    name: str = Field(description="Route name from Gemini")
    description: str = Field(description="Brief route description")

    # Detailed route data
    waypoints: list[DetailedWaypoint]
    segments: list[RouteSegment]

    # Classification
    classification: ClassificationResult

    # Metadata
    total_distance_m: float
    estimated_duration_seconds: float
    elevation_gain_m: float
    elevation_loss_m: float


class TacticalPlanRequest(BaseModel):
    """Request to plan a tactical attack."""
    request_id: Optional[str] = Field(default=None, description="Client-provided request ID for progress tracking")
    soldiers: list[TacticalUnit]
    enemies: list[TacticalUnit]
    bounds: dict = Field(description="Map bounds with north, south, east, west keys")
    zoom: Optional[int] = Field(default=14, description="Map zoom level (11-15 for tactical)")
    no_go_zones: Optional[list[list[tuple[float, float]]]] = Field(
        default=None,
        description="List of polygon coordinates to avoid"
    )
    analysis_depth: str = Field(
        default="full",
        description="full = all classification layers, quick = Gemini only"
    )


class TacticalPlanResponse(BaseModel):
    """Response with tactical routes."""
    request_id: str = Field(description="UUID for this planning request")
    timestamp: datetime

    # Input summary
    soldiers_count: int
    enemies_count: int
    no_go_zones_count: int

    # Generated routes
    routes: list[TacticalRoute]

    # Recommended route
    recommended_route_id: int = Field(description="Which route is recommended")

    # Overall assessment
    mission_assessment: str = Field(description="Overall tactical assessment")
    key_risks: list[str]
    recommendations: list[str]

    # Debug: Detection visualization data for UI
    detection_debug: Optional[dict] = Field(
        default=None,
        description="Grid detection debug info - building_cells, traversable_cells, grid_cells for visualization"
    )


# Backlog models

class APICall(BaseModel):
    """Record of an API call made during planning."""
    api_name: str = Field(description="Google Maps, OSRM, etc.")
    endpoint: str
    method: str = Field(default="GET")
    request_params: dict = Field(default_factory=dict)
    response_status: int
    response_data: Optional[dict] = None
    duration_seconds: float
    timestamp: datetime


class GeminiRequest(BaseModel):
    """Record of a Gemini API request."""
    stage: str = Field(description="Stage identifier (stage1_initial_routes, etc.)")
    prompt: str
    response: str = Field(description="JSON string response from Gemini")
    image_included: bool = Field(default=False, description="Whether images were sent")
    timestamp: datetime


class BacklogEntry(BaseModel):
    """Complete audit trail of a tactical planning request."""
    request_id: str
    timestamp: datetime

    # User input
    user_input: TacticalPlanRequest

    # API calls made (in order)
    api_calls: list[APICall] = Field(default_factory=list)

    # Gemini pipeline (sequential requests)
    gemini_pipeline: list[GeminiRequest] = Field(default_factory=list)

    # Images stored
    satellite_image: Optional[str] = Field(default=None, description="Base64 encoded")
    terrain_image: Optional[str] = Field(default=None, description="Base64 encoded")

    # Final result
    result: TacticalPlanResponse

    # Totals
    total_duration_seconds: float
    total_api_calls: int
    total_gemini_requests: int
