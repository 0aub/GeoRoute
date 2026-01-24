"""
Terrain Data Client for ESA WorldCover and Copernicus DEM.

Fetches real terrain data for accurate pathfinding:
- ESA WorldCover 2021: 10m land cover classification
- Copernicus DEM GLO-30: 30m elevation data

Both are available as Cloud Optimized GeoTIFFs from AWS without registration.

Configuration is centralized in config.yaml
"""

import os
import tempfile
from typing import Tuple, Optional
from dataclasses import dataclass

import numpy as np
import rasterio
from rasterio.windows import from_bounds
from scipy.ndimage import zoom
from pyproj import Transformer

from georoute.config import get_yaml_setting


def _load_landcover_classes() -> dict:
    """Load land cover classes from config.yaml"""
    return get_yaml_setting("landcover", "classes") or {}


def _load_landcover_costs() -> dict:
    """Load land cover costs from config.yaml, converting 'inf' to np.inf"""
    costs_config = get_yaml_setting("landcover", "costs") or {}
    costs = {}
    for key, value in costs_config.items():
        if value == "inf":
            costs[int(key)] = np.inf
        else:
            costs[int(key)] = float(value)
    return costs


# Load from centralized config
LANDCOVER_CLASSES = _load_landcover_classes()
LANDCOVER_COSTS = _load_landcover_costs()


@dataclass
class TerrainData:
    """Container for terrain analysis results."""
    dem: np.ndarray           # Elevation in meters
    landcover: np.ndarray     # ESA WorldCover class values
    slope: np.ndarray         # Slope gradient (rise/run)
    cost_surface: np.ndarray  # Combined movement cost (seconds per meter)
    transform: rasterio.Affine
    crs: str
    cell_size: float          # Cell size in meters


