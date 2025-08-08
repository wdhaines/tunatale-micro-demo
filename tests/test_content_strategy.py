"""
Tests for content_strategy.py - Go Wider vs Go Deeper framework.

This test suite validates the new content generation strategy framework
that allows users to either extend curriculum with new scenarios (wider)
or enhance existing scenarios with sophisticated language (deeper).
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile

# Import the modules to test
from content_strategy import (
    ContentStrategy, 
    DifficultyLevel, 
    EnhancedStoryParams,
    get_strategy_config,
    STRATEGY_CONFIGS
)
from story_generator import ContentGenerator, StoryParams, CEFRLevel
from curriculum_models import Curriculum, CurriculumDay


class TestContentStrategyEnums:
    """Test the content strategy enums and configurations."""
    
    def test_content_strategy_enum_values(self):
        """Test that ContentStrategy enum has correct values."""
        assert ContentStrategy.WIDER.value == "wider"
        assert ContentStrategy.DEEPER.value == "deeper" 
        assert ContentStrategy.BALANCED.value == "balanced"
    
    def test_difficulty_level_enum_values(self):
        """Test that DifficultyLevel enum has correct values."""
        assert DifficultyLevel.BASIC.value == "basic"
        assert DifficultyLevel.INTERMEDIATE.value == "intermediate"
        assert DifficultyLevel.ADVANCED.value == "advanced"
    
    def test_strategy_configs_exist(self):
        """Test that strategy configurations are properly defined."""
        assert ContentStrategy.WIDER in STRATEGY_CONFIGS
        assert ContentStrategy.DEEPER in STRATEGY_CONFIGS
        assert ContentStrategy.BALANCED in STRATEGY_CONFIGS
        
        # Test wider strategy config
        wider_config = STRATEGY_CONFIGS[ContentStrategy.WIDER]
        assert hasattr(wider_config, 'max_new_collocations')
        assert hasattr(wider_config, 'min_review_collocations')
        assert hasattr(wider_config, 'review_interval_multiplier')
        assert hasattr(wider_config, 'difficulty_preference')
        
        # Test deeper strategy config
        deeper_config = STRATEGY_CONFIGS[ContentStrategy.DEEPER]
        assert hasattr(deeper_config, 'max_new_collocations')
        assert hasattr(deeper_config, 'min_review_collocations')
        assert hasattr(deeper_config, 'review_interval_multiplier')
        assert hasattr(deeper_config, 'difficulty_preference')
    
    def test_get_strategy_config_function(self):
        """Test the get_strategy_config utility function."""
        wider_config = get_strategy_config(ContentStrategy.WIDER)
        assert wider_config is not None
        assert wider_config.difficulty_preference == 'expand_contexts'
        
        deeper_config = get_strategy_config(ContentStrategy.DEEPER)
        assert deeper_config is not None
        assert deeper_config.difficulty_preference == 'increase_complexity'
        
        # Test that configurations make strategic sense
        assert wider_config.max_new_collocations > deeper_config.max_new_collocations
        assert deeper_config.min_review_collocations > wider_config.min_review_collocations


class TestEnhancedStoryParams:
    """Test the enhanced story parameters for strategy-aware generation."""
    
    def test_enhanced_story_params_creation(self):
        """Test creating enhanced story parameters with strategy info."""
        params = EnhancedStoryParams(
            learning_objective="Test enhanced parameters",
            language="Filipino",
            cefr_level="A2",
            phase=1,
            content_strategy=ContentStrategy.WIDER,
            difficulty_level=DifficultyLevel.BASIC,
            source_day=None,
            new_vocabulary=["kumusta po", "salamat po"],
            review_collocations=["magandang umaga"]
        )
        
        assert params.content_strategy == ContentStrategy.WIDER
        assert params.difficulty_level == DifficultyLevel.BASIC
        assert params.source_day is None
        assert len(params.new_vocabulary) == 2
        assert len(params.review_collocations) == 1
    
    def test_enhanced_story_params_deeper_strategy(self):
        """Test enhanced parameters for DEEPER strategy with source day."""
        params = EnhancedStoryParams(
            learning_objective="Enhanced version of day 3",
            language="Filipino",
            cefr_level="B1",
            phase=7,
            content_strategy=ContentStrategy.DEEPER,
            difficulty_level=DifficultyLevel.INTERMEDIATE,
            source_day=3,
            new_vocabulary=["makakain na tayo", "tara na"],
            review_collocations=["kumusta po", "salamat po"]
        )
        
        assert params.content_strategy == ContentStrategy.DEEPER
        assert params.difficulty_level == DifficultyLevel.INTERMEDIATE
        assert params.source_day == 3
    
    def test_enhanced_story_params_defaults(self):
        """Test that enhanced parameters have sensible defaults."""
        params = EnhancedStoryParams(
            learning_objective="Test defaults",
            language="Filipino", 
            cefr_level="A2",
            phase=1
        )
        
        assert params.content_strategy == ContentStrategy.BALANCED
        assert params.difficulty_level == DifficultyLevel.BASIC
        assert params.source_day is None


class TestStrategyAwareContentGeneration:
    """Test strategy-aware content generation functionality."""
    
    @pytest.fixture
    def mock_content_generator(self):
        """Create a mock content generator with strategy support."""
        generator = MagicMock(spec=ContentGenerator)
        
        # Mock the story generation methods
        generator.generate_enhanced_story = MagicMock(return_value="Test generated story")
        generator.generate_day_with_srs = MagicMock(return_value="Test SRS story")
        
        return generator
    
    @pytest.fixture
    def sample_curriculum(self):
        """Create sample curriculum for testing strategies."""
        day1 = CurriculumDay(
            day=1,
            title="Basic Greetings",
            focus="Introductory conversations",
            collocations=["kumusta po", "salamat po"],
            presentation_phrases=["hello", "thank you"],
            learning_objective="Learn basic greetings",
            story_guidance="Keep it simple and polite"
        )
        
        day3 = CurriculumDay(
            day=3,
            title="Market Conversations",
            focus="Shopping vocabulary",
            collocations=["magkano po", "pwede po bang"],
            presentation_phrases=["how much", "can I"],
            learning_objective="Shop at the market",
            story_guidance="Include price negotiation"
        )
        
        curriculum = Curriculum(
            learning_objective="Filipino conversation basics",
            target_language="Filipino",
            learner_level="A2",
            presentation_length=30,
            days=[day1, day3]
        )
        
        return curriculum
    
    def test_wider_strategy_generation(self, mock_content_generator, sample_curriculum):
        """Test content generation using WIDER strategy."""
        # Simulate generating new scenario content based on existing day
        source_day = sample_curriculum.get_day(1)  # Basic greetings
        
        # WIDER strategy: expand to new contexts while maintaining difficulty
        wider_params = EnhancedStoryParams(
            learning_objective="Restaurant greetings (new scenario)",
            language="Filipino",
            cefr_level="A2",
            phase=5,  # New day
            content_strategy=ContentStrategy.WIDER,
            difficulty_level=DifficultyLevel.BASIC,
            source_day=1,  # Based on day 1
            new_vocabulary=["mesa para dos", "order po"],  # New context vocabulary
            review_collocations=["kumusta po", "salamat po"]  # Reinforce existing
        )
        
        # Test that parameters align with WIDER strategy
        assert wider_params.content_strategy == ContentStrategy.WIDER
        assert wider_params.source_day == 1
        assert wider_params.difficulty_level == DifficultyLevel.BASIC  # Same difficulty
        
        # Test strategy config alignment
        config = get_strategy_config(ContentStrategy.WIDER)
        assert len(wider_params.new_vocabulary) <= config.max_new_collocations
        
        # Mock generation
        mock_content_generator.generate_enhanced_story(wider_params)
        mock_content_generator.generate_enhanced_story.assert_called_once_with(wider_params)
    
    def test_deeper_strategy_generation(self, mock_content_generator, sample_curriculum):
        """Test content generation using DEEPER strategy."""
        # Simulate enhancing existing content with more sophisticated language
        source_day = sample_curriculum.get_day(3)  # Market conversations
        
        # DEEPER strategy: same scenario, advanced language
        deeper_params = EnhancedStoryParams(
            learning_objective="Advanced market negotiations",
            language="Filipino",
            cefr_level="B2",  # Higher level
            phase=8,  # Enhanced version
            content_strategy=ContentStrategy.DEEPER,
            difficulty_level=DifficultyLevel.INTERMEDIATE,
            source_day=3,  # Enhance day 3
            new_vocabulary=["makakuha ng magandang presyo"],  # More complex phrases
            review_collocations=["magkano po", "pwede po bang", "tara na po", "salamat po", 
                               "kumusta po", "paano po", "saan po"]  # 7 review collocations minimum
        )
        
        # Test that parameters align with DEEPER strategy
        assert deeper_params.content_strategy == ContentStrategy.DEEPER
        assert deeper_params.source_day == 3
        assert deeper_params.difficulty_level == DifficultyLevel.INTERMEDIATE
        
        # Test strategy config alignment
        config = get_strategy_config(ContentStrategy.DEEPER)
        assert len(deeper_params.new_vocabulary) <= config.max_new_collocations
        assert len(deeper_params.review_collocations) >= config.min_review_collocations
        
        # Mock generation
        mock_content_generator.generate_enhanced_story(deeper_params)
        mock_content_generator.generate_enhanced_story.assert_called_once_with(deeper_params)
    
    def test_balanced_strategy_generation(self, mock_content_generator):
        """Test content generation using BALANCED strategy (current approach)."""
        balanced_params = EnhancedStoryParams(
            learning_objective="Standard lesson progression",
            language="Filipino",
            cefr_level="A2",
            phase=2,
            content_strategy=ContentStrategy.BALANCED,
            difficulty_level=DifficultyLevel.BASIC,
            new_vocabulary=["opo", "hindi po"],
            review_collocations=["kumusta po"]
        )
        
        # Test that parameters use balanced approach
        assert balanced_params.content_strategy == ContentStrategy.BALANCED
        assert balanced_params.source_day is None  # Not based on specific day
        
        # Mock generation
        mock_content_generator.generate_enhanced_story(balanced_params)
        mock_content_generator.generate_enhanced_story.assert_called_once_with(balanced_params)


class TestStrategyValidation:
    """Test validation logic for strategy-aware content generation."""
    
    def test_wider_strategy_validation(self):
        """Test validation rules for WIDER strategy."""
        def validate_wider_strategy(params: EnhancedStoryParams) -> list:
            """Validate parameters for WIDER strategy."""
            issues = []
            
            if params.content_strategy != ContentStrategy.WIDER:
                return issues
            
            # WIDER strategy should have source day for context expansion
            if params.source_day is None:
                issues.append("WIDER strategy should specify source_day for context expansion")
            
            # Difficulty should not increase dramatically
            if params.difficulty_level == DifficultyLevel.ADVANCED:
                issues.append("WIDER strategy should maintain similar difficulty level")
            
            # Should focus on vocabulary expansion, not complexity
            config = get_strategy_config(ContentStrategy.WIDER)
            if len(params.new_vocabulary or []) > config.max_new_collocations:
                issues.append(f"Too many new collocations for WIDER strategy (max: {config.max_new_collocations})")
            
            return issues
        
        # Test valid WIDER parameters
        valid_wider = EnhancedStoryParams(
            learning_objective="New restaurant scenario",
            language="Filipino",
            cefr_level="A2", 
            phase=5,
            content_strategy=ContentStrategy.WIDER,
            difficulty_level=DifficultyLevel.BASIC,
            source_day=1,
            new_vocabulary=["mesa", "order", "bill"]
        )
        
        issues = validate_wider_strategy(valid_wider)
        assert len(issues) == 0, f"Valid WIDER params should pass validation: {issues}"
        
        # Test invalid WIDER parameters (no source day)
        invalid_wider = EnhancedStoryParams(
            learning_objective="Test",
            language="Filipino",
            cefr_level="A2",
            phase=5,
            content_strategy=ContentStrategy.WIDER,
            difficulty_level=DifficultyLevel.BASIC,
            source_day=None  # Missing source day
        )
        
        issues = validate_wider_strategy(invalid_wider)
        assert any("source_day" in issue for issue in issues)
    
    def test_deeper_strategy_validation(self):
        """Test validation rules for DEEPER strategy."""
        def validate_deeper_strategy(params: EnhancedStoryParams) -> list:
            """Validate parameters for DEEPER strategy."""
            issues = []
            
            if params.content_strategy != ContentStrategy.DEEPER:
                return issues
            
            # DEEPER strategy should have source day for enhancement
            if params.source_day is None:
                issues.append("DEEPER strategy should specify source_day for enhancement")
            
            # Should increase difficulty or complexity
            if params.difficulty_level == DifficultyLevel.BASIC:
                issues.append("DEEPER strategy should increase difficulty level from BASIC")
            
            # Should focus on fewer new items but more reviews
            config = get_strategy_config(ContentStrategy.DEEPER)
            if len(params.new_vocabulary or []) > config.max_new_collocations:
                issues.append(f"Too many new collocations for DEEPER strategy (max: {config.max_new_collocations})")
            
            if len(params.review_collocations or []) < config.min_review_collocations:
                issues.append(f"Not enough review collocations for DEEPER strategy (min: {config.min_review_collocations})")
            
            return issues
        
        # Test valid DEEPER parameters
        valid_deeper = EnhancedStoryParams(
            learning_objective="Advanced market conversations",
            language="Filipino",
            cefr_level="B1",
            phase=7,
            content_strategy=ContentStrategy.DEEPER,
            difficulty_level=DifficultyLevel.INTERMEDIATE,
            source_day=3,
            new_vocabulary=["makakuha ng magandang deal"],  # Limited new vocabulary
            review_collocations=["magkano po", "pwede po bang", "salamat po", "sige po", 
                               "kumusta po", "paano po", "tara na po"]  # 7 reviews minimum
        )
        
        issues = validate_deeper_strategy(valid_deeper)
        assert len(issues) == 0, f"Valid DEEPER params should pass validation: {issues}"
        
        # Test invalid DEEPER parameters (basic difficulty, no complexity target)
        invalid_deeper = EnhancedStoryParams(
            learning_objective="Test",
            language="Filipino",
            cefr_level="A2",
            phase=7,
            content_strategy=ContentStrategy.DEEPER,
            difficulty_level=DifficultyLevel.BASIC,  # Basic difficulty (should be higher)
            source_day=3,
            review_collocations=["one"]  # Too few reviews
        )
        
        issues = validate_deeper_strategy(invalid_deeper)
        assert any("difficulty" in issue for issue in issues)
        assert any("review collocations" in issue for issue in issues)


class TestStrategyIntegration:
    """Test integration of strategy framework with existing systems."""
    
    def test_strategy_srs_integration(self, tmp_path):
        """Test that strategy framework integrates properly with SRS."""
        # Import here to avoid circular imports during test collection
        from srs_tracker import SRSTracker
        
        # Create test SRS tracker
        srs_tracker = SRSTracker(data_dir=str(tmp_path), filename='strategy_test.json')
        
        # Add some existing collocations with different mastery levels
        basic_collocations = ["kumusta po", "salamat po"] 
        intermediate_collocations = ["pwede po bang", "magkano po"]
        advanced_collocations = ["makakuha ng magandang presyo", "tara na po", 
                                "paano po", "saan po", "ingat po kayo"]  # Added more for DEEPER minimum
        
        srs_tracker.add_collocations(basic_collocations, day=1)
        srs_tracker.add_collocations(intermediate_collocations, day=2)  
        srs_tracker.add_collocations(advanced_collocations, day=3)
        
        # Test WIDER strategy SRS selection
        def get_wider_strategy_collocations(srs_tracker, day: int) -> dict:
            """Get collocations appropriate for WIDER strategy."""
            config = get_strategy_config(ContentStrategy.WIDER)
            
            # WIDER focuses on expanding contexts with familiar vocabulary
            due_collocations = srs_tracker.get_due_collocations(
                day=day,
                min_items=config.min_review_collocations,
                max_items=config.max_new_collocations + config.min_review_collocations
            )
            
            return {
                'review_collocations': due_collocations[:config.min_review_collocations],
                'new_vocabulary_limit': config.max_new_collocations,
                'strategy': 'expand_contexts'
            }
        
        wider_selection = get_wider_strategy_collocations(srs_tracker, day=4)
        
        assert len(wider_selection['review_collocations']) >= 2  # min_review_collocations
        assert wider_selection['new_vocabulary_limit'] == 8    # max_new_collocations for WIDER
        assert wider_selection['strategy'] == 'expand_contexts'
        
        # Test DEEPER strategy SRS selection
        def get_deeper_strategy_collocations(srs_tracker, day: int) -> dict:
            """Get collocations appropriate for DEEPER strategy."""
            config = get_strategy_config(ContentStrategy.DEEPER)
            
            # DEEPER focuses on intensive review with limited new content
            due_collocations = srs_tracker.get_due_collocations(
                day=day,
                min_items=config.min_review_collocations,
                max_items=config.min_review_collocations + 2
            )
            
            return {
                'review_collocations': due_collocations,
                'new_vocabulary_limit': config.max_new_collocations,
                'strategy': 'increase_complexity'
            }
        
        deeper_selection = get_deeper_strategy_collocations(srs_tracker, day=4)
        
        assert len(deeper_selection['review_collocations']) >= 7  # min_review_collocations for DEEPER
        assert deeper_selection['new_vocabulary_limit'] == 3     # max_new_collocations for DEEPER  
        assert deeper_selection['strategy'] == 'increase_complexity'
    
    def test_strategy_curriculum_interaction(self):
        """Test how strategies interact with curriculum structure."""
        # Create base curriculum
        base_curriculum = Curriculum(
            learning_objective="Filipino conversation skills",
            target_language="Filipino", 
            learner_level="A2",
            presentation_length=30,
            days=[]
        )
        
        # Add initial days
        for i in range(1, 4):
            day = CurriculumDay(
                day=i,
                title=f"Day {i}",
                focus=f"Focus area {i}",
                collocations=[f"colloc_{i}_1", f"colloc_{i}_2"],
                presentation_phrases=[f"phrase_{i}"],
                learning_objective=f"Objective {i}",
                story_guidance=f"Guidance {i}"
            )
            base_curriculum.days.append(day)
        
        # Test WIDER strategy expansion
        def generate_wider_day(base_curriculum: Curriculum, source_day: int, new_day: int) -> CurriculumDay:
            """Generate new day using WIDER strategy."""
            source = base_curriculum.get_day(source_day)
            if not source:
                raise ValueError(f"Source day {source_day} not found")
            
            # Expand to new context while maintaining difficulty
            new_day_data = CurriculumDay(
                day=new_day,
                title=f"Expanded: {source.title} (New Context)",
                focus=f"New scenario: {source.focus}",
                collocations=source.collocations.copy(),  # Reuse familiar vocabulary
                presentation_phrases=[f"new_context_{new_day}"],  # New context phrases
                learning_objective=f"Apply {source.learning_objective} in new context",
                story_guidance=f"Expand on: {source.story_guidance}"
            )
            
            return new_day_data
        
        wider_day = generate_wider_day(base_curriculum, source_day=1, new_day=5)
        
        assert wider_day.day == 5
        assert "Expanded:" in wider_day.title
        assert "New Context" in wider_day.title
        assert wider_day.collocations == base_curriculum.get_day(1).collocations  # Reused vocabulary
        assert "Apply" in wider_day.learning_objective  # Extended objective
        
        # Test DEEPER strategy enhancement  
        def generate_deeper_day(base_curriculum: Curriculum, source_day: int, new_day: int) -> CurriculumDay:
            """Generate enhanced day using DEEPER strategy."""
            source = base_curriculum.get_day(source_day)
            if not source:
                raise ValueError(f"Source day {source_day} not found")
            
            # Enhance with more sophisticated language
            enhanced_collocations = [f"advanced_{colloc}" for colloc in source.collocations]
            
            new_day_data = CurriculumDay(
                day=new_day,
                title=f"Advanced: {source.title}",
                focus=f"Enhanced {source.focus}",
                collocations=enhanced_collocations,  # More sophisticated vocabulary
                presentation_phrases=[f"advanced_{phrase}" for phrase in source.presentation_phrases],
                learning_objective=f"Master advanced {source.learning_objective}",
                story_guidance=f"Add cultural nuance: {source.story_guidance}"
            )
            
            return new_day_data
        
        deeper_day = generate_deeper_day(base_curriculum, source_day=2, new_day=6)
        
        assert deeper_day.day == 6
        assert "Advanced:" in deeper_day.title
        assert all("advanced_" in colloc for colloc in deeper_day.collocations)  # Enhanced vocabulary
        assert "Master advanced" in deeper_day.learning_objective  # Enhanced objective
        assert "cultural nuance" in deeper_day.story_guidance  # Added sophistication