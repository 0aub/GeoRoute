"""
Complete terrain-aware military route optimization pipeline.

Integrates:
- Google Maps (elevation, satellite, roads)
- Gemini API (intelligent route planning)
- OSRM (route validation)
- OpenRouteService (elevation profiles)
"""

import math
import logging
from typing import Optional

from ..config import Config
from ..clients.google_maps import GoogleMapsClient
from ..clients.gemini import GeminiRoutePlanner
from ..clients.osrm import OSRMValidator
from ..clients.openrouteservice import OpenRouteServiceValidator
from ..models.vehicles import VehicleProfile
from ..models.routing import RoutingDecision

logger = logging.getLogger(__name__)


class MilitaryRoutePipeline:
    """
    Complete terrain-aware military route optimization pipeline.
    """

    def __init__(self, config: Config):
        self.config = config

        # Initialize required clients
        self.maps = GoogleMapsClient(config.google_maps_api_key)
        self.gemini = GeminiRoutePlanner(config.gemini_api_key)
        self.osrm = OSRMValidator()

        # Initialize optional client
        self.ors = (
            OpenRouteServiceValidator(config.ors_api_key)
            if config.ors_api_key
            else None
        )

    async def close(self):
        """Close all HTTP clients."""
        await self.maps.close()
        await self.osrm.close()
        if self.ors:
            await self.ors.close()

    async def test_all_apis(self) -> dict[str, bool]:
        """Test connectivity to all APIs."""
        results = {
            "google_maps": await self.maps.test_connection(),
            "gemini": await self.gemini.test_connection(),
            "osrm": await self.osrm.test_connection(),
        }

        if self.ors:
            results["ors"] = await self.ors.test_connection()
        else:
            results["ors"] = False

        return results

    async def collect_geospatial_data(
        self,
        center: tuple[float, float],
        radius_km: float = 2.0,
    ) -> dict:
        """
        Collect all geospatial data for a region.

        Args:
            center: (lat, lon) center point
            radius_km: Radius of analysis area

        Returns:
            Comprehensive geospatial dataset
        """
        # Calculate bounds
        lat_offset = radius_km / 111.0
        lon_offset = radius_km / (111.0 * math.cos(math.radians(center[0])))

        bounds = (
            center[0] - lat_offset,  # south
            center[0] + lat_offset,  # north
            center[1] - lon_offset,  # west
            center[1] + lon_offset,  # east
        )

        result = {
            "center": center,
            "radius_km": radius_km,
            "bounds": {
                "south": bounds[0],
                "north": bounds[1],
                "west": bounds[2],
                "east": bounds[3],
            },
        }

        # Get satellite imagery
        logger.info("Fetching satellite imagery...")
        result["satellite_image"] = await self.maps.get_satellite_image(
            center, zoom=13, size="640x640", scale=2
        )

        # Get terrain imagery
        logger.info("Fetching terrain map...")
        result["terrain_image"] = await self.maps.get_terrain_image(center, zoom=12)

        # Get elevation grid
        logger.info("Fetching elevation data...")
        elevation_grid = await self.maps.get_elevation_grid(bounds, grid_size=15)
        result["elevation"] = {
            "source": "Google Elevation API",
            "resolution_m": 30,
            "statistics": elevation_grid.get("statistics", {}),
        }

        return result

    async def plan_route(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        vehicle: VehicleProfile,
        waypoints: list[tuple[float, float]] = None,
        no_go_zones: list[list[tuple[float, float]]] = None,
    ) -> dict:
        """
        Plan an optimal route with full terrain analysis.

        Args:
            start: (lat, lon) origin
            end: (lat, lon) destination
            vehicle: Vehicle profile with capabilities
            waypoints: Optional intermediate waypoints
            no_go_zones: List of polygon coordinates to avoid

        Returns:
            Complete route plan with validation
        """
        logger.info(f"Planning route for {vehicle.name}")
        logger.info(f"From: {start} To: {end}")

        # Step 1: Collect geospatial data
        center = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        route_distance_km = self._haversine_km(start[0], start[1], end[0], end[1])
        radius_km = max(route_distance_km * 0.75, 1.5)  # Min 1.5km for tactical movement

        logger.info(f"Collecting geospatial data (radius: {radius_km:.1f} km)...")
        geo_data = await self.collect_geospatial_data(center, radius_km)

        # Step 2: Get baseline road route
        logger.info("Getting baseline road route...")
        wp_tuples = [(w[0], w[1]) for w in waypoints] if waypoints else None
        road_route = await self.maps.get_road_route(start, end, wp_tuples)

        # Step 3: Build structured context for Gemini
        logger.info("Building terrain context...")
        vehicle_dict = vehicle.to_dict()

        geospatial_context = {
            "region": geo_data.get("bounds", {}),
            "elevation": geo_data.get("elevation", {}),
            "road_network": {
                "baseline_route": {
                    "distance_m": (
                        road_route.get("distance_m", 0)
                        if road_route.get("success")
                        else None
                    ),
                    "duration_s": (
                        road_route.get("duration_s", 0)
                        if road_route.get("success")
                        else None
                    ),
                    "available": road_route.get("success", False),
                }
            },
        }

        if no_go_zones:
            geospatial_context["no_go_zones"] = no_go_zones

        # Step 4: Generate route with Gemini
        logger.info("Generating route with Gemini...")

        if not geo_data.get("satellite_image"):
            return {
                "status": "error",
                "error": "Failed to fetch satellite imagery",
            }

        routing_decision = self.gemini.plan_route(
            satellite_image=geo_data["satellite_image"],
            terrain_image=geo_data.get("terrain_image"),
            geospatial_data=geospatial_context,
            start_point=start,
            end_point=end,
            vehicle_profile=vehicle_dict,
            additional_constraints={"no_go_zones": no_go_zones} if no_go_zones else None,
        )

        # Step 5: Validate route
        logger.info("Validating route...")

        # Extract waypoint coordinates for validation (OSRM uses lon, lat)
        route_coords = [
            (wp.lon, wp.lat) for wp in routing_decision.waypoints
        ]

        # OSRM validation
        osrm_validation = await self.osrm.validate_route(route_coords)

        # ORS validation if available
        ors_validation = None
        if self.ors and len(route_coords) >= 2:
            ors_validation = await self.ors.validate_elevation_constraints(
                route_coords, max_slope_degrees=vehicle.max_slope_degrees
            )

        # Step 6: Compile results
        result = {
            "status": "success",
            "route_plan": routing_decision.model_dump(),
            "validation": {
                "osrm": osrm_validation,
                "openrouteservice": ors_validation,
            },
            "geospatial_summary": {
                "bounds": geo_data.get("bounds"),
                "elevation_stats": geo_data.get("elevation", {}).get("statistics"),
            },
            "vehicle_used": vehicle_dict,
        }

        logger.info(f"Route planning complete: {routing_decision.total_distance_km:.2f} km")

        return result

    async def quick_assessment(
        self,
        center: tuple[float, float],
        radius_km: float = 2.0,
    ) -> dict:
        """
        Quick terrain assessment without full route planning.
        Useful for initial reconnaissance.
        """
        # Get satellite image
        sat_image = await self.maps.get_satellite_image(center, zoom=13)

        if not sat_image:
            return {"status": "error", "error": "Failed to fetch satellite imagery"}

        # Get basic elevation data
        lat_off = radius_km / 111
        lon_off = radius_km / (111 * math.cos(math.radians(center[0])))
        bounds = (
            center[0] - lat_off,
            center[0] + lat_off,
            center[1] - lon_off,
            center[1] + lon_off,
        )

        elevation = await self.maps.get_elevation_grid(bounds, grid_size=10)

        # Quick Gemini analysis
        assessment = self.gemini.analyze_terrain_only(sat_image, bounds)

        return {
            "status": "success",
            "center": center,
            "radius_km": radius_km,
            "elevation_summary": elevation.get("statistics", {}),
            "terrain_assessment": assessment,
        }

    def _haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in kilometers."""
        R = 6371
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        return 2 * R * math.asin(math.sqrt(a))
