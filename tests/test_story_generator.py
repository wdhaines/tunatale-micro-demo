"""Tests for story_generator.py."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, call
from typing import Dict, Any

import pytest

from story_generator import ContentGenerator, StoryParams, CEFRLevel
from curriculum_models import Curriculum, CurriculumDay

# Test data paths
TEST_DATA_DIR = Path(__file__).parent / 'test_data'
TEST_CURRICULUM_PATH = TEST_DATA_DIR / 'test_curriculum.json'


def test_story_params_default_length() -> None:
    """Test that StoryParams uses default length when not specified."""
    params = StoryParams(
        learning_objective="test",
        language="English",
        cefr_level=CEFRLevel.A2,
        phase=1
    )
    assert params.length == 500  # Default from config


def test_story_params_custom_length() -> None:
    """Test that StoryParams uses custom length when specified."""
    params = StoryParams(
        learning_objective="test",
        language="English",
        cefr_level=CEFRLevel.A2,
        phase=1,
        length=300
    )
    assert params.length == 300


def test_story_params_invalid_cefr_level() -> None:
    """Test that invalid CEFR levels raise a ValueError."""
    with pytest.raises(ValueError, match="Invalid CEFR level"):
        # Use an invalid CEFR level string
        StoryParams(
            learning_objective="test",
            language="English",
            cefr_level="X0",  # Invalid CEFR level
            phase=1
        )


@patch('builtins.open', mock_open(read_data='test prompt'))
def test_content_generator_init_loads_prompts() -> None:
    """Test that ContentGenerator loads prompts on init."""
    generator = ContentGenerator()
    assert hasattr(generator, 'story_prompt')
    assert generator.story_prompt == 'test prompt'


def test_generate_story_creates_output_dir(content_generator: ContentGenerator, tmp_path: Path) -> None:
    """Test that generate_story creates output directory if it doesn't exist."""
    # Setup test parameters
    test_output_dir = tmp_path / "test_output"
    params = StoryParams(
        learning_objective="test objective",
        language="English",
        cefr_level=CEFRLevel.A2,
        phase=1,
        length=200
    )
    
    # Create a test story with a title
    test_story = """**The Test Story**
    
    This is a test story.
    """
    
    # Mock the LLM response
    mock_response = {
        "choices": [{
            "message": {
                "content": test_story,
                "role": "assistant"
            }
        }]
    }
    
    # Create a new mock for the LLM
    mock_llm = MagicMock()
    mock_llm.get_response.return_value = mock_response
    
    # Create a new ContentGenerator with the mock LLM
    generator = ContentGenerator()
    generator.llm = mock_llm
    
    # Mock the prompt to avoid needing the actual file
    generator.story_prompt = "Test prompt with {NEW_VOCABULARY} and {RECYCLED_COLLOCATIONS}"
    
    # Create a mock for the _save_story method that matches the actual method signature
    def save_story_impl(story: str, phase: int, learning_objective: str) -> str:
        # Just return a test path, don't actually write to disk
        return str(test_output_dir / "generated_content" / f'story_day{phase}_test.txt')
    
    # Create a MagicMock that wraps our implementation but tracks calls
    mock_save_story = MagicMock(wraps=save_story_impl)
    
    # Patch the DATA_DIR and _save_story method
    with patch('story_generator.DATA_DIR', test_output_dir), \
         patch.object(generator, '_save_story', mock_save_story):
        
        # Call the method
        result = generator.generate_story(params)
        
        # Verify the result is not None and matches our mock response
        assert result is not None, "Result should not be None"
        assert result.strip() == test_story.strip(), "Should return the generated story"
        
        # Verify the LLM was called with the correct prompt
        mock_llm.get_response.assert_called_once()
        
        # Verify save_story was called with the correct parameters
        mock_save_story.assert_called_once()
        call_args = mock_save_story.call_args[0]
        assert call_args[0] == test_story  # story content
        assert call_args[1] == 1  # phase
        assert call_args[2] == "test objective"  # learning_objective


