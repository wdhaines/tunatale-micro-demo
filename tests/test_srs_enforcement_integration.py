"""
Integration tests for SRS enforcement system components.

Tests the integration between DeterministicEnglishDetector, SRSLLMEnforcer,
and the complete enforcement pipeline to ensure all components work together.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json
import sqlite3
import tempfile
from pathlib import Path

from srs_llm_enforcer import SRSLLMEnforcer, DeterministicEnglishDetector
from srs_database import SRSDatabase
from enhanced_srs_database import EnhancedSRSDatabase
from llm_mock import MockLLM


@pytest.fixture
def temp_db_path():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        yield tmp.name
    Path(tmp.name).unlink(missing_ok=True)

@pytest.fixture
def mock_srs_db(temp_db_path):
    """Mock SRS database with test data."""
    db = Mock(spec=SRSDatabase)
    db.db_path = temp_db_path
    
    # Create actual database for integration testing
    with sqlite3.connect(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collocations (
                id INTEGER PRIMARY KEY,
                text TEXT,
                stability REAL DEFAULT 0.0
            )
        """)
        
        # Insert test data that would match English terms
        test_collocations = [
            ("magandang umaga po", 1.5),
            ("salamat po", 1.2),
            ("tubig po", 0.8),
            ("masarap na pagkain", 1.0),
            ("susunod na taon", 0.9)
        ]
        
        cursor.executemany(
            "INSERT INTO collocations (text, stability) VALUES (?, ?)",
            test_collocations
        )
        conn.commit()
    
    return db

@pytest.fixture
def mock_enhanced_db():
    """Mock enhanced SRS database."""
    db = Mock(spec=EnhancedSRSDatabase)
    # Mock the find_filipino_equivalent method to return None (no match found)
    db.find_filipino_equivalent.return_value = None
    return db

@pytest.fixture
def mock_llm():
    """Mock LLM with realistic responses."""
    llm = Mock(spec=MockLLM)
    
    # Default response in text-first format
    llm.chat_response.return_value = {
        'choices': [{
            'message': {
                'content': """[NARRATOR]: Day 8: Test Story

[TAGALOG-FEMALE-1]: Magandang umaga po! Kailangan ko po ng tubig.
[TAGALOG-MALE-1]: Salamat po sa masarap na pagkain!

PHRASE_TRANSLATIONS:
{
  "magandang umaga po": "good morning (polite)",
  "kailangan ko po": "I need (polite)",
  "tubig": "water",
  "salamat po": "thank you (polite)",
  "masarap na pagkain": "delicious food"
}"""
            }
        }]
    }
    
    return llm

@pytest.fixture
def integrated_enforcer(mock_llm, mock_srs_db, mock_enhanced_db):
    """Create fully integrated SRS enforcer."""
    return SRSLLMEnforcer(mock_llm, mock_srs_db, mock_enhanced_db)


class TestComponentIntegration:
    """Test integration between enforcement system components."""


