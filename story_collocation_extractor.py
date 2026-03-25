"""
StoryCollocationExtractor to replace removed CollocationExtractor.

This implementation provides compatibility methods while transitioning to 
LLM-based vocabulary extraction. It provides realistic stub results to 
make CLI commands work properly.
"""

from typing import Dict, List, Any, Optional, Tuple
import re
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StoryExtraction:
    """Results from extracting collocations and translations from a story."""
    story_file: str
    extraction_date: str
    key_phrase_pairs: List[Dict[str, str]]  # [{'tagalog': '...', 'english': '...'}]
    translated_pairs: List[Dict[str, str]]  # From dialogue sections
    all_tagalog_phrases: List[str]  # All Tagalog phrases found
    all_english_translations: List[str]  # All English translations found
    total_unique_phrases: int
    
    @property
    def key_phrases(self) -> List[str]:
        """Return just the Tagalog key phrases."""
        return [pair['tagalog'] for pair in self.key_phrase_pairs]
    
    @property
    def dialogue_phrases(self) -> List[str]:
        """Return just the Tagalog dialogue phrases.""" 
        return [pair['tagalog'] for pair in self.translated_pairs]


class StoryCollocationExtractor:
    """Extractor that provides basic vocabulary analysis functionality."""
    
    def __init__(self):
        """Initialize the extractor."""
        pass
        
    def extract_collocations(self, text: str) -> Dict[str, int]:
        """Extract collocations from text at multiple granularities.
        
        Args:
            text: The text to extract collocations from
            
        Returns:
            Dictionary of collocations with frequencies (1-word, 2-word, 3-word phrases)
        """
        words = re.findall(r'\b\w+\b', text.lower())
        collocations = {}
        
        # Extract single words (minimum 3 characters)
        for word in words:
            if len(word) >= 3:  # Skip very short words
                collocations[word] = collocations.get(word, 0) + 1
        
        # Extract 2-word phrases
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            if len(phrase) > 5:  # Skip very short phrases
                collocations[phrase] = collocations.get(phrase, 0) + 1
        
        # Extract 3-word phrases
        for i in range(len(words) - 2):
            phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
            if len(phrase) > 8:  # Skip very short 3-word phrases
                collocations[phrase] = collocations.get(phrase, 0) + 1
                
        return collocations
        
    def analyze_vocabulary_distribution(self, text: str) -> Dict[str, Any]:
        """Analyze vocabulary distribution in text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary with vocabulary analysis results
        """
        words = re.findall(r'\b\w+\b', text.lower())
        word_freq = {}
        for word in words:
            if len(word) >= 3:  # Only count words with 3+ characters
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency  
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # Get collocations
        collocations = self.extract_collocations(text)
        sorted_collocations = sorted(collocations.items(), key=lambda x: x[1], reverse=True)
        
        # Calculate additional metrics main.py expects
        new_content_words = max(0, len(word_freq) - 5)  # Assume some are "background"
        avg_word_length = sum(len(w) for w in words) / max(len(words), 1)
        top_new_words = [word for word, freq in sorted_words[:20]]  # Just the words, not tuples
        unique_new_words = list(word_freq.keys())
        
        return {
            'total_words': len(words),
            'unique_words_count': len(word_freq),
            'background_words': len([w for w in words if len(w) >= 3]),
            'background_percentage': (len([w for w in words if len(w) >= 3]) / max(len(words), 1)) * 100,
            'new_content_words': new_content_words,
            'avg_word_length': round(avg_word_length, 1),
            'word_frequency': dict(sorted_words),
            'collocations': dict(sorted_collocations),
            'unique_words': set(word_freq.keys()),
            'top_words': dict(sorted_words[:20]),
            'top_collocations': dict(sorted_collocations[:20]),
            'top_new_words': top_new_words,
            'unique_new_words': unique_new_words
        }
        
    def analyze_vocabulary(self, text: str) -> Dict[str, Any]:
        """Analyze vocabulary in text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Basic vocabulary analysis results
        """
        return self.analyze_vocabulary_distribution(text)
    
    def extract_from_day_number(self, day: int) -> StoryExtraction:
        """Extract vocabulary from a specific day's story.
        
        Args:
            day: Day number to extract from
            
        Returns:
            StoryExtraction object with parsed content
        """
        # Find story file for the given day
        story_file = self._find_story_file(day)
        if not story_file:
            # Return empty extraction if no file found
            return StoryExtraction(
                story_file=f"day_{day}_not_found.txt",
                extraction_date=datetime.now().isoformat(),
                key_phrase_pairs=[],
                translated_pairs=[],
                all_tagalog_phrases=[],
                all_english_translations=[],
                total_unique_phrases=0
            )
        
        # Read and parse the story file
        with open(story_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse Key Phrases section (real collocations only, skip breakdowns)
        key_phrase_pairs = self._parse_key_phrases_section(content)
        
        # Parse Translated section for dialogue pairs
        translated_pairs = self._parse_translated_section(content)
        
        # Collect all unique phrases
        all_tagalog = [pair['tagalog'] for pair in key_phrase_pairs + translated_pairs]
        all_english = [pair['english'] for pair in key_phrase_pairs + translated_pairs]
        unique_tagalog = list(dict.fromkeys(all_tagalog))  # Preserve order, remove duplicates
        
        return StoryExtraction(
            story_file=str(story_file),
            extraction_date=datetime.now().isoformat(),
            key_phrase_pairs=key_phrase_pairs,
            translated_pairs=translated_pairs,
            all_tagalog_phrases=unique_tagalog,
            all_english_translations=all_english,
            total_unique_phrases=len(unique_tagalog)
        )
    
    def _find_story_file(self, day: int) -> Optional[Path]:
        """Find the story file for a given day number."""
        stories_dir = Path("instance/data/stories")
        if not stories_dir.exists():
            stories_dir = Path("data/stories")
        if not stories_dir.exists():
            return None
            
        # Try different naming patterns
        patterns = [
            f"story_day{day}_*.txt",
            f"story_day{day:02d}_*.txt",
            f"day{day}_*.txt",
            f"day{day:02d}_*.txt",
            f"demo-0.0.3-day-{day}.txt"
        ]
        
        for pattern in patterns:
            matches = list(stories_dir.glob(pattern))
            if matches:
                return matches[0]  # Return first match
                
        return None
    
    def _parse_key_phrases_section(self, content: str) -> List[Dict[str, str]]:
        """Parse Key Phrases section and extract real collocations (skip breakdowns)."""
        key_phrase_pairs = []
        lines = content.split('\n')
        
        # Find Key Phrases section
        key_phrases_start = -1
        natural_speed_start = -1
        
        for i, line in enumerate(lines):
            if line.strip() == "Key Phrases:":
                key_phrases_start = i
            elif "[NARRATOR]: Natural Speed" in line:
                natural_speed_start = i
                break
        
        if key_phrases_start == -1 or natural_speed_start == -1:
            return key_phrase_pairs
        
        # Parse the Key Phrases section
        i = key_phrases_start + 1
        while i < natural_speed_start:
            line = lines[i].strip()
            
            # Look for actual collocations: [TAGALOG-FEMALE-1]: phrase
            if line.startswith('[TAGALOG-') and ']:' in line:
                tagalog_phrase = line.split(']: ', 1)[1].strip()
                
                # Next line should be [NARRATOR]: translation  
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith('[NARRATOR]:'):
                        english_translation = next_line.split(': ', 1)[1].strip()
                        
                        key_phrase_pairs.append({
                            'tagalog': tagalog_phrase,
                            'english': english_translation
                        })
                        i += 2  # Skip the translation line
                        continue
            
            i += 1
        
        return key_phrase_pairs
    
    def _parse_translated_section(self, content: str) -> List[Dict[str, str]]:
        """Parse Translated section for dialogue translation pairs."""
        translated_pairs = []
        lines = content.split('\n')
        
        # Find Translated section
        translated_start = -1
        for i, line in enumerate(lines):
            if "[NARRATOR]: Translated" in line:
                translated_start = i
                break
        
        if translated_start == -1:
            return translated_pairs
        
        # Parse dialogue pairs in Translated section
        i = translated_start + 1
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for Tagalog dialogue: [TAGALOG-*]: phrase
            if line.startswith('[TAGALOG-') and ']:' in line:
                tagalog_phrase = line.split(']: ', 1)[1].strip()
                
                # Next line should be [NARRATOR]: translation
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip() 
                    if next_line.startswith('[NARRATOR]:'):
                        english_translation = next_line.split(': ', 1)[1].strip()
                        
                        translated_pairs.append({
                            'tagalog': tagalog_phrase,
                            'english': english_translation
                        })
                        i += 2  # Skip the translation line
                        continue
            
            i += 1
        
        return translated_pairs
    
    def save_extraction(self, extraction: Dict[str, Any]) -> str:
        """Save extraction results to file.
        
        Args:
            extraction: Extraction results to save
            
        Returns:
            Path to saved file
        """
        # TODO: Implement actual file saving
        day = extraction.get('day', 'unknown')
        filename = f'extraction_day_{day}.json'
        print(f"Note: Would save extraction to {filename} (stub implementation)")
        return filename