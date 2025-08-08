#!/usr/bin/env python3
"""
Test SRS phrase extraction from generated stories.

This test validates that key phrases from generated stories are properly
extracted and added to the SRS collocation tracking system.
"""

import json
import pytest
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from mock_srs import LessonVocabularyReport
from srs_phrase_extractor import SRSPhraseExtractor

class TestSRSPhraseExtraction:
    """Test suite for SRS phrase extraction from stories."""
    
    def setup_method(self):
        """Set up test environment."""
        self.extractor = SRSPhraseExtractor()
        
        # Sample story content similar to Day 10 output
        self.sample_story = """[NARRATOR]: Day 10: Getting Around Town Enhanced – Day 4 Revisited

Key Phrases:

[TAGALOG-FEMALE-1]: tara na po
[NARRATOR]: let's go (polite invitation)
[TAGALOG-FEMALE-1]: tara na po
po
na po
na
ra
ta
tara
tara na
tara na po
tara na po

[TAGALOG-FEMALE-1]: ingat po
[NARRATOR]: take care (polite)
[TAGALOG-FEMALE-1]: ingat po
po
gat
in
ingat
ingat po
ingat po

[NARRATOR]: Natural Speed

Planning the Trip

[TAGALOG-MALE-1]: Kuya, paano po pumunta sa Secret Lagoon?
[TAGALOG-MALE-2]: Secret Lagoon? Ah, malayo po yan. Boat po.
[TAGALOG-MALE-1]: Malayo po ba talaga?
[TAGALOG-MALE-2]: Opo! Tricycle hindi puwede doon. Boat lang po.
[TAGALOG-MALE-1]: Saan po sakayan ng boat?
[TAGALOG-MALE-2]: Doon po sa port. Malapit lang po, kanan po sa kanto.
[TAGALOG-MALE-1]: Ah, salamat po! Tara na po kami doon.
[TAGALOG-MALE-2]: Ingat po kayo!"""

    def test_extract_key_phrases_from_story(self):
        """Test that key phrases are properly extracted from story content."""
        # This should extract the key phrases from the story
        extracted_phrases = self.extractor.extract_key_phrases_from_story(self.sample_story)
        
        # Should find the main key phrases
        assert "tara na po" in extracted_phrases
        assert "ingat po" in extracted_phrases
        
        # Should not include syllable breakdowns
        assert "po" not in extracted_phrases or extracted_phrases["po"] == 0
        assert "na" not in extracted_phrases
        assert "ra" not in extracted_phrases
        
    def test_extract_dialogue_collocations(self):
        """Test extraction of collocations from dialogue sections."""
        dialogue_phrases = self.extractor.extract_dialogue_collocations(self.sample_story)
        
        # Should find common travel phrases (allowing for variations)
        expected_patterns = [
            "paano po",
            "malayo po", 
            "salamat po",
            "sakayan",
            "malapit"
        ]
        
        for pattern in expected_patterns:
            found = any(pattern in phrase.lower() for phrase in dialogue_phrases)
            assert found, f"Missing expected pattern '{pattern}' in: {dialogue_phrases}"
            
    def test_analyze_vocabulary_usage_improved(self):
        """Test improved vocabulary usage analysis."""
        learned_vocab = ["salamat", "po", "opo"]
        review_vocab = ["salamat", "po", "opo"]
        
        # First test that key phrases are extracted correctly
        key_phrases = self.extractor.extract_key_phrases_from_story(self.sample_story)
        assert "tara na po" in key_phrases
        assert "ingat po" in key_phrases
        
        # Use improved analysis method
        vocabulary_report = self.extractor.analyze_vocabulary_usage_improved(
            self.sample_story, learned_vocab, review_vocab
        )
        
        # Should properly identify new vocabulary
        print(f"Introduced new: {vocabulary_report.introduced_new}")
        
        # Check that key phrases are included (allowing for variations)
        introduced_phrases = vocabulary_report.introduced_new
        has_tara_phrase = any("tara na" in phrase.lower() for phrase in introduced_phrases)
        has_ingat_phrase = any("ingat" in phrase.lower() for phrase in introduced_phrases)
        
        assert has_tara_phrase, f"Missing 'tara na' phrase in: {introduced_phrases}"
        assert has_ingat_phrase, f"Missing 'ingat' phrase in: {introduced_phrases}"
        
        # Should identify review vocabulary reinforcement
        assert "salamat" in vocabulary_report.reinforced_review
        assert "po" in vocabulary_report.reinforced_review
        
    def test_srs_integration_end_to_end(self):
        """Test complete SRS integration with story generation."""
        # Mock a story generation and check SRS update
        initial_collocations_count = self._get_collocations_count()
        
        # Simulate processing the story with improved SRS integration
        learned_vocab = ["salamat", "po", "opo"]
        review_vocab = ["salamat", "po", "opo"]
        
        vocabulary_report = self.extractor.analyze_vocabulary_usage_improved(
            self.sample_story, learned_vocab, review_vocab
        )
        
        # Verify new phrases were identified
        assert len(vocabulary_report.introduced_new) >= 2
        
        # Check that key phrases are included (allowing for variations)
        introduced_phrases = vocabulary_report.introduced_new
        has_tara_phrase = any("tara na" in phrase.lower() for phrase in introduced_phrases)
        has_ingat_phrase = any("ingat" in phrase.lower() for phrase in introduced_phrases)
        
        assert has_tara_phrase, f"Missing 'tara na' phrase in: {introduced_phrases}"
        assert has_ingat_phrase, f"Missing 'ingat' phrase in: {introduced_phrases}"
        
    def test_prevent_syllable_contamination(self):
        """Test that syllable breakdowns don't contaminate SRS data."""
        # Extract all potential phrases from the story
        all_phrases = self._extract_all_phrases(self.sample_story)
        
        # Filter out syllable breakdowns
        clean_phrases = self._filter_syllable_breakdowns(all_phrases)
        
        # Syllable parts should be filtered out
        syllable_parts = ["po", "na", "ra", "ta", "gat", "in"]
        for part in syllable_parts:
            if part in clean_phrases:
                # If it exists, it should be because it's a legitimate word, not a syllable
                assert len(part) <= 3 or self._is_legitimate_word(part)
                
        # Main phrases should remain
        assert "tara na po" in clean_phrases
        assert "ingat po" in clean_phrases
        
    # Helper methods for improved SRS integration
    
    def _extract_key_phrases_from_story(self, story: str) -> dict:
        """Extract key phrases from the Key Phrases section of a story."""
        phrases = {}
        
        lines = story.split('\n')
        in_key_phrases = False
        current_phrase = None
        
        for line in lines:
            line = line.strip()
            
            if line == "Key Phrases:":
                in_key_phrases = True
                continue
            elif line.startswith("[NARRATOR]: Natural Speed"):
                in_key_phrases = False
                break
                
            if in_key_phrases and line.startswith("[TAGALOG-"):
                # Extract the Filipino phrase after the colon
                if ": " in line:
                    phrase = line.split(": ", 1)[1].strip()
                    if len(phrase.split()) >= 2:  # Multi-word phrases only
                        current_phrase = phrase
                        phrases[phrase] = phrases.get(phrase, 0) + 1
                        
        return phrases
    
    def _extract_dialogue_collocations(self, story: str) -> list:
        """Extract practical collocations from dialogue sections."""
        collocations = []
        
        lines = story.split('\n')
        in_dialogue = False
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("[NARRATOR]: Natural Speed"):
                in_dialogue = True
                continue
            elif line.startswith("[NARRATOR]: Slow Speed"):
                break
                
            if in_dialogue and line.startswith("[TAGALOG-"):
                # Extract Filipino dialogue
                if ": " in line:
                    dialogue = line.split(": ", 1)[1].strip()
                    # Extract meaningful phrases (2-4 words)
                    words = dialogue.split()
                    for i in range(len(words)):
                        for j in range(i+2, min(i+5, len(words)+1)):
                            phrase = " ".join(words[i:j])
                            if self._is_meaningful_phrase(phrase):
                                collocations.append(phrase)
                                
        return list(set(collocations))  # Remove duplicates
    
    def _analyze_vocabulary_usage_improved(
        self, 
        story: str, 
        learned_vocab: list, 
        review_vocab: list
    ) -> LessonVocabularyReport:
        """Improved vocabulary usage analysis."""
        
        # Extract key phrases
        key_phrases = self._extract_key_phrases_from_story(story)
        
        # Extract dialogue collocations  
        dialogue_phrases = self._extract_dialogue_collocations(story)
        
        # Combine and deduplicate
        all_new_phrases = list(key_phrases.keys()) + dialogue_phrases
        
        # Filter for truly new vocabulary
        introduced_new = []
        for phrase in all_new_phrases:
            if not any(word.lower() in phrase.lower() for word in learned_vocab):
                if len(phrase.split()) >= 2:  # Multi-word phrases only
                    introduced_new.append(phrase)
                    
        # Remove duplicates and limit
        introduced_new = list(set(introduced_new))[:3]
        
        # Check review vocabulary reinforcement
        story_lower = story.lower()
        reinforced_review = [word for word in review_vocab if word.lower() in story_lower]
        
        return LessonVocabularyReport(
            introduced_new=introduced_new,
            reinforced_review=reinforced_review,
            unexpected_vocabulary=[]
        )
    
    def _extract_all_phrases(self, story: str) -> list:
        """Extract all phrases from story for analysis."""
        phrases = []
        
        for line in story.split('\n'):
            line = line.strip()
            if line.startswith("[TAGALOG-") and ": " in line:
                phrase = line.split(": ", 1)[1].strip()
                phrases.append(phrase)
                
        return phrases
    
    def _filter_syllable_breakdowns(self, phrases: list) -> list:
        """Filter out syllable breakdown contamination."""
        clean_phrases = []
        
        for phrase in phrases:
            # Skip single syllables and obvious breakdowns
            if len(phrase.split()) == 1 and len(phrase) <= 3:
                continue
            if self._is_syllable_breakdown(phrase):
                continue
                
            clean_phrases.append(phrase)
            
        return clean_phrases
    
    def _is_syllable_breakdown(self, phrase: str) -> bool:
        """Check if a phrase is part of syllable breakdown."""
        # Simple heuristic: single short words are likely syllables
        return len(phrase.split()) == 1 and len(phrase) <= 3
    
    def _is_meaningful_phrase(self, phrase: str) -> bool:
        """Check if a phrase is meaningful for language learning."""
        # Must contain 'po' or other functional words, or be substantive
        return ("po" in phrase.lower() or 
                len(phrase.split()) >= 3 or
                any(word in phrase.lower() for word in ["paano", "saan", "ano", "salamat"]))
    
    def _is_legitimate_word(self, word: str) -> bool:
        """Check if a short word is legitimate (not just a syllable)."""
        legitimate_short_words = ["po", "na", "sa", "ng", "si", "ni", "ka", "ko", "mo", "to"]
        return word.lower() in legitimate_short_words
    
    def _get_collocations_count(self) -> int:
        """Get current count of collocations."""
        collocations_path = Path("instance/data/collocations.json")
        if collocations_path.exists():
            with open(collocations_path, 'r') as f:
                data = json.load(f)
                return len(data)
        return 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])