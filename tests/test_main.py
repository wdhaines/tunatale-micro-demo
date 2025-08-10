"""Tests for main.py CLI functionality."""
import io
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY, mock_open

import pytest

from story_generator import CEFRLevel, ContentGenerator, StoryParams


def test_cli_help() -> None:
    """Test that the CLI shows help text."""
    # Test main help
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    output = result.stdout
    
    # Check for key sections in the help text
    assert "usage: main.py" in output
    assert "positional arguments:" in output or "commands:" in output
    assert "optional arguments:" in output or "options:" in output
    assert "use <command> -h for help" in output
    
    # Test help for the generate command
    result = subprocess.run(
        [sys.executable, "main.py", "generate", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    generate_help = result.stdout
    assert "usage: main.py generate" in generate_help
    assert "positional arguments:" in generate_help or "arguments:" in generate_help
    assert "goal" in generate_help
    assert "optional arguments:" in generate_help or "options:" in generate_help


def test_cli_generate_command_required_params() -> None:
    """Test that generate command shows help text when required parameters are missing."""
    # Test with no arguments
    result = subprocess.run(
        [sys.executable, "main.py", "generate"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 2  # Missing required argument: goal
    assert "the following arguments are required: goal" in result.stderr.lower()
    
    # Test with invalid CEFR level
    result = subprocess.run(
        [sys.executable, "main.py", "generate", "test goal", "--cefr-level", "INVALID"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 2  # Invalid choice for cefr-level
    assert "invalid choice" in result.stderr.lower() or "invalid cefr level" in result.stderr.lower()


def test_cli_invalid_cefr_level() -> None:
    """Test that invalid CEFR level is caught by CLI."""
    result = subprocess.run(
        [sys.executable, "main.py", "generate", "test goal", "--cefr-level", "INVALID"],
        capture_output=True,
        text=True
    )
    
    # Should fail with invalid choice error
    assert result.returncode == 2
    error_text = result.stderr.lower()
    assert "invalid choice" in error_text or "invalid cefr level" in error_text