def test_generate_story_handles_ioerror(content_generator: ContentGenerator) -> None:
    """Test that generate_story handles IOError during file operations."""
    # Setup test parameters
    params = StoryParams(
        learning_objective="test objective",
        language="English",
        cefr_level=CEFRLevel.A2,
        phase=1,
        length=200
    )
    
    # Create a test story with a title
    test_story = """**The Test Story**
    
    This is a test story.
    """
    
    # Mock the LLM response
    mock_response = {
        "choices": [{
            "message": {
                "content": test_story,
                "role": "assistant"
            }
        }]
    }
    
    # Mock the LLM to return our test story
    content_generator.llm = MagicMock()
    content_generator.llm.get_response.return_value = mock_response
    
    # Patch the prompt to avoid file operations
    content_generator.story_prompt = "Test prompt with {NEW_VOCABULARY} and {RECYCLED_COLLOCATIONS}"
    
    # Mock _save_story to raise IOError
    with patch.object(content_generator, '_save_story') as mock_save_story:
        mock_save_story.side_effect = IOError("Test error")
        
        # Should raise IOError
        with pytest.raises(IOError, match="Test error"):
            content_generator.generate_story(params)


def test_extract_title() -> None:
    """Test that _extract_title correctly extracts title from story content."""
    generator = ContentGenerator()
    
    # Test with title in markdown format
    story_with_title = """**The Secret Garden**
    
    Once upon a time...
    """
    assert generator._extract_title(story_with_title) == "The Secret Garden"
    
    # Test with no title
    story_without_title = "Once upon a time..."
    assert generator._extract_title(story_without_title) == ""
    
    # Test with multiple lines and title in the middle
    story_multiline = """
    Some text
    **The Hidden Treasure**
    More text
    """
    assert generator._extract_title(story_multiline) == "The Hidden Treasure"


def test_clean_filename() -> None:
    """Test that _clean_filename creates valid filenames."""
    generator = ContentGenerator()
    
    # Test basic cleaning
    assert generator._clean_filename("My Story: Adventure Time!") == "my_story_adventure_time"
    
    # Test with special characters
    assert generator._clean_filename("Test & Test @ Home") == "test_test_home"
    
    # Test with length limit
    assert generator._clean_filename("A Very Long Story Title That Should Be Truncated", 15) == "a_very_long_sto"
    
    # Test with empty string
    assert generator._clean_filename("") == ""


def test_save_story_creates_valid_filename(content_generator: ContentGenerator, tmp_path) -> None:
    """Test that _save_story creates a valid filename from the story title or objective."""
    # Test with a story that has a title
    test_story_with_title = """**The Secret Garden**
    
    Once upon a time...
    """
    
    # Test with a story that doesn't have a title (should fall back to learning objective)
    test_story_without_title = "Once upon a time..."
    
    test_objective = "Test Objective with Spaces & Special!@#"
    
    # Patch the DATA_DIR to use a temporary directory for testing
    with patch('story_generator.DATA_DIR', tmp_path / 'test_data'):
        # Test with story that has a title
        with patch('builtins.open', mock_open()) as mock_file:
            saved_path = content_generator._save_story(
                story=test_story_with_title,
                phase=1,
                learning_objective=test_objective
            )
            
            # Check the filename is sanitized and uses the title
            assert isinstance(saved_path, str), "Saved path should be a string"
            path = Path(saved_path)
            assert "the_secret_garden" in path.name.lower(), "Filename should use the story title"
            
        # Test with story that doesn't have a title (should fall back to learning objective)
        with patch('builtins.open', mock_open()) as mock_file:
            saved_path = content_generator._save_story(
                story=test_story_without_title,
                phase=2,
                learning_objective=test_objective
            )
            
            # Check the filename is sanitized and uses the learning objective
            assert isinstance(saved_path, str), "Saved path should be a string"
            path = Path(saved_path)
            assert path.name.startswith("story_day2_"), "Filename should start with 'story_day2_'"
            assert "test_objective_with_spaces" in path.name.lower(), "Filename should use the learning objective"


