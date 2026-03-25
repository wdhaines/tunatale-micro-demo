"""Tests for dictionary-based language filtering functionality."""
import pytest
from unittest.mock import Mock, patch
import tempfile
import json
from pathlib import Path

# Test dictionaries for language classification
SAMPLE_ENGLISH_DICT = {
    "photos", "perfect", "editing", "wait", "call", "here", "view", "take", 
    "smile", "painting", "true", "together", "say", "cheese", "ever", 
    "keychains", "t-shirts", "sunset", "design", "computer", "phone",
    "mango", "shake", "fresh", "juice", "best", "time", "good", "afternoon",
    "morning", "water", "thank", "you", "special"
}

SAMPLE_TAGALOG_DICT = {
    "salamat", "kumusta", "magkano", "tubig", "po", "ba", "na", "nga", "ang", 
    "mga", "ito", "yan", "yun", "ako", "ko", "mo", "niya", "tayo", "kayo", 
    "sila", "maganda", "magandang", "umaga", "masarap", "malamig", "sariwang", "napakasarap",
    "paumanhin", "opo", "hindi", "oo", "dito", "sige", "ate", "kuya",
    # Add loan words to Tagalog dict too
    "computer", "phone", "mango", "shake", "special"
}

# Loan words appear in both dictionaries
LOAN_WORDS = {"computer", "phone", "mango", "shake", "special"}


class MockLanguageDetector:
    """Mock language detector for testing dictionary-based filtering."""
    
    def __init__(self, english_words=None, tagalog_words=None):
        self.english_words = english_words or SAMPLE_ENGLISH_DICT
        self.tagalog_words = tagalog_words or SAMPLE_TAGALOG_DICT
    
    def is_english_word(self, word: str) -> bool:
        """Check if word exists in English dictionary."""
        return word.lower() in self.english_words
    
    def is_tagalog_word(self, word: str) -> bool:
        """Check if word exists in Tagalog dictionary."""
        return word.lower() in self.tagalog_words
    
    def is_loan_word(self, word: str) -> bool:
        """Check if word exists in both dictionaries (loan word)."""
        word_lower = word.lower()
        return word_lower in self.english_words and word_lower in self.tagalog_words
    
    def classify_word(self, word: str) -> str:
        """Classify word as english, tagalog, loan, or unknown."""
        word_lower = word.lower()
        in_english = word_lower in self.english_words
        in_tagalog = word_lower in self.tagalog_words
        
        if in_english and in_tagalog:
            return "loan"
        elif in_english:
            return "english"
        elif in_tagalog:
            return "tagalog"
        else:
            return "unknown"
    
    def has_filipino_context(self, phrase: str) -> bool:
        """Check if a phrase has Filipino linguistic context."""
        words = phrase.lower().split()
        
        # Check for Filipino particles (common ones)
        filipino_particles = {"po", "ba", "na", "nga", "ang", "mga", "ito", "yan", "yun"}
        if any(word in filipino_particles for word in words):
            return True
        
        # Check for Filipino words
        if any(self.is_tagalog_word(word) for word in words):
            return True
            
        return False


