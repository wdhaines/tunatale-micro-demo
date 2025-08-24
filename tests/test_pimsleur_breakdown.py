"""
Comprehensive test suite for Pimsleur breakdown generation.

Tests the traditional Pimsleur method based on verified Day 14 examples.
"""

import pytest
from utils.pimsleur_breakdown import generate_pimsleur_breakdown, is_english_loanword, syllabify_tagalog_word


class TestEnglishLoanwordDetection:
    """Test English loanword detection functionality."""
    
    def test_common_english_loanwords(self):
        """Test common English loanwords are detected correctly."""
        english_words = ['souvenir', 'camera', 'hotel', 'restaurant', 'photo', 'budget']
        for word in english_words:
            assert is_english_loanword(word), f"'{word}' should be detected as English loanword"
            
    def test_case_insensitive_detection(self):
        """Test English loanword detection is case insensitive."""
        assert is_english_loanword('SOUVENIR')
        assert is_english_loanword('Camera')
        assert is_english_loanword('HoTeL')
        
    def test_tagalog_words_not_detected(self):
        """Test Tagalog words are not detected as English loanwords."""
        tagalog_words = ['salamat', 'kumusta', 'magkano', 'puwede', 'meron', 'kayo']
        for word in tagalog_words:
            assert not is_english_loanword(word), f"'{word}' should not be detected as English loanword"


class TestSyllabifyTagalogWord:
    """Test Tagalog word syllabification."""
    
    def test_known_syllable_patterns(self):
        """Test words with known syllable patterns."""
        test_cases = [
            ('salamat', ['sa', 'la', 'mat']),
            ('kumusta', ['ku', 'mus', 'ta']),
            ('magkano', ['mag', 'ka', 'no']),
            ('puwede', ['pu', 'we', 'de']),
            ('meron', ['me', 'ron']),
            ('kayo', ['ka', 'yo']),
            ('lahat', ['la', 'hat']),
        ]
        
        for word, expected_syllables in test_cases:
            result = syllabify_tagalog_word(word)
            assert result == expected_syllables, f"'{word}' should syllabify to {expected_syllables}, got {result}"
    
    def test_unknown_words_syllabified_heuristically(self):
        """Test unknown words are syllabified using Filipino heuristic rules."""
        test_cases = [
            ('xyz', ['xyz']),  # No clear vowel pattern -> single syllable
            ('unknown', ['un', 'know', 'n']),  # Clear vowel pattern -> syllabified
            ('newword', ['new', 'wor', 'd'])   # Clear vowel pattern -> syllabified
        ]
        for word, expected in test_cases:
            result = syllabify_tagalog_word(word)
            assert result == expected, f"'{word}' should syllabify to {expected}, got {result}"


class TestPimsleurBreakdownBasic:
    """Test basic Pimsleur breakdown functionality."""
    
    def test_empty_input(self):
        """Test empty or None input returns empty list."""
        assert generate_pimsleur_breakdown("") == []
        assert generate_pimsleur_breakdown("   ") == []
        assert generate_pimsleur_breakdown(None) == []
    
    def test_single_syllable_word(self):
        """Test single syllable words."""
        result = generate_pimsleur_breakdown("po")
        expected = ["po"]
        assert result == expected, f"Expected {expected}, got {result}"
        
    def test_english_loanword_single_word(self):
        """Test English loanwords are not broken down."""
        result = generate_pimsleur_breakdown("souvenir")
        expected = ["souvenir"]
        assert result == expected, f"English loanword should not be broken down. Expected {expected}, got {result}"


class TestPimsleurBreakdownVerifiedExamples:
    """Test against all verified examples from user testing."""
    
    def test_salamat_po(self):
        """Test 'salamat po' breakdown - verified example."""
        result = generate_pimsleur_breakdown("salamat po")
        expected = [
            "salamat po",    # Full phrase
            "po",            # Last word
            "mat",           # Last syllable of first word
            "la",            # Previous syllable
            "lamat",         # Last two syllables combined
            "sa",            # First syllable
            "salamat",       # Complete first word
            "salamat po",    # Complete phrase
            "salamat po"     # Final repetition
        ]
        assert result == expected, f"Expected {expected}, got {result}"
        
    def test_kumusta_po(self):
        """Test 'kumusta po' breakdown - verified example."""
        result = generate_pimsleur_breakdown("kumusta po")
        expected = [
            "kumusta po",    # Full phrase
            "po",            # Last word
            "ta",            # Last syllable of first word  
            "mus",           # Previous syllable
            "musta",         # Last two syllables combined
            "ku",            # First syllable
            "kumusta",       # Complete first word
            "kumusta po",    # Complete phrase
            "kumusta po"     # Final repetition
        ]
        assert result == expected, f"Expected {expected}, got {result}"
        
    def test_puwede_po_ba(self):
        """Test 'puwede po ba' breakdown - verified example."""
        result = generate_pimsleur_breakdown("puwede po ba")
        expected = [
            "puwede po ba",  # Full phrase
            "ba",            # Last word
            "po",            # Previous word
            "po ba",         # Previous word + last word
            "de",            # Last syllable of first word
            "we",            # Previous syllable
            "wede",          # Last two syllables combined  
            "pu",            # First syllable
            "puwede",        # Complete first word
            "puwede po ba",  # Complete phrase
            "puwede po ba"   # Final repetition
        ]
        assert result == expected, f"Expected {expected}, got {result}"
        
    def test_salamat_po_sa_lahat(self):
        """Test 'salamat po sa lahat' breakdown - verified example."""
        result = generate_pimsleur_breakdown("salamat po sa lahat")
        expected = [
            "salamat po sa lahat",  # Full phrase
            "hat",                  # Last syllable of "lahat"
            "la",                   # Previous syllable of "lahat"  
            "lahat",                # Complete "lahat"
            "sa",                   # Previous word
            "sa lahat",             # Previous word + "lahat"
            "po",                   # Previous word
            "po sa lahat",          # Build backwards
            "mat",                  # Last syllable of "salamat" 
            "la",                   # Previous syllable
            "lamat",                # Last two syllables combined
            "sa",                   # First syllable  
            "salamat",              # Complete "salamat"
            "salamat po sa lahat",  # Complete phrase
            "salamat po sa lahat"   # Final repetition
        ]
        assert result == expected, f"Expected {expected}, got {result}"