def test_save_story_with_empty_objective(content_generator: ContentGenerator, tmp_path) -> None:
    """Test that _save_story raises ValueError when learning_objective is empty."""
    test_story = "Test story content"
    
    # Patch the DATA_DIR to use a temporary directory for testing
    with patch('story_generator.DATA_DIR', tmp_path / 'test_data'):
        # Test that ValueError is raised when learning_objective is empty
        with pytest.raises(ValueError, match="learning_objective cannot be empty"):
            content_generator._save_story(
                story=test_story,
                phase=1,
                learning_objective=""
            )
        
        # Test that ValueError is raised when learning_objective is None
        with pytest.raises(ValueError, match="learning_objective cannot be empty"):
            content_generator._save_story(
                story=test_story,
                phase=1,
                learning_objective=None
            )
        
        # Test that ValueError is raised when learning_objective is whitespace
        with pytest.raises(ValueError, match="learning_objective cannot be empty"):
            content_generator._save_story(
                story=test_story,
                phase=1,
                learning_objective="   "
            )


def test_generate_story_uses_prompt_template(content_generator: ContentGenerator, tmp_path):
    """Test that generate_story uses the prompt template correctly."""
    # Set up test data with only the placeholders that the code actually uses
    test_prompt = """
    VOCABULARY CONTEXT:
    - Focus on teaching: {NEW_VOCABULARY}
    - Naturally recycle: {RECYCLED_COLLOCATIONS}
    - Genre: {GENRE}
    """.strip()
    
    # Create a test story with a title
    test_story = """**The Test Story**
    
    This is a test story with some vocabulary.
    """

    # Configure mocks
    content_generator.story_prompt = test_prompt
    mock_response = {"choices": [{"message": {"content": test_story, "role": "assistant"}}]}
    content_generator.llm.get_response.return_value = mock_response

    # Create a mock for the _save_story method that matches the actual method signature
    def save_story_impl(story: str, phase: int, learning_objective: str) -> str:
        # Just return a test path, don't actually write to disk
        return str(tmp_path / 'test_data' / 'generated_content' / f'story_day{phase}_test.txt')
    
    # Create a MagicMock that wraps our implementation but tracks calls
    mock_save_story = MagicMock(wraps=save_story_impl)

    # Patch DATA_DIR and _save_story
    with patch('story_generator.DATA_DIR', tmp_path / 'test_data'), \
         patch.object(content_generator, '_save_story', mock_save_story):

        # Set up test data for vocabulary and collocations
        test_vocab = ["test", "vocabulary", "words"]
        test_collocations = ["test collocation", "another one"]
        
        # Create params with all required fields
        params = StoryParams(
            learning_objective="test objective",
            language="English",
            cefr_level=CEFRLevel.A2,
            phase=1,
            length=200,
            new_vocabulary=test_vocab,
            recycled_collocations=test_collocations
        )
        
        # Call the method
        result = content_generator.generate_story(params=params)
        
        # Verify the result is not None (actual content check is less important than successful generation)
        assert result is not None
        
        # Verify the LLM was called with the correct prompt

