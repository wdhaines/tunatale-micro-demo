"""
Content Strategy Framework for TunaTale

This module defines the content generation strategies and configuration
for implementing "Go Wider vs Go Deeper" learning approaches.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class ContentStrategy(Enum):
    """
    Content generation strategies for Filipino language learning.
    
    WIDER: Generate new scenarios using familiar vocabulary
    DEEPER: Enhance existing scenarios with advanced Filipino expressions
    BALANCED: Mix of both approaches (current default)
    """
    WIDER = "wider"
    DEEPER = "deeper"
    BALANCED = "balanced"


class DifficultyLevel(Enum):
    """
    Language complexity levels for story generation.
    
    BASIC: Current level with English fallbacks
    INTERMEDIATE: More Filipino, fewer English words
    ADVANCED: Native-level expressions and cultural references
    """
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class DifficultyProgressionSettings:
    """Settings for how difficulty progresses in DEEPER strategy."""
    
    # Language complexity
    filipino_ratio: float = 0.7  # Ratio of Filipino to English words
    cultural_context_depth: int = 3  # 1-5 scale of cultural references
    grammatical_complexity: int = 2  # 1-5 scale of grammar complexity
    
    # Vocabulary progression
    advanced_verb_forms: bool = False  # Use aspect markers, etc.
    idiomatic_expressions: bool = False  # Include Filipino idioms
    regional_variations: bool = False  # Include regional speech patterns
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for prompt templating."""
        return {
            'filipino_ratio': self.filipino_ratio,
            'cultural_depth': self.cultural_context_depth,
            'grammar_complexity': self.grammatical_complexity,
            'use_advanced_verbs': self.advanced_verb_forms,
            'include_idioms': self.idiomatic_expressions,
            'include_regional': self.regional_variations
        }


@dataclass
class ScenarioExpansionSettings:
    """Settings for how scenarios expand in WIDER strategy."""
    
    # Scenario variety
    scenario_types: List[str] = field(default_factory=lambda: [
        'restaurant', 'transportation', 'shopping', 'accommodation', 'activities'
    ])
    
    # Context expansion
    character_variety: int = 3  # Number of different character types
    setting_complexity: int = 2  # 1-5 scale of setting detail
    interaction_types: List[str] = field(default_factory=lambda: [
        'ordering', 'asking_directions', 'negotiating_price', 'making_reservations'
    ])
    
    # Vocabulary constraints
    maintain_difficulty_level: bool = True
    max_new_words_per_scenario: int = 5
    reuse_familiar_patterns: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for prompt templating."""
        return {
            'scenarios': self.scenario_types,
            'character_variety': self.character_variety,
            'setting_complexity': self.setting_complexity,
            'interaction_types': self.interaction_types,
            'maintain_difficulty': self.maintain_difficulty_level,
            'max_new_words': self.max_new_words_per_scenario,
            'reuse_patterns': self.reuse_familiar_patterns
        }


@dataclass
class StrategyConfig:
    """
    Comprehensive configuration for content generation strategies.
    Used to control both SRS behavior and content generation parameters.
    """
    
    # Core strategy
    strategy: ContentStrategy = ContentStrategy.BALANCED
    difficulty_level: DifficultyLevel = DifficultyLevel.BASIC
    
    # SRS parameters
    max_new_collocations: int = 5
    min_review_collocations: int = 3
    review_interval_multiplier: float = 1.0
    
    # Legacy parameters (for backward compatibility)
    difficulty_preference: str = "balanced_approach"
    english_scaffolding_level: str = "current_default"
    
    # Strategy-specific settings
    difficulty_settings: Optional[DifficultyProgressionSettings] = None
    expansion_settings: Optional[ScenarioExpansionSettings] = None
    
    # Advanced parameters
    cultural_authenticity_priority: float = 0.5  # 0-1 scale
    vocabulary_retention_focus: float = 0.5      # 0-1 scale  
    scenario_creativity: float = 0.5             # 0-1 scale
    
    def __post_init__(self):
        """Initialize strategy-specific settings if not provided."""
        if self.strategy == ContentStrategy.DEEPER and self.difficulty_settings is None:
            self.difficulty_settings = DifficultyProgressionSettings()
            
        if self.strategy == ContentStrategy.WIDER and self.expansion_settings is None:
            self.expansion_settings = ScenarioExpansionSettings()
    
    def validate(self) -> bool:
        """Validate configuration parameters."""
        try:
            # Check ranges
            assert 0 <= self.cultural_authenticity_priority <= 1
            assert 0 <= self.vocabulary_retention_focus <= 1
            assert 0 <= self.scenario_creativity <= 1
            assert self.max_new_collocations > 0
            assert self.min_review_collocations >= 0
            assert self.review_interval_multiplier > 0
            
            # Strategy-specific validation
            if self.strategy == ContentStrategy.DEEPER:
                assert self.difficulty_settings is not None
                assert 0 <= self.difficulty_settings.filipino_ratio <= 1
                
            if self.strategy == ContentStrategy.WIDER:
                assert self.expansion_settings is not None
                assert len(self.expansion_settings.scenario_types) > 0
                
            logger.debug(f"Strategy config validation passed for {self.strategy}")
            return True
            
        except AssertionError as e:
            logger.error(f"Strategy config validation failed: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization and templating."""
        result = {
            'strategy': self.strategy.value,
            'difficulty_level': self.difficulty_level.value,
            'max_new_collocations': self.max_new_collocations,
            'min_review_collocations': self.min_review_collocations,
            'review_interval_multiplier': self.review_interval_multiplier,
            'difficulty_preference': self.difficulty_preference,
            'english_scaffolding_level': self.english_scaffolding_level,
            'cultural_authenticity_priority': self.cultural_authenticity_priority,
            'vocabulary_retention_focus': self.vocabulary_retention_focus,
            'scenario_creativity': self.scenario_creativity
        }
        
        if self.difficulty_settings:
            result['difficulty_settings'] = self.difficulty_settings.to_dict()
            
        if self.expansion_settings:
            result['expansion_settings'] = self.expansion_settings.to_dict()
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyConfig':
        """Create StrategyConfig from dictionary."""
        strategy = ContentStrategy(data['strategy'])
        difficulty_level = DifficultyLevel(data['difficulty_level'])
        
        # Extract difficulty settings if present
        difficulty_settings = None
        if 'difficulty_settings' in data:
            ds = data['difficulty_settings']
            difficulty_settings = DifficultyProgressionSettings(
                filipino_ratio=ds.get('filipino_ratio', 0.7),
                cultural_context_depth=ds.get('cultural_depth', 3),
                grammatical_complexity=ds.get('grammar_complexity', 2),
                advanced_verb_forms=ds.get('use_advanced_verbs', False),
                idiomatic_expressions=ds.get('include_idioms', False),
                regional_variations=ds.get('include_regional', False)
            )
        
        # Extract expansion settings if present
        expansion_settings = None
        if 'expansion_settings' in data:
            es = data['expansion_settings']
            expansion_settings = ScenarioExpansionSettings(
                scenario_types=es.get('scenarios', ['restaurant', 'transportation']),
                character_variety=es.get('character_variety', 3),
                setting_complexity=es.get('setting_complexity', 2),
                interaction_types=es.get('interaction_types', ['ordering', 'asking_directions']),
                maintain_difficulty_level=es.get('maintain_difficulty', True),
                max_new_words_per_scenario=es.get('max_new_words', 5),
                reuse_familiar_patterns=es.get('reuse_patterns', True)
            )
        
        return cls(
            strategy=strategy,
            difficulty_level=difficulty_level,
            max_new_collocations=data.get('max_new_collocations', 5),
            min_review_collocations=data.get('min_review_collocations', 3),
            review_interval_multiplier=data.get('review_interval_multiplier', 1.0),
            difficulty_preference=data.get('difficulty_preference', 'balanced_approach'),
            english_scaffolding_level=data.get('english_scaffolding_level', 'current_default'),
            difficulty_settings=difficulty_settings,
            expansion_settings=expansion_settings,
            cultural_authenticity_priority=data.get('cultural_authenticity_priority', 0.5),
            vocabulary_retention_focus=data.get('vocabulary_retention_focus', 0.5),
            scenario_creativity=data.get('scenario_creativity', 0.5)
        )
    
    
