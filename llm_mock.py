import json
from pathlib import Path
from typing import Dict, Any, Optional
import hashlib

from utils import count_words

class MockLLM:
    def __init__(self, cache_dir: str = "data/mock_responses"):
        """
        Initialize the mock LLM with a cache directory for storing and loading responses.
        
        Args:
            cache_dir: Directory to store mock responses
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, prompt: str) -> Path:
        """Generate a cache file path based on the prompt content."""
        # Create a hash of the prompt to use as a filename
        prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{prompt_hash}.json"
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate a response using the mock LLM (compatibility method for CurriculumGenerator).
        
        Args:
            prompt: The prompt to generate a response for
            **kwargs: Additional arguments (ignored in mock implementation)
            
        Returns:
            Dictionary containing the mock response in the expected format
        """
        # Delegate to get_response with 'curriculum' as the default response_type
        return self.get_response(prompt, response_type="curriculum")
    
    def get_response(self, prompt: str, response_type: str = "curriculum") -> Dict[str, Any]:
        """
        Get a mock response for the given prompt, either from cache or by prompting the user.
        
        Args:
            prompt: The prompt to generate a response for
            response_type: Type of response (curriculum, story, etc.)
            
        Returns:
            Dictionary containing the mock response
        """
        cache_path = self._get_cache_path(prompt)
        
        # Try to load from cache first
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                return json.load(f)
                
        # For curriculum responses, use our predefined template
        if response_type == "curriculum":
            try:
                with open('prompts/30day_carnivorous_plants_curriculum.txt', 'r') as f:
                    response_content = f.read()
                print("Using predefined 30-day carnivorous plants curriculum template")
                response = {
                    "choices": [{
                        "message": {
                            "content": response_content,
                            "role": "assistant"
                        }
                    }]
                }
                # Cache the response
                with open(cache_path, 'w') as f:
                    json.dump(response, f, indent=2)
                return response
            except Exception as e:
                print(f"Error loading predefined curriculum: {e}")
                # Fall through to manual input
        
        # If not in cache and not using predefined curriculum, prompt the user
        print(f"\n=== MOCK LLM PROMPT ===")
        print(f"Type: {response_type}")
        print("-" * 30)
        print(prompt)
        print("-" * 30)
        print("Please provide the mock response (type 'exit' to cancel):")
        
        # Get multi-line input from user
        print("\n=== ENTER RESPONSE ===")
        print("Type your response (multiple lines OK).")
        print("To finish, enter '%%%' on a new line and press Enter.")
        print("To cancel, type 'exit' and press Enter.")
        print("=" * 40)
        
        lines = []
        while True:
            try:
                line = input()
                if line.lower() == 'exit':
                    raise ValueError("User cancelled mock response input")
                if line.strip() == '%%%':  # Custom delimiter to end input
                    break
                lines.append(line)
            except EOFError:
                # Handle Ctrl+D gracefully
                print("\n(End of input detected, finalizing response...)")
                break
        
        response_content = '\n'.join(lines).strip()
        
        # Show preview
        preview_length = 100  # Show first 100 words for preview
        preview_words = response_content.split()
        preview_text = ' '.join(preview_words[:preview_length])
        if len(preview_words) > preview_length:
            preview_text += '...'
            
        word_count = count_words(response_content)
        
        print("\n=== RESPONSE PREVIEW ===")
        print(preview_text)
        print("=" * 25)
        print(f"Total length: {word_count} words")
        
        # Confirm before saving
        while True:
            confirm = input("\nSave this response? (y/n): ").lower()
            if confirm in ('y', 'yes'):
                break
            elif confirm in ('n', 'no'):
                print("Discarding response. Please try again...\n")
                return self.get_response(prompt, response_type)
            else:
                print("Please enter 'y' to save or 'n' to discard.")
        
        # Format the response based on type
        if response_type == "curriculum":
            response = {
                "choices": [{
                    "message": {
                        "content": response_content,
                        "role": "assistant"
                    }
                }]
            }
        elif response_type == "story":
            # Validate that we have a proper story response
            if not response_content.strip():
                raise ValueError("Empty story response received. Please provide a valid story.")
            if len(response_content.strip()) < 100:
                raise ValueError(f"Story is too short ({len(response_content)} chars). Please provide a more detailed story (minimum 100 characters).")
            
            response = {
                "choices": [{
                    "message": {
                        "content": response_content,
                        "role": "assistant"
                    }
                }]
            }
        else:
            # For other types, still return a properly formatted response
            response = {
                "choices": [{
                    "message": {
                        "content": response_content,
                        "role": "assistant"
                    }
                }]
            }
        
        # Cache the response
        with open(cache_path, 'w') as f:
            json.dump(response, f, indent=2)
        
        return response
