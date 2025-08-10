import json
from pathlib import Path
from typing import Dict, Any, Optional
import hashlib

import config
from utils import count_words

class MockLLM:
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the mock LLM with a cache directory for storing and loading responses.
        
        Args:
            cache_dir: Optional custom directory to store mock responses. 
                     If not provided, uses MOCK_RESPONSES_DIR from config.
        """
        self.cache_dir = Path(cache_dir) if cache_dir else config.MOCK_RESPONSES_DIR
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
                
                # Generate a structured curriculum response compatible with CurriculumDay
                days = []
                for day_num in range(1, 6):
                    days.append({
                        'day': day_num,
                        'title': f'Day {day_num}: {learning_goal.capitalize()} - Part {day_num}',
                        'focus': f"{learning_goal} - Part {day_num}",
                        'collocations': [
                            f"learn about {learning_goal}",
                            f"study {learning_goal}",
                            f"explore {learning_goal}",
                            f"understand {learning_goal}"
                        ],
                        'presentation_phrases': [
                            f"learn about {learning_goal}",
                            f"study {learning_goal}",
                            f"explore {learning_goal}",
                            f"understand {learning_goal}"
                        ],
                        'learning_objective': f"Master {learning_goal} fundamentals",
                        'story_guidance': f"Focus on practical {learning_goal} scenarios"
                    })
                
                # Create the full curriculum structure compatible with Curriculum model
                curriculum = {
                    'learning_objective': f"Learn about {learning_goal}",
                    'target_language': 'English',
                    'learner_level': 'A2',
                    'presentation_length': 5,
                    'days': days,
                    'metadata': {
                        'generated_at': '2023-01-01T00:00:00Z',
                        'format': 'structured',
                        'version': '2.0',
                        'theme': f'{learning_goal.capitalize()} Learning',
                        'focus': f'Basic {learning_goal} concepts'
                    }
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

    def _prompt_user_for_response(self) -> str:
        """
        Get multi-line response from user with preview and confirmation.
        In non-interactive mode, generates appropriate story content automatically.
        
        Returns:
            The user's response content as a string
        """
        # Check if we're in a non-interactive environment first
        try:
            # Try to read from stdin to detect if we're interactive
            import sys
            if not sys.stdin.isatty():
                print("\n=== NON-INTERACTIVE MODE DETECTED ===")
                print("Generating default story content automatically...")
                return self._generate_default_story_content()
        except Exception as e:
            pass
        
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
                # Handle Ctrl+D gracefully or non-interactive environment
                print("\n(Non-interactive environment detected, generating default content...)")
                return self._generate_default_story_content()
        
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
            try:
                confirm = input("\nSave this response? (y/n): ").lower()
                if confirm in ('y', 'yes'):
                    break
                elif confirm in ('n', 'no'):
                    print("Discarding response. Please try again...\n")
                    return self._prompt_user_for_response()  # Recursive retry
                else:
                    print("Please enter 'y' to save or 'n' to discard.")
            except EOFError:
                # Handle non-interactive environments
                print("\nNon-interactive environment detected, saving response...")
                break
        
        return response_content
    
    def _generate_default_story_content(self) -> str:
        """
        Generate default story content for non-interactive mode.
        Creates a simple Filipino travel story with proper structure.
        
        Returns:
            Default story content as a string
        """
        return """**Key Phrases:**
- Kumusta ka? (How are you?)
- Magandang umaga po (Good morning, polite)
- Salamat po (Thank you)
- Walang anuman (You're welcome)

**Natural Speed Story:**
Si Maria ay pumunta sa El Nido para sa bakasyon. Pagdating niya sa hotel, nakipag-usap siya sa receptionist. "Magandang umaga po," sabi niya. "May reservation po ako." Ang receptionist ay ngumiti at nagsabi, "Kumusta ka? Ano ang pangalan mo?" Sumagot si Maria, "Maria Santos po." Pagkatapos ng check-in, nagpasalamat si Maria. "Salamat po." Sumagot ang receptionist, "Walang anuman. Enjoy your stay!"

**Slow Speed Story:**
Si Ma-ri-a... ay pu-mun-ta... sa El Ni-do... pa-ra sa ba-ka-syon. Pag-da-ting ni-ya... sa ho-tel, na-ki-pag-u-sap si-ya... sa re-cep-tion-ist. "Ma-gan-dang u-ma-ga po," sa-bi ni-ya. "May re-ser-va-tion po a-ko." Ang re-cep-tion-ist... ay ngu-mi-ti at nag-sa-bi, "Ku-mus-ta ka? A-no ang pan-ga-lan mo?" Su-ma-got si Ma-ri-a, "Ma-ri-a San-tos po." Pag-ka-ta-pos ng check-in, nag-pa-sa-la-mat si Ma-ri-a. "Sa-la-mat po." Su-ma-got ang re-cep-tion-ist, "Wa-lang a-nu-man. En-joy your stay!"

**English Translation:**
Maria went to El Nido for vacation. When she arrived at the hotel, she talked to the receptionist. "Good morning," she said. "I have a reservation." The receptionist smiled and said, "How are you? What's your name?" Maria replied, "Maria Santos." After check-in, Maria thanked her. "Thank you." The receptionist replied, "You're welcome. Enjoy your stay!\""""

    def chat_response(self, system_prompt: str, user_prompt: str, response_type: str = "story") -> Dict[str, Any]:
        """
        Get a response using a conversational chat approach with system and user prompts.
        
        This method separates the system constraints from the day-specific content,
        showing both to the user but only caching based on the user prompt.
        
        Args:
            system_prompt: The system/constraint prompt (displayed but not cached)
            user_prompt: The specific day prompt (used for caching)
            response_type: Type of response expected
            
        Returns:
            Dictionary containing the mock response
        """
        # Use only the user prompt for caching to avoid duplicating system constraints
        cache_path = self._get_cache_path(user_prompt)
        
        # Try to load from cache first
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                return json.load(f)
        
        # Display the conversational context to user
        print(f"\n=== MOCK LLM CHAT SESSION ===")
        print(f"System: {response_type}")
        print(f"------------------------------")
        print("SYSTEM PROMPT (persistent across all days):")
        print(system_prompt)
        print(f"\n{'='*50}")
        print("DAY-SPECIFIC PROMPT (changes per day):")
        print(user_prompt)
        print(f"------------------------------")
        
        # Get user response
        response_content = self._prompt_user_for_response()
        
        # Create structured response
        response = {
            "choices": [{
                "message": {
                    "content": response_content,
                    "role": "assistant"
                }
            }]
        }
        
        # Cache only the user prompt and response (not system prompt)
        cache_data = {
            "user_prompt": user_prompt,
            "response": response,
            "response_type": response_type
        }
        
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        return response
