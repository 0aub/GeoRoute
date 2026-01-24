"""
Balanced Tactical Pipeline - Fast but respects buildings.

This pipeline uses Gemini Vision for obstacle detection:
1. Fetches satellite imagery
2. Gemini Vision identifies buildings/obstacles in the image
3. A* pathfinding generates routes avoiding detected obstacles
4. Gemini analyzes tactical risks for final assessment

Estimated time: 10-20 seconds
"""

import uuid
import asyncio
import base64
import math
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
)
from ..utils.geo_validator import GulfRegionValidator
from ..config import load_config

# Import obstacle detection (SAM or Gemini) and grid pathfinding
from .gemini_obstacle_detector import GeminiObstacleDetector
from .sam_obstacle_detector import SAMObstacleDetector
from .grid_pathfinder import generate_tactical_routes


class BalancedTacticalPipeline:
    """
    Balanced tactical route planning - uses Gemini Vision for obstacle detection.
    """

    def __init__(
        self,
        gmaps_client: GoogleMapsClient,
        gemini_client: TacticalGeminiClient,
    ):
        self.gmaps = gmaps_client
        self.gemini = gemini_client
        self._progress_callback: Optional[Callable[[str, int, str], None]] = None

        # Initialize obstacle detector based on config
        config = load_config()
        from ..config import get_yaml_setting
        detection_method = get_yaml_setting("obstacle_detection", "method", "sam")

        if detection_method == "sam":
            # Use SAM (Segment Anything Model) for GPU-accelerated detection
            try:
                self.obstacle_detector = SAMObstacleDetector(
                    model_type=get_yaml_setting("sam", "model_type", "vit_h"),
                    device=get_yaml_setting("sam", "device", "cuda"),
                    buffer_pixels=0,  # No buffer - streets are already narrow in urban areas
                    grid_size=32,
                    min_area=get_yaml_setting("sam", "min_area", 100)
                )
                self._use_sam = True
                print("[BalancedPipeline] Using SAM for obstacle detection (GPU-accelerated)")
            except Exception as e:
                print(f"[BalancedPipeline] SAM init failed: {e}, falling back to Gemini")
                self.obstacle_detector = GeminiObstacleDetector(
                    api_key=config.gemini_api_key,
                    buffer_pixels=0,
                    grid_size=32
                )
                self._use_sam = False
        else:
            # Use Gemini Vision (API-based fallback)
            self.obstacle_detector = GeminiObstacleDetector(
                api_key=config.gemini_api_key,
                buffer_pixels=0,
                grid_size=32
            )
            self._use_sam = False
            print("[BalancedPipeline] Using Gemini Vision for obstacle detection")

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

    async def _get_satellite_image_fast(self, bounds: dict, zoom: int = 14) -> Optional[str]:
        """Get satellite image quickly."""
        center_lat = (bounds["north"] + bounds["south"]) / 2
        center_lon = (bounds["east"] + bounds["west"]) / 2

        # Calculate optimal zoom based on bounds size (more accurate than user zoom)
        optimal_zoom = self._calculate_optimal_zoom(bounds)
        # Use the higher zoom (more detail) but cap at 18 for stability
        actual_zoom = min(max(optimal_zoom, zoom), 18)

        print(f"[BalancedPipeline] Satellite image: center=({center_lat:.6f}, {center_lon:.6f}), zoom={actual_zoom} (requested={zoom}, optimal={optimal_zoom})")

        try:
            image_bytes = await self.gmaps.get_satellite_image(
                center=(center_lat, center_lon),
                zoom=actual_zoom,
                size="640x640"
            )
            if image_bytes:
                return base64.b64encode(image_bytes).decode("utf-8")
        except Exception as e:
            print(f"[BalancedPipeline] Satellite image failed: {e}")
        return None

    def _generate_geometric_routes(
        self,
        start: tuple[float, float],
        end: tuple[float, float]
    ) -> list[dict]:
        """Fallback: Generate simple geometric routes."""
        routes = []
        route_types = [
            ("Direct Route", "direct"),
            ("Left Approach", "left"),
            ("Right Approach", "right")
        ]

        for route_id, (name, route_type) in enumerate(route_types, 1):
            waypoints = []
            num_points = 10

            for i in range(num_points):
                t = i / (num_points - 1)
                lat = start[0] + t * (end[0] - start[0])
                lon = start[1] + t * (end[1] - start[1])

                # Apply curve for flanking routes
                if route_type != "direct":
                    offset = math.sin(t * math.pi) * 0.001
                    dx = end[1] - start[1]
                    dy = end[0] - start[0]
                    length = math.sqrt(dx*dx + dy*dy)
                    if length > 0:
                        if route_type == "left":
                            lat += (-dx / length) * offset
                            lon += (dy / length) * offset
                        else:
                            lat += (dx / length) * offset
                            lon += (-dy / length) * offset

                distance = self._haversine_distance(start[0], start[1], lat, lon)
                waypoints.append({
                    "lat": lat,
                    "lon": lon,
                    "elevation_m": 0.0,
                    "distance_from_start_m": distance,
                    "terrain_type": "open_terrain",
                    "risk_level": "moderate",
                    "reasoning": "Geometric route",
                })

            routes.append({
                "route_id": route_id,
                "name": name,
                "description": f"{name} to target",
                "waypoints": waypoints
            })

        return routes

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
            return self._default_analysis(routes_data)

    def _default_analysis(self, routes: list[dict]) -> dict:
        """Default analysis when Gemini fails."""
        return {
            "routes": [
                {
                    "route_id": route["route_id"],
                    "name": route["name"],
                    "segment_risks": ["moderate"] * min(len(route["waypoints"]), 5),
                    "scores": {"time_to_target": 70, "stealth_score": 60, "survival_probability": 70},
                    "verdict": "RISK",
                    "reasoning": "Default assessment - proceed with caution",
                    "detection_probability": 0.5
                }
                for route in routes
            ]
        }

    def _build_tactical_route(self, route_data: dict, analysis: dict) -> TacticalRoute:
        """Build TacticalRoute from route data and analysis."""
        waypoints = []
        segments = []

        route_analysis = next(
            (r for r in analysis.get("routes", []) if r["route_id"] == route_data["route_id"]),
            None
        )

        if not route_analysis:
            route_analysis = {
                "segment_risks": ["moderate"] * len(route_data["waypoints"]),
                "scores": {"time_to_target": 70, "stealth_score": 60, "survival_probability": 70},
                "verdict": "RISK",
                "reasoning": "Default assessment",
                "detection_probability": 0.5
            }

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

        # Build scores
        scores_data = route_analysis.get("scores", {})
        overall = (
            scores_data.get("time_to_target", 70) * 0.2 +
            scores_data.get("stealth_score", 60) * 0.3 +
            scores_data.get("survival_probability", 70) * 0.5
        )

        scores = RouteScores(
            time_to_target=scores_data.get("time_to_target", 70),
            stealth_score=scores_data.get("stealth_score", 60),
            survival_probability=scores_data.get("survival_probability", 70),
            overall_score=overall
        )

        # Build simulation
        detection_prob = route_analysis.get("detection_probability", 0.5)
        simulation = SimulationResult(
            detected=detection_prob > 0.5,
            detection_probability=detection_prob,
            detection_points=[],
            safe_percentage=(1 - detection_prob) * 100
        )

        # Build classification
        verdict_str = route_analysis.get("verdict", "RISK").upper()
        verdict = RouteVerdict.SUCCESS if verdict_str == "SUCCESS" else (
            RouteVerdict.FAILED if verdict_str == "FAILED" else RouteVerdict.RISK
        )

        classification = ClassificationResult(
            gemini_evaluation=verdict,
            gemini_reasoning=route_analysis.get("reasoning", ""),
            scores=scores,
            simulation=simulation,
            final_verdict=verdict,
            final_reasoning=route_analysis.get("reasoning", ""),
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

        self._report_progress("terrain", 5, "Validating request...")

        # Validate Gulf region
        is_valid, validation_msg = GulfRegionValidator.validate_route(
            request.soldiers, request.enemies
        )
        if not is_valid:
            self._report_progress("error", 0, f"Validation failed: {validation_msg}")
            raise ValueError(f"Geographic restriction: {validation_msg}")

        self._report_progress("terrain", 10, "Calculating positions...")

        # Calculate start/end positions
        start_lat = sum(s.lat for s in request.soldiers) / len(request.soldiers)
        start_lon = sum(s.lon for s in request.soldiers) / len(request.soldiers)
        target_lat = sum(e.lat for e in request.enemies) / len(request.enemies)
        target_lon = sum(e.lon for e in request.enemies) / len(request.enemies)

        print(f"[BalancedPipeline] Soldiers center: ({start_lat:.6f}, {start_lon:.6f})")
        print(f"[BalancedPipeline] Enemies center: ({target_lat:.6f}, {target_lon:.6f})")
        print(f"[BalancedPipeline] Bounds: N={request.bounds.get('north'):.6f}, S={request.bounds.get('south'):.6f}, E={request.bounds.get('east'):.6f}, W={request.bounds.get('west'):.6f}")
        print(f"[BalancedPipeline] Zoom: {request.zoom}")

        self._report_progress("imagery", 20, "Fetching satellite imagery...")

        # Get satellite image
        satellite_image = await self._get_satellite_image_fast(request.bounds, request.zoom or 14)

        detector_name = "SAM" if self._use_sam else "Gemini Vision"
        self._report_progress("routes", 30, f"Detecting obstacles with {detector_name}...")

        # Detect obstacles using SAM or Gemini, then run A* pathfinding
        routes_data = []
        detection_debug = {}
        try:
            if satellite_image:
                self._report_progress("routes", 40, f"{detector_name} analyzing satellite image...")

                # Step 1: Detect obstacles (buildings, structures)
                detection_result = await self.obstacle_detector.detect_obstacles(
                    satellite_image_base64=satellite_image,
                    bounds=request.bounds
                )

                obstacle_count = detection_result.obstacle_count
                grid_size = detection_result.grid_size[0]
                self._report_progress("routes", 50, f"Detected {obstacle_count} obstacle cells in {grid_size}x{grid_size} grid")

                # Step 2: A* pathfinding on the obstacle grid
                self._report_progress("routes", 55, "Running A* pathfinding...")

                routes_data, detection_debug = generate_tactical_routes(
                    obstacle_mask=detection_result.buffered_mask,
                    start_gps=(start_lat, start_lon),
                    end_gps=(target_lat, target_lon),
                    bounds=request.bounds,
                    single_route=False  # Generate 3 routes (direct, left flank, right flank)
                )

                print(f"[BalancedPipeline] Generated {len(routes_data)} routes via {detector_name} + A*")
            else:
                print("[BalancedPipeline] No satellite image, using geometric routes")
                routes_data = self._generate_geometric_routes(
                    (start_lat, start_lon),
                    (target_lat, target_lon)
                )
        except Exception as e:
            import traceback
            print(f"[BalancedPipeline] Route planning failed: {e}")
            traceback.print_exc()
            routes_data = self._generate_geometric_routes(
                (start_lat, start_lon),
                (target_lat, target_lon)
            )

        # FINAL SAFEGUARD: Ensure we ALWAYS have at least one route with valid waypoints
        valid_routes = [r for r in routes_data if r.get("waypoints") and len(r["waypoints"]) >= 2]
        if not valid_routes:
            print(f"[BalancedPipeline] WARNING: No valid routes generated! Creating direct line fallback.")
            routes_data = [{
                "route_id": 1,
                "name": "Direct Route",
                "description": "Direct line (obstacle detection may have failed)",
                "waypoints": [
                    {"lat": start_lat, "lon": start_lon, "elevation_m": 0, "distance_from_start_m": 0},
                    {"lat": target_lat, "lon": target_lon, "elevation_m": 0, "distance_from_start_m": self._haversine_distance(start_lat, start_lon, target_lat, target_lon)}
                ],
                "path_clear": False
            }]
        else:
            routes_data = valid_routes

        print(f"[BalancedPipeline] Final routes count: {len(routes_data)}, waypoints in route 1: {len(routes_data[0].get('waypoints', []))}")

        self._report_progress("routes", 60, f"Generated {len(routes_data)} routes via {detector_name} + A*")

        self._report_progress("risk", 60, "AI analyzing tactical risks...")

        # Single Gemini call for analysis
        try:
            analysis = await self._analyze_routes_combined(
                routes_data,
                request.enemies,
                satellite_image
            )
            print(f"[BalancedPipeline] Analysis complete: {len(analysis.get('routes', []))} routes analyzed")
        except Exception as e:
            import traceback
            print(f"[BalancedPipeline] Analysis failed: {e}")
            traceback.print_exc()
            # Use default analysis
            analysis = self._default_analysis(routes_data)

        self._report_progress("classification", 80, "Building route classifications...")

        # Build tactical routes
        tactical_routes = [
            self._build_tactical_route(route_data, analysis)
            for route_data in routes_data
        ]

        self._report_progress("classification", 95, "Finalizing plan...")

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
                f"Use Route {recommended_id} ({tactical_routes[recommended_id-1].name})" if tactical_routes else "No routes generated",
                f"Obstacles detected via {detector_name} (GPU-accelerated)" if self._use_sam else "Obstacles detected via Gemini Vision API",
                "Routes generated using A* pathfinding on obstacle grid"
            ],
            detection_debug=detection_debug if detection_debug else None
        )

        self._report_progress("complete", 100, "Tactical plan ready!")

        return response
