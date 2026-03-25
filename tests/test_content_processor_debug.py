#!/usr/bin/env python3
"""
Unit tests for content post-processor debugging
"""

import pytest
from unittest.mock import patch

from utils.content_post_processor import extract_key_phrases_sections, fix_pimsleur_breakdowns
from utils.pimsleur_breakdown import generate_pimsleur_breakdown


class TestContentProcessorDebug:
    """Test content post-processor debugging functionality."""

    @pytest.fixture
    def sample_content(self):
        """Sample content for testing."""
        return """[NARRATOR]: Day 14: Shopping - Day 6 Revisited

Key Phrases:

[TAGALOG-FEMALE-1]: meron po ba kayo
[NARRATOR]: do you have
[TAGALOG-FEMALE-1]: meron po ba kayo
kayo
ba kayo
po ba kayo
ron po ba kayo
me
meron
meron po
meron po ba
meron po ba kayo
meron po ba kayo

[NARRATOR]: Natural Speed"""

    def test_extract_key_phrases(self, sample_content):
        """Test phrase extraction from content."""
        phrases = extract_key_phrases_sections(sample_content)
        
        # Should extract at least one phrase
        assert len(phrases) > 0
        
        # First phrase should be the main phrase
        phrase, start, end, breakdown = phrases[0]
        assert phrase == "meron po ba kayo"
        assert isinstance(start, int)
        assert isinstance(end, int)
        assert isinstance(breakdown, list)

    @patch('utils.pimsleur_breakdown._load_english_dictionary')
    @patch('utils.pimsleur_breakdown._load_tagalog_dictionary')
    def test_algorithmic_breakdown_generation(self, mock_tagalog_dict, mock_english_dict, sample_content):
        """Test algorithmic Pimsleur breakdown generation with mocked dictionaries."""
        # Mock dictionaries to provide necessary vocabulary
        mock_tagalog_dict.return_value = {'meron', 'po', 'ba', 'kayo'}
        mock_english_dict.return_value = {'have', 'you', 'do'}
        
        # Extract phrases
        phrases = extract_key_phrases_sections(sample_content)
        assert len(phrases) > 0
        
        # Test algorithmic generation
        phrase = phrases[0][0]  # "meron po ba kayo"
        correct_breakdown = generate_pimsleur_breakdown(phrase)
        
        # Verify breakdown structure
        assert isinstance(correct_breakdown, list)
        assert len(correct_breakdown) > 0
        assert phrase in correct_breakdown  # Should contain the full phrase
        
        # Should contain syllable components
        assert "kayo" in correct_breakdown
        assert "po" in correct_breakdown

    @patch('utils.pimsleur_breakdown._load_english_dictionary')
    @patch('utils.pimsleur_breakdown._load_tagalog_dictionary')
    def test_detailed_fix_processing(self, mock_tagalog_dict, mock_english_dict, sample_content):
        """Test detailed fix processing with mocked dictionaries."""
        # Mock dictionaries
        mock_tagalog_dict.return_value = {'meron', 'po', 'ba', 'kayo'}
        mock_english_dict.return_value = {'have', 'you', 'do'}
        
        # Test fix processing
        corrected = fix_pimsleur_breakdowns(sample_content)
        
        # Verify content was processed
        assert isinstance(corrected, str)
        assert len(corrected) > 0
        assert "meron po ba kayo" in corrected

    def test_line_analysis(self, sample_content):
        """Test line-by-line content analysis."""
        lines = sample_content.split('\n')
        
        # Verify content structure
        assert len(lines) > 10
        assert any("[TAGALOG-FEMALE-1]:" in line for line in lines)
        assert any("[NARRATOR]:" in line for line in lines)

    @patch('utils.pimsleur_breakdown._load_english_dictionary')
    @patch('utils.pimsleur_breakdown._load_tagalog_dictionary')
    def test_debug_output_generation(self, mock_tagalog_dict, mock_english_dict, sample_content, capsys):
        """Test that debug output can be generated without errors."""
        # Mock dictionaries
        mock_tagalog_dict.return_value = {'meron', 'po', 'ba', 'kayo'}
        mock_english_dict.return_value = {'have', 'you', 'do'}
        
        # Run debug analysis
        self._run_debug_analysis(sample_content)
        
        # Verify no exceptions were raised
        captured = capsys.readouterr()
        # Debug output should be captured (or empty if not printing)

    def _run_debug_analysis(self, sample_content):
        """Internal method to run debug analysis without printing."""
        # Extract phrases
        phrases = extract_key_phrases_sections(sample_content)
        
        # Algorithmic generation
        if phrases:
            phrase = phrases[0][0]
            correct_breakdown = generate_pimsleur_breakdown(phrase)
            assert len(correct_breakdown) > 0
        
        # Line analysis
        lines = sample_content.split('\n')
        assert len(lines) > 0
        
        # Fix processing
        corrected = fix_pimsleur_breakdowns(sample_content)
        assert len(corrected) > 0


# For backwards compatibility, allow running as script
if __name__ == "__main__":
    # Run tests when executed as script
    pytest.main([__file__, "-v"])