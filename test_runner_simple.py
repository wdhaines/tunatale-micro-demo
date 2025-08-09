#!/usr/bin/env python3
"""
Simple test runner to identify and fix Phase 3 test issues.
"""
import sys
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def run_test_function(test_func, test_name):
    """Run a single test function and report results."""
    try:
        print(f"Running {test_name}...")
        test_func()
        print(f"✅ {test_name} PASSED")
        return True
    except Exception as e:
        print(f"❌ {test_name} FAILED: {e}")
        traceback.print_exc()
        return False

def test_content_quality_basic():
    """Test basic content quality analysis."""
    from content_quality_analyzer import ContentQualityAnalyzer
    
    analyzer = ContentQualityAnalyzer()
    content = "Kumusta po! Salamat po sa inyong tulong!"
    quality = analyzer.analyze_content_quality(content)
    
    assert quality.overall_quality_score > 0.0
    assert quality.filipino_ratio > 0.0
    assert isinstance(quality.cultural_expression_count, int)

def test_trip_readiness_basic():
    """Test basic trip readiness validation."""
    from el_nido_trip_validator import ElNidoTripValidator
    
    validator = ElNidoTripValidator()
    content = ["Kumusta po! Saan po ang hotel?", "Salamat po!"]
    metrics = validator.calculate_trip_readiness(content)
    
    assert isinstance(metrics.overall_readiness_score, float)
    assert isinstance(metrics.identified_gaps, list)

def test_recommendation_basic():
    """Test basic strategy recommendation."""
    from strategy_recommendation_engine import StrategyRecommendationEngine
    from strategy_recommendation_engine import StrategyRecommendation
    
    engine = StrategyRecommendationEngine()
    content = ["Kumusta po!"]
    rec = engine.recommend_next_action(content, ["balanced"])
    
    assert isinstance(rec, StrategyRecommendation)
    assert rec.confidence_score > 0.0
    assert len(rec.specific_actions) > 0

def test_content_comparison():
    """Test content comparison functionality."""
    from content_quality_analyzer import ContentQualityAnalyzer
    
    analyzer = ContentQualityAnalyzer()
    original = "Hello, where restaurant?"
    enhanced = "Kumusta po! Saan po ang restaurant?"
    
    comparison = analyzer.compare_strategy_outputs(original, enhanced, "deeper")
    
    assert 'improvements' in comparison
    assert 'strategy_effectiveness' in comparison

def test_fast_mode():
    """Test fast mode functionality."""
    from content_quality_analyzer import ContentQualityAnalyzer
    
    analyzer = ContentQualityAnalyzer(fast_mode=True)
    quality = analyzer.analyze_content_quality("Kumusta po! Salamat po!")
    
    assert quality.overall_quality_score > 0.0
    assert quality.filipino_ratio > 0.0

def test_trip_validation():
    """Test trip validation functionality."""
    from el_nido_trip_validator import ElNidoTripValidator
    
    validator = ElNidoTripValidator()
    content = ["Kumusta po! Check-in po sa hotel.", "Salamat po!"]
    validation = validator.validate_content_for_trip(content, trip_days=2)
    
    assert 'readiness_metrics' in validation
    assert 'trip_readiness_level' in validation

def test_strategy_validation():
    """Test strategy effectiveness validation."""
    from strategy_recommendation_engine import StrategyRecommendationEngine
    
    engine = StrategyRecommendationEngine()
    original = "Hello, I want food."
    enhanced = "Kumusta po! Gusto ko po ng pagkain."
    
    validation = engine.validate_strategy_effectiveness(original, enhanced, "deeper")
    
    assert 'strategy_worked' in validation
    assert 'overall_effectiveness' in validation

def main():
    """Run all basic tests and report results."""
    print("🧪 Running Phase 3 Basic Test Suite")
    print("=" * 50)
    
    tests = [
        (test_content_quality_basic, "Content Quality Basic"),
        (test_trip_readiness_basic, "Trip Readiness Basic"),
        (test_recommendation_basic, "Recommendation Basic"),
        (test_content_comparison, "Content Comparison"),
        (test_fast_mode, "Fast Mode"),
        (test_trip_validation, "Trip Validation"),
        (test_strategy_validation, "Strategy Validation"),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func, test_name in tests:
        if run_test_function(test_func, test_name):
            passed += 1
        print("-" * 30)
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        return 0
    else:
        print(f"⚠️  {total - passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())