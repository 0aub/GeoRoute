"""
Tactical Gemini client with 4-stage sequential pipeline.
Each stage builds on previous data to prevent hallucination.

Model configuration is centralized in config.yaml
"""

import json
import base64
from typing import Optional
from datetime import datetime
import google.generativeai as genai

from ..config import get_yaml_setting
from ..models.tactical import (
    TacticalUnit,
    DetailedWaypoint,
    RouteSegment,
    RouteScores,
    SimulationResult,
    ClassificationResult,
    TacticalRoute,
    RiskLevel,
    RouteVerdict,
    GeminiRequest,
)


class TacticalGeminiClient:
    """
    4-stage sequential Gemini pipeline for tactical route planning.

    Stages:
    1. Generate 3 initial routes with basic waypoints
    2. Refine waypoints with detailed risk analysis (every 20-50m)
    3. Calculate scores (time/stealth/survival)
    4. Final classification (SUCCESS/RISK/FAILED)

    Model selection by complexity:
    - Stage 1-2 (visual/complex): gemini-2.5-flash (vision capable)
    - Stage 3-4 (text reasoning): gemini-2.5-flash-lite (fast, cost-effective)
    """

    def __init__(self, api_key: str = None, project_id: str = None, use_vertex: bool = False, location: str = "us-central1"):
        """
        Initialize the tactical Gemini client.

        Args:
            api_key: AI Studio API key (if not using Vertex)
            project_id: Google Cloud project ID
            use_vertex: If True, use Vertex AI with ADC auth
            location: Vertex AI region
        """
        self.use_vertex = use_vertex
        self.project_id = project_id

        if use_vertex:
            # Use Vertex AI - requires ADC or service account
            import vertexai
            from vertexai.generative_models import GenerativeModel
            vertexai.init(project=project_id, location=location)
            print(f"[GeminiTactical] Using Vertex AI (project={project_id}, location={location})")
        else:
            # Use AI Studio with API key
            genai.configure(api_key=api_key)
            print(f"[GeminiTactical] Using AI Studio API key")

        # Load text model from centralized config.yaml
        text_model_name = get_yaml_setting("gemini", "text_model")
        if not text_model_name:
            raise ValueError("Missing gemini.text_model in config.yaml")

        # Initialize the text model
        try:
            if use_vertex:
                from vertexai.generative_models import GenerativeModel
                self.text_model = GenerativeModel(text_model_name)
            else:
                self.text_model = genai.GenerativeModel(text_model_name)
            print(f"[GeminiTactical] Text model: {text_model_name}")
        except Exception as e:
            raise ValueError(f"Failed to initialize {text_model_name}: {e}")

        # All stages use the same model now
        self.model = self.text_model
        self.complex_model = self.text_model  # Alias for compatibility
        self.simple_model = self.text_model   # Alias for compatibility
        self.gemini_requests: list[GeminiRequest] = []

    def _log_request(
        self, stage: str, prompt: str, response: str, image_included: bool = False
    ):
        """Log Gemini request for backlog."""
        self.gemini_requests.append(
            GeminiRequest(
                timestamp=datetime.utcnow(),
                stage=stage,
                prompt=prompt,
                response=response,
                image_included=image_included,
            )
        )

    async def stage1_generate_initial_routes(
        self,
        soldiers: list[TacticalUnit],
        enemies: list[TacticalUnit],
        terrain_data: dict,
        satellite_image_base64: Optional[str] = None,
    ) -> dict:
        """
        Stage 1: Generate 3 initial tactical routes.

        Args:
            soldiers: List of friendly units
            enemies: List of enemy units
            terrain_data: Elevation and terrain type data
            satellite_image_base64: Optional satellite imagery

        Returns:
            Dict with 3 routes, each with basic waypoints
        """
        # Build prompt with strict constraints
        prompt = f"""You are a military tactical planner. Generate exactly 3 different attack routes from the soldier position to the target area.

SOLDIER POSITIONS:
{json.dumps([{"lat": s.lat, "lon": s.lon, "type": "friendly"} for s in soldiers], indent=2)}

ENEMY POSITIONS:
{json.dumps([{"lat": e.lat, "lon": e.lon, "type": "enemy"} for e in enemies], indent=2)}

TERRAIN DATA (USE ONLY THIS DATA - DO NOT INVENT):
{json.dumps(terrain_data, indent=2)}

REQUIREMENTS:
1. Generate EXACTLY 3 routes with different tactical approaches
2. Each route should have 5-10 basic waypoints
3. Use ONLY the terrain data provided above
4. Provide a name and description for each route
5. Consider enemy positions when planning routes

OUTPUT FORMAT (JSON only):
{{
  "routes": [
    {{
      "route_id": 1,
      "name": "Route name",
      "description": "Brief tactical description",
      "waypoints": [
        {{"lat": 0.0, "lon": 0.0, "terrain_type": "forest", "reasoning": "why this point"}},
        ...
      ]
    }},
    ...
  ]
}}

Return ONLY valid JSON, no markdown formatting."""

        # Prepare content with optional image
        content = [prompt]
        image_included = False

        if satellite_image_base64:
            try:
                image_data = base64.b64decode(satellite_image_base64)
                content.insert(0, {
                    "mime_type": "image/png",
                    "data": image_data
                })
                image_included = True
            except Exception:
                pass  # Continue without image if decode fails

        # Call Gemini (complex model for visual/reasoning tasks)
        response = await self.complex_model.generate_content_async(content)
        response_text = response.text.strip()

        # Clean markdown if present
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()

        # Log request
        self._log_request("stage1_initial_routes", prompt, response_text, image_included)

        # Parse JSON
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini returned invalid JSON: {e}\n{response_text}")

    async def stage2_refine_waypoints(
        self,
        stage1_routes: dict,
        detailed_elevation: dict,
        enemies: list[TacticalUnit],
        satellite_image_base64: Optional[str] = None,
    ) -> dict:
        """
        Stage 2: Assess risk at waypoints with line-of-sight analysis.

        Args:
            stage1_routes: Output from stage 1
            detailed_elevation: Detailed elevation data along routes
            enemies: Enemy positions for risk calculation
            satellite_image_base64: Optional satellite image for LOS analysis

        Returns:
            Dict with routes containing risk-assessed waypoints
        """
        prompt = f"""You are a tactical analyst assessing RISK for waypoints along routes.

IMPORTANT: Do NOT modify coordinates. ONLY assess tactical risk at each waypoint.

ROUTES WITH WAYPOINTS:
{json.dumps(stage1_routes, indent=2)}

ENEMY POSITIONS:
{json.dumps([{"lat": e.lat, "lon": e.lon, "type": "enemy"} for e in enemies], indent=2)}

CRITICAL - LINE OF SIGHT ASSESSMENT:
The most important factor is whether the ENEMY CAN SEE the friendly unit at each waypoint.
Consider these factors in ORDER of importance:

1. DIRECT LINE OF SIGHT - Can the enemy physically see this point?
   - If buildings, walls, or large structures block the view → SAFE even if close
   - If the approach angle means the enemy is facing away → SAFE
   - If terrain (hills, dunes) blocks visibility → SAFE

2. ANGLE OF APPROACH - Is the friendly unit in the enemy's field of view?
   - Approaching from behind or the side of enemy position → lower risk
   - Approaching from the front (enemy facing you) → higher risk

3. DISTANCE - Only matters if there IS line of sight:
   - >500m with clear LOS: moderate risk
   - 200-500m with clear LOS: high risk
   - <200m with clear LOS: critical risk
   - ANY distance without LOS: safe or moderate

4. COVER - Available concealment at the waypoint:
   - Buildings, walls, vegetation provide cover
   - Open areas (sand, flat terrain) are exposed

RISK LEVEL DETERMINATION (BE REALISTIC):
- safe: No line of sight to enemy (buildings/terrain blocking), OR >500m with cover
- moderate: Partial line of sight, or approaching from blind spot, 200-500m
- high: Clear line of sight, enemy facing direction, 100-200m
- critical: Direct line of sight, fully exposed, <100m, enemy alert

VERY IMPORTANT: If buildings or structures are between the waypoint and enemy,
the risk should be SAFE regardless of distance. Urban environments provide
natural cover even when close to enemies.

OUTPUT FORMAT (JSON only):
{{
  "routes": [
    {{
      "route_id": 1,
      "name": "Route name",
      "description": "Description",
      "waypoints": [
        {{
          "lat": <EXACT VALUE FROM INPUT>,
          "lon": <EXACT VALUE FROM INPUT>,
          "elevation_m": <from input or 0>,
          "distance_from_start_m": <from input or 0>,
          "terrain_type": "sand/urban/grass/etc",
          "risk_level": "safe/moderate/high/critical",
          "reasoning": "Explain LOS analysis: distance to enemy, what blocks view, approach angle",
          "tactical_note": "Brief tactical observation"
        }}
      ]
    }}
  ]
}}

Return ONLY valid JSON."""

        # Build content with optional satellite image for visual LOS analysis
        content = [prompt]
        image_included = False

        if satellite_image_base64:
            try:
                image_data = base64.b64decode(satellite_image_base64)
                # Add image first for visual context
                content.insert(0, {
                    "mime_type": "image/png",
                    "data": image_data
                })
                image_included = True
                print("[GeminiTactical] Stage 2: Using satellite image for LOS analysis")
            except Exception as e:
                print(f"[GeminiTactical] Stage 2: Could not use satellite image: {e}")

        # Use complex model for risk assessment (reasoning task with vision)
        response = await self.complex_model.generate_content_async(content)
        response_text = response.text.strip()

        # Clean markdown
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()

        self._log_request("stage2_refine_waypoints", prompt, response_text)

        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini returned invalid JSON: {e}\n{response_text}")

    async def stage3_score_routes(
        self,
        stage2_routes: dict,
        enemies: list[TacticalUnit],
    ) -> dict:
        """
        Stage 3: Calculate objective scores for each route.

        Args:
            stage2_routes: Output from stage 2 with detailed waypoints
            enemies: Enemy positions

        Returns:
            Dict with routes including scores (0-100 scale)
        """
        prompt = f"""You are scoring tactical routes objectively.

ROUTES WITH DETAILED WAYPOINTS:
{json.dumps(stage2_routes, indent=2)}

ENEMY POSITIONS:
{json.dumps([{"lat": e.lat, "lon": e.lon, "type": "enemy"} for e in enemies], indent=2)}

TASK:
For each route, calculate these scores (0-100 scale):

1. TIME_TO_TARGET (0-100):
   - 100 = shortest distance, optimal terrain
   - 0 = very long, difficult terrain

2. STEALTH_SCORE (0-100):
   - 100 = always >500m from enemies, excellent cover
   - 0 = exposed, close to enemies

3. SURVIVAL_PROBABILITY (0-100):
   - 100 = minimal risk throughout
   - 0 = high risk of casualties

4. OVERALL_SCORE (0-100):
   - Weighted average: time(20%) + stealth(40%) + survival(40%)

OUTPUT FORMAT (JSON only):
{{
  "routes": [
    {{
      "route_id": 1,
      "name": "Route name",
      "scores": {{
        "time_to_target": 75.0,
        "stealth_score": 60.0,
        "survival_probability": 80.0,
        "overall_score": 70.0,
        "score_reasoning": "Explain the scores"
      }}
    }},
    ...
  ]
}}

Return ONLY valid JSON."""

        # Use simple model for scoring (lighter text reasoning)
        response = await self.simple_model.generate_content_async(prompt)
        response_text = response.text.strip()

        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()

        self._log_request("stage3_score_routes", prompt, response_text)

        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini returned invalid JSON: {e}\n{response_text}")

    async def stage4_final_classification(
        self,
        stage3_routes: dict,
        stage2_routes: dict,
        enemies: list[TacticalUnit],
    ) -> dict:
        """
        Stage 4: Final classification with verdict.

        Args:
            stage3_routes: Output from stage 3 with scores
            stage2_routes: Output from stage 2 with detailed waypoints
            enemies: Enemy positions

        Returns:
            Dict with final classifications (SUCCESS/RISK/FAILED)
        """
        prompt = f"""You are making final tactical assessments.

ROUTES WITH SCORES:
{json.dumps(stage3_routes, indent=2)}

DETAILED WAYPOINT DATA:
{json.dumps(stage2_routes, indent=2)}

ENEMY POSITIONS:
{json.dumps([{"lat": e.lat, "lon": e.lon, "type": "enemy"} for e in enemies], indent=2)}

TASK:
For each route, provide a final classification:

VERDICT OPTIONS:
- "success": High probability of success (overall_score >= 70, survival >= 75)
- "risk": Moderate risk (overall_score 40-69, OR survival 50-74)
- "failed": High risk of failure (overall_score < 40, OR survival < 50)

Also simulate enemy detection:
- Calculate detection probability (0.0-1.0)
- Identify detection points along route
- Calculate safe percentage of route

OUTPUT FORMAT (JSON only):
{{
  "routes": [
    {{
      "route_id": 1,
      "name": "Route name",
      "classification": {{
        "gemini_evaluation": "success",
        "gemini_reasoning": "Detailed reasoning for verdict",
        "final_verdict": "success",
        "final_reasoning": "Combined reasoning from all stages",
        "confidence": 0.85,
        "simulation": {{
          "detected": false,
          "detection_probability": 0.15,
          "detection_points": [],
          "safe_percentage": 85.0
        }}
      }}
    }},
    ...
  ]
}}

Return ONLY valid JSON."""

        # Use simple model for classification (lighter text reasoning)
        response = await self.simple_model.generate_content_async(prompt)
        response_text = response.text.strip()

        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()

        self._log_request("stage4_final_classification", prompt, response_text)

        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini returned invalid JSON: {e}\n{response_text}")

    def get_gemini_requests(self) -> list[GeminiRequest]:
        """Get all Gemini requests for backlog."""
        return self.gemini_requests

    def clear_requests(self):
        """Clear request log (for new planning session)."""
        self.gemini_requests = []
