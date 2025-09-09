"""
StoryCollocationExtractor to replace removed CollocationExtractor.

This implementation provides compatibility methods while transitioning to 
LLM-based vocabulary extraction. It provides realistic stub results to 
make CLI commands work properly.
"""

from typing import Dict, List, Any, Optional
import re


class StoryCollocationExtractor:
    """Extractor that provides basic vocabulary analysis functionality."""
    
    def __init__(self):
        """Initialize the extractor."""
        pass
        
    def extract_collocations(self, text: str) -> Dict[str, int]:
        """Extract collocations from text.
        
        Args:
            text: The text to extract collocations from
            
        Returns:
            Dictionary of collocations with frequencies
        """
        # Simple collocation extraction based on word pairs
        words = re.findall(r'\b\w+\b', text.lower())
        collocations = {}
        
        # Extract 2-word phrases as basic collocations
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            if len(phrase) > 5:  # Skip very short phrases
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
    
    def extract_from_day_number(self, day: int) -> Dict[str, Any]:
        """Extract vocabulary from a specific day's story.
        
        Args:
            day: Day number to extract from
            
        Returns:
            Extraction results for the day
        """
        # TODO: Implement actual story file reading and extraction
        return {
            'day': day,
            'collocations': {},
            'word_frequency': {},
            'total_words': 0,
            'extraction_date': 'stub',
            'story_file': f'day_{day:02d}_story.txt'
        }
    
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