"""
OSRM (Open Source Routing Machine) client for route validation.
100% free, no API key required.
"""

import httpx


class OSRMValidator:
    """
    Validate routes using OSRM (Open Source Routing Machine).

    FREE: 100% free, no API key required.
    Uses the public demo server.
    """

    def __init__(self, base_url: str = "https://router.project-osrm.org"):
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def test_connection(self) -> bool:
        """Test API connectivity."""
        try:
            # Simple route request to test
            result = await self.get_optimal_route(
                start=(-122.4194, 37.7749),  # San Francisco
                end=(-122.4089, 37.7849),
            )
            return result.get("valid", False)
        except Exception:
            return False

    async def validate_route(self, waypoints: list[tuple[float, float]]) -> dict:
        """
        Map-match waypoints against road network.

        Args:
            waypoints: List of (lon, lat) tuples - NOTE: lon first for OSRM!

        Returns:
            Validation results including confidence and snapped coordinates
        """
        # Build coordinate string
        coords_str = ";".join([f"{lon},{lat}" for lon, lat in waypoints])

        url = f"{self.base_url}/match/v1/driving/{coords_str}"
        params = {
            "geometries": "geojson",
            "overview": "full",
            "annotations": "true",
            "radiuses": ";".join(["50"] * len(waypoints)),  # 50m matching radius
        }

        response = await self._client.get(url, params=params)
        data = response.json()

        if data.get("code") == "Ok" and data.get("matchings"):
            matching = data["matchings"][0]
            return {
                "valid": True,
                "confidence": matching.get("confidence", 0),
                "matched_distance_m": matching.get("distance", 0),
                "matched_duration_s": matching.get("duration", 0),
                "snapped_coordinates": matching["geometry"]["coordinates"],
                "tracepoints": [
                    {
                        "original": waypoints[i],
                        "snapped": (t["location"][0], t["location"][1]) if t else None,
                        "distance_from_original_m": t.get("distance", 0) if t else None,
                        "matched": t is not None,
                    }
                    for i, t in enumerate(data.get("tracepoints", []))
                ],
            }

        return {
            "valid": False,
            "error": data.get("code", "Unknown error"),
            "message": data.get("message", ""),
        }

    async def get_optimal_route(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        via: list[tuple[float, float]] = None,
    ) -> dict:
        """
        Get optimal road route between points.

        Args:
            start: (lon, lat) origin
            end: (lon, lat) destination
            via: Optional intermediate waypoints

        Returns:
            Optimal route with geometry and turn-by-turn
        """
        points = [start]
        if via:
            points.extend(via)
        points.append(end)

        coords_str = ";".join([f"{lon},{lat}" for lon, lat in points])

        url = f"{self.base_url}/route/v1/driving/{coords_str}"
        params = {
            "geometries": "geojson",
            "overview": "full",
            "steps": "true",
            "annotations": "true",
        }

        response = await self._client.get(url, params=params)
        data = response.json()

        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            return {
                "valid": True,
                "distance_m": route.get("distance", 0),
                "duration_s": route.get("duration", 0),
                "geometry": route.get("geometry", {}),
                "legs": [
                    {
                        "distance_m": leg.get("distance", 0),
                        "duration_s": leg.get("duration", 0),
                        "steps": [
                            {
                                "name": step.get("name", ""),
                                "distance_m": step.get("distance", 0),
                                "duration_s": step.get("duration", 0),
                                "maneuver": step.get("maneuver", {}),
                            }
                            for step in leg.get("steps", [])
                        ],
                    }
                    for leg in route.get("legs", [])
                ],
            }

        return {"valid": False, "error": data.get("code", "Unknown")}

    async def compare_proposed_vs_optimal(
        self,
        proposed_waypoints: list[tuple[float, float]],
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> dict:
        """
        Compare a proposed route against the optimal road route.
        Useful for understanding how much the proposed route deviates.
        """
        # Get optimal route
        optimal = await self.get_optimal_route(start, end)

        # Validate proposed route
        proposed = await self.validate_route(proposed_waypoints)

        if optimal.get("valid") and proposed.get("valid"):
            optimal_dist = optimal["distance_m"]
            proposed_dist = proposed["matched_distance_m"]

            return {
                "comparison_valid": True,
                "optimal_route": {
                    "distance_m": optimal_dist,
                    "duration_s": optimal["duration_s"],
                },
                "proposed_route": {
                    "distance_m": proposed_dist,
                    "duration_s": proposed["matched_duration_s"],
                    "confidence": proposed["confidence"],
                },
                "analysis": {
                    "distance_ratio": (
                        proposed_dist / optimal_dist if optimal_dist > 0 else 0
                    ),
                    "detour_percentage": (
                        (proposed_dist - optimal_dist) / optimal_dist * 100
                        if optimal_dist > 0
                        else 0
                    ),
                    "is_efficient": proposed_dist
                    <= optimal_dist * 1.2,  # Within 20% of optimal
                },
            }

        return {
            "comparison_valid": False,
            "optimal_error": optimal.get("error"),
            "proposed_error": proposed.get("error"),
        }
