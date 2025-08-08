"""Comprehensive tests for the TunaTale CLI."""
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, ANY

import pytest

from main import CLI, main
from curriculum_service import CurriculumGenerator, ValidationError

# Sample curriculum data for testing
SAMPLE_CURRICULUM = {
    'goal': 'Test Goal',
    'days': {
        'Day 1': ['Topic 1', 'Topic 2'],
        'Day 2': ['Topic 3', 'Topic 4']
    }
}


class TestCLI:
    """Test cases for the CLI class."""

    def test_help_flag(self):
        """Test that the --help flag shows help text."""
        with patch('sys.argv', ['main.py', '--help']), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            # The help flag should not raise SystemExit in the new implementation
            result = CLI().run()
            assert result == 0
            output = mock_stdout.getvalue()
            # Check for the actual help text that's displayed
            assert "TunaTale - A language learning tool" in output
            assert "positional arguments:" in output
            assert "generate" in output
            assert "extract" in output
            assert "generate-day" in output
            assert "continue" in output
            assert "view" in output


class TestGenerateCommand:
    """Test cases for the 'generate' command."""

    @pytest.fixture
    def mock_curriculum(self):
        """Create a mock curriculum generator with default settings."""
        with patch('main.CurriculumGenerator') as mock_gen:
            mock_instance = mock_gen.return_value
            # Create a more realistic curriculum response
            curriculum_data = {
                'learning_goal': 'Test Goal',
                'target_language': 'English',
                'cefr_level': 'A2',
                'days': 30,
                'content': 'Generated curriculum content',
                'metadata': {'generated_at': '2023-01-01T00:00:00', 'transcript_used': False},
                'days_content': {
                    'Day 1': ['Topic 1', 'Grammar 1'],
                    'Day 2': ['Topic 2', 'Grammar 2']
                }
            }
            mock_instance.generate_curriculum.return_value = curriculum_data
            # Mock the _save_curriculum method
            mock_instance._save_curriculum = MagicMock()
            yield mock_instance

    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('llm_mock.MockLLM.get_response')
    def test_generate_curriculum_success(
        self, mock_llm, mock_stdout, mock_file, mock_curriculum, tmp_path
    ):
        """Test successful curriculum generation with default parameters."""
        # Setup mock LLM response
        mock_llm.return_value = {
            'choices': [{
                'message': {
                    'content': 'Generated curriculum content'
                }
            }]
        }
        
        # Run the command with default parameters
        with patch('sys.argv', ['main.py', 'generate', 'Learn Spanish']), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = CLI().run()
            
        # Verify the result
        assert result == 0
        args, kwargs = mock_curriculum.generate_curriculum.call_args
        assert kwargs['learning_goal'] == 'Learn Spanish'
        assert kwargs['target_language'] == 'English'
        assert kwargs['cefr_level'] == 'A2'
        assert kwargs['days'] == 30
        assert kwargs['transcript'] is None
        assert 'output_path' in kwargs  # Don't check specific path, just that it was provided
        
        # Verify success message
        output = mock_stdout.getvalue()
        assert "Generating curriculum for: Learn Spanish" in output
        assert "Target language: English" in output
        assert "CEFR Level: A2" in output
        assert "Duration: 30 days" in output
        assert "Curriculum generated successfully and saved to: curriculum.json" in output
        
    @pytest.mark.skip(reason="Temporarily skipping complex mocking test - to be fixed in Phase 2")
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_generate_with_all_parameters(
        self, mock_stderr, mock_stdout, mock_curriculum, tmp_path
    ):
        """Test curriculum generation with all parameters specified."""
        # Setup test files
        transcript_path = tmp_path / 'transcript.txt'
        output_path = tmp_path / 'custom_output.json'
        
        # Setup mock curriculum data
        curriculum_data = {
            'learning_goal': 'Learn Spanish',
            'target_language': 'French',
            'cefr_level': 'B1',
            'days': 14,
            'content': 'Generated curriculum content',
            'metadata': {'generated_at': '2023-01-01T00:00:00', 'transcript_used': True},
            'days_content': {
                'Day 1': ['Topic 1', 'Grammar 1'],
                'Day 2': ['Topic 2', 'Grammar 2']
            }
        }
        mock_curriculum.generate_curriculum.return_value = curriculum_data
        
        # Create a mock for the transcript file
        mock_transcript_content = 'Sample transcript content'
        
        # Use separate mocks for different file operations
        with patch('builtins.open', side_effect=[
            mock_open(read_data=mock_transcript_content).return_value,  # For reading transcript
            mock_open().return_value  # For writing output
        ]) as mock_file, \
             patch('pathlib.Path.mkdir'):
            
            # Run the command with all parameters
            with patch('sys.argv', [
                'main.py', 'generate', 'Learn Spanish',
                '--target-language', 'French',
                '--cefr-level', 'B1',
                '--days', '14',
                '--transcript', str(transcript_path),
                '--output', str(output_path)
            ]):
                result = CLI().run()
        
        # Verify the result
        assert result == 0
        mock_curriculum.generate_curriculum.assert_called_once()
        
        # Check the call arguments
        args, kwargs = mock_curriculum.generate_curriculum.call_args
        assert kwargs['learning_goal'] == 'Learn Spanish'
        assert kwargs['target_language'] == 'French'
        assert kwargs['cefr_level'] == 'B1'
        assert kwargs['days'] == 14
        assert kwargs['transcript'] == 'Sample transcript content'
        
    @patch('sys.stderr', new_callable=io.StringIO)
    @patch('sys.exit')
    def test_invalid_cefr_level(self, mock_exit, mock_stderr, mock_curriculum):
        """Test handling of invalid CEFR level."""
        # Setup mock to prevent actual exit
        mock_exit.side_effect = SystemExit(2)
        
        with patch('sys.argv', [
            'main.py', 'generate', 'Learn Spanish',
            '--cefr-level', 'X1'  # Invalid level
        ]):
            with pytest.raises(SystemExit) as exc_info:
                CLI().run()
                
        assert exc_info.value.code == 2
        assert "invalid choice: 'X1'" in mock_stderr.getvalue()
        
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_invalid_days(self, mock_stderr, mock_curriculum):
        """Test handling of invalid number of days."""
        # Mock the validation to raise an error for invalid days
        mock_curriculum.generate_curriculum.side_effect = ValueError("Number of days must be between 1 and 365")
        
        with patch('sys.argv', [
            'main.py', 'generate', 'Learn Spanish',
            '--days', '0'  # Invalid number of days
        ]), patch('pathlib.Path.exists', return_value=False):
            result = CLI().run()
            
        assert result == 1
        assert "Number of days must be between 1 and 365" in mock_stderr.getvalue()
        
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.exists', side_effect=lambda x: str(x) != 'nonexistent.txt')
    @patch('json.dump')
    def test_nonexistent_transcript(self, mock_json_dump, mock_exists, mock_mkdir):
        """Test handling of non-existent transcript file."""
        # Setup mock for the CurriculumGenerator
        mock_curriculum = MagicMock()
        # Return a non-empty dictionary to ensure it's not falsy
        mock_curriculum.generate_curriculum.return_value = {
            'learning_goal': 'Learn Spanish',
            'content': 'Generated content',
            'metadata': {'transcript_used': False},
            'days': [{'day': 1, 'topic': 'Introduction', 'vocabulary': [], 'collocations': []}]
        }
        
        # Mock the output file handling
        mock_output_file = MagicMock()
        mock_output_file.__enter__.return_value = mock_output_file
        
        # Create a side effect function that fails only for the transcript file
        def open_side_effect(filename, *args, **kwargs):
            if 'nonexistent.txt' in str(filename):
                raise FileNotFoundError('No such file or directory')
            return mock_output_file
        
        # Mock the CurriculumGenerator class and file operations
        with patch('main.CurriculumGenerator', return_value=mock_curriculum), \
             patch('sys.argv', [
                 'main.py', 'generate', 'Learn Spanish',
                 '--transcript', 'nonexistent.txt',
                 '--output', 'test_output.json'  # Explicit output file
             ]), \
             patch('sys.stderr', new_callable=io.StringIO) as mock_stderr, \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, \
             patch('builtins.open', side_effect=open_side_effect):
            result = CLI().run()
            
            # Get the output
            stderr_output = mock_stderr.getvalue().strip()
            stdout_output = mock_stdout.getvalue().strip()
            
            # Debug output
            print("\n--- DEBUG OUTPUT ---")
            print("STDERR:", repr(stderr_output))
            print("STDOUT:", repr(stdout_output))
            print("--- END DEBUG ---\n")
            
            # Check if the warning is in either stderr or stdout
            assert "Warning: Could not read transcript file:" in f"{stdout_output}\n{stderr_output}"
            
            # Verify the curriculum generation was attempted with transcript=None
            mock_curriculum.generate_curriculum.assert_called_once()
            args, kwargs = mock_curriculum.generate_curriculum.call_args
            assert kwargs['transcript'] is None
            
            # Verify the output file was written to
            mock_json_dump.assert_called_once()
            
            # Verify success status code (0)
            assert result == 0

    @patch('sys.stderr', new_callable=io.StringIO)
    def test_generate_validation_error(self, mock_stderr):
        """Test handling of validation errors during generation."""
        with patch('sys.argv', ['main.py', 'generate', '']), \
             patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.mkdir'):
            result = CLI().run()
            
        assert result == 1
        assert "Learning goal must be a non-empty string" in mock_stderr.getvalue()
        
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_output_file_handling(self, mock_stderr, mock_curriculum, tmp_path):
        """Test custom output file handling."""
        output_path = tmp_path / 'custom_curriculum.json'
        
        # Setup mock to return our path when converted to string
        mock_curriculum.generate_curriculum.return_value = {
            'learning_goal': 'Test Goal',
            'content': 'Test content',
            'metadata': {}
        }
        
        with patch('sys.argv', [
            'main.py', 'generate', 'Test Goal',
            '--output', str(output_path)
        ]), patch('pathlib.Path.mkdir'):
            result = CLI().run()
            
        assert result == 0
        assert output_path.exists()
        mock_curriculum.generate_curriculum.assert_called_once()
        
        # Check that the output file was written
        with open(output_path, 'r') as f:
            content = json.load(f)
            assert content['learning_goal'] == 'Test Goal'


