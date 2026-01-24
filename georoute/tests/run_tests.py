"""
Comprehensive test runner for GeoRoute tactical planning system.
"""

import sys
import traceback
from datetime import datetime


def run_test_module(module_name: str, test_function_name: str):
    """Run a specific test module."""
    print(f"\n{'=' * 80}")
    print(f"Running: {module_name}")
    print(f"{'=' * 80}")

    try:
        if module_name == "test_tactical_models":
            from .test_tactical_models import run_all_tests
            run_all_tests()
        elif module_name == "test_backlog_storage":
            from .test_backlog_storage import run_all_tests
            run_all_tests()
        elif module_name == "test_integration":
            from .test_integration import run_all_tests
            run_all_tests()
        else:
            print(f"❌ Unknown test module: {module_name}")
            return False

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {module_name}")
        print(f"Error: {str(e)}")
        print("\nTraceback:")
        traceback.print_exc()
        return False


def main():
    """Run all test suites."""
    print("\n" + "=" * 80)
    print("GEOROUTE TACTICAL PLANNING SYSTEM")
    print("COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    test_modules = [
        ("test_tactical_models", "Tactical Planning Models"),
        ("test_backlog_storage", "Backlog Storage System"),
        ("test_integration", "Integration Tests"),
    ]

    results = {}

    for module_name, description in test_modules:
        success = run_test_module(module_name, description)
        results[description] = success

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")

    print("=" * 80)
    print(f"Results: {passed}/{total} test suites passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("=" * 80)
        return 0
    else:
        print("⚠️  SOME TESTS FAILED")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
