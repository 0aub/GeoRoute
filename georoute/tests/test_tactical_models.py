"""
Test tactical planning models and data structures.
"""

import json
from datetime import datetime

from ..models.tactical import (
    UnitType,
    TacticalUnit,
    RiskLevel,
    RouteVerdict,
    DetailedWaypoint,
    RouteSegment,
    RouteScores,
    SimulationResult,
    ClassificationResult,
    TacticalRoute,
    TacticalPlanRequest,
    TacticalPlanResponse,
    APICall,
    GeminiRequest,
    BacklogEntry,
)


def test_unit_types():
    """Test UnitType enum values."""
    print("\n=== Testing UnitType Enum ===")

    # Friendly units
    assert UnitType.RIFLEMAN.value == "rifleman"
    assert UnitType.SNIPER.value == "sniper"
    assert UnitType.HEAVY_WEAPONS.value == "heavy_weapons"
    assert UnitType.MEDIC.value == "medic"

    # Enemy units
    assert UnitType.SENTRY.value == "sentry"
    assert UnitType.PATROL.value == "patrol"
    assert UnitType.HEAVY_POSITION.value == "heavy_position"

    print("✓ All UnitType values correct")


def test_tactical_unit():
    """Test TacticalUnit model."""
    print("\n=== Testing TacticalUnit Model ===")

    # Friendly soldier
    soldier = TacticalUnit(
        lat=36.1069,
        lon=-112.1129,
        unit_type=UnitType.RIFLEMAN,
        is_friendly=True,
        unit_id="soldier-1"
    )

    assert soldier.lat == 36.1069
    assert soldier.lon == -112.1129
    assert soldier.unit_type == UnitType.RIFLEMAN
    assert soldier.is_friendly is True
    assert soldier.unit_id == "soldier-1"

    # Enemy sentry
    enemy = TacticalUnit(
        lat=36.1089,
        lon=-112.1149,
        unit_type=UnitType.SENTRY,
        is_friendly=False
    )

    assert enemy.is_friendly is False
    assert enemy.unit_id is None  # Optional field

    # Test serialization
    soldier_dict = soldier.model_dump()
    assert soldier_dict["unit_type"] == "rifleman"

    # Test deserialization
    soldier_2 = TacticalUnit.model_validate(soldier_dict)
    assert soldier_2.lat == soldier.lat

    print("✓ TacticalUnit model works correctly")


def test_risk_levels():
    """Test RiskLevel enum."""
    print("\n=== Testing RiskLevel Enum ===")

    assert RiskLevel.SAFE.value == "safe"
    assert RiskLevel.MODERATE.value == "moderate"
    assert RiskLevel.HIGH.value == "high"
    assert RiskLevel.CRITICAL.value == "critical"

    print("✓ All RiskLevel values correct")


def test_route_verdict():
    """Test RouteVerdict enum."""
    print("\n=== Testing RouteVerdict Enum ===")

    assert RouteVerdict.SUCCESS.value == "success"
    assert RouteVerdict.RISK.value == "risk"
    assert RouteVerdict.FAILED.value == "failed"

    print("✓ All RouteVerdict values correct")


def test_detailed_waypoint():
    """Test DetailedWaypoint model."""
    print("\n=== Testing DetailedWaypoint Model ===")

    waypoint = DetailedWaypoint(
        lat=36.1069,
        lon=-112.1129,
        elevation_m=1500.0,
        distance_from_start_m=250.0,
        terrain_type="forest",
        risk_level=RiskLevel.MODERATE,
        reasoning="200m from enemy patrol, partial tree cover",
        tactical_note="Good ambush position"
    )

    assert waypoint.lat == 36.1069
    assert waypoint.elevation_m == 1500.0
    assert waypoint.risk_level == RiskLevel.MODERATE
    assert "enemy patrol" in waypoint.reasoning

    # Test without optional tactical_note
    waypoint_2 = DetailedWaypoint(
        lat=36.1070,
        lon=-112.1130,
        elevation_m=1505.0,
        distance_from_start_m=275.0,
        terrain_type="open",
        risk_level=RiskLevel.HIGH,
        reasoning="Exposed position"
    )
    assert waypoint_2.tactical_note is None

    print("✓ DetailedWaypoint model works correctly")


