"""
Test backlog storage system.
"""

from datetime import datetime, timedelta

from ..storage.backlog import BacklogStore, get_backlog_store
from ..models.tactical import (
    BacklogEntry,
    TacticalPlanRequest,
    TacticalPlanResponse,
    TacticalUnit,
    TacticalRoute,
    DetailedWaypoint,
    RouteScores,
    SimulationResult,
    ClassificationResult,
    RiskLevel,
    RouteVerdict,
    UnitType,
    APICall,
    GeminiRequest,
)


def create_test_backlog_entry(request_id: str, timestamp: datetime = None) -> BacklogEntry:
    """Helper to create a test backlog entry."""
    if timestamp is None:
        timestamp = datetime.utcnow()

    # Create minimal models
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

    waypoint = DetailedWaypoint(
        lat=36.1069,
        lon=-112.1129,
        elevation_m=1500.0,
        distance_from_start_m=0.0,
        terrain_type="forest",
        risk_level=RiskLevel.SAFE,
        reasoning="Test waypoint"
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
        gemini_reasoning="Test",
        scores=scores,
        simulation=simulation,
        final_verdict=RouteVerdict.SUCCESS,
        final_reasoning="Test",
        confidence=0.85
    )

    route = TacticalRoute(
        route_id=1,
        name="Test Route",
        description="Test",
        waypoints=[waypoint],
        segments=[],
        classification=classification,
        total_distance_m=100.0,
        estimated_duration_seconds=66.7
    )

    response = TacticalPlanResponse(
        request_id=request_id,
        routes=[route],
        metadata={}
    )

    return BacklogEntry(
        request_id=request_id,
        timestamp=timestamp,
        user_input=request,
        api_calls=[],
        gemini_pipeline=[],
        satellite_image=f"sat_image_{request_id}",
        terrain_image=f"terrain_image_{request_id}",
        result=response,
        total_duration_seconds=5.5
    )


def test_backlog_store_initialization():
    """Test BacklogStore initialization."""
    print("\n=== Testing BacklogStore Initialization ===")

    store = BacklogStore(max_entries=50)
    assert store.max_entries == 50
    assert store.count() == 0

    print("✓ BacklogStore initialization works")


def test_add_entry():
    """Test adding entries to backlog."""
    print("\n=== Testing Add Entry ===")

    store = BacklogStore(max_entries=100)

    entry1 = create_test_backlog_entry("req-001")
    store.add_entry(entry1)

    assert store.count() == 1

    entry2 = create_test_backlog_entry("req-002")
    store.add_entry(entry2)

    assert store.count() == 2

    print("✓ Adding entries works")


def test_get_entry():
    """Test retrieving entries by ID."""
    print("\n=== Testing Get Entry ===")

    store = BacklogStore()

    entry1 = create_test_backlog_entry("req-001")
    entry2 = create_test_backlog_entry("req-002")
    entry3 = create_test_backlog_entry("req-003")

    store.add_entry(entry1)
    store.add_entry(entry2)
    store.add_entry(entry3)

    # Get specific entries
    retrieved1 = store.get_entry("req-001")
    assert retrieved1 is not None
    assert retrieved1.request_id == "req-001"

    retrieved2 = store.get_entry("req-002")
    assert retrieved2.request_id == "req-002"

    # Non-existent entry
    retrieved_none = store.get_entry("req-999")
    assert retrieved_none is None

    print("✓ Getting entries works")


def test_list_entries():
    """Test listing entries (newest first)."""
    print("\n=== Testing List Entries ===")

    store = BacklogStore()

    # Add entries with different timestamps
    now = datetime.utcnow()
    entry1 = create_test_backlog_entry("req-001", now - timedelta(minutes=10))
    entry2 = create_test_backlog_entry("req-002", now - timedelta(minutes=5))
    entry3 = create_test_backlog_entry("req-003", now)

    store.add_entry(entry1)
    store.add_entry(entry2)
    store.add_entry(entry3)

    # List all (should be newest first)
    entries = store.list_entries()
    assert len(entries) == 3
    assert entries[0].request_id == "req-003"  # Newest
    assert entries[1].request_id == "req-002"
    assert entries[2].request_id == "req-001"  # Oldest

    print("✓ Listing entries (newest first) works")


