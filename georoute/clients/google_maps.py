"""
Google Maps Platform API client.
Provides elevation data, satellite imagery, and road routing.
"""

import math
from typing import Optional
import httpx


class GoogleMapsClient:
    """
    Client for Google Maps Platform APIs.

    FREE TIER: $200/month credit covers approximately:
    - 40,000 elevation API calls
    - 100,000 static map loads
    - 40,000 directions requests
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Google Maps API key is required")
        self.api_key = api_key
        self.elevation_url = "https://maps.googleapis.com/maps/api/elevation/json"
        self.static_maps_url = "https://maps.googleapis.com/maps/api/staticmap"
        self.directions_url = "https://maps.googleapis.com/maps/api/directions/json"
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def test_connection(self) -> bool:
        """Test API connectivity with a simple elevation request."""
        try:
            # Use valid land coordinates for testing (Grand Canyon)
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

    async def get_elevation_profile(
        self, path_coords: list[tuple[float, float]], samples: int = 100
    ) -> dict:
        """
        Extract elevation profile along a route path.

        Args:
            path_coords: List of (lat, lon) tuples defining the path
            samples: Number of equidistant sample points (max 512)

        Returns:
            Dict with elevation profile data
        """
        path_str = "|".join([f"{lat},{lon}" for lat, lon in path_coords])

        params = {
            "path": path_str,
            "samples": min(samples, 512),
            "key": self.api_key,
        }

        response = await self._client.get(self.elevation_url, params=params)
        data = response.json()

        if data["status"] == "OK":
            elevations = [r["elevation"] for r in data["results"]]
            locations = [
                (r["location"]["lat"], r["location"]["lng"]) for r in data["results"]
            ]

            # Calculate elevation statistics
            elevation_changes = [
                elevations[i + 1] - elevations[i] for i in range(len(elevations) - 1)
            ]

            return {
                "success": True,
                "elevations_m": elevations,
                "locations": locations,
                "resolution_m": data["results"][0].get("resolution", 30),
                "statistics": {
                    "min_elevation_m": min(elevations),
                    "max_elevation_m": max(elevations),
                    "total_ascent_m": sum(c for c in elevation_changes if c > 0),
                    "total_descent_m": abs(sum(c for c in elevation_changes if c < 0)),
                    "max_elevation_change_m": (
                        max(abs(c) for c in elevation_changes) if elevation_changes else 0
                    ),
                },
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
        else:
            print(f"[GoogleMaps] Static Maps API error: {response.status_code}")
            print(f"[GoogleMaps] Response: {response.text[:500] if response.text else 'No response body'}")
            return None

    async def get_terrain_image(
        self, center: tuple[float, float], zoom: int = 12
    ) -> Optional[bytes]:
        """Get terrain map showing elevation contours and shading."""
        return await self.get_satellite_image(
            center=center, zoom=zoom, map_type="terrain"
        )

    async def get_walking_routes(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        waypoints: list[tuple[float, float]] = None,
    ) -> list[dict]:
        """
        Get walking routes from origin to destination with alternatives.
        Uses Google Routes API v2.

        Args:
            origin: (lat, lon) start point
            destination: (lat, lon) end point
            waypoints: Optional intermediate waypoints to force route through

        Returns:
            List of route dictionaries with waypoints and metadata
        """
        # Routes API v2 endpoint
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"

        # Build request body
        request_body = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": origin[0],
                        "longitude": origin[1]
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": destination[0],
                        "longitude": destination[1]
                    }
                }
            },
            "travelMode": "WALK",
            "computeAlternativeRoutes": True,
            "routingPreference": "ROUTING_PREFERENCE_UNSPECIFIED",
        }

        if waypoints:
            request_body["intermediates"] = [
                {
                    "location": {
                        "latLng": {
                            "latitude": wp[0],
                            "longitude": wp[1]
                        }
                    }
                }
                for wp in waypoints
            ]

        # Required headers for Routes API v2
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.legs.steps.startLocation,routes.legs.steps.endLocation,routes.legs.distanceMeters,routes.legs.duration,routes.description"
        }

        response = await self._client.post(url, json=request_body, headers=headers)
        data = response.json()

        routes = []
        if "routes" in data:
            for idx, route in enumerate(data["routes"][:3]):  # Max 3 routes
                if not route.get("legs"):
                    continue

                leg = route["legs"][0]

                # Extract waypoints from steps
                route_waypoints = []
                distance_from_start = 0.0

                for step in leg.get("steps", []):
                    if "startLocation" in step and "latLng" in step["startLocation"]:
                        lat_lng = step["startLocation"]["latLng"]
                        route_waypoints.append({
                            "lat": lat_lng["latitude"],
                            "lon": lat_lng["longitude"],
                            "distance_from_start_m": distance_from_start,
                        })

                    # Add step distance
                    if "distanceMeters" in step:
                        distance_from_start += step["distanceMeters"]

                # Add final point from last step
                if leg.get("steps") and "endLocation" in leg["steps"][-1]:
                    end_loc = leg["steps"][-1]["endLocation"]["latLng"]
                    route_waypoints.append({
                        "lat": end_loc["latitude"],
                        "lon": end_loc["longitude"],
                        "distance_from_start_m": distance_from_start,
                    })

                # Get total distance and duration
                total_distance = leg.get("distanceMeters", 0)
                duration_str = leg.get("duration", "0s")
                # Parse duration string like "1234s" to integer
                total_duration = int(duration_str.rstrip('s')) if duration_str.endswith('s') else 0

                routes.append({
                    "route_id": idx + 1,
                    "waypoints": route_waypoints,
                    "total_distance_m": total_distance,
                    "total_duration_s": total_duration,
                    "summary": route.get("description", f"Route {idx + 1}"),
                })

        return routes

    async def get_road_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        waypoints: list[tuple[float, float]] = None,
        avoid: list[str] = None,
    ) -> dict:
        """
        Get road-based route with turn-by-turn segments.

        Args:
            origin: (lat, lon) start point
            destination: (lat, lon) end point
            waypoints: Optional intermediate points
            avoid: List of features to avoid: "tolls", "highways", "ferries"

        Returns:
            Route data including distance, duration, and steps
        """
        params = {
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
            "mode": "driving",
            "key": self.api_key,
        }

        if waypoints:
            wp_str = "|".join([f"{w[0]},{w[1]}" for w in waypoints])
            params["waypoints"] = f"optimize:true|{wp_str}"

        if avoid:
            params["avoid"] = "|".join(avoid)

        response = await self._client.get(self.directions_url, params=params)
        data = response.json()

        if data.get("status") == "OK" and data.get("routes"):
            route = data["routes"][0]
            leg = route["legs"][0]

            return {
                "success": True,
                "distance_m": leg["distance"]["value"],
                "duration_s": leg["duration"]["value"],
                "start_address": leg.get("start_address"),
                "end_address": leg.get("end_address"),
                "steps": [
                    {
                        "instruction": step.get("html_instructions", ""),
                        "distance_m": step["distance"]["value"],
                        "duration_s": step["duration"]["value"],
                        "start_location": (
                            step["start_location"]["lat"],
                            step["start_location"]["lng"],
                        ),
                        "end_location": (
                            step["end_location"]["lat"],
                            step["end_location"]["lng"],
                        ),
                    }
                    for step in leg.get("steps", [])
                ],
                "polyline": route.get("overview_polyline", {}).get("points"),
            }
        return {"success": False, "error": data.get("status", "Unknown error")}

    async def get_elevation_grid(
        self, bounds: tuple[float, float, float, float], grid_size: int = 10
    ) -> dict:
        """
        Get elevation data for a grid of points covering an area.

        Args:
            bounds: (south, north, west, east) bounding box
            grid_size: Number of points per side (total = grid_size^2)

        Returns:
            Grid of elevation data with statistics
        """
        south, north, west, east = bounds

        # Generate grid points
        lat_step = (north - south) / (grid_size - 1)
        lon_step = (east - west) / (grid_size - 1)

        grid_points = []
        for i in range(grid_size):
            for j in range(grid_size):
                lat = south + (i * lat_step)
                lon = west + (j * lon_step)
                grid_points.append((lat, lon))

        # Get elevations (may need multiple calls if > 512 points)
        all_elevations = []
        for i in range(0, len(grid_points), 512):
            batch = grid_points[i : i + 512]
            result = await self.get_elevation_at_points(batch)
            if result["success"]:
                all_elevations.extend(result["elevations"])

        if all_elevations:
            elevs = [e["elevation_m"] for e in all_elevations]
            return {
                "success": True,
                "bounds": bounds,
                "grid_size": grid_size,
                "points": all_elevations,
                "statistics": {
                    "min_elevation_m": min(elevs),
                    "max_elevation_m": max(elevs),
                    "mean_elevation_m": sum(elevs) / len(elevs),
                    "elevation_range_m": max(elevs) - min(elevs),
                },
            }
        return {"success": False, "error": "Failed to get elevations"}
