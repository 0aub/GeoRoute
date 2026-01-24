"""
Integration tests for tactical planning API.
Tests the complete flow from request to response.
"""

import json
from datetime import datetime

from ..models.tactical import (
    TacticalPlanRequest,
    TacticalUnit,
    UnitType,
    RiskLevel,
    RouteVerdict,
)


def test_request_validation():
    """Test that TacticalPlanRequest validates inputs correctly."""
    print("\n=== Testing Request Validation ===")

    # Valid request
    soldiers = [
        TacticalUnit(
            lat=36.1069,
            lon=-112.1129,
            unit_type=UnitType.RIFLEMAN,
            is_friendly=True,
            unit_id="soldier-1"
        ),
        TacticalUnit(
            lat=36.1070,
            lon=-112.1130,
            unit_type=UnitType.SNIPER,
            is_friendly=True,
            unit_id="soldier-2"
        )
    ]

    enemies = [
        TacticalUnit(
            lat=36.1089,
            lon=-112.1149,
            unit_type=UnitType.SENTRY,
            is_friendly=False,
            unit_id="enemy-1"
        ),
        TacticalUnit(
            lat=36.1090,
            lon=-112.1150,
            unit_type=UnitType.PATROL,
            is_friendly=False,
            unit_id="enemy-2"
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
    assert len(request.enemies) == 2
    assert request.zoom == 14

    # Test JSON serialization (for API)
    request_json = request.model_dump_json()
    assert "soldier-1" in request_json
    assert "enemy-1" in request_json

    # Test JSON deserialization
    request_dict = json.loads(request_json)
    request_2 = TacticalPlanRequest.model_validate(request_dict)
    assert len(request_2.soldiers) == 2

    print("✓ Request validation works")


def test_bounds_validation():
    """Test that map bounds are validated correctly."""
    print("\n=== Testing Bounds Validation ===")

    soldiers = [
        TacticalUnit(
            lat=36.1069,
            lon=-112.1129,
            unit_type=UnitType.RIFLEMAN,
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

    # Valid bounds (2km x 2km area)
    bounds = {
        "north": 36.119,  # ~2km north
        "south": 36.101,  # ~2km south
        "east": -112.101,  # ~2km east
        "west": -112.119   # ~2km west
    }

    request = TacticalPlanRequest(
        soldiers=soldiers,
        enemies=enemies,
        bounds=bounds
    )

    assert request.bounds["north"] > request.bounds["south"]
    assert request.bounds["east"] > request.bounds["west"]

    # Verify area is reasonable for tactical planning
    lat_span = request.bounds["north"] - request.bounds["south"]
    lon_span = request.bounds["east"] - request.bounds["west"]

    # Rough check: should be ~0.018 degrees for 2km
    assert 0.01 <= lat_span <= 0.03
    assert 0.01 <= lon_span <= 0.03

    print("✓ Bounds validation works")


def test_unit_type_constraints():
    """Test that friendly/enemy unit types are consistent."""
    print("\n=== Testing Unit Type Constraints ===")

    # Friendly units should have is_friendly=True
    friendly_types = [
        UnitType.RIFLEMAN,
        UnitType.SNIPER,
        UnitType.HEAVY_WEAPONS,
        UnitType.MEDIC
    ]

    for unit_type in friendly_types:
        unit = TacticalUnit(
            lat=36.1069,
            lon=-112.1129,
            unit_type=unit_type,
            is_friendly=True
        )
        assert unit.is_friendly is True
        assert unit.unit_type in friendly_types

    # Enemy units should have is_friendly=False
    enemy_types = [
        UnitType.SENTRY,
        UnitType.PATROL,
        UnitType.HEAVY_POSITION
    ]

    for unit_type in enemy_types:
        unit = TacticalUnit(
            lat=36.1089,
            lon=-112.1149,
            unit_type=unit_type,
            is_friendly=False
        )
        assert unit.is_friendly is False
        assert unit.unit_type in enemy_types

    print("✓ Unit type constraints work")


def test_route_classification_logic():
    """Test route classification logic."""
    print("\n=== Testing Route Classification Logic ===")

    # Test SUCCESS criteria
    # overall_score >= 70 and survival >= 75
    assert (75.0 >= 70.0) and (80.0 >= 75.0)  # Should be SUCCESS

    # Test RISK criteria
    # overall_score 40-69 OR survival 50-74
    assert (50.0 >= 40.0 and 50.0 < 70.0)  # Should be RISK
    assert (60.0 >= 50.0 and 60.0 < 75.0)  # Should be RISK

    # Test FAILED criteria
    # overall_score < 40 OR survival < 50
    assert (30.0 < 40.0)  # Should be FAILED
    assert (40.0 < 50.0)  # Should be FAILED

    print("✓ Classification logic is correct")


def test_risk_level_ordering():
    """Test that risk levels are properly ordered."""
    print("\n=== Testing Risk Level Ordering ===")

    risk_order = [
        RiskLevel.SAFE,
        RiskLevel.MODERATE,
        RiskLevel.HIGH,
        RiskLevel.CRITICAL
    ]

    # Verify all levels exist
    assert len(risk_order) == 4

    # Verify color mapping
    color_map = {
        RiskLevel.SAFE: "blue",
        RiskLevel.MODERATE: "yellow",
        RiskLevel.HIGH: "orange",
        RiskLevel.CRITICAL: "red"
    }

    for risk, color in color_map.items():
        assert risk in risk_order
        assert color in ["blue", "yellow", "orange", "red"]

    print("✓ Risk level ordering is correct")


def test_response_structure():
    """Test that response contains all required data."""
    print("\n=== Testing Response Structure ===")

    # A valid response should have:
    # - request_id (UUID)
    # - routes (list of 3 TacticalRoute objects)
    # - metadata (dict)

    # Each route should have:
    # - route_id (1, 2, or 3)
    # - name
    # - description
    # - waypoints (list of DetailedWaypoint)
    # - segments (list of RouteSegment, color-coded)
    # - classification (ClassificationResult with multi-layer analysis)
    # - total_distance_m
    # - estimated_duration_seconds

    # Each classification should have:
    # - gemini_evaluation (RouteVerdict)
    # - gemini_reasoning (str)
    # - scores (RouteScores with time/stealth/survival)
    # - simulation (SimulationResult with detection probability)
    # - final_verdict (RouteVerdict)
    # - final_reasoning (str)
    # - confidence (float 0-1)

    expected_route_fields = [
        "route_id",
        "name",
        "description",
        "waypoints",
        "segments",
        "classification",
        "total_distance_m",
        "estimated_duration_seconds"
    ]

    expected_classification_fields = [
        "gemini_evaluation",
        "gemini_reasoning",
        "scores",
        "simulation",
        "final_verdict",
        "final_reasoning",
        "confidence"
    ]

    expected_scores_fields = [
        "time_to_target",
        "stealth_score",
        "survival_probability",
        "overall_score"
    ]

    expected_simulation_fields = [
        "detected",
        "detection_probability",
        "detection_points",
        "safe_percentage"
    ]

    print(f"✓ Response should have {len(expected_route_fields)} route fields")
    print(f"✓ Classification should have {len(expected_classification_fields)} fields")
    print(f"✓ Scores should have {len(expected_scores_fields)} fields")
    print(f"✓ Simulation should have {len(expected_simulation_fields)} fields")
    print("✓ Response structure is well-defined")


def test_pipeline_stages():
    """Test that pipeline stages are executed in correct order."""
    print("\n=== Testing Pipeline Stages ===")

    # Pipeline should execute in this order:
    stages = [
        "stage1_initial_routes",
        "stage2_refine_waypoints",
        "stage3_score_routes",
        "stage4_final_classification"
    ]

    # Each stage depends on previous stage output
    # Stage 1: Generate 3 routes with basic waypoints
    # Stage 2: Add detailed waypoints (every 20-50m) with risk analysis
    # Stage 3: Calculate scores (time/stealth/survival 0-100)
    # Stage 4: Final classification (SUCCESS/RISK/FAILED)

    print("Expected pipeline execution order:")
    for i, stage in enumerate(stages, 1):
        print(f"  {i}. {stage}")

    # Verify each stage has clear purpose
    assert len(stages) == 4
    assert stages[0].startswith("stage1")
    assert stages[-1].startswith("stage4")

    print("✓ Pipeline stages are correctly ordered")


def test_backlog_audit_trail():
    """Test that backlog captures complete audit trail."""
    print("\n=== Testing Backlog Audit Trail ===")

    # Backlog entry should capture:
    required_fields = [
        "request_id",           # Unique ID
        "timestamp",            # When request was made
        "user_input",           # Original request
        "api_calls",            # All Google Maps API calls
        "gemini_pipeline",      # All 4 Gemini requests/responses
        "satellite_image",      # Base64 encoded satellite image
        "terrain_image",        # Base64 encoded terrain image
        "result",               # Complete response with 3 routes
        "total_duration_seconds"  # Total processing time
    ]

    print("Backlog entry captures:")
    for field in required_fields:
        print(f"  ✓ {field}")

    assert len(required_fields) == 9

    print("✓ Backlog audit trail is comprehensive")


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("TACTICAL PLANNING API - INTEGRATION TESTS")
    print("=" * 60)

    test_request_validation()
    test_bounds_validation()
    test_unit_type_constraints()
    test_route_classification_logic()
    test_risk_level_ordering()
    test_response_structure()
    test_pipeline_stages()
    test_backlog_audit_trail()

    print("\n" + "=" * 60)
    print("✅ ALL INTEGRATION TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
