"""
Story Collocation Extractor for TunaTale SRS Feedback System.

Extracts actual Filipino collocations from generated story files to enable
proper feedback processing and SRS analysis.
"""

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional, Set
import logging


@dataclass
class StoryCollocations:
    """Represents collocations extracted from a story file."""
    day: int
    story_file: str
    extraction_date: str
    
    # Different sections of collocations
    key_phrases: List[str]           # From Key Phrases section
    dialogue_phrases: List[str]      # From Natural Speed dialogue
    all_tagalog_phrases: List[str]   # All [TAGALOG-*]: phrases
    
    # Analysis
    total_unique_phrases: int
    english_phrases: List[str]       # Any English that appeared
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class StoryCollocationExtractor:
    """Extract actual collocations from TunaTale story files."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def extract_from_story_file(self, story_path: Path) -> StoryCollocations:
        """Extract collocations from a story file.
        
        Args:
            story_path: Path to the story file
            
        Returns:
            StoryCollocations object with extracted phrases
        """
        if not story_path.exists():
            raise FileNotFoundError(f"Story file not found: {story_path}")
            
        story_content = story_path.read_text(encoding='utf-8')
        
        # Extract day number from filename or content
        day = self._extract_day_number(story_path, story_content)
        
        # Extract different types of collocations
        key_phrases = self._extract_key_phrases_section(story_content)
        dialogue_phrases = self._extract_dialogue_collocations(story_content)
        all_tagalog_phrases = self._extract_all_tagalog_phrases(story_content)
        english_phrases = self._extract_english_phrases(story_content)
        
        # Remove duplicates while preserving order
        unique_phrases = self._deduplicate_preserving_order(all_tagalog_phrases)
        
        from datetime import datetime
        
        return StoryCollocations(
            day=day,
            story_file=str(story_path),
            extraction_date=datetime.now().isoformat(),
            key_phrases=key_phrases,
            dialogue_phrases=dialogue_phrases,
            all_tagalog_phrases=unique_phrases,
            total_unique_phrases=len(unique_phrases),
            english_phrases=english_phrases
        )
    
    def _extract_day_number(self, story_path: Path, content: str) -> int:
        """Extract day number from filename or content."""
        # Try filename first: story_day12_*, demo-0.0.3-day-4.txt, etc.
        filename = story_path.name
        
        # Pattern 1: story_day12_*
        match = re.search(r'story_day(\d+)', filename)
        if match:
            return int(match.group(1))
            
        # Pattern 2: demo-*-day-4.txt
        match = re.search(r'day-(\d+)', filename)
        if match:
            return int(match.group(1))
            
        # Pattern 3: Look in content for [NARRATOR]: Day X:
        match = re.search(r'\[NARRATOR\]:\s*Day\s*(\d+)', content)
        if match:
            return int(match.group(1))
            
        # Fallback: extract any number from filename
        match = re.search(r'(\d+)', filename)
        if match:
            return int(match.group(1))
            
        self.logger.warning(f"Could not extract day number from {filename}, using 0")
        return 0
    
    def _extract_key_phrases_section(self, content: str) -> List[str]:
        """Extract collocations from the Key Phrases section."""
        phrases = []
        
        # Find the Key Phrases section
        lines = content.split('\n')
        in_key_phrases = False
        
        for line in lines:
            line = line.strip()
            
            # Start of Key Phrases section
            if line == "Key Phrases:":
                in_key_phrases = True
                continue
                
            # End of Key Phrases section (Natural Speed starts)
            if in_key_phrases and "[NARRATOR]: Natural Speed" in line:
                break
                
            # Extract Tagalog phrases in Key Phrases section
            if in_key_phrases and line.startswith("[TAGALOG-"):
                phrase = self._extract_phrase_from_line(line)
                if phrase and phrase not in phrases:
                    phrases.append(phrase)
                    
        return phrases
    
    def _extract_dialogue_collocations(self, content: str) -> List[str]:
        """Extract collocations from Natural Speed dialogue section."""
        phrases = []
        
        # Find the Natural Speed section
        lines = content.split('\n')
        in_natural_speed = False
        
        for line in lines:
            line = line.strip()
            
            # Start of Natural Speed section
            if "[NARRATOR]: Natural Speed" in line:
                in_natural_speed = True
                continue
                
            # End of Natural Speed section (Slow Speed starts)
            if in_natural_speed and "[NARRATOR]: Slow Speed" in line:
                break
                
            # Extract Tagalog phrases in dialogue
            if in_natural_speed and line.startswith("[TAGALOG-"):
                phrase = self._extract_phrase_from_line(line)
                if phrase and phrase not in phrases:
                    phrases.append(phrase)
                    
        return phrases
    
    def _extract_all_tagalog_phrases(self, content: str) -> List[str]:
        """Extract all [TAGALOG-*]: phrases from the entire story."""
        phrases = []
        
        # Use regex to find all [TAGALOG-*]: lines
        pattern = r'\[TAGALOG-[^\]]+\]:\s*(.+)'
        matches = re.findall(pattern, content, re.MULTILINE)
        
        for match in matches:
            phrase = match.strip()
            if phrase and phrase not in phrases:
                phrases.append(phrase)
                
        return phrases
    
    def _extract_phrase_from_line(self, line: str) -> Optional[str]:
        """Extract the actual phrase from a [TAGALOG-*]: line."""
        # Pattern: [TAGALOG-FEMALE-1]: phrase
        match = re.match(r'\[TAGALOG-[^\]]+\]:\s*(.+)', line)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_english_phrases(self, content: str) -> List[str]:
        """Extract any English phrases that might need to be blocked."""
        english_phrases = []
        
        # Look for common English patterns in dialogue
        english_patterns = [
            r'\b(good morning|good evening|hello|hi|bye|goodbye)\b',
            r'\b(thank you|thanks|please|excuse me|sorry)\b', 
            r'\b(yes|no|okay|ok)\b',
            r'\b(how much|how are you|what is|where is)\b'
        ]
        
        for pattern in english_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    for submatch in match:
                        if submatch and submatch.lower() not in english_phrases:
                            english_phrases.append(submatch.lower())
                else:
                    if match.lower() not in english_phrases:
                        english_phrases.append(match.lower())
                        
        return english_phrases
    
    def _deduplicate_preserving_order(self, phrases: List[str]) -> List[str]:
        """Remove duplicates while preserving order."""
        seen = set()
        result = []
        for phrase in phrases:
            if phrase not in seen:
                seen.add(phrase)
                result.append(phrase)
        return result
    
    def extract_from_day_number(self, day: int, stories_dir: Optional[Path] = None) -> Optional[StoryCollocations]:
        """Extract collocations from a story by day number.
        
        Args:
            day: Day number to extract
            stories_dir: Directory containing story files (defaults to instance/data/stories)
            
        Returns:
            StoryCollocations object or None if story not found
        """
        if stories_dir is None:
            stories_dir = Path("instance/data/stories")
            
        if not stories_dir.exists():
            self.logger.error(f"Stories directory not found: {stories_dir}")
            return None
            
        # Try different naming patterns
        patterns = [
            f"story_day{day}_*.txt",
            f"*day-{day}.txt", 
            f"*day{day}_*.txt"
        ]
        
        for pattern in patterns:
            matching_files = list(stories_dir.glob(pattern))
            if matching_files:
                # Use the first match
                story_file = matching_files[0]
                self.logger.info(f"Found story file for day {day}: {story_file.name}")
                return self.extract_from_story_file(story_file)
                
        self.logger.warning(f"No story file found for day {day}")
        return None
    
    def save_extraction(self, extraction: StoryCollocations, output_dir: Optional[Path] = None) -> Path:
        """Save extraction results to JSON file.
        
        Args:
            extraction: StoryCollocations object to save
            output_dir: Directory to save to (defaults to instance/data/analysis)
            
        Returns:
            Path to saved file
        """
        if output_dir is None:
            output_dir = Path("instance/data/analysis")
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"day_{extraction.day}_collocations.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extraction.to_dict(), f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Saved collocation extraction to {output_file}")
        return output_file


def main():
    """Command-line interface for testing."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python story_collocation_extractor.py <story_file_or_day_number>")
        sys.exit(1)
        
    arg = sys.argv[1]
    extractor = StoryCollocationExtractor()
    
    try:
        # Try as day number first
        day = int(arg)
        extraction = extractor.extract_from_day_number(day)
        if extraction is None:
            print(f"No story found for day {day}")
            sys.exit(1)
    except ValueError:
        # Treat as file path
        story_path = Path(arg)
        extraction = extractor.extract_from_story_file(story_path)
    
    # Print results
    print(f"\\n=== Day {extraction.day} Collocations ===")
    print(f"Story: {extraction.story_file}")
    print(f"Total unique phrases: {extraction.total_unique_phrases}")
    
    print(f"\\nKey Phrases ({len(extraction.key_phrases)}):")
    for phrase in extraction.key_phrases:
        print(f"  - {phrase}")
        
    print(f"\\nDialogue Phrases ({len(extraction.dialogue_phrases)}):")
    for phrase in extraction.dialogue_phrases:
        print(f"  - {phrase}")
        
    if extraction.english_phrases:
        print(f"\\nEnglish Phrases Found ({len(extraction.english_phrases)}):")
        for phrase in extraction.english_phrases:
            print(f"  - {phrase}")
    
    # Save results
    output_file = extractor.save_extraction(extraction)
    print(f"\\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()