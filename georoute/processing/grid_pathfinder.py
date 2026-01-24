"""
Simple Grid-based A* Pathfinder.

Works directly with the grid-based obstacle mask from GeminiObstacleDetector.
No external dependencies beyond numpy and heapq.

This pathfinder:
1. Takes start/end GPS coordinates
2. Converts to grid coordinates
3. Runs A* on the obstacle grid
4. Returns path as GPS waypoints
"""

import heapq
import math
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PathResult:
    """Result of pathfinding."""
    path_valid: bool
    waypoints: List[Tuple[float, float]]  # List of (lat, lon)
    distance_cells: int  # Path length in grid cells
    path_clear: bool  # Whether path avoids all obstacles


class GridPathfinder:
    """
    A* pathfinder for grid-based obstacle avoidance.

    Optimized for small grids (32x32 to 64x64) from Gemini vision detection.
    """

    def __init__(self, allow_diagonal: bool = True):
        """
        Initialize pathfinder.

        Args:
            allow_diagonal: Whether to allow diagonal movement
        """
        self.allow_diagonal = allow_diagonal

        # Movement directions (8-connected if diagonal, 4-connected otherwise)
        if allow_diagonal:
            self.directions = [
                (-1, -1), (-1, 0), (-1, 1),
                (0, -1),          (0, 1),
                (1, -1),  (1, 0),  (1, 1)
            ]
            # Costs: diagonal = sqrt(2), cardinal = 1
            self.costs = [
                1.414, 1.0, 1.414,
                1.0,        1.0,
                1.414, 1.0, 1.414
            ]
        else:
            self.directions = [(-1, 0), (0, -1), (0, 1), (1, 0)]
            self.costs = [1.0, 1.0, 1.0, 1.0]

    def find_path(
        self,
        obstacle_mask: np.ndarray,
        start_grid: Tuple[int, int],
        end_grid: Tuple[int, int],
        bounds: dict
    ) -> PathResult:
        """
        Find path from start to end avoiding obstacles.

        Args:
            obstacle_mask: Binary mask (1 = obstacle, 0 = traversable)
            start_grid: (row, col) start position
            end_grid: (row, col) end position
            bounds: Geographic bounds for GPS conversion

        Returns:
            PathResult with waypoints as GPS coordinates
        """
        grid_h, grid_w = obstacle_mask.shape
        start_r, start_c = start_grid
        end_r, end_c = end_grid

        # Validate positions
        if not (0 <= start_r < grid_h and 0 <= start_c < grid_w):
            print(f"[GridPathfinder] Invalid start position: {start_grid}")
            return self._fallback_path(start_grid, end_grid, bounds, grid_h, grid_w)

        if not (0 <= end_r < grid_h and 0 <= end_c < grid_w):
            print(f"[GridPathfinder] Invalid end position: {end_grid}")
            return self._fallback_path(start_grid, end_grid, bounds, grid_h, grid_w)

        # If start or end is on obstacle, find nearest clear cell
        if obstacle_mask[start_r, start_c] == 1:
            start_r, start_c = self._find_nearest_clear(obstacle_mask, start_r, start_c)
            print(f"[GridPathfinder] Moved start to clear cell: ({start_r}, {start_c})")

        if obstacle_mask[end_r, end_c] == 1:
            end_r, end_c = self._find_nearest_clear(obstacle_mask, end_r, end_c)
            print(f"[GridPathfinder] Moved end to clear cell: ({end_r}, {end_c})")

        # Run A*
        path_grid = self._astar(obstacle_mask, (start_r, start_c), (end_r, end_c))

        if path_grid is None:
            print("[GridPathfinder] No valid path found, using fallback")
            return self._fallback_path(start_grid, end_grid, bounds, grid_h, grid_w)

        # Simplify path (reduce waypoints)
        simplified_path = self._simplify_path(path_grid)

        # Convert to GPS
        waypoints_gps = [
            self._grid_to_gps(r, c, bounds, grid_h, grid_w)
            for r, c in simplified_path
        ]

        print(f"[GridPathfinder] Found path with {len(waypoints_gps)} waypoints")

        return PathResult(
            path_valid=True,
            waypoints=waypoints_gps,
            distance_cells=len(path_grid),
            path_clear=True
        )

    def _astar(
        self,
        obstacle_mask: np.ndarray,
        start: Tuple[int, int],
        end: Tuple[int, int]
    ) -> Optional[List[Tuple[int, int]]]:
        """A* pathfinding algorithm."""
        grid_h, grid_w = obstacle_mask.shape

        # Heuristic: Euclidean distance
        def heuristic(pos):
            return math.sqrt((pos[0] - end[0])**2 + (pos[1] - end[1])**2)

        # Priority queue: (f_score, counter, position)
        # Counter ensures deterministic ordering for equal f_scores
        counter = 0
        open_set = [(heuristic(start), counter, start)]
        heapq.heapify(open_set)

        came_from = {}
        g_score = {start: 0}

        # Track visited to avoid revisiting
        closed_set = set()

        while open_set:
            _, _, current = heapq.heappop(open_set)

            if current in closed_set:
                continue

            if current == end:
                # Reconstruct path
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                return path[::-1]

            closed_set.add(current)

            # Explore neighbors
            for i, (dr, dc) in enumerate(self.directions):
                nr, nc = current[0] + dr, current[1] + dc
                neighbor = (nr, nc)

                # Check bounds
                if not (0 <= nr < grid_h and 0 <= nc < grid_w):
                    continue

                # Check obstacle
                if obstacle_mask[nr, nc] == 1:
                    continue

                # Check if already processed
                if neighbor in closed_set:
                    continue

                # Calculate tentative g_score
                move_cost = self.costs[i]
                tentative_g = g_score[current] + move_cost

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + heuristic(neighbor)

                    counter += 1
                    heapq.heappush(open_set, (f_score, counter, neighbor))

        # No path found
        return None

    def _find_nearest_clear(
        self,
        obstacle_mask: np.ndarray,
        start_r: int,
        start_c: int
    ) -> Tuple[int, int]:
        """Find nearest clear cell to a given position."""
        grid_h, grid_w = obstacle_mask.shape

        # BFS to find nearest clear cell
        visited = set()
        queue = [(start_r, start_c)]
        visited.add((start_r, start_c))

        while queue:
            r, c = queue.pop(0)

            if obstacle_mask[r, c] == 0:
                return (r, c)

            # Add neighbors
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < grid_h and 0 <= nc < grid_w and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    queue.append((nr, nc))

        # Fallback: return original position
        return (start_r, start_c)

    def _simplify_path(
        self,
        path: List[Tuple[int, int]],
        max_waypoints: int = 15
    ) -> List[Tuple[int, int]]:
        """
        Simplify path by keeping only key waypoints.

        Uses Ramer-Douglas-Peucker-like simplification.
        """
        if len(path) <= max_waypoints:
            return path

        # Always keep start and end
        if len(path) <= 2:
            return path

        # Sample evenly + direction changes
        simplified = [path[0]]

        # Detect direction changes
        prev_dir = None
        for i in range(1, len(path)):
            dr = path[i][0] - path[i-1][0]
            dc = path[i][1] - path[i-1][1]
            curr_dir = (dr, dc)

            if curr_dir != prev_dir:
                if path[i-1] not in simplified:
                    simplified.append(path[i-1])
            prev_dir = curr_dir

        simplified.append(path[-1])

        # If still too many, sample evenly
        if len(simplified) > max_waypoints:
            step = len(simplified) / max_waypoints
            indices = [int(i * step) for i in range(max_waypoints - 1)]
            indices.append(len(simplified) - 1)
            simplified = [simplified[i] for i in indices]

        return simplified

    def _grid_to_gps(
        self,
        row: int,
        col: int,
        bounds: dict,
        grid_h: int,
        grid_w: int
    ) -> Tuple[float, float]:
        """Convert grid coordinates to GPS."""
        # Row 0 = north, row max = south
        lat = bounds["north"] - (row / grid_h) * (bounds["north"] - bounds["south"])
        # Col 0 = west, col max = east
        lon = bounds["west"] + (col / grid_w) * (bounds["east"] - bounds["west"])

        return (lat, lon)

    def _fallback_path(
        self,
        start_grid: Tuple[int, int],
        end_grid: Tuple[int, int],
        bounds: dict,
        grid_h: int,
        grid_w: int
    ) -> PathResult:
        """Generate fallback straight-line path when A* fails."""
        # Generate 10 points along the straight line
        waypoints = []
        num_points = 10

        for i in range(num_points):
            t = i / (num_points - 1)
            row = int(start_grid[0] + t * (end_grid[0] - start_grid[0]))
            col = int(start_grid[1] + t * (end_grid[1] - start_grid[1]))
            lat, lon = self._grid_to_gps(row, col, bounds, grid_h, grid_w)
            waypoints.append((lat, lon))

        return PathResult(
            path_valid=True,
            waypoints=waypoints,
            distance_cells=abs(end_grid[0] - start_grid[0]) + abs(end_grid[1] - start_grid[1]),
            path_clear=False  # Indicates this is a fallback
        )


