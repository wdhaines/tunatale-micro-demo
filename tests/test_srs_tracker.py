"""Unit tests for the SRSTracker class."""
import json
from pathlib import Path
from typing import Dict, Any
import pytest

from srs_tracker import SRSTracker, CollocationStatus


def test_srs_tracker_init_creates_file(tmp_path: Path) -> None:
    """Test that SRSTracker creates a new file if it doesn't exist."""
    # Arrange
    data_file = tmp_path / "srs_status.json"
    
    # Act
    with SRSTracker(data_dir=str(tmp_path), filename="srs_status.json") as tracker:
        # Assert
        assert data_file.exists()
        assert tracker.current_day == 1
        assert not tracker.collocations
        
        # Verify the file has the correct structure
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data['current_day'] == 1
            assert data['collocations'] == {}


def test_add_new_collocation(tmp_path: Path) -> None:
    """Test adding new collocations to the tracker."""
    # Arrange
    collocations = ["heavy rain", "strong coffee"]
    
    # Act
    with SRSTracker(data_dir=str(tmp_path)) as tracker:
        tracker.add_collocations(collocations, day=1)
        
        # Assert
        assert len(tracker.collocations) == 2
        
        for text in collocations:
            assert text in tracker.collocations
            colloc = tracker.collocations[text]
            assert colloc.text == text
            assert colloc.first_seen_day == 1
            assert colloc.last_seen_day == 1
            assert colloc.appearances == [1]
            assert colloc.review_count == 1
            assert colloc.next_review_day == 2  # First review after 1 day
            assert colloc.stability == 1.0


def test_update_existing_collocation(tmp_path: Path) -> None:
    """Test updating existing collocations and verify SRS intervals."""
    # Arrange
    collocation = "heavy rain"
    
    # Act & Assert - First addition
    with SRSTracker(data_dir=str(tmp_path)) as tracker:
        tracker.add_collocations([collocation], day=1)
        
        # First review after 1 day
        colloc = tracker.collocations[collocation]
        assert colloc.review_count == 1
        assert colloc.next_review_day == 2
        
        # Review again on day 2 (should update interval)
        tracker.add_collocations([collocation], day=2)
        
        # Should have doubled the interval (1 * 2^1 = 2)
        assert colloc.review_count == 2
        assert colloc.next_review_day == 4  # 2 + (1 * 2^1) = 4
        assert colloc.stability > 1.0  # Stability should increase
        
        # Review again on day 4
        tracker.add_collocations([collocation], day=4)
        
        # Interval should double again (2 * 2^1 = 4)
        assert colloc.review_count == 3
        assert colloc.next_review_day == 8  # 4 + (2 * 2^1) = 8
        assert colloc.stability > 1.2  # Stability should increase further


def test_get_due_collocations(tmp_path: Path) -> None:
    """Test retrieving collocations that are due for review."""
    # Arrange
    collocations = ["heavy rain", "strong coffee", "fast car"]
    
    with SRSTracker(data_dir=str(tmp_path)) as tracker:
        # Add collocations on day 1
        tracker.add_collocations(collocations, day=1)
        
        # On day 1, nothing should be due yet
        assert not tracker.get_due_collocations(day=1)
        
        # On day 2, all collocations should be due
        due = tracker.get_due_collocations(day=2)
        assert len(due) == 3
        assert {c.text for c in due} == set(collocations)
        
        # Review two collocations on day 2
        tracker.add_collocations(["heavy rain", "strong coffee"], day=2)
        
        # On day 3, only "fast car" should be due
        due = tracker.get_due_collocations(day=3)
        assert len(due) == 1
        assert due[0].text == "fast car"
        
        # On day 4, the reviewed collocations should be due again, and "fast car" is still due
        due = tracker.get_due_collocations(day=4)
        assert len(due) == 3  # All three should be due
        assert {c.text for c in due} == {"heavy rain", "strong coffee", "fast car"}
        # "fast car" has review_count 1, others have 2
        assert sum(1 for c in due if c.review_count == 1) == 1
        assert sum(1 for c in due if c.review_count == 2) == 2


def test_save_and_load_state(tmp_path: Path) -> None:
    """Test that the tracker state is properly saved and loaded."""
    # Arrange
    collocations = ["heavy rain", "strong coffee"]
    
    # Create and populate a tracker
    with SRSTracker(data_dir=str(tmp_path)) as tracker:
        tracker.add_collocations(collocations, day=1)
        tracker.add_collocations(["heavy rain"], day=2)  # Update one collocation
    
    # Create a new tracker that should load the saved state
    with SRSTracker(data_dir=str(tmp_path)) as new_tracker:
        # Verify the state was loaded correctly
        assert len(new_tracker.collocations) == 2
        assert new_tracker.current_day == 2  # Should be the last day used
        
        # Verify the updated collocation
        heavy_rain = new_tracker.collocations["heavy rain"]
        assert heavy_rain.review_count == 2
        assert heavy_rain.next_review_day == 4  # 2 + (1 * 2^1) = 4
        
        # Verify the unchanged collocation
        coffee = new_tracker.collocations["strong coffee"]
        assert coffee.review_count == 1
        assert coffee.next_review_day == 2  # First review after 1 day


def test_handles_corrupted_file(tmp_path: Path) -> None:
    """Test that the tracker handles corrupted JSON files gracefully."""
    # Arrange - create a corrupted JSON file
    data_file = tmp_path / "srs_status.json"
    with open(data_file, 'w', encoding='utf-8') as f:
        f.write('{invalid json')
    
    # Act - should not raise an exception
    with SRSTracker(data_dir=str(tmp_path)) as tracker:
        # Assert - should start with empty state
        assert tracker.current_day == 1
        assert not tracker.collocations
        
        # Should be able to add collocations
        tracker.add_collocations(["test"], day=1)
        assert "test" in tracker.collocations