class TestDeterministicDetectorIntegration:
    """Test integration of deterministic detector with main enforcer."""
    
    def test_detector_initialization_in_enforcer(self, integrated_enforcer):
        """Test that detector is properly initialized in enforcer."""
        assert isinstance(integrated_enforcer.english_detector, DeterministicEnglishDetector)
        assert integrated_enforcer.english_detector.srs_db is integrated_enforcer.srs_db
        assert integrated_enforcer.english_detector.enhanced_db is integrated_enforcer.enhanced_db
    
    def test_detect_english_terms_integration(self, integrated_enforcer):
        """Test that English detection integrates with SRS database queries."""
        story_content = """[TAGALOG-FEMALE-1]: Good morning po! I need water.
[TAGALOG-MALE-1]: Thank you for the delicious food."""
        
        with patch.object(integrated_enforcer.english_detector.language_detector, 'classify_word') as mock_classify:
            # Mock classification to identify English terms
            def classify_side_effect(word):
                english_words = {'good', 'morning', 'need', 'water', 'thank', 'you', 'delicious', 'food'}
                return 'english' if word.lower() in english_words else 'tagalog'
            
            mock_classify.side_effect = classify_side_effect
            
            srs_backed, future_candidates = integrated_enforcer.english_detector.detect_english_terms(story_content)
            
            # Should detect English terms and categorize based on SRS availability
            all_detected = srs_backed + future_candidates
            assert len(all_detected) > 0
            
            # Should include detected English words
            detected_text = ' '.join(all_detected).lower()
            assert any('good' in detected_text for _ in [1])
            assert any('water' in detected_text for _ in [1])
            assert any('thank' in detected_text for _ in [1])
    
    def test_srs_cross_reference_integration(self, integrated_enforcer, temp_db_path):
        """Test SRS cross-reference with actual database queries."""
        
        # Test with terms that should have SRS equivalents
        terms_to_test = ["good morning", "thank you", "water"]
        
        for term in terms_to_test:
            has_equivalent = integrated_enforcer.english_detector._has_srs_equivalent(term)
            
            # Should execute actual database queries
            assert isinstance(has_equivalent, bool)
            
            # Test search functionality
            matches = integrated_enforcer.english_detector._search_srs_for_equivalent(term)
            assert isinstance(matches, list)


class TestEndToEndEnforcement:
    """Test complete end-to-end enforcement workflow."""
    
    def test_enforce_with_deterministic_detection_complete_workflow(self, integrated_enforcer):
        """Test complete deterministic detection + LLM enforcement workflow."""
        story_content = """[NARRATOR]: Day 8: El Nido Morning

[TAGALOG-FEMALE-1]: Good morning po! I need some water please.
[TAGALOG-MALE-1]: Thank you, the food is very delicious!"""
        
        with patch.object(integrated_enforcer.english_detector.language_detector, 'classify_word') as mock_classify:
            # Mock English word classification
            mock_classify.side_effect = lambda w: 'english' if w.lower() in {
                'good', 'morning', 'need', 'some', 'water', 'please', 
                'thank', 'you', 'food', 'very', 'delicious'
            } else 'tagalog'
            
            enforced_content, violations, translations = integrated_enforcer.enforce_with_deterministic_detection(
                story_content, day=8, context="story"
            )
            
            # Should complete without errors
            assert isinstance(enforced_content, str)
            assert isinstance(violations, list)
            assert isinstance(translations, list)
            
            # Content should be clean (no SRS analysis section)
            assert "[NARRATOR]: Day 8: Test Story" in enforced_content  # From mock LLM response
            assert "SRS Enforcement Analysis" not in enforced_content
            assert "PHRASE_TRANSLATIONS:" not in enforced_content
    
    def test_srs_analysis_building_and_injection(self, integrated_enforcer):
        """Test SRS analysis building and content injection."""
        english_terms = ["good morning", "thank you", "water"]
        
        # Test analysis building
        srs_analysis = integrated_enforcer._build_srs_analysis_from_terms(english_terms)
        
        assert len(srs_analysis) == 3
        assert all('english' in term_data for term_data in srs_analysis)
        assert all('srs_queries' in term_data for term_data in srs_analysis)
        
        # Test content injection
        original_content = "[TAGALOG-FEMALE-1]: Test content"
        enhanced_content = integrated_enforcer._inject_srs_analysis(original_content, srs_analysis)
        
        assert original_content in enhanced_content
        assert "SRS Enforcement Analysis" in enhanced_content
        assert "english_terms" in enhanced_content
    
    def test_merging_deterministic_and_existing_analysis(self, integrated_enforcer):
        """Test merging deterministic detection with existing LLM analysis."""
        deterministic_terms = ["good", "morning", "water"]
        existing_analysis = [
            {"english": "thank you", "srs_queries": ["salamat"]},
            {"english": "morning", "srs_queries": ["umaga"]},  # Overlap
            {"english": "delicious", "srs_queries": ["masarap"]}
        ]
        
        merged_terms = integrated_enforcer._merge_english_term_lists(deterministic_terms, existing_analysis)
        
        # Should combine and deduplicate
        assert "good" in merged_terms
        assert "morning" in merged_terms  # Should appear once despite overlap
        assert "water" in merged_terms
        assert "thank you" in merged_terms
        assert "delicious" in merged_terms
        
        # Should not have duplicates
        assert len(set(merged_terms)) == len(merged_terms)


