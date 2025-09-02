"""
Language detection and classification for Filipino/English vocabulary.

Uses existing dictionary loading functions for consistency with SRS enforcement.
"""
import logging
from typing import Set
from utils.pimsleur_breakdown import _load_tagalog_dictionary, _load_english_dictionary, is_english_loanword


class LanguageDetector:
    """Detects and classifies words as English, Tagalog, loan words, or unknown."""
    
    def __init__(self):
        """Initialize with dictionaries."""
        self.tagalog_words = _load_tagalog_dictionary()
        self.english_words = _load_english_dictionary()
        
        # Common Filipino particles that indicate Filipino context
        self.filipino_particles = {
            'po', 'ba', 'na', 'ng', 'sa', 'ay', 'ang', 'mga', 
            'naman', 'din', 'rin', 'lang', 'lamang', 'pala',
            'kasi', 'eh', 'ah', 'oh', 'uy', 'hey'
        }
        
        # Log dictionary loading status
        logging.info(f"LanguageDetector initialized - Tagalog: {len(self.tagalog_words)} words, English: {len(self.english_words)} words")
    
    def is_english_word(self, word: str) -> bool:
        """Check if word is in English dictionary."""
        return word.lower().strip() in self.english_words
    
    def is_tagalog_word(self, word: str) -> bool:
        """Check if word is in Tagalog dictionary."""
        return word.lower().strip() in self.tagalog_words
    
    def is_filipino_particle(self, word: str) -> bool:
        """Check if word is a Filipino particle."""
        return word.lower().strip() in self.filipino_particles
    
    def classify_word(self, word: str) -> str:
        """
        Classify a single word.
        
        Returns:
            'english': Pure English word
            'tagalog': Pure Tagalog word  
            'loan': English loanword used in Filipino
            'unknown': Not found in either dictionary
        """
        word_clean = word.lower().strip()
        
        # Check if it's a Filipino particle first
        if self.is_filipino_particle(word_clean):
            return 'tagalog'
        
        is_eng = self.is_english_word(word_clean)
        is_tag = self.is_tagalog_word(word_clean)
        
        if is_tag and is_eng:
            # Word exists in both dictionaries
            if is_english_loanword(word_clean):
                return 'loan'  # English loanword commonly used in Filipino
            else:
                return 'tagalog'  # Prioritize Tagalog classification
        elif is_tag:
            return 'tagalog'
        elif is_eng:
            if is_english_loanword(word_clean):
                return 'loan'  # English word that's commonly borrowed
            else:
                return 'english'  # Pure English
        else:
            return 'unknown'
    
    def has_filipino_context(self, phrase: str) -> bool:
        """
        Check if a phrase has Filipino linguistic context.
        
        Returns True if the phrase contains Filipino particles or markers
        that indicate it's being used in a Filipino context.
        """
        words = phrase.lower().split()
        
        # Check for Filipino particles
        if any(self.is_filipino_particle(word) for word in words):
            return True
        
        # Check for Filipino words
        if any(self.is_tagalog_word(word) for word in words):
            return True
            
        return False
    
    def should_keep_for_filipino_learning(self, phrase: str) -> bool:
        """
        Determine if a phrase should be kept for Filipino language learning.
        
        Filtering rules:
        1. Keep pure Filipino phrases
        2. Keep mixed phrases with Filipino context (particles, etc.)
        3. Keep loan words in Filipino context
        4. Filter pure English phrases unless in Filipino context
        """
        words = phrase.split()
        
        # Single word handling
        if len(words) == 1:
            classification = self.classify_word(words[0])
            if classification == 'tagalog':
                return True  # Keep Filipino words
            elif classification == 'unknown':
                # Be more selective with unknown words - check if they look English
                if self._looks_like_english(words[0]):
                    return False
                return True  # Keep unknown words that don't look English
            elif classification == 'loan':
                return False  # Filter standalone loan words
            else:  # english
                return False  # Filter standalone English words
        
        # Multi-word phrase handling
        has_filipino_context = self.has_filipino_context(phrase)
        
        if has_filipino_context:
            return True  # Keep phrases with Filipino context
        
        # Check if it's a pure English phrase
        word_classifications = [self.classify_word(word) for word in words]
        english_count = sum(1 for c in word_classifications if c in ['english', 'loan'])
        filipino_count = sum(1 for c in word_classifications if c in ['tagalog', 'unknown'])
        
        # If mostly English without Filipino context, filter it
        if english_count > filipino_count and english_count > len(words) * 0.6:
            return False
        
        return True  # Default to keeping
    
    def _looks_like_english(self, word: str) -> bool:
        """
        Check if an unknown word looks like English based on patterns.
        
        This helps filter English words that aren't in the system dictionary
        (like plurals, compound words, etc.)
        """
        word_lower = word.lower()
        
        # Common English suffixes
        english_suffixes = [
            's', 'es', 'ed', 'ing', 'er', 'est', 'ly', 'tion', 'sion', 
            'ness', 'ment', 'ful', 'less', 'able', 'ible', 'ous', 'eous'
        ]
        
        # Check for English suffixes
        for suffix in english_suffixes:
            if word_lower.endswith(suffix):
                # Remove suffix and check if root looks English
                root = word_lower[:-len(suffix)]
                if len(root) > 2:  # Reasonable root length
                    # Check if root is in English dictionary
                    if root in self.english_words:
                        return True
                    # Check for double letter before suffix (running -> run)
                    if len(root) > 3 and root[-1] == root[-2]:
                        single_root = root[:-1]
                        if single_root in self.english_words:
                            return True
        
        # Check for compound words with common English components
        english_components = [
            'photo', 'key', 'chain', 'shirt', 'post', 'card', 'sun', 'set',
            'time', 'view', 'point', 'refresh', 'ment', 'stand'
        ]
        
        for component in english_components:
            if component in word_lower:
                return True
        
        # Check if it contains typical English letter patterns
        # English often has: th, ch, sh, ph, gh
        english_patterns = ['th', 'ch', 'sh', 'ph', 'gh', 'ck', 'qu']
        if any(pattern in word_lower for pattern in english_patterns):
            # Additional check - if it also contains Filipino patterns, keep it
            filipino_patterns = ['ng', 'ny', 'ts']  # Common in Filipino
            if not any(pattern in word_lower for pattern in filipino_patterns):
                return True
        
        return False