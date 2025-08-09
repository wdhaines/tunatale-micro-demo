"""Test utilities for optimizing Phase 3 test performance.

This module provides mocks and fixtures to speed up tests by avoiding
expensive operations like SpaCy processing, file I/O, and complex analysis.
"""
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Dict, List, Any
import pytest

from content_quality_analyzer import QualityMetrics
from el_nido_trip_validator import TripReadinessMetrics
from strategy_recommendation_engine import StrategyRecommendation
from content_strategy import ContentStrategy


@dataclass
class FastQualityMetrics:
    """Fast mock quality metrics for testing."""
    
    @staticmethod
    def create_good_filipino_quality() -> QualityMetrics:
        """Create metrics for good Filipino content."""
        return QualityMetrics(
            filipino_ratio=0.8,
            authentic_spelling_score=0.9,
            po_usage_score=0.7,
            cultural_expression_count=5,
            vocabulary_complexity_score=0.6,
            collocation_complexity_score=0.5,
            cultural_vocabulary_count=8,
            strategy_differentiation_score=0.7,
            learning_objective_alignment=0.8,
            srs_integration_score=0.8,
            overall_quality_score=0.75
        )
    
    @staticmethod
    def create_poor_filipino_quality() -> QualityMetrics:
        """Create metrics for poor Filipino content."""
        return QualityMetrics(
            filipino_ratio=0.3,
            authentic_spelling_score=0.4,
            po_usage_score=0.2,
            cultural_expression_count=1,
            vocabulary_complexity_score=0.3,
            collocation_complexity_score=0.2,
            cultural_vocabulary_count=2,
            strategy_differentiation_score=0.3,
            learning_objective_alignment=0.4,
            srs_integration_score=0.5,
            overall_quality_score=0.35
        )
    
    @staticmethod
    def create_improved_quality() -> QualityMetrics:
        """Create metrics showing improvement from poor to good."""
        return QualityMetrics(
            filipino_ratio=0.7,
            authentic_spelling_score=0.8,
            po_usage_score=0.6,
            cultural_expression_count=4,
            vocabulary_complexity_score=0.5,
            collocation_complexity_score=0.4,
            cultural_vocabulary_count=6,
            strategy_differentiation_score=0.6,
            learning_objective_alignment=0.7,
            srs_integration_score=0.7,
            overall_quality_score=0.65
        )


@dataclass 
class FastTripMetrics:
    """Fast mock trip readiness metrics for testing."""
    
    @staticmethod
    def create_good_trip_readiness() -> TripReadinessMetrics:
        """Create good trip readiness metrics."""
        return TripReadinessMetrics(
            accommodation_coverage=0.8,
            transportation_coverage=0.7,
            restaurant_coverage=0.9,
            activity_coverage=0.6,
            emergency_coverage=0.5,
            essential_vocabulary_percentage=0.75,
            cultural_vocabulary_percentage=0.8,
            practical_vocabulary_percentage=0.7,
            respectful_interaction_score=0.85,
            social_boundary_awareness=0.8,
            authentic_goodbye_patterns=0.9,
            overall_readiness_score=0.73,
            identified_gaps=["Low emergency coverage", "Missing activity vocabulary"]
        )
    
    @staticmethod
    def create_poor_trip_readiness() -> TripReadinessMetrics:
        """Create poor trip readiness metrics."""
        return TripReadinessMetrics(
            accommodation_coverage=0.3,
            transportation_coverage=0.2,
            restaurant_coverage=0.4,
            activity_coverage=0.1,
            emergency_coverage=0.0,
            essential_vocabulary_percentage=0.3,
            cultural_vocabulary_percentage=0.4,
            practical_vocabulary_percentage=0.2,
            respectful_interaction_score=0.4,
            social_boundary_awareness=0.3,
            authentic_goodbye_patterns=0.5,
            overall_readiness_score=0.25,
            identified_gaps=[
                "Low accommodation coverage", 
                "Missing transportation vocabulary",
                "No emergency preparation"
            ]
        )


