"""
High-Resolution Pixel Pathfinder using scikit-image MCP_Geometric.

This module provides pixel-level pathfinding on cost grids, producing
smooth GPS waypoints suitable for tactical movement planning.

Key features:
- Uses scikit-image MCP_Geometric for efficient pathfinding
- Creates graduated cost buffers around obstacles
- Converts pixel paths to GPS coordinates
- Smooths paths with Douglas-Peucker + cubic spline
- Outputs waypoints at configurable intervals (default 5m)
"""

from typing import Tuple, List, Optional
from dataclasses import dataclass
import numpy as np

# scikit-image MCP is always available (part of scikit-image)
from skimage.graph import MCP_Geometric
PYASTAR_AVAILABLE = True  # Using MCP_Geometric as replacement

try:
    from rdp import rdp
    RDP_AVAILABLE = True
except ImportError:
    RDP_AVAILABLE = False
    print("[PixelPathfinder] rdp not available - install with: pip install rdp")

from scipy.ndimage import distance_transform_edt
from scipy.interpolate import CubicSpline
from pyproj import Transformer


@dataclass
class PathfindingResult:
    """Result of pathfinding operation."""
    waypoints: List[Tuple[float, float]]  # List of (lon, lat) GPS coordinates
    pixel_path: np.ndarray  # Raw pixel path
    total_cost: float
    distance_meters: float
    path_valid: bool
    error_message: Optional[str] = None


