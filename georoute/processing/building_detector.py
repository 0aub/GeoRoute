"""
Building Detection Module using OpenStreetMap data via OSMnx.

This module provides accurate building footprint detection by querying
actual building polygons from OpenStreetMap, rather than relying on
satellite image classification which cannot detect individual buildings.

Key features:
- Fetches real building polygons from OSM (free, no API key needed)
- Converts polygons to rasterized obstacle masks
- Adds configurable buffer zones around buildings (2-5m recommended)
- Returns obstacle masks at specified resolution (default 1m)
"""

from typing import Tuple, List, Optional
from dataclasses import dataclass
import numpy as np

try:
    import osmnx as ox
    import geopandas as gpd
    from shapely.geometry import box
    from rasterio.features import rasterize
    from rasterio.transform import from_bounds
    from pyproj import CRS
    OSMNX_AVAILABLE = True
except ImportError as e:
    OSMNX_AVAILABLE = False
    print(f"[BuildingDetector] OSMnx not available: {e}")


@dataclass
class BuildingDetectionResult:
    """Result of building detection."""
    obstacle_mask: np.ndarray  # Binary mask: 1 = obstacle, 0 = traversable
    buffered_mask: np.ndarray  # Mask with buffer zones included
    building_count: int
    bounds_utm: Tuple[float, float, float, float]  # UTM bounds
    transform: any  # Rasterio transform
    resolution_m: float
    utm_crs: str


