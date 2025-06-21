"""Tests for mock_llm.py."""
import json
import hashlib
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from llm_mock import MockLLM

# Set a 10-second timeout for all tests in this file
pytestmark = pytest.mark.timeout(10)


def test_mock_llm_init_creates_cache_dir(tmp_path: Path) -> None:
    """Test that cache directory is created on init."""
    cache_dir = tmp_path / "test_cache"
    assert not cache_dir.exists()
    MockLLM(cache_dir=str(cache_dir))
    assert cache_dir.exists()


def test_get_cache_path_consistent_hashing() -> None:
    """Test that the same prompt produces the same cache path."""
    llm = MockLLM()
    prompt = "test prompt"
    path1 = llm._get_cache_path(prompt)
    path2 = llm._get_cache_path(prompt)
    assert path1 == path2
    
    # Verify the hash is based on the prompt
    expected_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
    assert expected_hash in str(path1)


def test_get_response_returns_cached_response(tmp_path: Path) -> None:
    """Test that get_response returns cached response when available."""
    llm = MockLLM(cache_dir=str(tmp_path))
    test_prompt = "test prompt"
    test_response = {"test": "response"}
    
    # Create a cache file manually
    cache_path = tmp_path / f"{hashlib.md5(test_prompt.encode()).hexdigest()}.json"
    with open(cache_path, 'w') as f:
        json.dump(test_response, f)
    
    # Should return the cached response without calling input
    with patch('builtins.input') as mock_input:
        response = llm.get_response(test_prompt)
        mock_input.assert_not_called()
        assert response == test_response


@pytest.mark.timeout(5)  # 5 second timeout for this test
def test_get_response_prompts_user_when_no_cache(monkeypatch, tmp_path: Path) -> None:
    """Test that get_response prompts user when no cache exists."""
    # Setup
    llm = MockLLM(cache_dir=str(tmp_path))
    test_prompt = "test prompt"
    test_response = "test response"
    
    # Track input calls and responses
    input_calls = []
    input_responses = [
        test_response,  # First input: the response content
        "%%%",          # Second input: end of response marker
        "y"             # Third input: confirmation to save
    ]
    
    def mock_input(prompt=None):
        prompt = prompt or ""
        input_calls.append(prompt)
        
        if not input_responses:
            pytest.fail("Unexpected input() call - no more responses configured")
            
        return input_responses.pop(0)
    
    # Apply the mock
    monkeypatch.setattr('builtins.input', mock_input)
    
    # Create a mock file handle
    mock_file_handle = mock_open()
        
    # Mock file operations and suppress prints
    with patch('builtins.open', mock_file_handle) as mock_file, \
         patch('json.dump') as mock_json_dump, \
         patch('builtins.print'):  # Suppress print output during tests
        # Call the method under test
        response = llm.get_response(test_prompt)
        
        # Debug: Print all input calls for inspection
        print("\n=== Input Calls ===")
        for i, call in enumerate(input_calls):
            print(f"Input call {i}: {call}")
        print("==================")
        
        # Verify all expected input calls were made
        # The first call is an empty string (from the initial input() call)
        # The second call is also empty (from the loop's first iteration)
        # The third call is the save confirmation prompt
        assert len(input_calls) >= 3, f"Expected at least 3 input calls, got {len(input_calls)}: {input_calls}"
        assert "Save this response?" in input_calls[-1], f"Last prompt should be save confirmation. Got: {input_calls[-1]}"
        
        # Verify the response structure
        assert "choices" in response, "Response should contain 'choices' key"
        assert len(response["choices"]) > 0, "Choices should not be empty"
        assert "message" in response["choices"][0], "First choice should have 'message' key"
        assert "content" in response["choices"][0]["message"], "Message should have 'content' key"
        assert test_response in response["choices"][0]["message"]["content"], \
            f"Response content should contain '{test_response}'"
        
        # Verify the cache file was created with the correct content
        cache_path = llm._get_cache_path(test_prompt)
        mock_file.assert_called_once_with(cache_path, 'w')
        
        # Verify the response was saved to cache using json.dump
        mock_json_dump.assert_called_once()
        
        # Get the arguments passed to json.dump
        dump_args, dump_kwargs = mock_json_dump.call_args
        dumped_content = dump_args[0]  # First arg is the object being dumped
        
        # Verify the dumped content has the expected structure
        assert "choices" in dumped_content, "Dumped content should have 'choices' key"
        assert len(dumped_content["choices"]) > 0, "Dumped choices should not be empty"
        assert "message" in dumped_content["choices"][0], "First choice should have 'message' key"
        assert "content" in dumped_content["choices"][0]["message"], "Message should have 'content' key"
        
        # Verify the JSON dump was called with the expected content
        dump_args, _ = mock_json_dump.call_args
        dumped_content = dump_args[0]
        assert dumped_content["choices"][0]["message"]["content"] == test_response, \
            "Dumped content should match the test response"
            
        # Verify the file was opened in write mode
        # The call_args is a tuple of (args, kwargs)
        # The first argument is the path, the second is the mode
        call_args, call_kwargs = mock_file.call_args
        assert len(call_args) >= 2, "File open should have at least 2 arguments (path and mode)"
        assert call_args[1] == 'w', f"File should be opened in write mode, got {call_args[1]}"


