import json
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum

from config import DATA_DIR, PROMPTS_DIR, DEFAULT_STORY_LENGTH, MOCK_RESPONSES_DIR, CURRICULUM_PATH
from llm_mock import MockLLM
from srs_tracker import SRSTracker
from collocation_extractor import CollocationExtractor

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
        
    Raises:
        ValueError: If cefr_level is not a valid CEFR level (A1, A2, B1, B2, C1, C2)
    """
    learning_objective: str
    language: str
    cefr_level: Union[CEFRLevel, str]
    phase: int
    length: int = field(default_factory=lambda: DEFAULT_STORY_LENGTH)
    new_vocabulary: List[str] = field(default_factory=list)
    recycled_vocabulary: List[str] = field(default_factory=list)
    recycled_collocations: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate the CEFR level after initialization."""
        valid_levels = {level.value for level in CEFRLevel}
        
        # Convert to string if it's a CEFRLevel enum
        level_str = self.cefr_level.value if isinstance(self.cefr_level, CEFRLevel) else str(self.cefr_level).upper()
        
        if level_str not in valid_levels:
            raise ValueError(
                f"Invalid CEFR level: '{self.cefr_level}'. "
                f"Must be one of: {', '.join(valid_levels)}"
            )
        
        # Ensure cefr_level is stored as the enum value
        self.cefr_level = CEFRLevel(level_str)

