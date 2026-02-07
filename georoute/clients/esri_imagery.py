"""
ESRI ArcGIS World Imagery client - Tile-based.

Fetches the EXACT same tiles that Leaflet displays and stitches them together.
This ensures pixel-perfect visual consistency between UI and backend processing.
"""

import asyncio
import math
from typing import Optional
from io import BytesIO
import httpx
from PIL import Image


class ESRIImageryClient:
    """
    Client for ESRI ArcGIS World Imagery.

    Fetches tiles from the same URL that Leaflet uses:
    https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}

    This ensures the satellite imagery matches exactly what the user sees in the UI.
    """

    def __init__(self):
        self.tile_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    def _lat_lon_to_tile(self, lat: float, lon: float, zoom: int) -> tuple[int, int]:
        """Convert lat/lon to tile coordinates at given zoom level."""
        n = 2 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        lat_rad = math.radians(lat)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (x, y)

    def _tile_to_lat_lon(self, x: int, y: int, zoom: int) -> tuple[float, float, float, float]:
        """Convert tile coordinates to bounding box (north, south, east, west)."""
        n = 2 ** zoom
        west = x / n * 360.0 - 180.0
        east = (x + 1) / n * 360.0 - 180.0
        north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
        south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
        return (north, south, east, west)

    async def _fetch_tile(self, z: int, x: int, y: int) -> Optional[Image.Image]:
        """Fetch a single tile from ESRI."""
        url = self.tile_url.format(z=z, y=y, x=x)
        try:
            response = await self._client.get(url)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
            else:
                print(f"[ESRI] Tile fetch failed: {url} -> {response.status_code}")
                return None
        except Exception as e:
            print(f"[ESRI] Tile fetch error: {url} -> {e}")
            return None

    async def get_satellite_image(
        self,
        bounds: dict,
        width: int = 1280,
        height: int = 1280,
    ) -> tuple[Optional[bytes], dict]:
        """
        Retrieve satellite imagery for a bounding box by stitching tiles.

        Args:
            bounds: Dict with north, south, east, west coordinates
            width: Desired image width (used to calculate zoom)
            height: Desired image height (used to calculate zoom)

        Returns:
            Tuple of (Image bytes (PNG), actual_bounds) or (None, {}) if failed
            actual_bounds reflects the exact geographic area covered by the stitched tiles
        """
        # Calculate the center and span
        center_lat = (bounds['north'] + bounds['south']) / 2
        center_lon = (bounds['east'] + bounds['west']) / 2
        lat_span = bounds['north'] - bounds['south']
        lon_span = bounds['east'] - bounds['west']

        # Calculate required meters per pixel
        lat_meters = lat_span * 111000
        lon_meters = lon_span * 111000 * math.cos(math.radians(center_lat))
        max_meters = max(lat_meters, lon_meters)

        # Calculate optimal zoom level
        # Start with zoom 17 (max for ESRI coverage in all regions)
        # Higher zoom levels may show "map data not yet available" in some areas
        zoom = 17

        # Get tile coordinates for corners at this zoom
        nw_tile = self._lat_lon_to_tile(bounds['north'], bounds['west'], zoom)
        se_tile = self._lat_lon_to_tile(bounds['south'], bounds['east'], zoom)

        # Calculate tile range (no extra padding - just what's needed)
        min_x = nw_tile[0]
        max_x = se_tile[0]
        min_y = nw_tile[1]
        max_y = se_tile[1]

        num_tiles_x = max_x - min_x + 1
        num_tiles_y = max_y - min_y + 1
        total_tiles = num_tiles_x * num_tiles_y

        # Allow up to 36 tiles (6x6) for better image quality
        # Only reduce zoom if we exceed this - higher zoom = sharper image
        max_tiles = 36
        while total_tiles > max_tiles and zoom > 14:
            zoom -= 1
            nw_tile = self._lat_lon_to_tile(bounds['north'], bounds['west'], zoom)
            se_tile = self._lat_lon_to_tile(bounds['south'], bounds['east'], zoom)
            min_x = nw_tile[0]
            max_x = se_tile[0]
            min_y = nw_tile[1]
            max_y = se_tile[1]
            num_tiles_x = max_x - min_x + 1
            num_tiles_y = max_y - min_y + 1
            total_tiles = num_tiles_x * num_tiles_y

        print(f"[ESRI] Selected zoom level {zoom} for {max_meters:.0f}m span")
        print(f"[ESRI] Fetching {num_tiles_x}x{num_tiles_y} = {total_tiles} tiles")

        # Fetch all tiles in parallel
        tasks = []
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                tasks.append(self._fetch_tile(zoom, x, y))

        tiles = await asyncio.gather(*tasks)

        # Create stitched image
        tile_size = 256
        stitched_width = num_tiles_x * tile_size
        stitched_height = num_tiles_y * tile_size
        stitched = Image.new('RGB', (stitched_width, stitched_height))

        idx = 0
        for yi, y in enumerate(range(min_y, max_y + 1)):
            for xi, x in enumerate(range(min_x, max_x + 1)):
                tile = tiles[idx]
                if tile:
                    stitched.paste(tile, (xi * tile_size, yi * tile_size))
                idx += 1

        # Calculate actual bounds of stitched image
        tile_bounds_nw = self._tile_to_lat_lon(min_x, min_y, zoom)  # north, south, east, west
        tile_bounds_se = self._tile_to_lat_lon(max_x, max_y, zoom)

        actual_bounds = {
            'north': tile_bounds_nw[0],  # north from top-left tile
            'south': tile_bounds_se[1],  # south from bottom-right tile
            'west': tile_bounds_nw[3],   # west from top-left tile
            'east': tile_bounds_se[2],   # east from bottom-right tile
        }

        print(f"[ESRI] Stitched image: {stitched_width}x{stitched_height}px")
        print(f"[ESRI] Actual bounds: N={actual_bounds['north']:.6f}, S={actual_bounds['south']:.6f}, E={actual_bounds['east']:.6f}, W={actual_bounds['west']:.6f}")

        # Now crop to the requested bounds
        # Convert requested bounds to pixel coordinates within the stitched image
        def lat_to_y(lat):
            """Convert latitude to pixel Y in stitched image."""
            lat_range = actual_bounds['north'] - actual_bounds['south']
            return int((actual_bounds['north'] - lat) / lat_range * stitched_height)

        def lon_to_x(lon):
            """Convert longitude to pixel X in stitched image."""
            lon_range = actual_bounds['east'] - actual_bounds['west']
            return int((lon - actual_bounds['west']) / lon_range * stitched_width)

        # Calculate crop box for requested bounds
        crop_left = max(0, lon_to_x(bounds['west']))
        crop_right = min(stitched_width, lon_to_x(bounds['east']))
        crop_top = max(0, lat_to_y(bounds['north']))
        crop_bottom = min(stitched_height, lat_to_y(bounds['south']))

        print(f"[ESRI] Crop region: ({crop_left}, {crop_top}) to ({crop_right}, {crop_bottom})")

        # Check if crop would result in too small an image - keep full stitched for quality
        crop_width = crop_right - crop_left
        crop_height = crop_bottom - crop_top
        min_dimension = 800  # Minimum pixels for good quality

        if crop_right <= crop_left or crop_bottom <= crop_top:
            print(f"[ESRI] Invalid crop region, using full stitched image")
            cropped = stitched
            final_bounds = actual_bounds
        elif crop_width < min_dimension or crop_height < min_dimension:
            print(f"[ESRI] Crop too small ({crop_width}x{crop_height}), using full stitched image for quality")
            cropped = stitched
            final_bounds = actual_bounds
        else:
            cropped = stitched.crop((crop_left, crop_top, crop_right, crop_bottom))
            # Calculate ACTUAL bounds of the cropped image (accounts for pixel rounding)
            lat_range = actual_bounds['north'] - actual_bounds['south']
            lon_range = actual_bounds['east'] - actual_bounds['west']
            final_bounds = {
                'north': actual_bounds['north'] - (crop_top / stitched_height) * lat_range,
                'south': actual_bounds['north'] - (crop_bottom / stitched_height) * lat_range,
                'west': actual_bounds['west'] + (crop_left / stitched_width) * lon_range,
                'east': actual_bounds['west'] + (crop_right / stitched_width) * lon_range,
            }

        print(f"[ESRI] Final image: {cropped.size[0]}x{cropped.size[1]}px")
        print(f"[ESRI] Final bounds: N={final_bounds['north']:.6f}, S={final_bounds['south']:.6f}, E={final_bounds['east']:.6f}, W={final_bounds['west']:.6f}")

        # Convert to bytes
        buffer = BytesIO()
        cropped.save(buffer, format='PNG', quality=95)
        image_bytes = buffer.getvalue()

        print(f"[ESRI] Image size: {len(image_bytes)} bytes")

        return image_bytes, final_bounds

    async def get_satellite_image_by_center(
        self,
        center: tuple[float, float],
        zoom: int,
        width: int = 1280,
        height: int = 1280,
    ) -> tuple[Optional[bytes], dict]:
        """
        Retrieve satellite imagery centered on a point at a given zoom level.

        Args:
            center: (lat, lon) tuple for map center
            zoom: Zoom level (similar to Leaflet/Google Maps)
            width: Image width in pixels
            height: Image height in pixels

        Returns:
            Tuple of (image_bytes, bounds_dict) or (None, {}) if failed
        """
        lat, lon = center

        # Calculate bounds from center + zoom
        # Approximate meters per pixel at this zoom and latitude
        meters_per_pixel = 156543.03392 * math.cos(math.radians(lat)) / (2 ** zoom)

        # Calculate geographic span
        width_meters = width * meters_per_pixel
        height_meters = height * meters_per_pixel

        # Convert to degrees
        lat_span = height_meters / 111000
        lon_span = width_meters / (111000 * math.cos(math.radians(lat)))

        bounds = {
            "north": lat + lat_span / 2,
            "south": lat - lat_span / 2,
            "east": lon + lon_span / 2,
            "west": lon - lon_span / 2,
        }

        return await self.get_satellite_image(bounds, width, height)
