"""
MCP_Geometric Pathfinder for tactical route planning.

Uses scikit-image's MCP_Geometric algorithm for least-cost path analysis
through terrain cost surfaces. This provides accurate, realistic routes
that properly avoid obstacles like buildings and water.
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass

import numpy as np
from skimage.graph import MCP_Geometric, route_through_array
from shapely.geometry import LineString
import rasterio

from georoute.clients.terrain_data import TerrainDataClient, TerrainData


@dataclass
class PathResult:
    """Result of pathfinding operation."""
    waypoints: List[Tuple[float, float]]  # List of (lon, lat) coordinates
    total_cost: float                      # Total travel cost
    travel_time_hours: float              # Estimated travel time in hours
    distance_meters: float                # Total distance in meters
    path_valid: bool                      # Whether a valid path was found


class MCPPathfinder:
    """
    Pathfinder using MCP_Geometric algorithm with real terrain data.

    This class provides accurate tactical route planning by:
    1. Fetching real terrain data (ESA WorldCover, Copernicus DEM)
    2. Creating cost surfaces based on land cover and slope
    3. Finding least-cost paths using MCP_Geometric
    4. Simplifying and densifying paths for practical use
    """

    def __init__(self, terrain_client: Optional[TerrainDataClient] = None):
        """Initialize the pathfinder."""
        self.terrain_client = terrain_client or TerrainDataClient()

    def geo_to_pixel(
        self,
        lon: float,
        lat: float,
        transform: rasterio.Affine
    ) -> Tuple[int, int]:
        """
        Convert geographic coordinates to pixel indices.

        Args:
            lon: Longitude
            lat: Latitude
            transform: Rasterio affine transform

        Returns:
            Tuple of (row, col) pixel indices
        """
        inv_transform = ~transform
        col, row = inv_transform * (lon, lat)
        return int(row), int(col)

    def pixel_to_geo(
        self,
        row: int,
        col: int,
        transform: rasterio.Affine
    ) -> Tuple[float, float]:
        """
        Convert pixel indices to geographic coordinates.

        Args:
            row: Row index
            col: Column index
            transform: Rasterio affine transform

        Returns:
            Tuple of (lon, lat) coordinates
        """
        lon, lat = rasterio.transform.xy(transform, row, col, offset='center')
        return lon, lat

    def find_path(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        terrain: TerrainData,
        allow_diagonal: bool = True
    ) -> PathResult:
        """
        Find least-cost path between two points.

        Args:
            start: (lon, lat) start coordinates
            end: (lon, lat) end coordinates
            terrain: TerrainData object with cost surface

        Returns:
            PathResult with waypoints and statistics
        """
        print(f"[MCPPathfinder] Finding path from {start} to {end}")

        # Convert coordinates to pixel indices
        start_row, start_col = self.geo_to_pixel(start[0], start[1], terrain.transform)
        end_row, end_col = self.geo_to_pixel(end[0], end[1], terrain.transform)

        print(f"[MCPPathfinder] Start pixel: ({start_row}, {start_col})")
        print(f"[MCPPathfinder] End pixel: ({end_row}, {end_col})")
        print(f"[MCPPathfinder] Cost surface shape: {terrain.cost_surface.shape}")

        # Validate pixel coordinates
        height, width = terrain.cost_surface.shape
        if not (0 <= start_row < height and 0 <= start_col < width):
            print(f"[MCPPathfinder] Start point outside bounds")
            return self._create_fallback_path(start, end)

        if not (0 <= end_row < height and 0 <= end_col < width):
            print(f"[MCPPathfinder] End point outside bounds")
            return self._create_fallback_path(start, end)

        # Handle infinite costs by replacing with very high value
        # MCP doesn't handle inf well
        cost_finite = np.where(
            np.isinf(terrain.cost_surface),
            1e10,
            terrain.cost_surface
        )

        # Check if start/end are impassable
        if cost_finite[start_row, start_col] >= 1e10:
            print(f"[MCPPathfinder] Start point is impassable, finding nearest passable")
            start_row, start_col = self._find_nearest_passable(
                start_row, start_col, cost_finite
            )

        if cost_finite[end_row, end_col] >= 1e10:
            print(f"[MCPPathfinder] End point is impassable, finding nearest passable")
            end_row, end_col = self._find_nearest_passable(
                end_row, end_col, cost_finite
            )

        try:
            # Use route_through_array for simple pathfinding
            path_pixels, total_cost = route_through_array(
                cost_finite,
                start=(start_row, start_col),
                end=(end_row, end_col),
                fully_connected=allow_diagonal,
                geometric=True
            )

            print(f"[MCPPathfinder] Found path with {len(path_pixels)} points, cost: {total_cost:.2f}")

            # Convert pixel path to geographic coordinates
            waypoints = []
            for row, col in path_pixels:
                lon, lat = self.pixel_to_geo(row, col, terrain.transform)
                waypoints.append((lon, lat))

            # Calculate distance
            distance = self._calculate_distance(waypoints)

            # Estimate travel time based on distance and typical walking speed
            # Average walking speed: ~4 km/h = 4000 m/h (adjusted for terrain)
            # The cost already reflects terrain difficulty, so use it as a multiplier
            avg_cost_per_cell = total_cost / len(path_pixels) if path_pixels else 1.0
            terrain_factor = min(3.0, max(1.0, avg_cost_per_cell / 0.5))  # 1.0-3.0 multiplier
            effective_speed_mh = 4000 / terrain_factor  # m/h
            travel_time_hours = distance / effective_speed_mh

            return PathResult(
                waypoints=waypoints,
                total_cost=total_cost,
                travel_time_hours=travel_time_hours,
                distance_meters=distance,
                path_valid=True
            )

        except Exception as e:
            print(f"[MCPPathfinder] Error finding path: {e}")
            return self._create_fallback_path(start, end)

    def _find_nearest_passable(
        self,
        row: int,
        col: int,
        cost_array: np.ndarray,
        max_search: int = 50
    ) -> Tuple[int, int]:
        """Find nearest passable cell to given position."""
        height, width = cost_array.shape

        for radius in range(1, max_search):
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    if abs(dr) != radius and abs(dc) != radius:
                        continue  # Only check perimeter

                    nr, nc = row + dr, col + dc
                    if 0 <= nr < height and 0 <= nc < width:
                        if cost_array[nr, nc] < 1e10:
                            return nr, nc

        # No passable cell found, return original
        return row, col

    def _apply_no_go_zones(
        self,
        terrain: TerrainData,
        no_go_zones: List[Tuple[float, float, float, float]]
    ) -> TerrainData:
        """
        Apply no-go zones to terrain cost surface.

        This marks additional areas as impassable that aren't in the
        2021 ESA WorldCover data (e.g., newly constructed buildings).

        Args:
            terrain: Original TerrainData
            no_go_zones: List of (west, south, east, north) bounding boxes

        Returns:
            Modified TerrainData with blocked zones
        """
        import copy

        # Create a copy of the cost surface
        modified_cost = terrain.cost_surface.copy()

        for zone in no_go_zones:
            west, south, east, north = zone

            # Convert zone bounds to pixel coordinates
            top_left_row, top_left_col = self.geo_to_pixel(west, north, terrain.transform)
            bottom_right_row, bottom_right_col = self.geo_to_pixel(east, south, terrain.transform)

            # Ensure correct ordering (row increases downward)
            min_row = min(top_left_row, bottom_right_row)
            max_row = max(top_left_row, bottom_right_row)
            min_col = min(top_left_col, bottom_right_col)
            max_col = max(top_left_col, bottom_right_col)

            # Clamp to array bounds
            min_row = max(0, min_row)
            max_row = min(terrain.cost_surface.shape[0] - 1, max_row)
            min_col = max(0, min_col)
            max_col = min(terrain.cost_surface.shape[1] - 1, max_col)

            # Mark zone as impassable
            modified_cost[min_row:max_row+1, min_col:max_col+1] = np.inf

            print(f"[MCPPathfinder] Blocked zone: ({min_row}:{max_row}, {min_col}:{max_col})")

        # Return modified terrain
        return TerrainData(
            dem=terrain.dem,
            landcover=terrain.landcover,
            slope=terrain.slope,
            cost_surface=modified_cost,
            transform=terrain.transform,
            crs=terrain.crs,
            cell_size=terrain.cell_size
        )

    def _create_fallback_path(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> PathResult:
        """Create a simple straight-line fallback path."""
        print("[MCPPathfinder] Creating fallback straight-line path")

        # Create simple interpolated path
        num_points = 20
        waypoints = []
        for i in range(num_points + 1):
            t = i / num_points
            lon = start[0] + t * (end[0] - start[0])
            lat = start[1] + t * (end[1] - start[1])
            waypoints.append((lon, lat))

        distance = self._calculate_distance(waypoints)

        return PathResult(
            waypoints=waypoints,
            total_cost=0.0,
            travel_time_hours=distance / 4000,  # Assume 4 km/h walking
            distance_meters=distance,
            path_valid=False
        )

    def _calculate_distance(self, waypoints: List[Tuple[float, float]]) -> float:
        """Calculate total distance of path in meters."""
        if len(waypoints) < 2:
            return 0.0

        total = 0.0
        for i in range(1, len(waypoints)):
            total += self._haversine(waypoints[i-1], waypoints[i])

        return total

    def _haversine(
        self,
        coord1: Tuple[float, float],
        coord2: Tuple[float, float]
    ) -> float:
        """Calculate distance between two points in meters using Haversine formula."""
        import math

        lon1, lat1 = coord1
        lon2, lat2 = coord2

        R = 6371000  # Earth radius in meters

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def simplify_path(
        self,
        waypoints: List[Tuple[float, float]],
        tolerance_meters: float = 10.0
    ) -> List[Tuple[float, float]]:
        """
        Simplify path using Douglas-Peucker algorithm.

        Args:
            waypoints: List of (lon, lat) coordinates
            tolerance_meters: Simplification tolerance in meters

        Returns:
            Simplified list of waypoints
        """
        if len(waypoints) < 3:
            return waypoints

        # Convert tolerance from meters to degrees (approximate)
        tolerance_deg = tolerance_meters / 111000

        line = LineString(waypoints)
        simplified = line.simplify(tolerance_deg, preserve_topology=True)

        return list(simplified.coords)

    def densify_path(
        self,
        waypoints: List[Tuple[float, float]],
        interval_meters: float = 50.0
    ) -> List[Tuple[float, float]]:
        """
        Add waypoints at regular intervals along path.

        Args:
            waypoints: List of (lon, lat) coordinates
            interval_meters: Distance between waypoints in meters

        Returns:
            Densified list of waypoints
        """
        if len(waypoints) < 2:
            return waypoints

        line = LineString(waypoints)

        # Convert interval from meters to degrees (approximate)
        interval_deg = interval_meters / 111000

        total_length = line.length
        num_points = max(2, int(total_length / interval_deg))

        densified = []
        for i in range(num_points + 1):
            point = line.interpolate(i / num_points, normalized=True)
            densified.append((point.x, point.y))

        return densified

    def find_tactical_path(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        bounds: Tuple[float, float, float, float],
        simplify_tolerance: float = 10.0,
        waypoint_interval: float = 50.0,
        no_go_zones: Optional[List[Tuple[float, float, float, float]]] = None
    ) -> PathResult:
        """
        Find tactical path with simplification and densification.

        This is the main entry point for tactical route planning.

        Args:
            start: (lon, lat) start coordinates
            end: (lon, lat) end coordinates
            bounds: (west, south, east, north) area bounds
            simplify_tolerance: Douglas-Peucker tolerance in meters
            waypoint_interval: Interval between final waypoints in meters
            no_go_zones: List of (west, south, east, north) bounding boxes to avoid
                         Use this for buildings/obstacles not in 2021 WorldCover data

        Returns:
            PathResult with processed waypoints
        """
        print(f"[MCPPathfinder] Finding tactical path")
        print(f"[MCPPathfinder] Start: {start}, End: {end}")
        print(f"[MCPPathfinder] Bounds: {bounds}")

        # Fetch terrain data
        terrain = self.terrain_client.get_terrain_data(bounds)

        # Apply no-go zones if provided (for buildings not in 2021 WorldCover data)
        if no_go_zones:
            print(f"[MCPPathfinder] Applying {len(no_go_zones)} no-go zones")
            terrain = self._apply_no_go_zones(terrain, no_go_zones)

        # Find raw path
        result = self.find_path(start, end, terrain)

        if not result.path_valid or len(result.waypoints) < 2:
            return result

        # Simplify path
        simplified = self.simplify_path(result.waypoints, simplify_tolerance)
        print(f"[MCPPathfinder] Simplified from {len(result.waypoints)} to {len(simplified)} points")

        # Densify path
        densified = self.densify_path(simplified, waypoint_interval)
        print(f"[MCPPathfinder] Densified to {len(densified)} points at {waypoint_interval}m intervals")

        # Recalculate distance
        distance = self._calculate_distance(densified)

        return PathResult(
            waypoints=densified,
            total_cost=result.total_cost,
            travel_time_hours=result.travel_time_hours,
            distance_meters=distance,
            path_valid=True
        )


def find_tactical_route(
    start_lon: float,
    start_lat: float,
    end_lon: float,
    end_lat: float,
    bounds: Tuple[float, float, float, float],
    waypoint_interval: float = 50.0
) -> List[Tuple[float, float]]:
    """
    Convenience function for finding tactical route.

    Args:
        start_lon, start_lat: Start coordinates
        end_lon, end_lat: End coordinates
        bounds: (west, south, east, north) area bounds
        waypoint_interval: Interval between waypoints in meters

    Returns:
        List of (lon, lat) waypoints
    """
    pathfinder = MCPPathfinder()
    result = pathfinder.find_tactical_path(
        start=(start_lon, start_lat),
        end=(end_lon, end_lat),
        bounds=bounds,
        waypoint_interval=waypoint_interval
    )

    return result.waypoints