def test_route_segment():
    """Test RouteSegment model."""
    print("\n=== Testing RouteSegment Model ===")

    segment = RouteSegment(
        segment_id=1,
        start_waypoint_idx=0,
        end_waypoint_idx=1,
        color="yellow",
        risk_level=RiskLevel.MODERATE,
        distance_m=150.0,
        estimated_time_seconds=100.0,
        risk_factors=["enemy patrol nearby", "partial cover"]
    )

    assert segment.color == "yellow"
    assert segment.risk_level == RiskLevel.MODERATE
    assert len(segment.risk_factors) == 2

    # Test color mapping
    colors = ["blue", "yellow", "orange", "red"]
    risks = [RiskLevel.SAFE, RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.CRITICAL]

    for color, risk in zip(colors, risks):
        seg = RouteSegment(
            segment_id=1,
            start_waypoint_idx=0,
            end_waypoint_idx=1,
            color=color,
            risk_level=risk,
            distance_m=100.0,
            estimated_time_seconds=66.7,
            risk_factors=[]
        )
        assert seg.color == color
        assert seg.risk_level == risk

    print("✓ RouteSegment model works correctly")


def test_route_scores():
    """Test RouteScores model."""
    print("\n=== Testing RouteScores Model ===")

    scores = RouteScores(
        time_to_target=75.0,
        stealth_score=60.0,
        survival_probability=80.0,
        overall_score=70.0
    )

    assert 0 <= scores.time_to_target <= 100
    assert 0 <= scores.stealth_score <= 100
    assert 0 <= scores.survival_probability <= 100
    assert 0 <= scores.overall_score <= 100

    # Test that overall_score is reasonable weighted average
    # Formula: time(20%) + stealth(40%) + survival(40%)
    expected = 75.0 * 0.2 + 60.0 * 0.4 + 80.0 * 0.4
    assert abs(scores.overall_score - expected) < 5.0  # Allow some variance

    print("✓ RouteScores model works correctly")


def test_simulation_result():
    """Test SimulationResult model."""
    print("\n=== Testing SimulationResult Model ===")

    simulation = SimulationResult(
        detected=False,
        detection_probability=0.15,
        detection_points=[(36.107, -112.113), (36.108, -112.114)],
        safe_percentage=85.0
    )

    assert simulation.detected is False
    assert 0 <= simulation.detection_probability <= 1
    assert len(simulation.detection_points) == 2
    assert 0 <= simulation.safe_percentage <= 100

    # If detected is True, detection_probability should be high
    simulation_detected = SimulationResult(
        detected=True,
        detection_probability=0.85,
        detection_points=[(36.107, -112.113)],
        safe_percentage=15.0
    )
    assert simulation_detected.detected is True
    assert simulation_detected.detection_probability > 0.5

    print("✓ SimulationResult model works correctly")


def test_classification_result():
    """Test ClassificationResult model."""
    print("\n=== Testing ClassificationResult Model ===")

    scores = RouteScores(
        time_to_target=75.0,
        stealth_score=60.0,
        survival_probability=80.0,
        overall_score=70.0
    )

    simulation = SimulationResult(
        detected=False,
        detection_probability=0.15,
        detection_points=[],
        safe_percentage=85.0
    )

    classification = ClassificationResult(
        gemini_evaluation=RouteVerdict.SUCCESS,
        gemini_reasoning="High survival probability, good cover, acceptable risk",
        scores=scores,
        simulation=simulation,
        final_verdict=RouteVerdict.SUCCESS,
        final_reasoning="Combined analysis shows success probability >70%",
        confidence=0.85
    )

    assert classification.gemini_evaluation == RouteVerdict.SUCCESS
    assert classification.final_verdict == RouteVerdict.SUCCESS
    assert 0 <= classification.confidence <= 1
    assert classification.scores.overall_score == 70.0

    # Test verdict logic consistency
    # If overall_score >= 70 and survival >= 75, should be SUCCESS
    assert scores.overall_score >= 70
    assert scores.survival_probability >= 75
    assert classification.final_verdict == RouteVerdict.SUCCESS

    print("✓ ClassificationResult model works correctly")