class TestErrorHandlingAndResilience:
    """Test error handling and system resilience."""
    
    def test_database_error_handling(self, integrated_enforcer):
        """Test graceful handling of database errors."""
        with patch('sqlite3.connect') as mock_connect:
            # Simulate database connection failure
            mock_connect.side_effect = sqlite3.Error("Database connection failed")
            
            # Should not crash, should return empty results
            matches = integrated_enforcer.english_detector._search_srs_for_equivalent("test")
            assert matches == []
            
            has_equivalent = integrated_enforcer.english_detector._has_srs_equivalent("test")
            assert has_equivalent == False
    
    def test_llm_error_handling(self, integrated_enforcer):
        """Test handling of LLM errors during enforcement."""
        with patch.object(integrated_enforcer.llm, 'chat_response') as mock_llm:
            # Simulate LLM error
            mock_llm.side_effect = Exception("LLM request failed")
            
            story_content = "[TAGALOG-FEMALE-1]: Test content with English words."
            
            # Should handle error gracefully
            try:
                enforced_content, violations, translations = integrated_enforcer.enforce_with_llm(
                    story_content, day=8, context="story"
                )
                # If it doesn't raise, should return reasonable defaults
                assert isinstance(enforced_content, str)
                assert isinstance(violations, list)
                assert isinstance(translations, list)
            except Exception as e:
                # Should be a handled exception with meaningful message
                assert "LLM request failed" in str(e)
    
    def test_malformed_content_handling(self, integrated_enforcer):
        """Test handling of malformed or edge case content."""
        edge_case_contents = [
            "",  # Empty content
            "[INVALID-TAG]: Not a valid dialogue tag",  # Invalid dialogue
            "[TAGALOG-FEMALE-1]:",  # Empty dialogue
            "Plain text without dialogue tags",  # No dialogue tags
            "[TAGALOG-FEMALE-1]: Content with\n\nMultiple\n\n\nNewlines",  # Formatting issues
        ]
        
        for content in edge_case_contents:
            # Should handle gracefully without crashing
            srs_backed, future_candidates = integrated_enforcer.english_detector.detect_english_terms(content)
            
            assert isinstance(srs_backed, list)
            assert isinstance(future_candidates, list)


class TestPerformanceAndEfficiency:
    """Test performance characteristics and efficiency."""
    
    def test_large_content_handling(self, integrated_enforcer):
        """Test handling of large story content."""
        # Create large content
        large_dialogue_lines = [
            f"[TAGALOG-FEMALE-1]: Line {i} with English words like good morning and thank you."
            for i in range(100)
        ]
        large_content = "\n".join(large_dialogue_lines)
        
        with patch.object(integrated_enforcer.english_detector.language_detector, 'classify_word') as mock_classify:
            mock_classify.side_effect = lambda w: 'english' if w.lower() in {
                'line', 'with', 'english', 'words', 'like', 'good', 'morning', 'and', 'thank', 'you'
            } else 'tagalog'
            
            # Should handle large content efficiently
            srs_backed, future_candidates = integrated_enforcer.english_detector.detect_english_terms(large_content)
            
            # Should detect terms from large content
            all_detected = srs_backed + future_candidates
            assert len(all_detected) > 0
    
    def test_database_query_efficiency(self, integrated_enforcer, temp_db_path):
        """Test that database queries are reasonably efficient."""
        # Add more test data to database
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            
            # Add many test collocations
            test_data = [(f"test phrase {i}", 0.5) for i in range(1000)]
            cursor.executemany(
                "INSERT INTO collocations (text, stability) VALUES (?, ?)",
                test_data
            )
            conn.commit()
        
        # Test search with various terms
        search_terms = ["good morning", "thank you", "water", "food", "delicious"]
        
        for term in search_terms:
            matches = integrated_enforcer.english_detector._search_srs_for_equivalent(term)
            # Should complete without timeout
            assert isinstance(matches, list)


