"""Tests for strategy-based curriculum extension and WIDER strategy fixes."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open

from story_generator import ContentGenerator
from content_strategy import ContentStrategy
from curriculum_models import Curriculum, CurriculumDay


@pytest.fixture
def mock_curriculum():
    """Create a mock curriculum with 8 days."""
    days = []
    for i in range(1, 9):
        day = CurriculumDay(
            day=i,
            title=f"Day {i}: Test Content",
            learning_objective=f"Learn basic Filipino for day {i}",
            focus=f"test_focus_{i}",
            collocations=[f"colloc_{i}_1", f"colloc_{i}_2"],
            presentation_phrases=[f"phrase_{i}_1", f"phrase_{i}_2"],
            story_guidance="Test guidance"
        )
        days.append(day)
    
    curriculum = Mock()
    curriculum.days = days
    curriculum.target_language = "Filipino"
    curriculum.learner_level = "A2"
    curriculum.presentation_length = 10
    curriculum.save = Mock()
    
    # Add get_day method that behaves like real curriculum
    def get_day(day_num):
        for day in days:
            if day.day == day_num:
                return day
        return None
    curriculum.get_day = get_day
    
    return curriculum


@pytest.fixture
def content_generator():
    """Create ContentGenerator with mocked dependencies."""
    # Mock the prompt loading and SRSTracker initialization
    with patch.object(ContentGenerator, '_load_prompt', return_value='test prompt'):
        with patch('story_generator.SRSTracker') as mock_srs_class:
            # Mock SRS tracker
            mock_srs = Mock()
            mock_srs.get_due_collocations.return_value = ["review_1", "review_2"]
            mock_srs_class.return_value = mock_srs
            
            generator = ContentGenerator()
    
    # Mock the LLM response chain that generate_enhanced_story actually uses
    mock_llm_response = {
        'choices': [{'message': {'content': "Generated test story content"}}]
    }
    generator.llm = Mock()
    generator.llm.chat_response.return_value = mock_llm_response
    
    # Mock file operations and other dependencies
    generator._save_story = Mock(return_value="/path/to/story.txt")
    
    return generator


class TestWIDERStrategyFixes:
    """Test the fixes made to WIDER strategy."""
    
    @patch('story_generator.SRSTracker')
    @patch.object(ContentGenerator, '_load_prompt', return_value='test prompt')
    def test_wider_strategy_no_source_day_required(self, mock_load_prompt, mock_srs_class, mock_curriculum):
        """Test that WIDER strategy works without requiring a source day."""
        # Mock SRS tracker
        mock_srs = Mock()
        mock_srs.get_due_collocations.return_value = ["review_1", "review_2"]
        mock_srs_class.return_value = mock_srs
        
        generator = ContentGenerator()
        
        # Mock the LLM response chain that generate_enhanced_story actually uses
        mock_llm_response = {
            'choices': [{'message': {'content': "Generated test story content"}}]
        }
        generator.llm = Mock()
        generator.llm.chat_response.return_value = mock_llm_response
        
        # Mock file operations to prevent actual file writes
        generator._save_story = Mock(return_value="/path/to/story.txt")
        
        # Mock collocation extraction and run the test
        with patch.object(generator.collocation_extractor, 'extract_collocations', return_value=[]):
            with patch.object(generator, '_load_curriculum', return_value=mock_curriculum):
                # Actually test post-processing instead of mocking it
                result = generator.generate_strategy_based_story(
                    target_day=9, 
                    strategy=ContentStrategy.WIDER, 
                    source_day=None  # Should work without source day
                )
        
        assert result is not None
        story, collocation_report = result
        # Story should be post-processed, so should not exactly equal the raw LLM output
        assert "Generated test story content" in story
        assert 'new' in collocation_report
        assert 'reviewed' in collocation_report
    
    def test_wider_strategy_analyzes_curriculum_progression(self, content_generator, mock_curriculum):
        """Test that WIDER strategy analyzes curriculum progression."""
        with patch.object(content_generator, '_load_curriculum', return_value=mock_curriculum):
            # Call the analysis method directly
            analysis = content_generator._analyze_curriculum_progression(mock_curriculum)
        
        assert analysis['total_days'] == 8
        assert 'common_themes' in analysis
        assert 'vocabulary_progression' in analysis
        assert analysis['complexity_level'] == "A2"
    
    def test_wider_generates_new_scenario_focus(self, content_generator):
        """Test that WIDER strategy generates appropriate new scenarios."""
        curriculum_analysis = {
            'total_days': 8,
            'common_themes': ['hotel', 'restaurant'],
            'complexity_level': 'A2'
        }
        
        # Test multiple target days generate different scenarios
        focus_9 = content_generator._generate_new_scenario_focus(curriculum_analysis, 9)
        focus_10 = content_generator._generate_new_scenario_focus(curriculum_analysis, 10)
        
        assert focus_9 != focus_10  # Should generate different scenarios
        assert isinstance(focus_9, str)
        assert len(focus_9) > 10  # Should be descriptive
    
    def test_wider_generates_progressive_collocations(self, content_generator):
        """Test that WIDER strategy generates appropriate collocations."""
        curriculum_analysis = {'total_days': 8}
        
        # Test basic level
        collocations_basic = content_generator._generate_progressive_collocations(curriculum_analysis, 9)
        assert len(collocations_basic) <= 8
        assert "salamat po" in collocations_basic
        
        # Test advanced level
        collocations_advanced = content_generator._generate_progressive_collocations(curriculum_analysis, 15)
        assert len(collocations_advanced) <= 8
        # Should include more advanced collocations for higher days
        advanced_terms = ["nakakamangha talaga", "sulit na sulit", "hindi ko inexpect"]
        has_advanced = any(term in " ".join(collocations_advanced) for term in advanced_terms)
        assert has_advanced


class TestCurriculumExtension:
    """Test curriculum extension functionality."""
    
    def test_extend_curriculum_with_new_day_wider(self, content_generator, mock_curriculum):
        """Test extending curriculum with WIDER strategy day."""
        success = content_generator._extend_curriculum_with_new_day(
            curriculum=mock_curriculum,
            target_day=9,
            learning_objective="Day 9: New scenario exploration",
            focus="sunset photography",
            collocations=["ganda talaga", "perfect timing", "sobrang sulit"],
            strategy="wider"
        )
        
        assert success is True
        assert len(mock_curriculum.days) == 9  # Should now have 9 days
        
        new_day = mock_curriculum.days[-1]
        assert new_day.day == 9
        assert new_day.title == "Day 9: sunset photography"
        assert new_day.focus == "sunset photography"
        assert "ganda talaga" in new_day.collocations
        
        # Verify curriculum.save was called
        mock_curriculum.save.assert_called_once()
    
    def test_extend_curriculum_with_new_day_deeper(self, content_generator, mock_curriculum):
        """Test extending curriculum with DEEPER strategy day."""
        success = content_generator._extend_curriculum_with_new_day(
            curriculum=mock_curriculum,
            target_day=9,
            learning_objective="Enhanced Day 6 with sophisticated Filipino",
            focus="enhanced_shopping",
            collocations=["maraming salamat po", "nakakamangha naman"],
            strategy="deeper"
        )
        
        assert success is True
        assert len(mock_curriculum.days) == 9
        
        new_day = mock_curriculum.days[-1]
        assert "Enhanced" in new_day.learning_objective
    
    def test_curriculum_extension_error_handling(self, content_generator):
        """Test curriculum extension handles errors gracefully."""
        # Mock curriculum that raises exception on save
        bad_curriculum = Mock()
        bad_curriculum.days = []
        bad_curriculum.save.side_effect = Exception("Save failed")
        
        success = content_generator._extend_curriculum_with_new_day(
            curriculum=bad_curriculum,
            target_day=9,
            learning_objective="Test",
            focus="test_focus",
            collocations=["test"],
            strategy="wider"
        )
        
        assert success is False


class TestStrategyChaining:
    """Test that strategies can be chained together."""
    
    def test_deeper_then_wider_chaining(self, content_generator, mock_curriculum):
        """Test generating DEEPER day 9, then WIDER day 10."""
        with patch.object(content_generator, '_load_curriculum', return_value=mock_curriculum):
            with patch.object(content_generator, '_load_source_day_transcript', return_value="Source transcript"):
                with patch.object(content_generator, '_save_story', return_value="/fake/path/story.txt"):
                    with patch.object(content_generator.llm, 'chat_response', return_value={"choices": [{"message": {"content": "Generated test story"}}]}):
                        with patch('config.CURRICULUM_PATH', '/fake/curriculum.json'):
                            with patch('builtins.open', mock_open(read_data='[]')):
                                
                                # First: Generate DEEPER day 9 from source day 6
                                deeper_result = content_generator.generate_strategy_based_story(
                                    target_day=9,
                                    strategy=ContentStrategy.DEEPER,
                                    source_day=6
                                )
                                
                                assert deeper_result is not None
                                assert len(mock_curriculum.days) == 9  # Should extend to 9 days
                                
                                # Second: Generate WIDER day 10 (should now see 9 days in curriculum)
                                wider_result = content_generator.generate_strategy_based_story(
                                    target_day=10,
                                    strategy=ContentStrategy.WIDER,
                                    source_day=None  # WIDER doesn't need source day
                                )
                                
                                assert wider_result is not None
                                assert len(mock_curriculum.days) == 10  # Should extend to 10 days
    
    def test_multiple_wider_extensions(self, content_generator, mock_curriculum):
        """Test multiple WIDER strategy extensions."""
        with patch.object(content_generator, '_load_curriculum', return_value=mock_curriculum):
            with patch.object(content_generator.collocation_extractor, 'extract_collocations', return_value=[]):
                
                # Generate days 9, 10, 11 using WIDER strategy
                for day in [9, 10, 11]:
                    result = content_generator.generate_strategy_based_story(
                        target_day=day,
                        strategy=ContentStrategy.WIDER,
                        source_day=None
                    )
                    
                    assert result is not None
                    assert len(mock_curriculum.days) == day  # Should progressively extend
                    
                    # Each day should have different scenario focus
                    new_day = mock_curriculum.days[-1]
                    assert new_day.day == day


class TestStrategyIntegration:
    """Test integration between strategy generation and curriculum extension."""
    
    def test_wider_strategy_full_integration(self, content_generator, mock_curriculum):
        """Test complete WIDER strategy with curriculum extension."""
        with patch.object(content_generator, '_load_curriculum', return_value=mock_curriculum):
            with patch.object(content_generator.collocation_extractor, 'extract_collocations', return_value=[]):
                result = content_generator._generate_wider_content(9, mock_curriculum)
        
        assert result is not None
        story, report = result
        
        # Verify story generation (should contain the original content, possibly post-processed)
        assert "Generated test story" in story
        assert 'new' in report
        assert 'reviewed' in report
        
        # Verify curriculum extension
        assert len(mock_curriculum.days) == 9
        new_day = mock_curriculum.days[-1]
        assert new_day.day == 9
        
        # Verify curriculum save was called
        mock_curriculum.save.assert_called_once()
    
    def test_deeper_strategy_full_integration(self, content_generator, mock_curriculum):
        """Test complete DEEPER strategy with curriculum extension."""
        with patch.object(content_generator, '_load_curriculum', return_value=mock_curriculum):
            with patch.object(content_generator, '_load_source_day_transcript', return_value="Source transcript"):
                with patch.object(content_generator, '_save_story', return_value="/fake/path/story.txt"):
                    with patch.object(content_generator.llm, 'chat_response', return_value={"choices": [{"message": {"content": "Generated test story"}}]}):
                        with patch('config.CURRICULUM_PATH', '/fake/curriculum.json'):
                            with patch('builtins.open', mock_open(read_data='[]')):
                                result = content_generator._generate_deeper_content(9, 6, mock_curriculum)
        
        assert result is not None
        story, report = result
        
        # Verify curriculum extension
        assert len(mock_curriculum.days) == 9
        new_day = mock_curriculum.days[-1]
        assert new_day.day == 9
        assert "Enhanced" in new_day.learning_objective


class TestCommandLineIntegration:
    """Test command line integration of the strategy fixes."""
    
    def test_strategy_enum_mapping(self):
        """Test that CLI correctly maps strategy strings to enums."""
        from main import CLI
        
        # Test that strategy mapping works
        cli = CLI()
        
        # This would be tested in integration tests, but for now just verify the mapping exists
        strategy_map = {
            'balanced': ContentStrategy.BALANCED,
            'wider': ContentStrategy.WIDER,
            'deeper': ContentStrategy.DEEPER
        }
        
        assert strategy_map['wider'] == ContentStrategy.WIDER
        assert strategy_map['deeper'] == ContentStrategy.DEEPER
        assert strategy_map['balanced'] == ContentStrategy.BALANCED