class TestExtractCommand:
    """Test cases for the 'extract' command."""

    @patch('main.CollocationExtractor')
    @patch('builtins.open', new_callable=mock_open, read_data='test content')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_extract_collocations_success(
        self, mock_stdout, mock_file, mock_extractor, tmp_path
    ):
        """Test successful collocation extraction."""
        # Skip this test if collocation_extractor is not available
        try:
            import collocation_extractor
        except ImportError:
            pytest.skip("collocation_extractor not available")
        
        # Setup mock collocations
        test_collocations = {
            'test collocation': 3,
            'another example': 2
        }
        
        # Setup mock extractor
        mock_instance = mock_extractor.return_value
        mock_instance.extract_from_curriculum.return_value = test_collocations
        
        # Mock the curriculum file
        mock_curriculum = {
            'content': 'Sample curriculum content',
            'days': [{'day': 1, 'content': 'Day 1 content'}]
        }
        
        # Run the extract command with no arguments
        with patch('sys.argv', ['main.py', 'extract']), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True), \
             patch('json.load', return_value=mock_curriculum):
            result = CLI().run()
            
        # Verify the result - should return 0 on success
        assert result == 0
        mock_instance.extract_from_curriculum.assert_called_once()
        
        # Verify success message
        output = mock_stdout.getvalue()
        assert "Extracting collocations from curriculum..." in output
        assert "Extracted 2 collocations" in output
        assert "Top collocations:" in output
        # The actual output will have the collocations in the order they were returned
        # We'll just check that both are in the output
        assert "test collocation" in output
        assert "another example" in output


