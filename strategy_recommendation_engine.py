"""
Strategy Recommendation Engine for TunaTale Filipino Language Learning

Provides intelligent recommendations for when to use WIDER vs DEEPER strategies
based on content quality analysis and learning progress assessment.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

from content_quality_analyzer import ContentQualityAnalyzer, QualityMetrics
from el_nido_trip_validator import ElNidoTripValidator, TripReadinessMetrics
from content_strategy import ContentStrategy

logger = logging.getLogger(__name__)


@dataclass 
class StrategyRecommendation:
    """Represents a strategy recommendation with reasoning."""
    
    recommended_strategy: ContentStrategy
    confidence_score: float  # 0-1 scale of recommendation confidence
    primary_reason: str  # Main reason for recommendation
    specific_actions: List[str]  # Specific next steps to take
    expected_improvements: List[str]  # What this strategy should improve
    alternative_strategy: Optional[ContentStrategy] = None  # Backup option
    warning_notes: List[str] = None  # Important considerations


class StrategyRecommendationEngine:
    """
    Intelligent recommendation system for content generation strategies.
    
    Analyzes current content quality and trip readiness to suggest
    the most effective strategy for next content generation.
    """
    
    def __init__(self):
        """Initialize the recommendation engine."""
        self.quality_analyzer = ContentQualityAnalyzer()
        self.trip_validator = ElNidoTripValidator()
        
        # Strategy effectiveness thresholds
        self.thresholds = {
            'high_quality': 0.8,
            'adequate_quality': 0.6,
            'filipino_authenticity': 0.7,
            'trip_readiness': 0.7,
            'vocabulary_mastery': 0.75,
            'scenario_coverage': 0.8
        }
    
    def analyze_learning_progress(self, content_history: List[str], strategies_used: List[str]) -> Dict[str, Any]:
        """
        Analyze learner's progress across different content strategies.
        
        Args:
            content_history: List of all generated content
            strategies_used: List of strategies used for each content piece
            
        Returns:
            Dictionary with progress analysis
        """
        if not content_history:
            return {
                'progress_level': 'beginner',
                'content_quality_trend': 'unknown',
                'strategy_effectiveness': {},
                'mastery_indicators': []
            }
        
        # Analyze quality progression over time
        quality_scores = []
        strategy_performance = {}
        
        for i, content in enumerate(content_history):
            strategy = strategies_used[i] if i < len(strategies_used) else 'balanced'
            
            quality = self.quality_analyzer.analyze_content_quality(content, strategy)
            quality_scores.append(quality.overall_quality_score)
            
            if strategy not in strategy_performance:
                strategy_performance[strategy] = []
            strategy_performance[strategy].append(quality.overall_quality_score)
        
        # Calculate trends
        if len(quality_scores) >= 2:
            recent_trend = quality_scores[-1] - quality_scores[-2]
            content_quality_trend = 'improving' if recent_trend > 0.05 else \
                                  'declining' if recent_trend < -0.05 else 'stable'
        else:
            content_quality_trend = 'unknown'
        
        # Determine progress level
        current_quality = quality_scores[-1] if quality_scores else 0.0
        
        if current_quality >= self.thresholds['high_quality']:
            progress_level = 'advanced'
        elif current_quality >= self.thresholds['adequate_quality']:
            progress_level = 'intermediate'
        else:
            progress_level = 'beginner'
        
        # Identify mastery indicators
        mastery_indicators = []
        latest_content = content_history[-1] if content_history else ""
        latest_quality = self.quality_analyzer.analyze_content_quality(latest_content)
        
        if latest_quality.filipino_ratio >= self.thresholds['filipino_authenticity']:
            mastery_indicators.append('strong_filipino_usage')
        
        if latest_quality.vocabulary_complexity_score >= self.thresholds['vocabulary_mastery']:
            mastery_indicators.append('vocabulary_mastery')
        
        if latest_quality.cultural_expression_count >= 5:
            mastery_indicators.append('cultural_awareness')
        
        # Calculate average performance per strategy
        strategy_effectiveness = {}
        for strategy, scores in strategy_performance.items():
            strategy_effectiveness[strategy] = {
                'average_score': sum(scores) / len(scores),
                'usage_count': len(scores),
                'trend': 'improving' if len(scores) > 1 and scores[-1] > scores[0] else 'stable'
            }
        
        return {
            'progress_level': progress_level,
            'content_quality_trend': content_quality_trend,
            'current_quality_score': current_quality,
            'strategy_effectiveness': strategy_effectiveness,
            'mastery_indicators': mastery_indicators,
            'quality_progression': quality_scores
        }
    
    def assess_content_needs(self, content_list: List[str]) -> Dict[str, Any]:
        """
        Assess what the content currently needs most.
        
        Args:
            content_list: Current curriculum content
            
        Returns:
            Dictionary with content needs assessment
        """
        # Analyze current content quality
        combined_content = ' '.join(content_list)
        current_quality = self.quality_analyzer.analyze_content_quality(combined_content)
        
        # Analyze trip readiness
        trip_readiness = self.trip_validator.calculate_trip_readiness(content_list)
        
        # Identify primary needs
        needs_assessment = {
            'filipino_authenticity_need': current_quality.filipino_ratio < self.thresholds['filipino_authenticity'],
            'vocabulary_complexity_need': current_quality.vocabulary_complexity_score < self.thresholds['vocabulary_mastery'],
            'scenario_coverage_need': trip_readiness.overall_readiness_score < self.thresholds['trip_readiness'],
            'cultural_appropriateness_need': current_quality.po_usage_score < 0.7,
            'content_expansion_need': len(content_list) < 8  # Assuming 8-day curriculum
        }
        
        # Prioritize needs
        critical_needs = []
        moderate_needs = []
        
        if needs_assessment['filipino_authenticity_need']:
            if current_quality.filipino_ratio < 0.5:
                critical_needs.append('filipino_authenticity')
            else:
                moderate_needs.append('filipino_authenticity')
        
        if needs_assessment['scenario_coverage_need']:
            if trip_readiness.overall_readiness_score < 0.5:
                critical_needs.append('scenario_coverage')
            else:
                moderate_needs.append('scenario_coverage')
        
        if needs_assessment['vocabulary_complexity_need']:
            moderate_needs.append('vocabulary_complexity')
        
        if needs_assessment['cultural_appropriateness_need']:
            moderate_needs.append('cultural_appropriateness')
        
        if needs_assessment['content_expansion_need']:
            moderate_needs.append('content_expansion')
        
        return {
            'current_quality': current_quality,
            'trip_readiness': trip_readiness,
            'needs_assessment': needs_assessment,
            'critical_needs': critical_needs,
            'moderate_needs': moderate_needs,
            'overall_priority': 'critical' if critical_needs else 'moderate' if moderate_needs else 'low'
        }
    
    def recommend_next_action(self, content_history: List[str], strategies_used: List[str], target_scenario: str = 'el_nido_trip') -> StrategyRecommendation:
        """
        Recommend the best strategy for next content generation.
        
        Args:
            content_history: All previous content generated
            strategies_used: Strategies used for each content piece
            target_scenario: Target use case (default: 'el_nido_trip')
            
        Returns:
            StrategyRecommendation with detailed guidance
        """
        # Analyze current situation
        progress = self.analyze_learning_progress(content_history, strategies_used)
        needs = self.assess_content_needs(content_history)
        
        # Default recommendation
        recommendation = StrategyRecommendation(
            recommended_strategy=ContentStrategy.BALANCED,
            confidence_score=0.5,
            primary_reason="Continue balanced progression",
            specific_actions=["Generate next lesson with balanced approach"],
            expected_improvements=["Steady progression"],
            warning_notes=[]
        )
        
        # Decision logic based on analysis
        
        # CRITICAL: Filipino authenticity too low -> DEEPER strategy
        if 'filipino_authenticity' in needs['critical_needs']:
            recommendation.recommended_strategy = ContentStrategy.DEEPER
            recommendation.confidence_score = 0.9
            recommendation.primary_reason = "Filipino authenticity critically low - need cultural enhancement"
            recommendation.specific_actions = [
                "Use DEEPER strategy to replace English with authentic Tagalog",
                "Focus on cultural expressions and natural Filipino speech patterns", 
                "Emphasize proper 'po' usage and respectful interaction patterns"
            ]
            recommendation.expected_improvements = [
                "Higher Filipino-to-English ratio",
                "More authentic cultural expressions", 
                "Better preparation for respectful interactions"
            ]
            recommendation.warning_notes = [
                "May introduce more complex vocabulary - monitor learner comprehension"
            ]
        
        # CRITICAL: Scenario coverage too low -> WIDER strategy
        elif 'scenario_coverage' in needs['critical_needs']:
            recommendation.recommended_strategy = ContentStrategy.WIDER
            recommendation.confidence_score = 0.85
            recommendation.primary_reason = "Trip scenario coverage insufficient - need practical expansion"
            recommendation.specific_actions = [
                "Use WIDER strategy to add missing scenarios (transportation, emergency, etc.)",
                "Focus on practical vocabulary for real trip situations",
                "Maintain current difficulty while expanding contexts"
            ]
            recommendation.expected_improvements = [
                "Better coverage of essential trip scenarios",
                "More practical vocabulary for real situations",
                "Increased confidence for diverse interactions"
            ]
            recommendation.alternative_strategy = ContentStrategy.BALANCED
        
        # ADVANCED learner ready for enhancement -> DEEPER strategy
        elif progress['progress_level'] == 'advanced' and 'vocabulary_mastery' in progress['mastery_indicators']:
            recommendation.recommended_strategy = ContentStrategy.DEEPER
            recommendation.confidence_score = 0.8
            recommendation.primary_reason = "Advanced proficiency detected - ready for cultural enhancement"
            recommendation.specific_actions = [
                "Use DEEPER strategy to enhance cultural authenticity",
                "Introduce more sophisticated Filipino expressions",
                "Refine cultural appropriateness and natural speech patterns"
            ]
            recommendation.expected_improvements = [
                "More native-like Filipino expression",
                "Enhanced cultural sensitivity",
                "Advanced conversation skills"
            ]
        
        # INTERMEDIATE learner with good foundation -> WIDER for variety
        elif (progress['progress_level'] == 'intermediate' and 
              progress['current_quality_score'] >= self.thresholds['adequate_quality']):
            
            # Check if they need more scenarios or already have good coverage
            if needs['trip_readiness'].overall_readiness_score < self.thresholds['scenario_coverage']:
                recommendation.recommended_strategy = ContentStrategy.WIDER
                recommendation.confidence_score = 0.75
                recommendation.primary_reason = "Good foundation established - expand practical scenarios"
                recommendation.specific_actions = [
                    "Use WIDER strategy to practice vocabulary in new contexts",
                    "Add scenarios for accommodation, activities, and problem-solving",
                    "Reinforce learned vocabulary through varied practice"
                ]
                recommendation.expected_improvements = [
                    "Better practical preparedness for trip",
                    "Vocabulary reinforcement through varied practice",
                    "Increased scenario confidence"
                ]
            else:
                # Good coverage, focus on quality enhancement
                recommendation.recommended_strategy = ContentStrategy.DEEPER
                recommendation.confidence_score = 0.7
                recommendation.primary_reason = "Good scenario coverage achieved - enhance quality and authenticity"
        
        # BEGINNER or declining quality -> BALANCED to stabilize
        elif (progress['progress_level'] == 'beginner' or 
              progress['content_quality_trend'] == 'declining'):
            
            recommendation.recommended_strategy = ContentStrategy.BALANCED
            recommendation.confidence_score = 0.8
            recommendation.primary_reason = "Build solid foundation before strategy specialization"
            recommendation.specific_actions = [
                "Continue with BALANCED strategy to establish core competencies",
                "Focus on essential vocabulary and basic interaction patterns",
                "Ensure steady quality before attempting strategy enhancements"
            ]
            recommendation.expected_improvements = [
                "Stable learning progression",
                "Solid foundation building",
                "Consistent quality improvement"
            ]
            recommendation.warning_notes = [
                "Avoid advanced strategies until foundation is stronger"
            ]
        
        # Special case: Strategy effectiveness analysis
        if 'strategy_effectiveness' in progress:
            strategy_performance = progress['strategy_effectiveness']
            
            # If DEEPER strategy has been underperforming, suggest WIDER
            if ('deeper' in strategy_performance and 
                strategy_performance['deeper']['average_score'] < self.thresholds['adequate_quality']):
                
                if recommendation.recommended_strategy == ContentStrategy.DEEPER:
                    recommendation.alternative_strategy = ContentStrategy.WIDER
                    recommendation.warning_notes.append(
                        "DEEPER strategy showed lower performance in previous attempts - consider WIDER alternative"
                    )
        
        return recommendation
    
    def validate_strategy_effectiveness(self, original_content: str, enhanced_content: str, strategy_used: str) -> Dict[str, Any]:
        """
        Validate that a strategy actually improved content quality.
        
        Args:
            original_content: Original baseline content
            enhanced_content: Strategy-enhanced content  
            strategy_used: Strategy that was applied
            
        Returns:
            Dictionary with effectiveness validation results
        """
        comparison = self.quality_analyzer.compare_strategy_outputs(
            original_content, enhanced_content, strategy_used
        )
        
        # Validate strategy-specific expectations
        effectiveness_validation = {
            'strategy_worked': comparison['strategy_effectiveness'] == 'successful',
            'improvements_measured': comparison['improvements'],
            'strategy_validation': comparison['strategy_validation'],
            'recommendation_accuracy': True  # Would be set based on prediction vs actual
        }
        
        # Generate feedback for future recommendations
        feedback = []
        
        if strategy_used.lower() == 'deeper':
            if comparison['improvements']['filipino_ratio_improvement'] > 0.1:
                feedback.append("DEEPER strategy successfully enhanced Filipino authenticity")
            else:
                feedback.append("DEEPER strategy did not significantly improve Filipino usage")
                
        elif strategy_used.lower() == 'wider':
            if comparison['enhanced_quality'].cultural_vocabulary_count >= comparison['original_quality'].cultural_vocabulary_count:
                feedback.append("WIDER strategy maintained vocabulary quality in new contexts")
            else:
                feedback.append("WIDER strategy may have diluted vocabulary effectiveness")
        
        effectiveness_validation['feedback'] = feedback
        effectiveness_validation['overall_effectiveness'] = comparison['strategy_effectiveness']
        
        return effectiveness_validation