import json
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from config import DATA_DIR, PROMPTS_DIR, DEFAULT_STORY_LENGTH, MOCK_RESPONSES_DIR
from mock_llm import MockLLM

class CEFRLevel(str, Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"

@dataclass
class StoryParams:
    """Parameters for generating a story.
    
    Attributes:
        learning_objective: The main topic or objective of the story
        language: Target language for the story
        cefr_level: Language proficiency level (A1-C2)
        phase: Learning phase or day number
        length: Target word count (defaults to DEFAULT_STORY_LENGTH from config)
    """
    learning_objective: str
    language: str
    cefr_level: Union[CEFRLevel, str]
    phase: int
    length: int = field(default_factory=lambda: DEFAULT_STORY_LENGTH)

class ContentGenerator:
    def __init__(self):
        self.llm = MockLLM()
        self.story_prompt = self._load_prompt('story_prompt.txt')
    
    def _load_prompt(self, filename: str) -> str:
        """Load prompt from file or use default if not found."""
        prompt_path = PROMPTS_DIR / filename
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        with open(prompt_path, 'r') as f:
            return f.read()
    
    def generate_story(self, params: StoryParams, previous_story: str = "") -> str:
        """
        Generate a story based on the given parameters.
        
        Args:
            params: Story generation parameters
            previous_story: Content of the previous story for continuity (if any)
            
        Returns:
            Generated story text
        """
        try:
            # Format the prompt with story parameters
            prompt = self.story_prompt.format(
                LEARNING_OBJECTIVE=params.learning_objective,
                TARGET_LANGUAGE=params.language,
                CEFR_LEVEL=params.cefr_level,
                STORY_LENGTH=params.length,
                PHASE=params.phase,
                PREVIOUS_STORY=previous_story if previous_story else "Not applicable - this is the first story"
            )
            
            print("\n=== PROMPT ===")
            print(prompt)
            print("==============\n")
            
            # Get response from mock LLM
            response = self.llm.get_response(
                prompt=prompt,
                response_type="story"
            )
            
            # Extract the story content
            story = response['choices'][0]['message']['content']
            
            # Save the story with phase number and learning objective
            story_path = self._save_story(story, params.phase, params.learning_objective)
            print(f"Story saved to: {story_path}")
            return story
            
        except Exception as e:
            import traceback
            print(f"Error generating story: {e}")
            traceback.print_exc()
            return None
    
    def _save_story(self, story: str, phase: int, learning_objective: str) -> str:
        """Save the generated story to a file.
        
        Args:
            story: The story content to save
            phase: The learning phase number
            learning_objective: The learning objective for the story (required)
            
        Returns:
            str: Path to the saved story file
            
        Raises:
            ValueError: If learning_objective is empty or None
        """
        if not learning_objective or not learning_objective.strip():
            raise ValueError("learning_objective cannot be empty")
            
        # Create output directory if it doesn't exist
        output_dir = DATA_DIR / 'generated_content'
        output_dir.mkdir(exist_ok=True)
        
        # Generate a clean filename from the objective
        clean_obj = ''.join(c if c.isalnum() else '_' for c in learning_objective.strip()[:30])
        if not clean_obj:  # In case objective has no alphanumeric characters
            clean_obj = f"phase{phase}_story"
            
        story_path = output_dir / f"story_phase{phase}_{clean_obj}.txt"
        
        try:
            with open(story_path, 'w', encoding='utf-8') as f:
                f.write(story)
            return str(story_path)
            
        except IOError as e:
            error_msg = f"Failed to save story to {story_path}: {e}"
            print(f"Error: {error_msg}")
            raise
    
    def get_previous_story(self, day_number: int) -> str:
        """Get the story from the previous day, if it exists."""
        if day_number <= 1:
            return ""
            
        prev_day = day_number - 1
        story_path = DATA_DIR / 'generated_content' / f'day{prev_day}_story.txt'
        
        if story_path.exists():
            with open(story_path, 'r') as f:
                return f.read()
        return ""
