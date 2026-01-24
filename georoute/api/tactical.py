"""
Tactical planning API endpoints.
"""

import asyncio
import json
from typing import Annotated, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..models.tactical import (
    TacticalPlanRequest,
    TacticalPlanResponse,
    BacklogEntry,
)
from ..processing.balanced_tactical_pipeline import BalancedTacticalPipeline
from ..clients.google_maps import GoogleMapsClient
from ..clients.gemini_tactical import TacticalGeminiClient
from ..storage.backlog import get_backlog_store
from ..config import load_config


router = APIRouter(prefix="/api", tags=["tactical"])

# Global progress state for SSE (simple in-memory store)
_progress_state: dict[str, dict] = {}


# Dependency injection - Balanced pipeline: respects buildings, reasonably fast
def get_tactical_pipeline() -> BalancedTacticalPipeline:
    """Create balanced tactical pipeline - building avoidance with good speed."""
    config = load_config()

    gmaps = GoogleMapsClient(api_key=config.google_maps_api_key)
    gemini = TacticalGeminiClient(
        api_key=config.gemini_api_key,
        project_id=config.google_cloud_project,
    )

    return BalancedTacticalPipeline(
        gmaps_client=gmaps,
        gemini_client=gemini,
    )


def update_progress(request_id: str, stage: str, progress: int, message: str):
    """Update progress for a request (used by pipeline)."""
    _progress_state[request_id] = {
        "stage": stage,
        "progress": progress,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/progress/{request_id}")
async def get_progress_stream(request_id: str):
    """
    Server-Sent Events endpoint for real-time progress updates.

    Connect to this endpoint before starting plan-tactical-attack-stream.
    """
    async def event_generator():
        last_state = None
        timeout_counter = 0
        max_timeout = 300  # 5 minutes max

        while timeout_counter < max_timeout:
            current_state = _progress_state.get(request_id)

            if current_state and current_state != last_state:
                last_state = current_state
                yield f"data: {json.dumps(current_state)}\n\n"

                # If complete or error, end the stream
                if current_state.get("stage") in ["complete", "error"]:
                    break

            await asyncio.sleep(0.5)
            timeout_counter += 0.5

        # Cleanup
        if request_id in _progress_state:
            del _progress_state[request_id]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/plan-tactical-attack", response_model=TacticalPlanResponse)
async def plan_tactical_attack(
    request: TacticalPlanRequest,
    pipeline: Annotated[BalancedTacticalPipeline, Depends(get_tactical_pipeline)],
) -> TacticalPlanResponse:
    """
    Generate tactical attack plan with 3 routes.

    Process:
    1. Gather terrain and satellite imagery
    2. Run 4-stage Gemini pipeline:
       - Generate 3 initial routes
       - Refine waypoints with risk analysis
       - Calculate scores (time/stealth/survival)
       - Final classification (SUCCESS/RISK/FAILED)
    3. Build color-coded route segments
    4. Store complete audit trail

    Returns:
        Complete tactical plan with 3 classified routes
    """
    try:
        # Use client-provided request_id for progress tracking
        progress_id = request.request_id or 'default'

        # Set progress callback for real-time updates
        pipeline.set_progress_callback(
            lambda stage, progress, msg: update_progress(progress_id, stage, progress, msg)
        )
        response = await pipeline.plan_tactical_attack(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tactical planning failed: {str(e)}")


@router.get("/backlog", response_model=dict)
async def list_backlog(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    since: Optional[datetime] = Query(default=None),
) -> dict:
    """
    List tactical planning requests from backlog.

    Args:
        limit: Maximum number of entries (1-100)
        offset: Number of entries to skip
        since: Only return entries after this timestamp

    Returns:
        List of backlog entries with pagination info
    """
    backlog = get_backlog_store()

    entries = backlog.list_entries(limit=limit, offset=offset, since=since)
    total = backlog.count(since=since)

    # Convert to dict for JSON serialization
    entries_dict = [entry.model_dump() for entry in entries]

    return {
        "entries": entries_dict,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(entries) < total,
        },
    }


@router.get("/backlog/{request_id}", response_model=BacklogEntry)
async def get_backlog_entry(request_id: str) -> BacklogEntry:
    """
    Get detailed backlog entry by ID.

    Includes complete audit trail:
    - User input
    - All API calls (Google Maps, etc.)
    - All 4 Gemini requests/responses
    - Satellite and terrain images (base64)
    - Generated routes with classifications
    - Total duration

    Args:
        request_id: UUID of the request

    Returns:
        Complete backlog entry
    """
    backlog = get_backlog_store()
    entry = backlog.get_entry(request_id)

    if not entry:
        raise HTTPException(status_code=404, detail=f"Backlog entry not found: {request_id}")

    return entry


@router.get("/backlog/{request_id}/images", response_model=dict)
async def get_backlog_images(request_id: str) -> dict:
    """
    Get satellite and terrain images for a specific request.

    Args:
        request_id: UUID of the request

    Returns:
        Dict with satellite_image and terrain_image (base64 encoded)
    """
    backlog = get_backlog_store()
    images = backlog.get_images(request_id)

    if not images["satellite_image"] and not images["terrain_image"]:
        raise HTTPException(
            status_code=404,
            detail=f"No images found for request: {request_id}",
        )

    return images


@router.delete("/backlog", status_code=204)
async def clear_backlog():
    """
    Clear all backlog entries (for testing/debugging).

    WARNING: This permanently deletes all audit trail data.
    """
    backlog = get_backlog_store()
    backlog.clear()
    return None
