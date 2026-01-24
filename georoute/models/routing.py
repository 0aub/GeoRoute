"""Routing decision models - structured output from Gemini."""

from enum import Enum
from typing import Optional, Dict
from pydantic import BaseModel, Field


class TraversabilityLevel(str, Enum):
    """Terrain traversability classification."""
    EASY = "easy"
    MODERATE = "moderate"
    DIFFICULT = "difficult"
    VERY_DIFFICULT = "very_difficult"
    IMPASSABLE = "impassable"


class HazardSeverity(str, Enum):
    """Hazard severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RouteWaypoint(BaseModel):
    """A single waypoint along the route."""
    lat: float = Field(description="Latitude in decimal degrees")
    lon: float = Field(description="Longitude in decimal degrees")
    elevation_m: float = Field(description="Elevation in meters")
    distance_from_start_km: float = Field(description="Cumulative distance from start")
    terrain_type: str = Field(description="Dominant terrain: road, trail, off-road, etc.")
    surface_type: str = Field(description="Surface: asphalt, gravel, dirt, rock, etc.")
    traversability: TraversabilityLevel
    slope_deg: Optional[float] = Field(default=None, description="Slope at this point in degrees")
    notes: Optional[str] = Field(default=None, description="Special considerations for this waypoint")


class TerrainHazard(BaseModel):
    """A hazard identified along or near the route."""
    hazard_type: str = Field(description="Type: steep_slope, water_crossing, cliff, etc.")
    severity: HazardSeverity
    lat: float
    lon: float
    description: str
    mitigation: Optional[str] = Field(default=None, description="How to handle this hazard")


class RouteSegment(BaseModel):
    """A segment of the route between waypoints."""
    segment_id: int
    start_waypoint: int = Field(description="Index of start waypoint")
    end_waypoint: int = Field(description="Index of end waypoint")
    distance_km: float
    estimated_time_minutes: float
    average_slope_deg: float
    max_slope_deg: float
    surface_type: str
    traversability: TraversabilityLevel
    requires_4wd: bool
    hazards: list[int] = Field(default_factory=list, description="Indices of hazards on this segment")


class AlternativeRoute(BaseModel):
    """An alternative route option."""
    name: str
    description: str
    pros: list[str]
    cons: list[str]
    distance_km: float
    estimated_time_hours: float
    overall_difficulty: TraversabilityLevel


class TerrainDistribution(BaseModel):
    """Percentage breakdown of terrain types on route."""
    road: float = Field(default=0.0, description="Percentage on roads")
    trail: float = Field(default=0.0, description="Percentage on trails")
    off_road: float = Field(default=0.0, description="Percentage off-road")
    urban: float = Field(default=0.0, description="Percentage in urban areas")
    rocky: float = Field(default=0.0, description="Percentage on rocky terrain")
    sandy: float = Field(default=0.0, description="Percentage on sandy terrain")
    vegetated: float = Field(default=0.0, description="Percentage in vegetated areas")
    other: float = Field(default=0.0, description="Percentage other terrain")


class SurfaceDistribution(BaseModel):
    """Percentage breakdown of surface types on route."""
    asphalt: float = Field(default=0.0, description="Percentage on asphalt")
    gravel: float = Field(default=0.0, description="Percentage on gravel")
    dirt: float = Field(default=0.0, description="Percentage on dirt")
    rock: float = Field(default=0.0, description="Percentage on rock")
    sand: float = Field(default=0.0, description="Percentage on sand")
    mud: float = Field(default=0.0, description="Percentage on mud")
    grass: float = Field(default=0.0, description="Percentage on grass")
    other: float = Field(default=0.0, description="Percentage other surface")


class RoutingDecision(BaseModel):
    """Complete routing decision from Gemini."""
    route_name: str = Field(description="Descriptive name for this route")
    mission_summary: str = Field(description="Brief description of the routing solution")

    # Distance and time
    total_distance_km: float
    estimated_duration_hours: float

    # Elevation analysis
    total_elevation_gain_m: float
    total_elevation_loss_m: float
    max_elevation_m: float
    min_elevation_m: float
    max_slope_deg: float

    # Route details
    waypoints: list[RouteWaypoint]
    segments: list[RouteSegment]
    hazards: list[TerrainHazard]

    # Terrain breakdown
    terrain_distribution: TerrainDistribution = Field(
        description="Percentage of route by terrain type"
    )
    surface_distribution: SurfaceDistribution = Field(
        description="Percentage of route by surface type"
    )

    # Assessment
    overall_difficulty: TraversabilityLevel
    feasibility_score: float = Field(
        description="0-1 score of route viability",
        ge=0, le=1
    )
    confidence_score: float = Field(
        description="0-1 confidence in this analysis",
        ge=0, le=1
    )

    # Reasoning
    reasoning: str = Field(
        description="Detailed explanation of routing decisions"
    )
    key_challenges: list[str]
    recommendations: list[str]

    # Alternatives
    alternative_routes: Optional[list[AlternativeRoute]] = None
