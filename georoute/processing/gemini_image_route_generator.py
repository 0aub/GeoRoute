"""
Gemini 3 Pro Image Route Generator.

Uses Gemini's native image generation to draw tactical routes directly
on satellite imagery. The AI visually understands terrain and draws
the optimal path - no waypoint extraction needed.

Configuration is loaded from config.yaml - modify prompts there.
"""

import base64
import io
import re
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


@dataclass
class RouteEvaluationResult:
    """Result from Gemini route evaluation."""
    annotated_image_base64: str  # Image with tactical positions marked
    success: bool
    positions: list  # List of suggested positions
    segment_analysis: list  # Analysis of each route segment
    overall_assessment: str
    adjusted_bounds: Optional[dict] = None
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
        # Note: response_modalities must include both TEXT and IMAGE
        response = self.client.models.generate_content(
            model=self.image_model,
            contents=[prompt, marked_image],
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE'],
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

    def _draw_user_route(
        self,
        image_base64: str,
        waypoints: list,
        bounds: dict
    ) -> Tuple[Image.Image, dict]:
        """
        Draw user's route on satellite image as a dashed blue line.

        Args:
            image_base64: Base64-encoded satellite image
            waypoints: List of {lat, lng} waypoints
            bounds: Geographic bounds of the image

        Returns:
            (image_with_route, bounds)
        """
        import json

        # Decode image
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        width, height = image.size
        draw = ImageDraw.Draw(image)

        print(f"[GeminiImageRoute] Drawing user route with {len(waypoints)} waypoints")

        def gps_to_pixel(lat: float, lng: float) -> tuple[int, int]:
            """Convert GPS to pixel coordinates using bounds."""
            px = int((lng - bounds["west"]) / (bounds["east"] - bounds["west"]) * width)
            py = int((bounds["north"] - lat) / (bounds["north"] - bounds["south"]) * height)
            return (max(0, min(width-1, px)), max(0, min(height-1, py)))

        # Convert waypoints to pixel coordinates
        pixels = []
        for wp in waypoints:
            lat = wp.get('lat') or wp.get('latitude')
            lng = wp.get('lng') or wp.get('longitude') or wp.get('lon')
            px = gps_to_pixel(lat, lng)
            pixels.append(px)

        # Draw route as dashed blue line
        route_color = (0, 150, 255)  # Bright blue
        line_width = max(3, int(width / 200))  # Scale with image size
        dash_length = max(10, int(width / 50))

        for i in range(len(pixels) - 1):
            start = pixels[i]
            end = pixels[i + 1]

            # Draw dashed line between points
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            distance = (dx**2 + dy**2) ** 0.5

            if distance > 0:
                # Calculate number of dashes
                num_dashes = int(distance / (dash_length * 2)) + 1
                for j in range(num_dashes):
                    # Start and end of each dash
                    t1 = (j * 2 * dash_length) / distance
                    t2 = ((j * 2 + 1) * dash_length) / distance
                    if t1 > 1:
                        break
                    t2 = min(t2, 1)

                    dash_start = (int(start[0] + dx * t1), int(start[1] + dy * t1))
                    dash_end = (int(start[0] + dx * t2), int(start[1] + dy * t2))

                    draw.line([dash_start, dash_end], fill=route_color, width=line_width)

        # Draw waypoint markers (small circles)
        marker_radius = max(4, int(width / 150))
        for i, px in enumerate(pixels):
            # First point = blue, last point = red, middle = white
            if i == 0:
                color = (0, 100, 255)  # Blue start
            elif i == len(pixels) - 1:
                color = (255, 50, 50)  # Red end
            else:
                color = (255, 255, 255)  # White waypoint

            draw.ellipse(
                [px[0] - marker_radius, px[1] - marker_radius,
                 px[0] + marker_radius, px[1] + marker_radius],
                fill=color,
                outline=(255, 255, 255),
                width=2
            )

        print(f"[GeminiImageRoute] Route drawn with {len(pixels)} points")
        return image, bounds

    async def evaluate_user_route(
        self,
        satellite_image_base64: str,
        waypoints: list,
        units: dict,
        bounds: dict
    ) -> RouteEvaluationResult:
        """
        Evaluate a user-drawn route and suggest tactical positions.

        Args:
            satellite_image_base64: Base64-encoded satellite image
            waypoints: List of {lat, lng} waypoints defining the route
            units: Unit composition {squad_size, riflemen, snipers, support, medics}
            bounds: Geographic bounds of the image

        Returns:
            RouteEvaluationResult with annotated image and analysis
        """
        import json
        import re

        print(f"[GeminiImageRoute] Evaluating user route with {len(waypoints)} waypoints")
        print(f"[GeminiImageRoute] Unit composition: {units}")

        # Draw user's route on the satellite image
        marked_image, adjusted_bounds = self._draw_user_route(
            satellite_image_base64,
            waypoints,
            bounds
        )

        # Get evaluation prompt from config and fill in unit details
        prompt_template = get_yaml_setting("route_evaluation_prompt", default="""
Analyze this satellite image showing a user-planned route (BLUE DASHED LINE).
Mark tactical positions on the image and provide analysis.
""")

        prompt = prompt_template.format(
            squad_size=units.get('squad_size', 4),
            riflemen=units.get('riflemen', 2),
            snipers=units.get('snipers', 1),
            support=units.get('support', 0),
            medics=units.get('medics', 1)
        )

        print(f"[GeminiImageRoute] Sending route for evaluation...")

        # Call Gemini image model for route evaluation
        response = self.client.models.generate_content(
            model=self.image_model,
            contents=[prompt, marked_image],
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE'],
                temperature=0.2,  # Slight variation for position suggestions
                candidate_count=1,
            )
        )

        print(f"[GeminiImageRoute] Evaluation response received, parsing...")

        # Extract image and text from response
        annotated_image_data = None
        response_text = ""

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                annotated_image_data = part.inline_data.data
                print(f"[GeminiImageRoute] Got annotated image: {len(annotated_image_data)} bytes")
            elif hasattr(part, 'text') and part.text:
                response_text += part.text

        if annotated_image_data is None:
            error_msg = "Gemini did not return an annotated image"
            print(f"[GeminiImageRoute] ERROR: {error_msg}")
            raise RuntimeError(error_msg)

        # Encode annotated image to base64
        annotated_image = Image.open(io.BytesIO(annotated_image_data))
        buffer = io.BytesIO()
        annotated_image.save(buffer, format='PNG', optimize=False)
        annotated_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        # Parse JSON analysis from response text
        positions = []
        segment_analysis = []
        overall_assessment = "Route evaluation complete."

        try:
            # Find JSON in response text
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                analysis = json.loads(json_match.group())

                # Extract positions
                if 'positions' in analysis:
                    for pos in analysis['positions']:
                        positions.append({
                            'position_type': pos.get('type', 'cover'),
                            'description': pos.get('description', ''),
                            'for_unit': pos.get('for_unit'),
                            'icon': self._get_position_icon(pos.get('type', 'cover'))
                        })

                # Extract segment analysis
                if 'segments' in analysis:
                    for i, seg in enumerate(analysis['segments']):
                        segment_analysis.append({
                            'segment_index': seg.get('index', i),
                            'risk_level': seg.get('risk', 'medium'),
                            'description': seg.get('description', ''),
                            'suggestions': seg.get('suggestions', [])
                        })

                # Extract overall assessment
                if 'overall' in analysis:
                    overall_assessment = analysis['overall']

                print(f"[GeminiImageRoute] Parsed {len(positions)} positions, {len(segment_analysis)} segments")

        except json.JSONDecodeError as e:
            print(f"[GeminiImageRoute] Could not parse JSON analysis: {e}")
            overall_assessment = response_text[:500] if response_text else "Route evaluation complete."

        print(f"[GeminiImageRoute] Route evaluation complete")

        return RouteEvaluationResult(
            annotated_image_base64=annotated_image_base64,
            success=True,
            positions=positions,
            segment_analysis=segment_analysis,
            overall_assessment=overall_assessment,
            adjusted_bounds=adjusted_bounds
        )

    async def analyze_tactical_simulation(
        self,
        annotated_image_base64: str,
        prompt: str
    ) -> dict:
        """
        Analyze a tactical simulation using Gemini 3 Flash.

        Args:
            annotated_image_base64: Pre-annotated image with vision cones and route
            prompt: Analysis prompt with context

        Returns:
            Dictionary with analysis results including weak spots and recommendations
        """
        import json as json_lib

        # Decode image for Gemini
        image_data = base64.b64decode(annotated_image_base64)
        image = Image.open(io.BytesIO(image_data))

        print(f"[GeminiImageRoute] Analyzing tactical simulation with Gemini 3 Flash...")

        # Get analysis model from config
        analysis_model = get_yaml_setting("gemini", "analysis_model", default="gemini-3-flash-preview")

        try:
            # Use Gemini 3 Flash for tactical analysis with vision
            # Only request TEXT - no image generation (not available in all regions)
            response = self.client.models.generate_content(
                model=analysis_model,
                contents=[prompt, image],
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT'],
                    temperature=0.3,
                    candidate_count=1,
                )
            )

            print(f"[GeminiImageRoute] Simulation analysis response received")

            # Extract image and text from response
            result_image_data = None
            response_text = ""

            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    result_image_data = part.inline_data.data
                    print(f"[GeminiImageRoute] Got annotated result image: {len(result_image_data)} bytes")
                elif hasattr(part, 'text') and part.text:
                    response_text += part.text

            # Process result image if Gemini annotated it
            result_image_base64 = annotated_image_base64  # Default to input
            if result_image_data:
                result_image = Image.open(io.BytesIO(result_image_data))
                buffer = io.BytesIO()
                result_image.save(buffer, format='PNG', optimize=False)
                result_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # Parse JSON analysis from response text
            result = {
                'annotated_image': result_image_base64,
                'strategy_rating': 5.0,
                'verdict': None,
                'tactical_scores': None,
                'flanking_analysis': None,
                'segment_cover_analysis': [],
                'cover_breakdown': None,
                'weak_spots': [],
                'strong_points': [],
                'exposure_analysis': [],
                'terrain_assessment': '',
                'overall_assessment': 'Analysis complete.',
                'recommendations': []
            }

            try:
                # Find JSON in response text
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    analysis = json_lib.loads(json_match.group())

                    # Log what Gemini actually returned
                    print(f"[GeminiImageRoute] Gemini returned keys: {list(analysis.keys())}")

                    # Extract ALL fields from Gemini response
                    result['strategy_rating'] = float(analysis.get('strategy_rating', 5.0))
                    result['verdict'] = analysis.get('verdict')
                    result['tactical_scores'] = analysis.get('tactical_scores')
                    result['flanking_analysis'] = analysis.get('flanking_analysis')
                    result['segment_cover_analysis'] = analysis.get('segment_cover_analysis', [])
                    result['cover_breakdown'] = analysis.get('cover_breakdown')
                    result['weak_spots'] = analysis.get('weak_spots', [])
                    result['strong_points'] = analysis.get('strong_points', [])
                    result['exposure_analysis'] = analysis.get('exposure_analysis', [])
                    result['terrain_assessment'] = analysis.get('terrain_assessment', '')
                    result['overall_assessment'] = analysis.get('overall_assessment', 'Analysis complete.')
                    result['recommendations'] = analysis.get('recommendations', [])

                    # Log detailed parsing results
                    print(f"[GeminiImageRoute] Parsed: rating={result['strategy_rating']}, verdict={result['verdict']}")
                    print(f"[GeminiImageRoute] tactical_scores present: {result['tactical_scores'] is not None}")
                    print(f"[GeminiImageRoute] flanking_analysis present: {result['flanking_analysis'] is not None}")
                    print(f"[GeminiImageRoute] segment_cover_analysis count: {len(result['segment_cover_analysis'])}")
                    print(f"[GeminiImageRoute] cover_breakdown present: {result['cover_breakdown'] is not None}")
                    print(f"[GeminiImageRoute] weak_spots: {len(result['weak_spots'])}, strong_points: {len(result['strong_points'])}")
                else:
                    print(f"[GeminiImageRoute] No JSON found in response. Response text (first 500 chars): {response_text[:500]}")

            except json_lib.JSONDecodeError as e:
                print(f"[GeminiImageRoute] Could not parse JSON analysis: {e}")
                print(f"[GeminiImageRoute] Raw response (first 500 chars): {response_text[:500]}")
                # Use response text as assessment if JSON parsing fails
                if response_text:
                    result['overall_assessment'] = response_text[:1000]

            return result

        except Exception as e:
            print(f"[GeminiImageRoute] Tactical simulation analysis failed: {e}")
            # Return basic result with error
            return {
                'annotated_image': annotated_image_base64,
                'strategy_rating': 5.0,
                'weak_spots': [],
                'exposure_analysis': [],
                'overall_assessment': f'Analysis encountered an issue: {str(e)}',
                'recommendations': ['Review the route manually', 'Consider alternative approaches']
            }

    def _get_position_icon(self, position_type: str) -> str:
        """Get icon name for position type."""
        icons = {
            'overwatch': 'crosshair',
            'cover': 'shield',
            'rally': 'flag',
            'danger': 'alert-triangle',
            'medic': 'plus-circle'
        }
        return icons.get(position_type, 'map-pin')