def test_tactical_route():
    """Test complete TacticalRoute model."""
    print("\n=== Testing TacticalRoute Model ===")

    # Create waypoints
    waypoints = [
        DetailedWaypoint(
            lat=36.1069 + i * 0.0002,
            lon=-112.1129 + i * 0.0002,
            elevation_m=1500.0 + i * 5,
            distance_from_start_m=i * 30.0,
            terrain_type="forest",
            risk_level=RiskLevel.MODERATE,
            reasoning=f"Waypoint {i}"
        )
        for i in range(5)
    ]

    # Create segments
    segments = [
        RouteSegment(
            segment_id=i,
            start_waypoint_idx=i,
            end_waypoint_idx=i + 1,
            color="yellow",
            risk_level=RiskLevel.MODERATE,
            distance_m=30.0,
            estimated_time_seconds=20.0,
            risk_factors=[]
        )
        for i in range(4)
    ]

    # Create scores and simulation
    scores = RouteScores(
        time_to_target=75.0,
        stealth_score=60.0,
        survival_probability=80.0,
        overall_score=70.0
    )

    simulation = SimulationResult(
        detected=False,
        detection_probability=0.15,
        detection_points=[],
        safe_percentage=85.0
    )

    classification = ClassificationResult(
        gemini_evaluation=RouteVerdict.SUCCESS,
        gemini_reasoning="Good route",
        scores=scores,
        simulation=simulation,
        final_verdict=RouteVerdict.SUCCESS,
        final_reasoning="Success expected",
        confidence=0.85
    )

    # Create complete route
    route = TacticalRoute(
        route_id=1,
        name="Flanking Approach",
        description="Circle around enemy position using forest cover",
        waypoints=waypoints,
        segments=segments,
        classification=classification,
        total_distance_m=120.0,
        estimated_duration_seconds=80.0
    )

    assert route.route_id == 1
    assert route.name == "Flanking Approach"
    assert len(route.waypoints) == 5
    assert len(route.segments) == 4
    assert route.total_distance_m == 120.0
    assert route.classification.final_verdict == RouteVerdict.SUCCESS

    # Test serialization
    route_dict = route.model_dump()
    assert route_dict["route_id"] == 1
    assert len(route_dict["waypoints"]) == 5

    # Test deserialization
    route_2 = TacticalRoute.model_validate(route_dict)
    assert route_2.name == route.name

    print("✓ TacticalRoute model works correctly")


def test_tactical_plan_request():
    """Test TacticalPlanRequest model."""
    print("\n=== Testing TacticalPlanRequest Model ===")

    soldiers = [
        TacticalUnit(
            lat=36.1069,
            lon=-112.1129,
            unit_type=UnitType.RIFLEMAN,
            is_friendly=True
        ),
        TacticalUnit(
            lat=36.1070,
            lon=-112.1130,
            unit_type=UnitType.SNIPER,
            is_friendly=True
        )
    ]

    enemies = [
        TacticalUnit(
            lat=36.1089,
            lon=-112.1149,
            unit_type=UnitType.SENTRY,
            is_friendly=False
        )
    ]

    bounds = {
        "north": 36.11,
        "south": 36.10,
        "east": -112.11,
        "west": -112.12
    }

    request = TacticalPlanRequest(
        soldiers=soldiers,
        enemies=enemies,
        bounds=bounds,
        zoom=14
    )

    assert len(request.soldiers) == 2
    assert len(request.enemies) == 1
    assert request.zoom == 14
    assert request.bounds["north"] == 36.11

    # Test without optional zoom
    request_2 = TacticalPlanRequest(
        soldiers=soldiers,
        enemies=enemies,
        bounds=bounds
    )
    assert request_2.zoom is None

    print("✓ TacticalPlanRequest model works correctly")


def test_tactical_plan_response():
    """Test TacticalPlanResponse model."""
    print("\n=== Testing TacticalPlanResponse Model ===")

    # Create minimal route for testing
    waypoint = DetailedWaypoint(
        lat=36.1069,
        lon=-112.1129,
        elevation_m=1500.0,
        distance_from_start_m=0.0,
        terrain_type="forest",
        risk_level=RiskLevel.SAFE,
        reasoning="Start position"
    )

    scores = RouteScores(
        time_to_target=75.0,
        stealth_score=60.0,
        survival_probability=80.0,
        overall_score=70.0
    )

    simulation = SimulationResult(
        detected=False,
        detection_probability=0.15,
        detection_points=[],
        safe_percentage=85.0
    )

    classification = ClassificationResult(
        gemini_evaluation=RouteVerdict.SUCCESS,
        gemini_reasoning="Good route",
        scores=scores,
        simulation=simulation,
        final_verdict=RouteVerdict.SUCCESS,
        final_reasoning="Success expected",
        confidence=0.85
    )

    route = TacticalRoute(
        route_id=1,
        name="Route 1",
        description="Test route",
        waypoints=[waypoint],
        segments=[],
        classification=classification,
        total_distance_m=100.0,
        estimated_duration_seconds=66.7
    )

    response = TacticalPlanResponse(
        request_id="test-123",
        routes=[route, route, route],  # 3 routes
        metadata={"test": "data", "zoom_level": 14}
    )

    assert response.request_id == "test-123"
    assert len(response.routes) == 3
    assert response.metadata["zoom_level"] == 14

    print("✓ TacticalPlanResponse model works correctly")


