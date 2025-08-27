"""
Comprehensive test cases for all Pimsleur breakdowns in Day 16 story.
Based on the corrected expected patterns confirmed by the user.

These tests capture the exact breakdown patterns that should be generated
for every phrase in the Key Phrases section of story_day16.
"""

import pytest
from utils.pimsleur_breakdown import generate_pimsleur_breakdown


class TestStoryDay16PimsleurBreakdowns:
    """Test all Pimsleur breakdowns from Day 16 story with correct expected patterns."""

    def test_paano_po_ginagawa_breakdown(self):
        """Test 'paano po ginagawa' breakdown - corrected syllabification pa-a-no."""
        phrase = "paano po ginagawa"
        expected = [
            "paano po ginagawa",    # Full phrase
            "wa",                   # Last syllable of ginagawa
            "ga",                   # Previous syllable
            "gawa",                 # Buildup ga+wa
            "na",                   # Previous syllable
            "nagawa",               # Buildup na+ga+wa
            "gi",                   # First syllable
            "ginagawa",             # Complete ginagawa
            "po",                   # po (single syllable)
            "po ginagawa",          # Partial phrase
            "no",                   # Last syllable of paano (pa-a-no)
            "a",                    # Middle syllable of paano
            "ano",                  # Buildup a+no
            "pa",                   # First syllable of paano
            "paano",                # Complete paano
            "paano po ginagawa",    # Final phrase
            "paano po ginagawa"     # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_ano_pong_masasabi_ninyo_breakdown(self):
        """Test 'ano pong masasabi ninyo' breakdown - the main corrected example."""
        phrase = "ano pong masasabi ninyo"
        expected = [
            "ano pong masasabi ninyo",  # Full phrase
            "yo",                       # Last syllable of ninyo
            "nin",                      # Previous syllable of ninyo  
            "ninyo",                    # Complete ninyo
            "bi",                       # Last syllable of masasabi (IMMEDIATE breakdown)
            "sa",                       # Previous syllable
            "sabi",                     # Buildup sa+bi
            "sa",                       # Previous syllable
            "sasabi",                   # Buildup sa+sa+bi  
            "ma",                       # First syllable
            "masasabi",                 # Complete masasabi
            "masasabi ninyo",          # Partial phrase (AFTER masasabi is complete)
            "pong",                     # pong word (single syllable)
            "pong masasabi ninyo",     # Partial phrase with pong
            "no",                       # Last syllable of ano (a-no)
            "a",                        # First syllable of ano
            "ano",                      # Complete ano
            "ano pong masasabi ninyo", # Final phrase
            "ano pong masasabi ninyo"  # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_specialty_talaga_namin_breakdown(self):
        """Test 'specialty talaga namin' breakdown - corrected English loanword handling."""
        phrase = "specialty talaga namin"
        expected = [
            "specialty talaga namin",   # Full phrase
            "min",                      # Last syllable of namin
            "na",                       # Previous syllable of namin
            "namin",                    # Complete namin
            "ga",                       # Last syllable of talaga
            "la",                       # Previous syllable of talaga
            "laga",                     # Buildup la+ga
            "ta",                       # First syllable of talaga
            "talaga",                   # Complete talaga
            "talaga namin",            # Partial phrase
            "specialty",                # English loanword (no breakdown)
            "specialty talaga namin",   # Final phrase
            "specialty talaga namin"    # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_paumanhin_po_breakdown(self):
        """Test 'paumanhin po' breakdown - confirmed correct."""
        phrase = "paumanhin po"
        expected = [
            "paumanhin po",     # Full phrase
            "po",               # Last word (single syllable)
            "hin",              # Last syllable of paumanhin
            "man",              # Previous syllable
            "manhin",           # Buildup man+hin
            "u",                # Previous syllable
            "umanhin",          # Buildup u+man+hin
            "pa",               # First syllable
            "paumanhin",        # Complete paumanhin
            "paumanhin po",     # Final phrase
            "paumanhin po"      # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_bakit_po_recommended_breakdown(self):
        """Test 'bakit po recommended' breakdown - corrected English loanword handling."""
        phrase = "bakit po recommended"
        expected = [
            "bakit po recommended",     # Full phrase
            "recommended",              # English loanword (no breakdown)
            "po",                       # Previous word (single syllable)
            "po recommended",           # Partial phrase
            "kit",                      # Last syllable of bakit
            "ba",                       # First syllable of bakit
            "bakit",                    # Complete bakit
            "bakit po recommended",     # Final phrase
            "bakit po recommended"      # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_maraming_salamat_sa_inyo_breakdown(self):
        """Test 'maraming salamat sa inyo' breakdown - corrected partial phrase sequence."""
        phrase = "maraming salamat sa inyo"
        expected = [
            "maraming salamat sa inyo", # Full phrase
            "yo",                       # Last syllable of inyo
            "in",                       # Previous syllable of inyo
            "inyo",                     # Complete inyo
            "sa",                       # Previous word (single syllable)
            "sa inyo",                  # Partial phrase
            "mat",                      # Last syllable of salamat
            "la",                       # Previous syllable of salamat
            "lamat",                    # Buildup la+mat
            "sa",                       # First syllable of salamat
            "salamat",                  # Complete salamat
            "salamat sa inyo",          # Partial phrase
            "ming",                     # Last syllable of maraming
            "ra",                       # Previous syllable of maraming
            "raming",                   # Buildup ra+ming
            "ma",                       # First syllable of maraming
            "maraming",                 # Complete maraming
            "maraming salamat sa inyo", # Final phrase
            "maraming salamat sa inyo"  # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_ano_pong_gusto_ninyo_breakdown(self):
        """Test 'ano pong gusto ninyo' breakdown - confirmed correct."""
        phrase = "ano pong gusto ninyo"
        expected = [
            "ano pong gusto ninyo",     # Full phrase
            "yo",                       # Last syllable of ninyo
            "nin",                      # Previous syllable of ninyo
            "ninyo",                    # Complete ninyo
            "to",                       # Last syllable of gusto
            "gus",                      # Previous syllable of gusto
            "gusto",                    # Complete gusto
            "gusto ninyo",             # Partial phrase
            "pong",                     # Previous word (single syllable)
            "pong gusto ninyo",        # Partial phrase
            "no",                       # Last syllable of ano
            "a",                        # First syllable of ano
            "ano",                      # Complete ano
            "ano pong gusto ninyo",    # Final phrase
            "ano pong gusto ninyo"     # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_puwede_po_bang_malaman_breakdown(self):
        """Test 'puwede po bang malaman' breakdown - corrected spelling and syllabification."""
        phrase = "puwede po bang malaman"
        expected = [
            "puwede po bang malaman",    # Full phrase
            "man",                      # Last syllable of malaman
            "la",                       # Previous syllable of malaman
            "laman",                    # Buildup la+man
            "ma",                       # First syllable of malaman
            "malaman",                  # Complete malaman
            "bang",                     # Previous word (single syllable)
            "bang malaman",            # Partial phrase
            "po",                       # Previous word (single syllable)
            "po bang malaman",         # Partial phrase
            "de",                       # Last syllable of puwede (pu-we-de)
            "we",                      # Previous syllable of puwede
            "wede",                    # Buildup we+de
            "pu",                      # First syllable of puwede
            "puwede",                    # Complete puwede
            "puwede po bang malaman",   # Final phrase
            "puwede po bang malaman"    # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"


class TestKeyPatternValidation:
    """Additional tests to validate the key pattern requirements."""

    def test_syllable_breakdown_before_partial_phrases(self):
        """Ensure syllable breakdown happens BEFORE partial phrases for multi-syllable words."""
        phrase = "salamat po"
        breakdown = generate_pimsleur_breakdown(phrase)
        
        # Find key positions
        mat_pos = breakdown.index("mat")
        salamat_complete_pos = breakdown.index("salamat")
        
        # Find positions of the full phrase (appears multiple times)
        salamat_po_positions = [i for i, x in enumerate(breakdown) if x == "salamat po"]
        final_phrase_pos = salamat_po_positions[-1]  # Last occurrence
        
        # Syllable breakdown should happen before any partial phrase building
        assert mat_pos < salamat_complete_pos, "Syllable 'mat' should appear before complete word 'salamat'"
        assert salamat_complete_pos < final_phrase_pos, "Complete word should appear before final phrase repetition"

    def test_english_loanwords_not_broken_down(self):
        """Ensure English loanwords are not syllabified."""
        phrase = "hotel restaurant"
        breakdown = generate_pimsleur_breakdown(phrase)
        
        # Should not contain syllable fragments of English words
        for step in breakdown:
            assert step not in ["ho", "tel", "res", "tau", "rant"], f"English loanword syllables found: {step}"
        
        # Should contain whole English words
        assert "hotel" in breakdown, "Complete English word 'hotel' should be present"
        assert "restaurant" in breakdown, "Complete English word 'restaurant' should be present"

    def test_right_to_left_processing_order(self):
        """Verify words are processed right-to-left with immediate syllable breakdown."""
        phrase = "ano salamat"  # Simple 2-word phrase
        breakdown = generate_pimsleur_breakdown(phrase)
        
        # Find positions
        mat_pos = breakdown.index("mat")  # Start of salamat breakdown
        salamat_pos = breakdown.index("salamat")  # End of salamat breakdown
        ano_syllable_pos = breakdown.index("a")  # Start of ano breakdown (assuming ano = a-no)
        
        # salamat should be completely processed before ano breakdown starts
        assert salamat_pos < ano_syllable_pos, "Word 'salamat' should be completely processed before 'ano' breakdown begins"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v"])