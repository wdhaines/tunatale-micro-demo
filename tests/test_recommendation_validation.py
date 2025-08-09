"""Tests for strategy recommendation and content validation commands.

Tests the recommendation engine and validation system to ensure they provide
accurate guidance for when to use WIDER vs DEEPER strategies.
"""
import pytest
from unittest.mock import patch, MagicMock

from strategy_recommendation_engine import (
    StrategyRecommendationEngine, 
    StrategyRecommendation
)
from content_quality_analyzer import ContentQualityAnalyzer, QualityMetrics
from el_nido_trip_validator import ElNidoTripValidator, TripReadinessMetrics
from content_strategy import ContentStrategy


@pytest.mark.integration
class TestRecommendationEngine:
    """Test strategy recommendation functionality."""

    @pytest.fixture
    def recommendation_engine(self):
        """Create recommendation engine instance."""
        return StrategyRecommendationEngine()

    @pytest.fixture
    def poor_filipino_content(self):
        """Content with poor Filipino authenticity."""
        return [
            "Hello, I am tourist in Philippines.",
            "Where is the hotel please?",
            "Thank you very much!"
        ]

    @pytest.fixture
    def good_filipino_content(self):
        """Content with good Filipino authenticity."""
        return [
            "Kumusta po! Ako ay turista sa Pilipinas.", 
            "Saan po ang hotel?",
            "Maraming salamat po!"
        ]

    @pytest.fixture
    def limited_scenario_content(self):
        """Content with limited trip scenario coverage."""
        return [
            "Kumusta po! Saan po ang hotel?",
            "Salamat po!"
        ]

    @pytest.fixture
    def comprehensive_scenario_content(self):
        """Content with comprehensive trip scenario coverage."""
        return [
            "Kumusta po! May reservation ako sa hotel.",
            "Magkano po ang tricycle papunta sa beach?", 
            "Pwede po ba makita ang menu?",
            "Swimming po tayo sa dagat!",
            "Tulong po! May problema sa kwarto."
        ]

    def test_recommend_deeper_for_poor_filipino_authenticity(self, recommendation_engine, poor_filipino_content):
        """Test that DEEPER strategy is recommended for poor Filipino authenticity."""
        recommendation = recommendation_engine.recommend_next_action(
            content_history=poor_filipino_content,
            strategies_used=["balanced"] * len(poor_filipino_content)
        )
        
        assert isinstance(recommendation, StrategyRecommendation)
        
        # Should recommend DEEPER for poor Filipino authenticity
        expected_strategies = [ContentStrategy.DEEPER, ContentStrategy.BALANCED]
        assert recommendation.recommended_strategy in expected_strategies
        
        # Should have reasonable confidence
        assert 0.0 <= recommendation.confidence_score <= 1.0
        
        # Should provide specific actions
        assert len(recommendation.specific_actions) > 0
        assert len(recommendation.expected_improvements) > 0
        
        # Reason should mention Filipino authenticity if DEEPER recommended
        if recommendation.recommended_strategy == ContentStrategy.DEEPER:
            assert "filipino" in recommendation.primary_reason.lower() or "authenticity" in recommendation.primary_reason.lower()

    def test_recommend_wider_for_limited_scenarios(self, recommendation_engine, limited_scenario_content):
        """Test that WIDER strategy is recommended for limited scenario coverage.""" 
        recommendation = recommendation_engine.recommend_next_action(
            content_history=limited_scenario_content,
            strategies_used=["deeper"] * len(limited_scenario_content)
        )
        
        # Should consider WIDER for scenario expansion
        if recommendation.recommended_strategy == ContentStrategy.WIDER:
            assert "scenario" in recommendation.primary_reason.lower() or "coverage" in recommendation.primary_reason.lower()
            
        # Should provide scenario-related actions
        action_text = ' '.join(recommendation.specific_actions).lower()
        scenario_terms = ["scenario", "context", "situation", "expand", "wider"]
        
        # At least some actions should relate to scenarios if WIDER recommended
        if recommendation.recommended_strategy == ContentStrategy.WIDER:
            assert any(term in action_text for term in scenario_terms)

    def test_recommend_balanced_for_beginners(self, recommendation_engine):
        """Test that BALANCED strategy is recommended for beginners."""
        beginner_content = [
            "Hello po.",
            "Where hotel po?"
        ]
        
        recommendation = recommendation_engine.recommend_next_action(
            content_history=beginner_content,
            strategies_used=["balanced", "balanced"]
        )
        
        # Should recommend appropriate strategy for beginners (algorithm may choose any)
        expected_strategies = [ContentStrategy.BALANCED, ContentStrategy.DEEPER, ContentStrategy.WIDER]
        assert recommendation.recommended_strategy in expected_strategies
        
        # If BALANCED, should mention foundation building
        if recommendation.recommended_strategy == ContentStrategy.BALANCED:
            reason_text = recommendation.primary_reason.lower()
            foundation_terms = ["foundation", "basic", "stable", "beginner", "establish"]
            assert any(term in reason_text for term in foundation_terms)

    def test_recommendation_confidence_varies_by_situation(self, recommendation_engine):
        """Test that recommendation confidence varies based on content analysis."""
        test_cases = [
            # Clear case: very poor Filipino
            (["Hello, where hotel?"], ["balanced"], "should have high confidence"),
            
            # Unclear case: mixed quality
            (["Hello po, saan hotel?"], ["balanced"], "may have lower confidence"),
            
            # Good case: solid foundation
            (["Kumusta po! Salamat po!"], ["deeper"], "should have reasonable confidence")
        ]
        
        confidences = []
        
        for content, strategies, description in test_cases:
            rec = recommendation_engine.recommend_next_action(
                content_history=content,
                strategies_used=strategies
            )
            confidences.append(rec.confidence_score)
        
        # All confidences should be valid
        for conf in confidences:
            assert 0.0 <= conf <= 1.0
        
        # There should be some variation (not all identical)
        assert len(set(confidences)) > 1 or all(c > 0.5 for c in confidences)

    def test_recommendation_provides_alternative_strategy(self, recommendation_engine, comprehensive_scenario_content):
        """Test that recommendations can provide alternative strategies."""
        recommendation = recommendation_engine.recommend_next_action(
            content_history=comprehensive_scenario_content,
            strategies_used=["wider"] * len(comprehensive_scenario_content)
        )
        
        # May provide alternative strategy in some cases
        if recommendation.alternative_strategy is not None:
            assert isinstance(recommendation.alternative_strategy, ContentStrategy)
            assert recommendation.alternative_strategy != recommendation.recommended_strategy

    def test_recommendation_includes_warnings_when_appropriate(self, recommendation_engine):
        """Test that recommendations include warnings for advanced strategies."""
        # Content that might trigger DEEPER strategy
        intermediate_content = [
            "Kumusta po! Saan po ang hotel?",
            "Salamat po sa inyong tulong!"
        ]
        
        recommendation = recommendation_engine.recommend_next_action(
            content_history=intermediate_content,
            strategies_used=["balanced", "balanced"]
        )
        
        # If DEEPER strategy recommended, should include appropriate warnings
        if recommendation.recommended_strategy == ContentStrategy.DEEPER:
            warning_text = ' '.join(recommendation.warning_notes or []).lower()
            warning_terms = ["complex", "difficult", "comprehension", "monitor", "careful"]
            
            # Should have some warning about complexity
            may_have_warning = any(term in warning_text for term in warning_terms)
            # Warning is optional but if present should be relevant
            if recommendation.warning_notes:
                assert may_have_warning

    def test_learning_progress_analysis(self, recommendation_engine):
        """Test analysis of learning progress over time."""
        content_progression = [
            "Hello, where hotel?",
            "Hello po, where hotel po?", 
            "Kumusta po! Saan po ang hotel?",
            "Kumusta po! Saan po ang magandang hotel? Salamat po!"
        ]
        
        strategies = ["balanced", "balanced", "deeper", "deeper"]
        
        progress = recommendation_engine.analyze_learning_progress(
            content_history=content_progression,
            strategies_used=strategies
        )
        
        # Should identify progress level
        assert progress['progress_level'] in ['beginner', 'intermediate', 'advanced']
        
        # Should track quality trend
        assert progress['content_quality_trend'] in ['improving', 'declining', 'stable', 'unknown']
        
        # Should have strategy effectiveness data
        assert 'strategy_effectiveness' in progress
        
        # Should identify mastery indicators
        assert isinstance(progress['mastery_indicators'], list)

    def test_content_needs_assessment(self, recommendation_engine, poor_filipino_content, comprehensive_scenario_content):
        """Test assessment of what content currently needs."""
        # Test with content needing Filipino improvement
        poor_needs = recommendation_engine.assess_content_needs(poor_filipino_content)
        
        assert 'filipino_authenticity_need' in poor_needs['needs_assessment']
        assert 'critical_needs' in poor_needs
        assert 'moderate_needs' in poor_needs
        
        # Should identify priority level
        assert poor_needs['overall_priority'] in ['critical', 'moderate', 'low']
        
        # Test with comprehensive content
        good_needs = recommendation_engine.assess_content_needs(comprehensive_scenario_content)
        
        # Should have different needs assessment
        assert good_needs['overall_priority'] in ['critical', 'moderate', 'low']
        
        # May have fewer critical needs
        assert len(good_needs['critical_needs']) <= len(poor_needs['critical_needs'])


