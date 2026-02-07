"""
Google Maps Platform API client.
Provides elevation data and satellite imagery.

Requires enabling in Google Cloud Console:
- Maps Elevation API
- Maps Static API
"""

import math
from typing import Optional
from io import BytesIO
import httpx
from PIL import Image


class GoogleMapsClient:
    """
    Client for Google Maps Platform APIs.

    FREE TIER: $200/month credit covers approximately:
    - 40,000 elevation API calls
    - 100,000 static map loads
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Google Maps API key is required")
        self.api_key = api_key
        self.elevation_url = "https://maps.googleapis.com/maps/api/elevation/json"
        self.static_maps_url = "https://maps.googleapis.com/maps/api/staticmap"
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def test_connection(self) -> bool:
        """Test API connectivity with a simple elevation request."""
        try:
            result = await self.get_elevation_at_points([(36.1069, -112.1129)])
            return result.get("success", False)
        except Exception:
            return False

    async def get_elevation_at_points(
        self, coordinates: list[tuple[float, float]]
    ) -> dict:
        """
        Get elevation at specific coordinate points.

        Args:
            coordinates: List of (lat, lon) tuples (max 512 per request)

        Returns:
            Dict with elevations and metadata
        """
        if len(coordinates) > 512:
            raise ValueError("Maximum 512 coordinates per request")

        locations = "|".join([f"{lat},{lon}" for lat, lon in coordinates])
        params = {"locations": locations, "key": self.api_key}

        response = await self._client.get(self.elevation_url, params=params)
        data = response.json()

        if data["status"] == "OK":
            return {
                "success": True,
                "elevations": [
                    {
                        "lat": r["location"]["lat"],
                        "lon": r["location"]["lng"],
                        "elevation_m": r["elevation"],
                        "resolution_m": r.get("resolution", 30),
                    }
                    for r in data["results"]
                ],
            }
        return {"success": False, "error": data["status"]}

    async def get_satellite_image(
        self,
        center: tuple[float, float],
        zoom: int = 14,
        size: str = "640x640",
        scale: int = 2,
        map_type: str = "satellite",
    ) -> Optional[bytes]:
        """
        Retrieve satellite or terrain imagery for a location.

        Args:
            center: (lat, lon) tuple for map center
            zoom: Zoom level (1-21, higher = more detail)
            size: Image dimensions (max 640x640)
            scale: 1 or 2 (2 = high DPI)
            map_type: "satellite", "terrain", "roadmap", "hybrid"

        Returns:
            Image bytes (JPEG) or None if failed
        """
        params = {
            "center": f"{center[0]},{center[1]}",
            "zoom": zoom,
            "size": size,
            "maptype": map_type,
            "scale": scale,
            "key": self.api_key,
        }

        response = await self._client.get(self.static_maps_url, params=params)

        if response.status_code == 200:
            return response.content
        return None

    async def get_terrain_image(
        self, center: tuple[float, float], zoom: int = 12
    ) -> Optional[bytes]:
        """Get terrain map showing elevation contours and shading."""
        return await self.get_satellite_image(
            center=center, zoom=zoom, map_type="terrain"
        )

    async def get_satellite_image_by_bounds(
        self,
        bounds: dict,
        width: int = 1280,
        height: int = 1280,
    ) -> tuple[Optional[bytes], dict]:
        """
        Retrieve satellite imagery for a bounding box.

        Uses Google Maps Static API with multiple tiles stitched together
        for high-resolution coverage of the area.

        Args:
            bounds: Dict with north, south, east, west coordinates
            width: Desired image width (used to calculate zoom)
            height: Desired image height (used to calculate zoom)

        Returns:
            Tuple of (Image bytes (PNG), actual_bounds) or (None, {}) if failed
        """
        # Calculate center
        center_lat = (bounds['north'] + bounds['south']) / 2
        center_lon = (bounds['east'] + bounds['west']) / 2

        # Calculate geographic span
        lat_span = bounds['north'] - bounds['south']
        lon_span = bounds['east'] - bounds['west']

        # Calculate meters per degree at this latitude
        lat_meters = lat_span * 111000
        lon_meters = lon_span * 111000 * math.cos(math.radians(center_lat))
        max_span_meters = max(lat_meters, lon_meters)

        # Calculate optimal zoom level
        # Google Maps: ~156543 * cos(lat) / 2^zoom meters per pixel at equator
        # We want the span to fit in our image width
        target_meters_per_pixel = max_span_meters / width
        zoom = 21  # Start with max zoom
        for z in range(21, 0, -1):
            meters_per_pixel = 156543.03392 * math.cos(math.radians(center_lat)) / (2 ** z)
            if meters_per_pixel * width >= max_span_meters:
                zoom = z
                break

        # Clamp zoom to reasonable range (higher = better quality)
        zoom = max(15, min(20, zoom))

        print(f"[GoogleMaps] Calculated zoom {zoom} for {max_span_meters:.0f}m span")

        # Google Static Maps max size is 640x640 at scale=1, or 1280x1280 at scale=2
        # For larger areas, we need to stitch multiple tiles
        max_tile_size = 640
        scale = 2  # Get high-DPI images

        # Calculate how many tiles we need
        meters_per_pixel = 156543.03392 * math.cos(math.radians(center_lat)) / (2 ** zoom)
        tile_span_meters = max_tile_size * scale * meters_per_pixel
        tile_span_lat = tile_span_meters / 111000
        tile_span_lon = tile_span_meters / (111000 * math.cos(math.radians(center_lat)))

        # Calculate number of tiles needed
        num_tiles_lat = max(1, math.ceil(lat_span / tile_span_lat))
        num_tiles_lon = max(1, math.ceil(lon_span / tile_span_lon))

        # Limit to reasonable tile count
        max_tiles = 4  # 2x2 grid max to control costs
        if num_tiles_lat * num_tiles_lon > max_tiles:
            # Reduce zoom to fit in fewer tiles
            zoom = max(14, zoom - 1)
            meters_per_pixel = 156543.03392 * math.cos(math.radians(center_lat)) / (2 ** zoom)
            tile_span_meters = max_tile_size * scale * meters_per_pixel
            tile_span_lat = tile_span_meters / 111000
            tile_span_lon = tile_span_meters / (111000 * math.cos(math.radians(center_lat)))
            num_tiles_lat = max(1, min(2, math.ceil(lat_span / tile_span_lat)))
            num_tiles_lon = max(1, min(2, math.ceil(lon_span / tile_span_lon)))

        total_tiles = num_tiles_lat * num_tiles_lon
        print(f"[GoogleMaps] Fetching {num_tiles_lon}x{num_tiles_lat} = {total_tiles} tiles at zoom {zoom}")

        # For single tile, just fetch it centered
        if total_tiles == 1:
            image_bytes = await self.get_satellite_image(
                center=(center_lat, center_lon),
                zoom=zoom,
                size=f"{max_tile_size}x{max_tile_size}",
                scale=scale,
                map_type="satellite"
            )

            if image_bytes:
                # Calculate actual bounds covered by this tile
                actual_lat_span = tile_span_lat
                actual_lon_span = tile_span_lon
                actual_bounds = {
                    'north': center_lat + actual_lat_span / 2,
                    'south': center_lat - actual_lat_span / 2,
                    'east': center_lon + actual_lon_span / 2,
                    'west': center_lon - actual_lon_span / 2,
                }

                # Convert to PNG
                img = Image.open(BytesIO(image_bytes))
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                png_bytes = buffer.getvalue()

                print(f"[GoogleMaps] Single tile: {img.size[0]}x{img.size[1]}px")
                print(f"[GoogleMaps] Actual bounds: N={actual_bounds['north']:.6f}, S={actual_bounds['south']:.6f}")

                return png_bytes, actual_bounds
            return None, {}

        # Multi-tile stitching
        tiles = []
        tile_positions = []

        # Calculate tile centers
        total_lat_span = tile_span_lat * num_tiles_lat
        total_lon_span = tile_span_lon * num_tiles_lon
        start_lat = center_lat + total_lat_span / 2 - tile_span_lat / 2
        start_lon = center_lon - total_lon_span / 2 + tile_span_lon / 2

        for row in range(num_tiles_lat):
            for col in range(num_tiles_lon):
                tile_center_lat = start_lat - row * tile_span_lat
                tile_center_lon = start_lon + col * tile_span_lon

                tile_bytes = await self.get_satellite_image(
                    center=(tile_center_lat, tile_center_lon),
                    zoom=zoom,
                    size=f"{max_tile_size}x{max_tile_size}",
                    scale=scale,
                    map_type="satellite"
                )

                if tile_bytes:
                    tiles.append(Image.open(BytesIO(tile_bytes)))
                    tile_positions.append((col, row))
                else:
                    print(f"[GoogleMaps] Failed to fetch tile at ({tile_center_lat}, {tile_center_lon})")
                    return None, {}

        # Stitch tiles together
        tile_pixel_size = max_tile_size * scale
        stitched_width = num_tiles_lon * tile_pixel_size
        stitched_height = num_tiles_lat * tile_pixel_size
        stitched = Image.new('RGB', (stitched_width, stitched_height))

        for tile, (col, row) in zip(tiles, tile_positions):
            stitched.paste(tile, (col * tile_pixel_size, row * tile_pixel_size))

        # Calculate actual bounds of stitched image
        actual_bounds = {
            'north': start_lat + tile_span_lat / 2,
            'south': start_lat - (num_tiles_lat - 1) * tile_span_lat - tile_span_lat / 2,
            'west': start_lon - tile_span_lon / 2,
            'east': start_lon + (num_tiles_lon - 1) * tile_span_lon + tile_span_lon / 2,
        }

        print(f"[GoogleMaps] Stitched image: {stitched_width}x{stitched_height}px")
        print(f"[GoogleMaps] Actual bounds: N={actual_bounds['north']:.6f}, S={actual_bounds['south']:.6f}")

        # Convert to PNG bytes
        buffer = BytesIO()
        stitched.save(buffer, format='PNG')
        png_bytes = buffer.getvalue()

        print(f"[GoogleMaps] Image size: {len(png_bytes)} bytes")

        return png_bytes, actual_bounds