class ContentGenerator:
    def __init__(self):
        self.llm = MockLLM()
        self.story_prompt = self._load_prompt('story_prompt.txt')
        self.srs = SRSTracker()
        self._collocation_extractor = None
    
    @property
    def collocation_extractor(self):
        """Lazily load the CollocationExtractor to prevent test failures."""
        if self._collocation_extractor is None:
            self._collocation_extractor = CollocationExtractor()
        return self._collocation_extractor
    
    def _load_prompt(self, filename: str) -> str:
        """Load prompt from file or use default if not found."""
        prompt_path = PROMPTS_DIR / filename
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        with open(prompt_path, 'r') as f:
            return f.read()
    
    def generate_story(self, params: StoryParams, previous_story: str = "") -> Optional[str]:
        """
        Generate a story based on the given parameters.
        
        Args:
            params: Story generation parameters
            previous_story: Content of the previous story for continuity (if any)
            
        Returns:
            Generated story text
            
        Raises:
            IOError: If there's an error saving the story
        """
        try:
            # Format the prompt with the provided parameters
            cefr_level = params.cefr_level.value if isinstance(params.cefr_level, CEFRLevel) else params.cefr_level
            new_vocab = ", ".join(params.new_vocabulary) if params.new_vocabulary else "None"
            recycled_collocs = ", ".join(params.recycled_collocations) if params.recycled_collocations else "None"
            
            # Format the prompt according to story_prompt.txt structure
            prompt = self.story_prompt.format(
                NEW_VOCABULARY=new_vocab,
                RECYCLED_COLLOCATIONS=recycled_collocs,
                GENRE="adventure"  # Default genre, can be made configurable if needed
            )
            
            # Get the story from the LLM
            response = self.llm.get_response(
                prompt=prompt,
                response_type="story"
            )
            
            # Extract the story text from the response
            story = response['choices'][0]['message']['content']
            
            # Save the story with phase number and learning objective
            story_path = self._save_story(story, params.phase, params.learning_objective)
            print(f"Story saved to: {story_path}")
            
            # Extract collocations from the story and add them to SRS
            try:
                collocations = self.collocation_extractor.extract_collocations(story)
                if collocations:
                    self.srs.add_collocations(collocations, day=params.phase)
                    print(f"Added {len(collocations)} collocations to SRS")
            except Exception as e:
                print(f"Warning: Failed to extract collocations: {e}")
                
            return story
            
        except IOError as e:
            # Re-raise IOError to be handled by the caller
            raise
        except Exception as e:
            # Log other exceptions but don't expose implementation details
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
            
        # Create output directory and parent directories if they don't exist
        output_dir = DATA_DIR / 'generated_content'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate a clean filename from the objective
        clean_obj = learning_objective.strip().lower()
        # Replace any non-alphanumeric character with underscore
        clean_obj = ''.join(c if c.isalnum() else '_' for c in clean_obj)
        # Remove any leading/trailing underscores and consecutive underscores
        clean_obj = '_'.join(part for part in clean_obj.split('_') if part)
        # Truncate to ensure the total filename stays within reasonable limits
        # Keep it under 30 chars to match the test expectation
        clean_obj = clean_obj[:30]
        # Ensure we don't end with an underscore after truncation
        clean_obj = clean_obj.rstrip('_')
        
        if not clean_obj:  # Fallback if no valid characters remain
            clean_obj = f"phase{phase}_story"
        
        # Create the full filename with the required format
        filename = f"story_day{phase}_{clean_obj}.txt"
        story_path = output_dir / filename
        
    def _extract_title(self, story: str) -> str:
        """Extract the title from the story content.
        
        Args:
            story: The story content
            
        Returns:
            str: Extracted title or empty string if not found
        """
        # Look for a line that starts and ends with ** (markdown heading)
        for line in story.split('\n'):
            line = line.strip()
            if line.startswith('**') and line.endswith('**'):
                # Remove the ** markers and any leading/trailing whitespace
                title = line[2:-2].strip()
                if title:  # Only return if we actually found a title
                    return title
        return ''

    def _clean_filename(self, text: str, max_length: int = 30) -> str:
        """Clean and format text for use in a filename.
        
        Args:
            text: The text to clean
            max_length: Maximum length of the cleaned text
            
        Returns:
            str: Cleaned text suitable for a filename
        """
        if not text:
            return ''
            
        # Convert to lowercase and replace spaces with underscores
        clean = text.lower().replace(' ', '_')
        # Remove any remaining non-alphanumeric characters except underscores
        clean = ''.join(c if c.isalnum() or c == '_' else '' for c in clean)
        # Remove any leading/trailing underscores and consecutive underscores
        clean = '_'.join(part for part in clean.split('_') if part)
        # Truncate to max length
        clean = clean[:max_length].rstrip('_')
        
        return clean

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
            
        # Create output directory and parent directories if they don't exist
        output_dir = DATA_DIR / 'generated_content'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to extract title from story content
        title = self._extract_title(story)
        if title:
            clean_title = self._clean_filename(title)
            if clean_title:
                filename = f"story_day{phase}_{clean_title}.txt"
                story_path = output_dir / filename
                # Check if the file would be different from the learning_objective version
                clean_obj = self._clean_filename(learning_objective)
                if clean_obj and clean_obj != clean_title:
                    # If different, make sure we're not overwriting an existing file
                    if not story_path.exists():
                        return self._write_story_file(story_path, story)
                    
        # Fall back to learning objective if no title found or if file exists
        clean_obj = self._clean_filename(learning_objective)
        if not clean_obj:  # Fallback if no valid characters remain
            clean_obj = f"phase{phase}_story"
            
        # Create the full filename with the required format
        filename = f"story_day{phase}_{clean_obj}.txt"
        story_path = output_dir / filename
        
        return self._write_story_file(story_path, story)
        
    def _write_story_file(self, path: Path, content: str) -> str:
        """Helper method to write story content to a file."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return str(path)
        except IOError as e:
            error_msg = f"Failed to save story to {path}: {e}"
            print(f"Error: {error_msg}")
            raise IOError(error_msg) from e  
    def _load_curriculum(self) -> Dict[str, Any]:
        """Load and parse the curriculum JSON file.
        
        Returns:
            Dict containing the curriculum data
            
        Raises:
            FileNotFoundError: If the curriculum file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        if not CURRICULUM_PATH.exists():
            raise FileNotFoundError(f"Curriculum file not found at {CURRICULUM_PATH}")
            
        with open(CURRICULUM_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    def generate_story_for_day(self, day: int) -> Optional[str]:
        """Generate a story for a specific day using curriculum and SRS data.
        
        Args:
            day: The day number to generate the story for
            
        Returns:
            Generated story text, or None if generation failed
        """
        try:
            # Load curriculum and get phase data
            curriculum = self._load_curriculum()
            phase_data = curriculum.get('phases', {}).get(f'phase{day}')
            if not phase_data:
                print(f"No curriculum found for day {day}")
                return None
                
            # Get due collocations from SRS (already returns list of strings)
            recycled_collocations = self.srs.get_due_collocations(day) or []
            
            # Get recycled vocabulary from previous stories
            recycled_vocab = phase_data.get('recycled_vocabulary', [])
            
            print(f"\n--- SRS Status ---")
            print(f"Due collocations for day {day}: {len(recycled_collocations)}")
            if recycled_collocations:
                print("Recycled collocations:", ", ".join(f'"{c}"' for c in recycled_collocations))
            else:
                print("No collocations due for review today")
            
            # Create story parameters
            params = StoryParams(
                learning_objective=phase_data.get('learning_objective', 'General Learning'),
                language=curriculum.get('language', 'English'),
                cefr_level=phase_data.get('cefr_level', 'B1'),
                phase=day,
                length=phase_data.get('story_length', DEFAULT_STORY_LENGTH),
                recycled_collocations=recycled_collocations,
                new_vocabulary=phase_data.get('new_vocabulary', []),
                recycled_vocabulary=recycled_vocab
            )
            
            # Get previous story for continuity
            previous_story = self.get_previous_story(day)
            
            # Generate the story
            story = self.generate_story(params, previous_story)
            if not story:
                return None
                
            # Extract collocations from the generated story
            collocations = self.collocation_extractor.extract_collocations(story)
            
            if collocations:
                # Add new collocations to SRS
                self.srs.add_collocations(
                    collocations=collocations,
                    day=day
                )
                
                # Print summary
                new_count = len([c for c in collocations if c not in recycled_collocations])
                print(f"\n--- Collocation Summary ---")
                print(f"Recycled collocations: {len(recycled_collocations)}")
                print(f"New collocations found: {new_count}")
                print(f"Total collocations: {len(collocations)}")
                
            return story
            
        except Exception as e:
            print(f"Error generating story for day {day}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
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
