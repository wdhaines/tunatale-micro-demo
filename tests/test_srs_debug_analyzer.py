"""
Unit tests for SRS Debug Analyzer

Tests vocabulary recognition state analysis and SRS debugging capabilities.
"""

import pytest
import json
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, mock_open

from srs_debug_analyzer import (
    SRSDebugAnalyzer, 
    RecognitionState, 
    VocabularyAnalysis
)


class TestSRSDebugAnalyzer:
    """Test SRSDebugAnalyzer functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary database path
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        
        # Create test database with sample data
        self._create_test_database()
        
        # Initialize analyzer with test database
        self.analyzer = SRSDebugAnalyzer(db_path=self.temp_db.name)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        Path(self.temp_db.name).unlink(missing_ok=True)
    
    def _create_test_database(self):
        """Create test database with sample SRS data."""
        with sqlite3.connect(self.temp_db.name) as conn:
            # Create collocations table
            conn.execute("""
                CREATE TABLE collocations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT UNIQUE NOT NULL,
                    first_seen_day INTEGER NOT NULL,
                    last_seen_day INTEGER NOT NULL,
                    appearances TEXT NOT NULL,
                    review_count INTEGER NOT NULL DEFAULT 0,
                    next_review_day INTEGER NOT NULL DEFAULT 0,
                    stability REAL NOT NULL DEFAULT 1.0
                )
            """)
            
            # Insert test data
            test_collocations = [
                ('salamat', 1, 15, '[1, 3, 5, 10, 15]', 8, 18, 3.5),  # HIGH_STABILITY
                ('po', 1, 16, '[1, 2, 3, 5, 8, 16]', 6, 20, 4.0),    # HIGH_STABILITY
                ('tubig', 5, 16, '[5, 8, 12, 16]', 4, 18, 2.2),      # EXPLICITLY_LEARNED
                ('kumusta', 3, 16, '[3, 7, 16]', 2, 17, 1.8),        # NATURALLY_ACQUIRING
                ('unstable_word', 10, 16, '[10, 16]', 3, 17, 0.8),   # UNSTABLE
                ('dormant_word', 2, 8, '[2, 5, 8]', 2, 12, 1.5),     # DORMANT (last seen day 8, current 16)
            ]
            
            for colloc_data in test_collocations:
                conn.execute("""
                    INSERT INTO collocations 
                    (text, first_seen_day, last_seen_day, appearances, review_count, next_review_day, stability)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, colloc_data)
    
    def test_categorize_word_high_stability(self):
        """Test high stability word categorization."""
        srs_data = {
            'stability': 3.5,
            'review_count': 8,
            'last_seen_day': 15
        }
        
        state = self.analyzer._categorize_word('salamat', srs_data, 16)
        assert state == RecognitionState.HIGH_STABILITY
    
    def test_categorize_word_unstable(self):
        """Test unstable word categorization."""
        srs_data = {
            'stability': 0.8,
            'review_count': 3,
            'last_seen_day': 16
        }
        
        state = self.analyzer._categorize_word('unstable_word', srs_data, 16)
        assert state == RecognitionState.UNSTABLE
    
    def test_categorize_word_dormant(self):
        """Test dormant word categorization."""
        srs_data = {
            'stability': 1.5,
            'review_count': 2,
            'last_seen_day': 8  # More than 7 days ago from current day 16
        }
        
        state = self.analyzer._categorize_word('dormant_word', srs_data, 16)
        assert state == RecognitionState.DORMANT
    
    def test_categorize_word_unknown(self):
        """Test unknown word categorization."""
        state = self.analyzer._categorize_word('unknown_word', None, 16)
        assert state == RecognitionState.UNKNOWN
    
    def test_categorize_word_explicitly_learned(self):
        """Test explicitly learned word categorization."""
        srs_data = {
            'stability': 2.2,
            'review_count': 4,
            'last_seen_day': 16
        }
        
        state = self.analyzer._categorize_word('tubig', srs_data, 16)
        assert state == RecognitionState.EXPLICITLY_LEARNED
    
    def test_categorize_word_naturally_acquiring(self):
        """Test naturally acquiring word categorization."""
        srs_data = {
            'stability': 1.8,
            'review_count': 2,
            'last_seen_day': 16
        }
        
        state = self.analyzer._categorize_word('kumusta', srs_data, 16)
        assert state == RecognitionState.NATURALLY_ACQUIRING
    
    def test_extract_tagalog_vocabulary(self):
        """Test Tagalog vocabulary extraction from story content."""
        story_content = """
        [NARRATOR]: Day 16: Restaurant Confidence
        
        Key Phrases:
        
        [TAGALOG-FEMALE-1]: salamat po
        [NARRATOR]: thank you
        [TAGALOG-FEMALE-1]: salamat po
        [TAGALOG-FEMALE-1]: po
        [TAGALOG-FEMALE-1]: sa
        [TAGALOG-FEMALE-1]: salamat
        
        [TAGALOG-MALE-1]: kumusta kayo
        [NARRATOR]: how are you all
        [TAGALOG-MALE-1]: kumusta kayo
        """
        
        vocabulary = self.analyzer._extract_tagalog_vocabulary(story_content)
        
        # Should extract unique words from Tagalog speaker lines
        expected_words = ['kayo', 'kumusta', 'po', 'sa', 'salamat']
        assert vocabulary == expected_words
    
    def test_is_valid_tagalog_word(self):
        """Test Tagalog word validation."""
        # Valid particles and words
        assert self.analyzer._is_valid_tagalog_word('po') == True
        assert self.analyzer._is_valid_tagalog_word('ba') == True
        assert self.analyzer._is_valid_tagalog_word('salamat') == True
        assert self.analyzer._is_valid_tagalog_word('kumusta') == True
        
        # Invalid syllable fragments
        assert self.analyzer._is_valid_tagalog_word('te') == False
        assert self.analyzer._is_valid_tagalog_word('re') == False
        assert self.analyzer._is_valid_tagalog_word('mi') == False
    
    def test_analyze_learning_pattern(self):
        """Test learning pattern analysis."""
        # Exposure based pattern
        srs_data = {
            'appearances': [1, 2, 3, 5, 8, 12],  # 6 appearances
            'review_count': 2,  # But only 2 reviews
            'stability': 1.5
        }
        pattern = self.analyzer._analyze_learning_pattern(srs_data)
        assert pattern == "exposure_based"
        
        # Review intensive pattern
        srs_data = {
            'appearances': [5, 8],  # 2 appearances
            'review_count': 5,  # But 5 reviews
            'stability': 2.0
        }
        pattern = self.analyzer._analyze_learning_pattern(srs_data)
        assert pattern == "review_intensive"
        
        # Well consolidated pattern - need review_count <= len(appearances) to avoid review_intensive
        srs_data = {
            'appearances': [1, 3, 5, 7, 8],  # 5 appearances
            'review_count': 4,              # 4 reviews (less than appearances)
            'stability': 3.0               # High stability
        }
        pattern = self.analyzer._analyze_learning_pattern(srs_data)
        assert pattern == "well_consolidated"
        
        # Struggling pattern - review_count <= len(appearances) but low stability
        srs_data = {
            'appearances': [8, 10, 12, 14],  # 4 appearances
            'review_count': 4,               # Equal reviews (not more)
            'stability': 1.0                 # Low stability despite reviews
        }
        pattern = self.analyzer._analyze_learning_pattern(srs_data)
        assert pattern == "struggling"
    
    def test_calculate_effectiveness_metrics(self):
        """Test SRS effectiveness metrics calculation."""
        # Create sample analyses
        analyses = [
            VocabularyAnalysis('salamat', RecognitionState.HIGH_STABILITY, {}, [], None),
            VocabularyAnalysis('po', RecognitionState.HIGH_STABILITY, {}, [], None),
            VocabularyAnalysis('tubig', RecognitionState.EXPLICITLY_LEARNED, {}, [], None),
            VocabularyAnalysis('kumusta', RecognitionState.NATURALLY_ACQUIRING, {}, [], None),
            VocabularyAnalysis('unstable_word', RecognitionState.UNSTABLE, {}, [], None),
            VocabularyAnalysis('unknown_word', RecognitionState.UNKNOWN, {}, [], None),
        ]
        
        metrics = self.analyzer._calculate_effectiveness_metrics(analyses)
        
        # Check calculated metrics
        assert metrics['srs_coverage_percentage'] == 83.3  # 5 of 6 words in SRS
        assert metrics['high_stability_words'] == 2
        assert metrics['unknown_words'] == 1
        assert metrics['words_needing_attention'] == 1  # 1 unstable, 0 dormant
        assert 'learning_progress_percentage' in metrics
        assert 'stability_ratio_percentage' in metrics
    
    @patch('builtins.open', new_callable=mock_open, read_data="""
    [TAGALOG-FEMALE-1]: salamat po
    [NARRATOR]: thank you
    [TAGALOG-MALE-1]: kumusta unknown_word
    """)
    @patch('pathlib.Path.glob')
    def test_analyze_day_vocabulary(self, mock_glob, mock_file):
        """Test complete day vocabulary analysis."""
        # Mock story file discovery
        from unittest.mock import MagicMock
        mock_story_file = MagicMock()
        mock_story_file.name = 'story_day16.txt'
        mock_glob.return_value = [mock_story_file]
        
        report = self.analyzer.analyze_day_vocabulary(16)
        
        # Verify report structure
        assert 'day' in report
        assert 'story_file' in report
        assert 'total_vocabulary' in report
        assert 'vocabulary_analyses' in report
        assert 'recognition_state_distribution' in report
        assert 'srs_effectiveness_metrics' in report
        
        # Check that words were categorized
        assert report['total_vocabulary'] > 0
        
        # Verify analyses include recognition states
        for analysis in report['vocabulary_analyses']:
            assert 'word' in analysis
            assert 'recognition_state' in analysis
            assert analysis['recognition_state'] in [s.value for s in RecognitionState]
    
    def test_analyze_day_vocabulary_no_story_file(self):
        """Test analysis when no story file is found."""
        with patch('pathlib.Path.glob', return_value=[]):
            report = self.analyzer.analyze_day_vocabulary(999)
            
            assert 'error' in report
            assert 'No story file found' in report['error']
    
    def test_get_srs_data(self):
        """Test SRS data retrieval from database."""
        # Test existing word
        srs_data = self.analyzer._get_srs_data('salamat')
        assert srs_data is not None
        assert srs_data['text'] == 'salamat'
        assert srs_data['stability'] == 3.5
        assert srs_data['review_count'] == 8
        
        # Test non-existing word
        srs_data = self.analyzer._get_srs_data('nonexistent')
        assert srs_data is None
    
    def test_state_distribution_calculation(self):
        """Test recognition state distribution calculation."""
        analyses = [
            VocabularyAnalysis('word1', RecognitionState.HIGH_STABILITY, {}, [], None),
            VocabularyAnalysis('word2', RecognitionState.HIGH_STABILITY, {}, [], None),
            VocabularyAnalysis('word3', RecognitionState.UNKNOWN, {}, [], None),
        ]
        
        distribution = self.analyzer._calculate_state_distribution(analyses)
        
        assert distribution['high_stability'] == 2
        assert distribution['unknown'] == 1
        assert distribution['unstable'] == 0
        assert distribution['dormant'] == 0
        assert distribution['naturally_acquiring'] == 0
        assert distribution['explicitly_learned'] == 0


