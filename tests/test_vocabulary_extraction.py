"""Tests for vocabulary extraction and Natural Speed section filtering."""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from cli.vocab_commands import _extract_natural_speed_content, _extract_from_file
from collocation_extractor import CollocationExtractor


# Sample story content with all sections for testing
SAMPLE_STORY_COMPLETE = '''[NARRATOR]: Day 15: Test Story - Sunset viewing

Key Phrases:

[TAGALOG-FEMALE-1]: salamat po
[NARRATOR]: thank you
salamat po
po
mat
la
lamat
sa
salamat
salamat po
salamat po

[TAGALOG-FEMALE-1]: kumusta po
[NARRATOR]: how are you  
kumusta po
po
ta
mus
musta
ku
kumusta
kumusta po
kumusta po

[NARRATOR]: Natural Speed

[NARRATOR]: At the Viewpoint

[TAGALOG-MALE-1]: Good afternoon po! Welcome sa Taraw Cliff.
[TAGALOG-FEMALE-1]: Kumusta po! Magkano po ang entrance fee?
[TAGALOG-MALE-1]: Tatlumpung pesos po para sa tourist.
[TAGALOG-FEMALE-2]: Puwede po ba naming makakuha ng photos dito?
[NARRATOR]: They continue their conversation about the scenic location.

[NARRATOR]: At the Refreshment Stand

[TAGALOG-FEMALE-2]: Ate, ano po ang meron kayong drinks?
[TAGALOG-FEMALE-1]: Meron po kaming fresh buko juice at mango shake.

[NARRATOR]: Slow Speed

[NARRATOR]: At the Viewpoint

[TAGALOG-MALE-1]: Good... afternoon... po!... Welcome... sa... Taraw... Cliff.
[TAGALOG-FEMALE-1]: Kumusta... po!... Magkano... po... ang... entrance... fee?
[TAGALOG-FEMALE-2]: Puwede... po... ba... naming... makakuha... ng... photos... dito?

[NARRATOR]: Translated

[NARRATOR]: At the Viewpoint

[TAGALOG-MALE-1]: Good afternoon po! Welcome sa Taraw Cliff.
[NARRATOR]: Good afternoon! Welcome to Taraw Cliff.
[TAGALOG-FEMALE-1]: Kumusta po! Magkano po ang entrance fee?
[NARRATOR]: How are you! How much is the entrance fee?
'''

# Expected Natural Speed content (Filipino dialogue only)
EXPECTED_NATURAL_SPEED_CONTENT = (
    "Good afternoon po! Welcome sa Taraw Cliff. "
    "Kumusta po! Magkano po ang entrance fee? "
    "Tatlumpung pesos po para sa tourist. "
    "Puwede po ba naming makakuha ng photos dito? "
    "Ate, ano po ang meron kayong drinks? "
    "Meron po kaming fresh buko juice at mango shake."
)


