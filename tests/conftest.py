"""Pytest configuration and fixtures for TunaTale tests."""
import json
from pathlib import Path
from typing import Generator, Any, Dict
from unittest.mock import MagicMock, mock_open, patch

import pytest
from _pytest.monkeypatch import MonkeyPatch

from story_generator import ContentGenerator, StoryParams, CEFRLevel
from llm_mock import MockLLM


@pytest.fixture
def tmp_story_dir(tmp_path: Path) -> Path:
    """Create and return a temporary directory for story output."""
    story_dir = tmp_path / "stories"
    story_dir.mkdir()
    return story_dir


@pytest.fixture
def sample_story_params() -> StoryParams:
    """Return sample story parameters for testing."""
    return StoryParams(
        learning_objective="test objective",
        language="English",
        cefr_level=CEFRLevel.A2,
        phase=1,
        length=200,
    )


@pytest.fixture
def mock_llm_response() -> Dict[str, Any]:
    """Return a mock LLM response for testing."""
    return {
        "choices": [
            {
                "message": {
                    "content": "This is a test story.\n\nIt has multiple paragraphs.\n\nAnd it ends here.",
                    "role": "assistant",
                }
            }
        ]
    }


@pytest.fixture
def mock_llm(mocker, mock_llm_response):
    """Patch the MockLLM class for testing."""
    with mocker.patch("story_generator.MockLLM") as mock:
        instance = mock.return_value
        instance.get_response.return_value = mock_llm_response
        yield instance


@pytest.fixture
def content_generator(mocker, tmp_path):
    """Fixture that provides a ContentGenerator instance with mocked dependencies."""
    # Create a temporary directory for test output
    test_output_dir = tmp_path / "test_output"
    test_output_dir.mkdir()
    
    # Mock the DATA_DIR to use our test directory
    mocker.patch('story_generator.DATA_DIR', test_output_dir)
    
    # Create a mock for the LLM with a default response
    mock_llm = MagicMock()
    mock_llm.get_response.return_value = {
        "choices": [{
            "message": {
                "content": "This is a test story.",
                "role": "assistant"
            }
        }]
    }
    
    # Create a ContentGenerator instance with the mock LLM
    generator = ContentGenerator()
    generator.llm = mock_llm
    
    # Set a simple test prompt
    generator.story_prompt = """
    Learning Objective: {LEARNING_OBJECTIVE}
    Language: {TARGET_LANGUAGE}
    Level: {CEFR_LEVEL}
    Length: {STORY_LENGTH} words
    Previous Story: {PREVIOUS_STORY}
    """.strip()
    
    # Add the test output directory to the generator for test access
    generator.test_output_dir = test_output_dir
    
    # Create the output directory if it doesn't exist
    output_dir = test_output_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Add output_dir as an attribute for tests to use
    generator.output_dir = output_dir
    
    yield generator
    
    # Cleanup - no need to do anything special as pytest handles it