def generate_tactical_routes(
    obstacle_mask: np.ndarray,
    start_gps: Tuple[float, float],
    end_gps: Tuple[float, float],
    bounds: dict,
    single_route: bool = True  # Focus on ONE good route first
) -> Tuple[List[dict], dict]:
    """
    Generate tactical routes using A* pathfinding.

    Args:
        obstacle_mask: Binary obstacle grid from GeminiObstacleDetector
        start_gps: (lat, lon) start position
        end_gps: (lat, lon) end position
        bounds: Geographic bounds {"north", "south", "east", "west"}
        single_route: If True, generate only one route (for debugging)

    Returns:
        Tuple of (routes list, debug_info dict with grid visualization data)
    """
    grid_h, grid_w = obstacle_mask.shape
    pathfinder = GridPathfinder()

    # Log input parameters
    print(f"[GridPathfinder] === COORDINATE DEBUG ===")
    print(f"[GridPathfinder] Start GPS (soldier): ({start_gps[0]:.6f}, {start_gps[1]:.6f})")
    print(f"[GridPathfinder] End GPS (enemy): ({end_gps[0]:.6f}, {end_gps[1]:.6f})")
    print(f"[GridPathfinder] Bounds: N={bounds['north']:.6f}, S={bounds['south']:.6f}, E={bounds['east']:.6f}, W={bounds['west']:.6f}")

    # Calculate bounds size in meters (approximate)
    lat_span = bounds['north'] - bounds['south']
    lon_span = bounds['east'] - bounds['west']
    lat_meters = lat_span * 111000  # ~111km per degree latitude
    lon_meters = lon_span * 111000 * math.cos(math.radians((bounds['north'] + bounds['south']) / 2))
    print(f"[GridPathfinder] Bounds size: ~{lat_meters:.0f}m x ~{lon_meters:.0f}m")
    print(f"[GridPathfinder] Cell size: ~{lat_meters/grid_h:.1f}m x ~{lon_meters/grid_w:.1f}m")

    # Convert GPS to grid
    def gps_to_grid(lat, lon):
        row = int((bounds["north"] - lat) / (bounds["north"] - bounds["south"]) * grid_h)
        col = int((lon - bounds["west"]) / (bounds["east"] - bounds["west"]) * grid_w)
        return (max(0, min(grid_h - 1, row)), max(0, min(grid_w - 1, col)))

    # Convert grid to GPS (for visualization)
    def grid_to_gps(row, col):
        lat = bounds["north"] - (row / grid_h) * (bounds["north"] - bounds["south"])
        lon = bounds["west"] + (col / grid_w) * (bounds["east"] - bounds["west"])
        return (lat, lon)

    start_grid = gps_to_grid(start_gps[0], start_gps[1])
    end_grid = gps_to_grid(end_gps[0], end_gps[1])

    print(f"[GridPathfinder] Start grid cell: {start_grid}")
    print(f"[GridPathfinder] End grid cell: {end_grid}")

    # Build grid visualization data for UI (compact format - only obstacle cells)
    obstacle_cells = []
    traversable_cells = []
    for row in range(grid_h):
        for col in range(grid_w):
            lat, lon = grid_to_gps(row + 0.5, col + 0.5)  # Center of cell
            cell_data = {"row": row, "col": col, "lat": round(lat, 6), "lon": round(lon, 6)}
            if obstacle_mask[row, col] == 1:
                obstacle_cells.append(cell_data)
            else:
                traversable_cells.append(cell_data)

    debug_info = {
        "grid_size": grid_h,
        "bounds": bounds,
        "obstacle_cells": obstacle_cells,  # Only obstacle cells (for drawing red)
        "traversable_cells": traversable_cells,  # Only traversable cells (for drawing green)
        "start_cell": {"row": start_grid[0], "col": start_grid[1]},
        "end_cell": {"row": end_grid[0], "col": end_grid[1]},
        "cell_size_m": round(lat_meters / grid_h, 1),
        "total_cells": grid_h * grid_w,
        "obstacle_count": len(obstacle_cells),
        "traversable_count": len(traversable_cells)
    }

    print(f"[GridPathfinder] Grid stats: {len(obstacle_cells)} obstacles, {len(traversable_cells)} traversable")

    routes = []

    # Route 1: Direct path (always generated)
    result1 = pathfinder.find_path(obstacle_mask, start_grid, end_grid, bounds)
    routes.append({
        "route_id": 1,
        "name": "Direct Route",
        "description": "Shortest path avoiding detected obstacles",
        "waypoints": _convert_waypoints(result1.waypoints, start_gps, end_gps),
        "path_clear": result1.path_clear
    })

    print(f"[GridPathfinder] Route 1: {len(result1.waypoints)} waypoints, path_clear={result1.path_clear}")

    # If single_route mode, return just the direct route with debug info
    if single_route:
        print(f"[GridPathfinder] SINGLE ROUTE MODE - returning 1 route with debug info")
        return routes, debug_info

    # === MULTIPLE ROUTES (when single_route=False) ===
    # Route 2 & 3: Create DISTINCT flanking routes using corner waypoints

    # Calculate the bounding box of start and end positions
    min_row = min(start_grid[0], end_grid[0])
    max_row = max(start_grid[0], end_grid[0])
    min_col = min(start_grid[1], end_grid[1])
    max_col = max(start_grid[1], end_grid[1])

    # Add padding to create truly distinct flanking routes (at least 3 cells or 20% of grid)
    padding = max(3, grid_h // 5)

    # Determine the general direction of travel
    going_down = end_grid[0] > start_grid[0]
    going_right = end_grid[1] > start_grid[1]

    print(f"[GridPathfinder] Direction: {'down' if going_down else 'up'}-{'right' if going_right else 'left'}")
    print(f"[GridPathfinder] Bounding box: rows [{min_row}, {max_row}], cols [{min_col}, {max_col}]")

    # Left flank: go around the "left" side (relative to travel direction)
    if going_down and going_right:
        left_mid_row = min(grid_h - 2, max_row + padding // 2)
        left_mid_col = max(1, min_col - padding // 2)
    elif going_down and not going_right:
        left_mid_row = min(grid_h - 2, max_row + padding // 2)
        left_mid_col = min(grid_w - 2, max_col + padding // 2)
    elif not going_down and going_right:
        left_mid_row = max(1, min_row - padding // 2)
        left_mid_col = max(1, min_col - padding // 2)
    else:
        left_mid_row = max(1, min_row - padding // 2)
        left_mid_col = min(grid_w - 2, max_col + padding // 2)

    # Right flank: opposite side
    if going_down and going_right:
        right_mid_row = max(1, min_row - padding // 2)
        right_mid_col = min(grid_w - 2, max_col + padding // 2)
    elif going_down and not going_right:
        right_mid_row = max(1, min_row - padding // 2)
        right_mid_col = max(1, min_col - padding // 2)
    elif not going_down and going_right:
        right_mid_row = min(grid_h - 2, max_row + padding // 2)
        right_mid_col = min(grid_w - 2, max_col + padding // 2)
    else:
        right_mid_row = min(grid_h - 2, max_row + padding // 2)
        right_mid_col = max(1, min_col - padding // 2)

    # Clamp to valid grid range
    left_mid_row = max(0, min(grid_h - 1, left_mid_row))
    left_mid_col = max(0, min(grid_w - 1, left_mid_col))
    right_mid_row = max(0, min(grid_h - 1, right_mid_row))
    right_mid_col = max(0, min(grid_w - 1, right_mid_col))

    print(f"[GridPathfinder] Left flank waypoint: ({left_mid_row}, {left_mid_col})")
    print(f"[GridPathfinder] Right flank waypoint: ({right_mid_row}, {right_mid_col})")

    # Route 2: Left approach
    result2a = pathfinder.find_path(obstacle_mask, start_grid, (left_mid_row, left_mid_col), bounds)
    result2b = pathfinder.find_path(obstacle_mask, (left_mid_row, left_mid_col), end_grid, bounds)

    combined_waypoints_2 = result2a.waypoints[:-1] + result2b.waypoints
    routes.append({
        "route_id": 2,
        "name": "Left Approach",
        "description": "Flanking route from the left side",
        "waypoints": _convert_waypoints(combined_waypoints_2, start_gps, end_gps),
        "path_clear": result2a.path_clear and result2b.path_clear
    })

    # Route 3: Right approach
    result3a = pathfinder.find_path(obstacle_mask, start_grid, (right_mid_row, right_mid_col), bounds)
    result3b = pathfinder.find_path(obstacle_mask, (right_mid_row, right_mid_col), end_grid, bounds)

    combined_waypoints_3 = result3a.waypoints[:-1] + result3b.waypoints
    routes.append({
        "route_id": 3,
        "name": "Right Approach",
        "description": "Flanking route from the right side",
        "waypoints": _convert_waypoints(combined_waypoints_3, start_gps, end_gps),
        "path_clear": result3a.path_clear and result3b.path_clear
    })

    print(f"[GridPathfinder] Generated {len(routes)} routes")

    return routes, debug_info


def _convert_waypoints(
    waypoints_gps: List[Tuple[float, float]],
    start_gps: Tuple[float, float],
    end_gps: Tuple[float, float]
) -> List[dict]:
    """Convert GPS waypoints to waypoint dictionaries.

    IMPORTANT: Forces first waypoint to be exact start_gps and last to be exact end_gps
    to ensure routes connect properly to soldier/enemy markers.
    """
    if not waypoints_gps:
        # Fallback: direct line if no waypoints
        waypoints_gps = [start_gps, end_gps]

    # Force first waypoint to exact soldier position
    waypoints_gps = list(waypoints_gps)  # Make mutable copy
    waypoints_gps[0] = start_gps

    # Force last waypoint to exact enemy position
    waypoints_gps[-1] = end_gps

    result = []
    total_distance = 0.0

    for i, (lat, lon) in enumerate(waypoints_gps):
        if i > 0:
            prev_lat, prev_lon = waypoints_gps[i-1]
            # Haversine distance
            R = 6371000
            phi1 = math.radians(prev_lat)
            phi2 = math.radians(lat)
            dphi = math.radians(lat - prev_lat)
            dlambda = math.radians(lon - prev_lon)
            a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            segment_dist = R * c
            total_distance += segment_dist

        result.append({
            "lat": lat,
            "lon": lon,
            "elevation_m": 0.0,
            "distance_from_start_m": total_distance,
            "terrain_type": "traversable",
            "risk_level": "moderate",
            "reasoning": "Path avoiding detected obstacles"
        })

    return result
