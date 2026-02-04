"""Tactical military planning models."""

from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class TacticalUnit(BaseModel):
    """A tactical unit (friendly or enemy) - simplified to just position."""
    lat: float = Field(description="Latitude position")
    lon: float = Field(description="Longitude position")
    is_friendly: bool = Field(description="True for friendly units, False for enemies")
    unit_id: Optional[str] = Field(default=None, description="Unique identifier")


class GeminiRequest(BaseModel):
    """Record of a Gemini API request for debugging."""
    timestamp: datetime
    stage: str = Field(description="Pipeline stage name")
    prompt: str = Field(description="Prompt sent to Gemini")
    response: str = Field(description="Response from Gemini")
    image_included: bool = Field(default=False, description="Whether image was included")


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
    advanced_analytics: bool = Field(
        default=False,
        description="Enable detailed tactical analysis report"
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

    # Advanced tactical analysis report (when advanced_analytics enabled)
    tactical_analysis_report: Optional[dict] = Field(
        default=None,
        description="Detailed tactical analysis including recommendations, timing, equipment, flanking opportunities"
    )

    # Debug: Detection visualization data for UI
    detection_debug: Optional[dict] = Field(
        default=None,
        description="Grid detection debug info - building_cells, traversable_cells, grid_cells for visualization"
    )


# ============================================================================
# Route Evaluation Models (User-drawn route analysis)
# ============================================================================

class UnitComposition(BaseModel):
    """Unit composition for tactical evaluation."""
    squad_size: int = Field(ge=2, le=12, description="Total squad size")
    riflemen: int = Field(ge=0, default=0, description="Number of riflemen")
    snipers: int = Field(ge=0, default=0, description="Number of snipers")
    support: int = Field(ge=0, default=0, description="Number of support/MG units")
    medics: int = Field(ge=0, default=0, description="Number of medics")


class RouteWaypoint(BaseModel):
    """A waypoint in a user-drawn route."""
    lat: float
    lng: float


class SuggestedPosition(BaseModel):
    """A suggested tactical position from AI evaluation."""
    position_type: str = Field(description="overwatch, cover, rally, danger, medic")
    lat: float
    lng: float
    description: str
    for_unit: Optional[str] = Field(default=None, description="Recommended unit type for this position")
    icon: str = Field(description="Icon name for frontend display")


class SegmentAnalysis(BaseModel):
    """Analysis of a route segment."""
    segment_index: int
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    risk_level: str = Field(description="low, medium, high")
    description: str
    suggestions: list[str] = Field(default_factory=list)


class RouteEvaluationRequest(BaseModel):
    """Request to evaluate a user-drawn route."""
    request_id: Optional[str] = Field(default=None, description="Client-provided request ID for progress tracking")
    waypoints: list[RouteWaypoint] = Field(min_length=2, description="User-drawn route waypoints")
    units: UnitComposition
    bounds: dict = Field(description="Map bounds with north, south, east, west keys")


class RouteEvaluationResponse(BaseModel):
    """Response with route evaluation results."""
    request_id: str
    timestamp: datetime

    # Annotated image
    annotated_image: str = Field(description="Base64-encoded annotated satellite image")
    annotated_image_bounds: dict = Field(description="Geographic bounds of the annotated image")

    # Suggested positions
    positions: list[SuggestedPosition] = Field(default_factory=list)

    # Segment analysis
    segment_analysis: list[SegmentAnalysis] = Field(default_factory=list)

    # Overall assessment
    overall_assessment: str

    # Route metrics
    route_distance_m: float
    estimated_time_minutes: float


# ============================================================================
# Tactical Simulation Models (Vision cone analysis)
# ============================================================================

class SimEnemyType(str, Enum):
    """Types of enemy units in simulation."""
    SNIPER = "sniper"
    RIFLEMAN = "rifleman"
    OBSERVER = "observer"


class SimFriendlyType(str, Enum):
    """Types of friendly units in simulation."""
    RIFLEMAN = "rifleman"
    SNIPER = "sniper"
    MEDIC = "medic"


class SimEnemyUnit(BaseModel):
    """Enemy unit in tactical simulation with vision cone."""
    id: str
    type: SimEnemyType
    lat: float
    lng: float
    facing: float = Field(ge=0, lt=360, description="Facing direction in degrees (0=North)")


class SimFriendlyUnit(BaseModel):
    """Friendly unit in tactical simulation."""
    id: str
    type: SimFriendlyType
    lat: float
    lng: float


class WeakSpot(BaseModel):
    """A weak spot identified in the tactical plan."""
    location: str = Field(description="Description of where this weak spot is")
    description: str = Field(description="What makes this a weak spot")
    severity: str = Field(description="low, medium, high, critical")
    recommendation: str = Field(description="How to mitigate this weakness")


class StrongPoint(BaseModel):
    """A strong point where route uses terrain effectively."""
    location: str = Field(description="Description of where this strong point is")
    description: str = Field(description="What makes this position advantageous")
    benefit: str = Field(description="Tactical benefit of this position")


class ExposureAnalysis(BaseModel):
    """Analysis of route exposure to enemy vision."""
    segment_index: int
    enemy_id: str
    exposure_percentage: float = Field(ge=0, le=100)
    description: str


class SegmentCoverAnalysis(BaseModel):
    """Detailed cover analysis for a single route segment."""
    segment_index: int
    in_vision_cone: bool = Field(description="Is segment geometrically in enemy vision cone?")
    cover_status: Literal["exposed", "covered", "partial", "clear"] = Field(
        description="exposed=in cone no cover, covered=in cone with cover, partial=some cover, clear=not in cone"
    )
    cover_type: Optional[str] = Field(default=None, description="building, vegetation, terrain, or none")
    exposure_percentage: float = Field(ge=0, le=100, default=0)
    blocking_feature: Optional[str] = Field(default=None, description="What blocks LOS")
    enemy_id: Optional[str] = Field(default=None, description="Which enemy this analysis is for")
    explanation: str = Field(default="", description="Human-readable explanation")


class TacticalScores(BaseModel):
    """Multi-dimensional tactical scoring (0-100 each)."""
    stealth: float = Field(ge=0, le=100, description="How hidden is the approach")
    safety: float = Field(ge=0, le=100, description="Survival probability")
    terrain_usage: float = Field(ge=0, le=100, description="How well route uses available cover")
    flanking: float = Field(ge=0, le=100, description="Tactical advantage from approach angle")
    overall: float = Field(ge=0, le=100, description="Weighted composite score")


class FlankingAnalysis(BaseModel):
    """Analysis of flanking maneuver effectiveness."""
    is_flanking: bool = Field(description="Is route approaching from enemy blind spot?")
    approach_angle: float = Field(ge=0, lt=360, description="Angle from enemy facing direction")
    bonus_awarded: float = Field(ge=0, le=3, description="Rating bonus (0-3 points)")
    description: str = Field(description="Explanation of flanking analysis")


class CoverBreakdown(BaseModel):
    """Summary breakdown of cover along the route."""
    total_segments: int
    exposed_count: int = Field(ge=0, description="Segments with no cover in enemy cone")
    covered_count: int = Field(ge=0, description="Segments with hard cover in enemy cone")
    partial_count: int = Field(ge=0, description="Segments with partial cover")
    clear_count: int = Field(ge=0, description="Segments outside all enemy cones")
    overall_cover_percentage: float = Field(ge=0, le=100, description="% of route that is covered/clear")
    cover_types_used: list[str] = Field(default_factory=list, description="Types of cover used")


class TacticalSimulationRequest(BaseModel):
    """Request to analyze a tactical simulation scenario."""
    request_id: Optional[str] = Field(default=None, description="Client-provided request ID for progress tracking")
    enemies: list[SimEnemyUnit] = Field(min_length=1, description="Enemy units with vision cones")
    friendlies: list[SimFriendlyUnit] = Field(default_factory=list, description="Friendly units")
    route_waypoints: list[RouteWaypoint] = Field(min_length=2, description="Movement route waypoints")
    bounds: dict = Field(description="Map bounds with north, south, east, west keys")


class TacticalSimulationResponse(BaseModel):
    """Response with tactical simulation analysis."""
    request_id: str
    timestamp: datetime

    # Annotated image with weak spots marked
    annotated_image: str = Field(description="Base64-encoded annotated satellite image")
    annotated_image_bounds: dict = Field(description="Geographic bounds of the annotated image")

    # Strategy rating and verdict
    strategy_rating: float = Field(ge=0, le=10, description="Overall strategy rating 0-10")
    verdict: Optional[str] = Field(default=None, description="EXCELLENT, GOOD, ACCEPTABLE, or RISKY")

    # Enhanced tactical analysis (new)
    tactical_scores: Optional[TacticalScores] = Field(default=None, description="Multi-dimensional scoring")
    flanking_analysis: Optional[FlankingAnalysis] = Field(default=None, description="Flanking maneuver analysis")
    segment_cover_analysis: list[SegmentCoverAnalysis] = Field(default_factory=list, description="Per-segment cover analysis")
    cover_breakdown: Optional[CoverBreakdown] = Field(default=None, description="Summary of cover usage")

    # Weak spots identified
    weak_spots: list[WeakSpot] = Field(default_factory=list)

    # Strong points (good use of terrain/cover)
    strong_points: list[StrongPoint] = Field(default_factory=list)

    # Exposure analysis (legacy, kept for compatibility)
    exposure_analysis: list[ExposureAnalysis] = Field(default_factory=list)

    # Terrain assessment
    terrain_assessment: str = Field(default="", description="Analysis of terrain usage")

    # Overall assessment
    overall_assessment: str

    # Recommendations
    recommendations: list[str] = Field(default_factory=list)

    # Route metrics
    route_distance_m: float
    estimated_time_minutes: float
