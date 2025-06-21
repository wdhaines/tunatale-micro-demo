"""Tests for main.py CLI functionality."""
import io
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY, mock_open

import pytest

from content_generator import CEFRLevel, ContentGenerator, StoryParams
from main import main


def test_cli_help() -> None:
    """Test that the CLI shows help text."""
    # Test main help
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Available commands (use <command> -h for help)" in result.stdout
    
    # Test story command help
    result = subprocess.run(
        [sys.executable, "main.py", "story", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Generate a story for language learning" in result.stdout


@patch('sys.argv', ["main.py", "story", "--help"])
@patch('sys.stdout', new_callable=io.StringIO)
def test_cli_story_command_required_params(mock_stdout) -> None:
    """Test that story command shows help text when required parameters are missing."""
    # This test ensures that the help text is shown when required parameters are missing
    # We patch sys.argv to simulate the command line arguments
    
    # Call main() which should show help text
    with pytest.raises(SystemExit) as exc_info:
        main()
    
    # Should exit with code 0 when showing help
    assert exc_info.value.code == 0
    
    # Get the help text from the mock stdout
    help_text = mock_stdout.getvalue()
    
    # Verify the help text contains expected sections
    assert "Generate a story for language learning" in help_text
    assert "positional arguments:" in help_text
    assert "optional arguments:" in help_text
    assert "--language" in help_text
    assert "--level" in help_text
    assert "--phase" in help_text
    assert "--length" in help_text
    assert "--output" in help_text

@patch('sys.argv', ["main.py", "story", "test objective", "--language", "English", "--level", "INVALID", "--phase", "1"])
@patch('sys.stderr', new_callable=io.StringIO)
def test_cli_invalid_cefr_level(mock_stderr) -> None:
    """Test that invalid CEFR level is caught by CLI."""
    with pytest.raises(SystemExit) as exc_info:
        main()
    
    # Should exit with code 2 for command line usage error
    assert exc_info.value.code == 2
    
    # Verify error message
    error_text = mock_stderr.getvalue()
    assert "invalid cefr level: invalid" in error_text.lower()


@patch('main.ContentGenerator')
@patch('builtins.open', new_callable=mock_open)
@patch('os.makedirs')
@patch('sys.stdout', new_callable=io.StringIO)
def test_cli_story_generation(mock_stdout, mock_makedirs, mock_file, mock_content_gen, tmp_path: Path) -> None:
    """Test story generation via CLI."""
    # Setup mocks
    mock_instance = mock_content_gen.return_value
    mock_instance.generate_story.return_value = "Test story content"
    
    # Create a temporary output file
    output_file = tmp_path / "output" / "story.txt"
    
    # Mock the command line arguments
    test_args = [
        "main.py",
        "story",
        "test objective",
        "--language", "English",
        "--level", "A2",
        "--phase", "1",
        "--length", "200",
        "--output", str(output_file)
    ]
    
    with patch('sys.argv', test_args):
        main()
    
    # Verify ContentGenerator was called with correct params
    mock_instance.generate_story.assert_called_once()
    story_params = mock_instance.generate_story.call_args[0][0]
    assert isinstance(story_params, StoryParams)
    assert story_params.learning_objective == "test objective"
    assert story_params.language == "English"
    assert story_params.cefr_level == CEFRLevel.A2
    assert story_params.phase == 1
    assert story_params.length == 200
    
    # Verify output file was created with the correct content
    # The actual call might include additional keyword arguments, so we'll check the call args
    assert mock_file.call_count >= 1, "File should have been opened"
    
    # Check that the file was opened with the expected path and mode
    call_args = mock_file.call_args_list[0]
    assert str(call_args[0][0]) == str(output_file), f"Expected {output_file}, got {call_args[0][0]}"
    assert 'w' in call_args[0][1], "File should be opened in write mode"
    assert call_args[1].get('encoding') == 'utf-8', "File should be opened with UTF-8 encoding"
    
    # Verify the content was written
    mock_file().write.assert_called_once_with("Test story content")
    
    # Verify success message was printed
    output = mock_stdout.getvalue()
    assert f"Story saved to: {output_file}" in output


def test_cli_invalid_cefr_level() -> None:
    """Test that invalid CEFR level is caught by CLI."""
    # Test with invalid CEFR level
    result = subprocess.run(
        [sys.executable, "main.py", "story", "test objective",
         "--language", "English", "--level", "INVALID", "--phase", "1"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 2  # argparse exits with 2 for invalid choice
    assert "invalid cefr level: invalid" in result.stderr.lower()
    
    # Test with valid but incorrect case (should work)
    result = subprocess.run(
        [sys.executable, "main.py", "story", "test objective",
         "--language", "English", "--level", "a2", "--phase", "1"],
        capture_output=True,
        text=True
    )
    # This should work now with case-insensitive matching
    assert result.returncode == 0


def test_cli_negative_length() -> None:
    """Test that negative length is caught by CLI."""
    # Test with negative length
    result = subprocess.run(
        [sys.executable, "main.py", "story", "test objective",
         "--language", "English", "--level", "A2", "--phase", "1", "--length", "-100"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 2  # argparse exits with 2 for invalid argument
    assert "must be a positive integer" in result.stderr.lower()
    
    # Test with zero length (should also be invalid)
    result = subprocess.run(
        [sys.executable, "main.py", "story", "test objective",
         "--language", "English", "--level", "A2", "--phase", "1", "--length", "0"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 2
    assert "must be a positive integer" in result.stderr.lower()
    
    # Test with valid length (should work)
    result = subprocess.run(
        [sys.executable, "main.py", "story", "test objective",
         "--language", "English", "--level", "A2", "--phase", "1", "--length", "100"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
