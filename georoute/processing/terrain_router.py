"""
Terrain-Aware Off-Road Router using OSM building detection and pixel-level pathfinding.

This module generates routes that correctly avoid buildings by:
1. Fetching actual building polygons from OpenStreetMap
2. Creating high-resolution obstacle masks with buffer zones
3. Using pyastar2d for pixel-level A* pathfinding
4. Smoothing paths with Douglas-Peucker + cubic spline

STRICT: No fallbacks. Routes are generated using real building data only.
If building detection fails, an error is raised.

Model configuration is centralized in config.yaml
"""

import math
from dataclasses import dataclass
from typing import Optional

# Import building detection and pixel pathfinding modules
from .building_detector import BuildingDetector, BuildingDetectionResult, OSMNX_AVAILABLE
from .pixel_pathfinder import PixelPathfinder, PathfindingResult, PYASTAR_AVAILABLE


@dataclass
class TerrainRoute:
    """A route generated through terrain analysis"""
    route_id: int
    name: str
    description: str
    waypoints: list[dict]
    total_distance_m: float
    terrain_distribution: dict  # terrain_type -> percentage
    avg_passability: float


class TerrainRouter:
    """
    Terrain router using OSM building detection and pixel-level pathfinding.

    STRICT APPROACH:
    - Uses OpenStreetMap building footprints for accurate obstacle detection
    - Uses pyastar2d for high-resolution A* pathfinding
    - Creates buffer zones around buildings (2-5m default)
    - NO FALLBACKS - if building detection or pathfinding fails, error is raised

    This replaces the previous approach which used ESA WorldCover (10m resolution)
    that could not detect individual buildings.
    """

    def __init__(
        self,
        gemini_api_key: str = None,  # Kept for API compatibility, not used
        buffer_meters: float = 3.0,
        resolution_meters: float = 1.0,
        waypoint_interval_meters: float = 5.0
    ):
        """
        Initialize the terrain router.

        Args:
            gemini_api_key: Not used (kept for API compatibility)
            buffer_meters: Safety buffer around buildings (2-5m recommended)
            resolution_meters: Resolution of obstacle mask (1m default)
            waypoint_interval_meters: Spacing between output waypoints
        """
        # Validate dependencies
        if not OSMNX_AVAILABLE:
            raise ImportError(
                "OSMnx is required for building detection. "
                "Install with: pip install osmnx geopandas"
            )

        if not PYASTAR_AVAILABLE:
            raise ImportError(
                "pyastar2d is required for pathfinding. "
                "Install with: pip install pyastar2d"
            )

        self.buffer_meters = buffer_meters
        self.resolution_meters = resolution_meters
        self.waypoint_interval_meters = waypoint_interval_meters

        # Initialize building detector and pathfinder
        self.building_detector = BuildingDetector(
            buffer_meters=buffer_meters,
            resolution_meters=resolution_meters
        )
        self.pathfinder = PixelPathfinder(
            buffer_meters=buffer_meters,
            waypoint_interval_meters=waypoint_interval_meters
        )

        print(f"[TerrainRouter] Initialized with OSM building detection + pyastar2d pathfinding")
        print(f"[TerrainRouter] Buffer: {buffer_meters}m, Resolution: {resolution_meters}m, "
              f"Waypoint interval: {waypoint_interval_meters}m")

    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in meters"""
        R = 6371000  # Earth radius in meters

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    async def generate_terrain_routes(
        self,
        satellite_image_base64: str,  # Not used - kept for API compatibility
        bounds: dict,
        start: tuple[float, float],
        end: tuple[float, float],
        elevation_data: list[dict],
        num_routes: int = 3,
        zoom_level: int = 14
    ) -> list[TerrainRoute]:
        """
        Generate multiple off-road routes using OSM building detection.

        STRICT: Uses real OSM building data for obstacle detection.
        NO FALLBACKS - if detection fails, raises error.

        Args:
            satellite_image_base64: Not used (kept for API compatibility)
            bounds: {"north": lat, "south": lat, "east": lon, "west": lon}
            start: (lat, lon) start position
            end: (lat, lon) end position
            elevation_data: Elevation samples for the area
            num_routes: Number of route variants to generate
            zoom_level: Map zoom level (affects building detection area size)

        Returns:
            List of TerrainRoute objects
        """
        print(f"[TerrainRouter] Generating {num_routes} routes using OSM building detection")
        print(f"[TerrainRouter] Start: {start}, End: {end}")
        print(f"[TerrainRouter] Zoom level: {zoom_level}")

        # Calculate route-corridor bounds based on zoom level
        # Higher zoom = smaller visible area = smaller query area needed
        # Zoom 14: ~500m buffer, Zoom 19: ~50m buffer
        # Buffer decreases by half for each zoom level increase
        base_buffer_deg = 0.005  # ~500m at zoom 14
        zoom_factor = 2 ** (zoom_level - 14)  # 1 at zoom 14, 32 at zoom 19
        route_buffer_deg = max(base_buffer_deg / zoom_factor, 0.0005)  # Min ~50m

        print(f"[TerrainRouter] Route buffer: {route_buffer_deg:.6f} degrees (~{route_buffer_deg * 111000:.0f}m)")

        min_lat = min(start[0], end[0]) - route_buffer_deg
        max_lat = max(start[0], end[0]) + route_buffer_deg
        min_lon = min(start[1], end[1]) - route_buffer_deg
        max_lon = max(start[1], end[1]) + route_buffer_deg

        # Convert to tuple format (west, south, east, north)
        bounds_tuple = (min_lon, min_lat, max_lon, max_lat)
        print(f"[TerrainRouter] Using route corridor bounds: {bounds_tuple}")

        # Step 1: Detect buildings from OSM
        print("[TerrainRouter] Step 1: Detecting buildings from OpenStreetMap...")
        try:
            detection_result = self.building_detector.detect_buildings(bounds_tuple)
        except Exception as e:
            raise ValueError(f"Building detection failed: {e}")

        print(f"[TerrainRouter] Detected {detection_result.building_count} buildings")

        # Step 2: Generate routes with different configurations
        routes = []

        # Route configurations
        route_configs = [
            {
                "name": "Direct Route",
                "description": "Shortest path avoiding all buildings (OSM data)",
                "buffer_extra": 0.0,  # Use default buffer
                "waypoint_interval": 5.0,
            },
            {
                "name": "Safe Route",
                "description": "Wider margins around obstacles (OSM data + extra buffer)",
                "buffer_extra": 2.0,  # Extra 2m buffer
                "waypoint_interval": 5.0,
            },
            {
                "name": "Tactical Route",
                "description": "Balanced path for military movement (OSM data)",
                "buffer_extra": 1.0,  # Slight extra buffer
                "waypoint_interval": 3.0,  # Denser waypoints
            }
        ]

        for i, config in enumerate(route_configs[:num_routes]):
            print(f"[TerrainRouter] Generating route {i+1}: {config['name']}")

            try:
                route = await self._generate_single_route(
                    detection_result=detection_result,
                    start=start,
                    end=end,
                    elevation_data=elevation_data,
                    route_id=i + 1,
                    config=config
                )

                if route:
                    routes.append(route)
                    print(f"[TerrainRouter] Route {i+1}: {len(route.waypoints)} waypoints, "
                          f"{route.total_distance_m:.0f}m")
                else:
                    print(f"[TerrainRouter] Route {i+1}: Failed to generate")

            except Exception as e:
                print(f"[TerrainRouter] Route {i+1} generation failed: {e}")
                # STRICT: Re-raise the error - no fallbacks
                raise

        if not routes:
            raise ValueError(
                "No routes could be generated. The area may be completely blocked by buildings. "
                "Try expanding the search area or checking if there is a valid path."
            )

        print(f"[TerrainRouter] Successfully generated {len(routes)} routes")
        return routes

    async def _generate_single_route(
        self,
        detection_result: BuildingDetectionResult,
        start: tuple[float, float],
        end: tuple[float, float],
        elevation_data: list[dict],
        route_id: int,
        config: dict
    ) -> Optional[TerrainRoute]:
        """
        Generate a single route using pixel pathfinding.

        Args:
            detection_result: Building detection result with obstacle mask
            start: (lat, lon) start position
            end: (lat, lon) end position
            elevation_data: Elevation samples
            route_id: Route identifier
            config: Route configuration

        Returns:
            TerrainRoute or None if pathfinding fails
        """
        # Use buffered mask for pathfinding (includes safety margins)
        obstacle_mask = detection_result.buffered_mask

        # If extra buffer is requested, expand the mask
        if config.get("buffer_extra", 0) > 0:
            from scipy.ndimage import binary_dilation
            import numpy as np

            extra_pixels = int(config["buffer_extra"] / detection_result.resolution_m)
            if extra_pixels > 0:
                # Create structuring element for dilation
                struct = np.ones((extra_pixels * 2 + 1, extra_pixels * 2 + 1), dtype=bool)
                obstacle_mask = binary_dilation(obstacle_mask, structure=struct).astype(np.uint8)

        # Adjust pathfinder waypoint interval if specified
        original_interval = self.pathfinder.waypoint_interval_meters
        if config.get("waypoint_interval"):
            self.pathfinder.waypoint_interval_meters = config["waypoint_interval"]

        try:
            # Convert start/end from (lat, lon) to (lon, lat) for pathfinder
            start_gps = (start[1], start[0])  # (lon, lat)
            end_gps = (end[1], end[0])  # (lon, lat)

            # Find path
            path_result = self.pathfinder.find_tactical_path(
                obstacle_mask=obstacle_mask,
                start_gps=start_gps,
                goal_gps=end_gps,
                bounds_utm=detection_result.bounds_utm,
                utm_crs=detection_result.utm_crs,
                resolution_meters=detection_result.resolution_m
            )

        finally:
            # Restore original interval
            self.pathfinder.waypoint_interval_meters = original_interval

        if not path_result.path_valid:
            raise ValueError(
                f"Pathfinding failed: {path_result.error_message or 'No valid path found'}"
            )

        # Convert waypoints to route format
        waypoints = []
        total_distance = 0.0

        for i, (lon, lat) in enumerate(path_result.waypoints):
            # Calculate distance from start
            if i > 0:
                prev_lon, prev_lat = path_result.waypoints[i-1]
                segment_dist = self._haversine_distance(prev_lat, prev_lon, lat, lon)
                total_distance += segment_dist

            # Get elevation from nearest sample
            elevation = self._get_nearest_elevation(lat, lon, elevation_data)

            waypoints.append({
                "lat": lat,
                "lon": lon,
                "elevation_m": elevation,
                "distance_from_start_m": total_distance,
                "terrain_type": "traversable",  # All waypoints are on traversable terrain
                "passability": 0.8,  # Path was found through passable terrain
                "obstacles": []
            })

        # Calculate terrain distribution
        # Since we're avoiding all buildings, terrain is 100% traversable
        terrain_distribution = {
            "traversable": 100.0
        }

        return TerrainRoute(
            route_id=route_id,
            name=config["name"],
            description=config["description"],
            waypoints=waypoints,
            total_distance_m=path_result.distance_meters,
            terrain_distribution=terrain_distribution,
            avg_passability=0.8
        )

    def _get_nearest_elevation(
        self,
        lat: float,
        lon: float,
        elevation_data: list[dict]
    ) -> float:
        """Find elevation at nearest sample point"""
        if not elevation_data:
            return 0.0

        min_distance = float('inf')
        nearest_elevation = 0.0

        for sample in elevation_data:
            dist = self._haversine_distance(
                lat, lon,
                sample.get("lat", 0), sample.get("lon", 0)
            )
            if dist < min_distance:
                min_distance = dist
                nearest_elevation = sample.get("elevation_m", 0.0)

        return nearest_elevation


# Legacy compatibility - these are no longer used but kept for import compatibility
class TerrainType:
    """Legacy terrain type enum - kept for compatibility"""
    ROAD = 1.0
    PATH = 0.95
    GRASS = 0.8
    DIRT = 0.75
    SAND = 0.6
    GRAVEL = 0.7
    ROCKY = 0.4
    WATER = 0.0
    BUILDING = 0.0
    CLIFF = 0.0
    VEGETATION_LIGHT = 0.7
    VEGETATION_DENSE = 0.3
    UNKNOWN = 0.5


@dataclass
class GridCell:
    """Legacy grid cell - kept for compatibility"""
    row: int
    col: int
    lat: float
    lon: float
    elevation_m: float
    terrain_type: any
    passability: float
    slope_to_neighbors: dict
