"""
Content Quality Analyzer for TunaTale Filipino Language Learning

Validates that strategy-based content generation actually improves learning outcomes
and measures authentic Filipino language usage for real-world trip preparation.
"""

import re
import json
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Represents content quality analysis results."""
    
    # Filipino Authenticity Metrics
    filipino_ratio: float  # Ratio of Filipino to English words
    authentic_spelling_score: float  # Correct Tagalog spellings vs Spanish
    po_usage_score: float  # Natural "po" usage (not excessive)
    cultural_expression_count: int  # Number of cultural expressions used
    
    # Vocabulary Complexity Metrics  
    vocabulary_complexity_score: float  # 0-1 scale of sophistication
    collocation_complexity_score: float  # Average collocation sophistication
    cultural_vocabulary_count: int  # Context-specific vocabulary
    
    # Strategy Effectiveness Metrics
    strategy_differentiation_score: float  # How different from baseline
    learning_objective_alignment: float  # How well content matches objectives
    srs_integration_score: float  # Vocabulary constraints working correctly
    
    # Overall Quality Score
    overall_quality_score: float  # Weighted combination of all metrics


class ContentQualityAnalyzer:
    """
    Analyzes content quality for Filipino language learning effectiveness.
    
    Focuses on validating that WIDER/DEEPER strategies produce measurably 
    better content than BALANCED baseline for real-world trip preparation.
    """
    
    def __init__(self, fast_mode: bool = False):
        """Initialize the content quality analyzer.
        
        Args:
            fast_mode: If True, use simplified analysis for faster testing
        """
        self.fast_mode = fast_mode
        self.filipino_indicators = {
            # Authentic Filipino expressions (not literal English translations)
            'authentic_expressions': {
                'salamat po', 'kumusta po', 'paumanhin po', 'pakuha po',
                'pwede po ba', 'saan po', 'magkano po', 'ano po',
                'opo', 'hindi po', 'syempre', 'kasi', 'naman', 'nga',
                'talaga', 'siguro', 'baka', 'para sa', 'galing sa'
            },
            
            # Cultural context indicators
            'cultural_terms': {
                'ate', 'kuya', 'tita', 'tito', 'manang', 'manong',
                'cr', 'palikuran', 'tubig', 'kanin', 'ulam', 'merienda',
                'barkada', 'pasalip', 'balot', 'tsinelas', 'jeepney',
                'tricycle', 'banca', 'sari-sari', 'karinderya'
            },
            
            # Proper Tagalog spellings (not Spanish)
            'correct_spellings': {
                'asukal': 'azúcar',  # sugar
                'porke': 'porque',   # because
                'syempre': 'siempre', # of course
                'tinapay': 'pan',    # bread
                'kendi': 'dulce',    # candy
                'sapatos': 'zapatos', # shoes
                'bintana': 'ventana', # window
                'silya': 'silla',    # chair
                'lamesa': 'mesa'     # table
            }
        }
        
        # El Nido trip-specific vocabulary for practical validation
        self.el_nido_vocabulary = {
            'accommodation': {
                'kwarto', 'hotel', 'resort', 'check-in', 'check-out',
                'reservation', 'bayad', 'resibo', 'towel', 'kumot'
            },
            'transportation': {
                'tricycle', 'jeepney', 'banca', 'island hopping',
                'driver', 'bayad', 'magkano', 'saan', 'dito', 'doon'
            },
            'restaurant': {
                'pagkain', 'inumin', 'kanin', 'isda', 'hipon', 'baboy',
                'manok', 'gulay', 'prutas', 'tubig', 'softdrinks', 'bir'
            },
            'activities': {
                'swimming', 'snorkeling', 'diving', 'beach', 'dagat',
                'buhangin', 'araw', 'picture', 'photo', 'maganda'
            },
            'emergency': {
                'tulong', 'hospital', 'doktor', 'gamot', 'masakit',
                'nasaan', 'emergency', 'tawag', 'police', 'pasyente'
            }
        }
        
    def analyze_filipino_authenticity(self, content: str) -> Dict[str, float]:
        """
        Analyze how authentically Filipino the content is.
        
        Args:
            content: Story content to analyze
            
        Returns:
            Dictionary with authenticity metrics
        """
        content_lower = content.lower()
        
        # Fast mode: simplified analysis
        if self.fast_mode:
            filipino_indicators = ['kumusta', 'po', 'salamat', 'saan', 'ako', 'gusto']
            filipino_count = sum(1 for word in filipino_indicators if word in content_lower)
            
            return {
                'filipino_ratio': min(1.0, filipino_count / 5.0),  # Normalize to 0-1
                'authentic_spelling_score': 0.8 if filipino_count > 2 else 0.4,
                'po_usage_score': 0.7 if 'po' in content_lower else 0.2,
                'cultural_expression_count': filipino_count
            }
        
        words = re.findall(r'\b\w+\b', content_lower)
        total_words = len(words)
        
        if total_words == 0:
            return {
                'filipino_ratio': 0.0,
                'authentic_spelling_score': 0.0,
                'po_usage_score': 0.0,
                'cultural_expression_count': 0
            }
        
        # Calculate Filipino vs English ratio
        filipino_words = 0
        english_words = 0
        
        for word in words:
            if word in self.filipino_indicators['authentic_expressions']:
                filipino_words += 1
            elif word in self.filipino_indicators['cultural_terms']:
                filipino_words += 1
            elif len(word) > 2 and word.isalpha():
                # Simple heuristic: Filipino words often end in vowels
                if word.endswith(('a', 'o', 'i', 'e', 'u', 'ng', 'an', 'in')):
                    filipino_words += 1
                else:
                    english_words += 1
        
        filipino_ratio = filipino_words / max(1, filipino_words + english_words)
        
        # Score authentic Tagalog spellings vs Spanish
        authentic_spellings = 0
        total_spelling_opportunities = 0
        
        for correct, incorrect in self.filipino_indicators['correct_spellings'].items():
            if correct in content_lower:
                authentic_spellings += 1
            if incorrect.lower() in content_lower:
                total_spelling_opportunities += 1
        
        authentic_spelling_score = (
            authentic_spellings / max(1, total_spelling_opportunities) 
            if total_spelling_opportunities > 0 else 1.0
        )
        
        # Analyze "po" usage (should be natural, not excessive)
        po_count = content_lower.count(' po ')
        po_sentences = content.count('.')
        po_usage_ratio = po_count / max(1, po_sentences)
        
        # Natural "po" usage is roughly 0.3-0.7 per sentence in formal contexts
        if 0.2 <= po_usage_ratio <= 0.8:
            po_usage_score = 1.0
        elif po_usage_ratio < 0.2:
            po_usage_score = po_usage_ratio / 0.2  # Too little
        else:
            po_usage_score = 0.8 / po_usage_ratio  # Too much
        
        # Count cultural expressions
        cultural_expression_count = sum(
            1 for expr in self.filipino_indicators['authentic_expressions']
            if expr in content_lower
        )
        
        return {
            'filipino_ratio': filipino_ratio,
            'authentic_spelling_score': authentic_spelling_score,
            'po_usage_score': min(1.0, po_usage_score),
            'cultural_expression_count': cultural_expression_count
        }
    
    def analyze_vocabulary_complexity(self, content: str) -> Dict[str, float]:
        """
        Analyze vocabulary sophistication and complexity progression.
        
        Args:
            content: Story content to analyze
            
        Returns:
            Dictionary with complexity metrics
        """
        # Extract collocations (3-5 word phrases)
        collocation_patterns = re.findall(r'\b\w+\s+\w+\s+\w+(?:\s+\w+)?(?:\s+\w+)?\b', content.lower())
        
        # Score vocabulary complexity based on length and cultural context
        words = re.findall(r'\b\w+\b', content.lower())
        
        complexity_score = 0
        cultural_vocabulary_count = 0
        
        for word in words:
            # Longer words tend to be more sophisticated
            if len(word) > 6:
                complexity_score += 0.3
            elif len(word) > 4:
                complexity_score += 0.1
                
            # Cultural/contextual vocabulary scores higher
            if any(word in category for category in self.el_nido_vocabulary.values()):
                cultural_vocabulary_count += 1
                complexity_score += 0.2
        
        vocabulary_complexity_score = min(1.0, complexity_score / max(1, len(words)))
        
        # Score collocation complexity
        collocation_complexity = 0
        for collocation in collocation_patterns:
            words_in_collocation = len(collocation.split())
            if words_in_collocation >= 4:
                collocation_complexity += 0.3
            elif words_in_collocation >= 3:
                collocation_complexity += 0.2
            else:
                collocation_complexity += 0.1
        
        collocation_complexity_score = min(1.0, collocation_complexity / max(1, len(collocation_patterns)))
        
        return {
            'vocabulary_complexity_score': vocabulary_complexity_score,
            'collocation_complexity_score': collocation_complexity_score,
            'cultural_vocabulary_count': cultural_vocabulary_count
        }
    
    def analyze_strategy_effectiveness(self, content: str, strategy: str, baseline_content: Optional[str] = None) -> Dict[str, float]:
        """
        Measure how effectively a strategy differentiates from baseline content.
        
        Args:
            content: Strategy-enhanced content
            strategy: Strategy type ('wider', 'deeper', 'balanced') 
            baseline_content: Optional baseline content for comparison
            
        Returns:
            Dictionary with strategy effectiveness metrics
        """
        if baseline_content:
            # Compare against baseline
            baseline_auth = self.analyze_filipino_authenticity(baseline_content)
            content_auth = self.analyze_filipino_authenticity(content)
            
            # Measure improvement over baseline
            filipino_improvement = content_auth['filipino_ratio'] - baseline_auth['filipino_ratio']
            spelling_improvement = content_auth['authentic_spelling_score'] - baseline_auth['authentic_spelling_score']
            
            strategy_differentiation_score = min(1.0, max(0.0, (filipino_improvement + spelling_improvement) / 2))
        else:
            # Score based on strategy expectations
            auth_metrics = self.analyze_filipino_authenticity(content)
            
            if strategy.lower() == 'deeper':
                # DEEPER should have high Filipino authenticity
                strategy_differentiation_score = auth_metrics['filipino_ratio']
            elif strategy.lower() == 'wider':
                # WIDER should maintain consistency while expanding contexts
                strategy_differentiation_score = min(auth_metrics['filipino_ratio'], 0.8)
            else:
                # BALANCED baseline
                strategy_differentiation_score = auth_metrics['filipino_ratio']
        
        # Analyze learning objective alignment (simple keyword matching)
        learning_objectives = ['restaurant', 'food', 'travel', 'accommodation', 'transportation']
        objective_matches = sum(1 for obj in learning_objectives if obj in content.lower())
        learning_objective_alignment = min(1.0, objective_matches / len(learning_objectives))
        
        # Score SRS integration (vocabulary constraint compliance)
        # This is a simplified check for now
        srs_integration_score = 0.8  # Default good score, could be enhanced with actual SRS data
        
        return {
            'strategy_differentiation_score': strategy_differentiation_score,
            'learning_objective_alignment': learning_objective_alignment,
            'srs_integration_score': srs_integration_score
        }
    
    def analyze_content_quality(self, content: str, strategy: str = 'balanced', baseline_content: Optional[str] = None) -> QualityMetrics:
        """
        Perform comprehensive content quality analysis.
        
        Args:
            content: Story content to analyze
            strategy: Content generation strategy used
            baseline_content: Optional baseline for comparison
            
        Returns:
            QualityMetrics object with all analysis results
        """
        # Perform all analyses
        auth_metrics = self.analyze_filipino_authenticity(content)
        vocab_metrics = self.analyze_vocabulary_complexity(content)
        strategy_metrics = self.analyze_strategy_effectiveness(content, strategy, baseline_content)
        
        # Calculate overall quality score (weighted combination)
        overall_quality_score = (
            auth_metrics['filipino_ratio'] * 0.25 +
            auth_metrics['authentic_spelling_score'] * 0.15 +
            auth_metrics['po_usage_score'] * 0.10 +
            vocab_metrics['vocabulary_complexity_score'] * 0.20 +
            vocab_metrics['collocation_complexity_score'] * 0.15 +
            strategy_metrics['strategy_differentiation_score'] * 0.15
        )
        
        return QualityMetrics(
            filipino_ratio=auth_metrics['filipino_ratio'],
            authentic_spelling_score=auth_metrics['authentic_spelling_score'],
            po_usage_score=auth_metrics['po_usage_score'],
            cultural_expression_count=auth_metrics['cultural_expression_count'],
            vocabulary_complexity_score=vocab_metrics['vocabulary_complexity_score'],
            collocation_complexity_score=vocab_metrics['collocation_complexity_score'],
            cultural_vocabulary_count=vocab_metrics['cultural_vocabulary_count'],
            strategy_differentiation_score=strategy_metrics['strategy_differentiation_score'],
            learning_objective_alignment=strategy_metrics['learning_objective_alignment'],
            srs_integration_score=strategy_metrics['srs_integration_score'],
            overall_quality_score=overall_quality_score
        )
    
    def compare_strategy_outputs(self, original_content: str, enhanced_content: str, strategy: str) -> Dict[str, Any]:
        """
        Compare original vs strategy-enhanced content to validate improvements.
        
        Args:
            original_content: Baseline BALANCED content
            enhanced_content: WIDER or DEEPER strategy content
            strategy: Strategy type used for enhancement
            
        Returns:
            Dictionary with detailed comparison metrics
        """
        original_quality = self.analyze_content_quality(original_content, 'balanced')
        enhanced_quality = self.analyze_content_quality(enhanced_content, strategy, original_content)
        
        improvements = {
            'filipino_ratio_improvement': enhanced_quality.filipino_ratio - original_quality.filipino_ratio,
            'spelling_improvement': enhanced_quality.authentic_spelling_score - original_quality.authentic_spelling_score,
            'vocabulary_complexity_improvement': enhanced_quality.vocabulary_complexity_score - original_quality.vocabulary_complexity_score,
            'overall_improvement': enhanced_quality.overall_quality_score - original_quality.overall_quality_score
        }
        
        # Strategy-specific validation
        strategy_validation = {}
        
        if strategy.lower() == 'deeper':
            # DEEPER should improve Filipino authenticity significantly
            strategy_validation['authentic_enhancement'] = improvements['filipino_ratio_improvement'] > 0.1
            strategy_validation['cultural_depth'] = enhanced_quality.cultural_expression_count > original_quality.cultural_expression_count
            
        elif strategy.lower() == 'wider':
            # WIDER should maintain quality while expanding contexts
            strategy_validation['quality_maintained'] = enhanced_quality.overall_quality_score >= original_quality.overall_quality_score * 0.9
            strategy_validation['vocabulary_reinforced'] = enhanced_quality.cultural_vocabulary_count >= original_quality.cultural_vocabulary_count
        
        return {
            'original_quality': original_quality,
            'enhanced_quality': enhanced_quality,
            'improvements': improvements,
            'strategy_validation': strategy_validation,
            'strategy_effectiveness': 'successful' if sum(improvements.values()) > 0 else 'needs_improvement'
        }