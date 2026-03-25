"""
Tests for DeterministicEnglishDetector class.

Tests the new deterministic English term detection system that replaced 
the problematic database substring matching approach.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sqlite3
import tempfile
import json
from pathlib import Path

from srs_llm_enforcer import DeterministicEnglishDetector
from srs_database import SRSDatabase
from language_detector import LanguageDetector


@pytest.fixture
def mock_srs_db():
    """Mock SRS database for testing."""
    db = Mock(spec=SRSDatabase)
    db.db_path = ":memory:"
    return db

@pytest.fixture
def mock_language_detector():
    """Mock LanguageDetector for controlled testing."""
    detector = Mock(spec=LanguageDetector)
    
    # Define classification behavior
    def classify_word_side_effect(word):
        english_words = {'good', 'morning', 'water', 'thank', 'you', 'delicious', 'food', 'next', 'year', 'time', 'flight'}
        tagalog_words = {'po', 'magandang', 'umaga', 'tubig', 'salamat', 'masarap'}
        loan_words = {'mango', 'shake', 'special', 'meal'}
        
        word_lower = word.lower()
        if word_lower in english_words:
            return 'english'
        elif word_lower in tagalog_words:
            return 'tagalog'  
        elif word_lower in loan_words:
            return 'loan'
        else:
            return 'unknown'
    
    detector.classify_word.side_effect = classify_word_side_effect
    detector.has_filipino_context.return_value = False
    
    return detector

@pytest.fixture
def detector(mock_srs_db, mock_language_detector):
    """Create DeterministicEnglishDetector with mocked dependencies."""
    with patch('srs_llm_enforcer.LanguageDetector', return_value=mock_language_detector):
        return DeterministicEnglishDetector(mock_srs_db)


class TestDeterministicEnglishDetector:
    """Test suite for DeterministicEnglishDetector functionality."""
    

class TestDialogueExtraction:
    """Test dialogue content extraction from stories."""
    
    def test_extract_dialogue_content_basic(self, detector):
        """Test basic dialogue extraction from story content."""
        story_content = """[NARRATOR]: Day 8: Test Story
        
[TAGALOG-FEMALE-1]: Good morning po!
[TAGALOG-MALE-1]: Thank you very much.
[NARRATOR]: Some narrator text
[TAGALOG-FEMALE-2]: How are you?"""
        
        dialogue_lines = detector.extract_dialogue_content(story_content)
        
        expected = [
            "Good morning po!",
            "Thank you very much.",
            "How are you?"
        ]
        assert dialogue_lines == expected
    
    def test_extract_dialogue_content_empty_lines(self, detector):
        """Test extraction handles empty dialogue lines."""
        story_content = """[TAGALOG-FEMALE-1]: 
[TAGALOG-MALE-1]: Good morning
[TAGALOG-FEMALE-2]:   
[TAGALOG-MALE-2]: Thank you"""
        
        dialogue_lines = detector.extract_dialogue_content(story_content)
        
        expected = ["Good morning", "Thank you"]
        assert dialogue_lines == expected
    
    def test_extract_dialogue_content_malformed(self, detector):
        """Test extraction with malformed dialogue tags."""
        story_content = """[TAGALOG-FEMALE-1]: Valid dialogue
[INVALID-TAG]: Should be ignored
[TAGALOG-MALE-1] Missing colon
[TAGALOG-MALE-2]: Another valid line"""
        
        dialogue_lines = detector.extract_dialogue_content(story_content)
        
        expected = ["Valid dialogue", "Another valid line"]
        assert dialogue_lines == expected


class TestEnglishTermDetection:
    """Test English term detection from dialogue content."""
    
    def test_detect_english_terms_basic(self, detector):
        """Test basic English term detection."""
        story_content = """[TAGALOG-FEMALE-1]: Good morning po!
