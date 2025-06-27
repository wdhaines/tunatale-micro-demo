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
        
        Args:
            response_text: Raw text response from the LLM
            
        Returns:
            Dict containing the structured curriculum data
            
        Raises:
            ParserError: If the response cannot be parsed
        """
        try:
            # First, try to find a JSON block in the response
            import re
            
            # Look for a JSON block in the response
            json_match = re.search(r'```(?:json)?\n({.*})\n```', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON block: {e}")
            
            # If no JSON block found, try to parse the entire response as JSON
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                pass
            
            # If we get here, try to extract the curriculum from the text format
            curriculum = {
                'learning_objective': "",
                'target_language': "English",
                'learner_level': "A2",
                'presentation_length': 30,
                'days': [],
                'metadata': {
                    'generated_at': str(datetime.datetime.now(datetime.UTC)),
                    'version': '1.0',
                }
            }
            
            # Try to extract the learning objective from the response
            objective_match = re.search(r'# TunaTale 30-Day Curriculum: (.+)', response_text)
            if objective_match:
                curriculum['learning_objective'] = objective_match.group(1).strip()
            
            # Extract days
            day_sections = re.split(r'## Day (\d+)', response_text)[1:]
            for i in range(0, len(day_sections), 2):
                if i + 1 >= len(day_sections):
                    break
                    
                day_num = int(day_sections[i])
                day_content = day_sections[i+1].strip()
                
                # Extract story if present
                story_match = re.search(r'\*\*Word count\*\*: \d+\n\n([\s\S]+?)(?=\n\n## Day|\Z)', day_content, re.IGNORECASE)
                story = story_match.group(1).strip() if story_match else ""
                
                # Extract collocations if present
                collocations_match = re.search(r'\*\*Target collocations\*\*: ([^\n]+)', day_content)
                collocations = [c.strip('"\' ') for c in collocations_match.group(1).split('/')] if collocations_match else []
                
                curriculum['days'].append({
                    'day': day_num,
                    'content': day_content,
                    'story': story,
                    'collocations': collocations
                })
            
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
            # Format the prompt with all parameters (using uppercase to match template placeholders)
            prompt = self.curriculum_prompt.format(
                LEARNING_GOAL=learning_goal,
                TARGET_LANGUAGE=target_language,
                LEARNER_LEVEL=cefr_level,
                PRESENTATION_LENGTH=days,
                TARGET_PRESENTATION_TRANSCRIPT=transcript or ""
            )
            
            # Get response from LLM
            try:
                response = self.llm.generate(prompt)
                
                # Validate response format
                if not response or 'choices' not in response or not response['choices']:
                    raise LLMError("Invalid response format from LLM")
                    
                curriculum_content = response['choices'][0]['message']['content']
                
                # Parse the JSON response if it's a string
                try:
                    # First, ensure we have a properly structured curriculum dict
                    curriculum = {
                        'learning_goal': learning_goal,
                        'target_language': target_language,
                        'cefr_level': cefr_level,
                        'days': days,
                        'metadata': {
                            'generated_at': datetime.datetime.now(datetime.UTC).isoformat(),
                            'transcript_used': transcript is not None,
                            'format': 'json'
                        }
                    }
                    
                    # Try to parse the LLM response as JSON
                    try:
                        response_data = json.loads(curriculum_content)
                        if isinstance(response_data, dict):
                            # Update with any fields from the response
                            curriculum.update({
                                'learning_goal': response_data.get('learning_goal', learning_goal),
                                'target_language': response_data.get('target_language', target_language),
                                'cefr_level': response_data.get('cefr_level', cefr_level),
                                'days': response_data.get('days', days),
                                'content': json.dumps(response_data, indent=2)  # Store the JSON as a string
                            })
                            
                            # Update metadata if present in response
                            if 'metadata' in response_data and isinstance(response_data['metadata'], dict):
                                curriculum['metadata'].update(response_data['metadata'])
                        else:
                            # If response is not a dict, store it as content
                            curriculum['content'] = curriculum_content
                    except (json.JSONDecodeError, ValueError):
                        # If parsing fails, store the raw content
                        curriculum['content'] = curriculum_content
                        curriculum['metadata']['format'] = 'text'
                        
                except Exception as e:
                    logger.error(f"Error processing LLM response: {e}")
                    # Fall back to a minimal valid structure
                    curriculum = {
                        'learning_goal': learning_goal,
                        'target_language': target_language,
                        'cefr_level': cefr_level,
                        'days': days,
                        'content': curriculum_content,
                        'metadata': {
                            'generated_at': datetime.datetime.now(datetime.UTC).isoformat(),
                            'transcript_used': transcript is not None,
                            'format': 'text',
                            'error': str(e)
                        }
                    }
                
                # Save the curriculum
                save_path = Path(output_path) if output_path else CURRICULUM_PATH
                self._save_curriculum(curriculum['content'], learning_goal, save_path)
                
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
            
            # Prepare the data to save
            if isinstance(curriculum, dict):
                # If curriculum is already a dict, use it directly
                curriculum_data = curriculum
                curriculum_data['learning_goal'] = learning_goal
                if 'metadata' not in curriculum_data:
                    curriculum_data['metadata'] = {}
                curriculum_data['metadata'].update({
                    'generated_at': str(datetime.datetime.now(datetime.UTC)),
                    'format': 'json'
                })
            else:
                # For string content, parse it into days
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
                        "generated_at": str(datetime.datetime.now(datetime.UTC)),
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
        
        # If we get here, the structure is valid
        return True
            
    def _parse_curriculum_days(self, curriculum_text: str) -> Dict[str, List[str]]:
        """
        Parse the curriculum text into structured day-by-day content.
        
        Handles both daily and weekly formats:
        - Daily: "Day 1:", "Day 2:", etc.
        - Weekly: "Week 1 (Days 1-7):", "Week 2 (Days 8-14):", etc.
        
        Args:
            curriculum_text: The raw curriculum text to parse
            
        Returns:
            Dict mapping day/week names to lists of content lines
            
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
            
        # Check which format we're dealing with
        is_weekly_format = any(
            f"Week {i} (Days " in curriculum_text or 
            f"Week {i}:" in curriculum_text
            for i in range(1, (self.config.num_days // 7) + 2)
        )
        
        days = {}
        current_section = None
        current_content = []
        
        for line in curriculum_text.split('\n'):
            line = line.strip()
            if not line:
                if current_section and current_content:
                    days[current_section] = current_content
                    current_content = []
                continue
                
            # Check for weekly section headers
            if is_weekly_format and (
                line.lower().startswith('week ') and 
                ('(days ' in line.lower() or ':' in line)
            ):
                if current_section and current_content:
                    days[current_section] = current_content
                current_section = line.split(':', 1)[0].strip()
                current_content = [line]
            # Check for daily section headers
            elif line.lower().startswith('day ') and ':' in line:
                if current_section and current_content:
                    days[current_section] = current_content
                current_section = line.split(':', 1)[0].strip()
                current_content = [line]
            # Content lines
            elif current_section:
                current_content.append(line)
        
        # Add the last section
        if current_section and current_content:
            days[current_section] = current_content
            
        # If we're in daily format, validate that we have all required days
        if not is_weekly_format:
            expected_days = [f"Day {i}" for i in range(1, self.config.num_days + 1)]
            missing_days = [day for day in expected_days if day not in days]
            if missing_days:
                raise ParserError(f"Missing content for days: {', '.join(missing_days)}")
        
        return days
