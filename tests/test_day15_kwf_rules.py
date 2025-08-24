"""
Test cases for Day 15 phrases using official KWF syllabification rules.
Based on Ortograpiyang Pambansa (2013) from Komisyon ng Wikang Filipino.
"""

import pytest
from utils.pimsleur_breakdown import generate_pimsleur_breakdown, syllabify_tagalog_word


class TestDay15KWFSyllabification:
    """Test syllabification using official KWF rules."""
    
    def test_nakakamangha_syllabification(self):
        """Test 'nakakamangha' syllabification per KWF rules."""
        # Expected: na-ka-ka-mang-ha (mang is consonant cluster, ha is final CV)
        expected = ["na", "ka", "ka", "mang", "ha"]
        actual = syllabify_tagalog_word("nakakamangha")
        assert actual == expected, f"Expected {expected}, got {actual}"
    
    def test_talaga_syllabification(self):
        """Test 'talaga' syllabification per KWF rules."""
        # Expected: ta-la-ga (all CV syllables)
        expected = ["ta", "la", "ga"]
        actual = syllabify_tagalog_word("talaga")
        assert actual == expected, f"Expected {expected}, got {actual}"
    
    def test_salamat_syllabification(self):
        """Test 'salamat' syllabification per KWF rules."""
        # Expected: sa-la-mat (CVC final syllable)
        expected = ["sa", "la", "mat"]
        actual = syllabify_tagalog_word("salamat")
        assert actual == expected, f"Expected {expected}, got {actual}"
    
    def test_sarap_syllabification(self):
        """Test 'sarap' syllabification per KWF rules."""
        # Expected: sa-rap (CVC final syllable)
        expected = ["sa", "rap"]
        actual = syllabify_tagalog_word("sarap")
        assert actual == expected, f"Expected {expected}, got {actual}"
    
    def test_naman_syllabification(self):
        """Test 'naman' syllabification per KWF rules."""
        # Expected: na-man (CVC final syllable)
        expected = ["na", "man"]
        actual = syllabify_tagalog_word("naman")
        assert actual == expected, f"Expected {expected}, got {actual}"


class TestDay15PimsleurBreakdowns:
    """Test complete Pimsleur breakdowns for Day 15 phrases."""
    
    def test_nakakamangha_talaga_breakdown(self):
        """Test complete Pimsleur breakdown for 'nakakamangha talaga'."""
        phrase = "nakakamangha talaga"
        actual = generate_pimsleur_breakdown(phrase)
        
        # Expected breakdown based on correct syllabification:
        # nakakamangha: na-ka-ka-mang-ha
        # talaga: ta-la-ga
        expected = [
            "nakakamangha talaga",  # Full phrase
            "ga",                   # Last syllable of talaga
            "la",                   # Previous syllable
            "laga",                 # Last two syllables combined
            "ta",                   # First syllable of talaga
            "talaga",               # Complete talaga
            "nakakamangha talaga",  # Build back to full phrase
            "ha",                   # Last syllable of nakakamangha
            "mang",                 # Previous syllable
            "mangha",               # Last two syllables combined
            "ka",                   # Previous syllable
            "kamangha",             # Last three syllables combined
            "ka",                   # Previous syllable  
            "kakamangha",           # Last four syllables combined
            "na",                   # First syllable
            "nakakamangha",         # Complete nakakamangha
            "nakakamangha talaga",  # Complete phrase
            "nakakamangha talaga"   # Final repetition
        ]
        
        # Debug output for comparison
        print(f"\nExpected: {expected}")
        print(f"Actual:   {actual}")
        print(f"Match: {actual == expected}")
        
        assert actual == expected, f"Pimsleur breakdown mismatch for '{phrase}'"
    
    def test_sarap_naman_breakdown(self):
        """Test complete Pimsleur breakdown for 'sarap naman'."""
        phrase = "sarap naman"
        actual = generate_pimsleur_breakdown(phrase)
        
        # Expected breakdown:
        # sarap: sa-rap
        # naman: na-man
        expected = [
            "sarap naman",    # Full phrase
            "man",            # Last syllable of naman
            "na",             # First syllable of naman
            "naman",          # Complete naman
            "sarap naman",    # Build back to full phrase
            "rap",            # Last syllable of sarap
            "sa",             # First syllable of sarap
            "sarap",          # Complete sarap
            "sarap naman",    # Complete phrase
            "sarap naman"     # Final repetition
        ]
        
        # Debug output for comparison
        print(f"\nExpected: {expected}")
        print(f"Actual:   {actual}")
        print(f"Match: {actual == expected}")
        
        assert actual == expected, f"Pimsleur breakdown mismatch for '{phrase}'"
    
    def test_salamat_po_breakdown(self):
        """Test Pimsleur breakdown for 'salamat po' (should still work correctly)."""
        phrase = "salamat po"
        actual = generate_pimsleur_breakdown(phrase)
        
        expected = [
            "salamat po",    # Full phrase
            "po",            # Last word (single syllable)
            "mat",           # Last syllable of salamat
            "la",            # Previous syllable
            "lamat",         # Last two syllables combined
            "sa",            # First syllable
            "salamat",       # Complete salamat
            "salamat po",    # Complete phrase
            "salamat po"     # Final repetition
        ]
        
        assert actual == expected, f"Pimsleur breakdown mismatch for '{phrase}'"


class TestKWFConsonantClusters:
    """Test KWF consonant cluster handling."""
    
    def test_consonant_cluster_detection(self):
        """Test detection of true vs fake consonant clusters."""
        from utils.pimsleur_breakdown import _is_true_consonant_cluster
        
        # True clusters (can start syllables)
        true_clusters = ["pr", "tr", "kr", "br", "dr", "gr", "pl", "bl", "kl", "gl", "fl"]
        for cluster in true_clusters:
            assert _is_true_consonant_cluster(cluster), f"'{cluster}' should be true consonant cluster"
        
        # Fake clusters (should be split)
        fake_clusters = ["ng", "mp", "nt", "nk", "rt", "st", "pt"]
        for cluster in fake_clusters:
            assert not _is_true_consonant_cluster(cluster), f"'{cluster}' should be fake consonant cluster"
    
    def test_ng_as_single_consonant(self):
        """Test 'ng' is treated as single consonant unit."""
        # Words with 'ng' should keep it together
        test_cases = [
            ("mang", ["mang"]),           # ng at end
            ("mangga", ["mang", "ga"]),   # ng in middle
            ("ngayon", ["nga", "yon"]),   # ng at start
        ]
        
        for word, expected in test_cases:
            actual = syllabify_tagalog_word(word)
            assert actual == expected, f"'{word}' should syllabify to {expected}, got {actual}"


class TestKWFVowelSeparation:
    """Test KWF consecutive vowel separation rules."""
    
    def test_consecutive_vowel_separation(self):
        """Test that consecutive vowels are always separated per KWF Rule 2."""
        test_cases = [
            ("oo", ["o", "o"]),           # Two same vowels
            ("ea", ["e", "a"]),           # Two different vowels  
            ("iyo", ["i", "yo"]),         # i + other vowel
            ("iya", ["i", "ya"]),         # i + other vowel
            ("uyo", ["u", "yo"]),         # u + other vowel
        ]
        
        for word, expected in test_cases:
            actual = syllabify_tagalog_word(word)
            assert actual == expected, f"'{word}' should syllabify to {expected}, got {actual}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])