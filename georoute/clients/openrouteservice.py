"""
OpenRouteService client for elevation profiles and surface analysis.
FREE TIER: 2,000 requests/day.
"""

from typing import Optional
import httpx


class OpenRouteServiceValidator:
    """
    Additional route validation with elevation profiles and surface types.

    FREE TIER: 2,000 requests/day.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.openrouteservice.org/v2"
        self._client = httpx.AsyncClient(timeout=30.0) if api_key else None

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()

    def is_available(self) -> bool:
        """Check if ORS is configured."""
        return self.api_key is not None

    async def test_connection(self) -> bool:
        """Test API connectivity."""
        if not self._client:
            return False
        try:
            # Simple route request
            result = await self.get_route_with_elevation(
                start=(-122.4194, 37.7749),
                end=(-122.4089, 37.7849),
            )
            return result.get("valid", False)
        except Exception:
            return False

    async def get_route_with_elevation(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        waypoints: list[tuple[float, float]] = None,
    ) -> dict:
        """
        Get route with detailed elevation profile and surface analysis.

        Args:
            start: (lon, lat) origin
            end: (lon, lat) destination
            waypoints: Optional intermediate points (lon, lat)

        Returns:
            Route with elevation, surface, and steepness data
        """
        if not self._client:
            return {"valid": False, "error": "ORS client not initialized - no API key"}

        coordinates = [list(start)]
        if waypoints:
            coordinates.extend([list(w) for w in waypoints])
        coordinates.append(list(end))

        url = f"{self.base_url}/directions/foot-walking/geojson"
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "coordinates": coordinates,
            "elevation": True,
            "extra_info": ["steepness", "surface", "waycategory", "waytype"],
        }

        try:
            response = await self._client.post(url, headers=headers, json=body)
            data = response.json()

            if response.status_code == 200 and data.get("features"):
                feature = data["features"][0]
                props = feature.get("properties", {})
                geom = feature.get("geometry", {})
                coords = geom.get("coordinates", [])

                # Extract elevations if 3D coordinates
                elevations = []
                if coords and len(coords[0]) >= 3:
                    elevations = [c[2] for c in coords]

                summary = props.get("summary", {})
                extras = props.get("extras", {})

                return {
                    "valid": True,
                    "distance_m": summary.get("distance", 0),
                    "duration_s": summary.get("duration", 0),
                    "ascent_m": props.get("ascent", 0),
                    "descent_m": props.get("descent", 0),
                    "elevation_profile": {
                        "elevations": elevations,
                        "min_m": min(elevations) if elevations else None,
                        "max_m": max(elevations) if elevations else None,
                    },
                    "surface_analysis": self._parse_extras(extras.get("surface", {})),
                    "steepness_analysis": self._parse_extras(
                        extras.get("steepness", {})
                    ),
                    "way_types": self._parse_extras(extras.get("waytype", {})),
                    "geometry": geom,
                }

            return {
                "valid": False,
                "error": data.get("error", {}).get("message", "Unknown error"),
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def get_walking_routes(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> list[dict]:
        """
        Get walking routes using OpenRouteService foot-walking profile.
        Returns up to 3 alternative routes that respect buildings and obstacles.

        Args:
            origin: (lat, lon) start point
            destination: (lat, lon) end point

        Returns:
            List of route dictionaries with waypoints and metadata
        """
        if not self._client:
            return []

        # ORS uses (lon, lat) format, opposite of (lat, lon)
        coordinates = [[origin[1], origin[0]], [destination[1], destination[0]]]

        url = f"{self.base_url}/directions/foot-walking/geojson"
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "coordinates": coordinates,
            "elevation": True,
            "alternative_routes": {
                "target_count": 3,
                "share_factor": 0.6,
                "weight_factor": 1.4,
            },
            "extra_info": ["surface", "steepness", "waytype"],
        }

        try:
            response = await self._client.post(url, headers=headers, json=body)
            data = response.json()

            routes = []
            if response.status_code == 200 and data.get("features"):
                for idx, feature in enumerate(data["features"][:3]):  # Max 3 routes
                    props = feature.get("properties", {})
                    geom = feature.get("geometry", {})
                    coords = geom.get("coordinates", [])

                    # Extract waypoints from geometry
                    # Sample waypoints to reduce density (max 20 waypoints per route)
                    # This prevents Gemini from being overwhelmed with data
                    max_waypoints = 20
                    sample_rate = max(1, len(coords) // max_waypoints)

                    waypoints = []
                    distance_from_start = 0.0

                    for i in range(0, len(coords), sample_rate):
                        coord = coords[i]

                        # ORS returns [lon, lat, elevation]
                        waypoint = {
                            "lat": coord[1],
                            "lon": coord[0],
                            "distance_from_start_m": distance_from_start,
                        }

                        # Add elevation if available
                        if len(coord) >= 3:
                            waypoint["elevation_m"] = coord[2]

                        waypoints.append(waypoint)

                        # Calculate cumulative distance
                        if i > 0:
                            for j in range(max(0, i - sample_rate), i):
                                if j + 1 < len(coords):
                                    prev = coords[j]
                                    curr = coords[j + 1]

                                    from math import radians, sin, cos, sqrt, atan2
                                    lat1, lon1 = radians(prev[1]), radians(prev[0])
                                    lat2, lon2 = radians(curr[1]), radians(curr[0])

                                    dlat = lat2 - lat1
                                    dlon = lon2 - lon1

                                    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
                                    c = 2 * atan2(sqrt(a), sqrt(1 - a))
                                    dist = 6371000 * c

                                    distance_from_start += dist

                    # Always include the final point
                    if coords and coords[-1] != coords[i]:
                        final_coord = coords[-1]
                        waypoints.append({
                            "lat": final_coord[1],
                            "lon": final_coord[0],
                            "distance_from_start_m": distance_from_start,
                            "elevation_m": final_coord[2] if len(final_coord) >= 3 else 0.0,
                        })

                    summary = props.get("summary", {})

                    routes.append({
                        "route_id": idx + 1,
                        "waypoints": waypoints,
                        "total_distance_m": summary.get("distance", 0),
                        "total_duration_s": summary.get("duration", 0),
                        "summary": f"Walking Route {idx + 1}",
                        "ascent_m": props.get("ascent", 0),
                        "descent_m": props.get("descent", 0),
                    })

            return routes

        except Exception as e:
            print(f"ORS walking routes error: {e}")
            return []

    def _parse_extras(self, extra_data: dict) -> dict:
        """Parse ORS extra_info format into readable dict."""
        if not extra_data:
            return {}

        values = extra_data.get("values", [])
        summary = extra_data.get("summary", [])

        return {
            "segments": [
                {"start": v[0], "end": v[1], "value": v[2]} for v in values
            ],
            "summary": [
                {
                    "value": s.get("value"),
                    "distance_m": s.get("distance"),
                    "percentage": s.get("amount"),
                }
                for s in summary
            ],
        }

    async def validate_elevation_constraints(
        self,
        waypoints: list[tuple[float, float]],
        max_slope_degrees: float = 30,
    ) -> dict:
        """
        Check if a route meets elevation/slope constraints.
        """
        if len(waypoints) < 2:
            return {"valid": False, "error": "Need at least 2 waypoints"}

        route = await self.get_route_with_elevation(
            start=waypoints[0],
            end=waypoints[-1],
            waypoints=waypoints[1:-1] if len(waypoints) > 2 else None,
        )

        if not route.get("valid"):
            return route

        # Analyze steepness
        steepness = route.get("steepness_analysis", {})
        steep_segments = [
            s
            for s in steepness.get("summary", [])
            if abs(s.get("value", 0)) > max_slope_degrees
        ]

        total_distance = route["distance_m"]
        steep_distance = sum(s.get("distance_m", 0) for s in steep_segments)

        return {
            "valid": True,
            "meets_constraints": len(steep_segments) == 0,
            "max_slope_constraint": max_slope_degrees,
            "route_summary": {
                "distance_m": total_distance,
                "ascent_m": route.get("ascent_m", 0),
                "descent_m": route.get("descent_m", 0),
            },
            "constraint_violations": {
                "steep_segments_count": len(steep_segments),
                "steep_distance_m": steep_distance,
                "steep_percentage": (
                    (steep_distance / total_distance * 100) if total_distance > 0 else 0
                ),
            },
            "elevation_profile": route.get("elevation_profile", {}),
            "surface_breakdown": route.get("surface_analysis", {}),
        }
