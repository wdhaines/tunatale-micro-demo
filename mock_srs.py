"""
Mock SRS (Spaced Repetition System) for vocabulary-informed content generation.

This simulates vocabulary progression tracking to demonstrate how the real SRS 
will integrate with the two-part prompt architecture.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from content_strategy import ContentStrategy, DifficultyLevel


@dataclass
class VocabularyState:
    """Represents the current vocabulary state for content generation."""
    learned_vocabulary: List[str]  # Well-established words/phrases
    review_vocabulary: List[str]   # Due for reinforcement
    new_vocabulary_limit: int      # Max new words per lesson
    difficulty_level: str          # Current complexity level
    total_days_completed: int      # Track progression
    
    
@dataclass
class LessonVocabularyReport:
    """Report of vocabulary used in a generated lesson."""
    introduced_new: List[str]      # New vocabulary introduced
    reinforced_review: List[str]   # Review vocabulary used
    unexpected_vocabulary: List[str]  # Vocabulary that appeared but wasn't planned
    

class MockSRS:
    """Mock SRS that simulates vocabulary progression for content generation."""
    
    def __init__(self, data_path: Optional[Path] = None):
        """Initialize mock SRS with simulated vocabulary data."""
        self.data_path = data_path or Path("instance/data/mock_srs_state.json")
        self.vocabulary_state = self._load_or_create_initial_state()
        
        # El Nido specific vocabulary progression simulation
        self.day_vocabulary_map = self._create_el_nido_vocabulary_progression()
        
    def _create_el_nido_vocabulary_progression(self) -> Dict[int, Dict[str, List[str]]]:
        """Create a realistic vocabulary progression for El Nido trip preparation."""
        return {
            1: {
                "base": ["salamat", "po", "opo", "hindi", "oo", "kumusta"],
                "new": ["magandang umaga", "magandang gabi", "paalam"]
            },
            2: {
                "base": ["salamat", "po", "opo", "hindi", "oo", "kumusta", "magandang umaga"],
                "new": ["paumanhin", "saan", "nasa saan", "dito", "doon"]
            },
            3: {
                "base": ["salamat", "po", "saan", "dito", "paumanhin", "magandang umaga"],
                "new": ["magkano", "mahal", "mura", "bayad", "sukli"]
            },
            4: {
                "base": ["salamat", "po", "magkano", "bayad", "saan", "paumanhin"],
                "new": ["gutom", "tubig", "pagkain", "masarap", "hindi masarap"]
            },
            5: {
                "base": ["salamat", "po", "magkano", "pagkain", "masarap", "tubig"],
                "new": ["hotel", "kwarto", "banyo", "matulog", "gising"]
            },
            6: {
                "base": ["salamat", "po", "hotel", "kwarto", "masarap", "pagkain"],
                "new": ["beach", "dagat", "araw", "init", "lamig", "tubig"]
            },
            7: {
                "base": ["salamat", "po", "dagat", "araw", "masarap", "hotel"],
                "new": ["restaurant", "mesa", "menu", "order", "waiter"]
            },
            8: {
                "base": ["salamat", "po", "restaurant", "mesa", "order", "masarap"],
                "new": ["airport", "eroplano", "flight", "ticket", "paalam na"]
            }
        }
    
    def _load_or_create_initial_state(self) -> VocabularyState:
        """Load existing state or create initial vocabulary state."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return VocabularyState(**data)
            except Exception as e:
                logging.warning(f"Failed to load mock SRS state: {e}, creating new state")
        
        # Create initial state
        return VocabularyState(
            learned_vocabulary=["salamat", "po", "opo"],  # Basic courtesy words
            review_vocabulary=["kumusta", "magandang umaga"],
            new_vocabulary_limit=3,
            difficulty_level="basic",
            total_days_completed=0
        )
    
    def save_state(self):
        """Save current vocabulary state to file."""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.vocabulary_state), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to save mock SRS state: {e}")
    
    def get_vocabulary_state_for_day(self, day: int, strategy: ContentStrategy = ContentStrategy.BALANCED) -> VocabularyState:
        """Get vocabulary constraints for generating content for a specific day."""
        
        # Simulate vocabulary progression based on day
        if day <= len(self.day_vocabulary_map):
            day_data = self.day_vocabulary_map[day]
            learned = day_data["base"]
            new_to_introduce = day_data["new"][:2]  # Limit new vocabulary
        else:
            # For days beyond our map, use accumulated vocabulary
            learned = self.vocabulary_state.learned_vocabulary
            new_to_introduce = []
        
        # Adjust based on strategy
        if strategy == ContentStrategy.DEEPER:
            # Deeper mode: fewer new words, more focus on sophisticated usage
            new_limit = 2
            review_words = learned[-5:] if len(learned) >= 5 else learned
        elif strategy == ContentStrategy.WIDER:
            # Wider mode: more new words for different contexts
            new_limit = 4
            review_words = learned[-3:] if len(learned) >= 3 else learned
        else:
            # Balanced mode
            new_limit = 3
            review_words = learned[-4:] if len(learned) >= 4 else learned
        
        return VocabularyState(
            learned_vocabulary=learned,
            review_vocabulary=review_words,
            new_vocabulary_limit=new_limit,
            difficulty_level=self._determine_difficulty_level(day, strategy),
            total_days_completed=min(day - 1, self.vocabulary_state.total_days_completed)
        )
    
    def _determine_difficulty_level(self, day: int, strategy: ContentStrategy) -> str:
        """Determine difficulty level based on day and strategy."""
        if strategy == ContentStrategy.DEEPER:
            if day <= 3:
                return "basic_enhanced"
            elif day <= 6:
                return "intermediate"
            else:
                return "advanced"
        elif strategy == ContentStrategy.WIDER:
            # Wider maintains current difficulty but expands contexts
            if day <= 4:
                return "basic"
            else:
                return "intermediate"
        else:
            # Balanced progression
            if day <= 2:
                return "basic"
            elif day <= 5:
                return "basic_plus"
            else:
                return "intermediate"
    
    def update_from_lesson(self, day: int, vocabulary_report: LessonVocabularyReport):
        """Update vocabulary state based on lesson generation results."""
        
        # Add newly introduced vocabulary to learned set
        if vocabulary_report.introduced_new:
            for word in vocabulary_report.introduced_new:
                if word not in self.vocabulary_state.learned_vocabulary:
                    self.vocabulary_state.learned_vocabulary.append(word)
        
        # Move review vocabulary that was successfully used to learned
        for word in vocabulary_report.reinforced_review:
            if word in self.vocabulary_state.review_vocabulary:
                self.vocabulary_state.review_vocabulary.remove(word)
            if word not in self.vocabulary_state.learned_vocabulary:
                self.vocabulary_state.learned_vocabulary.append(word)
        
        # Update progression
        if day > self.vocabulary_state.total_days_completed:
            self.vocabulary_state.total_days_completed = day
        
        # Adjust difficulty based on success
        if len(vocabulary_report.unexpected_vocabulary) > 2:
            logging.warning(f"Unexpected vocabulary introduced: {vocabulary_report.unexpected_vocabulary}")
        
        self.save_state()
        logging.info(f"Updated mock SRS: {len(self.vocabulary_state.learned_vocabulary)} learned words")
    
    def get_srs_data_for_prompt(self, day: int, strategy: ContentStrategy = ContentStrategy.BALANCED) -> Dict[str, any]:
        """Get SRS data formatted for inclusion in day prompts."""
        vocab_state = self.get_vocabulary_state_for_day(day, strategy)
        
        return {
            "learned_vocabulary": vocab_state.learned_vocabulary,
            "review_vocabulary": vocab_state.review_vocabulary,
            "new_vocabulary_limit": vocab_state.new_vocabulary_limit,
            "difficulty_level": vocab_state.difficulty_level,
            "vocabulary_constraints": self._generate_vocabulary_constraints(vocab_state, strategy)
        }
    
    def _generate_vocabulary_constraints(self, vocab_state: VocabularyState, strategy: ContentStrategy) -> str:
        """Generate human-readable vocabulary constraints for prompts."""
        learned_str = ", ".join(vocab_state.learned_vocabulary[-10:])  # Show recent learned
        review_str = ", ".join(vocab_state.review_vocabulary)
        
        constraints = f"""
VOCABULARY CONSTRAINTS:
- LEARNED WORDS (use freely): {learned_str}
- REVIEW WORDS (must reinforce): {review_str}
- NEW WORDS LIMIT: Maximum {vocab_state.new_vocabulary_limit} new Filipino words/phrases
- DIFFICULTY: {vocab_state.difficulty_level}
- STRATEGY: {strategy.value}

VOCABULARY GUIDANCE:
- Build dialogues using LEARNED WORDS as foundation
- Naturally incorporate all REVIEW WORDS to reinforce learning
- Introduce new vocabulary only when essential for the scenario
- Ensure new words are practical for El Nido travel context
"""
        return constraints.strip()


def create_mock_srs() -> MockSRS:
    """Factory function to create a mock SRS instance."""
    return MockSRS()