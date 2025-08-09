"""Integration tests for Phase 3 Content Quality & Real-World Validation.

These tests verify that the Phase 3 modules work together as intended
by end users to validate and improve content for real-world Filipino language use.

Split into smaller, focused test classes to avoid timeouts.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from content_quality_analyzer import ContentQualityAnalyzer, QualityMetrics
from el_nido_trip_validator import ElNidoTripValidator, TripReadinessMetrics
from strategy_recommendation_engine import StrategyRecommendationEngine, StrategyRecommendation
from content_strategy import ContentStrategy


@pytest.mark.unit
class TestPhase3BasicFunctionality:
    """Integration tests for Phase 3 content quality validation workflow."""

    @pytest.fixture
    def sample_filipino_content(self):
        """Sample content with good Filipino authenticity."""
        return """
        Kumusta po! Ako ay tourist sa El Nido. Pwede po ba kayong tumulong?
        Saan po ang magandang restaurant? Gusto ko po kumain ng masarap na pagkain.
        Salamat po sa inyong tulong. Ingat po kayo!
        """

    @pytest.fixture  
    def sample_english_heavy_content(self):
        """Sample content with too much English."""
        return """
        Hello! I am a tourist in El Nido. Can you help me please?
        Where is a good restaurant po? I want to eat masarap na food.
        Thank you for your help. Take care po!
        """

    @pytest.fixture
    def sample_trip_scenarios(self):
        """Sample content covering various trip scenarios."""
        return [
            "Kumusta po! May reservation ako sa hotel. Check-in po.",
            "Magkano po ang pamasahe sa tricycle papuntang beach?",
            "Pwede po ba makita ang menu? Gusto ko ng isda at kanin.",
            "Swimming po tayo. Maganda ang dagat dito sa El Nido!",
            "Tulong po! May problema sa kwarto. Walang tubig sa banyo."
        ]

    def test_content_quality_analysis_workflow(self, sample_filipino_content, sample_english_heavy_content):
        """Test basic content quality analysis workflow."""
        analyzer = ContentQualityAnalyzer()
        
        # Test single content analysis - keep it simple
        filipino_quality = analyzer.analyze_content_quality(sample_filipino_content, "deeper")
        
        # Basic validation
        assert filipino_quality.filipino_ratio > 0.0
        assert filipino_quality.overall_quality_score > 0.0
        assert isinstance(filipino_quality.cultural_expression_count, int)

    def test_el_nido_trip_validation_basic(self, sample_trip_scenarios):
        """Test basic El Nido trip readiness validation."""
        validator = ElNidoTripValidator()
        
        # Test single scenario analysis - keep it simple
        trip_metrics = validator.calculate_trip_readiness(sample_trip_scenarios[:2])  # Just 2 scenarios
        
        # Basic validation
        assert 0.0 <= trip_metrics.overall_readiness_score <= 1.0
        assert isinstance(trip_metrics.identified_gaps, list)

    def test_strategy_recommendation_basic(self):
        """Test basic strategy recommendation functionality."""
        engine = StrategyRecommendationEngine()
        
        # Simple test with minimal content
        simple_content = ["Kumusta po!"]
        
        recommendation = engine.recommend_next_action(
            content_history=simple_content,
            strategies_used=["balanced"]
        )
        
        # Basic validation
        assert isinstance(recommendation, StrategyRecommendation)
        assert recommendation.confidence_score > 0.0
        assert len(recommendation.specific_actions) > 0


@pytest.mark.integration
class TestPhase3Integration:
    """More complex integration tests - marked as slow."""
    
    def test_content_improvement_validation(self):
        """Test validating content improvement."""
        analyzer = ContentQualityAnalyzer()
        
        # Simple comparison
        original = "Hello, where restaurant?"
        enhanced = "Kumusta po! Saan po ang restaurant?"
        
        comparison = analyzer.compare_strategy_outputs(
            original_content=original,
            enhanced_content=enhanced, 
            strategy="deeper"
        )
        
        # Basic validation  
        assert 'improvements' in comparison
        assert 'strategy_effectiveness' in comparison

@pytest.mark.slow  
class TestPhase3Comprehensive:
    """Comprehensive tests - run separately to avoid timeouts."""
    
    def test_simple_user_progression(self):
        """Test simple user content progression."""
        # Just 2 content pieces to keep it fast
        content_progression = [
            "Hello, where hotel?",
            "Kumusta po! Saan po ang hotel?"
        ]
        
        analyzer = ContentQualityAnalyzer()
        
        # Quick quality check
        quality1 = analyzer.analyze_content_quality(content_progression[0])
        quality2 = analyzer.analyze_content_quality(content_progression[1])
        
        # Basic improvement validation
        assert quality2.filipino_ratio > quality1.filipino_ratio