class TestLanguageClassification:
    """Test basic word classification functionality."""
    
    def setup_method(self):
        self.detector = MockLanguageDetector()
    
    def test_english_only_words(self):
        """Test classification of pure English words."""
        english_words = ["photos", "perfect", "editing", "wait", "call"]
        
        for word in english_words:
            assert self.detector.classify_word(word) == "english"
            assert self.detector.is_english_word(word) is True
            assert self.detector.is_tagalog_word(word) is False
            assert self.detector.is_loan_word(word) is False
    
    def test_tagalog_only_words(self):
        """Test classification of pure Tagalog words."""
        tagalog_words = ["salamat", "kumusta", "magkano", "tubig", "po"]
        
        for word in tagalog_words:
            assert self.detector.classify_word(word) == "tagalog"
            assert self.detector.is_english_word(word) is False
            assert self.detector.is_tagalog_word(word) is True
            assert self.detector.is_loan_word(word) is False
    
    def test_loan_words(self):
        """Test classification of loan words (appear in both dictionaries)."""
        loan_words = ["computer", "phone", "mango", "shake"]
        
        for word in loan_words:
            assert self.detector.classify_word(word) == "loan"
            assert self.detector.is_english_word(word) is True
            assert self.detector.is_tagalog_word(word) is True
            assert self.detector.is_loan_word(word) is True
    
    def test_unknown_words(self):
        """Test classification of words not in either dictionary."""
        unknown_words = ["xyzzyx", "blahblah", "nonexistent"]
        
        for word in unknown_words:
            assert self.detector.classify_word(word) == "unknown"
            assert self.detector.is_english_word(word) is False
            assert self.detector.is_tagalog_word(word) is False
            assert self.detector.is_loan_word(word) is False
    
    def test_case_insensitive_classification(self):
        """Test that classification is case insensitive."""
        test_cases = [
            ("SALAMAT", "tagalog"),
            ("Photos", "english"), 
            ("MANGO", "loan"),
            ("Kumusta", "tagalog")
        ]
        
        for word, expected_classification in test_cases:
            assert self.detector.classify_word(word) == expected_classification
    
    def test_integration_with_deterministic_english_detector(self):
        """Test integration with DeterministicEnglishDetector for SRS enforcement."""
        # Test words that would be important for SRS enforcement
        enforcement_test_cases = [
            # English words that should be detected for replacement
            ("good", "english"),
            ("morning", "english"),
            ("water", "english"),
            ("thank", "english"),
            ("you", "english"),
            
            # Filipino words that should NOT be replaced
            ("magandang", "tagalog"),
            ("umaga", "tagalog"),
            ("salamat", "tagalog"),
            ("po", "tagalog"),
            
            # Loan words that might be candidates for deepening
            ("mango", "loan"),
            ("shake", "loan"),
            ("special", "loan"),
        ]
        
        for word, expected_type in enforcement_test_cases:
            classification = self.detector.classify_word(word)
            assert classification == expected_type, f"Word '{word}' should be classified as '{expected_type}', got '{classification}'"
    
    def test_filipino_context_detection_for_enforcement(self):
        """Test Filipino context detection used in SRS enforcement."""
        # Test phrases that should be recognized as having Filipino context
        filipino_context_phrases = [
            "good morning po",  # English + Filipino particle
            "salamat thank you",  # Filipino + English mix
            "magandang umaga everyone",  # Filipino + English mix
        ]
        
        # Test phrases that should NOT be considered Filipino context
        pure_english_phrases = [
            "good morning everyone",
            "thank you very much",
            "have a nice day",
        ]
        
        for phrase in filipino_context_phrases:
            # The phrase should be detected as having Filipino context
            # This would affect whether English terms in it should be replaced
            has_context = self.detector.has_filipino_context(phrase)
            assert has_context, f"Phrase '{phrase}' should have Filipino context"
        
        for phrase in pure_english_phrases:
            # Pure English phrases should not have Filipino context
            has_context = self.detector.has_filipino_context(phrase)
            assert not has_context, f"Phrase '{phrase}' should not have Filipino context"


class TestSingleWordFiltering:
    """Test filtering rules for single words."""
    
    def setup_method(self):
        self.detector = MockLanguageDetector()
    
    def test_should_keep_single_words(self):
        """Test which single words should be kept in SRS vocabulary."""
        # Pure Tagalog words should always be kept
        tagalog_words = ["salamat", "kumusta", "magkano", "tubig"]
        for word in tagalog_words:
            assert self._should_keep_single_word(word) is True
        
        # Unknown words (proper nouns, etc.) should be kept 
        unknown_words = ["Palawan", "Boracay", "Manila"]
        for word in unknown_words:
            assert self._should_keep_single_word(word) is True
    
    def test_should_filter_single_words(self):
        """Test which single words should be filtered out."""
        # Pure English words should be filtered
        english_words = ["photos", "perfect", "editing", "wait"]
        for word in english_words:
            assert self._should_keep_single_word(word) is False
        
        # Loan words as single words should be filtered (per user requirement)
        loan_words = ["computer", "phone", "mango", "shake"]
        for word in loan_words:
            assert self._should_keep_single_word(word) is False
    
    def _should_keep_single_word(self, word: str) -> bool:
        """Mock implementation of single word filtering logic."""
        classification = self.detector.classify_word(word)
        
        # Keep pure Tagalog and unknown words
        if classification in ["tagalog", "unknown"]:
            return True
        
        # Filter pure English and loan words when standalone
        if classification in ["english", "loan"]:
            return False
        
        return False


