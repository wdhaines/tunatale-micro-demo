"""Tests for source day transcript loading functionality."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from story_generator import ContentGenerator


class TestSourceTranscriptLoading:
    """Test source day transcript loading with various file naming patterns."""
    
    def test_load_source_day_transcript_story_day_format(self):
        """Test loading transcript with story_dayX_*.txt format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test story file
            stories_dir = Path(temp_dir) / "stories"
            stories_dir.mkdir()
            
            story_file = stories_dir / "story_day4_test_story.txt"
            test_content = "[NARRATOR]: Day 4: Test Story\n\nKey Phrases:\n\n[TAGALOG-FEMALE-1]: test phrase"
            story_file.write_text(test_content)
            
            # Create a minimal generator just for this method
            generator = ContentGenerator.__new__(ContentGenerator)
            
            # Mock the stories directory
            with patch('config.STORIES_DIR', stories_dir):
                transcript = generator._load_source_day_transcript(4)
                
            assert transcript is not None
            assert "Day 4: Test Story" in transcript
            assert "test phrase" in transcript
    
    def test_load_source_day_transcript_demo_format(self):
        """Test loading transcript with demo-X.X.X-day-X.txt format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test story file
            stories_dir = Path(temp_dir) / "stories"
            stories_dir.mkdir()
            
            story_file = stories_dir / "demo-0.0.3-day-4.txt"
            test_content = "# Day 4: Getting Around Town\n\n[NARRATOR]: Day 4: Getting Around Town"
            story_file.write_text(test_content)
            
            # Create a minimal generator just for this method
            generator = ContentGenerator.__new__(ContentGenerator)
            
            # Mock the stories directory
            with patch('config.STORIES_DIR', stories_dir):
                transcript = generator._load_source_day_transcript(4)
                
            assert transcript is not None
            assert "Day 4: Getting Around Town" in transcript
    
    def test_load_source_day_transcript_not_found(self):
        """Test handling when source day transcript is not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty stories directory
            stories_dir = Path(temp_dir) / "stories"
            stories_dir.mkdir()
            
            # Create a minimal generator just for this method
            generator = ContentGenerator.__new__(ContentGenerator)
            
            # Mock the stories directory
            with patch('config.STORIES_DIR', stories_dir):
                transcript = generator._load_source_day_transcript(99)
                
            assert transcript is None
    
    def test_load_source_day_transcript_multiple_patterns(self):
        """Test that the method works with multiple naming patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test story files in different formats
            stories_dir = Path(temp_dir) / "stories"
            stories_dir.mkdir()
            
            # Create multiple files for the same day
            (stories_dir / "story_day4_old_format.txt").write_text("Old format content")
            (stories_dir / "demo-0.0.3-day-4.txt").write_text("Demo format content")
            
            # Create a minimal generator just for this method
            generator = ContentGenerator.__new__(ContentGenerator)
            
            # Mock the stories directory
            with patch('config.STORIES_DIR', stories_dir):
                transcript = generator._load_source_day_transcript(4)
                
            assert transcript is not None
            # Should find one of the files (first match in glob order)
            assert "content" in transcript
    
    def test_load_source_day_transcript_error_handling(self):
        """Test error handling in source day transcript loading."""
        # Create a minimal generator just for this method
        generator = ContentGenerator.__new__(ContentGenerator)
        
        # Test with non-existent directory
        with patch('config.STORIES_DIR', Path("/non/existent/directory")):
            transcript = generator._load_source_day_transcript(4)
            
        assert transcript is None
        
    def test_deeper_prompt_has_transcript_variable(self):
        """Test that DEEPER prompt template includes source transcript variable."""
        # Mock prompt loading to return a template with the variable
        mock_deeper_prompt = """
        **DEEPER Strategy Content Generation Request**
        
        **SOURCE DAY TRANSCRIPT TO ENHANCE:**
        ```
        {source_day_transcript}
        ```
        
        **Instructions:** Use the source transcript above...
        """
        
        def mock_load_prompt(filename):
            if filename == 'story_prompt_deeper.txt':
                return mock_deeper_prompt
            return "Mock prompt"
        
        with patch.object(ContentGenerator, '_load_prompt', side_effect=mock_load_prompt):
            with patch('story_generator.SRSTracker'):  # Mock SRS to avoid test data issues
                generator = ContentGenerator()
            
        assert hasattr(generator, 'story_prompt_deeper')
        assert generator.story_prompt_deeper is not None
        assert '{source_day_transcript}' in generator.story_prompt_deeper
        assert 'SOURCE DAY TRANSCRIPT TO ENHANCE:' in generator.story_prompt_deeper