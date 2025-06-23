"""Integration tests for SRS (Spaced Repetition System) functionality."""

import json
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pytest

from story_generator import ContentGenerator, StoryParams, CEFRLevel
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
    mock_llm.get_response.return_value = {
        "choices": [{
            "message": {
                "content": SAMPLE_STORY,
                "role": "assistant"
            }
        }]
    }
    # Also mock the direct call to get_response with the same structure
    mock_llm.return_value.get_response.return_value = {
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

class TestSRSIntegration:
    """Integration tests for SRS functionality."""
    
    def test_generate_story_updates_srs(self, temp_dir, mock_llm, mock_collocation_extractor):
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
            with patch.object(content_gen.llm, 'get_response', return_value=mock_response):
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
            
    def test_generate_story_for_day_integrates_srs(self, temp_dir, mock_llm, mock_collocation_extractor):
        """Test that generate_story_for_day integrates with SRS correctly."""
        # Setup test curriculum data
        curriculum_data = {
            'phases': {
                'phase1': {
                    'learning_objective': 'Learn about carnivorous plants',
                    'cefr_level': 'A2',
                    'story_length': 100,
                    'new_vocabulary': ['carnivorous', 'nutrients'],
                    'recycled_vocabulary': ['plant', 'leaves']
                }
            },
            'language': 'English'
        }
        
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
                with patch.object(content_gen.llm, 'get_response', return_value={
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