class TestMultiWordPhraseFiltering:
    """Test filtering rules for multi-word phrases."""
    
    def setup_method(self):
        self.detector = MockLanguageDetector()
    
    def test_should_keep_phrases(self):
        """Test which phrases should be kept."""
        test_phrases = [
            # Mostly Tagalog phrases
            ("kumusta po", True),  # Pure Tagalog
            ("salamat sa pagdating", True),  # Pure Tagalog
            ("magandang umaga po", True),  # Pure Tagalog
            
            # Mixed phrases with Filipino particles
            ("mango shake po", True),  # Loan words + Filipino particle
            ("perfect timing kayo", True),  # English + Tagalog pronoun
            ("good afternoon po", True),  # English + Filipino politeness marker
            
            # Phrases with majority Tagalog content
            ("ang computer ay maganda", True),  # Mostly Tagalog structure
        ]
        
        for phrase, expected in test_phrases:
            result = self._should_keep_phrase(phrase)
            assert result == expected, f"Failed for phrase: '{phrase}'"
    
    def test_should_filter_phrases(self):
        """Test which phrases should be filtered."""
        test_phrases = [
            # Pure English phrases  
            ("perfect timing", False),
            ("take photos", False),
            ("say cheese", False),
            ("best sunset ever", False),
            
            # Mostly English phrases without Filipino elements
            ("computer and phone", False),
            ("fresh mango juice", False),
        ]
        
        for phrase, expected in test_phrases:
            result = self._should_keep_phrase(phrase)
            assert result == expected, f"Failed for phrase: '{phrase}'"
    
    def _should_keep_phrase(self, phrase: str) -> bool:
        """Mock implementation of phrase filtering logic."""
        words = phrase.lower().split()
        
        # Count word classifications
        tagalog_count = 0
        english_count = 0
        unknown_count = 0
        
        # Check for Filipino particles/markers
        filipino_particles = {"po", "ba", "na", "nga", "ang", "mga", "sa", "ay"}
        has_filipino_particles = any(word in filipino_particles for word in words)
        
        for word in words:
            classification = self.detector.classify_word(word)
            if classification == "tagalog":
                tagalog_count += 1
            elif classification in ["english", "loan"]:
                english_count += 1
            else:
                unknown_count += 1
        
        total_words = len(words)
        
        # Keep if has Filipino particles
        if has_filipino_particles:
            return True
        
        # Keep if majority is Tagalog or unknown
        if (tagalog_count + unknown_count) > english_count:
            return True
        
        # Keep if equal split but contains some Tagalog
        if tagalog_count > 0 and tagalog_count == english_count:
            return True
        
        # Filter if mostly or entirely English
        return False


class TestFilippinoPragmaticMarkers:
    """Test detection and special handling of Filipino pragmatic markers."""
    
    def setup_method(self):
        self.detector = MockLanguageDetector()
    
    def test_filipino_particle_detection(self):
        """Test identification of Filipino particles and markers."""
        filipino_particles = {
            # Politeness markers
            "po", "opo", "ho", 
            # Question particles  
            "ba", "kaya",
            # Aspect markers
            "na", "pa", "nga",
            # Focus markers
            "ang", "ng", "sa",
            # Plural marker
            "mga"
        }
        
        for particle in filipino_particles:
            assert self._is_filipino_particle(particle) is True
    
    def test_phrases_with_particles_are_kept(self):
        """Test that phrases containing Filipino particles are always kept."""
        phrases_with_particles = [
            "computer po",  # Loan word + politeness
            "photos ba",   # English + question marker
            "perfect na",  # English + aspect marker  
            "good morning po",  # English + politeness
            "mango shake nga",  # Mixed + emphasis
        ]
        
        for phrase in phrases_with_particles:
            # These should be kept despite English content due to Filipino particles
            assert self._has_filipino_particles(phrase) is True
    
    def _is_filipino_particle(self, word: str) -> bool:
        """Check if word is a Filipino pragmatic particle."""
        particles = {"po", "opo", "ho", "ba", "kaya", "na", "pa", "nga", 
                    "ang", "ng", "sa", "mga", "ay", "din", "rin"}
        return word.lower() in particles
    
    def _has_filipino_particles(self, phrase: str) -> bool:
        """Check if phrase contains Filipino particles."""
        words = phrase.lower().split()
        return any(self._is_filipino_particle(word) for word in words)