class TerrainDataClient:
    """
    Client for fetching and processing terrain data from ESA WorldCover
    and Copernicus DEM for tactical pathfinding.

    Configuration is centralized in config.yaml
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the terrain data client."""
        # Load URLs from centralized config
        self.COPERNICUS_DEM_BASE = get_yaml_setting("terrain", "copernicus_dem_base")
        self.ESA_WORLDCOVER_BASE = get_yaml_setting("terrain", "esa_worldcover_base")
        self.CELL_SIZE = get_yaml_setting("terrain", "cell_size_meters")

        # Use config cache dir, Docker volume cache, or temp dir
        config_cache = get_yaml_setting("terrain", "cache_dir")
        if cache_dir:
            self.cache_dir = cache_dir
        elif config_cache and os.path.exists(os.path.dirname(config_cache)):
            self.cache_dir = config_cache
        else:
            self.cache_dir = tempfile.gettempdir()
        os.makedirs(self.cache_dir, exist_ok=True)
        print(f"[TerrainData] Cache directory: {self.cache_dir}")

        # Transformer for converting lat/lon to pixel coordinates
        self._transformer = Transformer.from_crs("EPSG:4326", "EPSG:4326", always_xy=True)

    def get_dem_tile_name(self, lat: float, lon: float) -> str:
        """
        Get Copernicus DEM tile name for given coordinates.
        Note: The copernicus-dem-30m S3 bucket actually contains COG_10 tiles (10m resolution)
        Tile naming: Copernicus_DSM_COG_10_N24_00_E046_00_DEM
        """
        lat_prefix = "N" if lat >= 0 else "S"
        lon_prefix = "E" if lon >= 0 else "W"

        lat_deg = int(abs(lat))
        lon_deg = int(abs(lon))

        # Use COG_10 format (10m resolution tiles in the copernicus-dem-30m bucket)
        tile_name = f"Copernicus_DSM_COG_10_{lat_prefix}{lat_deg:02d}_00_{lon_prefix}{lon_deg:03d}_00_DEM"
        return f"{tile_name}/{tile_name}.tif"

    def get_worldcover_tile_name(self, lat: float, lon: float) -> str:
        """
        Get ESA WorldCover tile name for given coordinates.
        Tile naming: ESA_WorldCover_10m_2021_v200_N24E046_Map.tif
        """
        lat_prefix = "N" if lat >= 0 else "S"
        lon_prefix = "E" if lon >= 0 else "W"

        # WorldCover uses 3-degree tiles
        lat_deg = int(abs(lat) // 3) * 3
        lon_deg = int(abs(lon) // 3) * 3

        return f"ESA_WorldCover_10m_2021_v200_{lat_prefix}{lat_deg:02d}{lon_prefix}{lon_deg:03d}_Map.tif"

    def fetch_dem(self, bounds: Tuple[float, float, float, float]) -> Tuple[np.ndarray, rasterio.Affine]:
        """
        Fetch Copernicus DEM data for the given bounds.

        Args:
            bounds: (west, south, east, north) in WGS84

        Returns:
            Tuple of (elevation_array, transform)
        """
        west, south, east, north = bounds
        center_lat = (south + north) / 2
        center_lon = (west + east) / 2

        tile_name = self.get_dem_tile_name(center_lat, center_lon)
        url = f"{self.COPERNICUS_DEM_BASE}/{tile_name}"

        print(f"[TerrainData] Fetching DEM from: {url}")

        try:
            with rasterio.open(url) as src:
                # Read only the window we need
                window = from_bounds(west, south, east, north, src.transform)
                dem = src.read(1, window=window).astype(np.float64)

                # Get the transform for this window
                transform = rasterio.windows.transform(window, src.transform)

                # Replace nodata values
                nodata = src.nodata
                if nodata is not None:
                    dem[dem == nodata] = np.nan

                print(f"[TerrainData] DEM shape: {dem.shape}, range: {np.nanmin(dem):.1f} - {np.nanmax(dem):.1f}m")
                return dem, transform

        except Exception as e:
            print(f"[TerrainData] Error fetching DEM: {e}")
            # Return flat terrain as fallback
            print("[TerrainData] Using flat terrain fallback")
            return self._create_flat_dem(bounds)

    def fetch_landcover(self, bounds: Tuple[float, float, float, float]) -> Tuple[np.ndarray, rasterio.Affine]:
        """
        Fetch ESA WorldCover data for the given bounds.

        Args:
            bounds: (west, south, east, north) in WGS84

        Returns:
            Tuple of (landcover_array, transform)
        """
        west, south, east, north = bounds
        center_lat = (south + north) / 2
        center_lon = (west + east) / 2

        tile_name = self.get_worldcover_tile_name(center_lat, center_lon)
        url = f"{self.ESA_WORLDCOVER_BASE}/{tile_name}"

        print(f"[TerrainData] Fetching WorldCover from: {url}")

        try:
            with rasterio.open(url) as src:
                # Read only the window we need
                window = from_bounds(west, south, east, north, src.transform)
                landcover = src.read(1, window=window)

                # Get the transform for this window
                transform = rasterio.windows.transform(window, src.transform)

                print(f"[TerrainData] WorldCover shape: {landcover.shape}")
                unique_classes = np.unique(landcover)
                print(f"[TerrainData] Land cover classes present: {unique_classes}")

                return landcover, transform

        except Exception as e:
            print(f"[TerrainData] Error fetching WorldCover: {e}")
            # Return all-passable terrain as fallback
            print("[TerrainData] Using passable terrain fallback")
            return self._create_passable_landcover(bounds)

    def _create_flat_dem(self, bounds: Tuple[float, float, float, float]) -> Tuple[np.ndarray, rasterio.Affine]:
        """Create a flat DEM as fallback."""
        west, south, east, north = bounds

        # Create 30m resolution grid
        cell_size = 30 / 111000  # ~30m in degrees
        width = int((east - west) / cell_size) + 1
        height = int((north - south) / cell_size) + 1

        dem = np.zeros((height, width), dtype=np.float64)
        transform = rasterio.transform.from_bounds(west, south, east, north, width, height)

        return dem, transform

    def _create_passable_landcover(self, bounds: Tuple[float, float, float, float]) -> Tuple[np.ndarray, rasterio.Affine]:
        """Create all-passable landcover as fallback."""
        west, south, east, north = bounds

        # Create 10m resolution grid
        cell_size = 10 / 111000  # ~10m in degrees
        width = int((east - west) / cell_size) + 1
        height = int((north - south) / cell_size) + 1

        # Use bare/sparse (60) as default - desert terrain
        landcover = np.full((height, width), 60, dtype=np.uint8)
        transform = rasterio.transform.from_bounds(west, south, east, north, width, height)

        return landcover, transform

    def calculate_slope(self, dem: np.ndarray, cell_size: float = 30.0) -> np.ndarray:
        """
        Calculate slope gradient from DEM.

        Args:
            dem: Elevation array in meters
            cell_size: Cell size in meters

        Returns:
            Slope gradient array (rise/run)
        """
        # Calculate gradients
        grad_y, grad_x = np.gradient(dem, cell_size)

        # Calculate slope magnitude
        slope = np.sqrt(grad_x**2 + grad_y**2)

        # Handle NaN values
        slope = np.nan_to_num(slope, nan=0.0)

        return slope

    def tobler_hiking_speed(self, slope_gradient: np.ndarray) -> np.ndarray:
        """
        Apply Tobler's hiking function to get walking speed.

        Args:
            slope_gradient: Slope as rise/run

        Returns:
            Walking speed in km/h
        """
        # Tobler's hiking function
        # Maximum ~6 km/h at slight downhill (-2.86°)
        # Flat terrain: ~5 km/h
        speed = 6.0 * np.exp(-3.5 * np.abs(slope_gradient + 0.05))

        # Clip to reasonable range
        speed = np.clip(speed, 0.5, 6.0)

        return speed

    def tobler_cost(self, slope_gradient: np.ndarray, off_road_factor: float = 0.6) -> np.ndarray:
        """
        Convert slope to time cost (seconds per meter).

        Args:
            slope_gradient: Slope as rise/run
            off_road_factor: Multiplier for off-path travel (0.6 = 60% of road speed)

        Returns:
            Cost in seconds per meter
        """
        speed_kmh = self.tobler_hiking_speed(slope_gradient) * off_road_factor
        speed_ms = speed_kmh / 3.6  # Convert to m/s

        # Avoid division by zero
        speed_ms = np.maximum(speed_ms, 0.1)

        return 1.0 / speed_ms  # seconds per meter

    def create_cost_surface(
        self,
        dem: np.ndarray,
        landcover: np.ndarray,
        cell_size: float = 30.0,
        off_road_factor: float = 0.6
    ) -> np.ndarray:
        """
        Create combined movement cost surface.

        Args:
            dem: Elevation array
            landcover: ESA WorldCover class array
            cell_size: Cell size in meters
            off_road_factor: Speed reduction for off-road travel

        Returns:
            Cost surface (seconds per meter), inf = impassable
        """
        # Calculate slope cost using Tobler's function
        slope = self.calculate_slope(dem, cell_size)
        slope_cost = self.tobler_cost(slope, off_road_factor)

        # Create terrain multiplier from land cover
        # IMPORTANT: Process at FULL landcover resolution first, then downsample
        # This prevents losing building/water data during resampling

        # Step 1: Create impassable mask at full resolution (10m)
        impassable_mask_fullres = np.zeros(landcover.shape, dtype=bool)
        terrain_cost_fullres = np.ones(landcover.shape, dtype=np.float64)

        for lc_class, cost_mult in LANDCOVER_COSTS.items():
            mask = landcover == lc_class
            if np.isinf(cost_mult):
                impassable_mask_fullres[mask] = True
            else:
                terrain_cost_fullres[mask] = cost_mult

        # Step 2: Downsample to DEM resolution, preserving impassable areas
        if landcover.shape != dem.shape:
            from skimage.measure import block_reduce

            # Calculate block size for downsampling
            block_y = max(1, landcover.shape[0] // dem.shape[0])
            block_z = max(1, landcover.shape[1] // dem.shape[1])

            # For impassable mask: use MAX (if ANY pixel is impassable, cell is impassable)
            impassable_reduced = block_reduce(
                impassable_mask_fullres.astype(np.float64),
                (block_y, block_z),
                func=np.max
            )
            # Crop or pad to match DEM shape
            impassable_reduced = impassable_reduced[:dem.shape[0], :dem.shape[1]]
            if impassable_reduced.shape != dem.shape:
                # Pad if needed
                pad_y = dem.shape[0] - impassable_reduced.shape[0]
                pad_x = dem.shape[1] - impassable_reduced.shape[1]
                impassable_reduced = np.pad(impassable_reduced, ((0, pad_y), (0, pad_x)), mode='edge')

            # For terrain cost: use MAX (worst case cost in each cell)
            terrain_cost_reduced = block_reduce(
                terrain_cost_fullres,
                (block_y, block_z),
                func=np.max
            )
            terrain_cost_reduced = terrain_cost_reduced[:dem.shape[0], :dem.shape[1]]
            if terrain_cost_reduced.shape != dem.shape:
                pad_y = dem.shape[0] - terrain_cost_reduced.shape[0]
                pad_x = dem.shape[1] - terrain_cost_reduced.shape[1]
                terrain_cost_reduced = np.pad(terrain_cost_reduced, ((0, pad_y), (0, pad_x)), mode='edge')

            terrain_mult = terrain_cost_reduced
            terrain_mult[impassable_reduced > 0.5] = np.inf

            print(f"[TerrainData] Downsampled landcover: {landcover.shape} -> {dem.shape}")
            print(f"[TerrainData] Impassable cells after block_reduce: {np.sum(np.isinf(terrain_mult))}/{terrain_mult.size}")
        else:
            terrain_mult = terrain_cost_fullres
            terrain_mult[impassable_mask_fullres] = np.inf

        # Combine costs
        final_cost = slope_cost * terrain_mult

        # Mark steep slopes (>45°, ~100% grade) as impassable
        final_cost[slope > 1.0] = np.inf

        # Mark NaN elevations as impassable
        final_cost[np.isnan(dem)] = np.inf

        return final_cost

    def get_terrain_data(self, bounds: Tuple[float, float, float, float]) -> TerrainData:
        """
        Fetch and process all terrain data for the given bounds.

        Args:
            bounds: (west, south, east, north) in WGS84

        Returns:
            TerrainData object with all processed arrays
        """
        print(f"[TerrainData] Fetching terrain data for bounds: {bounds}")

        # Fetch DEM and landcover
        dem, dem_transform = self.fetch_dem(bounds)
        landcover, lc_transform = self.fetch_landcover(bounds)

        # Use cell size from config
        cell_size = self.CELL_SIZE

        # Calculate slope
        slope = self.calculate_slope(dem, cell_size)

        # Create cost surface
        cost_surface = self.create_cost_surface(dem, landcover, cell_size)

        # Count impassable cells
        impassable_count = np.sum(np.isinf(cost_surface))
        total_cells = cost_surface.size
        impassable_pct = (impassable_count / total_cells) * 100
        print(f"[TerrainData] Impassable cells: {impassable_count}/{total_cells} ({impassable_pct:.1f}%)")

        return TerrainData(
            dem=dem,
            landcover=landcover,
            slope=slope,
            cost_surface=cost_surface,
            transform=dem_transform,
            crs="EPSG:4326",
            cell_size=cell_size
        )

    def get_passability_grid(
        self,
        bounds: Tuple[float, float, float, float],
        grid_size: int = 50
    ) -> Tuple[np.ndarray, dict]:
        """
        Get a simplified passability grid for the bounds.

        Args:
            bounds: (west, south, east, north) in WGS84
            grid_size: Number of cells in each dimension

        Returns:
            Tuple of (passability_array, metadata)
            passability_array: 0.0 = impassable, 1.0 = easy, intermediate values for difficulty
        """
        terrain = self.get_terrain_data(bounds)

        # Resample cost surface to grid size
        zoom_factors = (grid_size / terrain.cost_surface.shape[0],
                       grid_size / terrain.cost_surface.shape[1])

        # Use minimum cost in each cell (most optimistic)
        from scipy.ndimage import zoom as scipy_zoom
        cost_resampled = scipy_zoom(terrain.cost_surface, zoom_factors, order=0)

        # Convert cost to passability (0-1 scale)
        # Lower cost = higher passability
        passability = np.where(
            np.isinf(cost_resampled),
            0.0,
            1.0 / (1.0 + cost_resampled)  # Normalize to 0-1
        )

        metadata = {
            "bounds": bounds,
            "grid_size": grid_size,
            "cell_width": (bounds[2] - bounds[0]) / grid_size,
            "cell_height": (bounds[3] - bounds[1]) / grid_size,
        }

        return passability, metadata