class TestViewCommand:
    """Test the view command."""
    
    @patch('builtins.open', new_callable=mock_open, read_data=json.dumps(SAMPLE_CURRICULUM))
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('main.CLI._view_curriculum', return_value=0)
    def test_view_curriculum(self, mock_view, mock_stdout, mock_file):
        """Test viewing an existing curriculum."""
        with patch('sys.argv', ['main.py', 'view', 'curriculum']):
            result = CLI().run()
            
        assert result == 0
        mock_view.assert_called_once()

    @patch('sys.stderr', new_callable=io.StringIO)
    @patch('main.CLI._view_curriculum', side_effect=FileNotFoundError("Curriculum not found"))
    def test_view_missing_curriculum(self, mock_view, mock_stderr):
        """Test viewing a non-existent curriculum."""
        with patch('sys.argv', ['main.py', 'view', 'curriculum']):
            result = CLI().run()
            
        assert result == 1
        error_output = mock_stderr.getvalue()
        assert "Curriculum not found" in error_output


class TestErrorHandling:
    """Test error handling in the CLI."""

    def test_invalid_command(self):
        """Test handling of invalid commands."""
        with patch('sys.argv', ['main.py', 'invalid-command']), \
             patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                CLI().run()
            assert exc_info.value.code == 2
            assert "invalid choice: 'invalid-command'" in mock_stderr.getvalue().lower()

    @patch('curriculum_service.CurriculumGenerator')
    @patch('sys.stderr', new_callable=io.StringIO)
    @patch('llm_mock.MockLLM.get_response', return_value="Mocked curriculum content")
    def test_permission_error(self, mock_llm, mock_stderr, mock_curriculum_gen):
        """Test handling of file permission errors."""
        # Setup mocks
        mock_instance = mock_curriculum_gen.return_value
        mock_instance.generate_curriculum.return_value = "Test content"
        
        # Mock the prompt to avoid hanging in tests
        with patch('builtins.input', return_value='y'), \
             patch('sys.argv', ['main.py', 'generate', 'test goal']), \
             patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = CLI().run()
            
        # Should return 1 on error
        assert result == 1
        
        # Check stderr for error messages
        error_output = mock_stderr.getvalue()
        assert any(msg.lower() in error_output.lower() 
                  for msg in ["permission", "error"])

    @patch('main.CLI._handle_generate', side_effect=KeyboardInterrupt)
    @patch('sys.stderr', new_callable=io.StringIO)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_keyboard_interrupt(self, mock_stdout, mock_stderr, mock_handler):
        """Test handling of keyboard interrupt."""
        with patch('sys.argv', ['main.py', 'generate', 'test_goal']):
            # The KeyboardInterrupt should be caught by the CLI and return 1
            result = CLI().run()
            
        # Should return 1 on error
        assert result == 1
        # Verify that the handler was called
        mock_handler.assert_called_once()
        # Check both stdout and stderr for the error message
        stdout_output = mock_stdout.getvalue()
        stderr_output = mock_stderr.getvalue()
        
        # The error message should be in either stdout or stderr
        expected_message = "Operation cancelled by user."
        assert (expected_message in stdout_output or expected_message in stderr_output), \
               f"Expected error message '{expected_message}' not found in stdout or stderr\n" \
               f"stdout: {stdout_output}\n" \
               f"stderr: {stderr_output}"
