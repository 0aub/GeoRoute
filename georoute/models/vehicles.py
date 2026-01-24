"""Vehicle profile models and predefined profiles."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleProfile:
    """Vehicle capabilities and constraints."""
    name: str
    type: str  # e.g., "MRAP", "Light Tactical", "Heavy Truck"
    max_slope_degrees: float
    ground_clearance_cm: float
    weight_tons: float
    max_ford_depth_cm: float
    preferred_surfaces: list[str]
    avoid_surfaces: list[str]
    max_speed_on_road_kmh: float = 100
    max_speed_off_road_kmh: float = 30

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses and Gemini context."""
        return {
            "name": self.name,
            "type": self.type,
            "max_slope_degrees": self.max_slope_degrees,
            "ground_clearance_cm": self.ground_clearance_cm,
            "weight_tons": self.weight_tons,
            "max_ford_depth_cm": self.max_ford_depth_cm,
            "preferred_surfaces": list(self.preferred_surfaces),
            "avoid_surfaces": list(self.avoid_surfaces),
            "max_speed_on_road_kmh": self.max_speed_on_road_kmh,
            "max_speed_off_road_kmh": self.max_speed_off_road_kmh,
        }


# Predefined vehicle profiles
VEHICLE_PROFILES: dict[str, VehicleProfile] = {
    "mrap": VehicleProfile(
        name="M-ATV MRAP",
        type="Mine-Resistant Ambush Protected",
        max_slope_degrees=35,
        ground_clearance_cm=36,
        weight_tons=14.5,
        max_ford_depth_cm=76,
        preferred_surfaces=["asphalt", "concrete", "gravel", "improved_dirt"],
        avoid_surfaces=["deep_mud", "loose_sand", "swamp"],
        max_speed_on_road_kmh=105,
        max_speed_off_road_kmh=40,
    ),
    "humvee": VehicleProfile(
        name="HMMWV",
        type="High Mobility Multipurpose Wheeled Vehicle",
        max_slope_degrees=40,
        ground_clearance_cm=41,
        weight_tons=3.5,
        max_ford_depth_cm=76,
        preferred_surfaces=["asphalt", "gravel", "dirt", "sand"],
        avoid_surfaces=["deep_mud", "swamp", "boulder_field"],
        max_speed_on_road_kmh=113,
        max_speed_off_road_kmh=50,
    ),
    "light_truck": VehicleProfile(
        name="Light Tactical Truck",
        type="4x4 Light Truck",
        max_slope_degrees=30,
        ground_clearance_cm=25,
        weight_tons=5,
        max_ford_depth_cm=50,
        preferred_surfaces=["asphalt", "concrete", "gravel"],
        avoid_surfaces=["mud", "sand", "rock", "unimproved"],
        max_speed_on_road_kmh=110,
        max_speed_off_road_kmh=25,
    ),
    "heavy_truck": VehicleProfile(
        name="Heavy Equipment Transporter",
        type="Heavy Logistics Vehicle",
        max_slope_degrees=20,
        ground_clearance_cm=30,
        weight_tons=35,
        max_ford_depth_cm=100,
        preferred_surfaces=["asphalt", "concrete"],
        avoid_surfaces=["dirt", "sand", "mud", "gravel_loose"],
        max_speed_on_road_kmh=80,
        max_speed_off_road_kmh=15,
    ),
}