# Predefined strategy configurations
DEFAULT_STRATEGY_CONFIGS = {
    ContentStrategy.WIDER: StrategyConfig(
        strategy=ContentStrategy.WIDER,
        difficulty_level=DifficultyLevel.BASIC,
        max_new_collocations=8,
        min_review_collocations=2,
        review_interval_multiplier=1.5,
        difficulty_preference='expand_contexts',
        english_scaffolding_level='maintain_current',
        cultural_authenticity_priority=0.6,
        vocabulary_retention_focus=0.8,
        scenario_creativity=0.9
    ),
    
    ContentStrategy.DEEPER: StrategyConfig(
        strategy=ContentStrategy.DEEPER,
        difficulty_level=DifficultyLevel.INTERMEDIATE,
        max_new_collocations=3,
        min_review_collocations=7,
        review_interval_multiplier=0.8,
        difficulty_preference='increase_complexity',
        english_scaffolding_level='minimize_strategic',
        cultural_authenticity_priority=0.9,
        vocabulary_retention_focus=0.6,
        scenario_creativity=0.4
    ),
    
    ContentStrategy.BALANCED: StrategyConfig(
        strategy=ContentStrategy.BALANCED,
        difficulty_level=DifficultyLevel.BASIC,
        max_new_collocations=5,
        min_review_collocations=5,
        review_interval_multiplier=1.0,
        difficulty_preference='balanced_approach',
        english_scaffolding_level='current_default',
        cultural_authenticity_priority=0.5,
        vocabulary_retention_focus=0.5,
        scenario_creativity=0.5
    )
}

# Legacy alias for backward compatibility
STRATEGY_CONFIGS = DEFAULT_STRATEGY_CONFIGS


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
    """Get default configuration for a strategy."""
    return DEFAULT_STRATEGY_CONFIGS[strategy]


def create_custom_strategy_config(
    strategy: ContentStrategy,
    **kwargs
) -> StrategyConfig:
    """Create a custom strategy configuration with overrides."""
    base_config = get_strategy_config(strategy)
    
    # Create new config with overrides
    config_dict = base_config.to_dict()
    config_dict.update(kwargs)
    
    return StrategyConfig.from_dict(config_dict)


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