class TestRecognitionState:
    """Test RecognitionState enum."""
    
    def test_recognition_state_values(self):
        """Test recognition state enum values."""
        assert RecognitionState.UNKNOWN.value == "unknown"
        assert RecognitionState.DORMANT.value == "dormant"
        assert RecognitionState.UNSTABLE.value == "unstable"
        assert RecognitionState.NATURALLY_ACQUIRING.value == "naturally_acquiring"
        assert RecognitionState.EXPLICITLY_LEARNED.value == "explicitly_learned"
        assert RecognitionState.HIGH_STABILITY.value == "high_stability"


class TestVocabularyAnalysis:
    """Test VocabularyAnalysis dataclass."""
    
    def test_vocabulary_analysis_creation(self):
        """Test VocabularyAnalysis dataclass creation."""
        analysis = VocabularyAnalysis(
            word="salamat",
            recognition_state=RecognitionState.HIGH_STABILITY,
            srs_data={'stability': 3.5, 'review_count': 8},
            context_appearances=["restaurant", "greeting"],
            learning_pattern="well_consolidated"
        )
        
        assert analysis.word == "salamat"
        assert analysis.recognition_state == RecognitionState.HIGH_STABILITY
        assert analysis.srs_data['stability'] == 3.5
        assert analysis.context_appearances == ["restaurant", "greeting"]
        assert analysis.learning_pattern == "well_consolidated"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])