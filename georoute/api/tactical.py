"""
Tactical planning API endpoints.
"""

import asyncio
import json
from typing import Annotated
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..models.tactical import (
    TacticalPlanRequest,
    TacticalPlanResponse,
    RouteEvaluationRequest,
    RouteEvaluationResponse,
    TacticalSimulationRequest,
    TacticalSimulationResponse,
)
from ..processing.balanced_tactical_pipeline import BalancedTacticalPipeline
from ..config import load_config


router = APIRouter(prefix="/api", tags=["tactical"])

# Global progress state for SSE (simple in-memory store)
_progress_state: dict[str, dict] = {}


# Dependency injection - Balanced pipeline: respects buildings, reasonably fast
def get_tactical_pipeline() -> BalancedTacticalPipeline:
    """Create balanced tactical pipeline - building avoidance with good speed."""
    config = load_config()
    return BalancedTacticalPipeline(config)


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

        # Send immediate "connecting" state so UI doesn't show 0% for long
        yield f"data: {json.dumps({'stage': 'imagery', 'progress': 5, 'message': 'Connecting...'})}\n\n"

        while timeout_counter < max_timeout:
            current_state = _progress_state.get(request_id)

            if current_state and current_state != last_state:
                last_state = current_state
                yield f"data: {json.dumps(current_state)}\n\n"

                # If complete or error, end the stream
                if current_state.get("stage") in ["complete", "error"]:
                    break

            await asyncio.sleep(0.1)  # Faster polling for smoother progress
            timeout_counter += 0.1

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


@router.post("/evaluate-route", response_model=RouteEvaluationResponse)
async def evaluate_route(
    request: RouteEvaluationRequest,
    pipeline: Annotated[BalancedTacticalPipeline, Depends(get_tactical_pipeline)],
) -> RouteEvaluationResponse:
    """
    Evaluate a user-drawn route and suggest tactical positions.

    Process:
    1. Fetch satellite imagery for the route bounds
    2. Draw user's route on the satellite image
    3. Send to Gemini for tactical evaluation
    4. Parse suggested positions and segment analysis
    5. Return annotated image with analysis

    Returns:
        Route evaluation with annotated image and suggested positions
    """
    try:
        # Use client-provided request_id for progress tracking
        progress_id = request.request_id or 'default'

        # Set progress callback for real-time updates
        pipeline.set_progress_callback(
            lambda stage, progress, msg: update_progress(progress_id, stage, progress, msg)
        )
        response = await pipeline.evaluate_user_route(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Route evaluation failed: {str(e)}")


@router.post("/analyze-tactical-simulation", response_model=TacticalSimulationResponse)
async def analyze_tactical_simulation(
    request: TacticalSimulationRequest,
    pipeline: Annotated[BalancedTacticalPipeline, Depends(get_tactical_pipeline)],
) -> TacticalSimulationResponse:
    """
    Analyze a tactical simulation with enemy vision cones and movement routes.

    Process:
    1. Fetch satellite imagery for the simulation bounds
    2. Draw enemy vision cones and movement route on the image
    3. Send to Gemini 3 Flash for tactical analysis
    4. Identify weak spots where route crosses enemy vision
    5. Return annotated image with analysis and recommendations

    Returns:
        Tactical simulation analysis with annotated image, weak spots, and strategy rating
    """
    try:
        # Use client-provided request_id for progress tracking
        progress_id = request.request_id or 'default'

        # Set progress callback for real-time updates
        pipeline.set_progress_callback(
            lambda stage, progress, msg: update_progress(progress_id, stage, progress, msg)
        )
        response = await pipeline.analyze_tactical_simulation(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tactical simulation analysis failed: {str(e)}")
