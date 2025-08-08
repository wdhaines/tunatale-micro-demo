"""
Content Strategy Framework for TunaTale

This module defines the content generation strategies and configuration
for implementing "Go Wider vs Go Deeper" learning approaches.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional


class ContentStrategy(Enum):
    """Content generation strategy options."""
    WIDER = "wider"      # New scenarios, same difficulty
    DEEPER = "deeper"    # Same scenarios, enhanced language complexity
    BALANCED = "balanced"  # Current default approach


class DifficultyLevel(Enum):
    """Language complexity levels for DEEPER strategy."""
    BASIC = "basic"         # Current level (lots of English scaffolding)
    INTERMEDIATE = "intermediate"  # Reduced English, more authentic Tagalog
    ADVANCED = "advanced"   # Minimal English, native-level expressions


@dataclass
class StrategyConfig:
    """Configuration parameters for content strategies."""
    max_new_collocations: int
    min_review_collocations: int
    review_interval_multiplier: float
    difficulty_preference: str
    english_scaffolding_level: str
    
    
# Strategy-specific configuration parameters
STRATEGY_CONFIGS = {
    ContentStrategy.WIDER: StrategyConfig(
        max_new_collocations=8,
        min_review_collocations=2,
        review_interval_multiplier=1.5,
        difficulty_preference='expand_contexts',
        english_scaffolding_level='maintain_current'
    ),
    ContentStrategy.DEEPER: StrategyConfig(
        max_new_collocations=3,
        min_review_collocations=7,
        review_interval_multiplier=0.8,
        difficulty_preference='increase_complexity',
        english_scaffolding_level='minimize_strategic'
    ),
    ContentStrategy.BALANCED: StrategyConfig(
        max_new_collocations=5,
        min_review_collocations=5,
        review_interval_multiplier=1.0,
        difficulty_preference='balanced_approach',
        english_scaffolding_level='current_default'
    )
}


@dataclass
class EnhancedStoryParams:
    """Enhanced story generation parameters with strategy support."""
    # Core parameters (existing)
    learning_objective: str
    language: str = "Tagalog"
    cefr_level: str = "A2"
    phase: int = 1
    
    # Strategy parameters (new)
    content_strategy: ContentStrategy = ContentStrategy.BALANCED
    difficulty_level: DifficultyLevel = DifficultyLevel.BASIC
    source_day: Optional[int] = None  # For DEEPER mode - which day to enhance
    
    # SRS integration
    new_vocabulary: list = None
    review_collocations: list = None
    
    # Content guidance
    story_guidance: Optional[str] = None
    focus: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.new_vocabulary is None:
            self.new_vocabulary = []
        if self.review_collocations is None:
            self.review_collocations = []


def get_strategy_config(strategy: ContentStrategy) -> StrategyConfig:
    """Get configuration for a specific content strategy."""
    return STRATEGY_CONFIGS[strategy]


def create_enhanced_story_params(
    learning_objective: str,
    strategy: ContentStrategy = ContentStrategy.BALANCED,
    source_day: Optional[int] = None,
    difficulty_level: DifficultyLevel = DifficultyLevel.BASIC,
    **kwargs
) -> EnhancedStoryParams:
    """Factory function to create enhanced story parameters."""
    return EnhancedStoryParams(
        learning_objective=learning_objective,
        content_strategy=strategy,
        source_day=source_day,
        difficulty_level=difficulty_level,
        **kwargs
    )