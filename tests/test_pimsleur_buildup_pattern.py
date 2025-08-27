#!/usr/bin/env python3
"""
Test the correct Pimsleur buildup pattern with syllable combinations.

This test verifies that the Pimsleur breakdown algorithm correctly creates
progressive syllable buildup combinations following the traditional method.
"""

import pytest
import sys
import os

# Add the parent directory to the path so we can import from utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.pimsleur_breakdown import generate_pimsleur_breakdown

class TestPimsleurBuildupPattern:
    """Test cases for Pimsleur syllable buildup patterns."""
    
    def test_three_word_phrase_buildup(self):
        """Test that three-word phrases create proper syllable buildup."""
        phrase = "paano po ginagawa"
        
        expected = [
            "paano po ginagawa",  # Full phrase
            "wa",                 # Last syllable of "ginagawa"
            "ga",                 # Previous syllable  
            "gawa",              # Buildup: ga + wa
            "na",                # Previous syllable
            "nagawa",            # Buildup: na + ga + wa
            "gi",                # First syllable
            "ginagawa",          # Complete third word
            "po",                # Second word (single syllable)
            "po ginagawa",       # Partial phrase
            "no",                # Last syllable of "paano"
            "a",                 # Previous syllable
            "ano",               # Buildup: a + no
            "pa",                # First syllable
            "paano",             # Complete first word
            "paano po ginagawa"  # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        
        # Check that all expected combinations are present
        for item in expected:
            assert item in actual, f"Missing expected item: '{item}'"
        
        # Check specific buildup combinations
        assert "gawa" in actual, "Missing buildup combination 'gawa'"
        assert "nagawa" in actual, "Missing buildup combination 'nagawa'" 
        assert "ano" in actual, "Missing buildup combination 'ano'"
        
        # Verify proper repetition pattern (should be 3: initial, before final, final)
        phrase_count = actual.count(phrase)
        assert phrase_count == 3, f"Expected exactly 3 occurrences of full phrase, got {phrase_count}"
        
        # Verify the ending pattern: paano, paano po ginagawa, paano po ginagawa
        expected_ending = ["paano", phrase, phrase]
        actual_ending = actual[-3:]
        assert actual_ending == expected_ending, f"Expected ending {expected_ending}, got {actual_ending}"
    
    def test_single_word_buildup(self):
        """Test that single multi-syllable words create proper buildup."""
        word = "ginagawa"
        
        breakdown = generate_pimsleur_breakdown(word)
        
        # Should contain progressive buildup
        assert "wa" in breakdown, "Missing syllable 'wa'"
        assert "ga" in breakdown, "Missing syllable 'ga'"
        assert "gawa" in breakdown, "Missing buildup 'gawa'"
        assert "na" in breakdown, "Missing syllable 'na'"
        assert "nagawa" in breakdown, "Missing buildup 'nagawa'"
        assert "gi" in breakdown, "Missing syllable 'gi'"
        assert "ginagawa" in breakdown, "Missing complete word 'ginagawa'"
    
    def test_two_word_buildup(self):
        """Test that two-word phrases create proper buildup for both words."""
        phrase = "paumanhin po"
        
        breakdown = generate_pimsleur_breakdown(phrase)
        
        # Should contain buildup for "paumanhin"
        assert "hin" in breakdown, "Missing syllable 'hin'"
        assert "man" in breakdown, "Missing syllable 'man'"  
        assert "manhin" in breakdown, "Missing buildup 'manhin'"
        assert "u" in breakdown, "Missing syllable 'u'"
        assert "umanhin" in breakdown, "Missing buildup 'umanhin'"
        assert "pa" in breakdown, "Missing syllable 'pa'"
        assert "paumanhin" in breakdown, "Missing complete word 'paumanhin'"
        
        # Should contain single syllable word
        assert "po" in breakdown, "Missing word 'po'"
    
    def test_consecutive_vowel_word_buildup(self):
        """Test buildup for words with consecutive vowels."""
        phrase = "paano ko"
        
        breakdown = generate_pimsleur_breakdown(phrase)
        
        # "paano" has consecutive vowels: pa-a-no
        assert "no" in breakdown, "Missing syllable 'no'"
        assert "a" in breakdown, "Missing syllable 'a'"
        assert "ano" in breakdown, "Missing buildup 'ano'"
        assert "pa" in breakdown, "Missing syllable 'pa'"
        assert "paano" in breakdown, "Missing complete word 'paano'"
    
    def test_english_loanword_no_buildup(self):
        """Test that English loanwords don't get syllable buildup."""
        phrase = "souvenir po"
        
        breakdown = generate_pimsleur_breakdown(phrase)
        
        # "souvenir" should appear as whole word only
        assert "souvenir" in breakdown, "Missing loanword 'souvenir'"
        
        # Should not contain syllable breakdowns of "souvenir"
        loanword_syllables = ["sou", "ve", "nir", "venir", "uvenir"]
        for syllable in loanword_syllables:
            assert syllable not in breakdown, f"Loanword incorrectly broken into '{syllable}'"
    
    def test_buildup_order(self):
        """Test that buildup follows correct right-to-left order."""
        phrase = "salamat po"
        
        breakdown = generate_pimsleur_breakdown(phrase)
        
        # Find positions of key elements
        try:
            mat_pos = breakdown.index("mat")
            la_pos = breakdown.index("la") 
            lamat_pos = breakdown.index("lamat")
            sa_pos = breakdown.index("sa")
            salamat_pos = breakdown.index("salamat")
        except ValueError as e:
            pytest.fail(f"Missing expected element in breakdown: {e}")
        
        # Verify correct order: mat, la, lamat, sa, salamat
        assert mat_pos < la_pos, "Incorrect order: 'mat' should come before 'la'"
        assert la_pos < lamat_pos, "Incorrect order: 'la' should come before 'lamat'"
        assert lamat_pos < sa_pos, "Incorrect order: 'lamat' should come before 'sa'"
        assert sa_pos < salamat_pos, "Incorrect order: 'sa' should come before 'salamat'"
    
    def test_final_repetition_pattern(self):
        """Test that all phrases end with proper final repetition."""
        test_phrases = [
            "paano po ginagawa",
            "salamat po", 
            "paumanhin po",
            "pwede po ba"
        ]
        
        for phrase in test_phrases:
            breakdown = generate_pimsleur_breakdown(phrase)
            
            # Should have exactly 3 occurrences (initial + before final + final)
            phrase_count = breakdown.count(phrase)
            assert phrase_count == 3, f"Phrase '{phrase}' should appear exactly 3 times, got {phrase_count}"
            
            # Should start and end with the full phrase
            assert breakdown[0] == phrase, f"Should start with full phrase: {phrase}"
            assert breakdown[-1] == phrase, f"Should end with full phrase: {phrase}"

if __name__ == "__main__":
    # Run the tests if executed directly
    pytest.main([__file__, "-v"])