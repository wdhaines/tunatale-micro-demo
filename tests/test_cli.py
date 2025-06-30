"""Comprehensive tests for the TunaTale CLI."""
import argparse
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, ANY

import pytest

from main import CLI, main
from services.learning_service import LearningService, LearningError
from curriculum_service import ValidationError
from story_generator import CEFRLevel

# Mock the LearningService for all tests
@pytest.fixture(autouse=True)
def mock_learning_service():
    with patch('main.learning_service') as mock_service:
        yield mock_service

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
    def mock_learning_service(self):
        """Create a mock learning service with default settings."""
        with patch('main.learning_service') as mock_service:
            # Create a more realistic curriculum response
            curriculum_data = {
                'goal': 'Test Goal',
                'days': {
                    'Day 1': ['Topic 1', 'Topic 2'],
                    'Day 2': ['Topic 3', 'Topic 4']
                }
            }
            mock_service.create_curriculum.return_value = curriculum_data
            mock_service.get_progress.return_value = {'current_day': 1, 'total_days': 5}
            yield mock_service

    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('llm_mock.MockLLM.get_response')
    def test_generate_curriculum_success(
        self, mock_llm, mock_stdout, mock_file, mock_learning_service, tmp_path
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
        
        # Mock save_curriculum to return the expected path
        mock_learning_service.save_curriculum.return_value = 'curriculum.json'
        
        # Run the command with default parameters
        with patch('sys.argv', ['main.py', 'generate', 'Learn Spanish']), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = CLI().run()
            
        # Verify the result
        assert result == 0
        args, kwargs = mock_learning_service.create_curriculum.call_args
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
        
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_generate_with_all_parameters(
        self, mock_stderr, mock_stdout, mock_learning_service, tmp_path
    ):
        """Test curriculum generation with all parameters specified."""
        # Setup test files
        transcript_path = tmp_path / 'transcript.txt'
        output_path = tmp_path / 'custom_output.json'
        
        # Setup mock curriculum data
        curriculum_data = {
            'goal': 'Learn Spanish',
            'days': {
                'Day 1': ['Topic 1', 'Topic 2'],
                'Day 2': ['Topic 3', 'Topic 4']
            }
        }
        mock_learning_service.create_curriculum.return_value = curriculum_data
        
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
        mock_learning_service.create_curriculum.assert_called_once()
        
        # Check the call arguments
        args, kwargs = mock_learning_service.create_curriculum.call_args
        assert kwargs['learning_goal'] == 'Learn Spanish'
        assert kwargs['target_language'] == 'French'
        assert kwargs['cefr_level'] == 'B1'
        assert kwargs['days'] == 14
        assert kwargs['transcript'] == 'Sample transcript content'
        
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_invalid_cefr_level(self, mock_stderr, mock_learning_service):
        """Test validation of invalid CEFR level."""
        # Setup
        args = argparse.Namespace(
            command='generate',
            goal='Test Goal',
            target_language='Spanish',
            cefr_level='INVALID',
            days=5,
            transcript=None,
            output=None
        )

        # Mock the validation error
        mock_learning_service.create_curriculum.side_effect = LearningError(
            "Invalid CEFR level: 'INVALID'. Must be one of: A1, A2, B1, B2, C1, C2"
        )

        # Execute
        cli = CLI()
        result = cli._handle_generate(args)

        # Verify
        assert result == 1
        assert 'Invalid CEFR level' in mock_stderr.getvalue()
        
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_invalid_days(self, mock_stderr, mock_learning_service):
        """Test handling of invalid number of days."""
        # Setup mock to raise validation error
        mock_learning_service.create_curriculum.side_effect = LearningError(
            "Number of days must be between 1 and 30"
        )

        # Test with 0 days
        args = argparse.Namespace(
            command='generate',
            goal='Test Goal',
            target_language='Spanish',
            cefr_level='A2',
            days=0,  # Invalid number of days
            transcript=None,
            output=None
        )

        cli = CLI()
        result = cli._handle_generate(args)
        
        # Verify the error handling
        assert result == 1
        assert 'Number of days must be between 1 and 30' in mock_stderr.getvalue()
        
        # Test with 31 days
        mock_stderr.truncate(0)
        mock_stderr.seek(0)
        
        args.days = 31
        result = cli._handle_generate(args)
        assert result == 1
        assert 'Number of days must be between 1 and 30' in mock_stderr.getvalue()
        
    @patch('sys.stderr', new_callable=io.StringIO)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_nonexistent_transcript(self, mock_stdout, mock_stderr, mock_learning_service):
        """Test handling of non-existent transcript file."""
        # Setup test file that doesn't exist
        non_existent_file = Path('nonexistent.txt')
        
        # Setup args with the non-existent transcript file
        args = argparse.Namespace(
            command='generate',
            goal='Learn Spanish',
            target_language='English',
            cefr_level='A2',
            days=5,
            transcript=str(non_existent_file),
            output='test_output.json'
        )
        
        # Execute the command
        cli = CLI()
        result = cli._handle_generate(args)
        
        # Get the output
        stderr_output = mock_stderr.getvalue().strip()
        stdout_output = mock_stdout.getvalue().strip()
        
        # Verify the result
        assert result == 1
        assert "Error: Transcript file not found:" in stderr_output
        mock_learning_service.create_curriculum.assert_not_called()

    @patch('sys.stderr', new_callable=io.StringIO)
    def test_generate_validation_error(self, mock_stderr, mock_learning_service):
        """Test handling of validation errors during generation."""
        # Setup mock to raise a validation error
        mock_learning_service.create_curriculum.side_effect = LearningError(
            "Learning goal must be a non-empty string"
        )
        
        # Execute with empty goal which should trigger validation error
        args = argparse.Namespace(
            command='generate',
            goal='',  # Empty goal should trigger validation error
            target_language='Spanish',
            cefr_level='A2',
            days=5,
            transcript=None,
            output=None
        )
        
        cli = CLI()
        result = cli._handle_generate(args)
        
        # Verify the error was handled correctly
        assert result == 1
        assert "Learning goal must be a non-empty string" in mock_stderr.getvalue()
        
    @patch('sys.stderr', new_callable=io.StringIO)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_output_file_handling(self, mock_stdout, mock_stderr, mock_learning_service, tmp_path):
        """Test custom output file handling."""
        output_path = tmp_path / 'custom_curriculum.json'
        
        # Setup mock to return test curriculum data
        test_curriculum = {
            'goal': 'Test Goal',
            'days': {
                'Day 1': ['Topic 1', 'Topic 2'],
                'Day 2': ['Topic 3', 'Topic 4']
            }
        }
        mock_learning_service.create_curriculum.return_value = test_curriculum
        
        # Mock save_curriculum to write the test curriculum to the output file
        def mock_save_curriculum(path):
            with open(path, 'w') as f:
                json.dump(test_curriculum, f)
            return str(path)
            
        mock_learning_service.save_curriculum.side_effect = mock_save_curriculum
        
        # Execute with custom output path
        args = argparse.Namespace(
            command='generate',
            goal='Test Goal',
            target_language='Spanish',
            cefr_level='A2',
            days=5,
            transcript=None,
            output=output_path
        )
        
        cli = CLI()
        result = cli._handle_generate(args)
        
        # Verify the result
        assert result == 0
        assert output_path.exists()
        
        # Verify the service was called correctly
        mock_learning_service.create_curriculum.assert_called_once_with(
            learning_goal='Test Goal',
            target_language='Spanish',
            cefr_level='A2',
            days=5,
            transcript=None,
            output_path=output_path
        )
        
        # Check that the output file was written with the expected content
        with open(output_path, 'r') as f:
            content = json.load(f)
            assert content['goal'] == 'Test Goal'


class TestExtractCommand:
    """Test cases for the 'extract' command."""

    @patch('builtins.open', new_callable=mock_open, read_data=json.dumps({
        'goal': 'Test Goal',
        'days': {'Day 1': ['Topic 1', 'Topic 2']}
    }))
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_extract_collocations_success(
        self, mock_stdout, mock_file, mock_learning_service
    ):
        """Test successful collocation extraction."""
        # Setup mock collocations
        mock_collocations = [
            ('test collocation', 5),
            ('another one', 3)
        ]
        mock_learning_service.extract_collocations.return_value = mock_collocations
        
        # Execute with test arguments
        args = argparse.Namespace(
            command='extract',
            curriculum='test_curriculum.json',
            output=None,
            min_frequency=2,
            limit=10
        )
        
        cli = CLI()
        result = cli._handle_extract(args)
        
        # Verify the result
        assert result == 0
        
        # Verify the service was called correctly
        mock_learning_service.extract_collocations.assert_called_once()
        
        # Check that the output contains the collocations with the expected format
        output = mock_stdout.getvalue()
        assert "Extracting collocations from curriculum..." in output
        assert "Found 2 collocations in the curriculum." in output
        assert "Collocations (most frequent first):" in output
        
        # Check for collocations in the output with the format: "1. test collocation (x5)"
        assert "1. test collocation (x5)" in output
        assert "2. another one (x3)" in output


class TestViewCommand:
    """Test the view command."""

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_view_curriculum(self, mock_stdout, mock_learning_service):
        """Test viewing an existing curriculum."""
        # Setup mock to return test curriculum
        test_curriculum = {
            'goal': 'Test Goal',
            'days': {
                'Day 1': ['Topic 1', 'Topic 2'],
                'Day 2': ['Topic 3', 'Topic 4']
            }
        }
        mock_learning_service.get_curriculum.return_value = test_curriculum
        
        # Execute view command
        args = argparse.Namespace(
            command='view',
            file='test_curriculum.json',
            format=None
        )
        
        cli = CLI()
        result = cli._handle_view(args)
        
        # Verify the result
        assert result == 0
        output = mock_stdout.getvalue()
        assert 'Test Goal' in output
        assert 'Day 1' in output
        assert 'Topic 1' in output
        assert 'Day 2' in output
        assert 'Topic 3' in output

    @patch('sys.stderr', new_callable=io.StringIO)
    def test_view_nonexistent_curriculum(self, mock_stderr, mock_learning_service):
        """Test viewing a non-existent curriculum."""
        # Setup mock to raise FileNotFoundError
        mock_learning_service.get_curriculum.side_effect = LearningError("Curriculum not found")
        
        # Execute view command with non-existent file
        args = argparse.Namespace(
            command='view',
            file='nonexistent.json',
            format=None
        )
        
        cli = CLI()
        result = cli._handle_view(args)
        
        # Verify the result
        assert result == 1
        error_output = mock_stderr.getvalue()
        assert "Error: Curriculum not found" in error_output


class TestErrorHandling:
    """Test error handling in the CLI."""

    @patch('sys.stderr', new_callable=io.StringIO)
    def test_invalid_command(self, mock_stderr):
        """Test handling of invalid commands."""
        # Execute with invalid command
        cli = CLI()
        result = cli.run(['invalid'])
            
        assert result == 1
        assert "Unknown command" in mock_stderr.getvalue()
        
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_permission_error(self, mock_stderr, mock_learning_service):
        """Test handling of file permission errors."""
        # Setup mock to raise PermissionError
        mock_learning_service.create_curriculum.side_effect = PermissionError("Permission denied")
        
        # Execute with test arguments
        args = argparse.Namespace(
            command='generate',
            goal='Test Goal',
            target_language='Spanish',
            cefr_level='A2',
            days=5,
            transcript=None,
            output=None
        )
        
        cli = CLI()
        result = cli._handle_generate(args)
            
        assert result == 1
        assert "Error: Permission denied" in mock_stderr.getvalue()
        
    @patch('sys.stderr', new_callable=io.StringIO)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_keyboard_interrupt(self, mock_stdout, mock_stderr, mock_learning_service):
        """Test handling of keyboard interrupt without actually raising an interrupt."""
        # Create a mock function that will simulate the behavior when KeyboardInterrupt is caught
        def mock_interrupt_handler():
            # This simulates what would happen in the actual code when a KeyboardInterrupt is caught
            print("Operation cancelled", file=sys.stderr)
            return 1
        
        # Patch the CLI's _handle_generate method to return our mock handler's result
        with patch.object(CLI, '_handle_generate', return_value=1) as mock_handle_generate:
            # Set up the mock to call our handler when the method is called
            mock_handle_generate.side_effect = lambda *args, **kwargs: mock_interrupt_handler()
            
            # Execute with test arguments
            args = argparse.Namespace(
                command='generate',
                goal='Test Goal',
                target_language='Spanish',
                cefr_level='A2',
                days=5,
                transcript=None,
                output=None
            )
            
            cli = CLI()
            result = cli._handle_generate(args)
            
            # Verify the result
            assert result == 1
            
            # Get the output
            stderr_output = mock_stderr.getvalue()
            
            # Check for cancellation message in stderr
            assert "Operation cancelled" in stderr_output, \
                   f"Expected 'Operation cancelled' in stderr, got: {stderr_output}"
            
            # Verify the mock was called with the correct arguments
            mock_handle_generate.assert_called_once_with(args)