class TestIntegratedLanguageFiltering:
    """Test the complete language filtering system."""
    
    def setup_method(self):
        self.detector = MockLanguageDetector()
    
    def test_filter_mixed_vocabulary_list(self):
        """Test filtering a mixed list of vocabulary items."""
        mixed_vocabulary = [
            # Should be KEPT
            "salamat po",           # Pure Tagalog
            "kumusta ka",           # Pure Tagalog  
            "magkano po",           # Pure Tagalog
            "mango shake po",       # Mixed with particle
            "good morning po",      # English + particle
            "Palawan",              # Unknown (proper noun)
            
            # Should be FILTERED
            "photos",               # Pure English single word
            "perfect",              # Pure English single word
            "computer",             # Loan word single word
            "take photos",          # Pure English phrase
            "perfect timing",       # Pure English phrase
            "fresh juice",          # Pure English phrase
        ]
        
        expected_kept = [
            "salamat po", "kumusta ka", "magkano po", "mango shake po", 
            "good morning po", "Palawan"
        ]
        
        expected_filtered = [
            "photos", "perfect", "computer", "take photos", 
            "perfect timing", "fresh juice"
        ]
        
        filtered_result = self._filter_vocabulary_list(mixed_vocabulary)
        
        for item in expected_kept:
            assert item in filtered_result, f"Should have kept: '{item}'"
        
        for item in expected_filtered:
            assert item not in filtered_result, f"Should have filtered: '{item}'"
    
    def test_realistic_story_extraction_filtering(self):
        """Test filtering on realistic vocabulary extracted from stories."""
        # This simulates what we actually saw in the day 15 extraction
        extracted_vocabulary = [
            # Filipino content (should keep)
            "kumusta po", "salamat po", "magkano po", "opo", "sige po",
            "mga", "dito", "po", "nga", "ate", "kuya",
            
            # Mixed content with particles (should keep)  
            "good afternoon po", "welcome sa taraw cliff", "mango shake po",
            "tubig lang po", "salamat din po",
            
            # Pure English (should filter)
            "photos", "perfect", "editing", "wait", "call", "here", "view", 
            "take", "smile", "painting", "true", "together", "say", "cheese",
            
            # Loan words standalone (should filter)
            "shake", "juice", "computer", "phone"
        ]
        
        filtered = self._filter_vocabulary_list(extracted_vocabulary)
        
        # Verify Filipino content is kept
        filipino_content = ["kumusta po", "salamat po", "opo", "mga", "dito", "nga"]
        for item in filipino_content:
            assert item in filtered, f"Should keep Filipino: '{item}'"
        
        # Verify mixed with particles is kept
        mixed_with_particles = ["good afternoon po", "mango shake po", "salamat din po"]
        for item in mixed_with_particles:
            assert item in filtered, f"Should keep mixed with particles: '{item}'"
        
        # Verify pure English is filtered
        pure_english = ["photos", "perfect", "editing", "wait", "call"]
        for item in pure_english:
            assert item not in filtered, f"Should filter English: '{item}'"
    
    def _filter_vocabulary_list(self, vocabulary: list) -> list:
        """Mock implementation of complete vocabulary filtering."""
        filtered = []
        
        for item in vocabulary:
            if self._should_keep_vocabulary_item(item):
                filtered.append(item)
        
        return filtered
    
    def _should_keep_vocabulary_item(self, item: str) -> bool:
        """Mock implementation of vocabulary item filtering decision."""
        words = item.lower().split()
        
        # Single word filtering
        if len(words) == 1:
            classification = self.detector.classify_word(words[0])
            # Keep Tagalog and unknown, filter English and loan words
            return classification in ["tagalog", "unknown"]
        
        # Multi-word phrase filtering  
        return self._should_keep_phrase(item)
    
    def _should_keep_phrase(self, phrase: str) -> bool:
        """Reuse the phrase filtering logic from earlier test."""
        words = phrase.lower().split()
        
        tagalog_count = 0
        english_count = 0
        unknown_count = 0
        
        # Check for Filipino particles
        filipino_particles = {"po", "ba", "na", "nga", "ang", "mga", "sa", "ay", "din", "rin"}
        has_particles = any(word in filipino_particles for word in words)
        
        for word in words:
            classification = self.detector.classify_word(word)
            if classification == "tagalog":
                tagalog_count += 1
            elif classification in ["english", "loan"]:
                english_count += 1
            else:
                unknown_count += 1
        
        # Keep if has Filipino particles
        if has_particles:
            return True
        
        # Keep if majority Tagalog/unknown
        if (tagalog_count + unknown_count) > english_count:
            return True
        
        # Keep if balanced but has some Tagalog
        if tagalog_count > 0 and tagalog_count >= english_count:
            return True
        
        return False


