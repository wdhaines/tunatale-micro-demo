"""Integration tests for post-processing functionality with corrected Pimsleur breakdown."""

import pytest
from utils.content_post_processor import post_process_story_content, fix_pimsleur_breakdowns, extract_key_phrases_sections
from utils.pimsleur_breakdown import generate_pimsleur_breakdown


class TestPostProcessingIntegration:
    """Test post-processing integration with real Pimsleur breakdown correction."""
    
    def test_post_process_with_incorrect_breakdown(self):
        """Test post-processing corrects incorrect Pimsleur breakdown."""
        # Sample content with incorrect breakdown (like what LLM generates)
        content_with_incorrect_breakdown = """[NARRATOR]: Day 14: Shopping Test
        
Key Phrases:

[TAGALOG-FEMALE-1]: salamat po
[NARRATOR]: thank you (formal)
[TAGALOG-FEMALE-1]: salamat po
po
lam po
sa
salamat
salamat po
salamat po

[NARRATOR]: Natural Speed

[NARRATOR]: At the shop"""

        # Process the content
        corrected_content = post_process_story_content(content_with_incorrect_breakdown)
        
        # Verify the breakdown was corrected
        assert corrected_content != content_with_incorrect_breakdown
        
        # Should contain the correct Pimsleur breakdown steps
        expected_steps = generate_pimsleur_breakdown("salamat po")
        for step in expected_steps:
            assert step in corrected_content
        
        # Should NOT contain the incorrect steps
        incorrect_steps = ["lam po", "sa"]  # These are wrong
        for bad_step in incorrect_steps:
            assert bad_step not in corrected_content or corrected_content.count(bad_step) < content_with_incorrect_breakdown.count(bad_step)

    def test_post_process_complex_phrase(self):
        """Test post-processing with a more complex phrase."""
        content = """[NARRATOR]: Day 15: Complex Test
        
Key Phrases:

[TAGALOG-MALE-1]: meron po ba kayo
[NARRATOR]: do you have
[TAGALOG-MALE-1]: meron po ba kayo
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

        # Process the content
        corrected_content = post_process_story_content(content)
        
        # Verify correct breakdown was applied
        expected_steps = generate_pimsleur_breakdown("meron po ba kayo")
        for step in expected_steps:
            assert step in corrected_content
        
        # Should preserve the structure
        assert "[NARRATOR]: do you have" in corrected_content
        assert "[NARRATOR]: Natural Speed" in corrected_content

    def test_post_process_multiple_phrases(self):
        """Test post-processing with multiple phrases in Key Phrases section."""
        content = """[NARRATOR]: Day 16: Multiple Phrases Test
        
Key Phrases:

[TAGALOG-FEMALE-1]: salamat po
[NARRATOR]: thank you (formal)
[TAGALOG-FEMALE-1]: salamat po
po
wrong breakdown
sa
salamat

[TAGALOG-MALE-1]: kumusta po
[NARRATOR]: how are you (formal)
[TAGALOG-MALE-1]: kumusta po
po
usta po
kum
wrong steps

[NARRATOR]: Natural Speed"""

        # Process the content  
        corrected_content = post_process_story_content(content)
        
        # Check both phrases were corrected
        salamat_steps = generate_pimsleur_breakdown("salamat po")
        kumusta_steps = generate_pimsleur_breakdown("kumusta po")
        
        for step in salamat_steps:
            assert step in corrected_content
            
        for step in kumusta_steps:
            assert step in corrected_content
        
        # Should preserve translations
        assert "[NARRATOR]: thank you (formal)" in corrected_content
        assert "[NARRATOR]: how are you (formal)" in corrected_content

    def test_extract_key_phrases_sections(self):
        """Test the phrase extraction functionality."""
        content = """[NARRATOR]: Day Test
        
Key Phrases:

[TAGALOG-FEMALE-1]: test phrase
[NARRATOR]: test translation  
[TAGALOG-FEMALE-1]: test phrase
bad1
bad2
bad3

[TAGALOG-MALE-1]: second phrase
[NARRATOR]: second translation
[TAGALOG-MALE-1]: second phrase
wrong1
wrong2

[NARRATOR]: Natural Speed"""

        phrases = extract_key_phrases_sections(content)
        
        # Should extract both phrases
        assert len(phrases) == 2
        
        phrase1, start1, end1, breakdown1 = phrases[0]
        assert phrase1 == "test phrase"
        assert breakdown1 == ["bad1", "bad2", "bad3"]
        
        phrase2, start2, end2, breakdown2 = phrases[1] 
        assert phrase2 == "second phrase"
        assert breakdown2 == ["wrong1", "wrong2"]

    def test_fix_pimsleur_breakdowns_preserves_structure(self):
        """Test that breakdown fixing preserves the overall story structure."""
        content = """[NARRATOR]: Day 17: Structure Test

Key Phrases:

[TAGALOG-FEMALE-1]: salamat po
[NARRATOR]: thank you
[TAGALOG-FEMALE-1]: salamat po
wrong
steps
here

[NARRATOR]: Natural Speed

[NARRATOR]: At the beach

[TAGALOG-FEMALE-1]: Salamat po sa beautiful sunset!

[NARRATOR]: Slow Speed

