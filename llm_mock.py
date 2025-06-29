import json
from pathlib import Path
from typing import Dict, Any, Optional
import hashlib

from config import MOCK_RESPONSES_DIR
from utils import count_words

class MockLLM:
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the mock LLM with a cache directory for storing and loading responses.
        
        Args:
            cache_dir: Optional custom directory to store mock responses. 
                     If not provided, uses MOCK_RESPONSES_DIR from config.
        """
        self.cache_dir = Path(cache_dir) if cache_dir else MOCK_RESPONSES_DIR
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
                
        # For curriculum responses, generate a dynamic response based on the prompt
        if response_type == "curriculum":
            try:
                # Extract the learning goal from the prompt
                learning_goal = "space exploration"  # Default
                if "learning_goal" in prompt:
                    # Try to extract from JSON-like format
                    import re
                    match = re.search(r'"learning_goal"\s*:\s*"([^"]+)"', prompt)
                    if match:
                        learning_goal = match.group(1)
                
                # Generate a structured curriculum response
                days = {}
                for day_num in range(1, 6):
                    day_key = f'day_{day_num}'
                    days[day_key] = {
                        'title': f'Day {day_num}: {learning_goal.capitalize()} - Part {day_num}',
                        'content': f"This is day {day_num} of learning about {learning_goal}. "
                                 f"Today we'll focus on key aspects of this topic.",
                        'focus': f"{learning_goal} - Part {day_num}",
                        'collocations': [
                            f"learn about {learning_goal}",
                            f"study {learning_goal}",
                            f"explore {learning_goal}",
                            f"understand {learning_goal}"
                        ],
                        'vocabulary': [
                            {"word": f"{learning_goal} term {i}", "definition": f"Definition of {learning_goal} term {i}"}
                            for i in range(1, 4)  # 3 vocabulary words per day
                        ],
                        'activities': [
                            f"Read a short text about {learning_goal}",
                            f"Practice using key vocabulary related to {learning_goal}",
                            f"Have a conversation about {learning_goal}"
                        ]
                    }
                
                # Create the full curriculum structure
                curriculum = {
                    'metadata': {
                        'learning_goal': learning_goal,
                        'target_language': 'English',
                        'cefr_level': 'B1',
                        'format': 'json',
                        'generated_at': '2023-01-01T00:00:00Z',
                        'version': '1.0'
                    },
                    'content': f"A comprehensive curriculum for learning about {learning_goal} over 5 days.",
                    'days': days
                }
                
                response = {
                    "choices": [{
                        "message": {
                            "content": json.dumps(curriculum, indent=2),
                            "role": "assistant"
                        }
                    }]
                }
                # Cache the response
                with open(cache_path, 'w') as f:
                    json.dump(response, f, indent=2)
                return response
            except Exception as e:
                print(f"Error generating curriculum: {e}")
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