class TestNaturalSpeedExtraction:
    """Test Natural Speed section filtering functionality."""

    def test_extract_natural_speed_content_complete_story(self):
        """Test extraction from complete story with all sections."""
        result = _extract_natural_speed_content(SAMPLE_STORY_COMPLETE)
        
        # Should extract only Filipino dialogue from Natural Speed section
        assert result == EXPECTED_NATURAL_SPEED_CONTENT
        
        # Verify specific content is included
        assert "Kumusta po! Magkano po ang entrance fee?" in result
        assert "Tatlumpung pesos po para sa tourist" in result
        assert "Meron po kaming fresh buko juice at mango shake" in result
        
        # Verify excluded content
        assert "salamat po\npo\nmat" not in result  # Key Phrases artifacts
        assert "Good... afternoon... po!" not in result  # Slow Speed ellipses
        assert "How are you!" not in result  # Translated English
        assert "[NARRATOR]:" not in result  # Narrator tags
        assert "They continue their conversation" not in result  # Narrator descriptions

    def test_extract_natural_speed_no_section_found(self):
        """Test handling when no Natural Speed section exists."""
        story_no_natural = '''[NARRATOR]: Day 1: Test Story

Key Phrases:

[TAGALOG-FEMALE-1]: salamat po
[NARRATOR]: thank you

[NARRATOR]: Slow Speed

[TAGALOG-FEMALE-1]: salamat... po
'''
        
        result = _extract_natural_speed_content(story_no_natural)
        assert result == ""

    def test_extract_natural_speed_section_boundaries(self):
        """Test correct section boundary detection."""
        story_with_boundaries = '''[NARRATOR]: Key stuff before

[NARRATOR]: Natural Speed

[TAGALOG-MALE-1]: Test dialogue in natural speed.
[TAGALOG-FEMALE-1]: Another test line.

[NARRATOR]: Slow Speed

[TAGALOG-MALE-1]: Test... dialogue... in... slow... speed.
[NARRATOR]: This should not appear.
'''
        
        result = _extract_natural_speed_content(story_with_boundaries)
        expected = "Test dialogue in natural speed. Another test line."
        
        assert result == expected
        assert "Test... dialogue... in... slow... speed." not in result
        assert "This should not appear." not in result

    def test_extract_natural_speed_ignore_narrator_lines(self):
        """Test that narrator lines within Natural Speed section are ignored."""
        story_with_narrator = '''[NARRATOR]: Natural Speed

[TAGALOG-MALE-1]: Filipino dialogue line.
[NARRATOR]: English narrator description here.
[TAGALOG-FEMALE-1]: Another Filipino line.
[NARRATOR]: More English description.
'''
        
        result = _extract_natural_speed_content(story_with_narrator)
        expected = "Filipino dialogue line. Another Filipino line."
        
        assert result == expected
        assert "English narrator description" not in result
        assert "More English description" not in result

    def test_extract_natural_speed_empty_dialogue_lines(self):
        """Test handling of empty or whitespace-only dialogue lines."""
        story_with_empty_lines = '''[NARRATOR]: Natural Speed

[TAGALOG-MALE-1]: Good dialogue.
[TAGALOG-FEMALE-1]:    
[TAGALOG-MALE-2]: 
[TAGALOG-FEMALE-2]: Another good dialogue.
'''
        
        result = _extract_natural_speed_content(story_with_empty_lines)
        expected = "Good dialogue. Another good dialogue."
        
        assert result == expected

    def test_extract_natural_speed_no_slow_speed_boundary(self):
        """Test when Natural Speed section goes to end of file."""
        story_no_slow_boundary = '''[NARRATOR]: Natural Speed

[TAGALOG-MALE-1]: First dialogue.
[TAGALOG-FEMALE-1]: Second dialogue.
[TAGALOG-MALE-2]: Final dialogue.
'''
        
        result = _extract_natural_speed_content(story_no_slow_boundary)
        expected = "First dialogue. Second dialogue. Final dialogue."
        
        assert result == expected


