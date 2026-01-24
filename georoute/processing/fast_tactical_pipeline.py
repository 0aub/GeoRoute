"""
Fast Tactical Pipeline - Optimized for speed.

This pipeline is designed to generate tactical routes quickly by:
1. Using geometric route generation (no heavy A* or OSM queries)
2. Combining all Gemini analysis into a single API call
3. Minimal elevation sampling
4. No building detection (suitable for open terrain operations)

Use this for tactical planning in desert/open areas where buildings are not a concern.
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
    BacklogEntry,
    APICall,
)
from ..storage.backlog import get_backlog_store
from ..utils.geo_validator import GulfRegionValidator


class FastTacticalPipeline:
    """
    Fast tactical route planning - optimized for speed over precision.

    Best for:
    - Desert/open terrain operations
    - Quick tactical assessments
    - Areas without complex building layouts
    """

    def __init__(
        self,
        gmaps_client: GoogleMapsClient,
        gemini_client: TacticalGeminiClient,
    ):
        self.gmaps = gmaps_client
        self.gemini = gemini_client
        self.api_calls: list[APICall] = []
        self.backlog = get_backlog_store()
        self._progress_callback: Optional[Callable[[str, int, str], None]] = None

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

    def _generate_route_waypoints(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        route_type: str,
        num_waypoints: int = 10
    ) -> list[dict]:
        """
        Generate route waypoints geometrically.

        Route types:
        - direct: Straight line with minor variations
        - flanking_left: Curves left to approach from flank
        - flanking_right: Curves right to approach from flank
        """
        waypoints = []

        start_lat, start_lon = start
        end_lat, end_lon = end

        for i in range(num_waypoints):
            t = i / (num_waypoints - 1)  # 0 to 1

            # Base interpolation
            lat = start_lat + t * (end_lat - start_lat)
            lon = start_lon + t * (end_lon - start_lon)

            # Apply route-specific deviations
            if route_type == "flanking_left":
                # Curve to the left (perpendicular offset)
                offset = math.sin(t * math.pi) * 0.002  # ~200m max deviation
                # Perpendicular direction (rotate 90 degrees)
                dx = end_lon - start_lon
                dy = end_lat - start_lat
                length = math.sqrt(dx*dx + dy*dy)
                if length > 0:
                    lat += (-dx / length) * offset
                    lon += (dy / length) * offset

            elif route_type == "flanking_right":
                # Curve to the right
                offset = math.sin(t * math.pi) * 0.002
                dx = end_lon - start_lon
                dy = end_lat - start_lat
                length = math.sqrt(dx*dx + dy*dy)
                if length > 0:
                    lat += (dx / length) * offset
                    lon += (-dy / length) * offset
            else:
                # Direct route with small random variations
                lat += random.uniform(-0.0002, 0.0002)
                lon += random.uniform(-0.0002, 0.0002)

            # Calculate distance from start
            distance = self._haversine_distance(start_lat, start_lon, lat, lon)

            waypoints.append({
                "lat": lat,
                "lon": lon,
                "elevation_m": 0.0,  # Will be filled later if needed
                "distance_from_start_m": distance,
                "terrain_type": "open_terrain",
                "risk_level": "moderate",
                "reasoning": "Open terrain movement",
            })

        return waypoints

    async def _get_satellite_image_fast(self, bounds: dict, zoom: int = 14) -> Optional[str]:
        """Get satellite image quickly."""
        center_lat = (bounds["north"] + bounds["south"]) / 2
        center_lon = (bounds["east"] + bounds["west"]) / 2

        try:
            image_bytes = await self.gmaps.get_satellite_image(
                center=(center_lat, center_lon),
                zoom=min(zoom, 15),  # Cap zoom for faster response
                size="640x640"
            )
            if image_bytes:
                return base64.b64encode(image_bytes).decode("utf-8")
        except Exception:
            pass
        return None

    async def _analyze_routes_combined(
        self,
        routes_data: list[dict],
        enemies: list[TacticalUnit],
        satellite_image: Optional[str]
    ) -> dict:
        """
        Single Gemini call to analyze all routes at once.

        Combines what was previously 3 separate calls into 1.
        """
        prompt = f"""Analyze these {len(routes_data)} tactical routes for military movement.

ROUTES:
{self._format_routes_for_prompt(routes_data)}

ENEMY POSITIONS:
{self._format_enemies_for_prompt(enemies)}

For EACH route, provide:
1. Risk assessment for each waypoint segment (safe/moderate/high/critical)
2. Scores: time_to_target (0-100), stealth_score (0-100), survival_probability (0-100)
3. Final verdict: SUCCESS (viable), RISK (proceed with caution), or FAILED (not recommended)
4. Brief tactical reasoning

