"""API request models."""

from typing import Optional
from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """Latitude/longitude coordinate pair."""
    lat: float = Field(description="Latitude in decimal degrees", ge=-90, le=90)
    lon: float = Field(description="Longitude in decimal degrees", ge=-180, le=180)


class RouteRequest(BaseModel):
    """Request body for route planning."""
    start_lat: float = Field(description="Start point latitude", ge=-90, le=90)
    start_lon: float = Field(description="Start point longitude", ge=-180, le=180)
    end_lat: float = Field(description="End point latitude", ge=-90, le=90)
    end_lon: float = Field(description="End point longitude", ge=-180, le=180)
    vehicle_type: str = Field(default="mrap", description="Vehicle profile key")
    waypoints: Optional[list[Coordinates]] = Field(
        default=None,
        description="Optional intermediate waypoints"
    )
    no_go_zones: Optional[list[list[Coordinates]]] = Field(
        default=None,
        description="List of polygon coordinates to avoid"
    )


class PointRequest(BaseModel):
    """Request body for single point operations."""
    lat: float = Field(description="Latitude in decimal degrees", ge=-90, le=90)
    lon: float = Field(description="Longitude in decimal degrees", ge=-180, le=180)
    radius_km: float = Field(default=10, description="Analysis radius in kilometers", gt=0, le=100)
