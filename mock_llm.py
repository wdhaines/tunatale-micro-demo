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
        
        # If not in cache, prompt the user to provide a response
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
            # Provide a complete story if no content was provided
            if not response_content.strip() or len(response_content) < 100:
                response_content = """**The Amazing Discovery**

Emma loved plants. Every weekend, she visited the botanical garden to see the beautiful flowers and trees. But one day, something extraordinary caught her eye - a plant with red, tube-shaped leaves that looked like they were licking their lips!

"What kind of plant is that?" Emma asked the gardener.

"Ah, that's a carnivorous plant called a pitcher plant," the gardener explained. "It eats insects!"

Emma couldn't believe her ears. A plant that eats bugs? She had to learn more!

The next day, Emma went to the library and found books about carnivorous plants. She learned that these amazing plants grow in places where the soil doesn't have enough nutrients, so they've adapted to get food in a different way.

There are many types of carnivorous plants:
1. Venus Flytraps - They have special leaves that snap shut when an insect touches them.
2. Sundews - Their leaves have sticky hairs that trap insects.
3. Pitcher Plants - Insects fall into their tube-shaped leaves and can't climb out.
4. Bladderworts - They suck in tiny water creatures like a vacuum cleaner!

Emma decided to give a talk about these fascinating plants at her school's science fair. She made colorful posters showing how each plant catches its food. She even brought a small Venus flytrap to demonstrate.

On the day of the science fair, Emma was nervous but excited. She took a deep breath and began her presentation. Soon, all her classmates were gathered around, their eyes wide with wonder.

"These plants are like nature's pest control!" Emma explained. "They help keep the insect population in balance."

By the end of her talk, Emma had taught her whole class about these incredible plants. Her teacher was so impressed that she invited Emma to present to other classes too.

From that day on, Emma became known as the "Plant Detective" at school. She continued learning about different plants and even started a small garden at home with her very own carnivorous plants.

Who knew that one curious question could lead to such an exciting discovery? Emma learned that nature is full of surprises, and sometimes the most amazing things come in small, leafy packages!"""
            
            response = {
                "choices": [{
                    "message": {
                        "content": response_content,
                        "role": "assistant"
                    }
                }]
            }
        else:
            response = response_content
        
        # Cache the response
        with open(cache_path, 'w') as f:
            json.dump(response, f, indent=2)
        
        return response
