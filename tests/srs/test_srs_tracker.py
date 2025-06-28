"""Unit tests for srs_tracker.py"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from srs_tracker import SRSTracker, CollocationStatus

# Test data
SAMPLE_COLLOCATIONS = ["special plants", "heavy rain", "strong coffee"]

# Fixtures
@pytest.fixture
def tracker(tmp_path):
    """Fixture providing an SRSTracker with a temporary data directory."""
    return SRSTracker(data_dir=str(tmp_path), filename='test_srs.json')
class TestCollocationStatus:
    """Tests for CollocationStatus class."""
    
    def test_to_dict(self):
        """Test conversion of CollocationStatus to dictionary."""
        colloc = CollocationStatus(
            text="test phrase",
            first_seen_day=1,
            last_seen_day=1,
            appearances=[1],
            review_count=1,
            next_review_day=2,
            stability=1.0
        )
        expected = {
            'text': 'test phrase',
            'first_seen_day': 1,
            'last_seen_day': 1,
            'appearances': [1],
            'review_count': 1,
            'next_review_day': 2,
            'stability': 1.0
        }
        assert colloc.to_dict() == expected

    def test_from_dict(self):
        """Test creation of CollocationStatus from dictionary."""
        data = {
            'text': 'test phrase',
            'first_seen_day': 1,
            'last_seen_day': 1,
            'appearances': [1],
            'review_count': 1,
            'next_review_day': 2,
            'stability': 1.0
        }
        colloc = CollocationStatus.from_dict(data)
        assert colloc.text == 'test phrase'
        assert colloc.first_seen_day == 1
        assert colloc.next_review_day == 2


class TestSRSTracker:
    """Tests for SRSTracker class."""
    
    def test_initialization_new_file(self, tmp_path):
        """Test initializing with a new file."""
        test_file = tmp_path / 'test_srs.json'
        tracker = SRSTracker(data_dir=str(tmp_path), filename='test_srs.json')
        assert tracker.current_day == 1
        assert len(tracker.collocations) == 0
        assert test_file.exists()

    def test_add_collocations_new(self, tracker):
        """Test adding new collocations."""
        tracker.add_collocations(["test phrase"], day=1)
        
        assert len(tracker.collocations) == 1
        assert "test phrase" in tracker.collocations
        colloc = tracker.collocations["test phrase"]
        assert colloc.first_seen_day == 1
        assert colloc.last_seen_day == 1
        assert colloc.review_count == 0  # New collocations start with 0 reviews
        assert colloc.next_review_day == 1  # Due immediately on the current day

    def test_add_collocations_existing(self, tracker):
        """Test updating existing collocations."""
        # First add - should be due on day 1
        tracker.add_collocations(["test phrase"], day=1)
        
        # Second add on day 3 - should update review count and next review day
        tracker.add_collocations(["test phrase"], day=3)  # Reviewing
        
        colloc = tracker.collocations["test phrase"]
        assert colloc.review_count == 1  # One review (the second add)
        assert colloc.last_seen_day == 3
        assert colloc.next_review_day == 4  # Next review in 1 day (on day 4)
        assert abs(colloc.stability - 1.2) < 0.001  # Stability increased

    def test_get_due_collocations(self, tracker):
        """Test retrieving due collocations."""
        # Add a collocation - should be due immediately on day 1
        tracker.add_collocations(["test phrase"], day=1)
        
        # Should be due on day 1 (immediately)
        due = tracker.get_due_collocations(day=1)
        assert len(due) == 1
        assert due[0] == "test phrase"
        
        # Mark as reviewed on day 1 - next review on day 2
        tracker.add_collocations(["test phrase"], day=1)
        due = tracker.get_due_collocations(day=1)
        assert len(due) == 0  # Not due again on day 1 after review
        
        # Due on day 2
        due = tracker.get_due_collocations(day=2)
        assert len(due) == 1
        assert due[0] == "test phrase"

    def test_save_and_load_state(self, tmp_path):
        """Test that state is properly saved and loaded."""
        # Create and save state
        test_file = tmp_path / 'test_srs.json'
        tracker1 = SRSTracker(data_dir=str(tmp_path), filename='test_srs.json')
        tracker1.add_collocations(["test phrase"], day=1)
        tracker1.current_day = 5
        tracker1._save_state()
        
        # Verify file was created
        assert test_file.exists()
        
        # Load in a new tracker
        tracker2 = SRSTracker(data_dir=str(tmp_path), filename='test_srs.json')
        
        assert tracker2.current_day == 5
        assert "test phrase" in tracker2.collocations
        assert tracker2.collocations["test phrase"].first_seen_day == 1

    def test_corrupted_file_handling(self, tmp_path):
        """Test handling of corrupted JSON file."""
        test_file = tmp_path / 'test_srs.json'
        # Create a corrupted JSON file
        test_file.write_text('{invalid json')
        
        # Should not raise exception
        tracker = SRSTracker(data_dir=str(tmp_path), filename='test_srs.json')
        assert len(tracker.collocations) == 0
        assert tracker.current_day == 1

    def test_context_manager(self, tmp_path):
        """Test that context manager properly saves on exit."""
        test_file = tmp_path / 'test_srs.json'
        with SRSTracker(data_dir=str(tmp_path), filename='test_srs.json') as tracker:
            tracker.add_collocations(["test phrase"], day=1)
        
        # Check that file was saved
        assert test_file.exists()
        data = json.loads(test_file.read_text())
        assert 'test phrase' in data['collocations']
