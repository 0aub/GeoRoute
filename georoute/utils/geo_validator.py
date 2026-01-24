"""
Geographic validation utilities.
Restricts operations to Gulf Cooperation Council (GCC) countries.
"""

from typing import Tuple


class GulfRegionValidator:
    """
    Validates that coordinates are within Gulf countries:
    - Saudi Arabia
    - United Arab Emirates
    - Kuwait
    - Bahrain
    - Qatar
    - Oman
    """

    # Gulf region bounding box (approximate)
    # Covers KSA, UAE, Kuwait, Bahrain, Qatar, Oman
    GULF_BOUNDS = {
        "min_lat": 16.0,  # Southern Yemen border
        "max_lat": 32.0,  # Northern Kuwait/Iraq border
        "min_lon": 34.5,  # Red Sea coast (western Saudi)
        "max_lon": 60.0,  # Eastern Oman
    }

    # More precise country boundaries
    COUNTRY_BOUNDS = {
        "saudi_arabia": {
            "min_lat": 16.0,
            "max_lat": 32.0,
            "min_lon": 34.5,
            "max_lon": 56.0,
        },
        "uae": {
            "min_lat": 22.5,
            "max_lat": 26.5,
            "min_lon": 51.5,
            "max_lon": 56.5,
        },
        "kuwait": {
            "min_lat": 28.5,
            "max_lat": 30.1,
            "min_lon": 46.5,
            "max_lon": 49.0,
        },
        "bahrain": {
            "min_lat": 25.5,
            "max_lat": 26.5,
            "min_lon": 50.3,
            "max_lon": 50.9,
        },
        "qatar": {
            "min_lat": 24.5,
            "max_lat": 26.5,
            "min_lon": 50.7,
            "max_lon": 51.7,
        },
        "oman": {
            "min_lat": 16.5,
            "max_lat": 26.5,
            "min_lon": 52.0,
            "max_lon": 60.0,
        },
    }

    @classmethod
    def is_in_gulf_region(cls, lat: float, lon: float) -> bool:
        """
        Check if coordinates are within the Gulf region.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            True if within Gulf region bounds
        """
        return (
            cls.GULF_BOUNDS["min_lat"] <= lat <= cls.GULF_BOUNDS["max_lat"]
            and cls.GULF_BOUNDS["min_lon"] <= lon <= cls.GULF_BOUNDS["max_lon"]
        )

    @classmethod
    def get_country(cls, lat: float, lon: float) -> str | None:
        """
        Determine which Gulf country the coordinates are in.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Country name or None if outside Gulf region
        """
        for country, bounds in cls.COUNTRY_BOUNDS.items():
            if (
                bounds["min_lat"] <= lat <= bounds["max_lat"]
                and bounds["min_lon"] <= lon <= bounds["max_lon"]
            ):
                return country
        return None

    @classmethod
    def validate_coordinates(cls, lat: float, lon: float) -> Tuple[bool, str]:
        """
        Validate that coordinates are within Gulf region.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Tuple of (is_valid, message)
        """
        if not cls.is_in_gulf_region(lat, lon):
            return False, (
                f"Coordinates ({lat:.4f}, {lon:.4f}) are outside the Gulf region. "
                "This system only operates in Gulf Cooperation Council (GCC) countries: "
                "Saudi Arabia, UAE, Kuwait, Bahrain, Qatar, and Oman."
            )

        country = cls.get_country(lat, lon)
        if country:
            return True, f"Valid coordinates in {country.replace('_', ' ').title()}"
        else:
            # In Gulf bounds but not in a specific country (might be border area)
            return True, "Valid coordinates in Gulf region"

    @classmethod
    def validate_route(
        cls, soldiers: list, enemies: list
    ) -> Tuple[bool, str]:
        """
        Validate that all tactical units are within Gulf region.

        Args:
            soldiers: List of soldier units with lat/lon
            enemies: List of enemy units with lat/lon

        Returns:
            Tuple of (is_valid, message)
        """
        # Check all soldier positions
        for i, soldier in enumerate(soldiers):
            is_valid, msg = cls.validate_coordinates(soldier.lat, soldier.lon)
            if not is_valid:
                return False, f"Soldier {i+1}: {msg}"

        # Check all enemy positions
        for i, enemy in enumerate(enemies):
            is_valid, msg = cls.validate_coordinates(enemy.lat, enemy.lon)
            if not is_valid:
                return False, f"Enemy {i+1}: {msg}"

        return True, "All units within Gulf region"
