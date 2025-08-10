"""
Data models for managing language learning curriculum structure.

This module provides dataclasses for representing curriculum structure
and days, along with methods for serialization and deserialization.
"""

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Dict, Any, Optional, TypeVar, Type
import json


T = TypeVar('T', bound='Curriculum')


@dataclass
class CurriculumDay:
    """Represents a single day in the language learning curriculum.
    
    Attributes:
        day: The day number in the curriculum (1-based).
        title: The title of the day's lesson.
        focus: The main focus area for this day's content.
        collocations: List of target collocations for this day.
        presentation_phrases: List of key phrases for presentation.
        learning_objective: Specific objective for this day's story.
        story_guidance: Optional guidance for story generation.
    """
    day: int
    title: str
    focus: str
    collocations: List[str]
    presentation_phrases: List[str]
    learning_objective: str
    story_guidance: str = ""
    
    def __post_init__(self):
        """Validate the day number is positive."""
        if self.day < 1:
            raise ValueError("Day number must be positive")


@dataclass
class Curriculum:
    """Represents a complete language learning curriculum.
    
    Attributes:
        learning_objective: The overall learning objective of the curriculum.
        target_language: The target language for learning.
        learner_level: The proficiency level of the target learners.
        presentation_length: The expected length of presentations in minutes.
        days: List of CurriculumDay objects representing each day's plan.
        metadata: Additional metadata about the curriculum.
    """
    learning_objective: str
    target_language: str
    learner_level: str
    presentation_length: int
    days: List[CurriculumDay] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_day(self, day_num: int) -> Optional[CurriculumDay]:
        """Get the curriculum day with the specified day number.
        
        Args:
            day_num: The day number to retrieve (1-based).
            
        Returns:
            The CurriculumDay for the specified day, or None if not found.
        """
        for day in self.days:
            if day.day == day_num:
                return day
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the curriculum to a dictionary.
        
        Returns:
            A dictionary representation of the curriculum.
        """
        data = asdict(self)
        # Convert days to list of dicts
        data['days'] = [asdict(day) for day in self.days]
        return data
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create a Curriculum instance from a dictionary.
        
        Args:
            data: Dictionary containing curriculum data.
            
        Returns:
            A new Curriculum instance.
            
        Raises:
            ValueError: If the data is invalid.
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
            
        # Extract days data and create CurriculumDay objects
        days_data = data.pop('days', [])
        days = [CurriculumDay(**day_data) for day_data in days_data]
        
        return cls(days=days, **data)
    
    def save(self, path: Path) -> None:
        """Save the curriculum to a JSON file.
        
        Args:
            path: Path where the curriculum should be saved.
            
        Raises:
            ValueError: If the path is not a .json file.
        """
        if path.suffix.lower() != '.json':
            raise ValueError("Curriculum must be saved as a .json file")
        
        # LOG CORRUPTION DETECTION ON SAVE
        import logging
        import traceback
        import json
        data_dict = self.to_dict()
        data_str = json.dumps(data_dict)
        
        logging.error(f"CURRICULUM SAVE: Saving to {path}")
        
        if 'space exploration' in data_str:
            logging.error("🚨 SAVE CORRUPTION: space exploration found in curriculum being saved!")
            logging.error(f"SAVE CORRUPTION STACK TRACE:")
            for line in traceback.format_stack():
                logging.error(f"  {line.strip()}")
        
        if '"content":' in data_str:
            logging.error("🚨 SAVE CORRUPTION: 'content' field found in curriculum being saved!")
            logging.error(f"SAVE CORRUPTION STACK TRACE:")
            for line in traceback.format_stack():
                logging.error(f"  {line.strip()}")
            
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls: Type[T], path: Path) -> T:
        """Load a curriculum from a JSON file.
        
        Args:
            path: Path to the curriculum JSON file.
            
        Returns:
            A new Curriculum instance loaded from the file.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file is not a valid JSON or curriculum.
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # LOG CORRUPTION DETECTION
        import logging
        import traceback
        logging.error(f"CURRICULUM LOAD: Loading from {path}")
        logging.error(f"CURRICULUM LOAD: File size: {path.stat().st_size} bytes")
        
        # Check for corruption indicators
        data_str = json.dumps(data)
        if 'space exploration' in data_str:
            logging.error("🚨 CORRUPTION DETECTED: space exploration found in curriculum!")
            logging.error(f"CORRUPTION STACK TRACE:")
            for line in traceback.format_stack():
                logging.error(f"  {line.strip()}")
        
        if '"content":' in data_str:
            logging.error("🚨 CORRUPTION DETECTED: 'content' field found in curriculum!")
            logging.error(f"CORRUPTION STACK TRACE:")
            for line in traceback.format_stack():
                logging.error(f"  {line.strip()}")
                
        return cls.from_dict(data)
