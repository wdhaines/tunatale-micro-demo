#!/usr/bin/env python3
"""
Improved SRS phrase extraction for Filipino language learning stories.

This module provides enhanced phrase extraction specifically designed for
TunaTale's story format, avoiding syllable contamination and properly
identifying key Filipino collocations.
"""

import re
from typing import List, Dict, Set
from mock_srs import LessonVocabularyReport


class SRSPhraseExtractor:
    """Enhanced phrase extractor for SRS integration."""
    
    def __init__(self):
        """Initialize the phrase extractor."""
        # Common Filipino function words that should be part of phrases
        self.function_words = {
            'po', 'opo', 'na', 'sa', 'ng', 'si', 'ni', 'ka', 'ko', 'mo', 
            'to', 'mga', 'ang', 'ay', 'ba', 'kaya', 'lang'
        }
        
        # Patterns to identify syllable breakdowns vs. real phrases
        self.syllable_patterns = [
            r'^[a-z]{1,3}$',  # Single short words (likely syllables)
            r'^[a-z]{1,2} [a-z]{1,2}$',  # Two short words (likely syllables)
        ]
        
    def extract_key_phrases_from_story(self, story: str) -> Dict[str, int]:
        """Extract key phrases from the Key Phrases section of a story."""
        phrases = {}
        
        lines = story.split('\n')
        in_key_phrases = False
        
        for line in lines:
            line = line.strip()
            
            # Start of Key Phrases section
            if line == "Key Phrases:":
                in_key_phrases = True
                continue
            # End of Key Phrases section
            elif line.startswith("[NARRATOR]: Natural Speed"):
                in_key_phrases = False
                break
                
            if in_key_phrases and line.startswith("[TAGALOG-"):
                # Extract the Filipino phrase after the colon
                if ": " in line:
                    phrase = line.split(": ", 1)[1].strip()
                    
                    # Only count multi-word phrases that aren't syllable breakdowns
                    if self._is_valid_phrase(phrase):
                        phrases[phrase] = phrases.get(phrase, 0) + 1
                        
        return phrases
    
    def extract_dialogue_collocations(self, story: str) -> List[str]:
        """Extract practical collocations from dialogue sections."""
        collocations = set()
        
        lines = story.split('\n')
        in_dialogue = False
        
        for line in lines:
            line = line.strip()
            
            # Start of dialogue sections
            if line.startswith("[NARRATOR]: Natural Speed"):
                in_dialogue = True
                continue
            # End of dialogue sections  
            elif line.startswith("[NARRATOR]: Slow Speed"):
                break
                
            if in_dialogue and line.startswith("[TAGALOG-"):
                # Extract Filipino dialogue
                if ": " in line:
                    dialogue = line.split(": ", 1)[1].strip()
                    
                    # Extract meaningful phrases from dialogue
                    extracted_phrases = self._extract_phrases_from_dialogue(dialogue)
                    collocations.update(extracted_phrases)
                    
        return list(collocations)
    
    def analyze_vocabulary_usage_improved(
        self, 
        story: str, 
        learned_vocab: List[str], 
        review_vocab: List[str]
    ) -> LessonVocabularyReport:
        """Improved vocabulary usage analysis that properly extracts phrases."""
        
        # Extract key phrases from the structured section
        key_phrases = self.extract_key_phrases_from_story(story)
        
        # Extract dialogue collocations
        dialogue_phrases = self.extract_dialogue_collocations(story)
        
        # Prioritize key phrases from the structured section
        key_phrase_list = list(key_phrases.keys())
        dialogue_phrase_list = dialogue_phrases
        
        # Filter for truly new vocabulary  
        introduced_new = []
        learned_lower = [word.lower() for word in learned_vocab]
        
        # First, add key phrases (these are the most important)
        for phrase in key_phrase_list:
            phrase_lower = phrase.lower()
            
            # Skip if the entire phrase is already in learned vocabulary
            if phrase_lower in learned_lower:
                continue
            
            # For key phrases, be more lenient - they're explicitly taught
            if self._is_meaningful_phrase(phrase):
                introduced_new.append(phrase)
        
        # Then add dialogue phrases if we have room and they're truly new
        for phrase in dialogue_phrase_list:
            if len(introduced_new) >= 3:  # Limit total phrases
                break
                
            phrase_lower = phrase.lower()
            
            # Skip if already in learned vocab or already added
            if phrase_lower in learned_lower or phrase in introduced_new:
                continue
            
            # For dialogue phrases, require new content words
            phrase_words = phrase_lower.split()
            content_words = [w for w in phrase_words if w not in self.function_words]
            
            has_new_content = any(word not in learned_lower for word in content_words)
            
            if has_new_content and self._is_meaningful_phrase(phrase):
                introduced_new.append(phrase)
                    
        # Remove duplicates and limit to reasonable number
        introduced_new = list(set(introduced_new))[:3]
        
        # Check review vocabulary reinforcement
        story_lower = story.lower()
        reinforced_review = []
        for word in review_vocab:
            if word.lower() in story_lower:
                reinforced_review.append(word)
        
        return LessonVocabularyReport(
            introduced_new=introduced_new,
            reinforced_review=reinforced_review,
            unexpected_vocabulary=[]
        )
    
    def _is_valid_phrase(self, phrase: str) -> bool:
        """Check if a phrase is valid (not a syllable breakdown)."""
        # Must be multi-word
        words = phrase.split()
        if len(words) < 2:
            return False
            
        # Skip obvious syllable breakdowns
        if self._is_syllable_breakdown(phrase):
            return False
            
        return True
    
    def _is_syllable_breakdown(self, phrase: str) -> bool:
        """Check if a phrase is part of syllable breakdown."""
        phrase_lower = phrase.lower()
        
        # Check against syllable patterns
        for pattern in self.syllable_patterns:
            if re.match(pattern, phrase_lower):
                return True
                
        # If it's just repetitive single syllables, it's a breakdown
        words = phrase_lower.split()
        if len(words) <= 3 and all(len(word) <= 3 for word in words):
            # Check if it's repetitive (like "po na po")
            unique_words = set(words)
            if len(unique_words) <= 2:
                return True
                
        return False
    
    def _extract_phrases_from_dialogue(self, dialogue: str) -> List[str]:
        """Extract meaningful phrases from a dialogue line."""
        phrases = []
        words = dialogue.split()
        
        # Extract 2-4 word phrases that contain function words
        for i in range(len(words)):
            for length in range(2, 5):  # 2-4 word phrases
                if i + length <= len(words):
                    phrase = " ".join(words[i:i + length])
                    
                    if self._is_meaningful_phrase(phrase):
                        phrases.append(phrase)
                        
        return phrases
    
    def _is_meaningful_phrase(self, phrase: str) -> bool:
        """Check if a phrase is meaningful for language learning."""
        phrase_lower = phrase.lower()
        words = phrase_lower.split()
        
        # Must be at least 2 words
        if len(words) < 2:
            return False
            
        # Skip if it's likely a syllable breakdown
        if self._is_syllable_breakdown(phrase):
            return False
            
        # Should contain functional words or be substantive
        has_function_word = any(word in self.function_words for word in words)
        has_question_word = any(word in ['paano', 'saan', 'ano', 'kailan', 'bakit'] 
                              for word in words)
        has_polite_marker = 'po' in words or 'opo' in words
        is_greeting = any(word in ['salamat', 'kumusta', 'magandang'] for word in words)
        
        return (has_function_word or has_question_word or 
                has_polite_marker or is_greeting or len(words) >= 3)


# Integration function for story_generator.py
def create_improved_srs_extractor():
    """Factory function to create an improved SRS phrase extractor."""
    return SRSPhraseExtractor()