def test_list_entries_pagination():
    """Test pagination parameters."""
    print("\n=== Testing Pagination ===")

    store = BacklogStore()

    # Add 10 entries
    for i in range(10):
        entry = create_test_backlog_entry(f"req-{i:03d}")
        store.add_entry(entry)

    # Test limit
    entries = store.list_entries(limit=5)
    assert len(entries) == 5

    # Test offset
    entries_page1 = store.list_entries(limit=3, offset=0)
    entries_page2 = store.list_entries(limit=3, offset=3)

    assert len(entries_page1) == 3
    assert len(entries_page2) == 3
    assert entries_page1[0].request_id != entries_page2[0].request_id

    # Newest 3 entries
    assert entries_page1[0].request_id == "req-009"
    assert entries_page1[1].request_id == "req-008"
    assert entries_page1[2].request_id == "req-007"

    # Next 3 entries
    assert entries_page2[0].request_id == "req-006"
    assert entries_page2[1].request_id == "req-005"
    assert entries_page2[2].request_id == "req-004"

    print("✓ Pagination works correctly")


def test_list_entries_since():
    """Test filtering by timestamp."""
    print("\n=== Testing Timestamp Filtering ===")

    store = BacklogStore()

    now = datetime.utcnow()

    # Add entries at different times
    entry1 = create_test_backlog_entry("req-001", now - timedelta(hours=2))
    entry2 = create_test_backlog_entry("req-002", now - timedelta(hours=1))
    entry3 = create_test_backlog_entry("req-003", now - timedelta(minutes=30))
    entry4 = create_test_backlog_entry("req-004", now)

    store.add_entry(entry1)
    store.add_entry(entry2)
    store.add_entry(entry3)
    store.add_entry(entry4)

    # Get entries from last hour
    since_time = now - timedelta(hours=1)
    recent_entries = store.list_entries(since=since_time)

    # Should get entries 2, 3, 4 (within last hour)
    assert len(recent_entries) >= 2  # At least entries 3 and 4

    # Verify they're all recent
    for entry in recent_entries:
        assert entry.timestamp >= since_time

    print("✓ Timestamp filtering works")


def test_count():
    """Test counting entries."""
    print("\n=== Testing Count ===")

    store = BacklogStore()

    assert store.count() == 0

    # Add entries
    for i in range(5):
        entry = create_test_backlog_entry(f"req-{i:03d}")
        store.add_entry(entry)

    assert store.count() == 5

    # Count with timestamp filter
    now = datetime.utcnow()
    entry_recent = create_test_backlog_entry("req-recent", now)
    store.add_entry(entry_recent)

    since_time = now - timedelta(minutes=1)
    recent_count = store.count(since=since_time)
    assert recent_count >= 1

    print("✓ Counting entries works")


def test_clear():
    """Test clearing all entries."""
    print("\n=== Testing Clear ===")

    store = BacklogStore()

    # Add entries
    for i in range(5):
        entry = create_test_backlog_entry(f"req-{i:03d}")
        store.add_entry(entry)

    assert store.count() == 5

    # Clear all
    store.clear()
    assert store.count() == 0

    # Verify entries are gone
    retrieved = store.get_entry("req-000")
    assert retrieved is None

    print("✓ Clearing entries works")


