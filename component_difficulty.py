#!/usr/bin/env python3
"""
Component-based difficulty calculation for Filipino collocations.

This module provides functionality to calculate collocation difficulty based on
the frequency of component words, allowing collocations made of common words
to be considered easier to learn even if the complete phrase is rare.
"""

import json
import re
import math
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ComponentDifficultyConfig:
    """Configuration for component-based difficulty calculation."""
    
    # Frequency scoring parameters
    min_frequency_score: float = 0.1  # Minimum score for unknown words
    max_frequency_score: float = 1.0  # Maximum score for very common words
    frequency_threshold: int = 10     # Frequency above which words are considered "common"
    
    # Component combination method
    combination_method: str = "geometric_mean"  # "arithmetic_mean", "geometric_mean", "minimum"
    
    # Smoothing parameters
    smoothing_factor: float = 1.0     # Laplace smoothing for unseen words
    log_smoothing: bool = True        # Apply log smoothing to frequency scores
    
    # Length-based adjustments
    length_penalty: float = 0.1       # Penalty per additional word in collocation
    min_length_bonus: float = 0.0     # Bonus for short collocations
    
    # Phrase frequency bonus
    phrase_frequency_weight: float = 0.3  # Weight for phrase-level frequency


class ComponentDifficultyCalculator:
    """Calculate collocation difficulty based on component word frequencies."""
    
    def __init__(self, frequency_db_path: str = "instance/data/word_frequency.json", 
                 config: Optional[ComponentDifficultyConfig] = None):
        """Initialize with word frequency database."""
        self.config = config or ComponentDifficultyConfig()
        self.word_frequencies = {}
        self.phrase_frequencies = {}
        self.total_words = 0
        self.total_phrases = 0
        
        self.load_frequency_database(frequency_db_path)
    
    def load_frequency_database(self, db_path: str):
        """Load word frequency database from JSON file."""
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.word_frequencies = data.get('word_frequencies', {})
            self.phrase_frequencies = data.get('phrase_frequencies', {})
            self.total_words = data.get('total_words', 0)
            self.total_phrases = data.get('total_phrases', 0)
            
            logger.info(f"Loaded frequency database: {len(self.word_frequencies)} words, "
                       f"{len(self.phrase_frequencies)} phrases")
            
        except Exception as e:
            logger.error(f"Failed to load frequency database from {db_path}: {e}")
            # Initialize empty database
            self.word_frequencies = {}
            self.phrase_frequencies = {}
            self.total_words = 1  # Avoid division by zero
            self.total_phrases = 1
    
    def get_word_frequency_score(self, word: str) -> float:
        """
        Calculate frequency score for a single word.
        
        Returns score from 0.0 to 1.0 where higher scores indicate more frequent words.
        """
        word = word.lower().strip()
        
        # Remove punctuation
        word = re.sub(r'[^\w\s]', '', word)
        
        if not word:
            return self.config.min_frequency_score
        
        # Get raw frequency
        frequency = self.word_frequencies.get(word, 0)
        
        # Apply smoothing
        if frequency == 0:
            frequency = self.config.smoothing_factor
        
        # Normalize by total words
        normalized_freq = frequency / self.total_words
        
        # Apply log smoothing if enabled
        if self.config.log_smoothing:
            # Use log scale to handle wide frequency ranges
            score = math.log(frequency + 1) / math.log(self.config.frequency_threshold + 1)
        else:
            # Linear scaling
            score = frequency / self.config.frequency_threshold
        
        # Clamp to valid range
        score = max(self.config.min_frequency_score, 
                   min(self.config.max_frequency_score, score))
        
        return score
    
    def get_phrase_frequency_score(self, phrase: str) -> float:
        """Calculate frequency score for the complete phrase."""
        phrase = phrase.strip()
        frequency = self.phrase_frequencies.get(phrase, 0)
        
        if frequency == 0:
            return self.config.min_frequency_score
        
        # Normalize and apply log smoothing
        if self.config.log_smoothing:
            score = math.log(frequency + 1) / math.log(10 + 1)  # Assume phrases are less frequent
        else:
            score = frequency / 10  # Assume max phrase frequency around 10
        
        return max(self.config.min_frequency_score, 
                  min(self.config.max_frequency_score, score))
    
    def calculate_component_scores(self, collocation: str) -> List[Tuple[str, float]]:
        """Calculate frequency scores for each component word."""
        words = collocation.lower().split()
        component_scores = []
        
        for word in words:
            word = word.strip()
            if word:
                score = self.get_word_frequency_score(word)
                component_scores.append((word, score))
        
        return component_scores
    
    def combine_component_scores(self, component_scores: List[Tuple[str, float]]) -> float:
        """Combine individual component scores into a single collocation score."""
        if not component_scores:
            return self.config.min_frequency_score
        
        scores = [score for word, score in component_scores]
        
        if self.config.combination_method == "arithmetic_mean":
            combined = sum(scores) / len(scores)
        elif self.config.combination_method == "geometric_mean":
            # Geometric mean is more conservative - one difficult word lowers the whole score
            product = 1.0
            for score in scores:
                product *= score
            combined = product ** (1.0 / len(scores))
        elif self.config.combination_method == "minimum":
            # Most conservative - limited by the most difficult word
            combined = min(scores)
        else:
            # Default to arithmetic mean
            combined = sum(scores) / len(scores)
        
        return combined
    
    def apply_length_adjustment(self, base_score: float, word_count: int) -> float:
        """Apply length-based adjustments to the base score."""
        if word_count <= 1:
            # Single words or empty get minimum bonus
            adjustment = self.config.min_length_bonus
        else:
            # Longer phrases get penalty
            adjustment = -(word_count - 1) * self.config.length_penalty
        
        adjusted_score = base_score + adjustment
        
        # Clamp to valid range
        return max(self.config.min_frequency_score, 
                  min(self.config.max_frequency_score, adjusted_score))
    
    def calculate_difficulty_score(self, collocation: str) -> float:
        """
        Calculate overall difficulty score for a collocation.
        
        Higher scores indicate easier collocations (more frequent component words).
        Lower scores indicate harder collocations (less frequent component words).
        
        Returns score from 0.0 to 1.0.
        """
        if not collocation or not collocation.strip():
            return self.config.min_frequency_score
        
        # Calculate component word scores
        component_scores = self.calculate_component_scores(collocation)
        
        # Combine component scores
        component_score = self.combine_component_scores(component_scores)
        
        # Get phrase-level frequency score
        phrase_score = self.get_phrase_frequency_score(collocation)
        
        # Combine component and phrase scores
        combined_score = (
            (1 - self.config.phrase_frequency_weight) * component_score +
            self.config.phrase_frequency_weight * phrase_score
        )
        
        # Apply length adjustments
        word_count = len(collocation.split())
        final_score = self.apply_length_adjustment(combined_score, word_count)
        
        return final_score
    
    def calculate_stability_from_difficulty(self, difficulty_score: float) -> float:
        """
        Convert difficulty score to SRS stability value.
        
        Higher difficulty scores (easier words) -> higher stability (learned faster)
        Lower difficulty scores (harder words) -> lower stability (need more practice)
        """
        # Map difficulty score (0-1) to stability range (0.1-3.0)
        # Easy collocations start with higher stability
        min_stability = 0.1
        max_stability = 3.0
        
        stability = min_stability + (max_stability - min_stability) * difficulty_score
        
        return round(stability, 2)
    
    def analyze_collocation(self, collocation: str) -> Dict:
        """
        Provide detailed analysis of a collocation's difficulty.
        
        Returns dictionary with component analysis, scores, and recommendations.
        """
        component_scores = self.calculate_component_scores(collocation)
        difficulty_score = self.calculate_difficulty_score(collocation)
        stability = self.calculate_stability_from_difficulty(difficulty_score)
        phrase_score = self.get_phrase_frequency_score(collocation)
        
        # Analyze component breakdown
        word_analysis = []
        for word, score in component_scores:
            frequency = self.word_frequencies.get(word, 0)
            word_analysis.append({
                'word': word,
                'frequency': frequency,
                'score': round(score, 3),
                'category': self._categorize_word_difficulty(score)
            })
        
        return {
            'collocation': collocation,
            'difficulty_score': round(difficulty_score, 3),
            'stability': stability,
            'phrase_frequency': self.phrase_frequencies.get(collocation, 0),
            'phrase_score': round(phrase_score, 3),
            'word_count': len(collocation.split()),
            'component_analysis': word_analysis,
            'difficulty_category': self._categorize_collocation_difficulty(difficulty_score),
            'learning_recommendation': self._get_learning_recommendation(difficulty_score)
        }
    
    def _categorize_word_difficulty(self, score: float) -> str:
        """Categorize word difficulty based on score."""
        if score >= 0.8:
            return "Very Common"
        elif score >= 0.6:
            return "Common"
        elif score >= 0.4:
            return "Moderate"
        elif score >= 0.2:
            return "Uncommon"
        else:
            return "Rare"
    
    def _categorize_collocation_difficulty(self, score: float) -> str:
        """Categorize overall collocation difficulty."""
        if score >= 0.7:
            return "Easy"
        elif score >= 0.5:
            return "Moderate"
        elif score >= 0.3:
            return "Challenging"
        else:
            return "Difficult"
    
    def _get_learning_recommendation(self, score: float) -> str:
        """Get learning recommendation based on difficulty score."""
        if score >= 0.7:
            return "Ready for immediate use - high component familiarity"
        elif score >= 0.5:
            return "Good for active learning - some component practice needed"
        elif score >= 0.3:
            return "Requires focused study - unfamiliar components"
        else:
            return "Advanced level - extensive component work needed first"


