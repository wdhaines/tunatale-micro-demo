#!/usr/bin/env python3
"""
Build word frequency database from TunaTale story corpus.

This script scans all story files to extract Filipino words and phrases,
counting their frequency to support component-based collocation difficulty scoring.
"""

import re
import json
import glob
from collections import defaultdict, Counter
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WordFrequencyBuilder:
    """Build word frequency database from story corpus."""
    
    def __init__(self):
        self.word_frequencies = Counter()
        self.phrase_frequencies = Counter()
        self.total_words = 0
        self.total_phrases = 0
        
    def is_valid_filipino_word(self, word: str) -> bool:
        """Check if a word is valid Filipino (not English, voice tags, or fragments)."""
        word = word.strip().lower()
        
        # Skip empty or very short
        if len(word) < 2:
            return False
            
        # Skip voice tags and technical markers
        if any(tag in word for tag in ['[narrator', 'tagalog-', '[tagalog', 'female-', 'male-']):
            return False
            
        # Skip English words (common ones)
        english_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'among', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs',
            'a', 'an', 'is', 'are', 'was', 'were', 'be', 'being', 'been', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
            'can', 'good', 'very', 'much', 'how', 'what', 'when', 'where', 'why', 'who',
            'welcome', 'afternoon', 'thank', 'cost', 'look', 'help', 'work', 'amazing',
            'really', 'take', 'your', 'does', 'may', 'are', 'these'
        }
        
        if word in english_words:
            return False
            
        # Skip pure numbers
        if word.isdigit():
            return False
            
        # Skip single letters that are likely syllable fragments
        if len(word) == 1:
            return False
            
        # Skip obvious syllable fragments (consonant-only or vowel-only short words)
        if len(word) == 2 and (word.isalpha() and (
            all(c in 'bcdfghjklmnpqrstvwxz' for c in word) or  # consonant-only
            all(c in 'aeiou' for c in word)  # vowel-only
        )):
            return False
            
        return True
    
    def extract_phrases_from_story(self, story_content: str) -> list:
        """Extract Filipino phrases from Natural Speed dialogue sections."""
        phrases = []
        lines = story_content.split('\n')
        
        in_natural_speed = False
        
        for line in lines:
            line = line.strip()
            
            # Track Natural Speed section (this is where the real dialogues are)
            if line.startswith('[NARRATOR]:') and 'Natural Speed' in line:
                in_natural_speed = True
                continue
            elif line.startswith('[NARRATOR]:') and ('Slow Speed' in line or 'Translated' in line):
                # Stop when we hit other sections
                in_natural_speed = False
                continue
                
            if in_natural_speed and line:
                # Extract Filipino text from dialogue lines
                if line.startswith('[TAGALOG-'):
                    # Extract the dialogue after the voice tag
                    phrase_match = re.search(r'\]: (.+)', line)
                    if phrase_match:
                        dialogue = phrase_match.group(1).strip()
                        # Clean and split the dialogue
                        clean_phrases = self.clean_and_split_dialogue(dialogue)
                        for phrase in clean_phrases:
                            if self.is_valid_filipino_phrase(phrase):
                                phrases.append(phrase)
                            
                # Also capture standalone Filipino dialogue lines (no voice tag)
                elif not line.startswith('[') and not line.startswith('#'):
                    # Clean and split the line
                    clean_phrases = self.clean_and_split_dialogue(line)
                    for phrase in clean_phrases:
                        if self.is_valid_filipino_phrase(phrase):
                            phrases.append(phrase)
        
        return phrases
    
    def clean_and_split_dialogue(self, dialogue: str) -> list:
        """Clean punctuation and split multi-sentence dialogues into individual phrases."""
        if not dialogue or not dialogue.strip():
            return []
            
        # Split on sentence-ending punctuation but preserve question marks for questions
        # Split on: . ! ... but keep ?
        sentences = re.split(r'[.!]+(?:\s*\.\.\.)?', dialogue)
        
        clean_phrases = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Remove excessive punctuation but keep meaningful punctuation like ?
            # Remove trailing/leading punctuation except question marks
            cleaned = re.sub(r'^[^\w\s?]+|[^\w\s?]+$', '', sentence)
            
            # Clean up multiple spaces
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            
            if cleaned and len(cleaned) > 1:
                clean_phrases.append(cleaned)
                
        return clean_phrases
    
    def is_valid_filipino_phrase(self, phrase: str) -> bool:
        """Check if a phrase is valid Filipino (not syllable breakdown or English)."""
        phrase = phrase.strip()
        
        # Skip empty
        if not phrase:
            return False
            
        # Skip single words shorter than 3 characters (likely fragments)
        words = phrase.split()
        if len(words) == 1 and len(phrase) < 3:
            return False
            
        # Skip if it's mostly English
        english_word_count = sum(1 for word in words if not self.is_valid_filipino_word(word))
        if len(words) > 1 and english_word_count > len(words) / 2:
            return False
            
        # Skip obvious syllable fragments (very short repeated syllables)
        if len(words) == 1 and len(phrase) < 4 and phrase.lower() in phrase.lower() * 2:
            return False
            
        return True
    
    def process_story_file(self, file_path: Path):
        """Process a single story file and extract word/phrase frequencies."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            logger.info(f"Processing {file_path.name}")
            
            # Extract phrases from this story
            phrases = self.extract_phrases_from_story(content)
            
            for phrase in phrases:
                # Count the full phrase
                self.phrase_frequencies[phrase] += 1
                self.total_phrases += 1
                
                # Count individual words in the phrase
                words = phrase.split()
                for word in words:
                    word = word.strip().lower()
                    # Remove punctuation
                    word = re.sub(r'[^\w\s]', '', word)
                    
                    if word and self.is_valid_filipino_word(word):
                        self.word_frequencies[word] += 1
                        self.total_words += 1
                        
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    def process_all_stories(self, stories_dir: str = "instance/data/stories"):
        """Process all finalized story files in the corpus."""
        # Get all .txt files but exclude the originals folder
        all_files = list(Path(stories_dir).glob("**/*.txt"))
        story_files = [f for f in all_files if 'originals' not in str(f)]
        
        logger.info(f"Found {len(story_files)} finalized story files to process (excluding originals)")
        logger.info(f"Excluded {len(all_files) - len(story_files)} files from originals folder")
        
        for file_path in story_files:
            self.process_story_file(file_path)
            
        logger.info(f"Processed {len(story_files)} files")
        logger.info(f"Total unique words: {len(self.word_frequencies)}")
        logger.info(f"Total unique phrases: {len(self.phrase_frequencies)}")
        logger.info(f"Total word instances: {self.total_words}")
        logger.info(f"Total phrase instances: {self.total_phrases}")
    
    def save_frequency_database(self, output_file: str = "instance/data/word_frequency.json"):
        """Save the frequency database to JSON file."""
        # Convert Counter to regular dict for JSON serialization
        database = {
            'word_frequencies': dict(self.word_frequencies),
            'phrase_frequencies': dict(self.phrase_frequencies),
            'total_words': self.total_words,
            'total_phrases': self.total_phrases,
            'stats': {
                'unique_words': len(self.word_frequencies),
                'unique_phrases': len(self.phrase_frequencies),
                'most_common_words': self.word_frequencies.most_common(20),
                'most_common_phrases': self.phrase_frequencies.most_common(20)
            }
        }
        
        # Ensure directory exists
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(database, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Saved frequency database to {output_file}")
        
        # Print some statistics
        print("\n=== Word Frequency Statistics ===")
        print(f"Unique words: {len(self.word_frequencies)}")
        print(f"Total word instances: {self.total_words}")
        print(f"Unique phrases: {len(self.phrase_frequencies)}")
        print(f"Total phrase instances: {self.total_phrases}")
        
        print("\nMost common words:")
        for word, count in self.word_frequencies.most_common(15):
            print(f"  {word}: {count}")
            
        print("\nMost common phrases:")
        for phrase, count in self.phrase_frequencies.most_common(10):
            print(f"  '{phrase}': {count}")
    
    def get_word_frequency(self, word: str) -> int:
        """Get frequency count for a specific word."""
        return self.word_frequencies.get(word.lower(), 0)
    
    def get_phrase_frequency(self, phrase: str) -> int:
        """Get frequency count for a specific phrase."""
        return self.phrase_frequencies.get(phrase, 0)
    
    def calculate_component_frequency_score(self, collocation: str) -> float:
        """
        Calculate component-based frequency score for a collocation.
        
        Returns a score from 0.0 to 1.0 where higher scores indicate
        collocations made of more frequent component words.
        """
        words = collocation.lower().split()
        if not words:
            return 0.0
            
        # Get frequency for each component word
        word_scores = []
        for word in words:
            word = re.sub(r'[^\w\s]', '', word)  # Remove punctuation
            if word and self.is_valid_filipino_word(word):
                frequency = self.get_word_frequency(word)
                # Convert frequency to a 0-1 score (log scale to handle wide range)
                if frequency > 0:
                    # Normalize by total words and apply log scaling
                    normalized_freq = frequency / self.total_words
                    score = min(1.0, normalized_freq * 1000)  # Scale up for readability
                    word_scores.append(score)
                else:
                    word_scores.append(0.0)
        
        if not word_scores:
            return 0.0
            
        # Return average component word frequency score
        return sum(word_scores) / len(word_scores)


def main():
    """Main execution function."""
    builder = WordFrequencyBuilder()
    
    # Check if stories directory exists
    stories_dir = Path("instance/data/stories")
    if not stories_dir.exists():
        logger.error(f"Stories directory not found: {stories_dir}")
        return
        
    # Process all story files
    builder.process_all_stories()
    
    # Save the database
    builder.save_frequency_database()
    
    print("\n=== Component-based scoring examples ===")
    # Test some example collocations
    test_collocations = [
        "salamat po",
        "magkano po", 
        "kumusta po",
        "ah salamat po",
        "nakakamangha talaga",
        "adobo salamat po"
    ]
    
    for collocation in test_collocations:
        score = builder.calculate_component_frequency_score(collocation)
        print(f"'{collocation}': {score:.3f}")


if __name__ == "__main__":
    main()