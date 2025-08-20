"""Story generation functionality for TunaTale."""
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

import config

from llm_mock import MockLLM
from srs_tracker import SRSTracker
from collocation_extractor import CollocationExtractor
from curriculum_models import Curriculum, CurriculumDay
from content_strategy import (
    ContentStrategy, 
    DifficultyLevel, 
    EnhancedStoryParams,
    get_strategy_config
)
from prompt_generator import DayPromptGenerator, create_prompt_generator
from mock_srs import MockSRS, create_mock_srs, LessonVocabularyReport

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
    length: int = field(default_factory=lambda: config.DEFAULT_STORY_LENGTH)
    new_vocabulary: List[str] = field(default_factory=list)
    recycled_vocabulary: List[str] = field(default_factory=list)
    recycled_collocations: List[str] = field(default_factory=list)
    focus: str = ""
    story_guidance: str = ""
    source_day: Optional[int] = None
    source_day_transcript: Optional[str] = None
    
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
        # Load prompts for chat-based approach (graceful for testing)
        try:
            self.system_prompt = self._load_prompt('system_prompt.txt')
            self.day_prompt_template = self._load_prompt('day_prompt_template.txt')
        except FileNotFoundError:
            # For testing environments without chat prompts
            self.system_prompt = "Test system prompt"
            self.day_prompt_template = "Test day prompt template"
        
        # Legacy prompts (for backward compatibility)
        self.story_prompt = self._load_prompt('story_prompt_balanced.txt')  # Default/BALANCED
        
        # Try to load strategy-specific prompts, but don't fail if not available (for tests)
        try:
            self.story_prompt_deeper = self._load_prompt('story_prompt_deeper.txt')
        except FileNotFoundError:
            self.story_prompt_deeper = None  # For testing environments
            
        try:
            self.story_prompt_wider = self._load_prompt('story_prompt_wider.txt')
        except FileNotFoundError:
            self.story_prompt_wider = None  # For testing environments
        
        # New two-part prompt architecture (with safe initialization)
        try:
            self.prompt_generator = create_prompt_generator()
            self.mock_srs = create_mock_srs()
        except Exception:
            # For testing environments where new prompts may not exist
            self.prompt_generator = None
            self.mock_srs = None
        
        # Legacy SRS (for existing functionality)
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
        prompt_path = config.PROMPTS_DIR / filename
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
            
            # Format the day-specific prompt according to story_prompt_template.txt structure
            day_prompt = self.story_prompt.format(
                learning_objective=params.learning_objective,
                focus=params.focus or f"Language learning - Phase {params.phase}",
                learner_level=cefr_level,
                new_collocations=new_vocab,
                review_collocations=recycled_collocs,
                story_guidance=params.story_guidance or "Create an engaging story incorporating the target vocabulary."
            )
            
            # Get the story from the LLM using system/day prompt separation
            response = self.llm.chat_response(
                system_prompt=self.system_prompt,
                user_prompt=day_prompt,
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

    def generate_chat_story(self, params: StoryParams, day_number: int) -> Optional[str]:
        """
        Generate a story using the new chat-based approach with separate system and day prompts.
        
        Args:
            params: Story parameters 
            day_number: The day number for the story
            
        Returns:
            Generated story content or None if generation failed
        """
        try:
            # Format the day-specific prompt
            new_collocations_text = "\n".join(f"- {collocation}" for collocation in params.new_vocabulary)
            review_collocations_text = "\n".join(f"- {collocation}" for collocation in params.recycled_collocations)
            
            day_prompt = self.day_prompt_template.format(
                day_number=day_number,
                learning_objective=params.learning_objective,
                focus=params.focus or f"Language learning - Phase {params.phase}",
                learner_level=params.cefr_level,
                new_collocations=new_collocations_text,
                review_collocations=review_collocations_text,
                story_guidance=params.story_guidance or f"Generate engaging content for day {day_number}"
            )
            
            # Use the chat-based LLM method
            response = self.llm.chat_response(
                system_prompt=self.system_prompt,
                user_prompt=day_prompt,
                response_type="story"
            )
            
            # Handle both direct response format and nested response format
            if response:
                if 'choices' in response and len(response['choices']) > 0:
                    # Direct format
                    story = response['choices'][0]['message']['content']
                    return story.strip() if story else None
                elif 'response' in response and 'choices' in response['response'] and len(response['response']['choices']) > 0:
                    # Nested format from chat_response
                    story = response['response']['choices'][0]['message']['content']
                    return story.strip() if story else None
            
            return None
            
        except Exception as e:
            import traceback
            print(f"Error generating chat story: {e}")
            traceback.print_exc()
            return None

    def generate_enhanced_story(self, params: EnhancedStoryParams) -> Optional[str]:
        """
        Generate a story using enhanced parameters with strategy support.
        
        Args:
            params: Enhanced story generation parameters with strategy info
            
        Returns:
            Generated story text or None if generation fails
        """
        try:
            # Select appropriate prompt based on strategy
            if params.content_strategy == ContentStrategy.DEEPER and self.story_prompt_deeper:
                prompt_template = self.story_prompt_deeper
            elif params.content_strategy == ContentStrategy.WIDER and self.story_prompt_wider:
                prompt_template = self.story_prompt_wider
            else:
                # Use default template for BALANCED or fallback
                prompt_template = self.story_prompt
            
            # Get strategy configuration
            strategy_config = get_strategy_config(params.content_strategy)
            
            # Format new collocations and review collocations
            new_vocab = ", ".join(params.new_vocabulary) if params.new_vocabulary else "None"
            recycled_collocs = ", ".join(params.review_collocations) if params.review_collocations else "None"
            
            # Prepare prompt parameters
            prompt_params = {
                'learning_objective': params.learning_objective,
                'focus': params.focus or f"Language learning - Phase {params.phase}",
                'learner_level': params.cefr_level,
                'new_collocations': new_vocab,
                'review_collocations': recycled_collocs,
                'story_guidance': params.story_guidance or "Create an engaging story incorporating the target vocabulary.",
                'phase': params.phase
            }
            
            # Add strategy-specific parameters
            if params.content_strategy == ContentStrategy.DEEPER and params.source_day:
                prompt_params['source_day'] = params.source_day
                prompt_params['source_day_transcript'] = params.source_day_transcript or "No source transcript available"
            elif params.content_strategy == ContentStrategy.WIDER:
                # Add WIDER-specific parameters from strategy configuration
                if hasattr(strategy_config, 'expansion_settings') and strategy_config.expansion_settings:
                    expansion = strategy_config.expansion_settings
                    prompt_params.update({
                        'source_day': params.source_day or 'previous day',
                        'scenario_types': ', '.join(expansion.scenario_types),
                        'character_variety': expansion.character_variety,
                        'setting_complexity': expansion.setting_complexity,
                        'interaction_types': ', '.join(expansion.interaction_types),
                        'maintain_difficulty': str(expansion.maintain_difficulty_level).lower(),
                        'max_new_words': expansion.max_new_words_per_scenario,
                        'reuse_patterns': str(expansion.reuse_familiar_patterns).lower()
                    })
                else:
                    # Fallback values for WIDER strategy
                    prompt_params.update({
                        'source_day': params.source_day or 'previous day',
                        'scenario_types': 'restaurant, transportation, shopping',
                        'character_variety': '3',
                        'setting_complexity': '2',
                        'interaction_types': 'ordering, asking_directions, negotiating_price',
                        'maintain_difficulty': 'true',
                        'max_new_words': '5',
                        'reuse_patterns': 'true'
                    })
            
            # Format the strategy-specific prompt
            strategy_prompt = prompt_template.format(**prompt_params)
            
            # Get the story from the LLM using chat-based approach with system/strategy separation
            logging.info(f"\n--- Enhanced Story Generation ({params.content_strategy.value.upper()}) ---")
            logging.info(f"Day {params.phase}: {params.learning_objective}")
            logging.info(f"Focus: {params.focus}")
            logging.info(f"Strategy: {params.content_strategy.value}")
            if params.source_day:
                logging.info(f"Source Day: {params.source_day}")
            logging.info(f"New collocations: {new_vocab}")
            logging.info(f"Review collocations: {recycled_collocs}")
            
            # Use chat_response to separate system prompt from strategy prompt
            response = self.llm.chat_response(
                system_prompt=self.system_prompt,
                user_prompt=strategy_prompt,
                response_type="story"
            )
            
            logging.debug(f"LLM response type: {type(response)}")
            logging.debug(f"LLM response keys: {response.keys() if isinstance(response, dict) else 'Not a dict'}")
            
            # Handle both direct and nested response formats from MockLLM
            if not response:
                logging.error("No response from LLM")
                return None
            
            # Check for nested response format (MockLLM cache format)
            if 'response' in response and 'choices' in response['response']:
                story = response['response']['choices'][0]['message']['content'].strip()
            # Check for direct response format
            elif 'choices' in response:
                story = response['choices'][0]['message']['content'].strip()
            else:
                logging.error(f"Invalid LLM response format. Response keys: {response.keys() if isinstance(response, dict) else 'Not a dict'}")
                return None
            
            if not story:
                logging.error("Empty story generated")
                return None
            
            # Apply post-processing to fix Pimsleur breakdowns
            logging.info("Applying post-processing corrections to story content")
            from utils.content_post_processor import post_process_story_content
            story = post_process_story_content(story)
            
            # Extract and update collocations if needed
            try:
                extracted_collocations = self.collocation_extractor.extract_collocations(story)
                logging.info(f"Extracted {len(extracted_collocations)} collocations from generated story")
            except Exception as e:
                logging.warning(f"Failed to extract collocations: {e}")
                
            return story
            
        except Exception as e:
            logging.error(f"Error generating enhanced story: {e}")
            import traceback
            traceback.print_exc()
            return None


    def generate_day_with_srs(
        self, 
        day: int, 
        strategy: ContentStrategy = ContentStrategy.BALANCED,
        source_day: Optional[int] = None,
        learning_objective: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate content using the new two-part prompt architecture with SRS integration.
        
        Args:
            day: Day number for the lesson
            strategy: Content generation strategy (WIDER/DEEPER/BALANCED)
            source_day: Source day for DEEPER strategy (which day to enhance)
            learning_objective: Optional override for learning objective
            
        Returns:
            Generated story content or None if generation fails
        """
        try:
            logging.info(f"\n--- SRS-Informed Story Generation ---")
            logging.info(f"Day: {day}")
            logging.info(f"Strategy: {strategy.value}")
            if source_day:
                logging.info(f"Source Day: {source_day}")
            
            # Generate system and day prompts separately using two-part architecture
            system_prompt = self.prompt_generator.load_system_prompt()
            day_prompt = self.prompt_generator.generate_day_prompt(
                day=day,
                strategy=strategy,
                source_day=source_day,
                learning_objective=learning_objective
            )
            
            # Get vocabulary constraints from mock SRS
            srs_data = self.mock_srs.get_srs_data_for_prompt(day, strategy)
            
            logging.info(f"Vocabulary constraints:")
            logging.info(f"  - Learned: {len(srs_data['learned_vocabulary'])} words")
            logging.info(f"  - Review: {len(srs_data['review_vocabulary'])} words") 
            logging.info(f"  - New limit: {srs_data['new_vocabulary_limit']}")
            logging.info(f"  - Difficulty: {srs_data['difficulty_level']}")
            
            # Generate content using LLM with system/day prompt separation
            logging.info(f"Calling MockLLM with response_type='story'")
            logging.debug(f"System prompt length: {len(system_prompt)} characters")
            logging.debug(f"Day prompt length: {len(day_prompt)} characters")
            response = self.llm.chat_response(
                system_prompt=system_prompt,
                user_prompt=day_prompt,
                response_type="story"
            )
            
            if not response or 'choices' not in response:
                logging.error("Invalid LLM response format")
                return None
                
            story = response['choices'][0]['message']['content'].strip()
            
            if not story:
                logging.error("Empty story generated")
                return None
            
            # Extract vocabulary that was actually used (simplified mock)
            vocabulary_report = self._analyze_vocabulary_usage(
                story, 
                srs_data['learned_vocabulary'],
                srs_data['review_vocabulary']
            )
            
            # Update mock SRS with lesson results
            self.mock_srs.update_from_lesson(day, vocabulary_report)
            
            # Save the story
            saved_path = self._save_story(story, day, learning_objective or f"Day {day} Content")
            
            logging.info(f"Story generated and saved to: {saved_path}")
            logging.info(f"Vocabulary report:")
            logging.info(f"  - New introduced: {len(vocabulary_report.introduced_new)}")
            logging.info(f"  - Review reinforced: {len(vocabulary_report.reinforced_review)}")
            
            return story
            
        except Exception as e:
            logging.error(f"Error generating SRS-informed story: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _analyze_vocabulary_usage(
        self, 
        story: str, 
        learned_vocab: List[str], 
        review_vocab: List[str]
    ) -> LessonVocabularyReport:
        """
        Analyze vocabulary usage in generated story using improved extraction.
        
        This uses the SRSPhraseExtractor for better phrase identification.
        """
        try:
            from srs_phrase_extractor import SRSPhraseExtractor
            extractor = SRSPhraseExtractor()
            return extractor.analyze_vocabulary_usage_improved(story, learned_vocab, review_vocab)
        except ImportError:
            # Fallback to original simple implementation if extractor not available
            logging.warning("SRSPhraseExtractor not available, using simple extraction")
            return self._analyze_vocabulary_usage_simple(story, learned_vocab, review_vocab)
    
    def _analyze_vocabulary_usage_simple(
        self, 
        story: str, 
        learned_vocab: List[str], 
        review_vocab: List[str]
    ) -> LessonVocabularyReport:
        """
        Simple vocabulary analysis fallback.
        """
        story_lower = story.lower()
        
        # Check which review vocabulary was reinforced
        reinforced_review = [word for word in review_vocab if word.lower() in story_lower]
        
        # Mock detection of new vocabulary (simplified)
        # In real implementation, this would extract Filipino phrases not in learned_vocab
        introduced_new = []
        
        # Look for common new vocabulary patterns in the story
        new_vocab_indicators = [
            "ano po", "saan po", "kailan po", "paano po", "bakit po",
            "masarap po", "mahal po", "mura po", "malaki po", "maliit po"
        ]
        
        for phrase in new_vocab_indicators:
            if phrase in story_lower and phrase not in [v.lower() for v in learned_vocab]:
                introduced_new.append(phrase)
        
        # Limit to realistic numbers
        introduced_new = introduced_new[:3]  # Max 3 new items detected
        
        return LessonVocabularyReport(
            introduced_new=introduced_new,
            reinforced_review=reinforced_review,
            unexpected_vocabulary=[]  # Mock doesn't detect unexpected vocabulary
        )


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

    def _save_story(self, story: str, phase: int, learning_objective: str, strategy: 'ContentStrategy' = None, source_day: int = None) -> str:
        """Save the generated story to a file.
        
        Args:
            story: The story content to save
            phase: The learning phase number
            learning_objective: The learning objective for the story (required)
            strategy: Content generation strategy (optional)
            source_day: Source day for DEEPER/WIDER strategies (optional)
            
        Returns:
            str: Path to the saved story file
            
        Raises:
            ValueError: If learning_objective is empty or None
        """
        if not learning_objective or not learning_objective.strip():
            raise ValueError("learning_objective cannot be empty")
            
        # Ensure STORIES_DIR exists
        output_dir = Path(config.STORIES_DIR) if isinstance(config.STORIES_DIR, str) else config.STORIES_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create smart filename with strategy information
        strategy_suffix = ""
        if strategy:
            from content_strategy import ContentStrategy
            if strategy == ContentStrategy.DEEPER:
                strategy_suffix = f"_deeper"
                if source_day:
                    strategy_suffix += f"_from{source_day}"
            elif strategy == ContentStrategy.WIDER:
                strategy_suffix = f"_wider"
                if source_day:
                    strategy_suffix += f"_from{source_day}"
            # BALANCED strategy gets no suffix (default)
        
        # Try to extract title from story content
        title = self._extract_title(story)
        if title:
            clean_title = self._clean_filename(title)
            if clean_title:
                filename = f"story_day{phase:02d}_{clean_title}{strategy_suffix}.txt"
                story_path = output_dir / filename
                return self._write_story_file(story_path, story)
                    
        # Fall back to learning objective if no title found or if file exists
        clean_obj = self._clean_filename(learning_objective)
        if not clean_obj:  # Fallback if no valid characters remain
            clean_obj = f"phase{phase}_story"
            
        # Create the full filename with the required format including strategy
        filename = f"story_day{phase:02d}_{clean_obj}{strategy_suffix}.txt"
        story_path = output_dir / filename
        
        return self._write_story_file(story_path, story)
        
    def _load_source_day_transcript(self, source_day: int) -> Optional[str]:
        """Load the source day story transcript for enhancement."""
        try:
            # Try to find story file for the source day
            stories_dir = Path(config.STORIES_DIR)
            
            # Look for story files matching the day in multiple formats
            story_files = []
            
            # Try multiple naming patterns
            patterns = [
                f"story_day{source_day}_*.txt",  # Original format
                f"*day-{source_day}.txt",        # demo-0.0.3-day-4.txt format
                f"*day{source_day}_*.txt"        # story_day4_*.txt format
            ]
            
            for pattern in patterns:
                found_files = list(stories_dir.glob(pattern))
                if found_files:
                    story_files.extend(found_files)
            
            if story_files:
                # Use the first matching file
                with open(story_files[0], 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logging.warning(f"No story file found for source day {source_day}")
                return None
                
        except Exception as e:
            logging.error(f"Error loading source day transcript: {e}")
            return None
        
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
        return Curriculum.load(config.CURRICULUM_PATH)
            
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
                recycled_vocabulary=[],
                focus=day_data.focus,
                story_guidance=day_data.story_guidance
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
    
    def generate_strategy_based_story(self, target_day: int, strategy: 'ContentStrategy', source_day: int = None) -> Optional[Tuple[str, List[Dict[str, List[str]]]]]:
        """Generate a story using strategy-based content generation.
        
        Args:
            target_day: The day number for the new story
            strategy: ContentStrategy (DEEPER, WIDER, BALANCED)
            source_day: Source day to base content on (required for DEEPER/WIDER)
            
        Returns:
            A tuple of (generated_story, collocation_report) if successful, None otherwise
        """
        try:
            from content_strategy import ContentStrategy, DifficultyLevel
            
            curriculum = self._load_curriculum()
            
            # For DEEPER strategy, we need a source day
            if strategy == ContentStrategy.DEEPER and not source_day:
                logging.error(f"Strategy {strategy.value} requires a source_day parameter")
                return None
            
            if strategy == ContentStrategy.DEEPER:
                return self._generate_deeper_content(target_day, source_day, curriculum)
            elif strategy == ContentStrategy.WIDER:
                return self._generate_wider_content(target_day, curriculum)
            else:  # BALANCED - use regular generation
                return self.generate_day_story(target_day)
                
        except Exception as e:
            logging.error(f"Error generating strategy-based story for day {target_day}: {e}", exc_info=True)
            return None
    
    def _generate_deeper_content(self, target_day: int, source_day: int, curriculum) -> Optional[Tuple[str, List[Dict[str, List[str]]]]]:
        """Generate DEEPER strategy content - enhanced Filipino authenticity."""
        # Get source day data
        source_data = curriculum.get_day(source_day)
        if not source_data:
            logging.error(f"No curriculum found for source day {source_day}")
            return None
        
        # Load source day transcript for enhancement
        source_transcript = self._load_source_day_transcript(source_day)
        if not source_transcript:
            logging.warning(f"No source day transcript found for day {source_day}, using curriculum data only")
            source_transcript = f"Source day curriculum data:\nTitle: {source_data.title}\nFocus: {source_data.focus}\nCollocations: {', '.join(source_data.collocations)}"
        
        logging.info(f"\n--- DEEPER Strategy Generation ---")
        logging.info(f"Target day {target_day} based on source day {source_day}: {source_data.title}")
        
        # Create enhanced curriculum data for deeper content
        enhanced_collocations = self._enhance_collocations_for_deeper(source_data.collocations)
        enhanced_phrases = self._enhance_phrases_for_deeper(source_data.presentation_phrases)
        
        # Get review collocations from SRS
        review_collocations = self.srs.get_due_collocations(target_day, min_items=2, max_items=4)
        
        # Create enhanced story guidance for deeper Filipino
        deeper_guidance = f"{source_data.story_guidance}. DEEPER STRATEGY: Use more authentic Filipino expressions, reduce English, include cultural context and native speech patterns."
        
        # Create enhanced story parameters for strategy-based generation
        from content_strategy import EnhancedStoryParams, DifficultyLevel
        params = EnhancedStoryParams(
            learning_objective=f"DEEPER VERSION: {source_data.learning_objective} with enhanced Filipino authenticity",
            language=curriculum.target_language,
            cefr_level="B1",  # Slightly elevated for deeper content
            phase=target_day,
            content_strategy=ContentStrategy.DEEPER,
            difficulty_level=DifficultyLevel.INTERMEDIATE,
            source_day=source_day,
            source_day_transcript=source_transcript,
            new_vocabulary=enhanced_phrases,
            review_collocations=enhanced_collocations + review_collocations,
            story_guidance=deeper_guidance,
            focus=f"Enhanced Filipino authenticity: {source_data.focus}"
        )
        
        # Generate the story using strategy-specific approach
        story = self.generate_enhanced_story(params)
        if not story:
            return None
        
        # Save the story to file
        try:
            story_path = self._save_story(story, target_day, params.learning_objective, params.content_strategy, params.source_day)
            logging.info(f"Story saved to: {story_path}")
        except Exception as e:
            logging.warning(f"Failed to save story file: {e}")
        
        # Analyze collocations (simplified for strategy content)
        collocation_report = {
            'new': enhanced_collocations[:3],  # Show first 3 enhanced collocations
            'reviewed': review_collocations,
            'bonus': []  # Will be populated by analysis if available
        }
        
        # Extend curriculum with the new day
        enhanced_learning_objective = f"Enhanced {source_data.learning_objective} with sophisticated Filipino"
        extension_success = self._extend_curriculum_with_new_day(
            curriculum, target_day, enhanced_learning_objective, source_data.focus, enhanced_collocations[:6], "deeper"
        )
        if not extension_success:
            logging.warning(f"Story generated but curriculum extension failed for day {target_day}")
        
        logging.info(f"✅ DEEPER strategy story generated for day {target_day}")
        return story, collocation_report
    
    def _generate_wider_content(self, target_day: int, curriculum) -> Optional[Tuple[str, List[Dict[str, List[str]]]]]:
        """Generate WIDER strategy content - expanded scenarios based on curriculum progression."""
        logging.info(f"\n--- WIDER Strategy Generation ---")
        logging.info(f"Target day {target_day}: Creating new scenarios based on curriculum progression")
        
        # Analyze curriculum progression to determine appropriate difficulty and themes
        curriculum_analysis = self._analyze_curriculum_progression(curriculum)
        
        # Generate new scenarios based on curriculum patterns
        new_focus = self._generate_new_scenario_focus(curriculum_analysis, target_day)
        
        # Create collocations appropriate for target day difficulty level
        wider_collocations = self._generate_progressive_collocations(curriculum_analysis, target_day)
        
        # Get review collocations from SRS
        review_collocations = self.srs.get_due_collocations(target_day, min_items=4, max_items=6)
        
        # Create learning objective based on curriculum progression
        learning_objective = f"Day {target_day}: {new_focus} - Building on curriculum foundation"
        
        # Create story parameters
        params = StoryParams(
            learning_objective=learning_objective,
            language=curriculum.target_language,
            cefr_level=curriculum.learner_level,
            phase=target_day,
            length=curriculum.presentation_length * 15,  # Longer for more scenarios
            new_vocabulary=wider_collocations[:6],  # New collocations for this scenario
            recycled_collocations=review_collocations,
            recycled_vocabulary=[],
            focus=new_focus,
            story_guidance=f"WIDER STRATEGY: Create new scenarios and contexts while maintaining appropriate difficulty progression from the existing {len(curriculum.days)}-day curriculum."
        )
        
        # Generate the story using chat-based approach
        story = self.generate_chat_story(params, target_day)
        if not story:
            return None
        
        # Save the story to file
        try:
            story_path = self._save_story(story, target_day, params.learning_objective, "wider")
            logging.info(f"Story saved to: {story_path}")
        except Exception as e:
            logging.warning(f"Failed to save story file: {e}")
        
        # Analyze collocations
        collocation_report = {
            'new': wider_collocations[:4],
            'reviewed': review_collocations,
            'bonus': []
        }
        
        # Extend curriculum with the new day
        extension_success = self._extend_curriculum_with_new_day(
            curriculum, target_day, learning_objective, new_focus, wider_collocations[:6], "wider"
        )
        if not extension_success:
            logging.warning(f"Story generated but curriculum extension failed for day {target_day}")
        
        logging.info(f"✅ WIDER strategy story generated for day {target_day}")
        return story, collocation_report
    
    def _analyze_curriculum_progression(self, curriculum) -> Dict[str, Any]:
        """Analyze curriculum to understand difficulty progression and common themes."""
        analysis = {
            'total_days': len(curriculum.days),
            'common_themes': [],
            'vocabulary_progression': [],
            'complexity_level': curriculum.learner_level,
            'presentation_length': curriculum.presentation_length
        }
        
        # Extract themes from existing days
        for day in curriculum.days:
            if hasattr(day, 'focus'):
                analysis['common_themes'].append(day.focus)
            if hasattr(day, 'collocations'):
                analysis['vocabulary_progression'].extend(day.collocations[:3])  # Sample from each day
        
        # Remove duplicates while preserving order
        analysis['common_themes'] = list(dict.fromkeys(analysis['common_themes']))
        analysis['vocabulary_progression'] = list(dict.fromkeys(analysis['vocabulary_progression']))
        
        return analysis
    
    def _generate_new_scenario_focus(self, curriculum_analysis: Dict[str, Any], target_day: int) -> str:
        """Generate new scenario focus that expands on curriculum themes."""
        base_themes = curriculum_analysis['common_themes']
        
        # El Nido scenario expansions that build on common travel themes
        scenario_extensions = [
            "Exploring hidden lagoons and boat tours",
            "Local island hopping and snorkeling adventures", 
            "Traditional Filipino cooking experiences",
            "Shopping for local crafts and souvenirs at markets",
            "Experiencing Filipino hospitality and cultural exchanges",
            "Adventure activities: kayaking and rock climbing",
            "Sunset viewing and photography at scenic spots",
            "Local transportation and getting around islands"
        ]
        
        # Select scenario based on target day to ensure variety
        scenario_index = (target_day - 1) % len(scenario_extensions)
        return scenario_extensions[scenario_index]
    
    def _generate_progressive_collocations(self, curriculum_analysis: Dict[str, Any], target_day: int) -> List[str]:
        """Generate collocations appropriate for target day difficulty progression."""
        base_collocations = [
            "salamat po", "kumusta po", "magkano po", "puwede po ba",
            "sarap naman", "ganda talaga", "saan po", "paano po"
        ]
        
        # Add complexity based on target day
        if target_day > 10:
            # More advanced collocations for later days
            advanced_collocations = [
                "nakakamangha talaga", "sulit na sulit", "hindi ko inexpect",
                "masaya naman dito", "sobrang ganda", "worth it ba"
            ]
            # Replace some basic ones with advanced ones for higher days
            result = base_collocations[:5] + advanced_collocations[:3]
            return result
        
        return base_collocations[:8]  # Limit to reasonable number
    
    def _enhance_collocations_for_deeper(self, base_collocations: List[str]) -> List[str]:
        """Enhance collocations for DEEPER strategy - more authentic Filipino."""
        enhanced = []
        for collocation in base_collocations:
            # Add cultural authenticity markers
            if "po" not in collocation and any(word in collocation for word in ["salamat", "excuse", "magkano"]):
                enhanced.append(f"{collocation} po")
            else:
                enhanced.append(collocation)
            
            # Add more complex Filipino variants
            if collocation == "salamat po":
                enhanced.append("maraming salamat po")
            elif collocation == "magkano po":
                enhanced.append("magkano po ang presyo nito")
                
        return enhanced[:6]  # Limit to prevent overwhelming
    
    def _enhance_phrases_for_deeper(self, base_phrases: List[str]) -> List[str]:
        """Enhance phrases for DEEPER strategy with more Filipino context."""
        enhanced = []
        for phrase in base_phrases:
            enhanced.append(phrase)
            # Add cultural context variations
            if "thank you" in phrase.lower():
                enhanced.append("thank you very much (with cultural respect)")
            elif "how much" in phrase.lower():
                enhanced.append("what is the exact price")
                
        return enhanced
    
    def _expand_scenario_for_wider(self, base_focus: str) -> str:
        """Expand scenario focus for WIDER strategy."""
        # Add more contexts and situations
        scenario_expansions = {
            "airport": "airport, bus terminal, and taxi interactions",
            "hotel": "hotel, resort, and accommodation interactions", 
            "restaurant": "restaurant, café, and street food interactions",
            "shopping": "shopping, market, and souvenir interactions",
            "beach": "beach, island, and water activity interactions",
            "transportation": "transportation, directions, and local travel",
            "dining": "dining, local specialties, and food exploration"
        }
        
        for key, expansion in scenario_expansions.items():
            if key in base_focus.lower():
                return expansion
                
        return f"{base_focus} and expanded related scenarios"
    
    def _add_scenario_collocations(self, base_focus: str) -> List[str]:
        """Add scenario-specific collocations for WIDER strategy."""
        additional = []
        
        if "hotel" in base_focus.lower():
            additional.extend(["puwede po ba", "may available po ba", "anong floor po"])
        elif "restaurant" in base_focus.lower():
            additional.extend(["masarap po ba", "fresh po ba", "specialty ninyong"])
        elif "shopping" in base_focus.lower():
            additional.extend(["meron pa po ba", "discount po", "cash or card"])
        elif "beach" in base_focus.lower():
            additional.extend(["safe po ba", "life jacket po", "boat ride po"])
            
        return additional[:3]  # Limit additional collocations
    
    def _extend_curriculum_with_new_day(self, curriculum, target_day: int, learning_objective: str, focus: str, collocations: List[str], strategy: str) -> bool:
        """Extend curriculum with a new day and save it to file."""
        try:
            from curriculum_models import CurriculumDay
            
            # Create new curriculum day
            new_day = CurriculumDay(
                day=target_day,
                title=f"Day {target_day}: {focus}",
                learning_objective=learning_objective,
                focus=focus,
                collocations=collocations,
                presentation_phrases=collocations[:4],  # Use first few as presentation phrases
                story_guidance=f"Generated using {strategy.upper()} strategy"
            )
            
            # Add the new day to curriculum
            curriculum.days.append(new_day)
            
            # Save updated curriculum
            curriculum_path = config.CURRICULUM_PATH
            curriculum.save(curriculum_path)
            
            logging.info(f"✅ Extended curriculum with day {target_day} using {strategy} strategy")
            logging.info(f"Curriculum now has {len(curriculum.days)} days")
            return True
            
        except Exception as e:
            logging.error(f"Failed to extend curriculum with day {target_day}: {e}")
            return False
    
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
        story_path = Path(config.STORIES_DIR) / f'day{prev_day}_story.txt'
        
        if story_path.exists():
            with open(story_path, 'r') as f:
                return f.read()
        return ""
