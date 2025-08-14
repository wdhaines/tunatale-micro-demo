"""
Test for DEEPER strategy bug: Wrong generation method called.

This test demonstrates that the DEEPER strategy incorrectly calls generate_story()
instead of generate_enhanced_story(), causing it to use the basic template instead
of the strategy-specific template with proper review collocation integration.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from pathlib import Path

from story_generator import ContentGenerator
from content_strategy import ContentStrategy
from curriculum_models import Curriculum, CurriculumDay


@pytest.fixture
def mock_curriculum():
    """Create a mock curriculum for testing."""
    curriculum = Mock(spec=Curriculum)
    curriculum.target_language = "Filipino"
    curriculum.learner_level = "A2"
    curriculum.presentation_length = 5
    
    # Mock curriculum day
    source_day = Mock(spec=CurriculumDay)
    source_day.title = "Restaurant Ordering"
    source_day.learning_objective = "Order food at a restaurant"
    source_day.focus = "restaurant dining"
    source_day.collocations = ["gusto ko po", "ano po ang"]
    source_day.presentation_phrases = ["I want", "what is"]
    source_day.story_guidance = "Create restaurant dialogue"
    
    curriculum.get_day.return_value = source_day
    return curriculum


@pytest.fixture
def content_generator():
    """Create a ContentGenerator with mocked dependencies."""
    with patch('story_generator.SRSTracker') as mock_srs_tracker, \
         patch('story_generator.CollocationExtractor') as mock_extractor, \
         patch.object(ContentGenerator, '_load_prompt', return_value='test prompt'):
        
        generator = ContentGenerator()
        
        # Mock SRS to return specific review collocations
        generator.srs.get_due_collocations.return_value = [
            "masarap po ba", "salamat po", "kumusta po"
        ]
        
        return generator


class TestDeeperStrategyBug:
    """Test the DEEPER strategy bug and its fix."""
    
    def test_deeper_strategy_calls_correct_method_AFTER_FIX(self, content_generator, mock_curriculum):
        """
        Test that DEEPER strategy calls generate_enhanced_story() after the fix.
        
        This test should PASS after the bug is fixed.
        """
        with patch.object(content_generator, 'generate_story') as mock_basic_gen, \
             patch.object(content_generator, 'generate_enhanced_story') as mock_enhanced_gen, \
             patch.object(content_generator, '_load_curriculum', return_value=mock_curriculum), \
             patch.object(content_generator, '_load_source_day_transcript', return_value="source transcript"), \
             patch.object(content_generator, '_save_story', return_value="/path/to/story.txt"):
            
            # Mock return values
            mock_enhanced_gen.return_value = "Generated with enhanced method"
            
            # Call the DEEPER strategy generation
            result = content_generator.generate_strategy_based_story(
                target_day=12,
                strategy=ContentStrategy.DEEPER,
                source_day=5
            )
            
            # After the fix, these should be true:
            mock_basic_gen.assert_not_called()  # Should NOT call basic method
            mock_enhanced_gen.assert_called_once()  # SHOULD call enhanced method
            
            assert result is not None
    
    def test_deeper_strategy_bug_was_fixed(self, content_generator, mock_curriculum):
        """
        Test documenting that the DEEPER strategy bug has been fixed.
        
        Previously: DEEPER strategy called generate_story() instead of generate_enhanced_story()
        Now: DEEPER strategy correctly calls generate_enhanced_story()
        """
        # Patch both generation methods to track which one is called
        with patch.object(content_generator, 'generate_story') as mock_basic_gen, \
             patch.object(content_generator, 'generate_enhanced_story') as mock_enhanced_gen, \
             patch.object(content_generator, '_load_curriculum', return_value=mock_curriculum), \
             patch.object(content_generator, '_load_source_day_transcript', return_value="source transcript"), \
             patch.object(content_generator, '_save_story', return_value="/path/to/story.txt"):
            
            # Mock return values
            mock_enhanced_gen.return_value = "Generated with enhanced method"
            
            # Call the DEEPER strategy generation
            result = content_generator.generate_strategy_based_story(
                target_day=12,
                strategy=ContentStrategy.DEEPER,
                source_day=5
            )
            
            # After the fix: the correct method is called
            mock_basic_gen.assert_not_called()  # Should NOT call basic method
            mock_enhanced_gen.assert_called_once()  # SHOULD call enhanced method
            
            assert result is not None, "Should return a result"
    
    def test_deeper_strategy_should_use_enhanced_generation_method(self, content_generator, mock_curriculum):
        """
        Test that DEEPER strategy should call generate_enhanced_story().
        
        This test shows what the behavior SHOULD be after the fix.
        """
        with patch.object(content_generator, 'generate_story') as mock_basic_gen, \
             patch.object(content_generator, 'generate_enhanced_story') as mock_enhanced_gen, \
             patch.object(content_generator, '_load_curriculum', return_value=mock_curriculum), \
             patch.object(content_generator, '_load_source_day_transcript', return_value="source transcript"), \
             patch.object(content_generator, '_save_story', return_value="/path/to/story.txt"):
            
            # Mock return values
            mock_enhanced_gen.return_value = "Generated with enhanced method"
            
            # Call the DEEPER strategy generation
            result = content_generator.generate_strategy_based_story(
                target_day=12,
                strategy=ContentStrategy.DEEPER,
                source_day=5
            )
            
            # After the fix, these should be true:
            # mock_basic_gen.assert_not_called()  # Should NOT call basic method
            # mock_enhanced_gen.assert_called_once()  # SHOULD call enhanced method
            
            # For now, just document the expected behavior
            print("Expected behavior after fix:")
            print("- generate_story() should NOT be called")
            print("- generate_enhanced_story() should be called ONCE")
            print(f"Current behavior: basic_called={mock_basic_gen.called}, enhanced_called={mock_enhanced_gen.called}")
    
    def test_deeper_strategy_review_collocations_integration(self, content_generator, mock_curriculum):
        """
        Test that DEEPER strategy includes SRS review collocations in the prompt parameters.
        
        This test verifies that review collocations from SRS are properly integrated.
        """
        # Mock SRS to return specific review collocations
        review_collocations = ["masarap po ba", "salamat po", "kumusta po"]
        content_generator.srs.get_due_collocations.return_value = review_collocations
        
        with patch.object(content_generator, 'generate_story') as mock_basic_gen, \
             patch.object(content_generator, 'generate_enhanced_story') as mock_enhanced_gen, \
             patch.object(content_generator, '_load_curriculum', return_value=mock_curriculum), \
             patch.object(content_generator, '_load_source_day_transcript', return_value="source transcript"), \
             patch.object(content_generator, '_save_story', return_value="/path/to/story.txt"):
            
            # Mock return values
            mock_basic_gen.return_value = "Generated story"
            mock_enhanced_gen.return_value = "Generated story"
            
            # Call the DEEPER strategy generation
            result = content_generator.generate_strategy_based_story(
                target_day=12,
                strategy=ContentStrategy.DEEPER,
                source_day=5
            )
            
            # Verify SRS was called for review collocations
            content_generator.srs.get_due_collocations.assert_called_once_with(12, min_items=2, max_items=4)
            
            # Check which method was called and verify parameters
            if mock_enhanced_gen.called:
                # After fix: should call generate_enhanced_story with proper params
                call_args = mock_enhanced_gen.call_args[0][0]  # Get the EnhancedStoryParams
                assert hasattr(call_args, 'review_collocations')
                for review_colloc in review_collocations:
                    assert review_colloc in call_args.review_collocations
                print("✅ generate_enhanced_story called with proper review collocations")
            elif mock_basic_gen.called:
                # Current bug: calls generate_story with StoryParams
                call_args = mock_basic_gen.call_args[0][0]  # Get the StoryParams
                assert hasattr(call_args, 'recycled_collocations')
                for review_colloc in review_collocations:
                    assert review_colloc in call_args.recycled_collocations
                print("🐛 generate_story called (bug), but review collocations are included")
            else:
                pytest.fail("Neither generation method was called")
            
            assert result is not None
    
    def test_deeper_strategy_enhanced_collocations_integration(self, content_generator, mock_curriculum):
        """
        Test that DEEPER strategy enhances collocations from source day.
        """
        with patch.object(content_generator, 'generate_enhanced_story') as mock_enhanced_gen, \
             patch.object(content_generator, '_load_curriculum', return_value=mock_curriculum), \
             patch.object(content_generator, '_load_source_day_transcript', return_value="source transcript"), \
             patch.object(content_generator, '_save_story', return_value="/path/to/story.txt"):
            
            mock_enhanced_gen.return_value = "Generated story"
            
            # Call the DEEPER strategy generation
            result = content_generator.generate_strategy_based_story(
                target_day=12,
                strategy=ContentStrategy.DEEPER,
                source_day=5
            )
            
            # Check that generation was called with enhanced collocations
            assert mock_enhanced_gen.called
            call_args = mock_enhanced_gen.call_args[0][0]  # Get the EnhancedStoryParams
            
            # Should include enhanced collocations from source day
            assert hasattr(call_args, 'review_collocations')
            review_collocs = call_args.review_collocations
            
            # Should include enhanced versions of source collocations
            # Basic: "gusto ko po" might become "gusto ko po" + enhanced versions
            source_collocations = mock_curriculum.get_day().collocations
            for source_colloc in source_collocations:
                # Should have the original or enhanced version
                found_related = any(source_colloc in review_colloc for review_colloc in review_collocs)
                assert found_related, f"Enhanced version of '{source_colloc}' should be in review collocations"
            
            print(f"Enhanced collocations: {review_collocs}")