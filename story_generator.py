"""Story generation functionality for TunaTale."""
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Try to import config values, with fallbacks for testing
# This makes the module more resilient to missing config during testing
try:
    from config import (
        DATA_DIR, 
        PROMPTS_DIR, 
        DEFAULT_STORY_LENGTH, 
        MOCK_RESPONSES_DIR, 
        CURRICULUM_PATH,
        STORIES_DIR
    )
except ImportError:
    # Fallback values for testing
    TEST_DIR = Path(__file__).parent.parent / 'tests'
    DATA_DIR = TEST_DIR / 'test_data'
    PROMPTS_DIR = TEST_DIR / 'prompts'
    MOCK_RESPONSES_DIR = DATA_DIR / 'mock_responses'
    CURRICULUM_PATH = DATA_DIR / 'curriculum_processed.json'
    DEFAULT_STORY_LENGTH = 500

    # Ensure test directories exist
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    PROMPTS_DIR.mkdir(exist_ok=True, parents=True)
    MOCK_RESPONSES_DIR.mkdir(exist_ok=True, parents=True)

from llm_mock import MockLLM
from srs_tracker import SRSTracker
from collocation_extractor import CollocationExtractor
from curriculum_models import Curriculum, CurriculumDay

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
        
        # Handle different input types for cefr_level
        if isinstance(self.cefr_level, CEFRLevel):
            # Already a valid CEFRLevel enum, nothing to do
            pass
        elif isinstance(self.cefr_level, str):
            # Convert string to CEFRLevel enum
            level_str = self.cefr_level.upper()
            if level_str in valid_levels:
                self.cefr_level = CEFRLevel(level_str)
            else:
                raise ValueError(
                    f"Invalid CEFR level: '{self.cefr_level}'. "
                    f"Must be one of: {', '.join(sorted(valid_levels))}"
                )
        else:
            # For any other type, try to convert to string and validate
            level_str = str(self.cefr_level).upper()
            if level_str in valid_levels:
                self.cefr_level = CEFRLevel(level_str)
            else:
                raise ValueError(
                    f"Invalid CEFR level: '{self.cefr_level}'. "
                    f"Must be one of: {', '.join(sorted(valid_levels))}"
                )

