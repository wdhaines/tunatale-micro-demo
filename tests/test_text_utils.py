"""Tests for text_utils module."""
import pytest

from utils.text_utils import count_words


def test_count_words_empty_string() -> None:
    """Test counting words in an empty string."""
    assert count_words("") == 0


def test_count_words_single_word() -> None:
    """Test counting a single word."""
    assert count_words("hello") == 1


def test_count_words_multiple_words() -> None:
    """Test counting multiple words."""
    assert count_words("hello world") == 2


def test_count_words_with_punctuation() -> None:
    """Test counting words with punctuation."""
    assert count_words("Hello, world!") == 2


def test_count_words_multiple_spaces() -> None:
    """Test counting words with multiple spaces."""
    assert count_words("  hello   world  ") == 2


def test_count_words_newlines() -> None:
    """Test counting words with newlines."""
    assert count_words("hello\nworld") == 2


def test_count_words_mixed_whitespace() -> None:
    """Test counting words with mixed whitespace."""
    assert count_words("hello \t\n world") == 2


def test_count_words_only_whitespace() -> None:
    """Test counting words with only whitespace."""
    assert count_words("  \t\n ") == 0


def test_count_words_with_hyphens() -> None:
    """Test counting hyphenated words."""
    assert count_words("state-of-the-art") == 1  # Counts as one word


def test_count_words_with_numbers() -> None:
    """Test counting words with numbers."""
    # Numbers are treated as separate words
    assert count_words("Python 3.9 is great") == 4