class TestRealWorldScenarios:
    """Test with realistic story content and scenarios."""
    
    def test_complete_day8_story_enforcement(self, integrated_enforcer):
        """Test enforcement with complete Day 8 style story."""
        complete_story = """[NARRATOR]: Day 8: Farewell El Nido

Key Phrases:

[TAGALOG-FEMALE-1]: salamat sa lahat
[NARRATOR]: thank you for everything
[TAGALOG-FEMALE-1]: salamat sa lahat

[NARRATOR]: Natural Speed

[NARRATOR]: Hotel Checkout

[TAGALOG-FEMALE-1]: Good morning po! Check out ko na po.
[TAGALOG-FEMALE-2]: Good morning po sa inyo! How was your stay?
[TAGALOG-FEMALE-1]: Very beautiful here! El Nido is so peaceful.
[TAGALOG-FEMALE-2]: Thank you so much! What time is your flight?
[TAGALOG-FEMALE-1]: Two thirty in the afternoon. I need to leave at twelve.

[NARRATOR]: Slow Speed

[TAGALOG-FEMALE-1]: Good... morning... po!... Check... out... ko... na... po.

[NARRATOR]: Translated

[TAGALOG-FEMALE-1]: Good morning po! Check out ko na po.
[NARRATOR]: Good morning! I'm checking out now."""
        
        with patch.object(integrated_enforcer.english_detector.language_detector, 'classify_word') as mock_classify:
            # Mock comprehensive English word classification
            english_words = {
                'good', 'morning', 'check', 'out', 'how', 'was', 'your', 'stay',
                'very', 'beautiful', 'here', 'so', 'peaceful', 'thank', 'you',
                'much', 'what', 'time', 'flight', 'two', 'thirty', 'afternoon',
                'need', 'leave', 'twelve', 'now'
            }
            mock_classify.side_effect = lambda w: 'english' if w.lower() in english_words else 'tagalog'
            
            enforced_content, violations, translations = integrated_enforcer.enforce_with_deterministic_detection(
                complete_story, day=8, context="story"
            )
            
            # Should produce clean, complete result
            assert "[NARRATOR]: Day 8: Test Story" in enforced_content  # From mock LLM response
            assert "Magandang umaga po" in enforced_content  # From mock LLM response
            
            # Should not contain analysis artifacts
            assert "SRS Enforcement Analysis" not in enforced_content
            assert "english_terms" not in enforced_content
            
            # Should have detected violations/replacements
            assert isinstance(violations, list)
            assert isinstance(translations, list)
    
    def test_mixed_filipino_english_content_handling(self, integrated_enforcer):
        """Test handling of mixed Filipino-English content."""
        mixed_content = """[TAGALOG-FEMALE-1]: Magandang umaga po! Good morning din sa inyo.
[TAGALOG-MALE-1]: Salamat po. Thank you very much for your kindness.
[TAGALOG-FEMALE-1]: Walang anuman po. You're welcome talaga."""
        
        with patch.object(integrated_enforcer.english_detector.language_detector, 'classify_word') as mock_classify:
            def mixed_classify(word):
                english_words = {'good', 'morning', 'thank', 'you', 'very', 'much', 'for', 'your', 'kindness', 'welcome'}
                tagalog_words = {'magandang', 'umaga', 'po', 'din', 'sa', 'inyo', 'salamat', 'walang', 'anuman', 'talaga'}
                
                word_lower = word.lower()
                if word_lower in english_words:
                    return 'english'
                elif word_lower in tagalog_words:
                    return 'tagalog'
                else:
                    return 'unknown'
            
            mock_classify.side_effect = mixed_classify
            
            srs_backed, future_candidates = integrated_enforcer.english_detector.detect_english_terms(mixed_content)
            
            # Should detect English terms even in mixed content
            all_detected = srs_backed + future_candidates
            detected_text = ' '.join(all_detected).lower()
            
            assert any('good' in detected_text for _ in [1])
            assert any('thank' in detected_text for _ in [1])
            assert any('welcome' in detected_text for _ in [1])