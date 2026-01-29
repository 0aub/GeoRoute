"""
Military Route Optimization API - Entry Point

This module initializes the FastAPI application with strict configuration
validation and API health checks on startup.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import load_config, ConfigurationError
from .processing.balanced_tactical_pipeline import BalancedTacticalPipeline
from .api.routes import router, set_pipeline
from .api.tactical import router as tactical_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - startup and shutdown."""
    # Startup
    logger.info("=" * 60)
    logger.info("MILITARY ROUTE OPTIMIZATION API - STARTING")
    logger.info("=" * 60)

    try:
        # Load configuration (will fail fast if env vars missing)
        config = load_config()
        logger.info("Configuration loaded successfully")

        # Log which APIs are configured
        api_status = config.validate_apis()
        for api, available in api_status.items():
            status = "CONFIGURED" if available else "NOT CONFIGURED"
            logger.info(f"  {api}: {status}")

        # Initialize pipeline with SAM support
        pipeline = BalancedTacticalPipeline(config)
        set_pipeline(pipeline)
        logger.info("Pipeline initialized")

        # Test API connectivity
        logger.info("Testing API connectivity...")
        test_results = await pipeline.test_all_apis()

        all_required_ok = test_results.get("google_maps") and test_results.get("gemini")

        for api, ok in test_results.items():
            status = "OK" if ok else "FAILED"
            logger.info(f"  {api}: {status}")

        if not all_required_ok:
            logger.error("Required APIs (google_maps, gemini) are not responding!")
            logger.error("Please check your API keys and network connectivity.")
            # Don't exit - let the app run but log the warning

        logger.info("=" * 60)
        logger.info(f"Server ready on {config.backend_host}:{config.backend_port}")
        logger.info("=" * 60)

        # Store config and pipeline in app state
        app.state.config = config
        app.state.pipeline = pipeline

        yield

    except ConfigurationError as e:
        logger.error("=" * 60)
        logger.error("CONFIGURATION ERROR")
        logger.error("=" * 60)
        logger.error(str(e))
        logger.error("")
        logger.error("Please ensure all required environment variables are set.")
        logger.error("See .env.example for required variables.")
        logger.error("=" * 60)
        sys.exit(1)

    # Shutdown
    logger.info("Shutting down...")
    if hasattr(app.state, "pipeline"):
        await app.state.pipeline.close()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Load config early to get CORS origins (will fail if config is invalid)
    try:
        config = load_config()
    except ConfigurationError:
        # Let lifespan handle the error with better messaging
        config = None

    app = FastAPI(
        title="Military Route Optimization API",
        description="Terrain-aware route planning using Gemini AI",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    if config:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        # Fallback for startup - will be reconfigured or exit
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include API routes
    app.include_router(router, prefix="/api")  # Legacy routes
    app.include_router(tactical_router)  # Tactical routes (already have /api prefix)

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    # Load config to get port
    config = load_config()

    uvicorn.run(
        "georoute.main:app",
        host=config.backend_host,
        port=config.backend_port,
        reload=False,
    )
