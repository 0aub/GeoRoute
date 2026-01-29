"""FastAPI route definitions - Health and utility endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends

from ..processing.balanced_tactical_pipeline import BalancedTacticalPipeline

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get pipeline instance (set in main.py)
_pipeline: BalancedTacticalPipeline = None


def get_pipeline() -> BalancedTacticalPipeline:
    """Get the pipeline instance."""
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    return _pipeline


def set_pipeline(pipeline: BalancedTacticalPipeline):
    """Set the pipeline instance (called from main.py)."""
    global _pipeline
    _pipeline = pipeline


@router.get("/health")
async def health_check(pipeline: Annotated[BalancedTacticalPipeline, Depends(get_pipeline)]):
    """Health check endpoint - does NOT test APIs to preserve rate limits."""
    return {
        "status": "ok",
        "message": "Pipeline initialized",
    }