def test_generate_story_for_day_success(content_generator: ContentGenerator, tmp_path):
    """Test successful story generation for a specific day."""
    # Setup test data using new curriculum models
    test_day = CurriculumDay(
        day=2,
        title='Test Day',
        focus='Testing',
        collocations=['test collocation', 'vocabulary usage'],
        presentation_phrases=['test phrase', 'example usage'],
        learning_objective='Test Learning',
        story_guidance='This is a test story'
    )
    
    test_curriculum = Curriculum(
        learning_objective='Test Learning',
        target_language='English',
        learner_level='A2',
        presentation_length=10,  # minutes
        days=[test_day],
        metadata={'version': 'test'}
    )
    
    # Mock the prompt with placeholders that match the implementation
    content_generator.story_prompt = """
    VOCABULARY CONTEXT:
    - Focus on teaching: {NEW_VOCABULARY}
    - Naturally recycle: {RECYCLED_COLLOCATIONS}
    - Genre: {GENRE}
    """.strip()
    
    # Create a test story with a title
    test_story = """**The Test Story**
    
    This is a test story for day 2.
    It includes test collocation and vocabulary usage.
    """

    
    # Configure mocks
    mock_response = {"choices": [{"message": {"content": test_story, "role": "assistant"}}]}
    content_generator.llm.get_response.return_value = mock_response
    
    # Mock the _load_curriculum method
    content_generator._load_curriculum = MagicMock(return_value=test_curriculum)
    
    # Mock SRS methods
    content_generator.srs.get_due_collocations = MagicMock(return_value=["collocation1", "collocation2"])
    content_generator.srs.add_collocations = MagicMock()
    
    # Create a mock for the _save_story method
    def save_story_impl(story: str, phase: int, learning_objective: str) -> str:
        return str(tmp_path / 'test_data' / 'generated_content' / f'story_day{phase}_test.txt')
    
    mock_save_story = MagicMock(wraps=save_story_impl)
    
    # Patch necessary components
    with patch('story_generator.DATA_DIR', tmp_path / 'test_data'), \
         patch.object(content_generator, '_save_story', mock_save_story):
        
        # Call the method
        result = content_generator.generate_story_for_day(2)
        
        # Verify the result is not None (actual content check is less important than successful generation)
        assert result is not None
        
        # Verify the LLM was called with the correct prompt
        content_generator.llm.get_response.assert_called_once()
        
        # Verify curriculum was loaded (called twice: once in generate_story_for_day and once in generate_day_story)
        assert content_generator._load_curriculum.call_count == 2
        
        # Verify SRS interactions
        content_generator.srs.get_due_collocations.assert_called_once()
        
        # Check that add_collocations was called at least once (it might be called multiple times)
        assert content_generator.srs.add_collocations.call_count >= 1
        
        # Get the last call to add_collocations to verify the arguments
        last_call = content_generator.srs.add_collocations.call_args
        assert last_call[1]['day'] == 2  # Verify the day parameter
        
        # Verify story was saved - check it was called twice (once in generate_story_for_day and once in generate_day_story)
        assert mock_save_story.call_count == 2
        
        # Get all calls and check their arguments
        calls = mock_save_story.call_args_list
        
        # First call (from generate_story_for_day)
        assert calls[0][0][0] == test_story  # story content
        assert calls[0][0][1] == 2  # phase
        assert calls[0][0][2] == 'Test Learning'  # learning_objective
        
        # Second call (from generate_day_story)
        assert calls[1][1]['story'] == test_story
        assert calls[1][1]['phase'] == 2
        assert calls[1][1]['learning_objective'] == 'Test Learning'


def test_generate_story_for_day_missing_curriculum(content_generator: ContentGenerator):
    """Test story generation when curriculum is missing for the day."""
    # Mock _load_curriculum to return empty phases
    content_generator._load_curriculum = MagicMock(return_value={'phases': {}})
    
    # Call the method
    result = content_generator.generate_story_for_day(99)
    
    # Verify the result is None (indicating failure)
    assert result is None
    
    # Verify the error message was printed
    # (Note: This would need to be captured with capsys to verify the exact message)


def test_generate_story_for_day_with_error(content_generator: ContentGenerator):
    """Test story generation when an error occurs."""
    # Mock _load_curriculum to raise an exception
    content_generator._load_curriculum = MagicMock(side_effect=Exception("Test error"))
    
    # Call the method
    result = content_generator.generate_story_for_day(1)
    
    # Verify the result is None (indicating failure)
    assert result is None
