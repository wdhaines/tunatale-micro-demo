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
            with pytest.raises(SystemExit) as exc_info:
                CLI().run()
            assert exc_info.value.code == 0
            output = mock_stdout.getvalue()
            # Check for the actual help text that's displayed
            assert "TunaTale Micro-Demo 0.1" in output
            assert "positional arguments:" in output
            assert "generate" in output
            assert "extract" in output
            assert "story" in output
            assert "view" in output


class TestGenerateCommand:
    """Test cases for the 'generate' command."""

    @patch('main.CurriculumGenerator')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('llm_mock.MockLLM.get_response')
    def test_generate_curriculum_success(
        self, mock_llm, mock_stdout, mock_file, mock_curriculum_gen, tmp_path
    ):
        """Test successful curriculum generation."""
        # Setup mock LLM response
        mock_llm.return_value = {
            'choices': [{
                'message': {
                    'content': 'Generated curriculum content'
                }
            }]
        }
        
        # Setup mock curriculum generator
        mock_instance = mock_curriculum_gen.return_value
        mock_instance.generate_curriculum.return_value = "Generated curriculum content"
        
        # Run the command with a mock for the confirmation prompt
        with patch('sys.argv', ['main.py', 'generate', 'Learn Spanish']), \
             patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.mkdir'), \
             patch('json.dump'), \
             patch('builtins.input', return_value='y'):  # Mock user confirmation
            result = CLI().run()
            
        # Verify the result - should return 0 on success
        assert result == 0
        mock_instance.generate_curriculum.assert_called_once_with("Learn Spanish")
        
        # Verify success message
        output = mock_stdout.getvalue()
        assert "Generating curriculum for: Learn Spanish" in output
        assert "Curriculum generated successfully!" in output
        assert "Run 'python main.py view curriculum' to see it." in output

    @patch('sys.stderr', new_callable=io.StringIO)
    def test_generate_validation_error(self, mock_stderr):
        """Test handling of validation errors during generation."""
        with patch('sys.argv', ['main.py', 'generate', '']), \
             patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.mkdir'):
            result = CLI().run()
            
        assert result == 1
        assert "Learning goal must be a non-empty string" in mock_stderr.getvalue()


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

    @patch('main.CLI._handle_story', side_effect=KeyboardInterrupt)
    @patch('sys.stderr', new_callable=io.StringIO)
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_keyboard_interrupt(self, mock_stdout, mock_stderr, mock_handler):
        """Test handling of keyboard interrupt."""
        with patch('sys.argv', ['main.py', 'story', 'test_objective']):
            # The KeyboardInterrupt should be caught by the CLI and return 1
            result = CLI().run()
            
        # Should return 1 on error
        assert result == 1
        # Verify that the handler was called
        mock_handler.assert_called_once()
        # Verify that an error message was printed to stderr
        error_output = mock_stderr.getvalue()
        assert any(msg in error_output 
                 for msg in ["Error:", "Unexpected error:", "Operation cancelled"]), \
               f"Expected error message not found in: {error_output}"
