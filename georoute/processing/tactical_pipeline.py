"""
Tactical planning pipeline orchestrator.
Coordinates data gathering and 4-stage Gemini processing.

Supports AI-powered terrain routing for off-road military operations.
Routes can traverse sand, dirt, grass - not limited to roads.
"""

import uuid
import asyncio
import base64
from datetime import datetime
from typing import Optional, Callable
import io

from ..clients.gemini_tactical import TacticalGeminiClient
from ..clients.google_maps import GoogleMapsClient
from ..clients.openrouteservice import OpenRouteServiceValidator
from ..models.tactical import (
    TacticalPlanRequest,
    TacticalPlanResponse,
    TacticalUnit,
    TacticalRoute,
    DetailedWaypoint,
    RouteSegment,
    RouteScores,
    SimulationResult,
    ClassificationResult,
    RiskLevel,
    RouteVerdict,
    BacklogEntry,
    APICall,
)
from ..storage.backlog import get_backlog_store
from ..utils.geo_validator import GulfRegionValidator
from .terrain_router import TerrainRouter


class TacticalPipeline:
    """
    Orchestrates tactical route planning with 4-stage Gemini pipeline.

    Process:
    1. Gather terrain and satellite data from Google Maps
    2. Generate routes using AI terrain analysis (off-road capable)
    3. Run 4-stage Gemini pipeline for risk assessment
    4. Build color-coded route segments
    5. Store complete audit trail in backlog
    """

    def __init__(
        self,
        gmaps_client: GoogleMapsClient,
        gemini_client: TacticalGeminiClient,
        ors_client: OpenRouteServiceValidator,
        gemini_api_key: str = None,
    ):
        self.gmaps = gmaps_client
        self.gemini = gemini_client
        self.ors = ors_client
        self.api_calls: list[APICall] = []
        self.backlog = get_backlog_store()
        self._progress_callback: Optional[Callable[[str, int, str], None]] = None

        # Initialize terrain router for off-road routing
        self.terrain_router = None
        if gemini_api_key:
            self.terrain_router = TerrainRouter(gemini_api_key)

    def set_progress_callback(self, callback: Callable[[str, int, str], None]):
        """Set callback for progress updates: callback(stage, progress_percent, message)"""
        self._progress_callback = callback

    def _report_progress(self, stage: str, progress: int, message: str):
        """Report progress if callback is set."""
        if self._progress_callback:
            try:
                self._progress_callback(stage, progress, message)
            except Exception:
                pass  # Don't let progress reporting break the pipeline

    def _log_api_call(
        self,
        api_name: str,
        endpoint: str,
        request_params: dict,
        response_data: dict,
        response_status: int = 200,
        duration_seconds: float = 0.0,
    ):
        """Log API call for backlog."""
        self.api_calls.append(
            APICall(
                timestamp=datetime.utcnow(),
                api_name=api_name,
                endpoint=endpoint,
                method="GET",
                request_params=request_params,
                response_status=response_status,
                response_data=response_data,
                duration_seconds=duration_seconds,
            )
        )

    async def _gather_terrain_data(
        self,
        soldiers: list[TacticalUnit],
        enemies: list[TacticalUnit],
        bounds: dict,
    ) -> dict:
        """
        Gather terrain and elevation data from Google Maps.

        Args:
            soldiers: Friendly units
            enemies: Enemy units
            bounds: Map bounds {"north": ..., "south": ..., "east": ..., "west": ...}

        Returns:
            Dict with elevation grid and terrain types
        """
        # Calculate area center
        center_lat = (bounds["north"] + bounds["south"]) / 2
        center_lon = (bounds["east"] + bounds["west"]) / 2

        # Sample elevation at key points (soldiers, enemies, grid)
        sample_points = []

        # Add soldier/enemy positions
        for unit in soldiers + enemies:
            sample_points.append((unit.lat, unit.lon))

        # Add grid samples (10x10 grid)
        lat_step = (bounds["north"] - bounds["south"]) / 10
        lon_step = (bounds["east"] - bounds["west"]) / 10

        for i in range(11):
            for j in range(11):
                lat = bounds["south"] + i * lat_step
                lon = bounds["west"] + j * lon_step
                sample_points.append((lat, lon))

        # Get elevation for all points
        elevation_result = await self.gmaps.get_elevation_at_points(sample_points)

        elevations_data = []
        if elevation_result.get("success"):
            elevations_data = elevation_result["elevations"]

        self._log_api_call(
            api_name="google_maps",
            endpoint="elevation",
            request_params={"locations": sample_points[:5], "total_points": len(sample_points)},
            response_data={"elevations_count": len(elevations_data)},
        )

        # Build terrain data structure
        terrain_data = {
            "center": {"lat": center_lat, "lon": center_lon},
            "bounds": bounds,
            "elevation_samples": [
                {
                    "lat": elev["lat"],
                    "lon": elev["lon"],
                    "elevation_m": elev["elevation_m"],
                }
                for elev in elevations_data
            ],
            "terrain_type": "mixed",  # Could be enhanced with additional APIs
        }

        return terrain_data

    async def _get_satellite_image(self, bounds: dict, zoom: int = 14) -> Optional[str]:
        """
        Get satellite imagery for the tactical area.

        Args:
            bounds: Map bounds
            zoom: Zoom level (11-15 recommended)

        Returns:
            Base64 encoded PNG image
        """
        center_lat = (bounds["north"] + bounds["south"]) / 2
        center_lon = (bounds["east"] + bounds["west"]) / 2

        try:
            image_bytes = await self.gmaps.get_satellite_image(
                center=(center_lat, center_lon), zoom=zoom, size="640x640"
            )

            if image_bytes is None:
                return None

            self._log_api_call(
                api_name="google_maps",
                endpoint="static_maps_satellite",
                request_params={"center": [center_lat, center_lon], "zoom": zoom},
                response_data={"image_size_bytes": len(image_bytes)},
            )

            return base64.b64encode(image_bytes).decode("utf-8")
        except Exception as e:
            # Continue without satellite image if it fails
            return None

    async def _get_terrain_image(self, bounds: dict, zoom: int = 14) -> Optional[str]:
        """
        Get terrain map for the tactical area.

        Args:
            bounds: Map bounds
            zoom: Zoom level

        Returns:
            Base64 encoded PNG image
        """
        center_lat = (bounds["north"] + bounds["south"]) / 2
        center_lon = (bounds["east"] + bounds["west"]) / 2

        try:
            image_bytes = await self.gmaps.get_terrain_image(
                center=(center_lat, center_lon), zoom=zoom
            )

            if image_bytes is None:
                return None

            self._log_api_call(
                api_name="google_maps",
                endpoint="static_maps_terrain",
                request_params={"center": [center_lat, center_lon], "zoom": zoom},
                response_data={"image_size_bytes": len(image_bytes)},
            )

            return base64.b64encode(image_bytes).decode("utf-8")
        except Exception:
            return None

    def _build_route_segments(self, waypoints: list[dict]) -> list[RouteSegment]:
        """
        Build color-coded route segments from waypoints.

        Colors: blue (safe) -> yellow (moderate) -> orange (high) -> red (critical)
        """
        segments = []

        for i in range(len(waypoints) - 1):
            wp = waypoints[i]
            next_wp = waypoints[i + 1]

            risk_level = RiskLevel(wp.get("risk_level", "moderate"))

            # Map risk to color
            color_map = {
                RiskLevel.SAFE: "blue",
                RiskLevel.MODERATE: "yellow",
                RiskLevel.HIGH: "orange",
                RiskLevel.CRITICAL: "red",
            }

            # Calculate segment distance (simplified)
            distance = abs(next_wp.get("distance_from_start_m", 0) - wp.get("distance_from_start_m", 0))

            segments.append(
                RouteSegment(
                    segment_id=i,
                    start_waypoint_idx=i,
                    end_waypoint_idx=i + 1,
                    color=color_map.get(risk_level, "yellow"),
                    risk_level=risk_level,
                    distance_m=distance,
                    estimated_time_seconds=distance / 1.5,  # ~1.5 m/s walking speed
                    risk_factors=[wp.get("reasoning", "")],
                )
            )

        return segments

    async def plan_tactical_attack(
        self, request: TacticalPlanRequest
    ) -> TacticalPlanResponse:
        """
        Execute complete tactical planning pipeline.

        Args:
            request: Tactical planning request with soldiers, enemies, bounds

        Returns:
            Complete tactical plan with 3 routes and classifications
        """
        request_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        # Clear previous logs
        self.api_calls = []
        self.gemini.clear_requests()

        self._report_progress("terrain", 5, "Validating request...")

        # Validate all units are within Gulf region (GCC countries)
        is_valid, validation_msg = GulfRegionValidator.validate_route(
            request.soldiers, request.enemies
        )
        if not is_valid:
            self._report_progress("error", 0, f"Validation failed: {validation_msg}")
            raise ValueError(
                f"Geographic restriction: {validation_msg}. "
                "This system only operates in Gulf Cooperation Council countries: "
                "Saudi Arabia, UAE, Kuwait, Bahrain, Qatar, and Oman."
            )

        # Step 1: Gather terrain data
        self._report_progress("terrain", 10, "Gathering terrain elevation data...")
        terrain_data = await self._gather_terrain_data(
            request.soldiers, request.enemies, request.bounds
        )

        # Step 2: Get images (parallel)
        self._report_progress("imagery", 20, "Fetching satellite and terrain imagery...")
        satellite_task = self._get_satellite_image(request.bounds, zoom=request.zoom or 14)
        terrain_task = self._get_terrain_image(request.bounds, zoom=request.zoom or 14)

        satellite_image, terrain_image = await asyncio.gather(satellite_task, terrain_task)
        self._report_progress("imagery", 30, "Imagery acquired")

        # Step 3: Calculate tactical positions
        # Start position: average of soldier positions
        start_lat = sum(s.lat for s in request.soldiers) / len(request.soldiers)
        start_lon = sum(s.lon for s in request.soldiers) / len(request.soldiers)

        # Target position: average of enemy positions
        target_lat = sum(e.lat for e in request.enemies) / len(request.enemies)
        target_lon = sum(e.lon for e in request.enemies) / len(request.enemies)

        # Step 4: Generate routes using AI-powered terrain analysis
        # This allows off-road routing through sand, dirt, grass - not limited to roads

        stage1_result = None

        # STRICT: Use terrain-based routing ONLY - no ORS fallback
        # Routes go through sand, dirt, grass - NOT roads
        if not self.terrain_router:
            raise ValueError(
                "Terrain router not initialized. "
                "GEMINI_API_KEY is required for off-road terrain routing."
            )

        print("[TacticalPipeline] Using AI terrain router for off-road routing...")
        print(f"[TacticalPipeline] Satellite image available: {satellite_image is not None}")

        # Generate terrain-based routes (works with or without satellite image)
        # Pass zoom level for appropriate building detection area sizing
        self._report_progress("routes", 35, "Detecting buildings from OpenStreetMap...")
        terrain_routes = await self.terrain_router.generate_terrain_routes(
            satellite_image_base64=satellite_image,  # Can be None - will use coordinate-based analysis
            bounds=request.bounds,
            start=(start_lat, start_lon),
            end=(target_lat, target_lon),
            elevation_data=terrain_data.get("elevation_samples", []),
            num_routes=3,
            zoom_level=request.zoom or 14
        )
        self._report_progress("routes", 50, "Off-road routes generated")

        if not terrain_routes or len(terrain_routes) == 0:
            self._report_progress("error", 0, "No routes could be generated")
            raise ValueError("Terrain router failed to generate any routes")

        print(f"[TacticalPipeline] Terrain router generated {len(terrain_routes)} off-road routes")

        self._log_api_call(
            api_name="terrain_router",
            endpoint="generate_terrain_routes",
            request_params={
                "origin": [start_lat, start_lon],
                "destination": [target_lat, target_lon],
                "routing_mode": "off-road-terrain",
            },
            response_data={
                "routes_count": len(terrain_routes),
                "terrain_types": [r.terrain_distribution for r in terrain_routes],
            },
        )

        # Convert terrain routes to stage1 format
        stage1_result = {
            "routes": [
                {
                    "route_id": route.route_id,
                    "name": route.name,
                    "description": f"{route.description} (Terrain: {', '.join(route.terrain_distribution.keys())})",
                    "waypoints": route.waypoints,
                }
                for route in terrain_routes
            ]
        }

        # Ensure all waypoints have required fields
        for route in stage1_result["routes"]:
            for wp in route["waypoints"]:
                if "elevation_m" not in wp:
                    wp["elevation_m"] = 0.0
                if "terrain_type" not in wp:
                    wp["terrain_type"] = wp.get("terrain", "unknown")

        # Step 6: Gemini assesses risk for each waypoint with LOS analysis
        # Pass satellite image for visual line-of-sight assessment
        self._report_progress("risk", 55, "AI analyzing tactical risks...")
        stage2_result = await self.gemini.stage2_refine_waypoints(
            stage1_routes=stage1_result,
            detailed_elevation=terrain_data,
            enemies=request.enemies,
            satellite_image_base64=satellite_image,  # For visual LOS analysis
        )
        self._report_progress("risk", 70, "Risk assessment complete")

        # Stage 3: Score routes
        self._report_progress("scoring", 75, "Calculating route scores...")
        stage3_result = await self.gemini.stage3_score_routes(
            stage2_routes=stage2_result,
            enemies=request.enemies,
        )
        self._report_progress("scoring", 85, "Scores calculated")

        # Stage 4: Final classification
        self._report_progress("classification", 90, "Final classification in progress...")
        stage4_result = await self.gemini.stage4_final_classification(
            stage3_routes=stage3_result,
            stage2_routes=stage2_result,
            enemies=request.enemies,
        )
        self._report_progress("classification", 95, "Classification complete")

        # Step 4: Build TacticalRoute objects
        tactical_routes = []

        for route_data in stage4_result.get("routes", []):
            route_id = route_data["route_id"]

            # Find matching route from stage2 (detailed waypoints)
            stage2_route = next(
                (r for r in stage2_result["routes"] if r["route_id"] == route_id),
                None,
            )

            # Find matching route from stage3 (scores)
            stage3_route = next(
                (r for r in stage3_result["routes"] if r["route_id"] == route_id),
                None,
            )

            if not stage2_route or not stage3_route:
                continue

            # Build waypoints
            waypoints = [
                DetailedWaypoint(
                    lat=wp["lat"],
                    lon=wp["lon"],
                    elevation_m=wp.get("elevation_m", 0.0),
                    distance_from_start_m=wp.get("distance_from_start_m", 0.0),
                    terrain_type=wp.get("terrain_type", "unknown"),
                    risk_level=RiskLevel(wp.get("risk_level", "moderate")),
                    reasoning=wp.get("reasoning", ""),
                    tactical_note=wp.get("tactical_note"),
                )
                for wp in stage2_route["waypoints"]
            ]

            # Build segments
            segments = self._build_route_segments(stage2_route["waypoints"])

            # Build scores
            scores_data = stage3_route["scores"]
            scores = RouteScores(
                time_to_target=scores_data["time_to_target"],
                stealth_score=scores_data["stealth_score"],
                survival_probability=scores_data["survival_probability"],
                overall_score=scores_data["overall_score"],
            )

            # Build simulation
            sim_data = route_data["classification"]["simulation"]

            # Validate detection_points (Gemini sometimes returns wrong type)
            detection_points_data = sim_data.get("detection_points", [])
            if not isinstance(detection_points_data, list):
                detection_points_data = []

            # Validate each point is iterable (list/tuple with 2 elements)
            validated_points = []
            for pt in detection_points_data:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    validated_points.append(tuple(pt[:2]))  # Take first 2 elements as (lat, lon)

            simulation = SimulationResult(
                detected=sim_data["detected"],
                detection_probability=sim_data["detection_probability"],
                detection_points=validated_points,
                safe_percentage=sim_data["safe_percentage"],
            )

            # Build classification
            class_data = route_data["classification"]
            classification = ClassificationResult(
                gemini_evaluation=RouteVerdict(class_data["gemini_evaluation"]),
                gemini_reasoning=class_data["gemini_reasoning"],
                scores=scores,
                simulation=simulation,
                final_verdict=RouteVerdict(class_data["final_verdict"]),
                final_reasoning=class_data["final_reasoning"],
                confidence=class_data["confidence"],
            )

            # Calculate total distance
            total_distance = sum(seg.distance_m for seg in segments)
            total_duration = sum(seg.estimated_time_seconds for seg in segments)

            # Calculate elevation gain/loss from waypoints
            elevation_gain = 0.0
            elevation_loss = 0.0
            for i in range(len(waypoints) - 1):
                elev_diff = waypoints[i + 1].elevation_m - waypoints[i].elevation_m
                if elev_diff > 0:
                    elevation_gain += elev_diff
                else:
                    elevation_loss += abs(elev_diff)

            # Build complete route
            tactical_route = TacticalRoute(
                route_id=route_id,
                name=route_data["name"],
                description=route_data.get("description", ""),
                waypoints=waypoints,
                segments=segments,
                classification=classification,
                total_distance_m=total_distance,
                estimated_duration_seconds=total_duration,
                elevation_gain_m=elevation_gain,
                elevation_loss_m=elevation_loss,
            )

            tactical_routes.append(tactical_route)

        # Step 5: Build response
        # Determine recommended route (highest overall score with success verdict, or highest score)
        recommended_id = 1
        best_score = -1.0
        for route in tactical_routes:
            if route.classification.final_verdict == RouteVerdict.SUCCESS:
                if route.classification.scores.overall_score > best_score:
                    best_score = route.classification.scores.overall_score
                    recommended_id = route.route_id

        # If no success routes, pick highest scoring route
        if best_score == -1.0:
            for route in tactical_routes:
                if route.classification.scores.overall_score > best_score:
                    best_score = route.classification.scores.overall_score
                    recommended_id = route.route_id

        # Collect key risks from all routes
        all_risks = []
        for route in tactical_routes:
            if route.classification.final_verdict in [RouteVerdict.RISK, RouteVerdict.FAILED]:
                all_risks.append(f"{route.name}: {route.classification.final_reasoning[:100]}")

        # Generate overall assessment
        success_count = sum(1 for r in tactical_routes if r.classification.final_verdict == RouteVerdict.SUCCESS)
        if success_count == 3:
            assessment = "All routes viable. Mission has high probability of success."
        elif success_count > 0:
            assessment = f"{success_count} of 3 routes viable. Proceed with caution on recommended route."
        else:
            assessment = "No fully viable routes. Mission carries significant risk."

        response = TacticalPlanResponse(
            request_id=request_id,
            timestamp=start_time,
            soldiers_count=len(request.soldiers),
            enemies_count=len(request.enemies),
            no_go_zones_count=0,  # TODO: Add no-go zones support
            routes=tactical_routes,
            recommended_route_id=recommended_id,
            mission_assessment=assessment,
            key_risks=all_risks[:5],  # Top 5 risks
            recommendations=[
                f"Use Route {recommended_id} ({tactical_routes[recommended_id-1].name})",
                "Maintain tactical spacing between units",
                "Monitor enemy patrol patterns",
            ],
        )

        # Step 6: Store in backlog
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        gemini_requests = self.gemini.get_gemini_requests()

        backlog_entry = BacklogEntry(
            request_id=request_id,
            timestamp=start_time,
            user_input=request,
            api_calls=self.api_calls,
            gemini_pipeline=gemini_requests,
            satellite_image=satellite_image,
            terrain_image=terrain_image,
            result=response,
            total_duration_seconds=duration,
            total_api_calls=len(self.api_calls),
            total_gemini_requests=len(gemini_requests),
        )

        self.backlog.add_entry(backlog_entry)

        self._report_progress("complete", 100, "Tactical plan ready!")
        return response