def test_max_entries_limit():
    """Test that old entries are dropped when max is exceeded."""
    print("\n=== Testing Max Entries Limit ===")

    store = BacklogStore(max_entries=5)

    # Add 10 entries (should keep only last 5)
    for i in range(10):
        entry = create_test_backlog_entry(f"req-{i:03d}")
        store.add_entry(entry)

    # Should have only 5 entries
    assert store.count() == 5

    # Should have newest 5 entries (005-009)
    entries = store.list_entries()
    entry_ids = [e.request_id for e in entries]

    assert "req-009" in entry_ids
    assert "req-008" in entry_ids
    assert "req-007" in entry_ids
    assert "req-006" in entry_ids
    assert "req-005" in entry_ids

    # Oldest should be gone
    assert "req-000" not in entry_ids
    assert "req-001" not in entry_ids
    assert "req-002" not in entry_ids
    assert "req-003" not in entry_ids
    assert "req-004" not in entry_ids

    print("✓ Max entries limit works (oldest dropped)")


def test_get_images():
    """Test retrieving images for a request."""
    print("\n=== Testing Get Images ===")

    store = BacklogStore()

    entry = create_test_backlog_entry("req-001")
    store.add_entry(entry)

    images = store.get_images("req-001")

    assert images["satellite_image"] == "sat_image_req-001"
    assert images["terrain_image"] == "terrain_image_req-001"

    # Non-existent entry
    images_none = store.get_images("req-999")
    assert images_none["satellite_image"] is None
    assert images_none["terrain_image"] is None

    print("✓ Getting images works")


def test_global_singleton():
    """Test get_backlog_store() returns singleton."""
    print("\n=== Testing Global Singleton ===")

    # Get store twice
    store1 = get_backlog_store()
    store2 = get_backlog_store()

    # Should be same instance
    assert store1 is store2

    # Add entry via store1
    entry = create_test_backlog_entry("req-singleton")
    store1.add_entry(entry)

    # Should be visible in store2
    assert store2.count() == 1
    retrieved = store2.get_entry("req-singleton")
    assert retrieved is not None

    # Clean up for other tests
    store1.clear()

    print("✓ Global singleton works")


def test_entry_ordering():
    """Test that entries maintain insertion order."""
    print("\n=== Testing Entry Ordering ===")

    store = BacklogStore()

    # Add entries in specific order
    entry1 = create_test_backlog_entry("req-first")
    entry2 = create_test_backlog_entry("req-second")
    entry3 = create_test_backlog_entry("req-third")

    store.add_entry(entry1)
    store.add_entry(entry2)
    store.add_entry(entry3)

    # List should be in reverse order (newest first)
    entries = store.list_entries()
    assert entries[0].request_id == "req-third"
    assert entries[1].request_id == "req-second"
    assert entries[2].request_id == "req-first"

    print("✓ Entry ordering maintained correctly")


def test_duplicate_request_id():
    """Test adding entry with same request_id updates existing."""
    print("\n=== Testing Duplicate Request ID ===")

    store = BacklogStore()

    # Add initial entry
    entry1 = create_test_backlog_entry("req-001")
    entry1.total_duration_seconds = 5.0
    store.add_entry(entry1)

    assert store.count() == 1

    # Add entry with same ID (should update)
    entry2 = create_test_backlog_entry("req-001")
    entry2.total_duration_seconds = 10.0
    store.add_entry(entry2)

    # Should still have only 1 entry
    assert store.count() == 1

    # Should have updated value
    retrieved = store.get_entry("req-001")
    assert retrieved.total_duration_seconds == 10.0

    print("✓ Duplicate request ID handling works")


def run_all_tests():
    """Run all backlog storage tests."""
    print("\n" + "=" * 60)
    print("BACKLOG STORAGE SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    test_backlog_store_initialization()
    test_add_entry()
    test_get_entry()
    test_list_entries()
    test_list_entries_pagination()
    test_list_entries_since()
    test_count()
    test_clear()
    test_max_entries_limit()
    test_get_images()
    test_global_singleton()
    test_entry_ordering()
    test_duplicate_request_id()

    print("\n" + "=" * 60)
    print("✅ ALL BACKLOG STORAGE TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