[TAGALOG-MALE-1]: Thank you for the water."""
        
        with patch.object(detector, '_has_srs_equivalent') as mock_srs:
            mock_srs.return_value = False  # All terms are future candidates
            
            srs_backed, future_candidates = detector.detect_english_terms(story_content)
            
            assert srs_backed == []
            # Should detect individual English words
            assert 'good' in future_candidates
            assert 'morning' in future_candidates  
            assert 'thank' in future_candidates
            assert 'you' in future_candidates
            assert 'water' in future_candidates
    
    def test_detect_english_terms_with_srs_backing(self, detector):
        """Test detection with some terms having SRS equivalents."""
        story_content = """[TAGALOG-FEMALE-1]: Good morning and thank you."""
        
        def srs_equivalent_side_effect(term):
            # Only 'water' and 'thank you' have SRS equivalents
            return term in ['water', 'thank you', 'good morning']
        
        with patch.object(detector, '_has_srs_equivalent') as mock_srs:
            mock_srs.side_effect = srs_equivalent_side_effect
            
            srs_backed, future_candidates = detector.detect_english_terms(story_content)
            
            # Should categorize correctly
            assert 'good morning' in srs_backed or any('good' in term for term in srs_backed)
            assert len(future_candidates) > 0  # Other English words without SRS backing
    
    def test_detect_english_terms_loan_words(self, detector):
        """Test detection includes loan words for deepening."""
        story_content = """[TAGALOG-FEMALE-1]: I want mango shake please."""
        
        with patch.object(detector, '_has_srs_equivalent') as mock_srs:
            mock_srs.return_value = False
            
            srs_backed, future_candidates = detector.detect_english_terms(story_content)
            
            # Should detect loan words for potential deepening
            assert 'mango' in future_candidates
            assert 'shake' in future_candidates
    
    def test_detect_english_phrases_multiword(self, detector):
        """Test detection of multi-word English phrases."""
        story_content = """[TAGALOG-FEMALE-1]: Thank you very much for the good morning greeting."""
        
        with patch.object(detector, '_has_srs_equivalent') as mock_srs:
            mock_srs.return_value = False
            
            # Mock phrase detection
            with patch.object(detector, '_detect_english_phrases') as mock_phrases:
                mock_phrases.return_value = ['thank you', 'good morning', 'very much']
                
                srs_backed, future_candidates = detector.detect_english_terms(story_content)
                
                # Should include multi-word phrases
                detected_terms = srs_backed + future_candidates
                assert any('thank you' in str(term) for term in detected_terms)
                assert any('good morning' in str(term) for term in detected_terms)


class TestEnglishPhraseDetection:
    """Test multi-word English phrase detection logic."""
    
    def test_detect_english_phrases_two_word(self, detector):
        """Test detection of 2-word English phrases."""
        line = "good morning and thank you"
        
        phrases = detector._detect_english_phrases(line)
        
        # Should detect common English phrases
        assert 'good morning' in phrases
        assert 'thank you' in phrases
    
    def test_detect_english_phrases_three_word(self, detector):
        """Test detection of 3-word English phrases."""
        line = "thank you very much"
        
        with patch.object(detector, '_is_english_phrase') as mock_check:
            mock_check.side_effect = lambda phrase: phrase in ['thank you very']
            
            phrases = detector._detect_english_phrases(line)
            
            # Should check 3-word combinations
            mock_check.assert_any_call('thank you very')
    
    def test_is_english_phrase_classification(self, detector):
        """Test English phrase classification logic."""
        # Pure English phrase
        assert detector._is_english_phrase("good morning") == True
        
        # Mixed phrase (should be English if majority English)
        with patch.object(detector.language_detector, 'classify_word') as mock_classify:
            mock_classify.side_effect = lambda w: 'english' if w in ['good', 'very'] else 'tagalog'
            assert detector._is_english_phrase("good po") == False  # Mixed with Filipino particle
        
        # Single word (should return False)
        assert detector._is_english_phrase("good") == False


class TestSRSCrossReference:
    """Test SRS database cross-reference functionality."""
    
    def test_has_srs_equivalent_found(self, detector):
        """Test SRS equivalent detection when matches exist."""
        with patch.object(detector, '_search_srs_for_equivalent') as mock_search:
            mock_search.return_value = [{'text': 'magandang umaga', 'stability': 1.5}]
            
            result = detector._has_srs_equivalent('good morning')
            
            assert result == True
            mock_search.assert_called_once_with('good morning')
    
    def test_has_srs_equivalent_not_found(self, detector):
        """Test SRS equivalent detection when no matches exist."""
        with patch.object(detector, '_search_srs_for_equivalent') as mock_search:
            mock_search.return_value = []
            
            result = detector._has_srs_equivalent('rare english phrase')
            
            assert result == False
    
    def test_search_srs_for_equivalent_database_queries(self, detector):
        """Test SRS database search queries."""
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = [('magandang umaga po', 1.5), ('good morning', 0.8)]
            
            with patch.object(detector, '_generate_search_queries') as mock_queries:
                mock_queries.return_value = ['good morning', 'morning']
                
                results = detector._search_srs_for_equivalent('good morning')
                
                # Should query database for each search term
                assert mock_cursor.execute.call_count == 2
                assert len(results) == 4  # 2 results × 2 queries
    
    def test_generate_search_queries_multiword(self, detector):
        """Test search query generation for multi-word terms."""
        queries = detector._generate_search_queries('good morning')
        
        # Should include original term and individual words
        assert 'good morning' in queries
        assert 'goodmorning' in queries  # No spaces version
        assert 'good' in queries
        assert 'morning' in queries
    
    def test_generate_search_queries_single_word(self, detector):
        """Test search query generation for single words."""
        queries = detector._generate_search_queries('water')
        
        # Should include just the original term
        assert 'water' in queries
        assert len(queries) >= 1


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_detect_english_terms_empty_content(self, detector):
        """Test detection with empty story content."""
        srs_backed, future_candidates = detector.detect_english_terms("")
        
        assert srs_backed == []
        assert future_candidates == []
    
    def test_detect_english_terms_no_dialogue(self, detector):
        """Test detection with content containing no dialogue."""
        story_content = """[NARRATOR]: This is just narrator text.
        
