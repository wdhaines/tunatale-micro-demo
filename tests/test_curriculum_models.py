"""Tests for curriculum_models.py"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

# Add the parent directory to the path so we can import the module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from curriculum_models import Curriculum, CurriculumDay


class TestCurriculumDay(unittest.TestCase):
    """Test the CurriculumDay class."""
    
    def setUp(self):
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
        self.assertEqual(self.sample_day.day, 1)
        self.assertEqual(self.sample_day.title, "Introduction to Greetings")
        self.assertEqual(self.sample_day.focus, "Basic Greetings")
        self.assertEqual(len(self.sample_day.collocations), 3)
        self.assertEqual(len(self.sample_day.presentation_phrases), 3)
        self.assertIn("Hello!", self.sample_day.presentation_phrases)
        self.assertEqual(
            self.sample_day.learning_objective,
            "Learn basic greetings in the target language"
        )
        self.assertEqual(
            self.sample_day.story_guidance,
            "Include characters meeting for the first time"
        )
    
    def test_invalid_day_number(self):
        """Test that day number must be positive."""
        with self.assertRaises(ValueError):
            CurriculumDay(
                day=0,
                title="Invalid Day",
                focus="Test",
                collocations=[],
                presentation_phrases=[],
                learning_objective="Test"
            )


class TestCurriculum(unittest.TestCase):
    """Test the Curriculum class."""
    
    def setUp(self):
        """Set up test data."""
        self.day1 = CurriculumDay(
            day=1,
            title="Day 1",
            focus="Greetings",
            collocations=["hello", "hi"],
            presentation_phrases=["Hello!", "Hi there!"],
            learning_objective="Learn basic greetings"
        )
        self.day2 = CurriculumDay(
            day=2,
            title="Day 2",
            focus="Introductions",
            collocations=["my name is", "nice to meet you"],
            presentation_phrases=["What's your name?", "Nice to meet you!"],
            learning_objective="Learn to introduce yourself"
        )
        
        self.sample_curriculum = Curriculum(
            learning_objective="Learn basic conversation skills",
            target_language="Spanish",
            learner_level="Beginner",
            presentation_length=30,
            days=[self.day1, self.day2],
            metadata={"version": "1.0", "author": "Test"}
        )
    
    def test_creation(self):
        """Test that a Curriculum is created with the correct attributes."""
        self.assertEqual(self.sample_curriculum.learning_objective, 
                        "Learn basic conversation skills")
        self.assertEqual(self.sample_curriculum.target_language, "Spanish")
        self.assertEqual(self.sample_curriculum.learner_level, "Beginner")
        self.assertEqual(self.sample_curriculum.presentation_length, 30)
        self.assertEqual(len(self.sample_curriculum.days), 2)
        self.assertEqual(self.sample_curriculum.metadata["version"], "1.0")
    
    def test_get_day(self):
        """Test the get_day method."""
        # Test getting an existing day
        day = self.sample_curriculum.get_day(1)
        self.assertIsNotNone(day)
        self.assertEqual(day.title, "Day 1")
        
        # Test getting a non-existent day
        day = self.sample_curriculum.get_day(99)
        self.assertIsNone(day)
    
    def test_to_dict(self):
        """Test the to_dict method."""
        data = self.sample_curriculum.to_dict()
        
        # Check top-level fields
        self.assertEqual(data["learning_objective"], 
                        "Learn basic conversation skills")
        self.assertEqual(data["target_language"], "Spanish")
        
        # Check days
        self.assertEqual(len(data["days"]), 2)
        self.assertEqual(data["days"][0]["day"], 1)
        self.assertEqual(data["days"][1]["day"], 2)
        
        # Check metadata
        self.assertEqual(data["metadata"]["version"], "1.0")
    
    def test_from_dict(self):
        """Test the from_dict method."""
        # Create a dictionary representation
        data = self.sample_curriculum.to_dict()
        
        # Create a new curriculum from the dictionary
        new_curriculum = Curriculum.from_dict(data)
        
        # Verify the new curriculum matches the original
        self.assertEqual(new_curriculum.learning_objective, 
                        self.sample_curriculum.learning_objective)
        self.assertEqual(len(new_curriculum.days), 2)
        self.assertEqual(new_curriculum.days[0].title, "Day 1")
        self.assertEqual(new_curriculum.days[1].title, "Day 2")
    
    def test_save_and_load(self):
        """Test saving to and loading from a file."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            try:
                # Save the curriculum to a temporary file
                self.sample_curriculum.save(Path(tmp.name))
                
                # Load it back
                loaded = Curriculum.load(Path(tmp.name))
                
                # Verify the loaded curriculum matches the original
                self.assertEqual(loaded.learning_objective, 
                               self.sample_curriculum.learning_objective)
                self.assertEqual(len(loaded.days), 2)
                self.assertEqual(loaded.days[0].title, "Day 1")
                self.assertEqual(loaded.days[1].title, "Day 2")
                
            finally:
                # Clean up the temporary file
                try:
                    os.unlink(tmp.name)
                except:
                    pass
    
    def test_save_invalid_extension(self):
        """Test that saving with an invalid extension raises an error."""
        with self.assertRaises(ValueError):
            self.sample_curriculum.save(Path("invalid_extension.txt"))
    
    def test_load_nonexistent_file(self):
        """Test that loading a non-existent file raises an error."""
        with self.assertRaises(FileNotFoundError):
            Curriculum.load(Path("nonexistent_file.json"))
    
    def test_from_dict_invalid_data(self):
        """Test that from_dict raises an error with invalid data."""
        with self.assertRaises(ValueError):
            Curriculum.from_dict("not a dictionary")


if __name__ == "__main__":
    unittest.main()
