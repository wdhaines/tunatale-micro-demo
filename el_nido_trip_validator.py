"""
El Nido Trip Validator for TunaTale Filipino Language Learning

Validates that generated content covers essential scenarios and vocabulary
needed for a successful trip to El Nido, Philippines.
"""

import re
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class TripReadinessMetrics:
    """Represents trip preparation analysis results."""
    
    # Scenario Coverage
    accommodation_coverage: float  # Hotel/resort interactions
    transportation_coverage: float  # Tricycle, banca, directions
    restaurant_coverage: float  # Food ordering, dietary needs
    activity_coverage: float  # Beach, island hopping, tourism
    emergency_coverage: float  # Problems, help, medical
    
    # Vocabulary Completeness
    essential_vocabulary_percentage: float  # Core trip vocabulary present
    cultural_vocabulary_percentage: float  # Respectful interaction terms
    practical_vocabulary_percentage: float  # Problem-solving words
    
    # Cultural Appropriateness  
    respectful_interaction_score: float  # Appropriate formality levels
    social_boundary_awareness: float  # Cultural sensitivity
    authentic_goodbye_patterns: float  # Natural Filipino farewells
    
    # Overall Trip Readiness
    overall_readiness_score: float  # Weighted combination
    identified_gaps: List[str]  # Specific areas needing improvement


