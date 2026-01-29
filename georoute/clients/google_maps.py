"""
Google Maps Platform API client.
Provides elevation data and satellite imagery.
"""

from typing import Optional
import httpx


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