class BuildingDetector:
    """
    Detects buildings using OpenStreetMap data.

    This provides pixel-accurate building footprints that ESA WorldCover
    (10m resolution) cannot provide. OSM data is community-maintained
    and includes recent construction.
    """

    def __init__(self, buffer_meters: float = 3.0, resolution_meters: float = 1.0):
        """
        Initialize the building detector.

        Args:
            buffer_meters: Safety buffer around buildings (2-5m recommended)
            resolution_meters: Resolution of output mask in meters
        """
        if not OSMNX_AVAILABLE:
            raise ImportError(
                "OSMnx is required for building detection. "
                "Install with: pip install osmnx"
            )

        self.buffer_meters = buffer_meters
        self.resolution_meters = resolution_meters

        # Configure OSMnx for better performance
        ox.settings.use_cache = True
        ox.settings.log_console = False
        ox.settings.timeout = 30  # Shorter timeout
        # Keep default max query area - we limit bounds instead
        ox.settings.max_query_area_size = 2.5 * 1e6  # 2.5 km² default

        # Maximum area size for building queries (in degrees squared)
        # Approximately 2km x 2km area max
        self.max_query_area_deg = 0.02 * 0.02  # ~0.0004 deg^2

    def detect_buildings(
        self,
        bounds: Tuple[float, float, float, float],
        include_roads: bool = False
    ) -> BuildingDetectionResult:
        """
        Detect buildings within the given bounds.

        Args:
            bounds: (west, south, east, north) in WGS84 (EPSG:4326)
            include_roads: Whether to mark major roads as obstacles

        Returns:
            BuildingDetectionResult with obstacle masks
        """
        west, south, east, north = bounds

        # STRICT: Check if bounds area is too large
        # Max 0.0001 deg² = ~350m x 350m area to prevent OSM query explosion
        area_deg = (east - west) * (north - south)
        max_area = 0.0001  # STRICT: ~350m x 350m max

        if area_deg > max_area:
            print(f"[BuildingDetector] LIMITING query area from {area_deg:.6f} to {max_area} deg²")
            # Calculate center and create smaller bounds
            center_lat = (north + south) / 2
            center_lon = (east + west) / 2
            half_size = 0.005  # ~500m in each direction (total 1km x 1km)
            west = center_lon - half_size
            east = center_lon + half_size
            south = center_lat - half_size
            north = center_lat + half_size

        # Additional safety: limit individual dimensions
        if (east - west) > 0.015:  # ~1.5km
            center_lon = (east + west) / 2
            west = center_lon - 0.0075
            east = center_lon + 0.0075
        if (north - south) > 0.015:
            center_lat = (north + south) / 2
            south = center_lat - 0.0075
            north = center_lat + 0.0075

        bounds = (west, south, east, north)

        print(f"[BuildingDetector] Fetching buildings for bounds: {bounds}")
        print(f"[BuildingDetector] Buffer: {self.buffer_meters}m, Resolution: {self.resolution_meters}m")

        # Fetch buildings from OSM
        try:
            # OSMnx expects (north, south, east, west) for bbox
            buildings_gdf = ox.features.features_from_bbox(
                bbox=(north, south, east, west),
                tags={'building': True}
            )

            # Filter to only polygon geometries
            buildings_gdf = buildings_gdf[
                buildings_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])
            ]

            print(f"[BuildingDetector] Found {len(buildings_gdf)} buildings")

        except Exception as e:
            print(f"[BuildingDetector] OSM query failed: {e}")
            # Return empty result - no buildings found
            return self._create_empty_result(bounds)

        if len(buildings_gdf) == 0:
            print("[BuildingDetector] No buildings found in area")
            return self._create_empty_result(bounds)

        # Project to UTM for accurate meter-based calculations
        utm_crs = buildings_gdf.estimate_utm_crs()
        buildings_utm = buildings_gdf.to_crs(utm_crs)

        # Create bounding box in UTM
        bbox_gdf = gpd.GeoDataFrame(
            geometry=[box(west, south, east, north)],
            crs="EPSG:4326"
        ).to_crs(utm_crs)
        bounds_utm = bbox_gdf.total_bounds  # (minx, miny, maxx, maxy)

        # Calculate grid dimensions
        width = int((bounds_utm[2] - bounds_utm[0]) / self.resolution_meters)
        height = int((bounds_utm[3] - bounds_utm[1]) / self.resolution_meters)

        print(f"[BuildingDetector] Grid size: {width}x{height} pixels at {self.resolution_meters}m resolution")

        # Create transform for rasterization
        transform = from_bounds(
            bounds_utm[0], bounds_utm[1],
            bounds_utm[2], bounds_utm[3],
            width, height
        )

        # Rasterize buildings (no buffer)
        shapes = [(geom, 1) for geom in buildings_utm.geometry if geom is not None]
        obstacle_mask = rasterize(
            shapes,
            out_shape=(height, width),
            transform=transform,
            fill=0,
            all_touched=True,
            dtype=np.uint8
        )

        # Create buffered buildings
        buildings_buffered = buildings_utm.copy()
        buildings_buffered['geometry'] = buildings_utm.geometry.buffer(self.buffer_meters)

        # Rasterize buffered buildings
        buffered_shapes = [(geom, 1) for geom in buildings_buffered.geometry if geom is not None]
        buffered_mask = rasterize(
            buffered_shapes,
            out_shape=(height, width),
            transform=transform,
            fill=0,
            all_touched=True,
            dtype=np.uint8
        )

        # Optionally include roads as obstacles
        if include_roads:
            try:
                roads_gdf = ox.features.features_from_bbox(
                    bbox=(north, south, east, west),
                    tags={'highway': ['primary', 'secondary', 'tertiary', 'motorway']}
                )
                if len(roads_gdf) > 0:
                    roads_utm = roads_gdf.to_crs(utm_crs)
                    # Buffer roads by 3m on each side
                    roads_buffered = roads_utm.geometry.buffer(3.0)
                    road_shapes = [(geom, 1) for geom in roads_buffered if geom is not None]
                    road_mask = rasterize(
                        road_shapes,
                        out_shape=(height, width),
                        transform=transform,
                        fill=0,
                        all_touched=True,
                        dtype=np.uint8
                    )
                    buffered_mask = np.maximum(buffered_mask, road_mask)
            except Exception as e:
                print(f"[BuildingDetector] Road query failed (continuing without): {e}")

        obstacle_count = np.sum(obstacle_mask)
        buffered_count = np.sum(buffered_mask)
        total_pixels = obstacle_mask.size

        print(f"[BuildingDetector] Obstacle pixels: {obstacle_count}/{total_pixels} "
              f"({100*obstacle_count/total_pixels:.1f}%)")
        print(f"[BuildingDetector] Buffered obstacle pixels: {buffered_count}/{total_pixels} "
              f"({100*buffered_count/total_pixels:.1f}%)")

        return BuildingDetectionResult(
            obstacle_mask=obstacle_mask,
            buffered_mask=buffered_mask,
            building_count=len(buildings_gdf),
            bounds_utm=tuple(bounds_utm),
            transform=transform,
            resolution_m=self.resolution_meters,
            utm_crs=str(utm_crs)
        )

    def _create_empty_result(
        self,
        bounds: Tuple[float, float, float, float]
    ) -> BuildingDetectionResult:
        """Create an empty result when no buildings are found."""
        west, south, east, north = bounds

        # Estimate UTM zone from center
        center_lon = (west + east) / 2
        center_lat = (south + north) / 2
        utm_zone = int((center_lon + 180) / 6) + 1
        hemisphere = 'north' if center_lat >= 0 else 'south'
        utm_crs = CRS.from_dict({
            'proj': 'utm',
            'zone': utm_zone,
            'south': hemisphere == 'south'
        })

        # Create bounding box in UTM
        bbox_gdf = gpd.GeoDataFrame(
            geometry=[box(west, south, east, north)],
            crs="EPSG:4326"
        ).to_crs(utm_crs)
        bounds_utm = bbox_gdf.total_bounds

        # Calculate grid dimensions
        width = int((bounds_utm[2] - bounds_utm[0]) / self.resolution_meters)
        height = int((bounds_utm[3] - bounds_utm[1]) / self.resolution_meters)

        transform = from_bounds(
            bounds_utm[0], bounds_utm[1],
            bounds_utm[2], bounds_utm[3],
            width, height
        )

        # Empty masks (all traversable)
        empty_mask = np.zeros((height, width), dtype=np.uint8)

        return BuildingDetectionResult(
            obstacle_mask=empty_mask,
            buffered_mask=empty_mask,
            building_count=0,
            bounds_utm=tuple(bounds_utm),
            transform=transform,
            resolution_m=self.resolution_meters,
            utm_crs=str(utm_crs)
        )

    def get_building_polygons(
        self,
        bounds: Tuple[float, float, float, float]
    ) -> Optional[gpd.GeoDataFrame]:
        """
        Get building polygons as GeoDataFrame.

        Args:
            bounds: (west, south, east, north) in WGS84

        Returns:
            GeoDataFrame with building polygons, or None if query fails
        """
        west, south, east, north = bounds

        try:
            buildings_gdf = ox.features.features_from_bbox(
                bbox=(north, south, east, west),
                tags={'building': True}
            )

            buildings_gdf = buildings_gdf[
                buildings_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])
            ]

            return buildings_gdf

        except Exception as e:
            print(f"[BuildingDetector] Failed to get polygons: {e}")
            return None
