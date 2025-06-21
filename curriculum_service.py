import datetime
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Type, TypeVar
from config import PROMPTS_DIR, CURRICULUM_PATH
from llm_mock import MockLLM

# Type variable for generic type hints
T = TypeVar('T', bound='CurriculumError')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CurriculumError(Exception):
    """Base exception for curriculum-related errors."""
    pass

class ValidationError(CurriculumError):
    """Raised when input validation fails."""
    pass

class LLMError(CurriculumError):
    """Raised when there's an error with the LLM service."""
    pass

class ParserError(CurriculumError):
    """Raised when there's an error parsing the curriculum."""
    pass

@dataclass
class CurriculumConfig:
    """Configuration for curriculum generation."""
    num_days: int = 5
    required_sections: List[str] = field(
        default_factory=lambda: ["Topics", "Grammar", "Vocabulary", "Activities"]
    )
    default_prompt: str = """Create a {num_days}-day language learning curriculum for the following goal: {goal}

For each day, include:
1. Key phrases/concepts to learn (Topics)
2. Grammar points
3. Vocabulary focus
4. Suggested practice activities

Make it progressive, starting simple and building complexity.
Focus on practical, conversational language.
"""

class CurriculumGenerator:
    """
    A service for generating and managing language learning curriculums.
    
    Attributes:
        llm: The language model interface
        config: Configuration for curriculum generation
        curriculum_prompt: The template used for generating curriculums
    """
    
    def __init__(self, llm: Optional[Any] = None, config: Optional[CurriculumConfig] = None):
        """
        Initialize the CurriculumGenerator.
        
        Args:
            llm: Optional LLM instance (defaults to MockLLM)
            config: Optional configuration (defaults to default CurriculumConfig)
        """
        self.llm = llm if llm is not None else MockLLM()
        self.config = config if config is not None else CurriculumConfig()
        self.curriculum_prompt = self._load_prompt('curriculum_template.txt')
    
    def _load_prompt(self, filename: str) -> str:
        """
        Load a prompt template from file, creating a default if it doesn't exist.
        
        Args:
            filename: Name of the prompt file to load
            
        Returns:
            str: The loaded or created prompt template
            
        Raises:
            FileNotFoundError: If the prompt file doesn't exist and can't be created
            IOError: If there's an error reading or writing the prompt file
        """
        prompt_path = PROMPTS_DIR / filename
        
        # If file exists, try to read it
        if prompt_path.exists():
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # Only return if file has content
                        return content
            except IOError as e:
                logger.warning(f"Error reading prompt file {prompt_path}: {e}")
                # Continue to create a new file
        
        # If we get here, either file doesn't exist or was empty
        logger.info(f"Creating default prompt at {prompt_path}")
        try:
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(self.config.default_prompt)
            return self.config.default_prompt
        except IOError as e:
            logger.error(f"Failed to create default prompt file: {e}")
            # If we can't create the file, just return the default content
            return self.config.default_prompt
            
    def _load_prompt_template(self) -> str:
        """
        Load the curriculum prompt template.
        
        This is a convenience wrapper around _load_prompt for the curriculum template.
        
        Returns:
            str: The loaded prompt template
            
        Raises:
            FileNotFoundError: If the prompt file doesn't exist and can't be created
            IOError: If there's an error reading or writing the prompt file
        """
        return self._load_prompt('curriculum_template.txt')
    
    def generate_curriculum(self, learning_goal: str, output_path: Optional[Union[str, Path]] = None) -> str:
        """
        Generate a curriculum based on the learning goal.
        
        Args:
            learning_goal: The learning objective for the curriculum
            output_path: Optional path to save the curriculum (defaults to CURRICULUM_PATH)
            
        Returns:
            str: The generated curriculum text
            
        Raises:
            ValidationError: If the learning goal is invalid
            LLMError: If there's an error generating the curriculum
        """
        self._validate_learning_goal(learning_goal)
        
        try:
            logger.info(f"Generating curriculum for goal: {learning_goal}")
            
            # Create the prompt with the correct number of days
            prompt = self.curriculum_prompt.format(
                goal=learning_goal,
                num_days=self.config.num_days
            )
            
            # Get response from LLM
            try:
                response = self.llm.get_response(
                    prompt=prompt,
                    response_type="curriculum"
                )
                
                # Validate the response structure
                if not response or 'choices' not in response or not response['choices']:
                    raise LLMError("Invalid response format from LLM")
                    
                curriculum = response['choices'][0]['message']['content']
                
                # Validate the generated curriculum
                self._validate_curriculum(curriculum)
                
                # Save the curriculum
                save_path = Path(output_path) if output_path else CURRICULUM_PATH
                self._save_curriculum(curriculum, learning_goal, save_path)
                
                logger.info("Successfully generated and saved curriculum")
                return curriculum
                
            except Exception as e:
                logger.error(f"Error getting response from LLM: {e}")
                raise LLMError(f"Failed to generate curriculum: {e}") from e
                
        except Exception as e:
            logger.error(f"Error in generate_curriculum: {e}")
            if not isinstance(e, (ValidationError, LLMError)):
                raise LLMError(f"Unexpected error generating curriculum: {e}") from e
            raise
            
    def _validate_learning_goal(self, goal: str) -> None:
        """
        Validate the learning goal.
        
        Args:
            goal: The learning goal to validate
            
        Raises:
            ValidationError: If the goal is invalid
        """
        if not goal or not isinstance(goal, str):
            raise ValidationError("Learning goal must be a non-empty string")
            
        if len(goal.strip()) < 5:
            raise ValidationError("Learning goal is too short (minimum 5 characters)")
            
        if len(goal) > 1000:
            raise ValidationError("Learning goal is too long (maximum 1000 characters)")
    
    def _validate_curriculum(self, curriculum: str) -> None:
        """
        Validate the generated curriculum.
        
        Args:
            curriculum: The curriculum text to validate
            
        Raises:
            ValidationError: If the curriculum is invalid
        """
        if not curriculum or not isinstance(curriculum, str):
            raise ValidationError("Generated curriculum must be a non-empty string")
            
        # Check for minimum length (arbitrary threshold)
        if len(curriculum) < 100:
            raise ValidationError("Generated curriculum is too short")
            
        # Check for required day markers
        for day in range(1, self.config.num_days + 1):
            if f"Day {day}:" not in curriculum:
                raise ValidationError(f"Missing Day {day} in generated curriculum")
    
    def _save_curriculum(self, curriculum: str, learning_goal: str, output_path: Optional[Union[str, Path]] = None) -> None:
        """
        Save the generated curriculum to a file.
        
        Args:
            curriculum: The curriculum text to save
            learning_goal: The learning goal for the curriculum
            output_path: Path to save the curriculum (defaults to CURRICULUM_PATH)
            
        Raises:
            IOError: If there's an error writing the file
            ParserError: If there's an error parsing the curriculum
        """
        output_path = Path(output_path) if output_path else CURRICULUM_PATH
        output_path = output_path.absolute()
        
        try:
            # Ensure the directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Parse the curriculum into days
            try:
                days = self._parse_curriculum_days(curriculum)
            except Exception as e:
                raise ParserError(f"Error parsing curriculum: {e}") from e
            
            # Prepare the data to save
            curriculum_data = {
                "learning_goal": learning_goal,
                "content": curriculum,
                "days": days,
                "metadata": {
                    "num_days": len(days),
                    "generated_at": str(datetime.datetime.utcnow())
                }
            }
            
            # Write to a temporary file first, then rename (atomic write)
            temp_path = output_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(curriculum_data, f, indent=2, ensure_ascii=False)
            
            # On POSIX systems, this is atomic
            temp_path.replace(output_path)
            logger.info(f"Saved curriculum to {output_path}")
            
        except IOError as e:
            logger.error(f"Error saving curriculum to {output_path}: {e}")
            raise IOError(f"Failed to save curriculum: {e}") from e
    
    def _load_curriculum(self, file_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Load a saved curriculum from a JSON file.
        
        Args:
            file_path: Path to the curriculum file (defaults to CURRICULUM_PATH)
            
        Returns:
            Dict containing the loaded curriculum data
            
        Raises:
            FileNotFoundError: If the curriculum file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
            ParserError: If the curriculum data is invalid
        """
        file_path = Path(file_path) if file_path else CURRICULUM_PATH
        
        if not file_path.exists():
            raise FileNotFoundError(f"Curriculum file not found: {file_path}")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate the loaded data structure
            required_keys = ['learning_goal', 'content', 'days', 'metadata']
            if not all(key in data for key in required_keys):
                raise ParserError("Invalid curriculum format: missing required fields")
                
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing curriculum JSON: {e}")
            raise
            
    def _validate_curriculum_structure(self, curriculum_text: str) -> None:
        """
        Validate the structure of the curriculum content.
        
        Args:
            curriculum_text: The curriculum text to validate
            
        Raises:
            ValueError: If the curriculum structure is invalid
        """
        if not curriculum_text:
            raise ValueError("Empty curriculum content")
            
        # Check for required day sections
        days = {}
        current_day = None
        
        for day_num in range(1, self.config.num_days + 1):
            day_header = f"Day {day_num}:"
            if day_header.lower() not in curriculum_text.lower():
                raise ValueError(f"Missing {day_header} in curriculum")
        
        # Check for required sections in each day
        lines = curriculum_text.split('\n')
        current_day = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.lower().startswith('day '):
                current_day = line.split(':')[0].strip()
            
            # Check for required sections if we're in a day section
            if current_day:
                if any(section.lower() in line.lower() for section in self.config.required_sections):
                    continue
        
        # If we get here, all validations passed
        return True
            
    def _parse_curriculum_days(self, curriculum_text: str) -> Dict[str, List[str]]:
        """
        Parse the curriculum text into structured day-by-day content.
        
        Args:
            curriculum_text: The raw curriculum text to parse
            
        Returns:
            Dict mapping day names to lists of content lines
            
        Raises:
            ParserError: If there's an error in the curriculum format
        """
        if not curriculum_text:
            raise ParserError("Empty curriculum content")
            
        # First validate the overall structure
        try:
            self._validate_curriculum_structure(curriculum_text)
        except ValueError as e:
            raise ParserError(str(e)) from e
            
        days = {}
        current_day = None
        
        for line in curriculum_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check for day header (e.g., "Day 1:" or "Day 1 - Monday:")
            if line.lower().startswith('day '):
                # Extract just the day part (e.g., "Day 1" from "Day 1: Introduction")
                day_parts = line.split(':')
                current_day = day_parts[0].strip()
                days[current_day] = []
                
                # Add the rest of the line if it contains content
                if len(day_parts) > 1 and day_parts[1].strip():
                    days[current_day].append(day_parts[1].strip())
            
            # Add content to the current day
            elif current_day:
                # Skip list markers like "1.", "-", "*" at the start of lines
                line = line.lstrip('*- ').lstrip('0123456789.').strip()
                if line:  # Only add non-empty lines
                    days[current_day].append(line)
        
        # Validate that we found all required days
        expected_days = [f"Day {i+1}" for i in range(self.config.num_days)]
        missing_days = [day for day in expected_days if day not in days]
        
        if missing_days:
            raise ParserError(f"Missing content for days: {', '.join(missing_days)}")
        
        return days
