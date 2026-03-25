"""Tests for dynamic curriculum file discovery functionality."""

import pytest
import tempfile
import json
import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from main import CLI
# from collocation_extractor import CollocationExtractor # Removed - using LLM-based extraction


class TestCurriculumFileDiscovery:
    """Test dynamic curriculum file discovery and CLI integration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.cli = CLI()
        
    def test_find_curriculum_file_returns_none_if_no_directory(self):
        """Test that _find_curriculum_file returns None when curricula directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock curricula directory that doesn't exist
            non_existent_dir = Path(temp_dir) / "non_existent"
            
            with patch('config.CURRICULA_DIR', non_existent_dir):
                result = self.cli._find_curriculum_file()
                
            assert result is None
    
    def test_find_curriculum_file_returns_none_if_no_files(self):
        """Test that _find_curriculum_file returns None when no curriculum files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty curricula directory
            curricula_dir = Path(temp_dir) / "curricula"
            curricula_dir.mkdir()
            
            with patch('config.CURRICULA_DIR', curricula_dir):
                result = self.cli._find_curriculum_file()
                
            assert result is None
    
    def test_find_curriculum_file_finds_single_file(self):
        """Test that _find_curriculum_file finds a single curriculum file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create curricula directory with one file
            curricula_dir = Path(temp_dir) / "curricula"
            curricula_dir.mkdir()
            
            curriculum_file = curricula_dir / "curriculum_test.json"
            curriculum_file.write_text('{"test": "data"}')
            
            with patch('config.CURRICULA_DIR', curricula_dir):
                result = self.cli._find_curriculum_file()
                
            assert result is not None
            assert result.name == "curriculum_test.json"
    
    def test_find_curriculum_file_returns_most_recent(self):
        """Test that _find_curriculum_file returns the most recently modified file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create curricula directory with multiple files
            curricula_dir = Path(temp_dir) / "curricula"
            curricula_dir.mkdir()
            
            # Create first file
            old_file = curricula_dir / "curriculum_old.json"
            old_file.write_text('{"test": "old"}')
            
            # Sleep to ensure different modification times
            time.sleep(0.1)
            
            # Create second file (more recent)
            new_file = curricula_dir / "curriculum_new.json"
            new_file.write_text('{"test": "new"}')
            
            with patch('config.CURRICULA_DIR', curricula_dir):
                result = self.cli._find_curriculum_file()
                
            assert result is not None
            assert result.name == "curriculum_new.json"
    
    def test_find_curriculum_file_matches_pattern(self):
        """Test that _find_curriculum_file only finds files matching curriculum*.json pattern."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create curricula directory with mixed files
            curricula_dir = Path(temp_dir) / "curricula"
            curricula_dir.mkdir()
            
            # Create files that should match
            (curricula_dir / "curriculum.json").write_text('{"test": "data"}')
            (curricula_dir / "curriculum_test.json").write_text('{"test": "data"}')
            
            # Create files that should not match
            (curricula_dir / "other.json").write_text('{"test": "data"}')
            (curricula_dir / "curriculum.txt").write_text('test')
            
            with patch('config.CURRICULA_DIR', curricula_dir):
                result = self.cli._find_curriculum_file()
                
            assert result is not None
            assert result.name.startswith("curriculum")
            assert result.name.endswith(".json")
    
    def test_view_curriculum_with_dynamic_discovery(self):
        """Test that view curriculum command works with dynamic file discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create curricula directory with test file
            curricula_dir = Path(temp_dir) / "curricula"
            curricula_dir.mkdir()
            
            curriculum_data = {
                "learning_objective": "Test Learning Spanish",
                "target_language": "Spanish",
                "learner_level": "A2",
                "days": [
                    {"day": 1, "title": "Day 1: Greetings"},
                    {"day": 2, "title": "Day 2: Numbers"}
                ]
            }
            
            curriculum_file = curricula_dir / "curriculum_learn_spanish.json"
            curriculum_file.write_text(json.dumps(curriculum_data, indent=2))
            
            with patch('config.CURRICULA_DIR', curricula_dir):
                with patch('builtins.print') as mock_print:
                    result = self.cli._view_curriculum()
                    
            assert result == 0
            # Verify that curriculum content was printed
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("Test Learning Spanish" in call for call in print_calls)
            assert any("Spanish" in call for call in print_calls)
            assert any("Day 1: Greetings" in call for call in print_calls)
    
    def test_view_curriculum_no_file_found(self):
        """Test that view curriculum command handles no curriculum file gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty curricula directory
            curricula_dir = Path(temp_dir) / "curricula"
            curricula_dir.mkdir()
            
            with patch('config.CURRICULA_DIR', curricula_dir):
                with patch('builtins.print') as mock_print:
                    result = self.cli._view_curriculum()
                    
            assert result == 1
            # Verify error message was printed
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("No curriculum found" in call for call in print_calls)
    
    # def test_extract_with_dynamic_discovery(self):
    #     """Test that extract command works with dynamic file discovery."""
    #     # This test was disabled because the extract command was removed in CLI cleanup
    #     pass
    
