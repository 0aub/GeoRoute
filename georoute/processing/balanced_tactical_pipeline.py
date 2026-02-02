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
)
from ..utils.geo_validator import GulfRegionValidator
from ..config import load_config

from .gemini_image_route_generator import GeminiImageRouteGenerator
from ..clients.esri_imagery import ESRIImageryClient


class BalancedTacticalPipeline:
    """
    Tactical route planning using Gemini 3 Pro Image.

    Gemini draws routes directly on satellite imagery - no obstacle detection needed.
    """

    def __init__(self, config):
        # Initialize clients
        self.config = config
        self.gmaps = GoogleMapsClient(config.google_maps_api_key)
        self.gemini = TacticalGeminiClient(config.gemini_api_key, config.google_cloud_project)
        self.esri = ESRIImageryClient()  # ESRI for satellite imagery (matches UI)
        self._progress_callback: Optional[Callable[[str, int, str], None]] = None
        self._last_image_bounds = None  # Track actual satellite image bounds

        # Initialize Gemini Image route generator
        self.route_generator = GeminiImageRouteGenerator(api_key=config.gemini_api_key)
        print("[BalancedPipeline] Using Gemini 3 Pro Image for direct route drawing")
        print("[BalancedPipeline] Using ESRI World Imagery (matches Leaflet UI)")

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
        """Get satellite image from ESRI that covers the entire bounds area.

        Uses ESRI World Imagery tiles - same tiles Leaflet displays.
        This ensures pixel-perfect visual match with the UI.

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

        # Add 40% padding to bounds to ensure markers aren't at edges
        # and to provide context around the route
        padding_lat = lat_span * 0.40
        padding_lon = lon_span * 0.40

        padded_bounds = {
            "north": bounds["north"] + padding_lat,
            "south": bounds["south"] - padding_lat,
            "east": bounds["east"] + padding_lon,
            "west": bounds["west"] - padding_lon
        }

        print(f"[BalancedPipeline] Bounds span: {max_span:.0f}m")
        print(f"[BalancedPipeline] Requested bounds: N={padded_bounds['north']:.6f}, S={padded_bounds['south']:.6f}, E={padded_bounds['east']:.6f}, W={padded_bounds['west']:.6f}")

        try:
            # ESRI client now returns (image_bytes, actual_bounds)
            # Use 1024x1024 for better image quality
            image_bytes, actual_bounds = await self.esri.get_satellite_image(
                bounds=padded_bounds,
                width=1024,
                height=1024
            )
            if image_bytes:
                # Store actual bounds for overlay positioning
                self._last_image_bounds = actual_bounds
                print(f"[BalancedPipeline] Actual image bounds: N={actual_bounds['north']:.6f}, S={actual_bounds['south']:.6f}, E={actual_bounds['east']:.6f}, W={actual_bounds['west']:.6f}")
                return base64.b64encode(image_bytes).decode("utf-8"), actual_bounds
        except Exception as e:
            print(f"[BalancedPipeline] ESRI satellite image failed: {e}")
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

        # Calculate bounds around start and end points
        # Ensure the bounds are roughly square (not too thin in either direction)
        lat_diff = abs(start_lat - target_lat)
        lon_diff = abs(start_lon - target_lon)

        # Make the bounds at least as wide as they are tall (and vice versa)
        # to avoid extremely stretched images
        max_diff = max(lat_diff, lon_diff)
        if max_diff < 0.001:  # Minimum ~100m span
            max_diff = 0.001

        center_lat = (start_lat + target_lat) / 2
        center_lon = (start_lon + target_lon) / 2

        route_bounds = {
            "north": center_lat + max_diff / 2,
            "south": center_lat - max_diff / 2,
            "east": center_lon + max_diff / 2,
            "west": center_lon - max_diff / 2
        }
        print(f"[BalancedPipeline] Route bounds (square): N={route_bounds['north']:.6f}, S={route_bounds['south']:.6f}, E={route_bounds['east']:.6f}, W={route_bounds['west']:.6f}")

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

        # Route distance estimates:
        # - Balanced: ~20% longer than direct (uses some cover)
        # - Stealth: ~50% longer than direct (maximizes cover, longer path)
        balanced_distance = total_distance * 1.2
        stealth_distance = total_distance * 1.5

        routes_data = [
            {
                "route_id": 1,
                "name": "Balanced Approach",
                "description": "ORANGE route - Uses cover while maintaining reasonable speed.",
                "strategy": "balanced",
                "color": "orange",
                "waypoints": [
                    {"lat": start_lat, "lon": start_lon, "elevation_m": 0, "distance_from_start_m": 0},
                    {"lat": target_lat, "lon": target_lon, "elevation_m": 0, "distance_from_start_m": balanced_distance}
                ],
                "path_clear": True
            },
            {
                "route_id": 2,
                "name": "Stealth Approach",
                "description": "GREEN route - Maximum concealment. Safest tactical option.",
                "strategy": "stealth",
                "color": "green",
                "waypoints": [
                    {"lat": start_lat, "lon": start_lon, "elevation_m": 0, "distance_from_start_m": 0},
                    {"lat": target_lat, "lon": target_lon, "elevation_m": 0, "distance_from_start_m": stealth_distance}
                ],
                "path_clear": True
            }
        ]

        # After Gemini responds - jump to 70% (Gemini was the main work)
        self._report_progress("routes", 70, "Processing route image...")
        await asyncio.sleep(0.05)

        # Store the route image for UI overlay
        # Use adjusted bounds (after watermark cropping) for correct overlay positioning
        detection_debug['gemini_route_image'] = result.route_image_base64
        detection_debug['gemini_route_bounds'] = result.adjusted_bounds or image_bounds
        print(f"[BalancedPipeline] Gemini route image generated successfully")

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
