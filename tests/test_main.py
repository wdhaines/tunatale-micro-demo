"""Tests for main.py CLI functionality."""
import io
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY, mock_open

import pytest

from story_generator import CEFRLevel, ContentGenerator, StoryParams
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
@patch('pathlib.Path.mkdir')
@patch('pathlib.Path.write_text')
@patch('sys.stdout', new_callable=io.StringIO)
def test_cli_story_generation(mock_stdout, mock_write_text, mock_mkdir, mock_content_gen, tmp_path: Path) -> None:
    """Test story generation via CLI."""
    from main import CLI
    
    # Setup mocks
    mock_instance = mock_content_gen.return_value
    mock_instance.generate_story.return_value = "Test story content"
    mock_write_text.return_value = None  # write_text returns None
    
    # Create a temporary output file
    output_file = tmp_path / "output" / "story.txt"
    
    # Create a test namespace that argparse would create
    class Namespace:
        pass
    
    args = Namespace()
    args.command = 'story'
    args.objective = 'test objective'
    args.language = 'English'
    args.level = 'A2'
    args.phase = 1
    args.length = 200
    args.output = str(output_file)
    args.previous = None
    
    # Create CLI instance
    cli = CLI()
    
    # Call the handler directly
    result = cli._handle_story(args)
    
    # Verify the result is successful
    assert result == 0
    
    # In test mode, generate_story should not be called
    mock_instance.generate_story.assert_not_called()
    
    # Verify the directory was created
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    # Verify the test story content was written
    expected_story = f"Test story for {args.objective} at level {args.level}"
    mock_write_text.assert_called_once_with(expected_story, encoding='utf-8')
    
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
         "--language", "English", "--level", "A2", "--phase", "1"],  # Using uppercase A2 to match expected format
        capture_output=True,
        text=True
    )
    # This should work with correct case
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