class TestExtractFromFileIntegration:
    """Test integration of Natural Speed filtering with file extraction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary story file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        self.temp_file.write(SAMPLE_STORY_COMPLETE)
        self.temp_file.close()
        self.story_path = Path(self.temp_file.name)
        
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.story_path.exists():
            os.unlink(self.story_path)

    def test_extract_from_file_processes_natural_speed_only(self):
        """Test that _extract_from_file only processes Natural Speed content."""
        # Mock extractor to capture what content is passed to it
        mock_extractor = Mock()
        mock_extractor.extract_collocations.return_value = {
            'kumusta po': 1,
            'magkano po': 1
        }
        
        result = _extract_from_file(mock_extractor, self.story_path, filter_noise=False)
        
        # Verify extractor was called with Natural Speed content only
        mock_extractor.extract_collocations.assert_called_once()
        
        # Get the content that was passed to the extractor
        passed_content = mock_extractor.extract_collocations.call_args[0][0]
        
        # Should contain Natural Speed dialogue
        assert "Kumusta po! Magkano po ang entrance fee?" in passed_content
        assert "Tatlumpung pesos po para sa tourist" in passed_content
        
        # Should NOT contain other sections
        assert "salamat po\npo\nmat" not in passed_content  # Key Phrases
        assert "Good... afternoon... po!" not in passed_content  # Slow Speed  
        assert "Good afternoon!" not in passed_content  # Translated English
        
        # Verify result processing
        assert result == ['kumusta po', 'magkano po']

    def test_extract_from_file_no_natural_speed_section(self):
        """Test handling when story file has no Natural Speed section."""
        # Create story file without Natural Speed section
        story_no_natural = '''[NARRATOR]: Day 1: Test

Key Phrases:
[TAGALOG-FEMALE-1]: test

[NARRATOR]: Slow Speed  
[TAGALOG-FEMALE-1]: test...
'''
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_file.write(story_no_natural)
        temp_file.close()
        temp_path = Path(temp_file.name)
        
        try:
            mock_extractor = Mock()
            result = _extract_from_file(mock_extractor, temp_path, filter_noise=False)
            
            # Should return empty list when no Natural Speed content found
            assert result == []
            
            # Extractor should not be called when no content
            mock_extractor.extract_collocations.assert_not_called()
            
        finally:
            os.unlink(temp_path)

    def test_extract_from_file_with_noise_filtering(self):
        """Test that noise filtering is applied after Natural Speed extraction."""
        mock_extractor = Mock()
        mock_extractor.extract_collocations.return_value = {
            'kumusta po': 1,
            'tagalog-female-1': 1,  # Voice tag noise that should be filtered
            'good': 1,  # English that should be filtered
            'salamat po': 1
        }
        
        # Mock the noise filter to simulate filtering behavior
        with patch('cli.vocab_commands._filter_noisy_collocations') as mock_filter:
            mock_filter.return_value = ['kumusta po', 'salamat po']  # Clean results
            
            result = _extract_from_file(mock_extractor, self.story_path, filter_noise=True)
            
            # Verify noise filtering was applied
            mock_filter.assert_called_once()
            filtered_input = mock_filter.call_args[0][0]
            assert 'kumusta po' in filtered_input
            assert 'tagalog-female-1' in filtered_input
            assert 'good' in filtered_input
            assert 'salamat po' in filtered_input
            
            # Result should be filtered
            assert result == ['kumusta po', 'salamat po']


class TestRegressionPrevention:
    """Test to prevent regression of specific issues found during development."""

    def test_no_voice_tag_extraction(self):
        """Regression test: Ensure voice tags like 'tagalog-female-1' are not extracted."""
        story_with_tags = '''[NARRATOR]: Natural Speed

[TAGALOG-FEMALE-1]: Magandang umaga po.
[TAGALOG-MALE-2]: Salamat sa pagdating.
'''
        
        result = _extract_natural_speed_content(story_with_tags)
        expected = "Magandang umaga po. Salamat sa pagdating."
        
        assert result == expected
        # Most importantly, should not contain any tag fragments
        assert "tagalog" not in result.lower()
        assert "female" not in result.lower()
        assert "male" not in result.lower()
        assert "[" not in result
        assert "]" not in result

    def test_no_syllable_breakdown_extraction(self):
        """Regression test: Ensure Key Phrases syllable breakdowns are not extracted."""
        story_with_breakdowns = '''Key Phrases:

[TAGALOG-FEMALE-1]: salamat po
salamat po
po
mat
la
lamat
sa
salamat

[NARRATOR]: Natural Speed

[TAGALOG-FEMALE-1]: Salamat po sa lahat.
'''
        
        result = _extract_natural_speed_content(story_with_breakdowns)
        expected = "Salamat po sa lahat."
        
        assert result == expected
        # Should not contain syllable fragments from Key Phrases
        assert result != "po\nmat\nla\nlamat\nsa\nsalamat"

    def test_no_slow_speed_ellipses_extraction(self):
        """Regression test: Ensure Slow Speed ellipses content is not extracted."""
        story_with_ellipses = '''[NARRATOR]: Natural Speed

[TAGALOG-MALE-1]: Kumusta ka ngayon?

[NARRATOR]: Slow Speed

[TAGALOG-MALE-1]: Kumusta... ka... ngayon?
'''
        
        result = _extract_natural_speed_content(story_with_ellipses)
        expected = "Kumusta ka ngayon?"
        
        assert result == expected
        # Should not contain ellipses from Slow Speed
        assert "..." not in result

    def test_no_narrator_english_extraction(self):
        """Regression test: Ensure English narrator content is not extracted."""
        story_with_narrator_english = '''[NARRATOR]: Natural Speed

[NARRATOR]: The tourists arrive at the scenic viewpoint.
[TAGALOG-MALE-1]: Magandang tanghali po.
[NARRATOR]: They admire the beautiful sunset views.
[TAGALOG-FEMALE-1]: Salamat sa pagdala dito.
'''
        
        result = _extract_natural_speed_content(story_with_narrator_english)
        expected = "Magandang tanghali po. Salamat sa pagdala dito."
        
        assert result == expected
        # Should not contain narrator English
        assert "tourists arrive" not in result
        assert "scenic viewpoint" not in result
        assert "admire the beautiful" not in result