"""Tests for curriculum_models.py"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

# Add the parent directory to the path so we can import the module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from curriculum_models import Curriculum, CurriculumDay


class TestCurriculumDay:
    """Test the CurriculumDay class."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test data."""
        self.sample_day = CurriculumDay(
            day=1,
            title="Introduction to Greetings",
            focus="Basic Greetings",
            collocations=["good morning", "good afternoon", "good evening"],
            presentation_phrases=["Hello!", "How are you?", "Goodbye!"],
            learning_objective="Learn basic greetings in the target language",
            story_guidance="Include characters meeting for the first time"
        )
    
    def test_creation(self):
        """Test that a CurriculumDay is created with the correct attributes."""
        assert self.sample_day.day == 1
        assert self.sample_day.title == "Introduction to Greetings"
        assert self.sample_day.focus == "Basic Greetings"
        assert len(self.sample_day.collocations) == 3
        assert len(self.sample_day.presentation_phrases) == 3
        assert "Hello!" in self.sample_day.presentation_phrases
        assert self.sample_day.learning_objective == "Learn basic greetings in the target language"
        assert self.sample_day.story_guidance == "Include characters meeting for the first time"
    
    def test_invalid_day_number(self):
        """Test that day number must be positive."""
        with pytest.raises(ValueError):
            CurriculumDay(
                day=0,
                title="Invalid Day",
                focus="Test",
                collocations=[],
                presentation_phrases=[],
                learning_objective="Test"
            )


class TestCurriculum:
    """Test the Curriculum class."""
    
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test data."""
        # Create sample days
        self.day1 = CurriculumDay(
            day=1,
            title="Day 1",
            focus="Greetings",
            collocations=["good morning", "good afternoon"],
            presentation_phrases=["Hello!", "How are you?"],
            learning_objective="Learn basic greetings",
            story_guidance="Include a greeting between two people"
        )
        
        self.day2 = CurriculumDay(
            day=2,
            title="Day 2",
            focus="Introductions",
            collocations=["my name is", "nice to meet you"],
            presentation_phrases=["What's your name?", "Nice to meet you!"],
            learning_objective="Learn to introduce yourself",
            story_guidance="Include characters introducing themselves"
        )
        
        # Create a sample curriculum
        self.sample_curriculum = Curriculum(
            learning_objective="Learn basic conversation skills",
            target_language="Spanish",
            learner_level="Beginner",
            presentation_length=30,
            days=[self.day1, self.day2],
            metadata={"version": "1.0", "author": "Test"}
        )
        self.temp_file = tmp_path / "test_curriculum.json"
    
    def test_creation(self):
        """Test that a Curriculum is created with the correct attributes."""
        assert self.sample_curriculum.learning_objective == "Learn basic conversation skills"
        assert self.sample_curriculum.target_language == "Spanish"
        assert self.sample_curriculum.learner_level == "Beginner"
        assert self.sample_curriculum.presentation_length == 30
        assert len(self.sample_curriculum.days) == 2
        assert self.sample_curriculum.metadata["version"] == "1.0"
    
    def test_get_day(self):
        """Test the get_day method."""
        # Test getting an existing day
        day = self.sample_curriculum.get_day(1)
        assert day is not None
        assert day.title == "Day 1"
        
        # Test getting a non-existent day
        day = self.sample_curriculum.get_day(99)
        assert day is None
    
    def test_to_dict(self):
        """Test the to_dict method."""
        data = self.sample_curriculum.to_dict()
        
        # Check top-level fields
        assert data["learning_objective"] == "Learn basic conversation skills"
        assert data["target_language"] == "Spanish"
        
        # Check days
        assert len(data["days"]) == 2
        assert data["days"][0]["day"] == 1
        assert data["days"][1]["day"] == 2
        
        # Check metadata
        assert data["metadata"]["version"] == "1.0"
    
    def test_from_dict(self):
        """Test the from_dict method."""
        # Create a dictionary representation
        data = self.sample_curriculum.to_dict()
        
        # Create a new curriculum from the dictionary
        new_curriculum = Curriculum.from_dict(data)
        
        # Verify the new curriculum matches the original
        assert new_curriculum.learning_objective == self.sample_curriculum.learning_objective
        assert len(new_curriculum.days) == 2
        assert new_curriculum.days[0].title == "Day 1"
        assert new_curriculum.days[1].title == "Day 2"
    
    def test_save_and_load(self, tmp_path):
        """Test saving to and loading from a file."""
        # Create a temporary file path
        temp_file = tmp_path / "test_curriculum.json"
        
        # Save the curriculum to the temporary file
        self.sample_curriculum.save(temp_file)
        
        # Verify the file was created
        assert temp_file.exists()
        
        # Load it back
        loaded = Curriculum.load(temp_file)
        
        # Verify the loaded curriculum matches the original
        assert loaded.learning_objective == self.sample_curriculum.learning_objective
        assert len(loaded.days) == 2
        assert loaded.days[0].title == "Day 1"
        assert loaded.days[1].title == "Day 2"
    
    def test_save_invalid_extension(self, tmp_path):
        """Test that saving with an invalid extension raises an error."""
        invalid_file = tmp_path / "invalid_extension.txt"
        with pytest.raises(ValueError):
            self.sample_curriculum.save(invalid_file)
    
    def test_load_nonexistent_file(self, tmp_path):
        """Test that loading a non-existent file raises an error."""
        non_existent_file = tmp_path / "nonexistent_file.json"
        with pytest.raises(FileNotFoundError):
            Curriculum.load(non_existent_file)
    
    def test_from_dict_invalid_data(self):
        """Test that from_dict raises an error with invalid data."""
        with pytest.raises(ValueError):
            Curriculum.from_dict("not a dictionary")


# Remove unittest.main() since we're using pytest
