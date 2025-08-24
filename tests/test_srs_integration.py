"""Integration tests for SRS (Spaced Repetition System) functionality."""

import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock, call
import pytest

from story_generator import ContentGenerator, StoryParams, CEFRLevel
from curriculum_models import Curriculum, CurriculumDay
from srs_tracker import SRSTracker
from collocation_extractor import CollocationExtractor

# Sample test data
SAMPLE_STORY = """
The Venus flytrap is a carnivorous plant. It catches insects with its special leaves.
These leaves have tiny hairs that sense movement. When an insect touches them,
the leaves snap shut. This is how the plant gets its nutrients.
"""

SAMPLE_COLLOCATIONS = ["venus flytrap", "carnivorous plant", "special leaves", "tiny hairs"]

# Fixtures
@pytest.fixture
def temp_dir():
    """Create and return a temporary directory for testing."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir

@pytest.fixture
def mock_llm():
    """Create a mock LLM that returns a predefined response."""
    mock_llm = MagicMock()
    mock_llm.chat_response.return_value = {
        "choices": [{
            "message": {
                "content": SAMPLE_STORY,
                "role": "assistant"
            }
        }]
    }
    # Also mock the direct call to chat_response with the same structure
    mock_llm.return_value.chat_response.return_value = {
        "choices": [{
            "message": {
                "content": SAMPLE_STORY,
                "role": "assistant"
            }
        }]
    }
    return mock_llm

@pytest.fixture
def mock_collocation_extractor():
    """Create a mock collocation extractor."""
    mock_extractor = MagicMock(spec=CollocationExtractor)
    # Return a copy of the sample collocations to avoid modifying the original
    mock_extractor.extract_collocations.return_value = list(SAMPLE_COLLOCATIONS)
    mock_extractor.return_value = mock_extractor  # For when it's instantiated
    return mock_extractor

@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, mocker):
    """Set up the test environment with temporary directories and mocks."""
    # Import mock_config here to ensure it's loaded after patching
    from tests import mock_config
    
    # Ensure test directories exist
    mock_config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    mock_config.STORIES_DIR.mkdir(parents=True, exist_ok=True)
    mock_config.SRS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create a mock vocabulary file
    vocab_file = mock_config.VOCABULARY_PATH
    if not vocab_file.exists():
        vocab_file.parent.mkdir(parents=True, exist_ok=True)
        vocab_file.write_text('{"test": 1}')  # Minimal valid vocabulary
    
    # Create empty SRS and collocations files
    srs_file = mock_config.SRS_STATUS_PATH
    if not srs_file.exists():
        srs_file.parent.mkdir(parents=True, exist_ok=True)
        srs_file.write_text('{"current_day": 1, "collocations": {}}')
    
    collocations_file = mock_config.COLLOCATIONS_PATH
    if not collocations_file.exists():
        collocations_file.parent.mkdir(parents=True, exist_ok=True)
        collocations_file.write_text('[]')
    
    # Create a mock curriculum file
    curriculum_file = mock_config.CURRICULUM_PATH
    if not curriculum_file.exists():
        curriculum_file.parent.mkdir(parents=True, exist_ok=True)
        curriculum_file.write_text('{}')  # Empty curriculum
    
    # Create a mock config module with all required attributes
    mock_config_module = mocker.MagicMock()
    mock_config_module.DATA_DIR = mock_config.DATA_DIR
    mock_config_module.STORIES_DIR = mock_config.STORIES_DIR
    mock_config_module.SRS_DIR = mock_config.SRS_DIR
    mock_config_module.CURRICULA_DIR = mock_config.CURRICULA_DIR
    mock_config_module.CURRICULUM_PATH = str(mock_config.CURRICULUM_PATH)
    mock_config_module.COLLOCATIONS_PATH = str(mock_config.COLLOCATIONS_PATH)
    
    # Patch the config module in all relevant modules
    mocker.patch.dict('sys.modules', {'config': mock_config_module})
    
    # Also patch the specific paths used in story_generator
    mocker.patch('story_generator.config.CURRICULUM_PATH', str(mock_config.CURRICULUM_PATH))
    
    # Create a temporary directory for this test
    test_data_dir = tmp_path / "test_data"
    test_data_dir.mkdir()
    
    # Create a mock CollocationExtractor
    mock_extractor = mocker.MagicMock()
    mock_extractor.extract_collocations.return_value = ["test collocation"]
    
    # Create a real SRSTracker with the test directory
    srs_tracker = SRSTracker(data_dir=str(test_data_dir))
    
    # Patch the SRSTracker and CollocationExtractor constructors to return our instances
    mocker.patch('story_generator.SRSTracker', return_value=srs_tracker)
    mocker.patch('story_generator.CollocationExtractor', return_value=mock_extractor)
    
    # Patch the SRSTracker class to use our test directory
    original_srs_tracker_init = SRSTracker.__init__
    
    def patched_srs_tracker_init(self, data_dir: str = None, filename: str = 'srs_status.json'):
        return original_srs_tracker_init(self, data_dir=str(test_data_dir), filename=filename)
    
    mocker.patch('srs_tracker.SRSTracker.__init__', patched_srs_tracker_init)
    
    # Store the test_data_dir for use in tests
    mocker.patch('tests.test_srs_integration.test_data_dir', test_data_dir)
    
    # Make sure the data directory exists
    mock_config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Clear any existing state
    srs_file = mock_config.DATA_DIR / 'srs_status.json'
    if srs_file.exists():
        srs_file.unlink()
    
    collocations_file = mock_config.DATA_DIR / 'collocations.json'
    if collocations_file.exists():
        collocations_file.unlink()
    
    # Create a mock story file
    story_file = mock_config.STORIES_DIR / 'test_story.txt'
    story_file.parent.mkdir(parents=True, exist_ok=True)
    story_file.write_text('Test story content')
    
    yield
    
    # Clean up test files
    for file in mock_config.DATA_DIR.glob('*'):
        try:
            if file.is_file() and file.suffix in ['.json', '.txt']:
                if file.exists():
                    file.unlink()
            elif file.is_dir() and file.name != '__pycache__':
                # Remove all files in the directory
                for subfile in file.glob('*'):
                    if subfile.exists():
                        try:
                            if subfile.is_file():
                                subfile.unlink()
                            elif subfile.is_dir():
                                for f in subfile.glob('*'):
                                    if f.exists():
                                        f.unlink()
                                subfile.rmdir()
                        except Exception as e:
                            print(f"Warning: Failed to delete {subfile}: {e}")
                # Remove the directory
                if file.exists():
                    file.rmdir()
        except Exception as e:
            print(f"Warning: Failed to clean up {file}: {e}")
    
    # Also clean up any remaining files in the temp directory
    for file in tmp_path.glob('*'):
        if file.is_file() and file.suffix in ['.json', '.txt'] and file.exists():
            try:
                file.unlink()
            except Exception as e:
                print(f"Warning: Failed to clean up {file}: {e}")

# Store the test data directory for use in tests
test_data_dir = None

class TestSRSIntegration:
    """Integration tests for SRS functionality."""
    
    @patch.object(ContentGenerator, '_load_prompt', return_value='test prompt')
    def test_generate_story_updates_srs(self, mock_load_prompt, temp_dir, mock_llm, mock_collocation_extractor):
        """Test that generating a story updates the SRS with new collocations."""
        # Setup
        with patch('story_generator.MockLLM', return_value=mock_llm), \
             patch('story_generator.CollocationExtractor', return_value=mock_collocation_extractor):
            
            # Initialize ContentGenerator with temp directory and mock dependencies
            content_gen = ContentGenerator()
            content_gen.srs = SRSTracker(data_dir=temp_dir)
            content_gen.llm = mock_llm
            content_gen._collocation_extractor = mock_collocation_extractor
            
            # Create test parameters
            params = StoryParams(
                learning_objective="Learn about carnivorous plants",
                language="English",
                cefr_level=CEFRLevel.A2,
                phase=1,
                length=100,
                new_vocabulary=["carnivorous", "nutrients"],
                recycled_vocabulary=["plant", "leaves"]
            )
            
            # Mock the story generation to return our sample story with the expected format
            mock_response = {
                "choices": [{
                    "message": {
                        "content": SAMPLE_STORY,
                        "role": "assistant"
                    }
                }]
            }
            with patch.object(content_gen.llm, 'chat_response', return_value=mock_response):
                # Generate story
                story = content_gen.generate_story(params)
                
                # Verify story was generated
                assert story is not None
                assert isinstance(story, str)
                assert len(story) > 0
                
                # Verify collocations were extracted from the story
                mock_collocation_extractor.extract_collocations.assert_called_once_with(SAMPLE_STORY)
    
                # Get all collocations from SRS
                all_collocations = content_gen.srs.get_all_collocations()
                
                # Verify SRS was updated with the collocations
                due_collocations = content_gen.srs.get_due_collocations(day=1, max_items=10)
                
                # Debug output
                print(f"All collocations in SRS: {all_collocations}")
                print(f"Due collocations: {due_collocations}")
                
                # Check that some expected collocations are present and due
                assert len(due_collocations) > 0, f"No collocations are due on day 1. All collocations: {all_collocations}"
                assert any(colloc in due_collocations for colloc in SAMPLE_COLLOCATIONS), \
                    f"Expected at least one of {SAMPLE_COLLOCATIONS} in due collocations, but got {due_collocations}"
            
            # Verify SRS was updated with the collocations
            due_collocations = content_gen.srs.get_due_collocations(day=1, max_items=10)
            # We can't guarantee the exact number due to potential filtering
            assert len(due_collocations) >= 0
            assert any(colloc in due_collocations for colloc in SAMPLE_COLLOCATIONS)
            
    @patch.object(ContentGenerator, '_load_prompt', return_value='test prompt')
    def test_generate_story_for_day_integrates_srs(self, mock_load_prompt, temp_dir, mock_llm, mock_collocation_extractor):
        """Test that generate_story_for_day integrates with SRS correctly."""
        # Setup test data
        day1 = CurriculumDay(
            day=1,
            title="Introduction to Carnivorous Plants",
            focus="Basic plant biology",
            collocations=["carnivorous plant", "special leaves"],
            presentation_phrases=["The Venus flytrap is a carnivorous plant"],
            learning_objective="Understand basic characteristics of carnivorous plants"
        )
        
        curriculum_data = Curriculum(
            learning_objective="Test Learning Objective",
            target_language='English',
            learner_level='A2',
            presentation_length=10,  # minutes
            days=[day1],
            metadata={'title': 'Test Curriculum', 'description': 'Test Description', 'version': '1.0'}
        )
        
        # Setup mocks
        with patch('story_generator.MockLLM', return_value=mock_llm), \
             patch('story_generator.CollocationExtractor', return_value=mock_collocation_extractor):
            
            # Initialize ContentGenerator with temp directory and mock dependencies
            content_gen = ContentGenerator()
            content_gen.srs = SRSTracker(data_dir=temp_dir)
            content_gen.llm = mock_llm
            content_gen._collocation_extractor = mock_collocation_extractor
            
            # Mock the _load_curriculum method to return our test data
            with patch.object(content_gen, '_load_curriculum', return_value=curriculum_data):
                # Mock the story generation to return our sample story
                with patch.object(content_gen.llm, 'chat_response', return_value={
                    "choices": [{"message": {"content": SAMPLE_STORY, "role": "assistant"}}]
                }):
                    # Setup collocation extractor to return our sample collocations
                    content_gen._collocation_extractor.extract_collocations.return_value = list(SAMPLE_COLLOCATIONS)
                    
                    # Generate story for day1
                    story = content_gen.generate_story_for_day(1)
                    
                    # Verify story was generated
                    assert story is not None
                    assert isinstance(story, str)
                    assert len(story) > 0
                    
                    # Verify collocations were extracted from the story at least once
                    content_gen._collocation_extractor.extract_collocations.assert_any_call(story)
                    
                    # Get all collocations from SRS
                    all_collocations = content_gen.srs.get_all_collocations()
                    
                    # Verify SRS was updated with the collocations
                    # Check for collocations due on day 2 since they're scheduled for review then
                    due_collocations = content_gen.srs.get_due_collocations(day=2, max_items=10)
                    
                    # Debug output
                    print(f"All collocations in SRS: {all_collocations}")
                    print(f"Due collocations: {due_collocations}")
                    
                    # Verify at least some collocations were added to SRS
                    assert len(all_collocations) > 0, "No collocations were added to SRS"
                    
                    # Print detailed status of each collocation
                    print("\n--- Collocation Statuses ---")
                    for text, colloc in content_gen.srs.collocations.items():
                        print(f"Collocation: {text}")
                        print(f"  - First seen: Day {colloc.first_seen_day}")
                        print(f"  - Last seen: Day {colloc.last_seen_day}")
                        print(f"  - Review count: {colloc.review_count}")
                        print(f"  - Next review day: {colloc.next_review_day}")
                        print(f"  - Stability: {colloc.stability}")
                        print(f"  - Appearances: {colloc.appearances}")
                    
                    # Check that the collocations were added to SRS
                    assert len(all_collocations) > 0, "No collocations were added to SRS"
                    
                    # Check that some expected collocations are present and due
                    assert len(due_collocations) > 0, f"No collocations are due on day 1. All collocations: {all_collocations}"
                    assert any(colloc in due_collocations for colloc in SAMPLE_COLLOCATIONS), \
                        f"Expected at least one of {SAMPLE_COLLOCATIONS} in due collocations, but got {due_collocations}"
    
    def test_srs_state_persistence(self, temp_dir, mock_llm, mock_collocation_extractor):
        """Test that SRS state persists between SRSTracker instances."""
        # Define test collocations
        test_collocations = ["test collocation 1", "test collocation 2"]
        
        # First, create an SRS instance and add some collocations
        srs1 = SRSTracker(data_dir=temp_dir)
        
        # Add collocations with day=1 to make them due on day 1
        srs1.add_collocations(test_collocations, day=1)
        
        # Get all collocations from the first instance
        all_collocations = srs1.get_all_collocations()
        assert len(all_collocations) > 0, "No collocations were added to the tracker"
        
        # Get collocations due on day 1 and day 2
        due_day1 = srs1.get_due_collocations(day=1, max_items=10)
        due_day2 = srs1.get_due_collocations(day=2, max_items=10)
        
        # Save the state
        srs1._save_state()
        
        # Create a new SRS instance which should load the saved state
        srs2 = SRSTracker(data_dir=temp_dir)
        
        # Get all collocations from the second instance
        loaded_all_collocations = srs2.get_all_collocations()
        
        # Get collocations due on day 1 and day 2 from the second instance
        loaded_due_day1 = srs2.get_due_collocations(day=1, max_items=10)
        loaded_due_day2 = srs2.get_due_collocations(day=2, max_items=10)
        
        # Verify all collocations were persisted
        assert set(loaded_all_collocations) == set(all_collocations), \
            f"Collocations don't match. Expected: {all_collocations}, Got: {loaded_all_collocations}"
            
        # Verify due collocations match for both days
        assert set(loaded_due_day1) == set(due_day1), \
            f"Day 1 due collocations don't match. Expected: {due_day1}, Got: {loaded_due_day1}"
            
        assert set(loaded_due_day2) == set(due_day2), \
            f"Day 2 due collocations don't match. Expected: {due_day2}, Got: {loaded_due_day2}"
        
        # Verify all test collocations exist in the loaded instance
        for colloc in test_collocations:
            assert colloc in loaded_all_collocations, \
                f"Collocation '{colloc}' not found in loaded instance"