@dataclass
class FastRecommendations:
    """Fast mock recommendations for testing."""
    
    @staticmethod
    def create_deeper_recommendation() -> StrategyRecommendation:
        """Create DEEPER strategy recommendation."""
        return StrategyRecommendation(
            recommended_strategy=ContentStrategy.DEEPER,
            confidence_score=0.85,
            primary_reason="Low Filipino authenticity - need cultural enhancement",
            specific_actions=[
                "Use DEEPER strategy to replace English with authentic Tagalog",
                "Focus on cultural expressions and natural Filipino speech patterns"
            ],
            expected_improvements=[
                "Higher Filipino-to-English ratio",
                "More authentic cultural expressions"
            ],
            warning_notes=["Monitor comprehension with complex vocabulary"]
        )
    
    @staticmethod
    def create_wider_recommendation() -> StrategyRecommendation:
        """Create WIDER strategy recommendation."""
        return StrategyRecommendation(
            recommended_strategy=ContentStrategy.WIDER,
            confidence_score=0.75,
            primary_reason="Limited scenario coverage - need practical expansion",
            specific_actions=[
                "Use WIDER strategy to add missing scenarios",
                "Focus on practical vocabulary for real trip situations"
            ],
            expected_improvements=[
                "Better coverage of essential trip scenarios",
                "More practical vocabulary for real situations"
            ]
        )
    
    @staticmethod
    def create_balanced_recommendation() -> StrategyRecommendation:
        """Create BALANCED strategy recommendation."""
        return StrategyRecommendation(
            recommended_strategy=ContentStrategy.BALANCED,
            confidence_score=0.7,
            primary_reason="Build solid foundation before specialization",
            specific_actions=[
                "Continue with BALANCED strategy",
                "Focus on essential vocabulary and basic patterns"
            ],
            expected_improvements=[
                "Stable learning progression",
                "Solid foundation building"
            ]
        )


class MockContentQualityAnalyzer:
    """Fast mock content quality analyzer."""
    
    def __init__(self):
        self.call_count = 0
    
    def analyze_content_quality(self, content: str, strategy: str = "balanced", baseline_content: str = None) -> QualityMetrics:
        """Mock content analysis based on simple heuristics."""
        self.call_count += 1
        
        # Fast heuristic-based analysis
        content_lower = content.lower()
        
        # Simple Filipino vs English detection
        filipino_indicators = ['kumusta', 'po', 'salamat', 'saan', 'ako', 'tayo', 'kayo', 'gusto', 'masarap']
        filipino_count = sum(1 for word in filipino_indicators if word in content_lower)
        
        if filipino_count >= 3:
            return FastQualityMetrics.create_good_filipino_quality()
        elif filipino_count >= 1:
            return FastQualityMetrics.create_improved_quality()
        else:
            return FastQualityMetrics.create_poor_filipino_quality()
    
    def compare_strategy_outputs(self, original_content: str, enhanced_content: str, strategy: str) -> Dict[str, Any]:
        """Mock strategy comparison."""
        original_quality = self.analyze_content_quality(original_content)
        enhanced_quality = self.analyze_content_quality(enhanced_content)
        
        filipino_improvement = enhanced_quality.filipino_ratio - original_quality.filipino_ratio
        overall_improvement = enhanced_quality.overall_quality_score - original_quality.overall_quality_score
        
        return {
            'original_quality': original_quality,
            'enhanced_quality': enhanced_quality,
            'improvements': {
                'filipino_ratio_improvement': filipino_improvement,
                'spelling_improvement': 0.1 if filipino_improvement > 0 else 0,
                'vocabulary_complexity_improvement': 0.05,
                'overall_improvement': overall_improvement
            },
            'strategy_validation': {
                'authentic_enhancement': filipino_improvement > 0.1,
                'quality_maintained': overall_improvement >= 0,
                'cultural_depth': enhanced_quality.cultural_expression_count > original_quality.cultural_expression_count
            },
            'strategy_effectiveness': 'successful' if overall_improvement > 0 else 'needs_improvement'
        }


