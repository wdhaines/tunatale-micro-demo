"""
Test cases for Day 15 Pimsleur breakdown failures.

These tests capture the specific failing cases from Day 15 generation,
comparing current algorithm output with the expected correct breakdowns.
"""

import pytest
from utils.pimsleur_breakdown import generate_pimsleur_breakdown


class TestDay15PimsleurBreakdowns:
    """Test Day 15 specific phrases that are currently failing."""

    def test_salamat_po_breakdown(self):
        """Test 'salamat po' breakdown matches expected pattern."""
        phrase = "salamat po"
        expected = [
            "salamat po",  # Full phrase
            "po",          # Second word (single syllable)
            "mat",         # Last syllable of first word
            "la",          # Previous syllable  
            "lamat",       # Combination of syllables 2-3
            "sa",          # First syllable
            "salamat",     # Complete first word
            "salamat po",  # Full phrase
            "salamat po"   # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_kumusta_po_breakdown(self):
        """Test 'kumusta po' breakdown matches expected pattern."""
        phrase = "kumusta po"
        expected = [
            "kumusta po",  # Full phrase
            "po",          # Second word (single syllable)
            "ta",          # Last syllable of first word
            "mus",         # Previous syllable
            "musta",       # Combination of syllables 2-3
            "ku",          # First syllable
            "kumusta",     # Complete first word
            "kumusta po",  # Full phrase
            "kumusta po"   # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_magkano_po_breakdown(self):
        """Test 'magkano po' breakdown matches expected pattern."""
        phrase = "magkano po"
        expected = [
            "magkano po",  # Full phrase
            "po",          # Second word (single syllable)
            "no",          # Last syllable of first word
            "ka",          # Previous syllable
            "kano",        # Combination of syllables 2-3
            "mag",         # First syllable
            "magkano",     # Complete first word
            "magkano po",  # Full phrase
            "magkano po"   # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_puwede_po_ba_breakdown(self):
        """Test 'puwede po ba' breakdown matches expected pattern."""
        phrase = "puwede po ba"
        expected = [
            "puwede po ba",  # Full phrase
            "ba",            # Third word (single syllable)
            "po",            # Second word (single syllable)
            "po ba",         # Partial phrase from second word
            "de",            # Last syllable of first word
            "we",            # Previous syllable
            "wede",          # Combination of syllables 2-3
            "pu",            # First syllable
            "puwede",        # Complete first word
            "puwede po ba",  # Full phrase
            "puwede po ba"   # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_sarap_naman_breakdown(self):
        """Test 'sarap naman' breakdown matches expected pattern."""
        phrase = "sarap naman"
        expected = [
            "sarap naman",   # Full phrase
            "man",           # Last syllable of second word
            "na",            # Previous syllable of second word
            "naman",         # Complete second word
            "rap",           # Last syllable of first word
            "sa",            # First syllable of first word
            "sarap",         # Complete first word
            "sarap naman",   # Full phrase
            "sarap naman"    # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_nakakamangha_talaga_breakdown(self):
        """Test 'nakakamangha talaga' breakdown - KEY FAILING CASE."""
        phrase = "nakakamangha talaga"
        expected = [
            "nakakamangha talaga",  # Full phrase
            "ga",                   # Last syllable of second word
            "la",                   # Previous syllable of second word  
            "laga",                 # Combination of syllables 2-3
            "ta",                   # First syllable of second word
            "talaga",               # Complete second word
            "ha",                   # Last syllable of first word
            "mang",                 # Previous syllable
            "mangha",               # Combination
            "ka",                   # Previous syllable
            "kamangha",             # Combination
            "ka",                   # Previous syllable (repeated in pattern)
            "kakamangha",           # Combination
            "na",                   # First syllable
            "nakakamangha",         # Complete first word
            "nakakamangha talaga",  # Full phrase
            "nakakamangha talaga"   # Final repetition
        ]
        
        actual = generate_pimsleur_breakdown(phrase)
        assert actual == expected, f"Expected {expected}, got {actual}"


class TestSyllabificationForDay15Words:
    """Test syllabification of individual Day 15 words."""

    def test_salamat_syllabification(self):
        """Test that 'salamat' syllabifies correctly."""
        from utils.pimsleur_breakdown import syllabify_tagalog_word
        
        word = "salamat"
        expected = ["sa", "la", "mat"]
        actual = syllabify_tagalog_word(word)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_kumusta_syllabification(self):
        """Test that 'kumusta' syllabifies correctly."""
        from utils.pimsleur_breakdown import syllabify_tagalog_word
        
        word = "kumusta"
        expected = ["ku", "mus", "ta"]
        actual = syllabify_tagalog_word(word)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_magkano_syllabification(self):
        """Test that 'magkano' syllabifies correctly."""
        from utils.pimsleur_breakdown import syllabify_tagalog_word
        
        word = "magkano"
        expected = ["mag", "ka", "no"]
        actual = syllabify_tagalog_word(word)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_puwede_syllabification(self):
        """Test that 'puwede' syllabifies correctly."""
        from utils.pimsleur_breakdown import syllabify_tagalog_word
        
        word = "puwede"
        expected = ["pu", "we", "de"]
        actual = syllabify_tagalog_word(word)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_sarap_syllabification(self):
        """Test that 'sarap' syllabifies correctly - MISSING FROM DICTIONARY."""
        from utils.pimsleur_breakdown import syllabify_tagalog_word
        
        word = "sarap"
        expected = ["sa", "rap"]
        actual = syllabify_tagalog_word(word)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_naman_syllabification(self):
        """Test that 'naman' syllabifies correctly - MISSING FROM DICTIONARY."""
        from utils.pimsleur_breakdown import syllabify_tagalog_word
        
        word = "naman"
        expected = ["na", "man"]
        actual = syllabify_tagalog_word(word)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_nakakamangha_syllabification(self):
        """Test that 'nakakamangha' syllabifies correctly - KEY MISSING WORD."""
        from utils.pimsleur_breakdown import syllabify_tagalog_word
        
        word = "nakakamangha"
        expected = ["na", "ka", "ka", "mang", "ha"]
        actual = syllabify_tagalog_word(word)
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_talaga_syllabification(self):
        """Test that 'talaga' syllabifies correctly - MISSING FROM DICTIONARY."""
        from utils.pimsleur_breakdown import syllabify_tagalog_word
        
        word = "talaga"
        expected = ["ta", "la", "ga"]
        actual = syllabify_tagalog_word(word)
        assert actual == expected, f"Expected {expected}, got {actual}"


class TestCurrentFailuresVsExpected:
    """Compare current algorithm output with expected to isolate exact issues."""

    def test_current_vs_expected_breakdown_differences(self):
        """Run all Day 15 phrases and show current vs expected differences."""
        test_cases = [
            ("salamat po", ["salamat po", "po", "mat", "la", "lamat", "sa", "salamat", "salamat po", "salamat po"]),
            ("kumusta po", ["kumusta po", "po", "ta", "mus", "musta", "ku", "kumusta", "kumusta po", "kumusta po"]),
            ("magkano po", ["magkano po", "po", "no", "ka", "kano", "mag", "magkano", "magkano po", "magkano po"]),
            ("puwede po ba", ["puwede po ba", "ba", "po", "po ba", "de", "we", "wede", "pu", "puwede", "puwede po ba", "puwede po ba"]),
            ("sarap naman", ["sarap naman", "man", "na", "naman", "rap", "sa", "sarap", "sarap naman", "sarap naman"]),
            ("nakakamangha talaga", ["nakakamangha talaga", "ga", "la", "laga", "ta", "talaga", "ha", "mang", "mangha", "ka", "kamangha", "ka", "kakamangha", "na", "nakakamangha", "nakakamangha talaga", "nakakamangha talaga"])
        ]
        
        failures = []
        for phrase, expected in test_cases:
            actual = generate_pimsleur_breakdown(phrase)
            if actual != expected:
                failures.append({
                    'phrase': phrase,
                    'expected': expected,
                    'actual': actual,
                    'missing_steps': [step for step in expected if step not in actual],
                    'extra_steps': [step for step in actual if step not in expected]
                })
        
        # This test is designed to fail and show us exactly what needs to be fixed
        if failures:
            failure_report = "\n\nFAILURE REPORT:\n" + "="*50 + "\n"
            for failure in failures:
                failure_report += f"\nPhrase: '{failure['phrase']}'\n"
                failure_report += f"Expected ({len(failure['expected'])} steps): {failure['expected']}\n"
                failure_report += f"Actual ({len(failure['actual'])} steps):   {failure['actual']}\n"
                if failure['missing_steps']:
                    failure_report += f"Missing: {failure['missing_steps']}\n"
                if failure['extra_steps']:
                    failure_report += f"Extra:   {failure['extra_steps']}\n"
                failure_report += "-" * 40 + "\n"
            
            pytest.fail(f"Found {len(failures)} failing breakdown(s):{failure_report}")


if __name__ == "__main__":
    # Run the failure analysis
    test = TestCurrentFailuresVsExpected()
    test.test_current_vs_expected_breakdown_differences()