class ContentGenerator:
    def __init__(self):
        self.llm = MockLLM()
        self.story_prompt = self._load_prompt('story_prompt_template.txt')
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
            
            # Format the prompt according to story_prompt_template.txt structure
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
            
        # Ensure STORIES_DIR exists
        output_dir = Path(STORIES_DIR) if isinstance(STORIES_DIR, str) else STORIES_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to extract title from story content
        title = self._extract_title(story)
        if title:
            clean_title = self._clean_filename(title)
            if clean_title:
                filename = f"story_day{phase}_{clean_title}.txt"
                story_path = output_dir / filename
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
    def _load_curriculum(self) -> Curriculum:
        """Load and parse the curriculum from a JSON file.
        
        Returns:
            A Curriculum instance containing the curriculum data
            
        Raises:
            FileNotFoundError: If the curriculum file doesn't exist
            ValueError: If the file is not a valid curriculum
        """
        return Curriculum.load(CURRICULUM_PATH)
            
    def generate_day_story(self, day: int) -> Optional[Tuple[str, List[Dict[str, List[str]]]]]:
        """Generate a story for a specific day using curriculum and SRS data.
        
        Args:
            day: The day number to generate the story for
            
        Returns:
            A tuple of (generated_story, collocation_report) if successful, 
            where collocation_report is a dictionary with keys:
            - 'new': List of new collocations from the curriculum
            - 'reviewed': List of reviewed collocations from SRS
            - 'bonus': List of bonus collocations found in the story
            
            Returns None if generation failed
        """
        try:
            # Load the curriculum
            curriculum = self._load_curriculum()
            
            # Get the day's curriculum data
            day_data = curriculum.get_day(day)
            if not day_data:
                logging.error(f"No curriculum found for day {day}")
                return None
            
            # Get due collocations from SRS (3-5 collocations)
            review_collocations = self.srs.get_due_collocations(day, min_items=3, max_items=5)
            
            # Log the collocations being used
            logging.info(f"\n--- Story Generation ---")
            logging.info(f"Day {day}: {day_data.title}")
            logging.info(f"Learning Objective: {day_data.learning_objective}")
            logging.info(f"Focus: {day_data.focus}")
            logging.info(f"New collocations: {', '.join(day_data.collocations) if day_data.collocations else 'None'}")
            logging.info(f"Review collocations ({len(review_collocations)}): {', '.join(review_collocations) if review_collocations else 'None'}")
            
            # Get previous story for continuity
            previous_story = self.get_previous_story(day)
            
            # Create story parameters with separated new and review collocations
            params = StoryParams(
                learning_objective=day_data.learning_objective,
                language=curriculum.target_language,
                cefr_level=curriculum.learner_level,
                phase=day,
                length=curriculum.presentation_length * 10,  # Convert minutes to words (approx)
                new_vocabulary=day_data.presentation_phrases,
                recycled_collocations=day_data.collocations + review_collocations,
                recycled_vocabulary=[]
            )
            
            # Generate the story
            story = self.generate_story(params, previous_story)
            if not story:
                return None
                
            # Extract collocations from the generated story
            generated_collocations = self.collocation_extractor.extract_collocations(story)
            
            # Categorize collocations found in the story
            new_collocations = []
            reviewed_collocations = []
            bonus_collocations = []
            
            # Check each generated collocation against our lists
            for colloc in generated_collocations:
                if colloc in day_data.collocations:
                    new_collocations.append(colloc)
                elif colloc in review_collocations:
                    reviewed_collocations.append(colloc)
                else:
                    # Check if it's a known collocation in SRS
                    if colloc in self.srs.get_all_collocations():
                        reviewed_collocations.append(colloc)
                    else:
                        bonus_collocations.append(colloc)
            
            # Log the results
            logging.info(f"\n--- Generation Results ---")
            logging.info(f"Generated story with {len(generated_collocations)} collocations")
            logging.info(f"New collocations included: {len(new_collocations)}/{len(day_data.collocations)}")
            if day_data.collocations:
                logging.info(f"  - Included: {', '.join(new_collocations) if new_collocations else 'None'}")
                missing = set(day_data.collocations) - set(new_collocations)
                if missing:
                    logging.warning(f"  - Missing: {', '.join(missing)}")
            
            logging.info(f"Review collocations included: {len(reviewed_collocations)}/{len(review_collocations)}")
            if review_collocations:
                logging.info(f"  - Included: {', '.join(reviewed_collocations) if reviewed_collocations else 'None'}")
                missing = set(review_collocations) - set(reviewed_collocations)
                if missing:
                    logging.warning(f"  - Missing: {', '.join(missing)}")
            
            if bonus_collocations:
                logging.info(f"Bonus collocations found: {len(bonus_collocations)}")
                logging.info(f"  - {', '.join(bonus_collocations)}")
            
            # Prepare collocation report
            collocation_report = {
                'new': new_collocations,
                'reviewed': reviewed_collocations,
                'bonus': bonus_collocations
            }
            
            return story, collocation_report
            
        except Exception as e:
            logging.error(f"Error generating story for day {day}: {e}", exc_info=True)
            return None
    
    def generate_story_for_day(self, day: int) -> Optional[str]:
        """Generate and save a story for a specific day.
        
        This is the main entry point for generating stories. It handles:
        - Generating the story content with SRS integration
        - Updating SRS with new and reviewed collocations
        - Saving the story to a file
        
        Args:
            day: The day number to generate the story for
            
        Returns:
            The generated story text if successful, None otherwise
        """
        try:
            # Generate the story and get collocation report
            result = self.generate_day_story(day)
            if not result:
                return None
                
            story, collocation_report = result
            
            # Update SRS with new collocations
            if collocation_report['new']:
                self.srs.add_collocations(
                    collocations=collocation_report['new'],
                    day=day
                )
                logging.info(f"Added {len(collocation_report['new'])} new collocations to SRS")
            
            # Update SRS with reviewed collocations
            if collocation_report['reviewed']:
                self.srs.add_collocations(
                    collocations=collocation_report['reviewed'],
                    day=day
                )
                logging.info(f"Updated {len(collocation_report['reviewed'])} reviewed collocations in SRS")
            
            # Add any bonus collocations to SRS as well
            if collocation_report['bonus']:
                self.srs.add_collocations(
                    collocations=collocation_report['bonus'],
                    day=day
                )
                logging.info(f"Added {len(collocation_report['bonus'])} bonus collocations to SRS")
            
            # Save the story
            curriculum = self._load_curriculum()
            day_data = curriculum.get_day(day)
            if not day_data:
                logging.error(f"Could not find curriculum data for day {day} when saving story")
                return None
                
            story_path = self._save_story(
                story=story,
                phase=day,
                learning_objective=day_data.learning_objective
            )
            
            logging.info(f"Story saved to: {story_path}")
            return story
            
        except Exception as e:
            logging.error(f"Error in generate_story_for_day for day {day}: {e}", exc_info=True)
            return None
    
    def get_previous_story(self, day_number: int) -> str:
        """Get the story from the previous day, if it exists."""
        if day_number <= 1:
            return ""
            
        prev_day = day_number - 1
        story_path = Path(STORIES_DIR) / f'day{prev_day}_story.txt'
        
        if story_path.exists():
            with open(story_path, 'r') as f:
                return f.read()
        return ""
