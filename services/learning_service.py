"""
Learning Service for TunaTale - Single source of truth for both CLI and web interfaces.

This module provides the LearningService class that encapsulates all business logic
for curriculum management, content generation, and progress tracking.
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, TypeVar, Type
import json
import logging
import os
from pathlib import Path

# Import from existing modules
from curriculum_models import Curriculum, CurriculumDay
from curriculum_service import CurriculumGenerator, ValidationError, LLMError, ParserError
from story_generator import ContentGenerator, StoryParams, CEFRLevel
from collocation_extractor import CollocationExtractor

# Type variable for generic type hints
T = TypeVar('T', bound='LearningError')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LearningError(Exception):
    """Base exception for learning service errors."""
    pass

@dataclass
class DayContent:
    """Container for a day's learning content."""
    day: int
    title: str
    focus: str
    story: str
    new_collocations: List[str] = field(default_factory=list)
    review_collocations: List[str] = field(default_factory=list)

@dataclass
class ProgressInfo:
    """Information about the learner's progress."""
    current_day: int
    total_days: int
    completion_percentage: float
    next_review_date: Optional[datetime] = None
    recent_activity: List[Dict[str, Any]] = field(default_factory=list)

class LearningService:
    """
    Service layer for managing language learning content and progress.
    
    This class serves as the single source of truth for both CLI and web interfaces,
    encapsulating all business logic related to curriculum management, content
    generation, and progress tracking.
    """
    
    def __init__(self, 
                 data_dir: Optional[Union[str, Path]] = None, 
                 prompts_dir: Optional[Union[str, Path]] = None,
                 use_mock_llm: bool = True):
        """
        Initialize the LearningService.
        
        Args:
            data_dir: Base directory for storing application data. If not provided,
                     uses the default DATA_DIR from config or creates a default.
            prompts_dir: Directory containing prompt templates. If not provided,
                       uses the default from config.
        """
        import sys
        self._is_test = 'pytest' in sys.modules
        
        # In test mode, ensure we're using the test data directory
        if self._is_test:
            try:
                from tests.mock_config import DATA_DIR as test_data_dir, PROMPTS_DIR as test_prompts_dir
                self.data_dir = Path(test_data_dir)
                # Default to test prompts dir if not explicitly provided
                self.prompts_dir = Path(prompts_dir) if prompts_dir else Path(test_prompts_dir)
                # Ensure test data directory exists
                self.data_dir.mkdir(parents=True, exist_ok=True)
                self.prompts_dir.mkdir(parents=True, exist_ok=True)
            except ImportError:
                # Fallback to a temporary directory if we can't import test config
                import tempfile
                self.data_dir = Path(tempfile.mkdtemp(prefix='tunatale_test_'))
                self.prompts_dir = Path(tempfile.mkdtemp(prefix='tunatale_test_prompts_'))
        else:
            # In normal mode, use the provided directory or config default
            try:
                from config import DATA_DIR as config_data_dir, PROMPTS_DIR as config_prompts_dir
                self.data_dir = Path(data_dir) if data_dir else Path(config_data_dir)
                self.prompts_dir = Path(prompts_dir) if prompts_dir else Path(config_prompts_dir)
            except ImportError:
                self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent / 'data'
                self.prompts_dir = Path(prompts_dir) if prompts_dir else Path(__file__).parent.parent / 'prompts'
            
            # Ensure data directories exist
            self.data_dir.mkdir(exist_ok=True, parents=True)
            self.prompts_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize LLM (use MockLLM by default for manual input)
        if use_mock_llm:
            from llm_mock import MockLLM
            llm = MockLLM()
        else:
            # Import the real LLM implementation if needed
            from llm_service import LLMService  # Assuming this exists
            llm = LLMService()
        
        # Initialize components with proper data directory and prompts directory
        self.curriculum_generator = CurriculumGenerator(llm=llm)
        self.content_generator = ContentGenerator(
            data_dir=str(self.data_dir),
            prompts_dir=str(self.prompts_dir),
            llm=llm
        )
        self.collocation_extractor = CollocationExtractor()
        
        # State
        self._current_curriculum: Optional[Curriculum] = None
        self._current_day: int = 1
    
    def create_curriculum(self, learning_goal: str, **kwargs) -> Curriculum:
        """
        Create a new curriculum based on the learning goal.
        
        Args:
            learning_goal: The main learning goal for the curriculum.
            **kwargs: Additional parameters for curriculum generation.
                - target_language: str = 'English'
                - cefr_level: str = 'A2'
                - days: int = 30
                - transcript: Optional[str] = None
                - llm_response: Optional[str] = None  # Raw LLM response to parse
        
        Returns:
            The created Curriculum object.
            
        Raises:
            LearningError: If there's an error creating the curriculum.
        """
        try:
            # Import here to avoid circular imports
            from curriculum_models import Curriculum
            
            # Get parameters with defaults
            target_language = kwargs.get('target_language', 'English')
            cefr_level = kwargs.get('cefr_level', 'A2')
            days = kwargs.get('days', 30)
            transcript = kwargs.get('transcript')
            llm_response = kwargs.get('llm_response')
            
            if llm_response:
                # If we have a manual LLM response, parse it directly
                curriculum_dict = self.curriculum_generator._parse_comprehensive_response(llm_response)
            else:
                # Otherwise, generate the curriculum using the LLM
                curriculum_dict = self.curriculum_generator.generate_curriculum(
                    learning_goal=learning_goal,
                    target_language=target_language,
                    cefr_level=cefr_level,
                    days=days,
                    transcript=transcript
                )
            
            # Normalize the days data if it's a dictionary
            if isinstance(curriculum_dict.get('days'), dict):
                days_data = []
                for day_key, day_content in curriculum_dict['days'].items():
                    if isinstance(day_content, dict):
                        # If the day content is a dictionary, use it directly
                        day_data = day_content.copy()
                        
                        # Ensure all required fields are present with defaults
                        day_num = None
                        if 'day' not in day_data:
                            # Try to extract day number from the key (e.g., 'day_1' -> 1)
                            try:
                                day_num = int(day_key.split('_')[-1])
                                day_data['day'] = day_num
                            except (ValueError, IndexError, AttributeError):
                                # If we can't extract the day number, use the key as is
                                day_num = day_key
                                day_data['day'] = day_num
                        else:
                            day_num = day_data['day']
                        
                        # Set default values for required fields if not provided
                        if 'title' not in day_data:
                            day_data['title'] = f"Day {day_num}"
                        if 'focus' not in day_data:
                            day_data['focus'] = f"Learning focus for day {day_num}"
                        if 'collocations' not in day_data:
                            day_data['collocations'] = []
                        if 'presentation_phrases' not in day_data:
                            day_data['presentation_phrases'] = []
                        if 'learning_objective' not in day_data:
                            day_data['learning_objective'] = f"Learn about {learning_goal}"
                        if 'story_guidance' not in day_data:
                            day_data['story_guidance'] = ""
                        
                        # Filter out any unexpected fields that CurriculumDay doesn't accept
                        expected_fields = {
                            'day', 'title', 'focus', 'collocations', 
                            'presentation_phrases', 'learning_objective', 'story_guidance'
                        }
                        day_data = {k: v for k, v in day_data.items() if k in expected_fields}
                        
                        days_data.append(day_data)
                    else:
                        # If the day content is a string, create a basic day structure
                        day_num = day_key
                        try:
                            day_num = int(day_key.split('_')[-1])
                        except (ValueError, IndexError, AttributeError):
                            pass
                            
                        days_data.append({
                            'day': day_num,
                            'title': f"Day {day_num}",
                            'focus': str(day_content),
                            'collocations': [],
                            'presentation_phrases': [],
                            'learning_goal': f"Learn about {learning_goal}",
                            'story_guidance': ""
                        })
                curriculum_dict['days'] = days_data
            
            # Map and filter the curriculum data to match the expected fields
            mapped_curriculum_data = {}
            
            # Include expected fields
            expected_curriculum_fields = {
                'learning_goal', 'target_language', 'cefr_level', 'days',
                'presentation_length', 'metadata'
            }
            
            # Add other fields that exist in the expected fields
            for field in expected_curriculum_fields:
                if field in curriculum_dict and field != 'cefr_level':  # Skip cefr_level as we've already mapped it
                    mapped_curriculum_data[field] = curriculum_dict[field]
            
            # Ensure learning_goal is set (use the one passed to the method if not in the dict)
            if 'learning_goal' not in mapped_curriculum_data and learning_goal:
                mapped_curriculum_data['learning_goal'] = learning_goal
            
            # Ensure required fields have default values if not provided
            if 'presentation_length' not in mapped_curriculum_data:
                mapped_curriculum_data['presentation_length'] = 15  # Default presentation length in minutes
            
            # Ensure target_language is set
            if 'target_language' not in mapped_curriculum_data:
                mapped_curriculum_data['target_language'] = 'English'  # Default target language
            
            # Ensure learner_level is set (use 'B1' as default if not provided)
            if 'learner_level' not in mapped_curriculum_data:
                mapped_curriculum_data['learner_level'] = 'B1'
            
            # Create a Curriculum object from the mapped and filtered data
            curriculum = Curriculum.from_dict(mapped_curriculum_data)
            
            # Save the curriculum
            self._current_curriculum = curriculum
            self._current_day = 1
            
            return curriculum
            
        except (ValidationError, LLMError, ParserError) as e:
            raise LearningError(f"Failed to create curriculum: {str(e)}")
    
    def extract_collocations(self) -> Dict[str, List[str]]:
        """
        Extract collocations from the current curriculum.
        
        Returns:
            Dictionary mapping day numbers to lists of collocations.
            
        Raises:
            LearningError: If no curriculum is loaded.
        """
        if not self._current_curriculum:
            raise LearningError("No curriculum loaded. Please create or load a curriculum first.")
        
        collocations = {}
        for day in self._current_curriculum.days:
            text = f"{day.title} {day.focus} {day.learning_goal} {' '.join(day.presentation_phrases)}"
            collocations[day.day] = self.collocation_extractor.extract_collocations(text)
            
        return collocations
    
    def generate_day_content(self, day: int) -> DayContent:
        """
        Generate content for a specific day.
        
        Args:
            day: The day number (1-based).
            
        Returns:
            DayContent object containing the day's learning materials.
            
        Raises:
            LearningError: If no curriculum is loaded or the day is invalid.
        """
        if not self._current_curriculum:
            raise LearningError("No curriculum loaded. Please create or load a curriculum first.")
        
        if day < 1 or day > len(self._current_curriculum.days):
            raise LearningError(f"Invalid day: {day}. Must be between 1 and {len(self._current_curriculum.days)}")
        
        # Get the curriculum day
        curriculum_day = self._current_curriculum.days[day - 1]
        
        # Generate story using the existing story generator
        story_params = StoryParams(
            topic=curriculum_day.title,
            focus=curriculum_day.focus,
            collocations=curriculum_day.collocations,
            level=CEFRLevel[curriculum_day.cefr_level],
            length=500  # Default length
        )
        
        try:
            story = self.content_generator.generate_story(story_params)
        except Exception as e:
            logger.error(f"Failed to generate story for day {day}: {str(e)}")
            story = f"Could not generate story: {str(e)}"
        
        # Create DayContent object
        day_content = DayContent(
            day=day,
            title=curriculum_day.title,
            focus=curriculum_day.focus,
            story=story,
            new_collocations=curriculum_day.collocations,
            # For now, review collocations are empty - could be enhanced with SRS
            review_collocations=[]
        )
        
        return day_content
    
    def get_progress(self) -> ProgressInfo:
        """
        Get the learner's progress information.
        
        Returns:
            ProgressInfo object containing progress details.
            
        Raises:
            LearningError: If no curriculum is loaded.
        """
        if not self._current_curriculum:
            raise LearningError("No curriculum loaded. Please create or load a curriculum first.")
        
        total_days = len(self._current_curriculum.days)
        completion_percentage = (self._current_day / total_days) * 100
        
        return ProgressInfo(
            current_day=self._current_day,
            total_days=total_days,
            completion_percentage=completion_percentage
        )
    
    def get_current_day(self) -> int:
        """
        Get the current day in the curriculum.
        
        Returns:
            The current day number (1-based).
            
        Raises:
            LearningError: If no curriculum is loaded.
        """
        if not self._current_curriculum:
            raise LearningError("No curriculum loaded. Please create or load a curriculum first.")
            
        return self._current_day
    
    def set_current_day(self, day: int) -> None:
        """
        Set the current day in the curriculum.
        
        Args:
            day: The day number to set (1-based).
            
        Raises:
            LearningError: If no curriculum is loaded or the day is invalid.
        """
        if not self._current_curriculum:
            raise LearningError("No curriculum loaded. Please create or load a curriculum first.")
            
        if day < 1 or day > len(self._current_curriculum.days):
            raise LearningError(f"Invalid day: {day}. Must be between 1 and {len(self._current_curriculum.days)}")
            
        self._current_day = day
    
    def load_curriculum(self, file_path: Union[str, Path]) -> None:
        """
        Load a curriculum from a file.
        
        Args:
            file_path: Path to the curriculum file (can be relative or absolute).
                     If relative, will be resolved against the curricula directory.
            
        Raises:
            LearningError: If there's an error loading the curriculum.
        """
        try:
            # Convert to Path object if it's a string
            path = Path(file_path)
            
            # If path is not absolute, try to resolve it relative to the data directory
            if not path.is_absolute():
                # Try the root data directory first
                path_in_data_dir = self.data_dir / path
                # Then try the curricula subdirectory
                path_in_curricula_dir = self.data_dir / 'curricula' / path
                
                # Check which path exists
                if path_in_data_dir.exists():
                    path = path_in_data_dir
                elif path_in_curricula_dir.exists():
                    path = path_in_curricula_dir
                else:
                    # Raise error with both paths for debugging
                    raise FileNotFoundError(
                        f"Curriculum file not found. Tried:\n"
                        f"- {path_in_data_dir}\n"
                        f"- {path_in_curricula_dir}"
                    )
            
            # Ensure the file exists (should be true if we got here, but double-check)
            if not path.exists():
                raise FileNotFoundError(f"Curriculum file not found: {path}")
                
            # Load the curriculum data directly
            with open(path, 'r', encoding='utf-8') as f:
                logger.info(f"Loading curriculum from: {path}")
                data = json.load(f)
                
            # Create a Curriculum object from the loaded data
            logger.info(f"Creating Curriculum object from data: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
            self._current_curriculum = Curriculum.from_dict(data)
            self._current_day = 1
            
            logger.info(f"Successfully loaded curriculum from {path}")
            return self._current_curriculum
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from {path}: {str(e)}")
            raise LearningError(f"Invalid curriculum file: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading curriculum from {file_path}: {str(e)}", exc_info=True)
            raise LearningError(f"Failed to load curriculum: {str(e)}")
    
    def save_curriculum(self, file_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Save the current curriculum to a file.
        
        Args:
            file_path: Optional path to save the curriculum. If not provided,
                     uses a default path in the data directory.
                     
        Returns:
            Path where the curriculum was saved.
            
        Raises:
            LearningError: If no curriculum is loaded or there's an error saving.
        """
        if not self._current_curriculum:
            raise LearningError("No curriculum loaded. Please create or load a curriculum first.")
        
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = self.data_dir / f"curriculum_{timestamp}.json"
        else:
            file_path = Path(file_path)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._current_curriculum.to_dict(), f, indent=2, ensure_ascii=False)
            return file_path
        except Exception as e:
            raise LearningError(f"Failed to save curriculum: {str(e)}")

# Singleton instance for easy import
learning_service = LearningService()
