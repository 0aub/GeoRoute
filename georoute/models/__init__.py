"""Pydantic models for the route optimization pipeline."""

from .routing import (
    TraversabilityLevel,
    HazardSeverity,
    RouteWaypoint,
    TerrainHazard,
    RouteSegment,
    AlternativeRoute,
    RoutingDecision,
)
from .vehicles import VehicleProfile, VEHICLE_PROFILES
from .requests import (
    RouteRequest,
    PointRequest,
    Coordinates,
)
from .tactical import (
    TacticalUnit,
    RiskLevel,
    RouteVerdict,
    DetailedWaypoint,
    RouteSegment as TacticalRouteSegment,
    RouteScores,
    SimulationResult,
    ClassificationResult,
    TacticalRoute,
    TacticalPlanRequest,
    TacticalPlanResponse,
    APICall,
    GeminiRequest,
    BacklogEntry,
)

__all__ = [
    # Legacy routing models
    "TraversabilityLevel",
    "HazardSeverity",
    "RouteWaypoint",
    "TerrainHazard",
    "RouteSegment",
    "AlternativeRoute",
    "RoutingDecision",
    "VehicleProfile",
    "VEHICLE_PROFILES",
    "RouteRequest",
    "PointRequest",
    "Coordinates",
    # Tactical models
    "TacticalUnit",
    "RiskLevel",
    "RouteVerdict",
    "DetailedWaypoint",
    "TacticalRouteSegment",
    "RouteScores",
    "SimulationResult",
    "ClassificationResult",
    "TacticalRoute",
    "TacticalPlanRequest",
    "TacticalPlanResponse",
    "APICall",
    "GeminiRequest",
    "BacklogEntry",
]
