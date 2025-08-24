"""Pytest configuration and fixtures for TunaTale tests."""
# Ensure we patch sys.modules before any other imports
import builtins
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import mock config first - this must happen before any other imports
from tests import mock_config

# Set up environment for testing
os.environ["TESTING"] = "1"
os.environ["PYTHONPATH"] = str(PROJECT_ROOT)

# Patch sys.modules to use our mock config before any other imports
import sys
sys.modules['config'] = mock_config

# Now import the rest of the testing dependencies
import json
import shutil
import pytest
from typing import Dict, Any
from pathlib import Path

# Import the config (which will be our mock)
import config

# Ensure test templates directory exists and contains required templates
def ensure_test_templates(tmp_path: Path) -> Path:
    """Ensure test templates directory exists with all required template files."""
    test_templates_dir = tmp_path / "templates"
    test_templates_dir.mkdir(exist_ok=True)
    
    # Copy templates from project templates directory
    project_templates = PROJECT_ROOT / "templates"
    if project_templates.exists():
        for template_file in project_templates.glob("*.html"):
            shutil.copy2(template_file, test_templates_dir / template_file.name)
    
    return test_templates_dir

# Verify the patch worked
assert config.DATA_DIR == mock_config.DATA_DIR, "Config patching failed!"

import warnings
import pytest
from unittest.mock import Mock, patch

# Suppress deprecation warnings from third-party libraries
warnings.filterwarnings(
    "ignore",
    message=r"Importing 'parser.split_arg_string' is deprecated",
    category=DeprecationWarning,
    module=r'(spacy\\.cli\\._util|weasel\\.util\\.config)'
)

from story_generator import ContentGenerator, StoryParams, CEFRLevel
from llm_mock import MockLLM


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch, request):
    """Set up a clean test environment with isolated file operations."""
    # Skip if test is marked to allow data dir access
    if 'allow_data_dir' in request.keywords:
        yield
        return
    
    # Create a temporary directory for test data
    test_data_dir = tmp_path / "test_data"
    test_data_dir.mkdir(exist_ok=True)
    
    # Set up required subdirectories
    (test_data_dir / 'stories').mkdir(exist_ok=True)
    (test_data_dir / 'mock_responses').mkdir(exist_ok=True)
    
    # Create minimal required files
    vocab_file = test_data_dir / 'a2_flat_vocabulary.json'
    if not vocab_file.exists():
        vocab_file.write_text('{"test": 1}')  # Minimal valid vocabulary
    
    # Create empty SRS and collocations files if they don't exist
    srs_file = test_data_dir / 'srs_status.json'
    if not srs_file.exists():
        srs_file.write_text('{"current_day": 1, "collocations": {}}')
    
    collocations_file = test_data_dir / 'collocations.json'
    if not collocations_file.exists():
        collocations_file.write_text('[]')
    
    # Store original config values
    original_data_dir = config.DATA_DIR
    
    # Update config to use test directories
    config.DATA_DIR = test_data_dir
    config.MOCK_RESPONSES_DIR = test_data_dir / "mock_responses"
    
    # Ensure the DATA_DIR is properly patched in all modules
    import sys
    import importlib
    
    # Patch the config module in sys.modules
    sys.modules['config'].DATA_DIR = test_data_dir
    
    # Reload modules that might have imported DATA_DIR
    for module_name in ['story_generator', 'collocation_extractor', 'srs_tracker']:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    
    # Track original files in the data directory
    original_files = set()
    if original_data_dir.exists():
        original_files = set(f for f in original_data_dir.glob('*') if f.is_file())
    
    yield
    
    # Restore original config values
    config.DATA_DIR = original_data_dir
    config.MOCK_RESPONSES_DIR = original_data_dir / "mock_responses"
    
    # Clean up any files created in the original data directory
    if original_data_dir.exists():
        new_files = set(f for f in original_data_dir.glob('*') if f.is_file()) - original_files
        if new_files:
            for f in new_files:
                try:
                    if f.exists():
                        f.unlink()
                except Exception as e:
                    print(f"Warning: Could not clean up {f}: {e}")
            
            if not hasattr(request.node, 'allow_data_dir'):
                pytest.fail(
                    f"Test created files in the main data directory: "
                    f"{', '.join(str(f) for f in new_files)}"
                )


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


@pytest.fixture(autouse=True)
def verify_no_files_in_data_dir(request, tmp_path):
    """Verify no files are created in the main data directory during tests."""
    from config import DATA_DIR
    
    # Skip this check for tests that are expected to use the main data directory
    if 'allow_data_dir' in request.keywords:
        yield
        return
        
    # Ensure DATA_DIR exists and is a directory
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get initial list of files in DATA_DIR
    initial_files = set(f for f in DATA_DIR.glob('*') if f.is_file())
    
    # Create a temporary directory for test output
    test_output_dir = tmp_path / "test_output"
    test_output_dir.mkdir()
    
    # Patch DATA_DIR in the existing config (preserve all other attributes)
    import sys
    from unittest.mock import patch
    
    # Save the original DATA_DIR before patching
    original_data_dir = DATA_DIR
    
    # Patch DATA_DIR in the config module to use our test directory
    with patch.object(sys.modules['config'], 'DATA_DIR', test_output_dir):
        yield
    
    # Verify no new files were created in the main DATA_DIR  
    final_files = set(f for f in original_data_dir.glob('*') if f.is_file())
    new_files = final_files - initial_files
    
    # Clean up any new files that were created
    for f in new_files:
        try:
            f.unlink()
        except Exception as e:
            print(f"Warning: Could not clean up {f}: {e}")
    
    if new_files:
        pytest.fail(f"Test created files in the main data directory: {', '.join(str(f) for f in new_files)}")