def analyze_database_collocations(db_path: str = "instance/data/srs/tunatale_srs.db",
                                frequency_db_path: str = "instance/data/word_frequency.json"):
    """
    Analyze all collocations in the SRS database using component-based difficulty.
    
    This function can be used to batch-update stability values for all collocations.
    """
    calculator = ComponentDifficultyCalculator(frequency_db_path)
    
    # Import SRSDatabase to read collocations
    try:
        from srs_database import SRSDatabase
        
        srs_db = SRSDatabase(db_path)
        all_collocations = srs_db.get_all_collocations()
        
        print(f"\n=== Component Difficulty Analysis ===")
        print(f"Analyzing {len(all_collocations)} collocations from database...")
        
        # Analyze each collocation
        analyses = []
        for item in all_collocations:
            collocation = item['text']
            analysis = calculator.analyze_collocation(collocation)
            analyses.append(analysis)
        
        # Sort by difficulty score (easiest first)
        analyses.sort(key=lambda x: x['difficulty_score'], reverse=True)
        
        # Display results
        print(f"\nTop 15 Easiest Collocations (highest component frequency):")
        for i, analysis in enumerate(analyses[:15], 1):
            print(f"{i:2d}. '{analysis['collocation']}' "
                  f"(score: {analysis['difficulty_score']}, "
                  f"stability: {analysis['stability']}, "
                  f"category: {analysis['difficulty_category']})")
        
        print(f"\nTop 15 Hardest Collocations (lowest component frequency):")
        for i, analysis in enumerate(analyses[-15:], 1):
            print(f"{i:2d}. '{analysis['collocation']}' "
                  f"(score: {analysis['difficulty_score']}, "
                  f"stability: {analysis['stability']}, "
                  f"category: {analysis['difficulty_category']})")
        
        # Statistics
        scores = [a['difficulty_score'] for a in analyses]
        stabilities = [a['stability'] for a in analyses]
        
        print(f"\n=== Statistics ===")
        print(f"Average difficulty score: {sum(scores)/len(scores):.3f}")
        print(f"Average stability: {sum(stabilities)/len(stabilities):.3f}")
        print(f"Score range: {min(scores):.3f} - {max(scores):.3f}")
        print(f"Stability range: {min(stabilities):.3f} - {max(stabilities):.3f}")
        
        return analyses
        
    except ImportError:
        logger.error("SRSDatabase not available for analysis")
        return []


def main():
    """Main execution function for testing."""
    calculator = ComponentDifficultyCalculator()
    
    # Test with example collocations from the user's original issue
    test_collocations = [
        "salamat po",
        "kumusta po", 
        "magkano po",
        "adobo salamat po",
        "ah paano po",
        "ah saan po",
        "ah salamat po",
        "ah! meron po ba kayong kape?",
        "nakakamangha talaga",
        "puwede po ba"
    ]
    
    print("=== Component-Based Difficulty Analysis ===")
    print("Testing collocations from user's WIDER strategy selection...\n")
    
    for collocation in test_collocations:
        analysis = calculator.analyze_collocation(collocation)
        
        print(f"Collocation: '{collocation}'")
        print(f"  Difficulty Score: {analysis['difficulty_score']} ({analysis['difficulty_category']})")
        print(f"  Suggested Stability: {analysis['stability']}")
        print(f"  Component Analysis:")
        for component in analysis['component_analysis']:
            print(f"    '{component['word']}': freq={component['frequency']}, "
                  f"score={component['score']} ({component['category']})")
        print(f"  Recommendation: {analysis['learning_recommendation']}")
        print()


if __name__ == "__main__":
    main()