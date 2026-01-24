"""FastAPI route definitions."""

import base64
import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends

from ..models.requests import RouteRequest, PointRequest
from ..models.vehicles import VEHICLE_PROFILES
from ..processing.pipeline import MilitaryRoutePipeline

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get pipeline instance (set in main.py)
_pipeline: MilitaryRoutePipeline = None


def get_pipeline() -> MilitaryRoutePipeline:
    """Get the pipeline instance."""
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    return _pipeline


def set_pipeline(pipeline: MilitaryRoutePipeline):
    """Set the pipeline instance (called from main.py)."""
    global _pipeline
    _pipeline = pipeline


@router.get("/health")
async def health_check(pipeline: Annotated[MilitaryRoutePipeline, Depends(get_pipeline)]):
    """Health check endpoint - does NOT test APIs to preserve rate limits."""
    # IMPORTANT: Do NOT call test_all_apis() here - it depletes Gemini rate limits
    # API testing happens once on startup in main.py lifespan
    return {
        "status": "ok",
        "message": "Pipeline initialized",
    }


@router.get("/vehicles")
async def list_vehicles():
    """List available vehicle profiles."""
    return [
        {
            "id": name,
            "name": v.name,
            "type": v.type,
            "max_slope_degrees": v.max_slope_degrees,
            "ground_clearance_cm": v.ground_clearance_cm,
            "weight_tons": v.weight_tons,
            "max_ford_depth_cm": v.max_ford_depth_cm,
            "preferred_surfaces": v.preferred_surfaces,
            "avoid_surfaces": v.avoid_surfaces,
            "max_speed_on_road_kmh": v.max_speed_on_road_kmh,
            "max_speed_off_road_kmh": v.max_speed_off_road_kmh,
        }
        for name, v in VEHICLE_PROFILES.items()
    ]


@router.post("/plan-route")
async def plan_route(
    request: RouteRequest,
    pipeline: Annotated[MilitaryRoutePipeline, Depends(get_pipeline)],
):
    """Main route planning endpoint."""
    # Validate vehicle type
    vehicle = VEHICLE_PROFILES.get(request.vehicle_type)
    if not vehicle:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown vehicle type: {request.vehicle_type}. "
            f"Available: {list(VEHICLE_PROFILES.keys())}",
        )

    # Convert waypoints if provided
    waypoints = None
    if request.waypoints:
        waypoints = [(w.lat, w.lon) for w in request.waypoints]

    # Convert no-go zones if provided
    no_go_zones = None
    if request.no_go_zones:
        no_go_zones = [[(p.lat, p.lon) for p in zone] for zone in request.no_go_zones]

    try:
        result = await pipeline.plan_route(
            start=(request.start_lat, request.start_lon),
            end=(request.end_lat, request.end_lon),
            vehicle=vehicle,
            waypoints=waypoints,
            no_go_zones=no_go_zones,
        )

        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error"))

        return result

    except Exception as e:
        logger.exception("Route planning failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-assess")
async def quick_assessment(
    request: PointRequest,
    pipeline: Annotated[MilitaryRoutePipeline, Depends(get_pipeline)],
):
    """Quick terrain assessment for a point."""
    try:
        result = await pipeline.quick_assessment(
            center=(request.lat, request.lon),
            radius_km=request.radius_km,
        )

        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error"))

        return result

    except Exception as e:
        logger.exception("Quick assessment failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/elevation")
async def get_elevation(
    lat: float,
    lon: float,
    pipeline: Annotated[MilitaryRoutePipeline, Depends(get_pipeline)],
):
    """Get elevation at a single point."""
    try:
        result = await pipeline.maps.get_elevation_at_points([(lat, lon)])
        return result
    except Exception as e:
        logger.exception("Elevation lookup failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/satellite-image")
async def get_satellite(
    pipeline: Annotated[MilitaryRoutePipeline, Depends(get_pipeline)],
    lat: float,
    lon: float,
    zoom: int = 14,
):
    """Get satellite image for a location as base64."""
    try:
        image_bytes = await pipeline.maps.get_satellite_image(
            center=(lat, lon),
            zoom=zoom,
        )

        if image_bytes:
            return {"image": base64.b64encode(image_bytes).decode()}

        raise HTTPException(status_code=500, detail="Failed to fetch image")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Satellite image fetch failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/terrain-image")
async def get_terrain(
    pipeline: Annotated[MilitaryRoutePipeline, Depends(get_pipeline)],
    lat: float,
    lon: float,
    zoom: int = 12,
):
    """Get terrain image for a location as base64."""
    try:
        image_bytes = await pipeline.maps.get_terrain_image(
            center=(lat, lon),
            zoom=zoom,
        )

        if image_bytes:
            return {"image": base64.b64encode(image_bytes).decode()}

        raise HTTPException(status_code=500, detail="Failed to fetch image")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Terrain image fetch failed")
        raise HTTPException(status_code=500, detail=str(e))