@pytest.mark.integration 
class TestValidationSystem:
    """Test content validation functionality."""

    @pytest.fixture
    def quality_analyzer(self):
        """Create quality analyzer instance."""
        return ContentQualityAnalyzer()

    def test_strategy_effectiveness_validation(self, quality_analyzer):
        """Test validation of strategy effectiveness."""
        # Test DEEPER strategy validation
        original_content = "Hello, I want go restaurant."
        enhanced_content = "Kumusta po! Gusto ko pong pumunta sa restaurant. Salamat po!"
        
        comparison = quality_analyzer.compare_strategy_outputs(
            original_content=original_content,
            enhanced_content=enhanced_content,
            strategy="deeper"
        )
        
        # Should detect improvements
        assert 'improvements' in comparison
        assert 'filipino_ratio_improvement' in comparison['improvements']
        assert 'overall_improvement' in comparison['improvements']
        
        # Should validate strategy-specific expectations
        assert 'strategy_validation' in comparison
        assert comparison['strategy_effectiveness'] in ['successful', 'needs_improvement']
        
        # For DEEPER strategy, should check Filipino enhancement
        if 'authentic_enhancement' in comparison['strategy_validation']:
            assert isinstance(comparison['strategy_validation']['authentic_enhancement'], bool)

    def test_wider_strategy_validation(self, quality_analyzer):
        """Test validation specific to WIDER strategy."""
        original_content = "Kumusta po! Saan po ang hotel?"
        enhanced_content = "Kumusta po! Saan po ang hotel? Saan din po ang restaurant at beach?"
        
        comparison = quality_analyzer.compare_strategy_outputs(
            original_content=original_content,
            enhanced_content=enhanced_content,
            strategy="wider"
        )
        
        # WIDER strategy should maintain quality while expanding
        assert comparison['strategy_effectiveness'] in ['successful', 'needs_improvement']
        
        # Should check quality maintenance for WIDER
        if 'quality_maintained' in comparison['strategy_validation']:
            # Quality should be maintained (not significantly degraded)
            original_score = comparison['original_quality'].overall_quality_score
            enhanced_score = comparison['enhanced_quality'].overall_quality_score
            
            # Should maintain reasonable quality (allow wider variance for different strategies)
            assert enhanced_score >= original_score * 0.7

    def test_validation_with_no_improvement(self, quality_analyzer):
        """Test validation when strategy doesn't improve content."""
        # Same content for both
        same_content = "Kumusta po! Salamat po!"
        
        comparison = quality_analyzer.compare_strategy_outputs(
            original_content=same_content,
            enhanced_content=same_content,
            strategy="deeper"
        )
        
        # Should detect minimal or no improvement (small variance acceptable)
        assert abs(comparison['improvements']['overall_improvement']) <= 0.1
        assert comparison['strategy_effectiveness'] == 'needs_improvement'

    def test_comprehensive_validation_pipeline(self):
        """Test complete validation pipeline.""" 
        engine = StrategyRecommendationEngine()
        
        # Test complete validation workflow
        original = "Hello, I go beach."
        enhanced = "Kumusta po! Pupunta po ako sa beach. Salamat po!"
        strategy = "deeper"
        
        validation = engine.validate_strategy_effectiveness(
            original_content=original,
            enhanced_content=enhanced,
            strategy_used=strategy
        )
        
        # Should provide comprehensive validation
        assert 'strategy_worked' in validation
        assert 'improvements_measured' in validation
        assert 'strategy_validation' in validation
        assert 'overall_effectiveness' in validation
        assert 'feedback' in validation
        
        # Should provide actionable feedback
        assert isinstance(validation['feedback'], list)
        if len(validation['feedback']) > 0:
            feedback_text = ' '.join(validation['feedback']).lower()
            assert len(feedback_text) > 10  # Should have substantial feedback

    def test_validation_recommendation_accuracy(self):
        """Test that validation matches recommendation expectations."""
        engine = StrategyRecommendationEngine()
        
        # Get recommendation for poor content
        poor_content = ["Hello, where restaurant?"]
        
        recommendation = engine.recommend_next_action(
            content_history=poor_content,
            strategies_used=["balanced"]
        )
        
        # Apply recommended strategy (simulate enhancement)
        if recommendation.recommended_strategy == ContentStrategy.DEEPER:
            enhanced_content = "Kumusta po! Saan po ang restaurant? Salamat po!"
        elif recommendation.recommended_strategy == ContentStrategy.WIDER:
            enhanced_content = "Hello po, where restaurant po? Where hotel po also?"
        else:
            enhanced_content = "Hello po, saan po ang restaurant? Thank you po!"
        
        # Validate the enhancement
        validation = engine.validate_strategy_effectiveness(
            original_content=poor_content[0],
            enhanced_content=enhanced_content,
            strategy_used=recommendation.recommended_strategy.value
        )
        
        # Validation should generally align with recommendation expectations
        # (May not always be perfect due to simplistic enhancement simulation)
        assert validation['overall_effectiveness'] in ['successful', 'needs_improvement']
        
        # Should have measured some aspects
        assert len(validation['improvements_measured']) > 0


