"""
Gemini 3 Pro Image Route Generator.

Uses Gemini's native image generation to draw tactical routes directly
on satellite imagery. The AI visually understands terrain and draws
the optimal path - no waypoint extraction needed.

Configuration is loaded from config.yaml - modify prompts there.
"""

import base64
import io
from typing import Optional, Tuple
from dataclasses import dataclass
from PIL import Image, ImageDraw

from google import genai
from google.genai import types

from ..config import get_yaml_setting


@dataclass
class RouteGenerationResult:
    """Result from Gemini image route generation."""
    route_image_base64: str  # Image with route drawn
    success: bool
    adjusted_bounds: Optional[dict] = None  # Bounds after watermark cropping
    error_message: Optional[str] = None


class GeminiImageRouteGenerator:
    """
    Generates tactical routes using Gemini 3 Pro Image.

    Gemini draws the route directly on the satellite image.
    The output is the image itself - no waypoints needed.
    """

    def __init__(self, api_key: str):
        """
        Initialize the Gemini Image Route Generator.

        Args:
            api_key: Google AI API key
        """
        self.client = genai.Client(api_key=api_key)
        # Separate models for different tasks
        self.image_model = get_yaml_setting("gemini", "image_model", default="gemini-3-pro-image-preview")
        self.text_model = get_yaml_setting("gemini", "text_model", default="gemini-2.5-flash")
        print(f"[GeminiImageRoute] Image model: {self.image_model}")
        print(f"[GeminiImageRoute] Text model: {self.text_model}")

    def _crop_watermarks(
        self,
        image: Image.Image,
        bounds: dict
    ) -> Tuple[Image.Image, dict]:
        """
        Crop Google Maps watermarks from the satellite image.

        Removes:
        - Left edge: "Google" text (~80 pixels at scale=2)
        - Bottom edge: Attribution text (~100 pixels at scale=2)

        Returns cropped image and adjusted bounds.
        """
        width, height = image.size

        # Crop amounts (pixels to remove)
        left_crop = 80   # "Google" text
        bottom_crop = 100  # "(c) 2026 Airbus..." attribution

        # Crop the image: left, upper, right, lower
        cropped = image.crop((left_crop, 0, width, height - bottom_crop))
        new_width, new_height = cropped.size

        # Adjust bounds to reflect the cropped area
        # The cropped image now represents a smaller geographic area
        lon_per_pixel = (bounds["east"] - bounds["west"]) / width
        lat_per_pixel = (bounds["north"] - bounds["south"]) / height

        adjusted_bounds = {
            "west": bounds["west"] + left_crop * lon_per_pixel,  # Shift west edge right
            "east": bounds["east"],  # East edge unchanged
            "north": bounds["north"],  # North edge unchanged
            "south": bounds["south"] + bottom_crop * lat_per_pixel  # Shift south edge up
        }

        print(f"[GeminiImageRoute] Cropped watermarks: {width}x{height} -> {new_width}x{new_height}")
        print(f"[GeminiImageRoute] Adjusted bounds: W={adjusted_bounds['west']:.6f}, E={adjusted_bounds['east']:.6f}, N={adjusted_bounds['north']:.6f}, S={adjusted_bounds['south']:.6f}")

        return cropped, adjusted_bounds

    def _add_markers_to_image(
        self,
        image_base64: str,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        bounds: dict
    ) -> Tuple[Image.Image, Tuple[int, int], dict]:
        """
        Add small start/end markers to satellite image for Gemini to see.
        Upscales image to ensure high quality output from Gemini.
        Returns: (marked_image, original_size, bounds)
        """
        # Decode image
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        original_size = image.size
        width, height = original_size
        print(f"[GeminiImageRoute] Image size: {width}x{height}")

        draw = ImageDraw.Draw(image)

        def gps_to_pixel(lat: float, lon: float) -> tuple[int, int]:
            """Convert GPS to pixel coordinates using bounds."""
            px = int((lon - bounds["west"]) / (bounds["east"] - bounds["west"]) * width)
            py = int((bounds["north"] - lat) / (bounds["north"] - bounds["south"]) * height)
            return (max(0, min(width-1, px)), max(0, min(height-1, py)))

        # Get marker settings from config - scale with image size
        base_marker_size = get_yaml_setting("markers", "size", default=12)
        # Scale marker size based on image dimensions (larger image = larger markers)
        scale_factor = max(width, height) / 640  # Base scale for 640px image
        marker_size = int(base_marker_size * scale_factor)
        outline_width_scaled = max(2, int(get_yaml_setting("markers", "outline_width", default=2) * scale_factor))

        start_color = tuple(get_yaml_setting("markers", "start_color", default=[0, 100, 255]))
        end_color = tuple(get_yaml_setting("markers", "end_color", default=[255, 50, 50]))
        outline_color = tuple(get_yaml_setting("markers", "outline_color", default=[255, 255, 255]))
        outline_width = outline_width_scaled

        # Start marker - blue filled circle
        start_px = gps_to_pixel(start_lat, start_lon)
        draw.ellipse(
            [start_px[0]-marker_size, start_px[1]-marker_size,
             start_px[0]+marker_size, start_px[1]+marker_size],
            fill=start_color,
            outline=outline_color,
            width=outline_width
        )
        print(f"[GeminiImageRoute] START marker at pixel ({start_px[0]}, {start_px[1]})")

        # End marker - red filled circle
        end_px = gps_to_pixel(end_lat, end_lon)
        draw.ellipse(
            [end_px[0]-marker_size, end_px[1]-marker_size,
             end_px[0]+marker_size, end_px[1]+marker_size],
            fill=end_color,
            outline=outline_color,
            width=outline_width
        )
        print(f"[GeminiImageRoute] END marker at pixel ({end_px[0]}, {end_px[1]})")

        return image, original_size, bounds

    async def generate_route(
        self,
        satellite_image_base64: str,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        bounds: dict
    ) -> RouteGenerationResult:
        """
        Generate tactical routes using Gemini 3 Pro Image.

        Adds small markers to image, sends to Gemini with strict edit prompt.
        """
        print(f"[GeminiImageRoute] Generating route from ({start_lat:.6f}, {start_lon:.6f}) to ({end_lat:.6f}, {end_lon:.6f})")

        # Add markers to image for Gemini to see
        marked_image, original_size, adjusted_bounds = self._add_markers_to_image(
            satellite_image_base64,
            start_lat, start_lon,
            end_lat, end_lon,
            bounds
        )

        # Get route generation prompt from config
        prompt = get_yaml_setting("route_prompt", default="""
CRITICAL: This is an IMAGE EDITING task. Preserve the EXACT satellite image.
BLUE circle = Start, RED circle = Target.
Draw TWO dashed route lines: ORANGE (balanced) and GREEN (stealth).
Routes go around buildings, use cover. NO text labels.
""")

        print(f"[GeminiImageRoute] Sending to Gemini...")

        # Call Gemini image model for route drawing
        # Use low temperature for more deterministic/consistent output
        response = self.client.models.generate_content(
            model=self.image_model,
            contents=[prompt, marked_image],
            config=types.GenerateContentConfig(
                response_modalities=['Image'],
                temperature=0,  # Zero temperature = most deterministic
                candidate_count=1,
            )
        )

        print(f"[GeminiImageRoute] Response received, parsing...")

        # Find the image in response
        route_image_data = None
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                route_image_data = part.inline_data.data
                print(f"[GeminiImageRoute] Got image: {len(route_image_data)} bytes")
                break

        if route_image_data is None:
            error_msg = "Gemini did not return an image"
            print(f"[GeminiImageRoute] ERROR: {error_msg}")
            raise RuntimeError(error_msg)

        # Load the returned image - keep full resolution for quality
        returned_image = Image.open(io.BytesIO(route_image_data))
        returned_size = returned_image.size
        print(f"[GeminiImageRoute] Returned image size: {returned_size[0]}x{returned_size[1]} (input was: {original_size[0]}x{original_size[1]})")

        # DO NOT resize - keep Gemini's output at full resolution
        # The Leaflet ImageOverlay will scale it to fit the bounds
        # This preserves maximum quality

        # Encode to base64 - PNG for lossless quality
        buffer = io.BytesIO()
        returned_image.save(buffer, format='PNG', optimize=False)
        route_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        print(f"[GeminiImageRoute] Success - route image generated ({len(route_image_base64)} bytes base64)")

        return RouteGenerationResult(
            route_image_base64=route_image_base64,
            success=True,
            adjusted_bounds=adjusted_bounds
        )

    async def analyze_tactical_situation(
        self,
        route_image_base64: str,
        num_soldiers: int,
        num_enemies: int
    ) -> dict:
        """
        Generate detailed tactical analysis report using Gemini.

        This is called when advanced_analytics is enabled.
        Analyzes the route image and provides detailed tactical recommendations.
        """
        print(f"[GeminiImageRoute] Generating advanced tactical analysis...")

        # Decode image for Gemini
        image_data = base64.b64decode(route_image_base64)
        image = Image.open(io.BytesIO(image_data))

        prompt = f"""Analyze this tactical situation satellite image showing infantry approach routes.

Context:
- Friendly forces: {num_soldiers} units (at BLUE marker)
- Enemy position: {num_enemies} units (at RED marker)
- Two routes are drawn: ORANGE (balanced/medium risk), GREEN (stealth/safest)

Provide a detailed tactical analysis report in JSON format:
{{
    "recommended_approach": {{
        "route": "green",
        "reasoning": "Detailed explanation of why this route is recommended"
    }},
    "timing_suggestions": {{
        "optimal_time": "dawn/dusk/night/day",
        "reasoning": "Why this timing is optimal",
        "weather_notes": "Any weather considerations visible"
    }},
    "equipment_recommendations": [
        {{"item": "Equipment name", "reason": "Why needed"}}
    ],
    "flanking_opportunities": [
        {{"location": "Description of location", "approach": "How to execute", "risk_level": "low/medium/high"}}
    ],
    "cover_positions": [
        {{"type": "building/vegetation/terrain", "description": "Location description", "use": "Rally point/observation/fallback"}}
    ],
    "risk_zones": [
        {{"location": "Description", "threat_type": "Open exposure/enemy sightline/chokepoint", "mitigation": "How to reduce risk"}}
    ],
    "enemy_analysis": {{
        "likely_fields_of_fire": "Description of enemy sight lines",
        "blind_spots": "Areas enemy cannot easily observe",
        "weakness": "Tactical weakness to exploit"
    }},
    "mission_summary": "2-3 sentence tactical summary"
}}

Be specific and actionable based on what you can see in the satellite imagery."""

        try:
            # Use text model for tactical analysis report
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=[prompt, image],
                config=types.GenerateContentConfig(
                    response_modalities=['Text']
                )
            )

            response_text = response.text.strip()

            # Clean markdown if present
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()

            import json
            report = json.loads(response_text)
            print(f"[GeminiImageRoute] Advanced tactical analysis complete")
            return report

        except Exception as e:
            print(f"[GeminiImageRoute] Advanced analysis failed: {e}")
            # Return None - don't show fake data
            return None