class MockElNidoTripValidator:
    """Fast mock trip validator."""
    
    def __init__(self):
        self.call_count = 0
    
    def calculate_trip_readiness(self, content_list: List[str]) -> TripReadinessMetrics:
        """Mock trip readiness calculation."""
        self.call_count += 1
        
        # Simple heuristic based on content length and keywords
        combined_content = ' '.join(content_list).lower()
        
        # Check for trip scenario keywords
        scenario_keywords = {
            'hotel': ['hotel', 'check-in', 'kwarto', 'room'],
            'transport': ['tricycle', 'jeepney', 'banca', 'sakay'],
            'restaurant': ['pagkain', 'menu', 'kumain', 'restaurant'],
            'activity': ['swimming', 'beach', 'dagat', 'island'],
            'emergency': ['tulong', 'problema', 'hospital', 'help']
        }
        
        coverage_scores = {}
        for scenario, keywords in scenario_keywords.items():
            coverage_scores[scenario] = min(1.0, sum(1 for kw in keywords if kw in combined_content) / len(keywords))
        
        avg_coverage = sum(coverage_scores.values()) / len(coverage_scores)
        
        if avg_coverage > 0.6:
            return FastTripMetrics.create_good_trip_readiness()
        else:
            return FastTripMetrics.create_poor_trip_readiness()
    
    def validate_content_for_trip(self, content_list: List[str], trip_days: int = 5) -> Dict[str, Any]:
        """Mock trip validation."""
        readiness_metrics = self.calculate_trip_readiness(content_list)
        
        if readiness_metrics.overall_readiness_score > 0.7:
            readiness_level = 'good'
        elif readiness_metrics.overall_readiness_score > 0.5:
            readiness_level = 'adequate'
        else:
            readiness_level = 'needs_improvement'
        
        return {
            'readiness_metrics': readiness_metrics,
            'trip_readiness_level': readiness_level,
            'recommendations': ["Add more scenarios"] if readiness_level != 'good' else [],
            'readiness_percentage': readiness_metrics.overall_readiness_score * 100,
            'critical_gaps': readiness_metrics.identified_gaps,
            'cultural_appropriateness': 'appropriate' if readiness_metrics.respectful_interaction_score > 0.7 else 'needs_improvement'
        }


class MockStrategyRecommendationEngine:
    """Fast mock strategy recommendation engine."""
    
    def __init__(self):
        self.call_count = 0
        self.quality_analyzer = MockContentQualityAnalyzer()
        self.trip_validator = MockElNidoTripValidator()
    
    def recommend_next_action(self, content_history: List[str], strategies_used: List[str], target_scenario: str = 'el_nido_trip') -> StrategyRecommendation:
        """Mock recommendation based on simple heuristics."""
        self.call_count += 1
        
        if not content_history:
            return FastRecommendations.create_balanced_recommendation()
        
        # Analyze latest content
        latest_content = content_history[-1]
        latest_quality = self.quality_analyzer.analyze_content_quality(latest_content)
        
        # Simple recommendation logic
        if latest_quality.filipino_ratio < 0.5:
            return FastRecommendations.create_deeper_recommendation()
        elif len(content_history) < 5:
            return FastRecommendations.create_wider_recommendation()
        else:
            return FastRecommendations.create_balanced_recommendation()
    
    def validate_strategy_effectiveness(self, original_content: str, enhanced_content: str, strategy_used: str) -> Dict[str, Any]:
        """Mock strategy validation."""
        comparison = self.quality_analyzer.compare_strategy_outputs(original_content, enhanced_content, strategy_used)
        
        return {
            'strategy_worked': comparison['strategy_effectiveness'] == 'successful',
            'improvements_measured': comparison['improvements'],
            'strategy_validation': comparison['strategy_validation'],
            'overall_effectiveness': comparison['strategy_effectiveness'],
            'feedback': [f"{strategy_used.title()} strategy {'succeeded' if comparison['strategy_effectiveness'] == 'successful' else 'needs improvement'}"]
        }


# Test fixtures using fast mocks
@pytest.fixture
def fast_quality_analyzer():
    """Provide fast mock quality analyzer."""
    return MockContentQualityAnalyzer()


@pytest.fixture
def fast_trip_validator():
    """Provide fast mock trip validator."""
    return MockElNidoTripValidator()


@pytest.fixture
def fast_recommendation_engine():
    """Provide fast mock recommendation engine."""
    return MockStrategyRecommendationEngine()


@pytest.fixture
def mock_phase3_modules():
    """Patch all Phase 3 modules with fast mocks."""
    with patch('content_quality_analyzer.ContentQualityAnalyzer', MockContentQualityAnalyzer), \
         patch('el_nido_trip_validator.ElNidoTripValidator', MockElNidoTripValidator), \
         patch('strategy_recommendation_engine.StrategyRecommendationEngine', MockStrategyRecommendationEngine):
        yield


# Pytest markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Fast unit tests (< 5s)")
    config.addinivalue_line("markers", "integration: Integration tests (may be slow)")
    config.addinivalue_line("markers", "slow: Slow tests (> 10s)")
    config.addinivalue_line("markers", "phase3: Phase 3 content validation tests")


# Custom timeout decorator for specific tests
def timeout_override(seconds: int):
    """Override timeout for specific test functions."""
    def decorator(func):
        func.pytestmark = pytest.mark.timeout(seconds)
        return func
    return decorator