[TAGALOG-FEMALE-1]: Sa-la-mat po sa beau-ti-ful sun-set!"""

        corrected = fix_pimsleur_breakdowns(content)
        
        # Should preserve all non-breakdown content
        assert "[NARRATOR]: Day 17: Structure Test" in corrected
        assert "[NARRATOR]: thank you" in corrected
        assert "[NARRATOR]: Natural Speed" in corrected
        assert "[NARRATOR]: At the beach" in corrected
        assert "[NARRATOR]: Slow Speed" in corrected
        assert "[TAGALOG-FEMALE-1]: Salamat po sa beautiful sunset!" in corrected
        assert "[TAGALOG-FEMALE-1]: Sa-la-mat po sa beau-ti-ful sun-set!" in corrected
        
        # Should have correct breakdown
        correct_steps = generate_pimsleur_breakdown("salamat po")
        for step in correct_steps:
            assert step in corrected

    def test_post_process_handles_empty_content(self):
        """Test that post-processing handles edge cases gracefully."""
        # Empty content
        assert post_process_story_content("") == ""
        
        # None content  
        assert post_process_story_content(None) == None
        
        # Content without Key Phrases section
        no_key_phrases = """[NARRATOR]: Just a story
        
[NARRATOR]: Natural Speed

[NARRATOR]: Some dialogue here"""
        
        result = post_process_story_content(no_key_phrases)
        assert result == no_key_phrases  # Should be unchanged

    def test_post_process_handles_malformed_content(self):
        """Test handling of malformed Key Phrases sections."""
        malformed_content = """[NARRATOR]: Malformed Test
        
Key Phrases:

[TAGALOG-FEMALE-1]: good phrase
Missing narrator line
[TAGALOG-FEMALE-1]: good phrase
some
breakdown
lines

[NARRATOR]: Natural Speed"""

        # Should not crash and should attempt to process what it can
        result = post_process_story_content(malformed_content)
        assert result is not None
        assert "[NARRATOR]: Natural Speed" in result

    def test_integration_with_actual_day15_content(self):
        """Test with content that matches Day 15 structure."""
        day15_style_content = """[NARRATOR]: Day 15: Sunset viewing and photography at scenic spots

Key Phrases:

[TAGALOG-FEMALE-1]: salamat po
[NARRATOR]: thank you (formal)
[TAGALOG-FEMALE-1]: salamat po
[TAGALOG-FEMALE-1]: sa-la-mat po
[TAGALOG-FEMALE-1]: sa-la-mat
[TAGALOG-FEMALE-1]: sa-la
[TAGALOG-FEMALE-1]: sa

[TAGALOG-MALE-1]: kumusta po
[NARRATOR]: how are you (formal)
[TAGALOG-MALE-1]: kumusta po
[TAGALOG-MALE-1]: ku-mus-ta po
[TAGALOG-MALE-1]: ku-mus-ta
[TAGALOG-MALE-1]: ku-mus
[TAGALOG-MALE-1]: ku

[NARRATOR]: Natural Speed

[NARRATOR]: Late afternoon at the resort reception"""

        corrected = post_process_story_content(day15_style_content)
        
        # Should have correct breakdowns for both phrases
        salamat_correct = generate_pimsleur_breakdown("salamat po")
        kumusta_correct = generate_pimsleur_breakdown("kumusta po")
        
        for step in salamat_correct:
            assert step in corrected
            
        for step in kumusta_correct:
            assert step in corrected
        
        # Should preserve story structure
        assert "[NARRATOR]: Day 15: Sunset viewing" in corrected
        assert "[NARRATOR]: Natural Speed" in corrected
        assert "[NARRATOR]: Late afternoon at the resort reception" in corrected
        
        # Should NOT have the incorrect syllabic breakdowns
        incorrect_syllables = ["sa-la-mat", "sa-la", "ku-mus-ta", "ku-mus"]
        for incorrect in incorrect_syllables:
            # These might still appear in the Natural Speed section, but not as breakdown steps
            assert corrected.count(incorrect) <= day15_style_content.count(incorrect)


class TestPostProcessingErrorHandling:
    """Test error handling in post-processing."""
    
    def test_post_processing_error_recovery(self):
        """Test that errors in post-processing don't crash the system."""
        # Content that might cause regex issues
        problematic_content = """[NARRATOR]: Problem Test
        
Key Phrases:

[TAGALOG-FEMALE-1]: phrase with [brackets] and (parens)
[NARRATOR]: translation
[TAGALOG-FEMALE-1]: phrase with [brackets] and (parens)
some
breakdown

[NARRATOR]: Natural Speed"""

        # Should not crash
        result = post_process_story_content(problematic_content)
        assert result is not None
        
        # In case of any processing error, should return original content
        # or attempt partial processing
        assert "[NARRATOR]: Natural Speed" in result

    def test_breakdown_generation_fallback(self):
        """Test fallback behavior when breakdown generation fails."""
        # Test with a phrase that might cause issues
        unusual_phrase = "test phrase with $pecial char$"
        
        content = f"""Key Phrases:

[TAGALOG-FEMALE-1]: {unusual_phrase}
[NARRATOR]: test translation
[TAGALOG-FEMALE-1]: {unusual_phrase}
bad
breakdown

[NARRATOR]: Natural Speed"""

        # Should handle gracefully  
        result = post_process_story_content(content)
        assert result is not None
        assert "[NARRATOR]: Natural Speed" in result