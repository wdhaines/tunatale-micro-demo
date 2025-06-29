"""Curriculum generation and management service for TunaTale."""
import datetime
from datetime import timezone
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Type, TypeVar

# Try to import config values, with fallbacks for testing
try:
    from config import PROMPTS_DIR, CURRICULUM_PATH, DATA_DIR
except ImportError:
    # Fallback values for testing
    TEST_DIR = Path(__file__).parent.parent / 'tests'
    PROMPTS_DIR = TEST_DIR / 'prompts'
    DATA_DIR = TEST_DIR / 'test_data'
    CURRICULUM_PATH = DATA_DIR / 'curriculum_processed.json'
    
    # Ensure test directories exist
    PROMPTS_DIR.mkdir(exist_ok=True, parents=True)
    DATA_DIR.mkdir(exist_ok=True, parents=True)

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
    
    def _load_prompt(self, filename: str, allow_default: bool = True) -> str:
        """
        Load a prompt template from file.
        
        Args:
            filename: Name of the prompt file to load
            allow_default: If True and file doesn't exist, return default prompt without writing to disk.
                          If False, raise FileNotFoundError.
            
        Returns:
            str: The loaded prompt template or default prompt if allow_default is True
            
        Raises:
            FileNotFoundError: If the prompt file doesn't exist and allow_default is False
            IOError: If there's an error reading the prompt file
        """
        prompt_path = PROMPTS_DIR / filename
        
        try:
            # Try to read the existing file
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:  # Only return if file has content
                    return content
                
                # File exists but is empty
                logger.warning(f"Prompt file {prompt_path} is empty")
                if not allow_default:
                    raise IOError(f"Prompt file {prompt_path} is empty")
                    
        except FileNotFoundError:
            if not allow_default:
                raise
            logger.info(f"Prompt file {prompt_path} not found, using default"
                      )
        except IOError as e:
            logger.error(f"Error reading prompt file {prompt_path}: {e}")
            if not allow_default:
                raise
                
        # Return default prompt without writing to disk
        return self.config.default_prompt
    
    def generate_comprehensive_curriculum(
        self, 
        learning_objective: str, 
        presentation_transcript: str = "",
        learner_level: str = "A2",
        presentation_length: int = 30,
        output_path: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive curriculum using the detailed template.
        
        Args:
            learning_objective: The main learning objective/topic
            presentation_transcript: Optional transcript of the target presentation
            learner_level: CEFR level (A1, A2, B1, etc.)
            presentation_length: Target presentation length in minutes
            output_path: Optional path to save the curriculum
            
        Returns:
            Dict containing the generated curriculum data
            
        Raises:
            ValidationError: If the learning goal is invalid
            LLMError: If there's an error generating the curriculum
            ParserError: If there's an error parsing the LLM response
        """
        try:
            # Validate inputs
            if not learning_objective or not isinstance(learning_objective, str):
                raise ValidationError("Learning objective must be a non-empty string")
                
            # Load the comprehensive template
            template = self._load_prompt('curriculum_template.txt')
            if not template:
                raise FileNotFoundError("Comprehensive curriculum template not found")
            
            # Format the prompt with parameters
            prompt = template.format(
                learning_objective=learning_objective,
                target_language="English",
                learner_level=learner_level,
                presentation_length=presentation_length,
                presentation_transcript=presentation_transcript,
                # Add any additional parameters from the template
                num_days=30,  # Default 30-day curriculum
            )
            
            # Generate the curriculum using the LLM
            logger.info("Generating comprehensive curriculum...")
            response = self.llm.get_response(prompt, response_type="comprehensive_curriculum")
            
            # Log the raw response for debugging
            logger.debug(f"Raw LLM response: {json.dumps(response, indent=2)[:1000]}...")
            
            # Extract content from the response structure
            try:
                if not response or 'choices' not in response or not response['choices']:
                    raise LLMError("Invalid response format from LLM: missing or empty 'choices'")
                    
                # Get the first choice's message content
                message = response['choices'][0].get('message', {})
                content = message.get('content', '')
                
                if not content:
                    raise LLMError("Empty content in LLM response")
                    
                logger.debug(f"Extracted content from LLM response (first 200 chars): {content[:200]}...")
                
                # Parse the response into the expected format
                curriculum = self._parse_comprehensive_response(content)
                
            except (KeyError, IndexError, TypeError) as e:
                logger.error(f"Error processing LLM response: {e}")
                raise LLMError(f"Failed to process LLM response: {e}")
                
            # Save the curriculum if output path is provided
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(curriculum, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved comprehensive curriculum to {output_path}")
            
            return curriculum
            
        except Exception as e:
            logger.error(f"Error generating comprehensive curriculum: {e}")
            if not isinstance(e, (ValidationError, LLMError, ParserError)):
                raise LLMError(f"Unexpected error generating curriculum: {e}") from e
            raise
    
    def _parse_comprehensive_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the LLM response into a structured curriculum format.
        
        Extracts only the curriculum structure including day number, title, focus,
        target collocations, presentation phrases, and learning objective based on focus.
        Does not extract or store generated stories.
        
        Args:
            response_text: Raw text response from the LLM
            
        Returns:
            Dict containing the structured curriculum data
            
        Raises:
            ParserError: If the response cannot be parsed
        """
        try:
            # Initialize curriculum structure
            curriculum = {
                'learning_objective': "",
                'target_language': "English",
                'learner_level': "A2",
                'presentation_length': 30,
                'days': [],
                'metadata': {
                    'generated_at': str(datetime.datetime.now(timezone.utc)),
                    'version': '1.0',
                    'is_template': True  # Indicate this is a template, not final content
                }
            }
            
            # Extract learning objective from the response if available
            objective_match = re.search(r'# TunaTale (\d+-Day )?Curriculum: (.+)', response_text, re.IGNORECASE)
            if objective_match:
                curriculum['learning_objective'] = objective_match.group(2).strip()
            
            # Extract days using a more flexible pattern to handle different formats
            day_sections = re.split(r'##\s*Day\s*(\d+)', response_text, flags=re.IGNORECASE)[1:]
            
            for i in range(0, len(day_sections), 2):
                if i + 1 >= len(day_sections):
                    break
                    
                day_num = int(day_sections[i].strip())
                day_content = day_sections[i+1].strip()
                
                # Extract title (first line after day header)
                title_match = re.search(r'^\s*([^\n]+)', day_content)
                title = title_match.group(1).strip() if title_match else f"Day {day_num}"
                
                # Extract focus (look for a line starting with Focus: or similar)
                focus_match = re.search(r'(?:Focus|Topic|Theme)[:\s]+([^\n]+)', day_content, re.IGNORECASE)
                focus = focus_match.group(1).strip() if focus_match else ""
                
                # Extract collocations (handle multiple formats)
                collocations = []
                collocations_match = re.search(
                    r'(?:Target )?(?:Collocations|Phrases|Vocabulary)[:\s]+([^\n]+)', 
                    day_content, 
                    re.IGNORECASE
                )
                
                if collocations_match:
                    # Handle different delimiters: commas, slashes, newlines
                    colloc_text = collocations_match.group(1).strip()
                    # Split by commas, then by slashes, then clean up
                    collocations = [
                        c.strip(' "\'.,;') 
                        for part in colloc_text.split(',')
                        for c in part.split('/')
                        if c.strip()
                    ]
                    # Filter to only include 3-5 word phrases
                    collocations = [
                        c for c in collocations 
                        if 3 <= len(c.split()) <= 5
                    ]
                
                # Extract presentation phrases (similar to collocations but look for specific heading)
                phrases_match = re.search(
                    r'(?:Presentation )?Phrases?[\s:]+([^\n]+(?:\n[^\n]+)*)', 
                    day_content, 
                    re.IGNORECASE
                )
                presentation_phrases = []
                if phrases_match:
                    # Split by newlines and clean up
                    presentation_phrases = [
                        p.strip(' -•*') 
                        for p in phrases_match.group(1).split('\n')
                        if p.strip()
                    ]
                
                # Extract story guidance if present
                guidance_match = re.search(
                    r'(?:Story )?Guidance[\s:]+([^\n]+(?:\n[^\n]+)*)', 
                    day_content, 
                    re.IGNORECASE
                )
                story_guidance = guidance_match.group(1).strip() if guidance_match else ""
                
                # Create learning objective from focus if not provided
                learning_objective = f"Learn and practice {focus.lower()}" if focus else f"Day {day_num} Learning Objectives"
                
                # Add day to curriculum
                curriculum['days'].append({
                    'day': day_num,
                    'title': title,
                    'focus': focus,
                    'collocations': collocations[:5],  # Limit to 5 collocations
                    'presentation_phrases': presentation_phrases[:5],  # Limit to 5 phrases
                    'learning_objective': learning_objective,
                    'story_guidance': story_guidance
                })
            
            # Ensure we have at least one day
            if not curriculum['days']:
                raise ParserError("No valid days found in curriculum response")
                
            return curriculum
            
        except Exception as e:
            raise ParserError(f"Failed to parse curriculum response: {e}") from e
        
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
            str: The loaded prompt template or default content if not found
            
        Note:
            This method will not create or modify any files on disk.
            It will return the default prompt template if the file doesn't exist.
        """
        return self._load_prompt('curriculum_template.txt', allow_default=True)
    
    def generate_curriculum(
        self,
        learning_goal: str,
        target_language: str = 'English',
        cefr_level: str = 'A2',
        days: int = 30,
        transcript: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """
        Generate a curriculum based on the learning goal and parameters.
        
        Args:
            learning_goal: The learning objective for the curriculum
            target_language: The target language for the curriculum
            cefr_level: CEFR level (A1, A2, B1, B2, C1, C2)
            days: Number of days for the curriculum
            transcript: Optional transcript of the target presentation
            output_path: Optional path to save the curriculum (defaults to CURRICULUM_PATH)
            
        Returns:
            Dict containing the generated curriculum data
            
        Raises:
            ValidationError: If the learning goal is invalid
            LLMError: If there's an error generating the curriculum
        """
        self._validate_learning_goal(learning_goal)
        
        # Validate CEFR level
        cefr_level = cefr_level.upper()
        if cefr_level not in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
            raise ValidationError(f"Invalid CEFR level: {cefr_level}. Must be one of: A1, A2, B1, B2, C1, C2")
            
        # Validate days
        if days < 1 or days > 365:  # Reasonable limits
            raise ValidationError(f"Number of days must be between 1 and 365, got {days}")
        
        try:
            # Format the prompt with all parameters
            prompt = self.curriculum_prompt.format(
                learning_objective=learning_goal,
                target_language=target_language,
                learner_level=cefr_level,
                presentation_length=days,
                presentation_transcript=transcript or ""
            )
            
            # Get response from LLM
            try:
                response = self.llm.generate(prompt)
                
                # Validate response format
                if not response or 'choices' not in response or not response['choices']:
                    raise LLMError("Invalid response format from LLM")
                
                # Extract content from the first choice
                curriculum_content = response['choices'][0]['message']['content']
                
                # Initialize curriculum with basic structure
                curriculum = {
                    'learning_goal': learning_goal,
                    'target_language': target_language,
                    'cefr_level': cefr_level,
                    'days': {},
                    'metadata': {
                        'generated_at': datetime.datetime.now(timezone.utc).isoformat(),
                        'transcript_used': transcript is not None,
                        'format': 'text',
                        'version': '1.0'
                    },
                    'content': curriculum_content
                }
                
                # Generate the curriculum using the LLM with the template
                prompt = self.curriculum_prompt.format(
                    learning_objective=learning_goal,
                    target_language=target_language,
                    learner_level=cefr_level,
                    presentation_length=days,
                    presentation_transcript=transcript or ""
                )
                
                # Get response from LLM
                try:
                    response = self.llm.generate(prompt)
                    curriculum_content = response['choices'][0]['message']['content']
                    
                    # Parse the LLM response into structured curriculum
                    curriculum['content'] = curriculum_content
                    curriculum['metadata']['format'] = 'text'
                    
                    # Try to extract structured days from the response
                    try:
                        parsed_days = self._parse_curriculum_days(curriculum_content)
                        if parsed_days:
                            curriculum['days'] = parsed_days
                            curriculum['metadata']['format'] = 'json'
                    except Exception as parse_error:
                        logger.warning(f"Could not parse days from LLM response: {parse_error}")
                        # Fall back to a single day with the full content
                        curriculum['days'] = {
                            'day_1': {
                                'title': f'Introduction to {learning_goal}',
                                'content': curriculum_content,
                                'focus': learning_goal,
                                'collocations': [],
                                'vocabulary': [],
                                'activities': []
                            }
                        }
                except Exception as e:
                    logger.error(f"Error generating curriculum with LLM: {e}")
                    raise LLMError(f"Failed to generate curriculum: {e}")
                
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
    
    def _save_curriculum(self, curriculum: Union[str, dict], learning_goal: str, output_path: Optional[Union[str, Path]] = None) -> None:
        """
        Save the generated curriculum to a file.
        
        Args:
            curriculum: The curriculum content to save (can be a string or a dict)
            learning_goal: The learning goal for the curriculum
            output_path: Path to save the curriculum (defaults to CURRICULUM_PATH in data directory)
            
        Raises:
            IOError: If there's an error writing the file
            ParserError: If there's an error parsing the curriculum
        """
        # Ensure we're using the data directory
        if output_path is None:
            output_path = CURRICULUM_PATH
        else:
            output_path = Path(output_path)
            # If it's not an absolute path, make it relative to the data directory
            if not output_path.is_absolute():
                output_path = DATA_DIR / output_path
        
        output_path = output_path.absolute()
        
        try:
            # Ensure the directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare the data to save
            if isinstance(curriculum, dict):
                # If curriculum is already a dict, use it directly
                curriculum_data = curriculum
            else:
                # If it's a string, try to parse it as JSON
                try:
                    curriculum_data = json.loads(curriculum)
                    if not isinstance(curriculum_data, dict):
                        # If it's not a dict after parsing, create a proper structure
                        curriculum_data = {
                            'content': curriculum,
                            'days': {},
                            'metadata': {}
                        }
                except (json.JSONDecodeError, ValueError):
                    # If it's not valid JSON, create a basic structure
                    curriculum_data = {
                        'content': curriculum,
                        'days': {},
                        'metadata': {}
                    }
            
            # Ensure all required fields are present
            if 'learning_goal' not in curriculum_data:
                curriculum_data['learning_goal'] = learning_goal
                
            if 'days' not in curriculum_data:
                curriculum_data['days'] = {}
                
            if 'metadata' not in curriculum_data:
                curriculum_data['metadata'] = {}
                
            # Update metadata
            curriculum_data['metadata'].update({
                'generated_at': datetime.datetime.now(timezone.utc).isoformat(),
                'format': 'json' if 'content' in curriculum_data and isinstance(curriculum_data['content'], dict) else 'text',
                'version': '1.0'
            })
            
            # For string content, parse it into days
            if isinstance(curriculum, str) and 'content' not in curriculum_data:
                try:
                    days = self._parse_curriculum_days(curriculum)
                except Exception as e:
                    raise ParserError(f"Error parsing curriculum: {e}") from e
                
                curriculum_data = {
                    "learning_goal": learning_goal,
                    "content": curriculum,
                    "days": days,
                    "metadata": {
                        "num_days": len(days),
                        "generated_at": str(datetime.datetime.now(timezone.utc)),
                        "format": "text"
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
            raise ParserError(f"Invalid JSON in curriculum file: {e}") from e
            
    def _validate_curriculum_structure(self, curriculum_text: str) -> bool:
        """
        Validate the structure of the curriculum content.
        
        This method checks for either:
        1. Daily format: "Day 1:", "Day 2:", etc.
        2. Weekly format: "Week 1 (Days 1-7)", etc.
        
        Args:
            curriculum_text: The curriculum text to validate
            
        Raises:
            ValueError: If the curriculum structure is invalid
        """
        if not curriculum_text:
            raise ValueError("Empty curriculum content")
            
        # Check for weekly format first (e.g., "Week 1 (Days 1-7)")
        has_weekly_format = any(
            f"Week {i} (Days " in curriculum_text or 
            f"Week {i}:" in curriculum_text
            for i in range(1, (self.config.num_days // 7) + 2)  # +2 to be safe with partial weeks
        )
        
        # If not weekly format, check for daily format
        if not has_weekly_format:
            # Check for at least some day headers to validate daily format
            has_daily_format = any(
                f"Day {i}:" in curriculum_text or 
                f"Day {i} " in curriculum_text
                for i in range(1, min(8, self.config.num_days + 1))  # Check first 7 days
            )
            
            if not has_daily_format:
                raise ValueError(
                    "Invalid curriculum format. Expected either:"
                    "\n- Daily format (e.g., 'Day 1:', 'Day 2:'...)'"
                    "\n- Weekly format (e.g., 'Week 1 (Days 1-7):', 'Week 2 (Days 8-14):'...)"
                )
    
    def _parse_curriculum_days(self, curriculum_text: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse the curriculum text into structured day-by-day content.
        
        Handles various formats including:
        - Daily: "Day 1:", "Day 2:", etc.
        - Weekly: "Week 1 (Days 1-7):", "Week 2 (Days 8-14):", etc.
        - Markdown headers: "## Day 1", "## Week 1"
        - Custom formats with focus and collocations
        
        Args:
            curriculum_text: The raw curriculum text to parse
            
        Returns:
            Dict mapping day keys to structured day content
            
        Raises:
            ParserError: If there's an error in the curriculum format
        """
        days = {}
        current_day = None
        current_content = []
        current_metadata = {}
        
        # Normalize line endings and split into lines
        lines = curriculum_text.replace('\r\n', '\n').split('\n')
        
        def save_current_day():
            if current_day and (current_content or current_metadata):
                day_data = {
                    'title': current_metadata.get('title', f'Day {current_day}'),
                    'content': '\n'.join(current_content).strip(),
                    'focus': current_metadata.get('focus', ''),
                    'collocations': current_metadata.get('collocations', []),
                    'vocabulary': current_metadata.get('vocabulary', []),
                    'activities': current_metadata.get('activities', [])
                }
                days[f'day_{current_day}'] = day_data
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines between sections
            if not line and not current_day:
                continue
                
            # Check for day/week headers in various formats
            day_match = re.match(r'(?:##\s*)?(?:Day|Week)\s+(\d+)(?:\s*\(?Day[s\s]*(\d+)(?:-\s*(\d+))?\)?)?[:\-\s]*(.*)', line, re.IGNORECASE)
            if day_match:
                # Save previous day's content if exists
                save_current_day()
                
                # Start new day
                day_num = day_match.group(1)
                current_day = day_num
                current_content = []
                current_metadata = {}
                
                # Extract title if present
                title = day_match.group(4).strip()
                if title:
                    current_metadata['title'] = title
                
                continue
            
            # Check for metadata lines (key: value)
            meta_match = re.match(r'^\s*([A-Za-z\s]+):\s*(.+?)\s*$', line, re.IGNORECASE)
            if meta_match and current_day is not None:
                key = meta_match.group(1).lower().strip()
                value = meta_match.group(2).strip()
                
                # Handle different metadata types
                if key in ['focus', 'title']:
                    current_metadata[key] = value
                elif key in ['collocations', 'vocabulary', 'activities']:
                    if key not in current_metadata:
                        current_metadata[key] = []
                    # Split by commas or other delimiters
                    items = [item.strip() for item in re.split(r'[,\n]', value) if item.strip()]
                    current_metadata[key].extend(items)
                continue
                
            # Add content line if we're in a day section
            if current_day is not None and line:
                current_content.append(line)
        
        # Save the last day's content
        save_current_day()
        
        if not days:
            # If no structured days found, try to split by sections
            sections = re.split(r'(?i)(?:^|\n)(?=##?\s*(?:Day|Week)\s+\d+)', curriculum_text)
            if len(sections) > 1:
                for i, section in enumerate(sections[1:], 1):
                    days[f'day_{i}'] = {
                        'title': f'Day {i}',
                        'content': section.strip(),
                        'focus': '',
                        'collocations': [],
                        'vocabulary': [],
                        'activities': []
                    }
            else:
                # If all else fails, create a single day with all content
                days['day_1'] = {
                    'title': 'Complete Curriculum',
                    'content': curriculum_text.strip(),
                    'focus': '',
                    'collocations': [],
                    'vocabulary': [],
                    'activities': []
                }
            
        return days