def test_api_call_logging():
    """Test APICall logging model."""
    print("\n=== Testing APICall Model ===")

    api_call = APICall(
        timestamp=datetime.utcnow(),
        service="google_maps",
        endpoint="elevation",
        request_params={"locations": [(36.1, -112.1)]},
        response_data={"elevations": [1500.0]}
    )

    assert api_call.service == "google_maps"
    assert api_call.endpoint == "elevation"
    assert "locations" in api_call.request_params

    print("✓ APICall model works correctly")


def test_gemini_request_logging():
    """Test GeminiRequest logging model."""
    print("\n=== Testing GeminiRequest Model ===")

    gemini_req = GeminiRequest(
        timestamp=datetime.utcnow(),
        stage="stage1_initial_routes",
        prompt="Generate 3 routes...",
        response='{"routes": []}',
        image_included=True
    )

    assert gemini_req.stage == "stage1_initial_routes"
    assert gemini_req.image_included is True
    assert "Generate" in gemini_req.prompt

    print("✓ GeminiRequest model works correctly")


def test_backlog_entry():
    """Test complete BacklogEntry model."""
    print("\n=== Testing BacklogEntry Model ===")

    # Create request
    request = TacticalPlanRequest(
        soldiers=[
            TacticalUnit(
                lat=36.1069,
                lon=-112.1129,
                unit_type=UnitType.RIFLEMAN,
                is_friendly=True
            )
        ],
        enemies=[
            TacticalUnit(
                lat=36.1089,
                lon=-112.1149,
                unit_type=UnitType.SENTRY,
                is_friendly=False
            )
        ],
        bounds={"north": 36.11, "south": 36.10, "east": -112.11, "west": -112.12}
    )

    # Create response
    waypoint = DetailedWaypoint(
        lat=36.1069,
        lon=-112.1129,
        elevation_m=1500.0,
        distance_from_start_m=0.0,
        terrain_type="forest",
        risk_level=RiskLevel.SAFE,
        reasoning="Start"
    )

    scores = RouteScores(
        time_to_target=75.0,
        stealth_score=60.0,
        survival_probability=80.0,
        overall_score=70.0
    )

    simulation = SimulationResult(
        detected=False,
        detection_probability=0.15,
        detection_points=[],
        safe_percentage=85.0
    )

    classification = ClassificationResult(
        gemini_evaluation=RouteVerdict.SUCCESS,
        gemini_reasoning="Good",
        scores=scores,
        simulation=simulation,
        final_verdict=RouteVerdict.SUCCESS,
        final_reasoning="Success",
        confidence=0.85
    )

    route = TacticalRoute(
        route_id=1,
        name="Route 1",
        description="Test",
        waypoints=[waypoint],
        segments=[],
        classification=classification,
        total_distance_m=100.0,
        estimated_duration_seconds=66.7
    )

    response = TacticalPlanResponse(
        request_id="test-123",
        routes=[route],
        metadata={}
    )

    # Create backlog entry
    backlog_entry = BacklogEntry(
        request_id="test-123",
        timestamp=datetime.utcnow(),
        user_input=request,
        api_calls=[
            APICall(
                timestamp=datetime.utcnow(),
                service="google_maps",
                endpoint="elevation",
                request_params={},
                response_data={}
            )
        ],
        gemini_pipeline=[
            GeminiRequest(
                timestamp=datetime.utcnow(),
                stage="stage1",
                prompt="test",
                response="test",
                image_included=False
            )
        ],
        satellite_image="base64_image_data",
        terrain_image="base64_terrain_data",
        result=response,
        total_duration_seconds=5.5
    )

    assert backlog_entry.request_id == "test-123"
    assert len(backlog_entry.api_calls) == 1
    assert len(backlog_entry.gemini_pipeline) == 1
    assert backlog_entry.satellite_image == "base64_image_data"
    assert backlog_entry.total_duration_seconds == 5.5

    # Test serialization to JSON
    entry_dict = backlog_entry.model_dump()
    json_str = json.dumps(entry_dict, default=str)  # default=str for datetime
    assert "test-123" in json_str

    print("✓ BacklogEntry model works correctly")


def run_all_tests():
    """Run all model tests."""
    print("\n" + "=" * 60)
    print("TACTICAL PLANNING MODELS - COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    test_unit_types()
    test_tactical_unit()
    test_risk_levels()
    test_route_verdict()
    test_detailed_waypoint()
    test_route_segment()
    test_route_scores()
    test_simulation_result()
    test_classification_result()
    test_tactical_route()
    test_tactical_plan_request()
    test_tactical_plan_response()
    test_api_call_logging()
    test_gemini_request_logging()
    test_backlog_entry()

    print("\n" + "=" * 60)
    print("✅ ALL MODEL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
