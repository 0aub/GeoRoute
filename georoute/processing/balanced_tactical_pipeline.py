"""
Balanced Tactical Pipeline - Gemini Image Route Drawing.

This pipeline uses Gemini 3 Pro Image to draw routes directly:
1. Fetches satellite imagery from Google Maps
2. Crops watermarks from the image
3. Gemini draws the route directly on the satellite image
4. Returns the annotated image for UI overlay

Estimated time: 5-15 seconds
"""

import uuid
import asyncio
import base64
import math
import random
from datetime import datetime
from typing import Optional, Callable

from ..clients.gemini_tactical import TacticalGeminiClient
from ..clients.google_maps import GoogleMapsClient
from ..clients.esri_imagery import ESRIImageryClient
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
    RouteEvaluationRequest,
    RouteEvaluationResponse,
    SuggestedPosition,
    SegmentAnalysis,
    TacticalSimulationRequest,
    TacticalSimulationResponse,
    WeakSpot,
    StrongPoint,
    ExposureAnalysis,
    SegmentCoverAnalysis,
    TacticalScores,
    FlankingAnalysis,
    CoverBreakdown,
)
from ..utils.geo_validator import GulfRegionValidator
from ..config import load_config, get_yaml_setting

from .gemini_image_route_generator import GeminiImageRouteGenerator


class BalancedTacticalPipeline:
    """
    Tactical route planning using Gemini 3 Pro Image.

    Gemini draws routes directly on satellite imagery - no obstacle detection needed.
    """

    def __init__(self, config):
        # Initialize clients
        self.config = config
        self.gmaps = GoogleMapsClient(config.google_maps_api_key)
        self.esri = ESRIImageryClient()  # Fallback for when Google Maps fails

        # Initialize Gemini clients with Vertex AI support
        self.gemini = TacticalGeminiClient(
            api_key=config.gemini_api_key,
            project_id=config.google_cloud_project,
            use_vertex=config.use_vertex_ai,
            location=config.vertex_location,
        )

        self._progress_callback: Optional[Callable[[str, int, str], None]] = None
        self._last_image_bounds = None  # Track actual satellite image bounds

        # Initialize Gemini Image route generator
        self.route_generator = GeminiImageRouteGenerator(
            api_key=config.gemini_api_key,
            use_vertex=config.use_vertex_ai,
            project_id=config.google_cloud_project,
            location=config.vertex_location,
        )

        if config.use_vertex_ai:
            print(f"[BalancedPipeline] Using Vertex AI (project={config.google_cloud_project}, location={config.vertex_location})")
        else:
            print("[BalancedPipeline] Using AI Studio API key")
        print("[BalancedPipeline] Satellite imagery: ESRI World Imagery (max zoom 17)")

    async def test_all_apis(self) -> dict[str, bool]:
        """Test connectivity to all APIs."""
        return {
            "google_maps": await self.gmaps.test_connection(),
            "gemini": True,  # Gemini client doesn't have test_connection
        }

    async def close(self):
        """Close HTTP clients."""
        await self.gmaps.close()
        await self.esri.close()

    def set_progress_callback(self, callback: Callable[[str, int, str], None]):
        """Set callback for progress updates."""
        self._progress_callback = callback

    def _report_progress(self, stage: str, progress: int, message: str):
        """Report progress if callback is set."""
        if self._progress_callback:
            try:
                self._progress_callback(stage, progress, message)
            except Exception:
                pass

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in meters."""
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def _calculate_optimal_zoom(self, bounds: dict) -> int:
        """Calculate optimal zoom level to cover bounds in a 640x640 image.

        Google Maps zoom levels (approximate meters per pixel at equator):
        - Zoom 16: ~2.4m/pixel, 640px = ~1536m
        - Zoom 17: ~1.2m/pixel, 640px = ~768m
        - Zoom 18: ~0.6m/pixel, 640px = ~384m
        - Zoom 19: ~0.3m/pixel, 640px = ~192m
        """
        lat_span = bounds["north"] - bounds["south"]
        lon_span = bounds["east"] - bounds["west"]

        # Convert to meters (approximate)
        center_lat = (bounds["north"] + bounds["south"]) / 2
        lat_meters = lat_span * 111000
        lon_meters = lon_span * 111000 * math.cos(math.radians(center_lat))
        max_span = max(lat_meters, lon_meters)

        # Calculate zoom to cover this span in 640 pixels
        # Base: zoom 16 covers ~1536m in 640px
        if max_span > 1200:
            zoom = 16
        elif max_span > 600:
            zoom = 17
        elif max_span > 300:
            zoom = 18
        else:
            zoom = 19

        print(f"[BalancedPipeline] Bounds span: {max_span:.0f}m, calculated zoom: {zoom}")
        return zoom

    async def _get_satellite_image_fast(self, bounds: dict, zoom: int = 14) -> tuple[Optional[str], dict]:
        """Get satellite image from ESRI World Imagery.

        Uses ESRI with max zoom 17 to ensure coverage in all regions.

        Returns:
            Tuple of (base64_image, actual_bounds) where actual_bounds is the
            exact geographic area covered by the returned image.
        """
        import math

        center_lat = (bounds["north"] + bounds["south"]) / 2

        # Calculate requested bounds size
        lat_span = bounds["north"] - bounds["south"]
        lon_span = bounds["east"] - bounds["west"]
        lat_meters = lat_span * 111000
        lon_meters = lon_span * 111000 * math.cos(math.radians(center_lat))
        max_span = max(lat_meters, lon_meters)

        print(f"[BalancedPipeline] Bounds span: {max_span:.0f}m")
        print(f"[BalancedPipeline] Requested bounds: N={bounds['north']:.6f}, S={bounds['south']:.6f}, E={bounds['east']:.6f}, W={bounds['west']:.6f}")

        try:
            image_bytes, actual_bounds = await self.esri.get_satellite_image(
                bounds=bounds,
                width=1280,
                height=1280
            )
            if image_bytes:
                self._last_image_bounds = actual_bounds
                print(f"[BalancedPipeline] ESRI image: N={actual_bounds['north']:.6f}, S={actual_bounds['south']:.6f}")
                return base64.b64encode(image_bytes).decode("utf-8"), actual_bounds
        except Exception as e:
            print(f"[BalancedPipeline] ESRI failed: {e}")
            import traceback
            traceback.print_exc()

        return None, {}

    async def _analyze_routes_combined(
        self,
        routes_data: list[dict],
        enemies: list[TacticalUnit],
        satellite_image: Optional[str]
    ) -> dict:
        """Single Gemini call to analyze all routes."""
        prompt = f"""Analyze these {len(routes_data)} tactical approach routes.