class TestPimsleurBreakdownComplexExamples:
    """Test complex examples with English loanwords and multiple multi-syllable words."""
    
    def test_meron_po_ba_kayo_ng_magandang_souvenir(self):
        """Test complex phrase with English loanword - verified example."""
        result = generate_pimsleur_breakdown("meron po ba kayo ng magandang souvenir")
        expected = [
            "meron po ba kayo ng magandang souvenir",  # Full phrase
            "souvenir",                                # English loanword (no breakdown)
            "dang",                                    # Last syllable of "magandang"
            "gan",                                     # Previous syllable
            "gandang",                                 # Last two syllables combined
            "ma",                                      # First syllable
            "magandang",                               # Complete "magandang"
            "magandang souvenir",                      # Build partial phrase
            "ng",                                      # Previous word
            "ng magandang souvenir",                   # Build backwards
            "yo",                                      # Last syllable of "kayo"
            "ka",                                      # First syllable
            "kayo",                                    # Complete "kayo"
            "kayo ng magandang souvenir",              # Build partial phrase
            "ba",                                      # Previous word
            "ba kayo ng magandang souvenir",           # Build backwards
            "po",                                      # Previous word  
            "po ba kayo ng magandang souvenir",        # Build backwards
            "ron",                                     # Last syllable of "meron"
            "me",                                      # First syllable
            "meron",                                   # Complete "meron"
            "meron po ba kayo ng magandang souvenir",  # Complete phrase
            "meron po ba kayo ng magandang souvenir"   # Final repetition
        ]
        assert result == expected, f"Expected {expected}, got {result}"
        
    def test_mixed_single_multi_syllable(self):
        """Test phrase mixing single and multi-syllable words."""
        result = generate_pimsleur_breakdown("ako po")
        expected = [
            "ako po",        # Full phrase
            "po",            # Last word (single syllable)
            "ko",            # Last syllable of "ako"
            "a",             # First syllable
            "ako",           # Complete "ako"
            "ako po",        # Complete phrase
            "ako po"         # Final repetition
        ]
        assert result == expected, f"Expected {expected}, got {result}"


class TestPimsleurBreakdownEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_all_single_syllable_words(self):
        """Test phrase with only single-syllable words."""
        result = generate_pimsleur_breakdown("sa po ba")
        expected = [
            "sa po ba",      # Full phrase
            "ba",            # Last word
            "po",            # Previous word  
            "po ba",         # Build backwards
            "sa",            # Previous word
            "sa po ba"       # Final repetition
        ]
        assert result == expected, f"Expected {expected}, got {result}"
        
    def test_all_english_loanwords(self):
        """Test phrase with only English loanwords."""  
        result = generate_pimsleur_breakdown("hotel restaurant")
        expected = [
            "hotel restaurant",  # Full phrase
            "restaurant",        # Last word (English)
            "hotel",             # Previous word (English) 
            "hotel restaurant"   # Final repetition
        ]
        assert result == expected, f"Expected {expected}, got {result}"
        
    def test_phrase_with_whitespace(self):
        """Test phrase with extra whitespace is handled correctly."""
        result = generate_pimsleur_breakdown("  salamat   po  ")
        expected = generate_pimsleur_breakdown("salamat po")  # Should be same as cleaned version
        assert result == expected, f"Whitespace should be normalized"


class TestPimsleurBreakdownRegression:
    """Test to prevent regressions from previous versions."""
    
    def test_no_duplicate_final_phrases(self):
        """Test that final phrases are not duplicated incorrectly."""
        result = generate_pimsleur_breakdown("salamat po")
        
        # Count occurrences of the full phrase
        full_phrase_count = result.count("salamat po")
        
        # Should appear exactly 3 times: initial, before final, and final
        assert full_phrase_count == 3, f"Full phrase should appear exactly 3 times, got {full_phrase_count} in {result}"
        
    def test_syllable_order_backwards(self):
        """Test that syllables are processed in backwards order."""
        result = generate_pimsleur_breakdown("salamat")
        
        # Find syllable positions
        mat_pos = result.index("mat") if "mat" in result else -1
        la_pos = result.index("la") if "la" in result else -1  
        sa_pos = result.index("sa") if "sa" in result else -1
        
        assert mat_pos != -1 and la_pos != -1 and sa_pos != -1, "All syllables should be present"
        assert mat_pos < la_pos < sa_pos, f"Syllables should be in backwards order: mat({mat_pos}) < la({la_pos}) < sa({sa_pos})"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v"])