Some other non-dialogue content here."""
        
        srs_backed, future_candidates = detector.detect_english_terms(story_content)
        
        assert srs_backed == []
        assert future_candidates == []
    
    def test_srs_search_database_error(self, detector):
        """Test handling of database errors during SRS search."""
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")
            
            # Should not crash, just return empty results
            results = detector._search_srs_for_equivalent('test term')
            assert results == []
    
    def test_has_srs_equivalent_error_handling(self, detector):
        """Test error handling in SRS equivalent checking."""
        with patch.object(detector, '_search_srs_for_equivalent') as mock_search:
            mock_search.side_effect = Exception("Search error")
            
            # Should return False on error, not crash
            result = detector._has_srs_equivalent('test term')
            assert result == False


class TestRealWorldScenarios:
    """Test with real-world problematic scenarios from Day 19."""
    
    def test_day19_problematic_terms(self, detector):
        """Test detection of originally problematic Day 19 terms."""
        # This is the type of content that was causing issues
        story_content = """[TAGALOG-FEMALE-1]: Good morning po! I need some water please.
[TAGALOG-MALE-1]: Thank you, that's very delicious food!
[TAGALOG-FEMALE-1]: What time is it? I have a flight next year.
[TAGALOG-MALE-1]: The special meal and mango shake are ready."""
        
        with patch.object(detector, '_has_srs_equivalent') as mock_srs:
            mock_srs.return_value = False  # Simulate no SRS backing for simplicity
            
            srs_backed, future_candidates = detector.detect_english_terms(story_content)
            
            # Should detect all the originally problematic terms
            all_detected = srs_backed + future_candidates
            problematic_terms = ['good', 'morning', 'water', 'thank', 'you', 'delicious', 'food', 
                                'time', 'flight', 'next', 'year', 'special', 'meal', 'mango', 'shake', 'ready']
            
            # Check that most problematic terms are detected
            detected_count = sum(1 for term in problematic_terms if any(term in detected.lower() for detected in all_detected))
            assert detected_count >= len(problematic_terms) * 0.7  # At least 70% detection rate
    
    def test_no_database_driven_replacements(self, detector):
        """Test that detector doesn't create problematic database-driven replacements."""
        story_content = """[TAGALOG-FEMALE-1]: Good morning po!"""
        
        # The key test: detector should only identify English terms, not create replacements
        srs_backed, future_candidates = detector.detect_english_terms(story_content)
        
        # Should detect English terms
        assert len(srs_backed + future_candidates) > 0
        
        # But should NOT create any nonsensical mappings like 'Good morning' → 'ito magandang umaga'
        # The detector's job is ONLY to identify English terms, not create replacements
        for term in srs_backed + future_candidates:
            # All detected terms should be reasonable English words/phrases
            assert isinstance(term, str)
            assert len(term) > 0
            assert not term.startswith('ito ')  # Should never create the problematic mappings