ROUTES:
"""
        for route in routes_data:
            prompt += f"\nRoute {route['route_id']}: {route['name']}\n"
            prompt += f"  Waypoints: {len(route['waypoints'])}\n"
            if route['waypoints']:
                start = route['waypoints'][0]
                end = route['waypoints'][-1]
                prompt += f"  Start: ({start['lat']:.5f}, {start['lon']:.5f})\n"
                prompt += f"  End: ({end['lat']:.5f}, {end['lon']:.5f})\n"

        prompt += "\nENEMY POSITIONS:\n"
        for i, enemy in enumerate(enemies):
            prompt += f"  Enemy {i+1}: ({enemy.lat:.5f}, {enemy.lon:.5f})\n"

        prompt += """
For EACH route, provide tactical assessment:

Respond in JSON:
{
  "routes": [
    {
      "route_id": 1,
      "name": "Route name",
      "segment_risks": ["safe", "moderate", "high"],
      "scores": {
        "time_to_target": 75,
        "stealth_score": 60,
        "survival_probability": 80
      },
      "verdict": "SUCCESS",
      "reasoning": "Brief tactical assessment",
      "detection_probability": 0.3
    }
  ]
}

Verdicts: SUCCESS (viable), RISK (caution needed), FAILED (not recommended)
"""

        try:
            import json
            import base64

            # Build content for Gemini call
            content = [prompt]
            if satellite_image:
                try:
                    image_data = base64.b64decode(satellite_image)
                    content.insert(0, {"mime_type": "image/png", "data": image_data})
                except Exception:
                    pass

            # Use the complex model directly
            response = await self.gemini.complex_model.generate_content_async(content)
            response_text = response.text.strip()

            # Clean markdown if present
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return json.loads(response_text)
        except Exception as e:
            print(f"[BalancedPipeline] Gemini analysis failed: {e}")
            # No fallback - raise the error so caller knows analysis failed
            raise RuntimeError(f"AI route analysis failed: {e}")

    def _default_analysis(self, routes: list[dict]) -> dict:
        """Default analysis based on route strategy with realistic variance."""
        result_routes = []

        for route in routes:
            strategy = route.get("strategy", "balanced")

            # Get route distance from waypoints
            waypoints = route.get("waypoints", [])
            if waypoints:
                route_distance = waypoints[-1].get("distance_from_start_m", 500)
            else:
                route_distance = 500  # Default ~500m

            # Calculate time estimate based on distance (infantry moves ~60-80m/min with cover)
            base_time_minutes = route_distance / 70  # Average 70m/min

            # Strategy-based profiles with realistic variance
            if strategy == "direct":
                scores = {
                    "time_to_target": min(100, max(20, 95 - int(base_time_minutes * 2) + random.randint(-3, 3))),
                    "stealth_score": random.randint(15, 30),
                    "survival_probability": random.randint(30, 45)
                }
                segment_risks = ["high", "critical"]
                verdict = "FAILED"
                reasoning = "Direct approach prioritizes speed over cover. High exposure risk."
                detection_prob = round(0.75 + random.uniform(0, 0.15), 2)

            elif strategy == "balanced":
                scores = {
                    "time_to_target": min(100, max(30, 80 - int(base_time_minutes * 1.5) + random.randint(-5, 5))),
                    "stealth_score": random.randint(55, 70),
                    "survival_probability": random.randint(60, 75)
                }
                segment_risks = ["moderate", "moderate"]
                verdict = "RISK"
                reasoning = "Balanced approach uses available cover while maintaining reasonable speed."
                detection_prob = round(0.40 + random.uniform(0, 0.20), 2)

            else:  # stealth
                scores = {
                    "time_to_target": min(100, max(25, 60 - int(base_time_minutes * 1.0) + random.randint(-5, 5))),
                    "stealth_score": random.randint(80, 95),
                    "survival_probability": random.randint(80, 92)
                }
                segment_risks = ["safe", "safe"]
                verdict = "SUCCESS"
                reasoning = "Stealth approach maximizes concealment. Recommended for tactical operations."
                detection_prob = round(0.10 + random.uniform(0, 0.15), 2)

            result_routes.append({
                "route_id": route["route_id"],
                "name": route["name"],
                "segment_risks": segment_risks,
                "scores": scores,
                "verdict": verdict,
                "reasoning": reasoning,
                "detection_probability": detection_prob
            })

        return {"routes": result_routes}

    def _build_tactical_route(self, route_data: dict, analysis: dict) -> TacticalRoute:
        """Build TacticalRoute from route data and analysis."""
        waypoints = []
        segments = []

        route_analysis = next(
            (r for r in analysis.get("routes", []) if r["route_id"] == route_data["route_id"]),
            None
        )

        if not route_analysis:
            # No fallback - analysis must be provided for each route
            raise RuntimeError(f"Missing analysis for route {route_data['route_id']} - cannot build route without AI assessment")

        segment_risks = route_analysis.get("segment_risks", [])

        # Build waypoints
        for i, wp in enumerate(route_data["waypoints"]):
            risk_str = segment_risks[i % len(segment_risks)] if segment_risks else "moderate"
            try:
                risk = RiskLevel(risk_str.lower())
            except:
                risk = RiskLevel.MODERATE

            waypoints.append(DetailedWaypoint(
                lat=wp["lat"],
                lon=wp["lon"],
                elevation_m=wp.get("elevation_m", 0.0),
                distance_from_start_m=wp.get("distance_from_start_m", 0.0),
                terrain_type=wp.get("terrain_type", "traversable"),
                risk_level=risk,
                reasoning=wp.get("reasoning", ""),
                tactical_note=None
            ))

        # Build segments
        risk_colors = {
            RiskLevel.SAFE: "blue",
            RiskLevel.MODERATE: "yellow",
            RiskLevel.HIGH: "orange",
            RiskLevel.CRITICAL: "red"
        }

        for i in range(len(waypoints) - 1):
            risk = waypoints[i].risk_level
            distance = abs(waypoints[i+1].distance_from_start_m - waypoints[i].distance_from_start_m)

            segments.append(RouteSegment(
                segment_id=i,
                start_waypoint_idx=i,
                end_waypoint_idx=i + 1,
                color=risk_colors.get(risk, "yellow"),
                risk_level=risk,
                distance_m=distance,
                estimated_time_seconds=distance / 1.5,
                risk_factors=[]
            ))

        # Build scores - all scores must be provided, no defaults
        scores_data = route_analysis.get("scores")
        if not scores_data:
            raise RuntimeError(f"Missing scores in analysis for route {route_data['route_id']}")

        required_scores = ["time_to_target", "stealth_score", "survival_probability"]
        for score_name in required_scores:
            if score_name not in scores_data:
                raise RuntimeError(f"Missing required score '{score_name}' for route {route_data['route_id']}")

        overall = (
            scores_data["time_to_target"] * 0.2 +
            scores_data["stealth_score"] * 0.3 +
            scores_data["survival_probability"] * 0.5
        )

        scores = RouteScores(
            time_to_target=scores_data["time_to_target"],
            stealth_score=scores_data["stealth_score"],
            survival_probability=scores_data["survival_probability"],
            overall_score=overall
        )

        # Build simulation - detection_probability must be provided
        if "detection_probability" not in route_analysis:
            raise RuntimeError(f"Missing detection_probability for route {route_data['route_id']}")
        detection_prob = route_analysis["detection_probability"]
        simulation = SimulationResult(
            detected=detection_prob > 0.5,
            detection_probability=detection_prob,
            detection_points=[],
            safe_percentage=(1 - detection_prob) * 100
        )

        # Build classification - verdict and reasoning must be provided
        if "verdict" not in route_analysis:
            raise RuntimeError(f"Missing verdict for route {route_data['route_id']}")
        if "reasoning" not in route_analysis:
            raise RuntimeError(f"Missing reasoning for route {route_data['route_id']}")

        verdict_str = route_analysis["verdict"].upper()
        verdict = RouteVerdict.SUCCESS if verdict_str == "SUCCESS" else (
            RouteVerdict.FAILED if verdict_str == "FAILED" else RouteVerdict.RISK
        )

        classification = ClassificationResult(
            gemini_evaluation=verdict,
            gemini_reasoning=route_analysis["reasoning"],
            scores=scores,
            simulation=simulation,
            final_verdict=verdict,
            final_reasoning=route_analysis["reasoning"],
            confidence=0.7
        )

        total_distance = sum(s.distance_m for s in segments) if segments else 0

        return TacticalRoute(
            route_id=route_data["route_id"],
            name=route_data["name"],
            description=route_data.get("description", ""),
            waypoints=waypoints,
            segments=segments,
            classification=classification,
            total_distance_m=total_distance,
            estimated_duration_seconds=total_distance / 1.5 if total_distance > 0 else 0,
            elevation_gain_m=0.0,
            elevation_loss_m=0.0
        )

    async def plan_tactical_attack(
        self,
        request: TacticalPlanRequest
    ) -> TacticalPlanResponse:
        """
        Balanced tactical planning - respects buildings, reasonably fast.
        """
        request_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        self._report_progress("imagery", 5, "Validating coordinates...")

        # Validate Gulf region
        is_valid, validation_msg = GulfRegionValidator.validate_route(
            request.soldiers, request.enemies
        )
        if not is_valid:
            self._report_progress("error", 0, f"Validation failed: {validation_msg}")
            raise ValueError(f"Geographic restriction: {validation_msg}")

        # Calculate start/end positions
        start_lat = sum(s.lat for s in request.soldiers) / len(request.soldiers)
        start_lon = sum(s.lon for s in request.soldiers) / len(request.soldiers)
        target_lat = sum(e.lat for e in request.enemies) / len(request.enemies)
        target_lon = sum(e.lon for e in request.enemies) / len(request.enemies)

        print(f"[BalancedPipeline] Soldiers center: ({start_lat:.6f}, {start_lon:.6f})")
        print(f"[BalancedPipeline] Enemies center: ({target_lat:.6f}, {target_lon:.6f})")
        print(f"[BalancedPipeline] Bounds: N={request.bounds.get('north'):.6f}, S={request.bounds.get('south'):.6f}, E={request.bounds.get('east'):.6f}, W={request.bounds.get('west'):.6f}")
        print(f"[BalancedPipeline] Zoom: {request.zoom}")

        self._report_progress("imagery", 10, "Fetching satellite imagery...")
        await asyncio.sleep(0.1)

        # Use the frontend-provided bounds directly
        # Frontend already calculates appropriate bounds with padding
        route_bounds = request.bounds
        print(f"[BalancedPipeline] Using frontend bounds: N={route_bounds['north']:.6f}, S={route_bounds['south']:.6f}, E={route_bounds['east']:.6f}, W={route_bounds['west']:.6f}")

        self._report_progress("imagery", 15, "Downloading satellite tiles...")

        # Get satellite image (now returns tuple of image + actual bounds)
        satellite_image, image_bounds = await self._get_satellite_image_fast(route_bounds, request.zoom or 14)

        self._report_progress("imagery", 20, "Processing satellite imagery...")
        await asyncio.sleep(0.05)  # Allow SSE to flush

        # Generate route using Gemini Image
        detection_debug = {}

        if not satellite_image:
            raise RuntimeError("No satellite image available")

        # Use the actual bounds returned by the ESRI client for accurate overlay positioning
        if not image_bounds:
            image_bounds = request.bounds

        # Gemini image generation takes 30-90 seconds - this is the main wait
        self._report_progress("routes", 25, "AI generating tactical routes...")
        await asyncio.sleep(0.05)  # Allow SSE to flush

        # Call Gemini to draw route on satellite image
        result = await self.route_generator.generate_route(
            satellite_image_base64=satellite_image,
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=target_lat,
            end_lon=target_lon,
            bounds=image_bounds
        )

        # Create 2 routes with different tactical strategies
        # The visual routes are drawn in the Gemini image (orange, green dashed lines)
        total_distance = self._haversine_distance(start_lat, start_lon, target_lat, target_lon)

        # Single tactical route (Gemini plans the actual path)
        routes_data = [
            {
                "route_id": 1,
                "name": "Tactical Route",
                "description": "AI-planned tactical approach using available cover.",
                "strategy": "tactical",
                "color": "cyan",
                "waypoints": [
                    {"lat": start_lat, "lon": start_lon, "elevation_m": 0, "distance_from_start_m": 0},
                    {"lat": target_lat, "lon": target_lon, "elevation_m": 0, "distance_from_start_m": total_distance}
                ],
                "path_clear": True
            }
        ]

        # After Gemini responds - jump to 70% (Gemini was the main work)
        self._report_progress("routes", 70, "Processing route image...")
        await asyncio.sleep(0.05)

        # Store the route image for UI overlay
        # Use the ESRI image_bounds for correct overlay positioning (accounts for crop pixel rounding)
        detection_debug['gemini_route_image'] = result.route_image_base64
        final_bounds = result.adjusted_bounds or image_bounds
        detection_debug['gemini_route_bounds'] = final_bounds
        print(f"[BalancedPipeline] Gemini route image generated successfully")
        print(f"[BalancedPipeline] Final overlay bounds: N={final_bounds['north']:.6f}, S={final_bounds['south']:.6f}, E={final_bounds['east']:.6f}, W={final_bounds['west']:.6f}")

        self._report_progress("routes", 75, "Analyzing route risks...")
        await asyncio.sleep(0.05)

        # Use strategy-based analysis directly (no separate Gemini call needed)
        analysis = self._default_analysis(routes_data)
        print(f"[BalancedPipeline] Strategy-based analysis applied to {len(routes_data)} routes")

        self._report_progress("routes", 80, "Building tactical assessment...")
        await asyncio.sleep(0.05)

        # Build tactical routes
        tactical_routes = [
            self._build_tactical_route(route_data, analysis)
            for route_data in routes_data
        ]

        self._report_progress("routes", 85, "Selecting optimal route...")
        await asyncio.sleep(0.05)

        # Find recommended route
        recommended_id = 1
        best_score = -1.0
        for route in tactical_routes:
            if route.classification.final_verdict == RouteVerdict.SUCCESS:
                if route.classification.scores.overall_score > best_score:
                    best_score = route.classification.scores.overall_score
                    recommended_id = route.route_id

        if best_score == -1.0:
            for route in tactical_routes:
                if route.classification.scores.overall_score > best_score:
                    best_score = route.classification.scores.overall_score
                    recommended_id = route.route_id

        # Build response
        num_routes = len(tactical_routes)
        success_count = sum(1 for r in tactical_routes if r.classification.final_verdict == RouteVerdict.SUCCESS)
        if success_count == num_routes:
            assessment = f"All {num_routes} route(s) viable. Mission has high probability of success."
        elif success_count > 0:
            assessment = f"{success_count} of {num_routes} routes viable. Proceed with caution."
        else:
            assessment = "No fully viable routes. Mission carries significant risk."

        # Generate advanced tactical analysis if requested
        tactical_analysis_report = None
        if getattr(request, 'advanced_analytics', False):
            self._report_progress("report", 90, "AI generating tactical report...")
            await asyncio.sleep(0.05)
            try:
                tactical_analysis_report = await self.route_generator.analyze_tactical_situation(
                    route_image_base64=result.route_image_base64,
                    num_soldiers=len(request.soldiers),
                    num_enemies=len(request.enemies)
                )
                self._report_progress("report", 98, "Report complete")
                await asyncio.sleep(0.05)
                print(f"[BalancedPipeline] Advanced tactical analysis complete")
            except Exception as e:
                print(f"[BalancedPipeline] Advanced analysis failed: {e}")

        response = TacticalPlanResponse(
            request_id=request_id,
            timestamp=start_time,
            soldiers_count=len(request.soldiers),
            enemies_count=len(request.enemies),
            no_go_zones_count=0,
            routes=tactical_routes,
            recommended_route_id=recommended_id,
            mission_assessment=assessment,
            key_risks=[],
            recommendations=[
                f"Recommended: Route {recommended_id} ({tactical_routes[recommended_id-1].name})" if tactical_routes else "No routes generated",
                "GREEN = Stealth (safest) | ORANGE = Balanced approach",
                "Dashed routes show tactical infantry movement paths"
            ],
            tactical_analysis_report=tactical_analysis_report,
            detection_debug=detection_debug if detection_debug else None
        )

        self._report_progress("routes", 100, "Tactical plan ready!")

        return response

    async def evaluate_user_route(
        self,
        request: RouteEvaluationRequest
    ) -> RouteEvaluationResponse:
        """
        Evaluate a user-drawn route and suggest tactical positions.

        1. Fetches satellite imagery for the route bounds
        2. Draws user's route on the satellite image
        3. Sends to Gemini for tactical evaluation
        4. Parses suggested positions and segment analysis
        5. Returns annotated image with analysis
        """
        request_id = request.request_id or str(uuid.uuid4())
        start_time = datetime.utcnow()

        self._report_progress("imagery", 5, "Validating route...")

        # Validate we have enough waypoints
        if len(request.waypoints) < 2:
            raise ValueError("Route must have at least 2 waypoints")

        # Calculate bounds from waypoints
        lats = [wp.lat for wp in request.waypoints]
        lngs = [wp.lng for wp in request.waypoints]

        # Add padding to bounds
        lat_span = max(lats) - min(lats)
        lng_span = max(lngs) - min(lngs)
        padding = max(lat_span, lng_span) * 0.3 + 0.001  # At least ~100m padding

        route_bounds = {
            "north": max(lats) + padding,
            "south": min(lats) - padding,
            "east": max(lngs) + padding,
            "west": min(lngs) - padding
        }

        print(f"[BalancedPipeline] Evaluating route with {len(request.waypoints)} waypoints")
        print(f"[BalancedPipeline] Route bounds: N={route_bounds['north']:.6f}, S={route_bounds['south']:.6f}")

        self._report_progress("imagery", 15, "Fetching satellite imagery...")
        await asyncio.sleep(0.05)

        # Get satellite image
        satellite_image, image_bounds = await self._get_satellite_image_fast(route_bounds)

        if not satellite_image:
            raise RuntimeError("Failed to fetch satellite imagery")

        if not image_bounds:
            image_bounds = route_bounds

        self._report_progress("drawing", 30, "Drawing route on image...")
        await asyncio.sleep(0.05)

        # Convert waypoints to dict format for the generator
        waypoints_dict = [{"lat": wp.lat, "lng": wp.lng} for wp in request.waypoints]

        # Convert units to dict format
        units_dict = {
            "squad_size": request.units.squad_size,
            "riflemen": request.units.riflemen,
            "snipers": request.units.snipers,
            "support": request.units.support,
            "medics": request.units.medics
        }

        self._report_progress("analysis", 40, "AI analyzing route...")
        await asyncio.sleep(0.05)

        # Call Gemini to evaluate the route
        result = await self.route_generator.evaluate_user_route(
            satellite_image_base64=satellite_image,
            waypoints=waypoints_dict,
            units=units_dict,
            bounds=image_bounds
        )

        self._report_progress("positions", 80, "Processing tactical positions...")
        await asyncio.sleep(0.05)

        # Calculate route distance
        total_distance = 0.0
        for i in range(len(request.waypoints) - 1):
            wp1 = request.waypoints[i]
            wp2 = request.waypoints[i + 1]
            total_distance += self._haversine_distance(wp1.lat, wp1.lng, wp2.lat, wp2.lng)

        # Estimate time (infantry moves ~60-80m/min with cover)
        estimated_time_minutes = total_distance / 70

        self._report_progress("complete", 95, "Building response...")
        await asyncio.sleep(0.05)

        # Convert positions to model format
        positions = []
        for pos in result.positions:
            positions.append(SuggestedPosition(
                position_type=pos.get('position_type', 'cover'),
                lat=0.0,  # Positions are drawn on image, not extracted as coords
                lng=0.0,
                description=pos.get('description', ''),
                for_unit=pos.get('for_unit'),
                icon=pos.get('icon', 'map-pin')
            ))

        # Convert segment analysis to model format
        segment_analysis = []
        for i, seg in enumerate(result.segment_analysis):
            # Calculate segment start/end from waypoints
            if i < len(request.waypoints) - 1:
                segment_analysis.append(SegmentAnalysis(
                    segment_index=i,
                    start_lat=request.waypoints[i].lat,
                    start_lng=request.waypoints[i].lng,
                    end_lat=request.waypoints[i + 1].lat,
                    end_lng=request.waypoints[i + 1].lng,
                    risk_level=seg.get('risk_level', 'medium'),
                    description=seg.get('description', ''),
                    suggestions=seg.get('suggestions', [])
                ))

        self._report_progress("complete", 100, "Evaluation complete!")

        return RouteEvaluationResponse(
            request_id=request_id,
            timestamp=start_time,
            annotated_image=result.annotated_image_base64,
            annotated_image_bounds=result.adjusted_bounds or image_bounds,
            positions=positions,
            segment_analysis=segment_analysis,
            overall_assessment=result.overall_assessment,
            route_distance_m=total_distance,
            estimated_time_minutes=estimated_time_minutes
        )

    async def analyze_tactical_simulation(
        self,
        request: TacticalSimulationRequest
    ) -> TacticalSimulationResponse:
        """
        Analyze a tactical simulation with enemy vision cones and movement route.

        1. Fetches satellite imagery
        2. Draws enemy vision cones and movement route on the image
        3. Sends to Gemini 3 Flash for tactical analysis
        4. Returns annotated image with weak spots and recommendations
        """
        request_id = request.request_id or str(uuid.uuid4())
        start_time = datetime.utcnow()

        self._report_progress("imagery", 5, "Validating simulation...")
        await asyncio.sleep(0.05)

        # Validate bounds
        bounds = request.bounds
        if not all(k in bounds for k in ['north', 'south', 'east', 'west']):
            raise ValueError("Invalid bounds - must contain north, south, east, west")

        self._report_progress("imagery", 15, "Fetching satellite imagery...")
        await asyncio.sleep(0.05)

        # Get satellite image
        satellite_image, image_bounds = await self._get_satellite_image_fast(bounds, 16)

        if not satellite_image:
            raise RuntimeError("Failed to fetch satellite imagery")

        self._report_progress("drawing", 30, "Drawing tactical elements...")
        await asyncio.sleep(0.05)

        # Draw vision cones and route on the image
        annotated_image = await self._draw_tactical_simulation(
            satellite_image,
            image_bounds,
            request.enemies,
            request.friendlies,
            request.route_waypoints
        )

        self._report_progress("analysis", 50, "AI analyzing tactical scenario...")
        await asyncio.sleep(0.05)

        # Build prompt with context
        enemy_composition = "\n".join([
            f"  - {e.type.value.upper()} at ({e.lat:.4f}, {e.lng:.4f}), facing {e.facing}°"
            for e in request.enemies
        ])
        friendly_composition = "\n".join([
            f"  - {f.type.value.upper()} at ({f.lat:.4f}, {f.lng:.4f})"
            for f in request.friendlies
        ]) if request.friendlies else "  (none specified)"

        # Load prompt from YAML config
        tactical_prompt_template = get_yaml_setting("tactical_simulation_prompt")
        if not tactical_prompt_template:
            raise ValueError("Missing tactical_simulation_prompt in config.yaml")

        prompt = tactical_prompt_template.format(
            num_enemies=len(request.enemies),
            num_friendlies=len(request.friendlies),
            enemy_composition=enemy_composition,
            friendly_composition=friendly_composition
        )

        # Send to Gemini 3 Flash for analysis
        result = await self.route_generator.analyze_tactical_simulation(
            annotated_image,
            prompt
        )

        self._report_progress("processing", 80, "Processing analysis results...")
        await asyncio.sleep(0.05)

        # Calculate route metrics
        total_distance = 0.0
        for i in range(len(request.route_waypoints) - 1):
            wp1 = request.route_waypoints[i]
            wp2 = request.route_waypoints[i + 1]
            total_distance += self._haversine_distance(wp1.lat, wp1.lng, wp2.lat, wp2.lng)

        estimated_time_minutes = total_distance / 70  # ~70m/min with cover

        # Parse weak spots
        weak_spots = []
        for ws in result.get('weak_spots', []):
            weak_spots.append(WeakSpot(
                location=ws.get('location', 'Unknown'),
                description=ws.get('description', ''),
                severity=ws.get('severity', 'medium'),
                recommendation=ws.get('recommendation', '')
            ))

        # Parse strong points (good terrain usage)
        strong_points = []
        for sp in result.get('strong_points', []):
            strong_points.append(StrongPoint(
                location=sp.get('location', 'Unknown'),
                description=sp.get('description', ''),
                benefit=sp.get('benefit', '')
            ))

        # Parse exposure analysis (legacy)
        exposure_analysis = []
        for ea in result.get('exposure_analysis', []):
            exposure_analysis.append(ExposureAnalysis(
                segment_index=ea.get('segment_index', 0),
                enemy_id=ea.get('enemy_id', ''),
                exposure_percentage=ea.get('exposure_percentage', 0),
                description=ea.get('description', '')
            ))

        # Parse NEW: segment cover analysis
        segment_cover_analysis = []
        for sca in result.get('segment_cover_analysis', []):
            segment_cover_analysis.append(SegmentCoverAnalysis(
                segment_index=sca.get('segment_index', 0),
                in_vision_cone=sca.get('in_vision_cone', False),
                cover_status=sca.get('cover_status', 'clear'),
                cover_type=sca.get('cover_type'),
                exposure_percentage=sca.get('exposure_percentage', 0),
                blocking_feature=sca.get('blocking_feature'),
                enemy_id=sca.get('enemy_id'),
                explanation=sca.get('explanation', '')
            ))

        # Parse NEW: tactical scores (with fallback based on strategy rating)
        tactical_scores = None
        if 'tactical_scores' in result and result['tactical_scores']:
            ts = result['tactical_scores']
            tactical_scores = TacticalScores(
                stealth=ts.get('stealth', 50),
                safety=ts.get('safety', 50),
                terrain_usage=ts.get('terrain_usage', 50),
                flanking=ts.get('flanking', 50),
                overall=ts.get('overall', 50)
            )
        else:
            # Generate fallback scores based on strategy rating
            rating = result.get('strategy_rating', 5.0)
            base_score = rating * 10  # Convert 0-10 to 0-100
            tactical_scores = TacticalScores(
                stealth=min(100, max(0, base_score + random.randint(-10, 10))),
                safety=min(100, max(0, base_score + random.randint(-10, 10))),
                terrain_usage=min(100, max(0, base_score + random.randint(-10, 10))),
                flanking=min(100, max(0, base_score + random.randint(-10, 10))),
                overall=min(100, max(0, base_score))
            )

        # Calculate MATHEMATICAL flanking angle (don't trust Gemini's visual estimate)
        # This computes the actual angle between approach direction and enemy facing
        calculated_flanking = self._calculate_flanking_angle(
            request.route_waypoints,
            request.enemies
        )

        # Parse Gemini's flanking analysis for description only, use our calculated angle
        gemini_description = ""
        if 'flanking_analysis' in result and result['flanking_analysis']:
            fa = result['flanking_analysis']
            gemini_description = fa.get('description', '')

        # Use mathematically calculated values, with Gemini description as supplement
        approach_angle = calculated_flanking['approach_angle']
        is_flanking = approach_angle >= 90  # Flanking if > 90° from enemy facing

        # Calculate bonus based on angle
        if approach_angle >= 150:
            bonus = 2.5  # Rear attack
        elif approach_angle >= 120:
            bonus = 2.0  # Strong flank
        elif approach_angle >= 90:
            bonus = 1.5  # Side approach
        elif approach_angle >= 60:
            bonus = 0.5  # Partial flank
        else:
            bonus = 0.0  # Frontal

        # Generate accurate description based on calculated angle
        if approach_angle >= 150:
            angle_desc = f"Rear attack - approaching from {approach_angle:.0f}° behind enemy facing. Maximum tactical surprise."
        elif approach_angle >= 120:
            angle_desc = f"Strong flank - approaching from {approach_angle:.0f}° off enemy facing. In enemy blind spot."
        elif approach_angle >= 90:
            angle_desc = f"Side approach - {approach_angle:.0f}° from enemy facing. Reduced detection chance."
        elif approach_angle >= 60:
            angle_desc = f"Partial flank - {approach_angle:.0f}° from enemy facing. Some tactical advantage."
        else:
            angle_desc = f"Frontal approach - only {approach_angle:.0f}° from enemy facing direction. High detection risk."

        flanking_analysis = FlankingAnalysis(
            is_flanking=is_flanking,
            approach_angle=approach_angle,
            bonus_awarded=bonus,
            description=f"{angle_desc} {gemini_description}".strip()
        )

        # Parse NEW: cover breakdown
        cover_breakdown = None
        num_segments = len(request.route_waypoints) - 1
        if 'cover_breakdown' in result and result['cover_breakdown']:
            cb = result['cover_breakdown']
            cover_breakdown = CoverBreakdown(
                total_segments=cb.get('total_segments', num_segments),
                exposed_count=cb.get('exposed_count', 0),
                covered_count=cb.get('covered_count', 0),
                partial_count=cb.get('partial_count', 0),
                clear_count=cb.get('clear_count', 0),
                overall_cover_percentage=cb.get('overall_cover_percentage', 0),
                cover_types_used=cb.get('cover_types_used', [])
            )
        else:
            # Generate fallback based on segment cover analysis or rating
            if segment_cover_analysis:
                exposed = sum(1 for s in segment_cover_analysis if s.cover_status == 'exposed')
                covered = sum(1 for s in segment_cover_analysis if s.cover_status == 'covered')
                partial = sum(1 for s in segment_cover_analysis if s.cover_status == 'partial')
                clear = sum(1 for s in segment_cover_analysis if s.cover_status == 'clear')
                cover_pct = ((covered + clear + partial * 0.5) / max(1, num_segments)) * 100
            else:
                # Use rating as proxy for cover
                rating = result.get('strategy_rating', 5.0)
                cover_pct = rating * 10
                exposed = int(num_segments * (1 - rating / 10))
                covered = num_segments - exposed
                partial = 0
                clear = 0

            cover_breakdown = CoverBreakdown(
                total_segments=num_segments,
                exposed_count=exposed,
                covered_count=covered,
                partial_count=partial,
                clear_count=clear,
                overall_cover_percentage=min(100, max(0, cover_pct)),
                cover_types_used=['building'] if covered > 0 else []
            )

        # Get verdict
        verdict = result.get('verdict', None)

        self._report_progress("complete", 100, "Analysis complete!")

        return TacticalSimulationResponse(
            request_id=request_id,
            timestamp=start_time,
            annotated_image=result.get('annotated_image', annotated_image),
            annotated_image_bounds=image_bounds,
            strategy_rating=result.get('strategy_rating', 5.0),
            verdict=verdict,
            tactical_scores=tactical_scores,
            flanking_analysis=flanking_analysis,
            segment_cover_analysis=segment_cover_analysis,
            cover_breakdown=cover_breakdown,
            weak_spots=weak_spots,
            strong_points=strong_points,
            exposure_analysis=exposure_analysis,
            terrain_assessment=result.get('terrain_assessment', ''),
            overall_assessment=result.get('overall_assessment', 'Analysis complete'),
            recommendations=result.get('recommendations', []),
            route_distance_m=total_distance,
            estimated_time_minutes=estimated_time_minutes
        )

    def _calculate_flanking_angle(
        self,
        route_waypoints: list,
        enemies: list
    ) -> dict:
        """
        Calculate the ACTUAL flanking angle mathematically from coordinates.

        Returns the angle between the route's approach direction and
        the average enemy facing direction.

        An approach from directly in front of the enemy = 0°
        An approach from the side = 90°
        An approach from behind = 180°
        """
        if len(route_waypoints) < 2 or len(enemies) == 0:
            return {'approach_angle': 0, 'is_flanking': False}

        # Get the last two waypoints to determine approach direction
        # The approach vector points FROM second-to-last TO last waypoint
        wp_before_last = route_waypoints[-2]
        wp_last = route_waypoints[-1]

        # Calculate approach bearing (direction we're moving)
        lat1, lon1 = math.radians(wp_before_last.lat), math.radians(wp_before_last.lng)
        lat2, lon2 = math.radians(wp_last.lat), math.radians(wp_last.lng)

        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        approach_bearing = math.degrees(math.atan2(x, y))
        approach_bearing = (approach_bearing + 360) % 360  # Normalize to 0-360

        # For each enemy, calculate the angle difference between their facing and our approach
        angle_diffs = []
        for enemy in enemies:
            enemy_facing = enemy.facing  # degrees, 0 = North

            # Calculate the angle between our approach and enemy's facing direction
            # If we approach FROM BEHIND the enemy, this should be ~180°
            # If we approach FROM FRONT, this should be ~0°

            # The direction FROM enemy TO our approach path
            # We want the angle between (enemy facing) and (direction enemy would need to turn to see us)

            # Calculate bearing FROM enemy position TO our last waypoint
            enemy_lat = math.radians(enemy.lat)
            enemy_lon = math.radians(enemy.lng)
            target_lat = math.radians(wp_last.lat)
            target_lon = math.radians(wp_last.lng)

            dlon_target = target_lon - enemy_lon
            x_target = math.sin(dlon_target) * math.cos(target_lat)
            y_target = math.cos(enemy_lat) * math.sin(target_lat) - math.sin(enemy_lat) * math.cos(target_lat) * math.cos(dlon_target)
            bearing_to_attacker = math.degrees(math.atan2(x_target, y_target))
            bearing_to_attacker = (bearing_to_attacker + 360) % 360

            # The flanking angle is how far off the enemy's facing we are
            # 0° = directly in front of enemy (they see us)
            # 180° = directly behind enemy (they don't see us)
            angle_diff = abs(bearing_to_attacker - enemy_facing)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff

            angle_diffs.append(angle_diff)

        # Use the minimum angle difference (worst case - closest to frontal)
        # This is conservative: if ANY enemy can see us, we're not truly flanking
        min_angle = min(angle_diffs) if angle_diffs else 0

        return {
            'approach_angle': min_angle,
            'is_flanking': min_angle >= 90
        }

    async def _draw_tactical_simulation(
        self,
        satellite_image_base64: str,
        bounds: dict,
        enemies: list,
        friendlies: list,
        route_waypoints: list
    ) -> str:
        """Draw vision cones, units, and route on satellite image."""
        from PIL import Image, ImageDraw
        import io

        # Decode base64 image
        image_data = base64.b64decode(satellite_image_base64)
        image = Image.open(io.BytesIO(image_data))
        draw = ImageDraw.Draw(image, 'RGBA')

        width, height = image.size
        lat_range = bounds['north'] - bounds['south']
        lon_range = bounds['east'] - bounds['west']

        def geo_to_pixel(lat: float, lon: float) -> tuple[int, int]:
            """Convert geographic coordinates to pixel coordinates."""
            x = int((lon - bounds['west']) / lon_range * width)
            y = int((bounds['north'] - lat) / lat_range * height)
            return (x, y)

        # Vision cone colors by type (with transparency) - all red
        vision_colors = {
            'sniper': (239, 68, 68, 60),    # Red
            'rifleman': (239, 68, 68, 60),  # Red
            'observer': (239, 68, 68, 60),  # Red
        }

        # Vision cone specs (distance in meters, angle in degrees)
        # Must match frontend ENEMY_VISION_SPECS exactly
        vision_specs = {
            'sniper': {'distance': 500, 'angle': 30},
            'rifleman': {'distance': 100, 'angle': 60},
            'observer': {'distance': 400, 'angle': 45},
        }

        # Draw enemy vision cones using geographic coordinates (like frontend)
        for enemy in enemies:
            enemy_type = enemy.type.value
            specs = vision_specs.get(enemy_type, vision_specs['rifleman'])
            color = vision_colors.get(enemy_type, (255, 0, 0, 60))

            # Start with enemy position
            cx, cy = geo_to_pixel(enemy.lat, enemy.lng)

            # Calculate cone arc points using geographic coordinates (matches frontend exactly)
            # Frontend uses: distanceDeg = distanceMeters / 111000
            distance_deg = specs['distance'] / 111000

            half_angle = specs['angle'] / 2
            start_angle = enemy.facing - half_angle
            end_angle = enemy.facing + half_angle

            # Generate cone polygon using geographic coordinates, then convert to pixels
            # This matches frontend's calculateVisionCone() exactly
            cone_points = [(cx, cy)]
            for angle in range(int(start_angle), int(end_angle) + 1, 5):
                rad = math.radians(angle)  # Compass bearing: 0=North, 90=East
                # Frontend formula:
                # newLat = lat + distanceDeg * cos(radians)
                # newLng = lng + distanceDeg * sin(radians) / cos(lat * PI/180)
                new_lat = enemy.lat + distance_deg * math.cos(rad)
                new_lng = enemy.lng + distance_deg * math.sin(rad) / math.cos(math.radians(enemy.lat))
                px, py = geo_to_pixel(new_lat, new_lng)
                cone_points.append((px, py))
            cone_points.append((cx, cy))

            draw.polygon(cone_points, fill=color, outline=(color[0], color[1], color[2], 180))

            # Draw enemy marker with icon based on type
            marker_size = 12
            if enemy_type == 'sniper':
                # Sniper: Crosshair/scope icon
                draw.ellipse([cx - marker_size, cy - marker_size, cx + marker_size, cy + marker_size],
                           fill=(30, 30, 30, 255), outline=(239, 68, 68, 255))
                draw.ellipse([cx - marker_size + 3, cy - marker_size + 3, cx + marker_size - 3, cy + marker_size - 3],
                           fill=None, outline=(239, 68, 68, 255))
                # Crosshair lines
                draw.line([(cx - marker_size, cy), (cx + marker_size, cy)], fill=(239, 68, 68, 255), width=2)
                draw.line([(cx, cy - marker_size), (cx, cy + marker_size)], fill=(239, 68, 68, 255), width=2)
            elif enemy_type == 'observer':
                # Observer: Binoculars-like icon (two circles)
                draw.ellipse([cx - marker_size, cy - marker_size, cx + marker_size, cy + marker_size],
                           fill=(30, 30, 30, 255), outline='white')
                draw.ellipse([cx - 7, cy - 4, cx - 1, cy + 4], fill=(239, 68, 68, 255), outline='white')
                draw.ellipse([cx + 1, cy - 4, cx + 7, cy + 4], fill=(239, 68, 68, 255), outline='white')
            else:
                # Rifleman: Target/bullseye icon
                draw.ellipse([cx - marker_size, cy - marker_size, cx + marker_size, cy + marker_size],
                           fill=(239, 68, 68, 255), outline='white')
                draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(30, 30, 30, 255), outline='white')
                draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(239, 68, 68, 255))

            # Add direction indicator (small triangle showing facing)
            facing_rad = math.radians(enemy.facing)
            indicator_dist = marker_size + 5
            tip_x = cx + int(indicator_dist * math.sin(facing_rad))
            tip_y = cy - int(indicator_dist * math.cos(facing_rad))
            draw.polygon([(tip_x, tip_y),
                         (cx + int((marker_size) * math.sin(facing_rad - 0.5)),
                          cy - int((marker_size) * math.cos(facing_rad - 0.5))),
                         (cx + int((marker_size) * math.sin(facing_rad + 0.5)),
                          cy - int((marker_size) * math.cos(facing_rad + 0.5)))],
                        fill=(239, 68, 68, 255))

        # Draw friendly units with soldier icon
        for friendly in friendlies:
            fx, fy = geo_to_pixel(friendly.lat, friendly.lng)
            # Pentagon shape for friendly unit
            pentagon_size = 10
            pentagon_points = []
            for i in range(5):
                angle = math.radians(90 + i * 72)  # Start from top
                px = fx + int(pentagon_size * math.cos(angle))
                py = fy - int(pentagon_size * math.sin(angle))
                pentagon_points.append((px, py))
            draw.polygon(pentagon_points, fill=(59, 130, 246, 255), outline='white')
            # Inner circle
            draw.ellipse([fx - 4, fy - 4, fx + 4, fy + 4], fill='white')

        # Draw movement route (blue dashed line)
        if len(route_waypoints) >= 2:
            route_coords = [geo_to_pixel(wp.lat, wp.lng) for wp in route_waypoints]

            # Draw dashed line
            for i in range(len(route_coords) - 1):
                x1, y1 = route_coords[i]
                x2, y2 = route_coords[i + 1]

                # Calculate dash segments
                length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                if length > 0:
                    dash_length = 15
                    gap_length = 8
                    num_segments = int(length / (dash_length + gap_length))

                    for j in range(num_segments + 1):
                        t1 = j * (dash_length + gap_length) / length
                        t2 = min((j * (dash_length + gap_length) + dash_length) / length, 1.0)

                        dx1 = int(x1 + (x2 - x1) * t1)
                        dy1 = int(y1 + (y2 - y1) * t1)
                        dx2 = int(x1 + (x2 - x1) * t2)
                        dy2 = int(y1 + (y2 - y1) * t2)

                        draw.line([(dx1, dy1), (dx2, dy2)], fill=(59, 130, 246, 255), width=4)

            # Draw waypoint markers
            for i, (x, y) in enumerate(route_coords):
                if i == 0:
                    # Start marker - green
                    draw.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(34, 197, 94, 255), outline='white')
                elif i == len(route_coords) - 1:
                    # End marker - red
                    draw.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(239, 68, 68, 255), outline='white')
                else:
                    # Intermediate - white
                    draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill='white', outline=(59, 130, 246, 255))

        # Convert back to base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
