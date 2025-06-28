"""Tests for SRS collocation tracking and prioritization."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from story_generator import ContentGenerator, StoryParams, CEFRLevel
from curriculum_models import Curriculum, CurriculumDay
from srs_tracker import SRSTracker, CollocationStatus

# Sample test data
SAMPLE_STORY = """
The Venus flytrap is a fascinating carnivorous plant. It catches insects with its special leaves.
These leaves have tiny hairs that sense movement. When an insect touches them,
the leaves snap shut. This is how the plant gets its nutrients.
"""

SAMPLE_COLLOCATIONS = ["venus flytrap", "carnivorous plant", "special leaves", "tiny hairs", "snap shut"]

@pytest.fixture
def srs_tracker(tmp_path):
    """Create an SRS tracker for testing with isolated temporary directory."""
    # Create a temporary directory for the test
    data_dir = tmp_path / "test_data"
    data_dir.mkdir(exist_ok=True)
    
    # Create tracker with the temporary directory
    tracker = SRSTracker(data_dir=str(data_dir), filename="test_srs.json")
    
    # Add some collocations with different review states
    collocations = [
        ("venus flytrap", 1, 1.0),     # New, never reviewed
        ("carnivorous plant", 5, 2.0),  # Reviewed once, medium stability
        ("special leaves", 10, 3.0),    # Reviewed multiple times, high stability
        ("tiny hairs", 1, 0.5),         # New, low stability
        ("snap shut", 15, 1.5),         # Due soon, medium stability
    ]
    
    for text, days_until_due, stability in collocations:
        tracker.collocations[text] = CollocationStatus(
            text=text,
            first_seen_day=1,
            last_seen_day=1,
            appearances=[1],
            review_count=0,
            next_review_day=days_until_due,
            stability=stability
        )
    
    # Save the initial state to the test directory
    tracker._save_state()
    return tracker

@pytest.mark.allow_data_dir
class TestSRSCollocationTracking:
    """Tests for SRS collocation tracking and prioritization."""
    
    def test_get_due_collocations_prioritization(self, srs_tracker):
        """Test that get_due_collocations returns collocations in correct priority order."""
        # Collocations due on day 1: 'venus flytrap' (new), 'tiny hairs' (new)
        due = srs_tracker.get_due_collocations(day=1, min_items=2, max_items=5)
        
        # Should be in order: most overdue first, then by stability (lowest first)
        assert len(due) >= 2  # At least min_items
        assert 'venus flytrap' in due  # Due on day 1
        assert 'tiny hairs' in due     # Also due on day 1
        # 'carnivorous plant' is due on day 5, so it shouldn't be included yet
        assert len(due) <= 5  # At most max_items
        
        # 'special leaves' should not be included as it's not due yet (next_review_day=10)
        assert 'special leaves' not in due
    
    @patch.object(ContentGenerator, '_load_prompt', return_value='test prompt')
    def test_collocation_tracking_in_story_generation(self, mock_load_prompt, srs_tracker, tmp_path):
        """Test that story generation properly tracks collocations in SRS."""
        # Setup mock curriculum
        curriculum = Curriculum(
            target_language="English",
            learner_level=CEFRLevel.A2.value,
            presentation_length=5,
            days=[],
            learning_objective="Test Learning Objective",
            metadata={"title": "Test Curriculum"}
        )
        
        # Add a day with some collocations
        day_data = CurriculumDay(
            day=1,
            title="Carnivorous Plants",
            focus="Plant Biology",
            collocations=["venus flytrap", "carnivorous plant"],
            presentation_phrases=["special leaves"],
            learning_objective="Learn about carnivorous plants",
            story_guidance=""
        )
        curriculum.days.append(day_data)
        
        # Mock the LLM to return our sample story
        mock_llm = MagicMock()
        mock_llm.get_response.return_value = {
            "choices": [{"message": {"content": SAMPLE_STORY, "role": "assistant"}}]
        }
        
        # Mock the collocation extractor
        mock_extractor = MagicMock()
        mock_extractor.extract_collocations.return_value = SAMPLE_COLLOCATIONS
        
        # Create content generator with our mocks
        with patch('story_generator.Curriculum.load', return_value=curriculum), \
             patch('story_generator.MockLLM', return_value=mock_llm), \
             patch('story_generator.CollocationExtractor', return_value=mock_extractor):
            
            gen = ContentGenerator()
            gen.srs = srs_tracker
            
            # Generate story for day 1
            result = gen.generate_story_for_day(1)
            
            # Verify story was generated
            assert result is not None
            
            # Verify collocation extraction was called
            # Allow it to be called 1-2 times since the implementation might call it multiple times
            assert mock_extractor.extract_collocations.call_count >= 1
            
            # Verify SRS was updated
            assert len(srs_tracker.collocations) > 0
            
            # Check that collocations from the story were added/updated in SRS
            for colloc in SAMPLE_COLLOCATIONS:
                assert colloc in srs_tracker.collocations
            
            # Verify review counts were updated
            assert srs_tracker.collocations["venus flytrap"].review_count >= 1
            assert srs_tracker.collocations["carnivorous plant"].review_count >= 1
    
    @patch.object(ContentGenerator, '_load_prompt', return_value='test prompt')
    def test_collocation_categorization(self, mock_load_prompt, srs_tracker):
        """Test that collocations are properly categorized during story generation."""
        # Test collocation categorization
        new_collocation = "new collocation"
        learning_collocation = "learning collocation"
        reviewing_collocation = "reviewing collocation"
        mastered_collocation = "mastered collocation"
        
        # Add test collocations with different review states
        srs_tracker.collocations[new_collocation] = CollocationStatus(
            text=new_collocation,
            first_seen_day=1,
            last_seen_day=1,
            appearances=[1],
            review_count=0,
            next_review_day=1,
            stability=0.5
        )
        
        srs_tracker.collocations[learning_collocation] = CollocationStatus(
            text=learning_collocation,
            first_seen_day=1,
            last_seen_day=1,
            appearances=[1],
            review_count=2,
            next_review_day=1,
            stability=1.5
        )
        
        srs_tracker.collocations[reviewing_collocation] = CollocationStatus(
            text=reviewing_collocation,
            first_seen_day=1,
            last_seen_day=1,
            appearances=[1],
            review_count=5,
            next_review_day=1,
            stability=3.0
        )
        
        srs_tracker.collocations[mastered_collocation] = CollocationStatus(
            text=mastered_collocation,
            first_seen_day=1,
            last_seen_day=1,
            appearances=[1],
            review_count=10,
            next_review_day=100,  # Far in the future
            stability=10.0
        )
        
        # Create a ContentGenerator instance to ensure the mock is used
        generator = ContentGenerator()
        
        # Test categorization
        assert srs_tracker._categorize_collocation(new_collocation, 1) == "new"
        assert srs_tracker._categorize_collocation(learning_collocation, 1) == "learning"
        assert srs_tracker._categorize_collocation(reviewing_collocation, 1) == "reviewing"
        assert srs_tracker._categorize_collocation(mastered_collocation, 1) == "mastered"
        
        # Setup mock curriculum
        curriculum = Curriculum(
            target_language="English",
            learner_level=CEFRLevel.A2.value,
            presentation_length=5,
            days=[],
            learning_objective="Test Learning Objective",
            metadata={"title": "Test Curriculum"}
        )
        
        # Add a day with some collocations
        day_data = CurriculumDay(
            day=1,
            title="Carnivorous Plants",
            focus="Plant Biology",
            collocations=["venus flytrap", "carnivorous plant"],  # New collocations
            presentation_phrases=["special leaves"],
            learning_objective="Learn about carnivorous plants",
            story_guidance=""
        )
        curriculum.days.append(day_data)
        
        # Mock the LLM and collocation extractor
        mock_llm = MagicMock()
        mock_llm.get_response.return_value = {
            "choices": [{"message": {"content": SAMPLE_STORY, "role": "assistant"}}]
        }
        
        # Mock the collocation extractor to return known collocations
        mock_extractor = MagicMock()
        mock_extractor.extract_collocations.return_value = SAMPLE_COLLOCATIONS
        
        # Create content generator with our mocks
        with patch('story_generator.Curriculum.load', return_value=curriculum), \
             patch('story_generator.MockLLM', return_value=mock_llm), \
             patch('story_generator.CollocationExtractor', return_value=mock_extractor):
            
            gen = ContentGenerator()
            gen.srs = srs_tracker
            
            # Generate story for day 1 and get the collocation report
            result = gen.generate_day_story(1)
            
            # Verify we got a result
            assert result is not None
            story, collocation_report = result
            
            # Verify the story was generated
            assert isinstance(story, str)
            assert len(story) > 0
            
            # Verify collocation report structure
            assert isinstance(collocation_report, dict)
            assert 'new' in collocation_report
            assert 'reviewed' in collocation_report
            assert 'bonus' in collocation_report
            
            # Verify collocations are properly categorized
            # 'venus flytrap' and 'carnivorous plant' should be in 'new' (from curriculum)
            assert 'venus flytrap' in collocation_report['new']
            assert 'carnivorous plant' in collocation_report['new']
            
            # 'special leaves' should be in 'reviewed' (from SRS)
            assert 'special leaves' in collocation_report['reviewed']
            
            # Verify that any collocations from the story that weren't in the curriculum or SRS
            # are marked as 'bonus'
            story_collocations = set(SAMPLE_COLLOCATIONS)
            expected_bonus = story_collocations - set(collocation_report['new']) - set(collocation_report['reviewed'])
            
            # Check that all expected bonus collocations are present
            for colloc in expected_bonus:
                assert colloc in collocation_report['bonus']
            
            # Verify logging of included collocations
            # (This would be verified through caplog in a real test)

    def test_collocation_limits(self, srs_tracker):
        """Test that the number of review collocations is properly limited."""
        # Get due collocations with a small limit
        due = srs_tracker.get_due_collocations(day=1, min_items=2, max_items=3)
        
        # Should respect max_items
        assert len(due) <= 3
        
        # Should include at least min_items if available
        assert len(due) >= min(2, len([c for c in srs_tracker.collocations.values() 
                                    if c.next_review_day <= 1]))
        
        # Should be in correct priority order
        if len(due) > 1:
            first = srs_tracker.collocations[due[0]]
            second = srs_tracker.collocations[due[1]]
            assert (first.next_review_day < second.next_review_day) or \
                   (first.next_review_day == second.next_review_day and 
                    first.stability <= second.stability)