class ElNidoTripValidator:
    """
    Validates content for real-world El Nido trip preparation.
    
    Ensures generated lessons cover practical scenarios a traveler
    will encounter and teaches culturally appropriate interactions.
    """
    
    def __init__(self):
        """Initialize with comprehensive El Nido trip scenarios and vocabulary."""
        
        # Essential trip scenarios with required vocabulary
        self.trip_scenarios = {
            'accommodation': {
                'scenarios': [
                    'hotel check-in', 'room requests', 'problem reporting', 
                    'check-out process', 'payment issues', 'amenity requests'
                ],
                'essential_phrases': {
                    'may reservation ako', 'check-in po', 'check-out po',
                    'saan ang kwarto', 'may problema', 'tulong po',
                    'magkano', 'bayad', 'resibo po', 'salamat po'
                },
                'vocabulary': {
                    'kwarto', 'hotel', 'resort', 'reservation', 'check-in',
                    'check-out', 'bayad', 'resibo', 'towel', 'kumot',
                    'aircon', 'banyo', 'shower', 'wifi', 'breakfast'
                }
            },
            
            'transportation': {
                'scenarios': [
                    'tricycle negotiation', 'direction asking', 'fare payment',
                    'banca booking', 'island hopping arrangement', 'schedule inquiry'
                ],
                'essential_phrases': {
                    'saan po', 'magkano ang pamasahe', 'pwede po ba',
                    'dito po', 'doon po', 'sakay po', 'baba po',
                    'island hopping po', 'anong oras', 'bukas po'
                },
                'vocabulary': {
                    'tricycle', 'jeepney', 'banca', 'driver', 'pamasahe',
                    'island hopping', 'schedule', 'oras', 'aalis', 'babalik',
                    'puerto', 'pantalan', 'pier', 'sakay', 'baba'
                }
            },
            
            'restaurant': {
                'scenarios': [
                    'menu reading', 'food ordering', 'dietary restrictions',
                    'bill payment', 'recommendation asking', 'complaint handling'
                ],
                'essential_phrases': {
                    'ano ang masarap', 'pwede makita menu', 'order po',
                    'walang baboy', 'allergic ako sa', 'bill po',
                    'magkano lahat', 'masarap po', 'salamat po'
                },
                'vocabulary': {
                    'pagkain', 'inumin', 'menu', 'order', 'kanin', 'isda',
                    'hipon', 'baboy', 'manok', 'gulay', 'prutas', 'tubig',
                    'juice', 'bill', 'bayad', 'tip', 'masarap', 'matamis'
                }
            },
            
            'activities': {
                'scenarios': [
                    'beach activities', 'snorkeling arrangement', 'photo requests',
                    'tour booking', 'equipment rental', 'safety concerns'
                ],
                'essential_phrases': {
                    'swimming po', 'snorkeling po', 'picture po',
                    'maganda dito', 'safe ba', 'rent po',
                    'tour po', 'anong oras', 'magkano po'
                },
                'vocabulary': {
                    'swimming', 'snorkeling', 'diving', 'beach', 'dagat',
                    'buhangin', 'araw', 'picture', 'photo', 'camera',
                    'tour', 'guide', 'rent', 'equipment', 'safe', 'ingat'
                }
            },
            
            'emergency': {
                'scenarios': [
                    'medical emergency', 'lost items', 'police assistance',
                    'hospital visit', 'pharmacy needs', 'help seeking'
                ],
                'essential_phrases': {
                    'tulong po', 'emergency po', 'hospital po',
                    'may sakit', 'masakit', 'gamot po',
                    'nawala', 'police po', 'tawag po'
                },
                'vocabulary': {
                    'tulong', 'emergency', 'hospital', 'doktor', 'nurse',
                    'gamot', 'pharmacy', 'masakit', 'sakit', 'sugat',
                    'police', 'pulis', 'tawag', 'telepono', 'nawala'
                }
            }
        }
        
        # Cultural appropriateness indicators
        self.cultural_patterns = {
            'respectful_greetings': {
                'kumusta po', 'magandang umaga po', 'magandang hapon po',
                'magandang gabi po', 'salamat po', 'walang anuman po'
            },
            
            'polite_requests': {
                'pwede po ba', 'maaari po ba', 'pakuha po', 'paki po',
                'paumanhin po', 'excuse me po', 'pasensya na po'
            },
            
            'appropriate_farewells': {
                'salamat po', 'ingat po', 'paalam po', 'see you po',
                'balik po kayo', 'maraming salamat po'
            },
            
            'social_awareness': {
                'po', 'opo', 'hindi po', 'tama po', 'sige po',
                'pakisuyo po', 'pasensya po', 'sorry po'
            }
        }
        
        # Vocabulary gaps that commonly cause problems
        self.common_gaps = {
            'basic_needs': ['tubig', 'banyo', 'cr', 'kain', 'tulog'],
            'directions': ['saan', 'nasaan', 'dito', 'doon', 'tawid', 'kaliwa', 'kanan'],
            'numbers': ['isa', 'dalawa', 'tatlo', 'apat', 'lima', 'sampu', 'bente'],
            'time': ['anong oras', 'kailan', 'ngayon', 'bukas', 'kahapon'],
            'problems': ['problema', 'ayaw gumana', 'sira', 'walang', 'ubos']
        }
    
    def validate_scenario_coverage(self, content_list: List[str]) -> Dict[str, float]:
        """
        Analyze how well content covers essential El Nido trip scenarios.
        
        Args:
            content_list: List of lesson content to analyze
            
        Returns:
            Dictionary with coverage percentages for each scenario category
        """
        combined_content = ' '.join(content_list).lower()
        coverage_scores = {}
        
        for category, scenario_data in self.trip_scenarios.items():
            scenarios_covered = 0
            total_scenarios = len(scenario_data['scenarios'])
            
            for scenario in scenario_data['scenarios']:
                # Check if scenario is covered by looking for key terms
                scenario_terms = scenario.replace('-', ' ').split()
                terms_found = sum(1 for term in scenario_terms if term in combined_content)
                
                # Scenario is "covered" if at least 50% of its key terms appear
                if terms_found >= len(scenario_terms) * 0.5:
                    scenarios_covered += 1
            
            coverage_scores[category] = scenarios_covered / total_scenarios if total_scenarios > 0 else 0.0
        
        return {
            'accommodation_coverage': coverage_scores.get('accommodation', 0.0),
            'transportation_coverage': coverage_scores.get('transportation', 0.0),
            'restaurant_coverage': coverage_scores.get('restaurant', 0.0),
            'activity_coverage': coverage_scores.get('activities', 0.0),
            'emergency_coverage': coverage_scores.get('emergency', 0.0)
        }
    
    def identify_vocabulary_gaps(self, content_list: List[str]) -> Dict[str, List[str]]:
        """
        Identify missing essential vocabulary for trip scenarios.
        
        Args:
            content_list: List of lesson content to analyze
            
        Returns:
            Dictionary mapping scenario categories to missing vocabulary
        """
        combined_content = ' '.join(content_list).lower()
        vocabulary_gaps = {}
        
        for category, scenario_data in self.trip_scenarios.items():
            missing_vocab = []
            essential_vocab = scenario_data['vocabulary']
            
            for vocab_word in essential_vocab:
                if vocab_word.lower() not in combined_content:
                    missing_vocab.append(vocab_word)
            
            if missing_vocab:
                vocabulary_gaps[category] = missing_vocab
        
        # Check common problem areas
        for gap_category, vocab_list in self.common_gaps.items():
            missing_basic = [word for word in vocab_list if word not in combined_content]
            if missing_basic:
                vocabulary_gaps[f'basic_{gap_category}'] = missing_basic
        
        return vocabulary_gaps
    
    def score_cultural_appropriateness(self, content: str) -> Dict[str, float]:
        """
        Score how culturally appropriate and respectful the content is.
        
        Args:
            content: Content to analyze
            
        Returns:
            Dictionary with cultural appropriateness scores
        """
        content_lower = content.lower()
        
        # Score respectful interactions
        respectful_patterns = 0
        total_interactions = content.count('?') + content.count('.')  # Rough interaction count
        
        for pattern_category, patterns in self.cultural_patterns.items():
            patterns_found = sum(1 for pattern in patterns if pattern in content_lower)
            respectful_patterns += patterns_found
        
        respectful_interaction_score = min(1.0, respectful_patterns / max(1, total_interactions))
        
        # Analyze "po" usage appropriateness (should be consistent but not excessive)
        po_count = content_lower.count(' po')
        sentences = content.count('.') + content.count('?') + content.count('!')
        
        if sentences > 0:
            po_ratio = po_count / sentences
            # Appropriate range for tourist interactions: 0.4-0.8 per sentence
            if 0.4 <= po_ratio <= 0.8:
                social_boundary_awareness = 1.0
            elif po_ratio < 0.4:
                social_boundary_awareness = po_ratio / 0.4  # Too casual
            else:
                social_boundary_awareness = 0.8 / po_ratio  # Too formal
        else:
            social_boundary_awareness = 0.5
        
        # Score farewell patterns (should be natural, not Western)
        farewell_score = 0
        farewells_found = sum(1 for farewell in self.cultural_patterns['appropriate_farewells'] 
                            if farewell in content_lower)
        
        # Penalize Western farewells in Filipino content
        western_farewells = ['goodbye', 'bye bye', 'see ya', 'later']
        western_found = sum(1 for farewell in western_farewells if farewell in content_lower)
        
        if farewells_found > 0:
            authentic_goodbye_patterns = max(0.0, 1.0 - (western_found / farewells_found))
        else:
            authentic_goodbye_patterns = 0.5  # Neutral if no farewells
        
        return {
            'respectful_interaction_score': respectful_interaction_score,
            'social_boundary_awareness': min(1.0, social_boundary_awareness),
            'authentic_goodbye_patterns': authentic_goodbye_patterns
        }
    
    def calculate_trip_readiness(self, content_list: List[str]) -> TripReadinessMetrics:
        """
        Calculate comprehensive trip readiness score.
        
        Args:
            content_list: List of all lesson content
            
        Returns:
            TripReadinessMetrics with detailed analysis
        """
        # Analyze scenario coverage
        coverage = self.validate_scenario_coverage(content_list)
        
        # Analyze vocabulary completeness
        gaps = self.identify_vocabulary_gaps(content_list)
        total_essential_vocab = sum(len(data['vocabulary']) for data in self.trip_scenarios.values())
        missing_vocab_count = sum(len(gap_list) for gap_list in gaps.values())
        
        essential_vocabulary_percentage = 1.0 - (missing_vocab_count / max(1, total_essential_vocab))
        
        # Count cultural and practical vocabulary
        combined_content = ' '.join(content_list).lower()
        
        cultural_vocab_found = sum(
            1 for patterns in self.cultural_patterns.values()
            for pattern in patterns if pattern in combined_content
        )
        total_cultural_vocab = sum(len(patterns) for patterns in self.cultural_patterns.values())
        cultural_vocabulary_percentage = cultural_vocab_found / max(1, total_cultural_vocab)
        
        practical_vocab_found = sum(
            1 for vocab_list in self.common_gaps.values()
            for vocab in vocab_list if vocab in combined_content
        )
        total_practical_vocab = sum(len(vocab_list) for vocab_list in self.common_gaps.values())
        practical_vocabulary_percentage = practical_vocab_found / max(1, total_practical_vocab)
        
        # Score cultural appropriateness
        cultural_scores = self.score_cultural_appropriateness(' '.join(content_list))
        
        # Calculate overall readiness score (weighted)
        overall_readiness_score = (
            coverage['accommodation_coverage'] * 0.15 +
            coverage['transportation_coverage'] * 0.20 +
            coverage['restaurant_coverage'] * 0.25 +
            coverage['activity_coverage'] * 0.15 +
            coverage['emergency_coverage'] * 0.10 +
            essential_vocabulary_percentage * 0.15
        )
        
        # Identify specific improvement areas
        identified_gaps = []
        
        for category, score in coverage.items():
            if score < 0.7:  # Less than 70% coverage
                identified_gaps.append(f"Low {category.replace('_coverage', '')} scenario coverage ({score:.1%})")
        
        for gap_category, missing_words in gaps.items():
            if len(missing_words) > 3:  # More than 3 missing words
                identified_gaps.append(f"Missing {gap_category} vocabulary: {', '.join(missing_words[:3])}...")
        
        return TripReadinessMetrics(
            accommodation_coverage=coverage['accommodation_coverage'],
            transportation_coverage=coverage['transportation_coverage'],
            restaurant_coverage=coverage['restaurant_coverage'],
            activity_coverage=coverage['activity_coverage'],
            emergency_coverage=coverage['emergency_coverage'],
            essential_vocabulary_percentage=essential_vocabulary_percentage,
            cultural_vocabulary_percentage=cultural_vocabulary_percentage,
            practical_vocabulary_percentage=practical_vocabulary_percentage,
            respectful_interaction_score=cultural_scores['respectful_interaction_score'],
            social_boundary_awareness=cultural_scores['social_boundary_awareness'],
            authentic_goodbye_patterns=cultural_scores['authentic_goodbye_patterns'],
            overall_readiness_score=overall_readiness_score,
            identified_gaps=identified_gaps
        )
    
    def validate_content_for_trip(self, content_list: List[str], trip_days: int = 5) -> Dict[str, Any]:
        """
        Comprehensive validation of content for El Nido trip preparation.
        
        Args:
            content_list: All lesson content to validate
            trip_days: Expected trip duration
            
        Returns:
            Dictionary with comprehensive validation results
        """
        readiness_metrics = self.calculate_trip_readiness(content_list)
        
        # Trip-specific recommendations
        recommendations = []
        
        if readiness_metrics.overall_readiness_score < 0.7:
            recommendations.append("Content needs significant improvement for trip readiness")
        
        if readiness_metrics.transportation_coverage < 0.8:
            recommendations.append("Add more transportation scenarios (tricycle, banca navigation)")
        
        if readiness_metrics.restaurant_coverage < 0.8:
            recommendations.append("Include more dining scenarios (ordering, dietary restrictions)")
        
        if readiness_metrics.emergency_coverage < 0.6:
            recommendations.append("Add basic emergency and problem-solving vocabulary")
        
        if readiness_metrics.respectful_interaction_score < 0.7:
            recommendations.append("Improve cultural appropriateness (respectful greetings, 'po' usage)")
        
        # Success assessment
        trip_readiness_level = 'excellent' if readiness_metrics.overall_readiness_score >= 0.9 else \
                             'good' if readiness_metrics.overall_readiness_score >= 0.7 else \
                             'adequate' if readiness_metrics.overall_readiness_score >= 0.5 else \
                             'needs_improvement'
        
        return {
            'readiness_metrics': readiness_metrics,
            'trip_readiness_level': trip_readiness_level,
            'recommendations': recommendations,
            'readiness_percentage': readiness_metrics.overall_readiness_score * 100,
            'critical_gaps': [gap for gap in readiness_metrics.identified_gaps if 'Low' in gap or 'Missing' in gap],
            'cultural_appropriateness': 'appropriate' if readiness_metrics.respectful_interaction_score >= 0.7 else 'needs_improvement'
        }