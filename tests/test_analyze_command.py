"""Tests for the analyze command in main.py."""
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest

from main import CLI


class TestAnalyzeCommand:
    """Test cases for the 'analyze' command."""

    @pytest.fixture
    def mock_extractor(self):
        """Create a mock collocation extractor with sample analysis results."""
        with patch('main.CollocationExtractor') as mock_extractor_cls:
            mock_instance = mock_extractor_cls.return_value
            
            # Create a custom mock class that handles comparison operations
            class MockResult(dict):
                def __init__(self, data):
                    super().__init__(data)
                    self._data = data
                    
                def __lt__(self, other):
                    return False
                
                def __gt__(self, other):
                    return True
                    
                def __getitem__(self, key):
                    return self._data[key]
                    
                def get(self, key, default=None):
                    return self._data.get(key, default)
                    
                def items(self):
                    return self._data.items()
            
            # Mock the vocabulary analysis to return different results based on input
            def mock_analyze(text):
                if not text.strip():
                    return MockResult({
                        'total_words': 0,
                        'unique_words_count': 0,
                        'background_words': 0,
                        'background_percentage': 0.0,
                        'new_content_words': 0,
                        'avg_word_length': 0.0,
                        'top_new_words': [],
                        'collocations': {},
                        'unique_new_words': []
                    })
                elif "carnivorous" in text.lower():
                    return MockResult({
                        'total_words': 100,
                        'unique_words_count': 50,
                        'background_words': 70,
                        'background_percentage': 70.0,
                        'new_content_words': 30,
                        'avg_word_length': 5.5,
                        'top_new_words': ['plant', 'carnivorous', 'trap', 'insect', 'digest'],
                        'collocations': {
                            'carnivorous plant': 5,
                            'trap insects': 4,
                            'digest prey': 3,
                        },
                        'unique_new_words': ['plant', 'carnivorous', 'trap', 'insect', 'digest', 'prey']
                    })
                else:  # For other test cases
                    return MockResult({
                        'total_words': 50,
                        'unique_words_count': 30,
                        'background_words': 35,
                        'background_percentage': 70.0,
                        'new_content_words': 15,
                        'avg_word_length': 5.0,
                        'top_new_words': ['test', 'story', 'plants'],
                        'collocations': {
                            'test story': 2,
                            'carnivorous plants': 2,
                        },
                        'unique_new_words': ['test', 'story', 'plants', 'carnivorous']
                    })
            
            mock_instance.analyze_vocabulary_distribution.side_effect = mock_analyze
            yield mock_instance

    def test_analyze_file(self, mock_extractor, capsys, tmp_path):
        """Test analyzing a file with the analyze command."""
        # Setup - create a temporary file
        test_file = tmp_path / "test_curriculum.json"
        test_content = "Carnivorous plants are fascinating because they can trap and digest insects."
        test_file.write_text(test_content)
        
        # Execute
        cli = CLI()
        args = MagicMock()
        args.file_or_text = str(test_file)
        args.verbose = False
        args.min_word_len = 3
        args.top_words = 20
        args.top_collocations = 20
        args.day = None
        
        # Mock file operations
        with patch('builtins.open', mock_open(read_data=test_content)) as mock_file:
            result = cli._handle_analyze(args)
            
            # Verify file was opened with correct arguments
            mock_file.assert_called_once()
            call_args = mock_file.call_args[0]
            assert str(call_args[0]) == str(test_file)  # Handle Path vs string
            assert call_args[1] == 'r'
            assert 'encoding' in mock_file.call_args[1]
            assert mock_file.call_args[1]['encoding'] == 'utf-8'
        
        # Verify
        assert result == 0
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that the output contains expected elements
        assert "VOCABULARY ANALYSIS" in output
        assert "Total words:" in output
        assert "100" in output  # From our mock data
        
        # Verify the extractor was called with the file content
        mock_extractor.analyze_vocabulary_distribution.assert_called_once()
        call_args = mock_extractor.analyze_vocabulary_distribution.call_args[0][0]
        assert "Carnivorous plants" in call_args

    def test_analyze_direct_text(self, mock_extractor, capsys):
        """Test analyzing direct text input with the analyze command."""
        # Setup
        test_text = "Carnivorous plants are fascinating because they can trap and digest insects."
        
        # Execute
        cli = CLI()
        args = MagicMock()
        args.file_or_text = test_text
        args.verbose = False
        args.min_word_len = 3
        args.top_words = 5
        args.top_collocations = 5
        args.day = None
        
        result = cli._handle_analyze(args)
        
        # Verify
        assert result == 0
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that the output contains expected elements
        assert "VOCABULARY ANALYSIS" in output
        assert "Total words:" in output
        assert "100" in output  # From our mock data
        
        # Verify the extractor was called with the direct text
        mock_extractor.analyze_vocabulary_distribution.assert_called_once_with(test_text)

    def test_analyze_verbose_output(self, mock_extractor, capsys):
        """Test verbose output shows all unique words."""
        # Setup test data
        test_text = "Carnivorous plants are fascinating because they can trap and digest insects."
        
        # Create a proper mock result dictionary
        mock_result = {
            'total_words': 100,
            'unique_words_count': 50,
            'background_words': 70,
            'background_percentage': 70.0,
            'new_content_words': 30,
            'avg_word_length': 5.5,
            'top_new_words': ['plant', 'carnivorous', 'trap', 'insect', 'digest'],
            'collocations': {
                'carnivorous plant': 5,
                'trap insects': 4,
                'digest prey': 3,
            },
            'unique_new_words': ['plant', 'carnivorous', 'trap', 'insect', 'digest', 'prey']
        }
        
        # Configure the mock to return our test result
        mock_extractor.analyze_vocabulary_distribution.return_value = mock_result
        
        # Execute with verbose flag
        cli = CLI()
        args = MagicMock()
        args.file_or_text = test_text
        args.verbose = True  # Enable verbose output
        args.min_word_len = 3
        args.top_words = 5
        args.top_collocations = 5
        args.day = None
        
        # Patch print to capture output
        with patch('builtins.print') as mock_print:
            result = cli._handle_analyze(args)
            
            # Verify the result code
            assert result == 0, f"Expected return code 0, got {result}"
            
            # Get all printed output as a single string
            output = "\n".join(str(call[0][0]) if call[0] else "" 
                              for call in mock_print.call_args_list)
            
            # Check that verbose output includes the unique words section
            assert "ALL UNIQUE NEW WORDS" in output
            assert "carnivorous" in output
            assert "plant" in output
            assert "trap" in output
        
        # Verify the extractor was called with the correct parameters
        mock_extractor.analyze_vocabulary_distribution.assert_called_once_with(test_text)

    def test_analyze_nonexistent_file(self, capsys):
        """Test handling of non-existent file."""
        # Setup
        non_existent_file = "nonexistent.json"
        
        # Execute
        cli = CLI()
        args = MagicMock()
        args.file_or_text = non_existent_file
        args.verbose = False
        args.min_word_len = 3
        args.top_words = 20
        args.top_collocations = 20
        
        with patch('pathlib.Path.exists', return_value=False):
            result = cli._handle_analyze(args)
        
        # Verify
        assert result == 1  # Should indicate error
        captured = capsys.readouterr()
        error_output = captured.err
        
        assert "Error during analysis" in error_output

    def test_analyze_empty_file(self, mock_extractor, capsys, tmp_path):
        """Test handling of empty file."""
        # Setup - create an empty temporary file
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("")
        
        # Create a proper mock result dictionary
        mock_result = {
            'total_words': 0,
            'unique_words_count': 0,
            'background_words': 0,
            'background_percentage': 0.0,
            'new_content_words': 0,
            'avg_word_length': 0.0,
            'top_new_words': [],
            'collocations': {},
            'unique_new_words': []
        }
        
        # Configure the mock to return our test result
        mock_extractor.analyze_vocabulary_distribution.return_value = mock_result
        
        # Execute
        cli = CLI()
        args = MagicMock()
        args.file_or_text = str(empty_file)
        args.verbose = False
        args.min_word_len = 3
        args.top_words = 20
        args.top_collocations = 20
        args.day = None  # Explicitly test file-based analysis
        
        # Mock file operations to return empty content
        with patch('builtins.open', mock_open(read_data="")) as mock_file, \
             patch('builtins.print') as mock_print:
            
            # Call the method under test
            result = cli._handle_analyze(args)
            
            # Verify the result code
            assert result == 0, f"Expected return code 0, got {result}"
            
            # Verify file was opened with correct arguments
            mock_file.assert_called_once()
            call_args = mock_file.call_args[0]
            assert str(call_args[0]) == str(empty_file)  # Handle Path vs string
            assert call_args[1] == 'r'
            assert 'encoding' in mock_file.call_args[1]
            assert mock_file.call_args[1]['encoding'] == 'utf-8'
            
            # Get all print calls and join their arguments
            output_lines = []
            for call in mock_print.call_args_list:
                if call[0]:  # If there are positional arguments
                    output_lines.append(str(call[0][0]))
            output = "\n".join(output_lines)
            
            # Check that the warning message is in the output
            assert "Warning: File is empty, showing empty analysis" in output
            
            # Check that the analysis header is in the output
            assert "VOCABULARY ANALYSIS" in output
            
            # Check that the summary shows 0 words
            assert "Total words:" in output
            assert "0" in output
        
    def test_analyze_by_day_number(self, mock_extractor, capsys, tmp_path, monkeypatch):
        """Test analyzing by day number."""
        # Setup - create a test story file that would be found by day number
        test_content = "This is a test story about carnivorous plants."
        test_dir = tmp_path / "stories"
        test_dir.mkdir()
        story_file = test_dir / "story_day01_venus_flytrap.txt"
        story_file.write_text(test_content)
        
        # Mock Path.glob to return our test file
        def mock_glob(pattern):
            if "day01" in pattern:
                return [story_file]
            return []
            
        monkeypatch.setattr("pathlib.Path.glob", lambda self, pattern: mock_glob(pattern))
        
        # Execute
        cli = CLI()
        args = MagicMock()
        args.file_or_text = ""  # Empty for day-based analysis
        args.day = 1
        args.verbose = False
        args.min_word_len = 3
        args.top_words = 20
        args.top_collocations = 20
        
        result = cli._handle_analyze(args)
        
        # Verify
        assert result == 0
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that day-based analysis was performed
        assert "Day 1 story" in output
        assert "VOCABULARY ANALYSIS" in output
        
    def test_analyze_by_day_number_not_found(self, mock_extractor, capsys, monkeypatch):
        """Test handling of non-existent day number."""
        # Mock Path.glob to return no files
        monkeypatch.setattr("pathlib.Path.glob", lambda self, pattern: [])
        
        # Execute with non-existent day
        cli = CLI()
        args = MagicMock()
        args.file_or_text = ""
        args.day = 99  # Non-existent day
        args.verbose = False
        args.min_word_len = 3
        args.top_words = 20
        args.top_collocations = 20
        
        result = cli._handle_analyze(args)
        
        # Verify
        assert result == 1  # Should indicate error
        captured = capsys.readouterr()
        error_output = captured.err
        
        assert "No file found for day 99" in error_output
        
    def test_analyze_by_day_with_verbose(self, mock_extractor, capsys, tmp_path, monkeypatch):
        """Test verbose output with day-based analysis."""
        # Setup - create a test story file
        test_content = "This is a verbose test story about carnivorous plants."
        test_dir = tmp_path / "stories"
        test_dir.mkdir()
        story_file = test_dir / "story_day02_swamp_adventure.txt"
        story_file.write_text(test_content)
        
        # Mock Path.glob to return our test file
        def mock_glob(pattern):
            if "day02" in pattern:
                return [story_file]
            return []
            
        monkeypatch.setattr("pathlib.Path.glob", lambda self, pattern: mock_glob(pattern))
        
        # Execute with verbose flag
        cli = CLI()
        args = MagicMock()
        args.file_or_text = ""
        args.day = 2
        args.verbose = True  # Enable verbose output
        args.min_word_len = 3
        args.top_words = 5
        args.top_collocations = 5
        
        result = cli._handle_analyze(args)
        
        # Verify
        assert result == 0
        captured = capsys.readouterr()
        output = captured.out
        
        # Check verbose output elements
        assert "Day 2 story" in output
        assert "ALL UNIQUE NEW WORDS" in output
        assert "VOCABULARY ANALYSIS" in output
        
    def test_analyze_mutually_exclusive_args(self, mock_extractor, capsys):
        """Test that file/text and --day are mutually exclusive."""
        # This is more of an integration test for the argument parser
        cli = CLI()
        parser = cli._create_parser()
        
        # Should work with just file/text
        args = parser.parse_args(["analyze", "test.txt"])
        assert args.file_or_text == "test.txt"
        assert not hasattr(args, 'day') or args.day is None
        
        # Should work with just --day
        args = parser.parse_args(["analyze", "--day", "1"])
        assert args.day == 1
        assert args.file_or_text == ""
        
        # Should raise error with both (handled by argparse)
        with pytest.raises(SystemExit):
            parser.parse_args(["analyze", "test.txt", "--day", "1"])
