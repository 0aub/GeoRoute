"""
Gemini Vision-based Obstacle Detection.

Uses Gemini's vision capabilities to detect buildings and obstacles
from satellite imagery. This is a practical alternative to SAM/U-Net
when GPU resources are limited.

The approach:
1. Send satellite image to Gemini Vision
2. Ask it to identify obstacle regions with grid-based coordinates
3. Convert response to binary obstacle mask
4. Use mask for A* pathfinding

Accuracy: ~70-80% (lower than SAM's 91%, but routes will avoid buildings)
Speed: 2-5 seconds per image
Cost: Standard Gemini API pricing
"""

import numpy as np
import base64
import json
from typing import Tuple, Optional
from dataclasses import dataclass
import google.generativeai as genai

from ..config import get_yaml_setting


@dataclass
class ObstacleDetectionResult:
    """Result of Gemini-based obstacle detection."""
    obstacle_mask: np.ndarray  # Binary mask: 1 = obstacle, 0 = traversable
    buffered_mask: np.ndarray  # Mask with buffer zones
    obstacle_count: int  # Number of detected obstacles
    confidence: float  # Overall confidence score
    grid_size: Tuple[int, int]  # (height, width) of the grid
    detection_notes: str  # Gemini's analysis notes


class GeminiObstacleDetector:
    """
    Detects obstacles using Gemini Vision on satellite imagery.

    This provides building/obstacle detection without requiring:
    - Local GPU for SAM/U-Net
    - OSMnx queries (which can explode for large areas)

    Trade-off: Slightly lower accuracy (~70-80%) but practical and fast.
    Routes will successfully avoid detected buildings with generous buffers.
    """

    def __init__(
        self,
        api_key: str,
        buffer_pixels: int = 3,
        grid_size: int = 32
    ):
        """
        Initialize the Gemini-based obstacle detector.

        Args:
            api_key: Gemini API key
            buffer_pixels: Buffer around obstacles (default 3 = ~60m at 20m/pixel)
            grid_size: Grid resolution for obstacle detection (default 32x32)
        """
        genai.configure(api_key=api_key)

        # Use complex model for vision tasks
        model_name = get_yaml_setting("gemini", "complex_model")
        try:
            self.model = genai.GenerativeModel(model_name)
            print(f"[GeminiObstacle] Using model: {model_name}")
        except Exception as e:
            raise ValueError(f"Failed to initialize Gemini model: {e}")

        self.buffer_pixels = buffer_pixels
        self.grid_size = grid_size

    async def plan_route_directly(
        self,
        satellite_image_base64: str,
        bounds: dict,
        start_gps: Tuple[float, float],
        end_gps: Tuple[float, float]
    ) -> list:
        """
        NEW APPROACH: Have Gemini directly plan the route by identifying waypoints.

        Instead of detecting obstacles and running A*, we ask Gemini to:
        1. Look at the satellite image with markers drawn on it
        2. Identify the street network
        3. Return waypoints that follow streets from start to end

        Returns:
            List of (lat, lon) waypoints along streets
        """
        print(f"[GeminiObstacle] DIRECT ROUTE PLANNING - asking Gemini to find street path...")

        try:
            image_data = base64.b64decode(satellite_image_base64)
        except Exception as e:
            print(f"[GeminiObstacle] Image decode failed: {e}")
            return [start_gps, end_gps]

        # Calculate pixel positions of start and end
        img_size = 640  # Google Maps image size
        start_pixel_x = int((start_gps[1] - bounds["west"]) / (bounds["east"] - bounds["west"]) * img_size)
        start_pixel_y = int((bounds["north"] - start_gps[0]) / (bounds["north"] - bounds["south"]) * img_size)
        end_pixel_x = int((end_gps[1] - bounds["west"]) / (bounds["east"] - bounds["west"]) * img_size)
        end_pixel_y = int((bounds["north"] - end_gps[0]) / (bounds["north"] - bounds["south"]) * img_size)

        # Clamp to valid image bounds
        start_pixel_x = max(10, min(img_size - 10, start_pixel_x))
        start_pixel_y = max(10, min(img_size - 10, start_pixel_y))
        end_pixel_x = max(10, min(img_size - 10, end_pixel_x))
        end_pixel_y = max(10, min(img_size - 10, end_pixel_y))

        print(f"[GeminiObstacle] Start pixel: ({start_pixel_x}, {start_pixel_y})")
        print(f"[GeminiObstacle] End pixel: ({end_pixel_x}, {end_pixel_y})")

        # Draw markers on the image so Gemini can see them
        try:
            from PIL import Image, ImageDraw
            import io

            # Load the satellite image
            img = Image.open(io.BytesIO(image_data))
            draw = ImageDraw.Draw(img)

            # Draw START marker (blue circle with "S")
            marker_radius = 15
            draw.ellipse(
                [start_pixel_x - marker_radius, start_pixel_y - marker_radius,
                 start_pixel_x + marker_radius, start_pixel_y + marker_radius],
                fill=(0, 100, 255), outline=(255, 255, 255), width=3
            )

            # Draw END marker (red circle with "E")
            draw.ellipse(
                [end_pixel_x - marker_radius, end_pixel_y - marker_radius,
                 end_pixel_x + marker_radius, end_pixel_y + marker_radius],
                fill=(255, 50, 50), outline=(255, 255, 255), width=3
            )

            # Convert back to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            image_data = img_buffer.getvalue()

            print(f"[GeminiObstacle] Drew markers on image at START({start_pixel_x},{start_pixel_y}) END({end_pixel_x},{end_pixel_y})")

        except Exception as e:
            print(f"[GeminiObstacle] Failed to draw markers: {e}")
            # Continue with original image

        prompt = f"""Satellite image (640x640 pixels) with two markers:
- BLUE circle = START position
- RED circle = END position

TASK: Plan a route from the BLUE marker to the RED marker that follows STREETS.

CRITICAL RULES:
1. Route must stay on STREETS (the dark gray road surfaces with lane markings)
2. NEVER cross through buildings (the lighter colored rectangular structures)
3. Use INTERSECTIONS to change direction
4. Include a waypoint at EVERY turn

Look at the image - trace a path along the visible streets from blue to red.

Output JSON only with pixel coordinates:
{{"waypoints":[{{"x":100,"y":50}},{{"x":100,"y":150}},{{"x":200,"y":150}},{{"x":200,"y":300}}]}}

x=0 is left edge, y=0 is top edge. Return 4-8 waypoints."""

        try:
            content = [{"mime_type": "image/png", "data": image_data}, prompt]
            response = await self.model.generate_content_async(content)
            response_text = response.text.strip()

            # Clean markdown
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)
            waypoints_px = result.get("waypoints", [])

            print(f"[GeminiObstacle] Got {len(waypoints_px)} waypoints from Gemini")

            # Convert pixel coordinates to GPS
            waypoints_gps = []
            for wp in waypoints_px:
                px_x = wp.get("x", 0)
                px_y = wp.get("y", 0)

                # Clamp to image bounds
                px_x = max(0, min(img_size - 1, px_x))
                px_y = max(0, min(img_size - 1, px_y))

                # Convert to GPS
                lon = bounds["west"] + (px_x / img_size) * (bounds["east"] - bounds["west"])
                lat = bounds["north"] - (px_y / img_size) * (bounds["north"] - bounds["south"])
                waypoints_gps.append((lat, lon))

            # Ensure start and end are exact
            if waypoints_gps:
                waypoints_gps[0] = start_gps
                waypoints_gps[-1] = end_gps
            else:
                waypoints_gps = [start_gps, end_gps]

            print(f"[GeminiObstacle] Converted to GPS: {len(waypoints_gps)} waypoints")
            return waypoints_gps

        except Exception as e:
            print(f"[GeminiObstacle] Direct route planning failed: {e}")
            return [start_gps, end_gps]

    async def detect_obstacles(
        self,
        satellite_image_base64: str,
        bounds: dict,
        context: Optional[str] = None
    ) -> ObstacleDetectionResult:
        """
        Detect obstacles using PARALLEL Gemini calls for higher accuracy.

        Makes two simultaneous calls:
        1. Detect BUILDINGS (obstacles)
        2. Detect TRAVERSABLE paths (streets, alleys)

        Combines results: traversable = marked_traversable AND NOT marked_building

        Args:
            satellite_image_base64: Base64-encoded satellite image
            bounds: Geographic bounds {"north", "south", "east", "west"}
            context: Optional context about the area

        Returns:
            ObstacleDetectionResult with combined obstacle mask
        """
        import asyncio

        print(f"[GeminiObstacle] PARALLEL detection in {self.grid_size}x{self.grid_size} grid...")

        # Prepare image data
        try:
            image_data = base64.b64decode(satellite_image_base64)
        except Exception as e:
            print(f"[GeminiObstacle] Image decode failed: {e}")
            return self._create_empty_result()

        # Build prompts for parallel detection
        buildings_prompt = self._build_buildings_prompt()
        traversable_prompt = self._build_traversable_prompt()

        # Make parallel Gemini calls
        async def call_gemini(prompt: str, task_name: str) -> dict:
            try:
                content = [{"mime_type": "image/png", "data": image_data}, prompt]
                response = await self.model.generate_content_async(content)
                response_text = response.text.strip()

                # Clean markdown
                if response_text.startswith("```json"):
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif response_text.startswith("```"):
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                result = json.loads(response_text)
                print(f"[GeminiObstacle] {task_name}: Got {len(result.get('cells', []))} cells")
                return result
            except Exception as e:
                print(f"[GeminiObstacle] {task_name} failed: {e}")
                return {"cells": []}

        # Run both detections in parallel
        buildings_task = call_gemini(buildings_prompt, "BUILDINGS")
        traversable_task = call_gemini(traversable_prompt, "TRAVERSABLE")

        buildings_result, traversable_result = await asyncio.gather(
            buildings_task, traversable_task
        )

        # Combine results into obstacle mask
        return self._combine_detection_results(buildings_result, traversable_result)

    def _build_buildings_prompt(self) -> str:
        """Prompt to detect building rooftops (obstacles)."""
        return f"""Satellite image analysis. Divide into {self.grid_size}x{self.grid_size} grid.

TASK: Mark every cell containing ANY building, structure, or rooftop.

DETECT BY SHAPE (not color - buildings may match sand color):
- RECTANGULAR/SQUARE shapes with SHARP 90-degree corners
- SHADOWS next to structures (dark lines on one side)
- REGULAR geometric patterns (AC units, windows, roof features)
- ENCLOSED courtyards (rectangular empty spaces surrounded by structure)
- Walls/fences creating STRAIGHT LINES

ALSO MARK AS OBSTACLES:
- Parking lots (rectangular areas with small car shapes)
- Construction sites (irregular disturbed areas)
- Walled compounds (enclosed by straight lines)

KEY: Look for GEOMETRIC SHAPES and SHADOWS, not colors.
BE AGGRESSIVE. If you see sharp rectangular edges, it's a building.

Output JSON only:
{{"cells":[{{"row":0,"col":5}},{{"row":1,"col":5}}]}}

row 0=top, col 0=left."""

    def _build_traversable_prompt(self) -> str:
        """Prompt to detect traversable paths (streets, alleys)."""
        return f"""Satellite image analysis. Divide into {self.grid_size}x{self.grid_size} grid.

TASK: Mark ONLY cells that are part of ROADS or STREETS.

DETECT STREETS BY SHAPE (not color - roads may match sand color):
- LONG NARROW LINEAR paths (length >> width)
- VEHICLES visible (small rectangular shapes in a line)
- LANE MARKINGS or road edges (parallel lines)
- SHADOWS from adjacent buildings create clear road edges
- Roads form a CONNECTED NETWORK (they connect to other roads)

STREET PATTERN:
- Streets run BETWEEN buildings, not through them
- Streets have PARALLEL edges (buildings on both sides)
- At INTERSECTIONS, multiple streets meet at right angles

DO NOT MARK:
- Open desert/sand (no clear edges, no vehicles)
- Parking lots (wide areas, not linear)
- Building courtyards (enclosed by structures)
- Anything without clear LINEAR shape

TRACE COMPLETE STREETS from edge to edge. Mark ALL cells along each street.

Output JSON only:
{{"cells":[{{"row":2,"col":0}},{{"row":2,"col":1}},{{"row":2,"col":2}},{{"row":2,"col":3}}]}}

row 0=top, col 0=left."""

    def _combine_detection_results(
        self,
        buildings_result: dict,
        traversable_result: dict
    ) -> ObstacleDetectionResult:
        """Combine parallel detection results into final obstacle mask.

        Logic: A cell is traversable ONLY if:
        - It IS marked as traversable, AND
        - It is NOT marked as a building

        This gives us high confidence in what's actually passable.
        """
        # Initialize: everything is obstacle by default
        obstacle_mask = np.ones((self.grid_size, self.grid_size), dtype=np.uint8)

        # Get cell lists
        building_cells = set()
        for cell in buildings_result.get("cells", []):
            row, col = cell.get("row", -1), cell.get("col", -1)
            if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
                building_cells.add((row, col))

        traversable_cells = set()
        for cell in traversable_result.get("cells", []):
            row, col = cell.get("row", -1), cell.get("col", -1)
            if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
                traversable_cells.add((row, col))

        # A cell is traversable if marked traversable AND NOT marked as building
        confirmed_traversable = traversable_cells - building_cells

        # Stats
        total_cells = self.grid_size * self.grid_size
        overlap_cells = building_cells & traversable_cells  # Cells marked as both

        print(f"[GeminiObstacle] ═══════════════════════════════════════════════")
        print(f"[GeminiObstacle] DETECTION RESULTS ({self.grid_size}x{self.grid_size} grid = {total_cells} cells)")
        print(f"[GeminiObstacle] ───────────────────────────────────────────────")
        print(f"[GeminiObstacle] BUILDINGS detected: {len(building_cells)} cells ({100*len(building_cells)/total_cells:.1f}%)")
        print(f"[GeminiObstacle] TRAVERSABLE detected: {len(traversable_cells)} cells ({100*len(traversable_cells)/total_cells:.1f}%)")
        print(f"[GeminiObstacle] OVERLAP (both): {len(overlap_cells)} cells (removed from traversable)")

        # SAFEGUARD: If no traversable cells found, detection likely failed
        # Fall back to using traversable cells directly (ignore building detection)
        if len(confirmed_traversable) == 0 and len(traversable_cells) > 0:
            print(f"[GeminiObstacle] WARNING: All traversable cells overlap with buildings!")
            print(f"[GeminiObstacle] FALLBACK: Using traversable cells without building filter")
            confirmed_traversable = traversable_cells

        # SAFEGUARD 2: If still no traversable, make everything traversable
        if len(confirmed_traversable) == 0:
            print(f"[GeminiObstacle] WARNING: No traversable cells detected at all!")
            print(f"[GeminiObstacle] FALLBACK: Marking all non-building cells as traversable")
            # Mark everything except detected buildings as traversable
            all_cells = set((r, c) for r in range(self.grid_size) for c in range(self.grid_size))
            confirmed_traversable = all_cells - building_cells

        # Mark confirmed traversable cells as clear (0)
        for row, col in confirmed_traversable:
            obstacle_mask[row, col] = 0

        obstacle_count = self.grid_size * self.grid_size - len(confirmed_traversable)

        print(f"[GeminiObstacle] ───────────────────────────────────────────────")
        print(f"[GeminiObstacle] FINAL traversable: {len(confirmed_traversable)} cells ({100*len(confirmed_traversable)/total_cells:.1f}%)")
        print(f"[GeminiObstacle] FINAL obstacles: {obstacle_count} cells ({100*obstacle_count/total_cells:.1f}%)")
        print(f"[GeminiObstacle] ═══════════════════════════════════════════════")

        # Apply buffer if configured
        buffered_mask = self._apply_buffer(obstacle_mask)

        # Store detection details for UI visualization
        self._last_detection_details = {
            "building_cells": [{"row": r, "col": c} for r, c in building_cells],
            "traversable_cells": [{"row": r, "col": c} for r, c in traversable_cells],
            "confirmed_traversable": [{"row": r, "col": c} for r, c in confirmed_traversable],
            "grid_size": self.grid_size
        }

        return ObstacleDetectionResult(
            obstacle_mask=obstacle_mask,
            buffered_mask=buffered_mask,
            obstacle_count=obstacle_count,
            confidence=0.8,
            grid_size=(self.grid_size, self.grid_size),
            detection_notes=f"Parallel detection: {len(building_cells)} buildings, {len(confirmed_traversable)} traversable"
        )

    def get_last_detection_details(self) -> dict:
        """Get detailed detection info for UI visualization."""
        return getattr(self, '_last_detection_details', {})

    def _build_detection_prompt(
        self,
        bounds: dict,
        context: Optional[str]
    ) -> str:
        """Legacy prompt - kept for backwards compatibility."""
        return self._build_traversable_prompt()

    def _process_detection_result(self, result: dict) -> ObstacleDetectionResult:
        """Process Gemini's detection result into obstacle masks.

        Uses INVERSE detection: Gemini returns traversable cells, everything else is obstacle.
        """
        # Initialize grid as ALL OBSTACLES (1 = obstacle)
        obstacle_mask = np.ones((self.grid_size, self.grid_size), dtype=np.uint8)

        # Check for both old format (obstacles) and new format (traversable)
        traversable = result.get("traversable", [])
        old_obstacles = result.get("obstacles", [])

        if traversable:
            # NEW FORMAT: Mark traversable cells as clear (0)
            traversable_count = 0
            for cell in traversable:
                row = cell.get("row", 0)
                col = cell.get("col", 0)

                if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
                    obstacle_mask[row, col] = 0  # Mark as traversable
                    traversable_count += 1

            obstacle_count = (self.grid_size * self.grid_size) - traversable_count
            print(f"[GeminiObstacle] INVERSE: {traversable_count} traversable cells, {obstacle_count} obstacle cells")
        elif old_obstacles:
            # OLD FORMAT: Backwards compatibility - mark obstacles as blocked (1)
            obstacle_mask = np.zeros((self.grid_size, self.grid_size), dtype=np.uint8)
            obstacle_count = 0
            for obs in old_obstacles:
                row = obs.get("row", 0)
                col = obs.get("col", 0)

                if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
                    obstacle_mask[row, col] = 1
                    obstacle_count += 1

            print(f"[GeminiObstacle] OLD FORMAT: Detected {obstacle_count} obstacle cells")
        else:
            # No data - assume all traversable (empty obstacles)
            obstacle_mask = np.zeros((self.grid_size, self.grid_size), dtype=np.uint8)
            obstacle_count = 0
            print(f"[GeminiObstacle] No detection data - using empty mask")

        # Create buffered mask (dilate obstacles)
        buffered_mask = self._apply_buffer(obstacle_mask)

        buffered_count = np.sum(buffered_mask)
        total_cells = self.grid_size * self.grid_size

        print(f"[GeminiObstacle] Obstacle coverage: {100*obstacle_count/total_cells:.1f}%")
        print(f"[GeminiObstacle] Buffered coverage: {100*buffered_count/total_cells:.1f}%")

        return ObstacleDetectionResult(
            obstacle_mask=obstacle_mask,
            buffered_mask=buffered_mask,
            obstacle_count=obstacle_count,
            confidence=result.get("overall_confidence", 0.7),
            grid_size=(self.grid_size, self.grid_size),
            detection_notes=result.get("analysis_notes", "")
        )

    def _apply_buffer(self, mask: np.ndarray) -> np.ndarray:
        """Apply buffer around obstacles using dilation."""
        if self.buffer_pixels == 0:
            return mask.copy()

        # Simple dilation using numpy (no scipy dependency)
        buffered = mask.copy()

        for _ in range(self.buffer_pixels):
            new_buffered = buffered.copy()

            # Expand each obstacle cell to neighbors
            for row in range(self.grid_size):
                for col in range(self.grid_size):
                    if buffered[row, col] == 1:
                        # Mark neighbors
                        for dr in [-1, 0, 1]:
                            for dc in [-1, 0, 1]:
                                nr, nc = row + dr, col + dc
                                if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                                    new_buffered[nr, nc] = 1

            buffered = new_buffered

        return buffered

    def _create_empty_result(self) -> ObstacleDetectionResult:
        """Create empty result when detection fails."""
        empty_mask = np.zeros((self.grid_size, self.grid_size), dtype=np.uint8)

        return ObstacleDetectionResult(
            obstacle_mask=empty_mask,
            buffered_mask=empty_mask,
            obstacle_count=0,
            confidence=0.0,
            grid_size=(self.grid_size, self.grid_size),
            detection_notes="Detection failed - using empty mask"
        )

    def grid_to_gps(
        self,
        row: int,
        col: int,
        bounds: dict
    ) -> Tuple[float, float]:
        """Convert grid coordinates to GPS (lat, lon)."""
        # Row 0 is at north (top), row max is at south (bottom)
        lat = bounds["north"] - (row / self.grid_size) * (bounds["north"] - bounds["south"])
        # Col 0 is at west (left), col max is at east (right)
        lon = bounds["west"] + (col / self.grid_size) * (bounds["east"] - bounds["west"])

        return (lat, lon)

    def gps_to_grid(
        self,
        lat: float,
        lon: float,
        bounds: dict
    ) -> Tuple[int, int]:
        """Convert GPS coordinates to grid (row, col)."""
        # Clamp to bounds
        lat = max(bounds["south"], min(bounds["north"], lat))
        lon = max(bounds["west"], min(bounds["east"], lon))

        # Convert to grid coordinates
        row = int((bounds["north"] - lat) / (bounds["north"] - bounds["south"]) * self.grid_size)
        col = int((lon - bounds["west"]) / (bounds["east"] - bounds["west"]) * self.grid_size)

        # Clamp to valid range
        row = max(0, min(self.grid_size - 1, row))
        col = max(0, min(self.grid_size - 1, col))

        return (row, col)