Respond in JSON format:
{{
  "routes": [
    {{
      "route_id": 1,
      "name": "Route name",
      "segment_risks": ["safe", "moderate", "high", ...],
      "scores": {{
        "time_to_target": 75,
        "stealth_score": 60,
        "survival_probability": 80
      }},
      "verdict": "SUCCESS",
      "reasoning": "Brief tactical assessment",
      "detection_probability": 0.3
    }},
    ...
  ]
}}
"""
        try:
            response = await self.gemini._call_gemini(
                prompt=prompt,
                image_base64=satellite_image,
                response_format="json"
            )

            # Parse response
            import json
            return json.loads(response)

        except Exception as e:
            print(f"[FastPipeline] Gemini analysis failed: {e}")
            # Return default analysis
            return self._default_analysis(routes_data)

    def _format_routes_for_prompt(self, routes: list[dict]) -> str:
        """Format routes for Gemini prompt."""
        lines = []
        for route in routes:
            lines.append(f"Route {route['route_id']}: {route['name']}")
            lines.append(f"  Waypoints: {len(route['waypoints'])}")
            if route['waypoints']:
                start = route['waypoints'][0]
                end = route['waypoints'][-1]
                lines.append(f"  Start: ({start['lat']:.4f}, {start['lon']:.4f})")
                lines.append(f"  End: ({end['lat']:.4f}, {end['lon']:.4f})")
        return "\n".join(lines)

    def _format_enemies_for_prompt(self, enemies: list[TacticalUnit]) -> str:
        """Format enemy positions for Gemini prompt."""
        if not enemies:
            return "No enemy positions specified"

        lines = []
        for i, enemy in enumerate(enemies):
            lines.append(f"Enemy {i+1}: ({enemy.lat:.4f}, {enemy.lon:.4f})")
        return "\n".join(lines)

    def _default_analysis(self, routes: list[dict]) -> dict:
        """Default analysis when Gemini fails."""
        return {
            "routes": [
                {
                    "route_id": route["route_id"],
                    "name": route["name"],
                    "segment_risks": ["moderate"] * len(route["waypoints"]),
                    "scores": {
                        "time_to_target": 70,
                        "stealth_score": 60,
                        "survival_probability": 70
                    },
                    "verdict": "RISK",
                    "reasoning": "Analysis unavailable - proceed with caution",
                    "detection_probability": 0.5
                }
                for route in routes
            ]
        }

    def _build_tactical_route(
        self,
        route_data: dict,
        analysis: dict
    ) -> TacticalRoute:
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
            risk = segment_risks[i] if i < len(segment_risks) else "moderate"
            waypoints.append(DetailedWaypoint(
                lat=wp["lat"],
                lon=wp["lon"],
                elevation_m=wp.get("elevation_m", 0.0),
                distance_from_start_m=wp.get("distance_from_start_m", 0.0),
                terrain_type="open_terrain",
                risk_level=RiskLevel(risk),
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
                estimated_time_seconds=distance / 1.5,  # ~1.5 m/s walking
                risk_factors=["Open terrain movement"]
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

        total_distance = sum(s.distance_m for s in segments)

        return TacticalRoute(
            route_id=route_data["route_id"],
            name=route_data["name"],
            description=route_data.get("description", ""),
            waypoints=waypoints,
            segments=segments,
            classification=classification,
            total_distance_m=total_distance,
            estimated_duration_seconds=total_distance / 1.5,
            elevation_gain_m=0.0,
            elevation_loss_m=0.0
        )

    async def plan_tactical_attack(
        self,
        request: TacticalPlanRequest
    ) -> TacticalPlanResponse:
        """
        Fast tactical planning - optimized for speed.
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

        self._report_progress("terrain", 15, "Calculating positions...")

        # Calculate start/end positions
        start_lat = sum(s.lat for s in request.soldiers) / len(request.soldiers)
        start_lon = sum(s.lon for s in request.soldiers) / len(request.soldiers)
        target_lat = sum(e.lat for e in request.enemies) / len(request.enemies)
        target_lon = sum(e.lon for e in request.enemies) / len(request.enemies)

        self._report_progress("imagery", 25, "Fetching satellite imagery...")

        # Get satellite image (quick)
        satellite_image = await self._get_satellite_image_fast(request.bounds, request.zoom or 14)

        self._report_progress("routes", 40, "Generating tactical routes...")

        # Generate 3 routes geometrically (FAST - no OSM or A*)
        routes_data = [
            {
                "route_id": 1,
                "name": "Direct Assault",
                "description": "Shortest path to target",
                "waypoints": self._generate_route_waypoints(
                    (start_lat, start_lon),
                    (target_lat, target_lon),
                    "direct"
                )
            },
            {
                "route_id": 2,
                "name": "Left Flank",
                "description": "Approach from the left flank",
                "waypoints": self._generate_route_waypoints(
                    (start_lat, start_lon),
                    (target_lat, target_lon),
                    "flanking_left"
                )
            },
            {
                "route_id": 3,
                "name": "Right Flank",
                "description": "Approach from the right flank",
                "waypoints": self._generate_route_waypoints(
                    (start_lat, start_lon),
                    (target_lat, target_lon),
                    "flanking_right"
                )
            }
        ]

        self._report_progress("risk", 60, "AI analyzing tactical risks (single pass)...")

        # Single Gemini call for all analysis (FAST - 1 call instead of 3)
        analysis = await self._analyze_routes_combined(
            routes_data,
            request.enemies,
            satellite_image
        )

        self._report_progress("classification", 85, "Building route classifications...")

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
        success_count = sum(1 for r in tactical_routes if r.classification.final_verdict == RouteVerdict.SUCCESS)
        if success_count == 3:
            assessment = "All routes viable. Mission has high probability of success."
        elif success_count > 0:
            assessment = f"{success_count} of 3 routes viable. Proceed with caution."
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
                f"Use Route {recommended_id} ({tactical_routes[recommended_id-1].name})",
                "Maintain tactical spacing",
                "Monitor enemy movements"
            ]
        )

        self._report_progress("complete", 100, "Tactical plan ready!")

        return response