@pytest.fixture
def content_generator(mocker, tmp_path):
    """Fixture that provides a ContentGenerator instance with mocked dependencies."""
    # Create a temporary directory for test output
    test_output_dir = tmp_path / "test_output"
    (test_output_dir / 'stories').mkdir(exist_ok=True, parents=True)
    
    # Create necessary subdirectories
    (test_output_dir / 'generated_content').mkdir(exist_ok=True)
    
    # Create a mock vocabulary file
    vocab_file = test_output_dir / 'a2_flat_vocabulary.json'
    vocab_file.write_text('{"test": 1}')  # Minimal valid vocabulary
    
    # Create a temporary directory for SRSTracker
    srs_data_dir = tmp_path / 'srs_data'
    srs_data_dir.mkdir(exist_ok=True)
    
    # Create empty SRS and collocations files in the test directory
    srs_file = srs_data_dir / 'srs_status.json'
    srs_file.write_text('{"current_day": 1, "collocations": {}}')
    
    collocations_file = test_output_dir / 'collocations.json'
    collocations_file.write_text('[]')
    
    # Create a real SRSTracker with the test directory
    from srs_tracker import SRSTracker
    srs_tracker = SRSTracker(data_dir=str(srs_data_dir), filename='srs_status.json')
    
    # Patch the SRSTracker to use our test instance
    mocker.patch('story_generator.SRSTracker', return_value=srs_tracker)
    
    # Create a prompts directory and a test prompt file
    test_prompts_dir = test_output_dir / 'prompts'
    test_prompts_dir.mkdir(exist_ok=True)
    
    # Create test prompt files with the expected format
    # Main story prompt (balanced strategy)
    test_prompt_file = test_prompts_dir / 'story_prompt_balanced.txt'
    test_prompt_file.write_text("""
    VOCABULARY CONTEXT:
    - Focus on teaching: {NEW_VOCABULARY}
    - Naturally recycle: {RECYCLED_COLLOCATIONS}
    - Genre: {GENRE}
    
    Write a short, engaging story that teaches the new vocabulary
    while naturally incorporating the recycled collocations.
    The story should be appropriate for language learning.
    """)
    
    # Create system prompt for chat-based generation
    system_prompt_file = test_prompts_dir / 'system_prompt.txt'
    system_prompt_file.write_text("Test system prompt for story generation")
    
    # Create day prompt template for chat-based generation
    day_prompt_file = test_prompts_dir / 'day_prompt_template.txt'
    day_prompt_file.write_text("Test day prompt template")
    
    # Mock the DATA_DIR and PROMPTS_DIR to use our test directories
    mocker.patch('story_generator.config.DATA_DIR', test_output_dir)
    mocker.patch('story_generator.config.PROMPTS_DIR', test_prompts_dir)
    mocker.patch('collocation_extractor.config.DATA_DIR', test_output_dir)
    
    # Create a temporary directory for SRSTracker data if it doesn't exist
    srs_data_dir = tmp_path / 'srs_data'
    srs_data_dir.mkdir(exist_ok=True)
    
    # Create a real SRSTracker with the test directory
    from srs_tracker import SRSTracker
    srs_tracker = SRSTracker(data_dir=str(srs_data_dir), filename='test_srs.json')
    
    # Create a mock CollocationExtractor
    mock_extractor = mocker.MagicMock()
    mock_extractor.extract_collocations.return_value = ["test collocation"]
    
    # Patch the SRSTracker and CollocationExtractor to return our instances
    mocker.patch('story_generator.SRSTracker', return_value=srs_tracker)
    mocker.patch('story_generator.CollocationExtractor', return_value=mock_extractor)
    
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
    
    # Patch the _load_prompt method at the class level before instantiation
    mock_load_prompt = mocker.patch('story_generator.ContentGenerator._load_prompt', 
                                  return_value='test prompt')
    
    # Create a ContentGenerator instance with the mock LLM
    generator = ContentGenerator()
    generator.llm = mock_llm
    
    # Create a mock for the _save_story method
    mock_save_story = mocker.MagicMock()
    
    # Set up the mock to return a path when called
    def save_story_side_effect(story, phase, learning_objective):
        output_file = test_output_dir / 'stories' / f'test_story_{phase}.txt'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(story)
        return str(output_file)
    
    mock_save_story.side_effect = save_story_side_effect
    
    # Patch the _save_story method to use our mock
    generator._save_story = mock_save_story
    
    # Mock the _load_curriculum method to return a test curriculum
    generator._load_curriculum = mocker.MagicMock(return_value=None)
    
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
    output_dir = test_output_dir / "stories"
    output_dir.mkdir(exist_ok=True)
    
    # Add output_dir as an attribute for tests to use
    generator.output_dir = output_dir
    
    # Patch the SRS tracker to use our test directory
    generator.srs = MagicMock()
    generator.srs.get_due_collocations.return_value = []
    generator.srs.add_collocation = MagicMock()
    generator.srs.mark_reviewed = MagicMock()
    
    # Clear any existing SRS state
    if srs_file.exists():
        srs_file.unlink()
    if collocations_file.exists():
        collocations_file.unlink()
    
    yield generator
    
    # Clean up test files
    if srs_file.exists():
        srs_file.unlink()
    if collocations_file.exists():
        collocations_file.unlink()
    
    # Cleanup - no need to do anything special as pytest handles it