class PixelPathfinder:
    """
    High-resolution pathfinder using pyastar2d with buffer zones.

    This pathfinder works on pixel-level cost grids, providing much
    higher resolution than the MCP_Geometric approach with ESA WorldCover.
    """

    def __init__(
        self,
        buffer_meters: float = 3.0,
        waypoint_interval_meters: float = 5.0,
        simplify_epsilon: float = 2.0
    ):
        """
        Initialize the pixel pathfinder.

        Args:
            buffer_meters: Buffer zone width around obstacles
            waypoint_interval_meters: Spacing between output waypoints
            simplify_epsilon: Douglas-Peucker simplification tolerance
        """
        if not PYASTAR_AVAILABLE:
            raise ImportError(
                "pyastar2d is required for pixel pathfinding. "
                "Install with: pip install pyastar2d"
            )

        self.buffer_meters = buffer_meters
        self.waypoint_interval_meters = waypoint_interval_meters
        self.simplify_epsilon = simplify_epsilon

    def create_cost_grid(
        self,
        obstacle_mask: np.ndarray,
        resolution_meters: float = 1.0,
        buffer_cost_gradient: bool = True
    ) -> np.ndarray:
        """
        Create weighted cost grid from binary obstacle mask.

        Args:
            obstacle_mask: Binary mask (1 = obstacle, 0 = traversable)
            resolution_meters: Resolution of the mask in meters
            buffer_cost_gradient: Whether to apply graduated costs near obstacles

        Returns:
            Cost grid where obstacles = inf, buffer zones = graduated costs
        """
        buffer_pixels = int(self.buffer_meters / resolution_meters)

        # Initialize cost grid with base cost of 1.0
        cost = np.ones(obstacle_mask.shape, dtype=np.float32)

        # Mark obstacles as impassable (infinity)
        cost[obstacle_mask == 1] = np.inf

        if buffer_cost_gradient and buffer_pixels > 0:
            # Calculate distance transform from obstacles
            walkable = obstacle_mask == 0
            distances = distance_transform_edt(walkable)

            # Within buffer zone: cost increases from 1 to 5 approaching obstacles
            # This makes the pathfinder prefer routes away from obstacles
            in_buffer = (distances > 0) & (distances < buffer_pixels)
            cost[in_buffer] = 1.0 + 4.0 * (1.0 - distances[in_buffer] / buffer_pixels)

        # Statistics
        inf_count = np.sum(np.isinf(cost))
        total = cost.size
        print(f"[PixelPathfinder] Cost grid: {cost.shape}, "
              f"impassable: {inf_count}/{total} ({100*inf_count/total:.1f}%)")

        return cost

    def find_path(
        self,
        cost_grid: np.ndarray,
        start_pixel: Tuple[int, int],
        goal_pixel: Tuple[int, int],
        allow_diagonal: bool = True
    ) -> Tuple[Optional[np.ndarray], float]:
        """
        Find least-cost path using scikit-image MCP_Geometric.

        Args:
            cost_grid: Cost surface (inf = impassable)
            start_pixel: (row, col) start position
            goal_pixel: (row, col) goal position
            allow_diagonal: Whether to allow diagonal movement

        Returns:
            Tuple of (path_array, total_cost) or (None, 0) if no path
        """
        # MCP_Geometric handles inf values but we need float64
        cost_for_mcp = np.where(
            np.isinf(cost_grid),
            1e10,  # Very high cost instead of inf
            cost_grid
        ).astype(np.float64)

        # Validate start/goal are within bounds
        height, width = cost_grid.shape
        if not (0 <= start_pixel[0] < height and 0 <= start_pixel[1] < width):
            print(f"[PixelPathfinder] Start pixel {start_pixel} out of bounds")
            return None, 0

        if not (0 <= goal_pixel[0] < height and 0 <= goal_pixel[1] < width):
            print(f"[PixelPathfinder] Goal pixel {goal_pixel} out of bounds")
            return None, 0

        # Check if start/goal are passable
        if cost_for_mcp[start_pixel[0], start_pixel[1]] >= 1e10:
            # Find nearest passable cell
            start_pixel = self._find_nearest_passable(start_pixel, cost_for_mcp)
            print(f"[PixelPathfinder] Adjusted start to nearest passable: {start_pixel}")

        if cost_for_mcp[goal_pixel[0], goal_pixel[1]] >= 1e10:
            # Find nearest passable cell
            goal_pixel = self._find_nearest_passable(goal_pixel, cost_for_mcp)
            print(f"[PixelPathfinder] Adjusted goal to nearest passable: {goal_pixel}")

        print(f"[PixelPathfinder] Finding path from {start_pixel} to {goal_pixel}")
        print(f"[PixelPathfinder] Grid size: {cost_grid.shape}")

        try:
            # Use MCP_Geometric for pathfinding (supports diagonal movement)
            mcp = MCP_Geometric(cost_for_mcp, fully_connected=allow_diagonal)

            # Find path from start to goal
            # MCP finds path from multiple starts to multiple ends
            cumulative_costs, traceback = mcp.find_costs(
                starts=[start_pixel],
                ends=[goal_pixel]
            )

            # Trace back the path
            path_indices = mcp.traceback(goal_pixel)

            if path_indices is None or len(path_indices) == 0:
                print("[PixelPathfinder] No path found")
                return None, 0

            # Convert to numpy array
            path = np.array(path_indices)

            # Calculate total cost along path
            total_cost = sum(
                cost_for_mcp[int(p[0]), int(p[1])]
                for p in path
            )

            print(f"[PixelPathfinder] Found path with {len(path)} points, cost: {total_cost:.2f}")
            return path, total_cost

        except Exception as e:
            print(f"[PixelPathfinder] Pathfinding error: {e}")
            return None, 0

    def _find_nearest_passable(
        self,
        pixel: Tuple[int, int],
        cost_grid: np.ndarray,
        max_search: int = 50
    ) -> Tuple[int, int]:
        """Find nearest passable pixel to given position."""
        height, width = cost_grid.shape
        row, col = pixel

        for radius in range(1, max_search):
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    if abs(dr) != radius and abs(dc) != radius:
                        continue  # Only check perimeter

                    nr, nc = row + dr, col + dc
                    if 0 <= nr < height and 0 <= nc < width:
                        if cost_grid[nr, nc] < 1e10:
                            return (nr, nc)

        return pixel  # Return original if no passable found

    def simplify_path(self, path: np.ndarray) -> np.ndarray:
        """
        Simplify path using Douglas-Peucker algorithm.

        Args:
            path: Nx2 array of pixel coordinates

        Returns:
            Simplified path
        """
        if not RDP_AVAILABLE or len(path) < 3:
            return path

        simplified = rdp(path, epsilon=self.simplify_epsilon)
        print(f"[PixelPathfinder] Simplified: {len(path)} -> {len(simplified)} points")
        return np.array(simplified)

    def smooth_path(
        self,
        path: np.ndarray,
        resolution_meters: float
    ) -> np.ndarray:
        """
        Smooth path with cubic spline and resample at fixed intervals.

        Args:
            path: Nx2 array of pixel coordinates
            resolution_meters: Resolution of pixels in meters

        Returns:
            Smoothed path resampled at waypoint_interval_meters
        """
        if len(path) < 3:
            return path

        # Extract x and y coordinates
        x = path[:, 0].astype(float)
        y = path[:, 1].astype(float)

        # Parameterize by arc length
        dx = np.diff(x)
        dy = np.diff(y)
        distances = np.sqrt(dx**2 + dy**2)
        s = np.concatenate([[0], np.cumsum(distances)])

        # Handle zero-length segments
        if s[-1] < 1e-10:
            return path

        # Fit cubic splines
        try:
            cs_x = CubicSpline(s, x)
            cs_y = CubicSpline(s, y)
        except Exception as e:
            print(f"[PixelPathfinder] Spline fitting failed: {e}")
            return path

        # Resample at fixed intervals (in pixels)
        total_length_pixels = s[-1]
        total_length_meters = total_length_pixels * resolution_meters
        num_waypoints = max(2, int(total_length_meters / self.waypoint_interval_meters) + 1)

        s_new = np.linspace(0, s[-1], num_waypoints)
        smooth_x = cs_x(s_new)
        smooth_y = cs_y(s_new)

        smooth_path = np.column_stack([smooth_x, smooth_y])
        print(f"[PixelPathfinder] Smoothed to {len(smooth_path)} waypoints "
              f"at {self.waypoint_interval_meters}m intervals")

        return smooth_path

    def pixels_to_gps(
        self,
        pixel_path: np.ndarray,
        bounds_utm: Tuple[float, float, float, float],
        utm_crs: str,
        resolution_meters: float
    ) -> List[Tuple[float, float]]:
        """
        Convert pixel path to GPS coordinates.

        Args:
            pixel_path: Nx2 array of (row, col) pixel coordinates
            bounds_utm: (min_x, min_y, max_x, max_y) in UTM
            utm_crs: UTM CRS string (e.g., "EPSG:32638")
            resolution_meters: Resolution of pixels in meters

        Returns:
            List of (lon, lat) GPS coordinates
        """
        # Create transformer from UTM to WGS84
        to_wgs84 = Transformer.from_crs(utm_crs, "EPSG:4326", always_xy=True)

        min_x, min_y, max_x, max_y = bounds_utm
        height = int((max_y - min_y) / resolution_meters)

        gps_waypoints = []
        for row, col in pixel_path:
            # Convert pixel to UTM coordinates
            # Note: row 0 is at max_y (north), row increases southward
            utm_x = min_x + col * resolution_meters
            utm_y = max_y - row * resolution_meters  # Y is inverted

            # Transform to WGS84
            lon, lat = to_wgs84.transform(utm_x, utm_y)
            gps_waypoints.append((lon, lat))

        return gps_waypoints

    def find_tactical_path(
        self,
        obstacle_mask: np.ndarray,
        start_gps: Tuple[float, float],
        goal_gps: Tuple[float, float],
        bounds_utm: Tuple[float, float, float, float],
        utm_crs: str,
        resolution_meters: float = 1.0
    ) -> PathfindingResult:
        """
        Find tactical path from GPS start to GPS goal.

        This is the main entry point for tactical pathfinding.

        Args:
            obstacle_mask: Binary mask (1 = obstacle, 0 = traversable)
            start_gps: (lon, lat) start position
            goal_gps: (lon, lat) goal position
            bounds_utm: (min_x, min_y, max_x, max_y) in UTM
            utm_crs: UTM CRS string
            resolution_meters: Resolution of the mask in meters

        Returns:
            PathfindingResult with GPS waypoints
        """
        print(f"[PixelPathfinder] Finding tactical path")
        print(f"[PixelPathfinder] Start GPS: {start_gps}, Goal GPS: {goal_gps}")

        # Convert GPS to UTM
        from_wgs84 = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)

        min_x, min_y, max_x, max_y = bounds_utm
        height, width = obstacle_mask.shape

        # Convert start/goal to UTM then to pixels
        start_utm = from_wgs84.transform(start_gps[0], start_gps[1])
        goal_utm = from_wgs84.transform(goal_gps[0], goal_gps[1])

        # UTM to pixel conversion (note: row 0 is at max_y)
        start_col = int((start_utm[0] - min_x) / resolution_meters)
        start_row = int((max_y - start_utm[1]) / resolution_meters)

        goal_col = int((goal_utm[0] - min_x) / resolution_meters)
        goal_row = int((max_y - goal_utm[1]) / resolution_meters)

        # Clamp to grid bounds
        start_row = max(0, min(height - 1, start_row))
        start_col = max(0, min(width - 1, start_col))
        goal_row = max(0, min(height - 1, goal_row))
        goal_col = max(0, min(width - 1, goal_col))

        print(f"[PixelPathfinder] Start pixel: ({start_row}, {start_col})")
        print(f"[PixelPathfinder] Goal pixel: ({goal_row}, {goal_col})")

        # Create cost grid with buffer zones
        cost_grid = self.create_cost_grid(obstacle_mask, resolution_meters)

        # Find path
        path, total_cost = self.find_path(
            cost_grid,
            (start_row, start_col),
            (goal_row, goal_col)
        )

        if path is None:
            return PathfindingResult(
                waypoints=[],
                pixel_path=np.array([]),
                total_cost=0,
                distance_meters=0,
                path_valid=False,
                error_message="No path found - area may be completely blocked by obstacles"
            )

        # Simplify path
        simplified = self.simplify_path(path)

        # Smooth path and resample
        smoothed = self.smooth_path(simplified, resolution_meters)

        # Convert to GPS
        gps_waypoints = self.pixels_to_gps(
            smoothed,
            bounds_utm,
            utm_crs,
            resolution_meters
        )

        # Calculate total distance
        total_distance = self._calculate_distance(gps_waypoints)

        print(f"[PixelPathfinder] Final: {len(gps_waypoints)} waypoints, "
              f"{total_distance:.0f}m total distance")

        return PathfindingResult(
            waypoints=gps_waypoints,
            pixel_path=path,
            total_cost=total_cost,
            distance_meters=total_distance,
            path_valid=True
        )

    def _calculate_distance(self, waypoints: List[Tuple[float, float]]) -> float:
        """Calculate total distance of path in meters using Haversine."""
        if len(waypoints) < 2:
            return 0.0

        import math
        R = 6371000  # Earth radius in meters

        total = 0.0
        for i in range(1, len(waypoints)):
            lon1, lat1 = waypoints[i-1]
            lon2, lat2 = waypoints[i]

            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)

            a = (math.sin(dphi / 2) ** 2 +
                 math.cos(phi1) * math.cos(phi2) *
                 math.sin(dlambda / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

            total += R * c

        return total


def to_geojson(waypoints: List[Tuple[float, float]], route_name: str = "tactical_route") -> dict:
    """
    Export waypoints as GeoJSON for React frontend.

    Args:
        waypoints: List of (lon, lat) coordinates
        route_name: Name for the route

    Returns:
        GeoJSON FeatureCollection
    """
    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": list(waypoints)
            },
            "properties": {
                "type": route_name,
                "waypoint_count": len(waypoints)
            }
        }
    ]

    # Add waypoint markers every 5th point
    for i, wp in enumerate(waypoints[::5]):
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": list(wp)
            },
            "properties": {
                "waypoint_index": i * 5
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }
