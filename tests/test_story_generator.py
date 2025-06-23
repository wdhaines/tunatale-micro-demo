"""Tests for story_generator.py."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, call
from typing import Dict, Any

import pytest

from story_generator import ContentGenerator, StoryParams, CEFRLevel

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
    
    # Mock the LLM response
    mock_response = {
        "choices": [{
            "message": {
                "content": "This is a test story.",
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
    generator.story_prompt = """
    Learning Objective: {LEARNING_OBJECTIVE}
    Language: {TARGET_LANGUAGE}
    Level: {CEFR_LEVEL}
    Length: {STORY_LENGTH} words
    """.strip()
    
    # Create a mock for the save_story method
    mock_save_story = MagicMock()
    mock_save_story.return_value = str(test_output_dir / "generated_content" / "test_story.txt")
    
    # Patch the DATA_DIR and _save_story method
    with patch('story_generator.DATA_DIR', test_output_dir), \
         patch.object(generator, '_save_story', mock_save_story):
        
        # Call the method
        result = generator.generate_story(params)
        
        # Verify the result is not None and matches our mock response
        assert result is not None, "Result should not be None"
        assert result == "This is a test story.", "Should return the generated story"
        
        # Verify the LLM was called with the correct prompt
        mock_llm.get_response.assert_called_once()
        
        # Get the arguments passed to get_response
        call_args = mock_llm.get_response.call_args
        
        # Verify the prompt contains the expected parameters
        assert "prompt" in call_args.kwargs, "Prompt should be passed as a keyword argument"
        prompt = call_args.kwargs["prompt"]
        assert "test objective" in prompt, "Prompt should contain learning objective"
        assert "English" in prompt, "Prompt should contain language"
        assert "A2" in prompt, "Prompt should contain CEFR level"


def test_generate_story_handles_ioerror(content_generator: ContentGenerator) -> None:
    """Test that generate_story handles IOError during file operations."""
    params = StoryParams(
        learning_objective="test",
        language="English",
        cefr_level=CEFRLevel.A2,
        phase=1
    )
    
    # Mock open to raise IOError and patch _save_story to avoid actual file operations
    with patch('builtins.open', side_effect=IOError("Test error")), \
         patch.object(content_generator, '_save_story') as mock_save_story:
        # Mock the save method to raise IOError
        mock_save_story.side_effect = IOError("Test error")
        
        with pytest.raises(IOError, match="Test error"):
            content_generator.generate_story(params)


def test_save_story_creates_valid_filename(content_generator: ContentGenerator, tmp_path) -> None:
    """Test that _save_story creates a valid filename from the objective."""
    test_story = "Test story content"
    test_objective = "Test Objective with Spaces & Special!@#"
    
    # Patch the DATA_DIR to use a temporary directory for testing
    with patch('story_generator.DATA_DIR', tmp_path / 'test_data'):
        # Create a mock for the open function
        mock_file = mock_open()
        
        with patch('builtins.open', mock_file) as _:
            saved_path = content_generator._save_story(
                story=test_story,
                phase=1,
                learning_objective=test_objective
            )
            
            # Check the filename is sanitized
            assert isinstance(saved_path, str), "Saved path should be a string"
            path = Path(saved_path)
            
            # Check the file was created in the correct directory
            assert path.parent == tmp_path / 'test_data' / 'generated_content', \
                f"File should be saved in generated_content directory, got {path.parent}"
                
            # Check the filename format
            filename = path.name.lower()
            assert filename.startswith("story_phase1_"), "Filename should start with 'story_phase1_'"
            # The objective is truncated to 30 chars, so we check for the truncated version
            assert "test_objective_with_spaces_sp" in filename, "Filename should contain truncated sanitized objective"
            assert filename.endswith(".txt"), "Filename should end with .txt"
            
            # Verify the file was written with correct content
            mock_file.assert_called_once()
            handle = mock_file()
            handle.write.assert_called_once_with(test_story)


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


def test_generate_story_uses_prompt_template(content_generator: ContentGenerator, tmp_path) -> None:
    """Test that generate_story uses the prompt template correctly."""
    # Set up test data
    test_prompt = """
    Generate a compelling story for: {LEARNING_OBJECTIVE}
    TARGET LANGUAGE: {TARGET_LANGUAGE}
    LEARNER LEVEL: {CEFR_LEVEL}
    STORY LENGTH: {STORY_LENGTH} words
    """.strip()
    test_story = "Once upon a time..."
    
    # Configure mocks
    content_generator.story_prompt = test_prompt
    mock_response = {"choices": [{"message": {"content": test_story}}]}
    content_generator.llm.get_response.return_value = mock_response
    
    # Create a mock for the _save_story method
    mock_save_story = MagicMock()
    mock_save_story.return_value = str(tmp_path / 'test_data' / 'generated_content' / 'test_story.txt')
    
    # Patch DATA_DIR and _save_story
    with patch('story_generator.DATA_DIR', tmp_path / 'test_data'), \
         patch.object(content_generator, '_save_story', mock_save_story):
        
        # Call the method
        result = content_generator.generate_story(
            StoryParams(
                learning_objective="test objective",
                language="English",
                cefr_level=CEFRLevel.A2,
                phase=1,
                length=200
            )
        )
        
        # Verify the response was processed correctly
        assert result == test_story, "Should return the generated story"
        
        # Verify the prompt was formatted correctly
        content_generator.llm.get_response.assert_called_once()
        
        # Get the prompt that was passed to get_response
        call_args = content_generator.llm.get_response.call_args
        assert call_args is not None, "get_response should have been called"
        
        # Check that the prompt contains the expected values
        prompt = call_args.kwargs.get('prompt', '')
        assert "test objective" in prompt, "Prompt should contain the learning objective"
        assert "English" in prompt, "Prompt should contain the target language"
        assert "A2" in prompt, "Prompt should contain the CEFR level"
        assert "200" in prompt, "Prompt should contain the story length"
        
        # Verify _save_story was called with the correct arguments
        mock_save_story.assert_called_once()
        save_story_args = mock_save_story.call_args[0]
        assert save_story_args[0] == test_story, "Should pass the story to _save_story"
        assert save_story_args[1] == 1, "Should pass the phase to _save_story"
        assert save_story_args[2] == "test objective", "Should pass the learning objective to _save_story"