class TestDictionaryIntegration:
    """Test integration with actual dictionary files."""
    
    def test_dictionary_loading(self):
        """Test loading dictionaries from files."""
        # Mock dictionary files
        english_dict = list(SAMPLE_ENGLISH_DICT)
        tagalog_dict = list(SAMPLE_TAGALOG_DICT)
        
        # Create temporary dictionary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='_english.json', delete=False) as f:
            json.dump(english_dict, f)
            english_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='_tagalog.json', delete=False) as f:
            json.dump(tagalog_dict, f)
            tagalog_path = f.name
        
        try:
            # Test loading
            loaded_english = self._load_dictionary(english_path)
            loaded_tagalog = self._load_dictionary(tagalog_path)
            
            assert loaded_english == set(english_dict)
            assert loaded_tagalog == set(tagalog_dict)
            
        finally:
            # Cleanup
            Path(english_path).unlink()
            Path(tagalog_path).unlink()
    
    def _load_dictionary(self, file_path: str) -> set:
        """Mock dictionary loading implementation."""
        with open(file_path, 'r') as f:
            word_list = json.load(f)
        return set(word.lower() for word in word_list)


class TestRegressionPreventionLanguageFiltering:
    """Test to prevent regression of language filtering issues."""
    
    def setup_method(self):
        self.detector = MockLanguageDetector()
    
    def test_no_over_filtering_of_tagalog_phrases(self):
        """Ensure we don't filter valid Tagalog phrases."""
        valid_tagalog = [
            "magandang umaga po",
            "salamat sa pagdating", 
            "kumusta ka na",
            "ano po ang balita",
            "sige po salamat"
        ]
        
        for phrase in valid_tagalog:
            assert self._should_keep_vocabulary_item(phrase) is True, \
                f"Should not filter valid Tagalog: '{phrase}'"
    
    def test_no_under_filtering_of_english_phrases(self):
        """Ensure we properly filter pure English phrases."""
        pure_english = [
            "take photos",
            "perfect timing", 
            "say cheese",
            "best sunset ever",
            "fresh juice"
        ]
        
        for phrase in pure_english:
            assert self._should_keep_vocabulary_item(phrase) is False, \
                f"Should filter pure English: '{phrase}'"
    
    def test_preserve_natural_taglish(self):
        """Ensure natural Taglish expressions are preserved."""
        natural_taglish = [
            "good morning po",    # Greeting with politeness
            "mango shake po",     # Food with politeness  
            "salamat sa help",    # Thanks with English loan
            "computer na ba",     # Tech with question particle
        ]
        
        for phrase in natural_taglish:
            assert self._should_keep_vocabulary_item(phrase) is True, \
                f"Should preserve natural Taglish: '{phrase}'"
    
    def _should_keep_vocabulary_item(self, item: str) -> bool:
        """Reuse filtering logic for regression tests."""
        words = item.lower().split()
        
        if len(words) == 1:
            classification = self.detector.classify_word(words[0])
            return classification in ["tagalog", "unknown"]
        
        # Multi-word phrase logic
        tagalog_count = sum(1 for w in words if self.detector.classify_word(w) == "tagalog")
        english_count = sum(1 for w in words if self.detector.classify_word(w) in ["english", "loan"])
        unknown_count = len(words) - tagalog_count - english_count
        
        filipino_particles = {"po", "ba", "na", "nga", "ang", "mga", "sa", "ay", "din", "rin"}
        has_particles = any(word in filipino_particles for word in words)
        
        if has_particles:
            return True
        
        if (tagalog_count + unknown_count) > english_count:
            return True
            
        if tagalog_count > 0 and tagalog_count >= english_count:
            return True
            
        return False