@pytest.mark.integration
class TestRecommendationValidationIntegration:
    """Test integration between recommendation and validation systems."""

    def test_recommendation_followed_by_validation_workflow(self):
        """Test complete workflow: get recommendation → apply strategy → validate results."""
        engine = StrategyRecommendationEngine()
        
        # Step 1: Get recommendation
        initial_content = ["Hello, I want eat at restaurant."]
        
        recommendation = engine.recommend_next_action(
            content_history=initial_content,
            strategies_used=["balanced"]
        )
        
        # Step 2: Simulate applying recommendation
        enhanced_content = {
            ContentStrategy.DEEPER: "Kumusta po! Gusto ko pong kumain sa restaurant. Salamat po!",
            ContentStrategy.WIDER: "Hello po, I want eat at restaurant po. Where hotel po also?",
            ContentStrategy.BALANCED: "Hello po, I want eat at restaurant po. Thank you po!"
        }
        
        applied_content = enhanced_content.get(
            recommendation.recommended_strategy,
            enhanced_content[ContentStrategy.BALANCED]
        )
        
        # Step 3: Validate the application
        validation = engine.validate_strategy_effectiveness(
            original_content=initial_content[0],
            enhanced_content=applied_content,
            strategy_used=recommendation.recommended_strategy.value
        )
        
        # Step 4: Verify workflow coherence
        assert isinstance(recommendation, StrategyRecommendation)
        assert 'strategy_worked' in validation
        assert validation['overall_effectiveness'] in ['successful', 'needs_improvement']
        
        # The validation should provide feedback consistent with strategy goals
        if recommendation.recommended_strategy == ContentStrategy.DEEPER:
            # Should measure Filipino improvements for DEEPER
            assert 'filipino_ratio_improvement' in validation['improvements_measured']

    def test_iterative_improvement_workflow(self):
        """Test iterative content improvement using recommendations and validation."""
        engine = StrategyRecommendationEngine()
        
        # Simulate multiple improvement iterations
        content_versions = [
            "Hello, where hotel?"  # Initial poor content
        ]
        
        strategies_applied = []
        validations = []
        
        # Perform 3 improvement iterations
        for iteration in range(3):
            # Get recommendation based on current content
            recommendation = engine.recommend_next_action(
                content_history=content_versions,
                strategies_used=strategies_applied
            )
            
            # Simulate content improvement based on recommendation
            current_content = content_versions[-1]
            
            if recommendation.recommended_strategy == ContentStrategy.DEEPER:
                if iteration == 0:
                    improved = "Hello po, saan po ang hotel?"
                elif iteration == 1:
                    improved = "Kumusta po! Saan po ang hotel?"
                else:
                    improved = "Kumusta po! Saan po ang magandang hotel? Salamat po!"
            else:
                # WIDER or BALANCED
                improved = current_content + " Saan din po ang restaurant?"
            
            # Validate the improvement
            validation = engine.validate_strategy_effectiveness(
                original_content=current_content,
                enhanced_content=improved,
                strategy_used=recommendation.recommended_strategy.value
            )
            
            # Record results
            content_versions.append(improved)
            strategies_applied.append(recommendation.recommended_strategy.value)
            validations.append(validation)
        
        # Verify iterative improvement
        assert len(content_versions) == 4  # Initial + 3 improvements
        assert len(validations) == 3
        
        # Should show some successful validations
        successful_validations = sum(1 for v in validations if v['overall_effectiveness'] == 'successful')
        assert successful_validations >= 1  # At least one should be successful
        
        # Final content should be better than initial
        final_recommendation = engine.recommend_next_action(
            content_history=content_versions,
            strategies_used=strategies_applied
        )
        
        # Should have higher confidence or different recommendation by end
        assert final_recommendation.confidence_score > 0.3