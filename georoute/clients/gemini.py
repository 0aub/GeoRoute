"""
Gemini API client for route planning with terrain awareness.

Model configuration is centralized in config.yaml
"""

import json
from typing import Optional
from google import genai
from google.genai import types

from ..models.routing import RoutingDecision
from ..config import get_yaml_setting


class GeminiRoutePlanner:
    """
    Gemini-powered route planning with terrain awareness.

    FREE TIER: Google AI Studio provides free access.
    """

    SYSTEM_INSTRUCTION = """You are an expert military terrain analyst and route planner.
Your task is to analyze satellite imagery combined with structured geospatial data to plan optimal routes.

CRITICAL RULES:
1. ALWAYS trust the provided elevation/slope data over visual estimates from the image
2. The structured JSON contains ground-truth terrain measurements - use them
3. The satellite image shows current conditions (obstacles, flooding, construction) - use it for verification
4. Never route through slopes exceeding the vehicle's maximum capability
5. Prefer established roads when available, but assess off-road alternatives
6. Consider all hazards: water crossings, cliffs, dense vegetation, urban areas

When analyzing:
- Cross-reference visual features with elevation data
- Identify discrepancies between image and data (recent changes, errors)
- Be conservative - when uncertain, assume worse conditions
- Provide confidence scores reflecting data quality and visibility

Your output must follow the exact JSON schema provided."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Gemini API key is required")
        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key)
        # Load model name from centralized config - no fallbacks
        self.model_name = get_yaml_setting("gemini", "complex_model")
        if not self.model_name:
            raise ValueError("Missing gemini.complex_model in config.yaml")
        print(f"[GeminiRoutePlanner] Using model: {self.model_name}")

    async def test_connection(self) -> bool:
        """Test API connectivity."""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Say 'OK' if you can hear me.",
                config=types.GenerateContentConfig(max_output_tokens=10),
            )
            return bool(response.text)
        except Exception:
            return False

    def plan_route(
        self,
        satellite_image: bytes,
        terrain_image: Optional[bytes],
        geospatial_data: dict,
        start_point: tuple[float, float],
        end_point: tuple[float, float],
        vehicle_profile: dict,
        additional_constraints: dict = None,
    ) -> RoutingDecision:
        """
        Generate optimal route using Gemini multimodal analysis.

        Args:
            satellite_image: JPEG bytes of satellite imagery
            terrain_image: Optional terrain map showing contours
            geospatial_data: Structured terrain data (elevation, slopes, roads)
            start_point: (lat, lon) origin
            end_point: (lat, lon) destination
            vehicle_profile: Vehicle capabilities and constraints
            additional_constraints: No-go zones, time limits, etc.

        Returns:
            RoutingDecision with complete route plan
        """
        # Build the complete context
        mission_context = {
            "mission": {
                "start": {"lat": start_point[0], "lon": start_point[1]},
                "end": {"lat": end_point[0], "lon": end_point[1]},
                "objective": "Plan optimal route considering terrain constraints",
            },
            "terrain_data": geospatial_data,
            "vehicle": vehicle_profile,
            "constraints": additional_constraints or {},
        }

        # Build prompt
        prompt = f"""
<mission_briefing>
Plan a route from ({start_point[0]:.6f}, {start_point[1]:.6f}) to ({end_point[0]:.6f}, {end_point[1]:.6f}).

Vehicle: {vehicle_profile.get('name', 'Military vehicle')}
- Maximum traversable slope: {vehicle_profile.get('max_slope_degrees', 30)}°
- Ground clearance: {vehicle_profile.get('ground_clearance_cm', 30)} cm
- Weight: {vehicle_profile.get('weight_tons', 10)} tons
- Can ford water depth: {vehicle_profile.get('max_ford_depth_cm', 50)} cm
- Preferred surfaces: {', '.join(vehicle_profile.get('preferred_surfaces', ['paved', 'gravel']))}
</mission_briefing>

<geospatial_data>
{json.dumps(mission_context, indent=2)}
</geospatial_data>

<analysis_instructions>
1. Analyze the satellite image for current ground conditions
2. Cross-reference with the structured elevation and slope data
3. Identify the optimal route respecting all constraints
4. Mark waypoints every 1-2 km with terrain assessments
5. Identify all hazards visible in imagery or implied by terrain data
6. Calculate realistic time estimates based on terrain difficulty
7. Suggest alternatives if the primary route has significant risks
</analysis_instructions>

<output_instructions>
Provide a complete routing decision in JSON format.
Be thorough but realistic. Include all waypoints, hazards, and reasoning.
Your confidence score should reflect actual data quality - lower if visibility is poor or data seems incomplete.
</output_instructions>
"""

        # Build content parts
        content_parts = []

        # Add satellite image
        content_parts.append(
            types.Part.from_bytes(data=satellite_image, mime_type="image/jpeg")
        )

        # Add terrain image if provided
        if terrain_image:
            content_parts.append(
                types.Part.from_bytes(data=terrain_image, mime_type="image/jpeg")
            )

        # Add text prompt
        content_parts.append(prompt)

        # Generate response
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=content_parts,
            config=types.GenerateContentConfig(
                system_instruction=self.SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=RoutingDecision,
                temperature=0.2,  # Low for consistent, deterministic output
                max_output_tokens=8192,
            ),
        )

        # Parse response
        return RoutingDecision.model_validate_json(response.text)

    def analyze_terrain_only(
        self, satellite_image: bytes, bounds: tuple[float, float, float, float]
    ) -> dict:
        """
        Analyze terrain from satellite image only (quick assessment).
        Useful for initial reconnaissance before detailed planning.
        """
        prompt = f"""
Analyze this satellite image covering the area from
({bounds[0]:.4f}, {bounds[2]:.4f}) to ({bounds[1]:.4f}, {bounds[3]:.4f}).

Identify and describe:
1. Terrain types visible (mountains, valleys, plains, etc.)
2. Apparent elevation variations
3. Road/path networks
4. Water bodies
5. Vegetation density
6. Urban/built areas
7. Potential obstacles for vehicle movement
8. Overall traversability assessment

Provide a structured JSON response with these fields:
- terrain_types: list of identified terrain types with approximate percentages
- elevation_assessment: description of elevation variations
- road_network: description of visible roads/paths
- water_bodies: list of water features
- vegetation: description of vegetation coverage
- urban_areas: description of built-up areas
- obstacles: list of potential obstacles
- overall_traversability: one of "easy", "moderate", "difficult", "very_difficult"
- confidence: 0-1 confidence in this assessment
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[
                types.Part.from_bytes(data=satellite_image, mime_type="image/jpeg"),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", temperature=0.3
            ),
        )

        return json.loads(response.text)