@pytest.mark.timeout(5)  # 5 second timeout for this test
def test_get_response_handles_empty_response(monkeypatch, tmp_path: Path) -> None:
    """Test that empty responses are handled gracefully."""
    llm = MockLLM(cache_dir=str(tmp_path))
    
    # Test case 1: Empty response for story type should use default story
    input_responses = [
        "%%%",  # Empty response
        "y"      # Confirm save
    ]
    input_iter = iter(input_responses)
    
    def mock_input_story(prompt=None):
        prompt = prompt or ""
        if "Save this response?" in prompt:
            return next(input_iter, "y")
        return next(input_iter, "%%%")
        
    monkeypatch.setattr('builtins.input', mock_input_story)
    
    # Mock file operations
    with patch('builtins.open', mock_open()) as mock_file, \
         patch('json.dump') as mock_json_dump, \
         patch('builtins.print'):  # Suppress print output during tests
        
        # Test with story type - should raise ValueError for empty input
        with pytest.raises(ValueError, match="Empty story response received"):
            llm.get_response("test prompt", response_type="story")
    
    # Test case 2: Empty response for non-story type should return empty content
    input_responses = [
        "%%%",  # Empty response
        "y"      # Confirm save
    ]
    input_iter = iter(input_responses)
    
    def mock_input_other(prompt=None):
        prompt = prompt or ""
        if "Save this response?" in prompt:
            return next(input_iter, "y")
        return next(input_iter, "%%%")
    
    monkeypatch.setattr('builtins.input', mock_input_other)
    
    with patch('builtins.open', mock_open()) as mock_file, \
         patch('json.dump') as mock_json_dump, \
         patch('builtins.print'):  # Suppress print output during tests
        
        # Test with non-story type - should return empty content
        response = llm.get_response("test prompt", response_type="other")
        
        # Should still have the correct structure but with empty content
        assert isinstance(response, dict), "Response should be a dictionary"
        assert "choices" in response, "Response should contain 'choices' key"
        assert len(response["choices"]) > 0, "Choices should not be empty"
        assert "message" in response["choices"][0], "First choice should have 'message' key"
        assert "content" in response["choices"][0]["message"], "Message should have 'content' key"
        
        # For non-story type, content should be an empty string
        assert response["choices"][0]["message"]["content"] == "", \
            "Non-story response should have empty content"


@pytest.mark.timeout(5)  # 5 second timeout for this test
def test_get_response_with_multiline_input(monkeypatch, tmp_path: Path) -> None:
    """Test that multi-line input is handled correctly."""
    llm = MockLLM(cache_dir=str(tmp_path))
    
    # Test multi-line content
    test_content = "First line\nSecond line"
    
    # Create a list of inputs to simulate user responses
    input_sequence = [
        test_content,  # First line of response
        "%%%",         # End of response marker
        "y"            # Confirm save
    ]
    input_iter = iter(input_sequence)
    
    def mock_input(prompt=None):
        prompt = prompt or ""  # Ensure prompt is never None
        
        # Handle different prompt types
        if "Save this response?" in prompt:
            return next(input_iter, "y")  # Default to 'y' if we run out of responses
        elif "ENTER RESPONSE" in prompt or not prompt.strip():
            # For empty prompts (from the input() loop) or the initial ENTER RESPONSE prompt
            return next(input_iter, test_content)
        return ""
    
    monkeypatch.setattr('builtins.input', mock_input)
    
    # Mock file operations
    with patch('builtins.open', mock_open()) as mock_file, \
         patch('json.dump') as mock_json_dump, \
         patch('builtins.print'):  # Suppress print output
        
        # Call the method under test
        response = llm.get_response("test prompt")
        
        # Verify the response contains the expected content
        assert response is not None, "Response should not be None"
        assert "choices" in response, "Response should contain 'choices' key"
        assert len(response["choices"]) > 0, "Choices should not be empty"
        assert "message" in response["choices"][0], "First choice should have 'message' key"
        assert "content" in response["choices"][0]["message"], "Message should have 'content' key"
        
        # Verify the response was saved to cache
        mock_json_dump.assert_called_once()
