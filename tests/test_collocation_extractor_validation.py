"""Tests for CollocationExtractor validation and classification."""
import pytest
from unittest.mock import patch, MagicMock
import spacy

from collocation_extractor import CollocationExtractor


class TestCollocationClassificationValidation:
    """Test proper classification of single words vs multi-word collocations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        # Create a real spaCy model for testing
        self.nlp = spacy.load("en_core_web_sm")
        
        # Create extractor with real spaCy model
        with patch('collocation_extractor.spacy.load', return_value=self.nlp):
            self.extractor = CollocationExtractor()

    def test_single_word_classification(self):
        """Test that actual single words are classified correctly."""
        # Text with clear single words
        text = "The plant grows slowly in soil."
        
        # Extract with debug to capture classification
        with patch('builtins.print') as mock_print:
            result = self.extractor.extract_collocations(text, min_words=1, max_words=1, debug=True)
            
            # Get all debug output
            debug_calls = [call for call in mock_print.call_args_list if 'Debug: Added single word:' in str(call)]
            
            # Validate that each "single word" is actually a single word
            for call in debug_calls:
                debug_message = str(call[0][0])  # Get the printed message
                # Extract the word after "Debug: Added single word: "
                word_part = debug_message.split("Debug: Added single word: ")[1]
                
                # Remove any trailing parentheses or other formatting
                word = word_part.strip().rstrip(')')
                
                # Assert this is actually a single word (no spaces, reasonable length)
                assert ' ' not in word, f"'{word}' contains spaces but was classified as single word"
                assert len(word.split()) == 1, f"'{word}' has multiple words but classified as single"
                assert len(word) < 50, f"'{word}' is suspiciously long ({len(word)} chars) for a single word"
                assert not word.endswith('!'), f"'{word}' ends with punctuation, likely malformed"

    def test_multi_word_classification(self):
        """Test that multi-word phrases are not classified as single words."""
        # Text that might produce problematic tokenization
        text = "Kumusta po! Magkano po ang entrance fee?"
        
        # Extract with debug to capture classification
        with patch('builtins.print') as mock_print:
            result = self.extractor.extract_collocations(text, min_words=1, max_words=4, debug=True)
            
            # Get all debug output
            debug_calls = [call for call in mock_print.call_args_list if 'Debug: Added single word:' in str(call)]
            
            # Validate no multi-word phrases are classified as single words
            for call in debug_calls:
                debug_message = str(call[0][0])
                word_part = debug_message.split("Debug: Added single word: ")[1].strip()
                
                # This should catch the regression where "kumusta po! magkano po ang entrance fee" 
                # was classified as a single word
                assert len(word_part) < 30, f"Single word '{word_part}' is too long ({len(word_part)} chars)"
                assert '!' not in word_part, f"Single word '{word_part}' contains exclamation mark"
                assert ' po ' not in word_part, f"Single word '{word_part}' contains ' po ' suggesting multiple words"
                assert word_part.count(' ') == 0, f"Single word '{word_part}' contains {word_part.count(' ')} spaces"

    def test_no_sentence_fragments_as_single_words(self):
        """Test that sentence fragments are not classified as single words."""
        # Text with potential sentence fragments
        text = "Good afternoon po! Welcome sa Taraw Cliff. How much is the entrance fee?"
        
        with patch('builtins.print') as mock_print:
            result = self.extractor.extract_collocations(text, min_words=1, max_words=1, debug=True)
            
            debug_calls = [call for call in mock_print.call_args_list if 'Debug: Added single word:' in str(call)]
            
            for call in debug_calls:
                debug_message = str(call[0][0])
                word_part = debug_message.split("Debug: Added single word: ")[1].strip()
                
                # Should not classify sentences or long phrases as single words
                assert not any(fragment in word_part.lower() for fragment in [
                    'good afternoon', 'entrance fee', 'how much', 'welcome sa'
                ]), f"Sentence fragment '{word_part}' classified as single word"

    def test_proper_word_count_validation(self):
        """Test that the word counting logic works correctly."""
        test_cases = [
            ("hello", 1),
            ("hello world", 2),
            ("kumusta po", 2),
            ("kumusta po ang", 3),
            ("kumusta po! magkano po ang entrance fee", 7),  # The problematic case
            ("salamat", 1),
            ("salamat po", 2),
        ]
        
        for text, expected_word_count in test_cases:
            actual_count = len(text.split())
            assert actual_count == expected_word_count, \
                f"'{text}' should have {expected_word_count} words, got {actual_count}"

    def test_extractor_returns_proper_format(self):
        """Test that extractor returns properly formatted collocations."""
        text = "Kumusta po! Magkano po ang entrance fee?"
        
        result = self.extractor.extract_collocations(text, min_words=1, max_words=4)
        
        # Verify result is a dictionary with proper keys
        assert isinstance(result, dict), "Result should be a dictionary"
        
        for collocation, count in result.items():
            # Each key should be a string
            assert isinstance(collocation, str), f"Collocation key should be string, got {type(collocation)}"
            
            # Each key should not be excessively long (likely indicates malformed extraction)
            assert len(collocation) < 100, f"Collocation '{collocation}' is too long ({len(collocation)} chars)"
            
            # Count should be positive integer
            assert isinstance(count, int) and count > 0, f"Count should be positive integer, got {count}"
            
            # No collocation should contain the entire sentence
            assert collocation.lower() != text.lower(), f"Collocation '{collocation}' is the entire input text"

    def test_regression_prevent_sentence_as_single_word(self):
        """Regression test to prevent classifying sentences as single words."""
        # The exact problematic case from the user's report
        problematic_text = "kumusta po! magkano po ang entrance fee"
        
        with patch('builtins.print') as mock_print:
            result = self.extractor.extract_collocations(
                "Kumusta po! Magkano po ang entrance fee?", 
                min_words=1, max_words=4, debug=True
            )
            
            # Check that the problematic text is NOT classified as a single word
            debug_calls = [call for call in mock_print.call_args_list if 'Debug: Added single word:' in str(call)]
            
            for call in debug_calls:
                debug_message = str(call[0][0])
                if 'Debug: Added single word:' in debug_message:
                    word_part = debug_message.split("Debug: Added single word: ")[1].strip()
                    # The exact regression case should not happen
                    assert word_part.lower() != problematic_text, \
                        f"Regression: '{problematic_text}' was classified as single word"