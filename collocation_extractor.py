import json
import spacy
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Tuple
from config import CURRICULUM_PATH, COLLOCATIONS_PATH

class CollocationExtractor:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise ImportError(
                "English language model not found. Please run: "
                "python -m spacy download en_core_web_sm"
            )
    
    def extract_from_curriculum(self) -> Dict[str, int]:
        """Extract collocations from the generated curriculum."""
        if not CURRICULUM_PATH.exists():
            raise FileNotFoundError("Curriculum file not found. Generate a curriculum first.")
        
        with open(CURRICULUM_PATH, 'r') as f:
            curriculum = json.load(f)
        
        # Extract text from curriculum
        text = curriculum['content']
        return self.extract_collocations(text)
    
    def extract_collocations(self, text: str, min_words: int = 3, max_words: int = 5) -> Dict[str, int]:
        """
        Extract collocations (3-5 word phrases) from text.
        Returns a dictionary of collocations and their counts.
        """
        doc = self.nlp(text.lower())
        collocations = defaultdict(int)
        
        # Extract n-grams of different lengths
        for n in range(min_words, max_words + 1):
            for i in range(len(doc) - n + 1):
                # Skip if any token is a stopword or punctuation
                if all(not (token.is_stop or token.is_punct) for token in doc[i:i+n]):
                    # Join tokens to form the collocation
                    colloc = ' '.join(token.text for token in doc[i:i+n])
                    collocations[colloc] += 1
        
        # Filter out very common or very rare collocations
        filtered_collocations = {
            k: v for k, v in collocations.items() 
            if 3 <= len(k.split()) <= 5  # Ensure proper length
            and 2 <= v <= 20  # Filter too rare or too common
        }
        
        # Sort by frequency (descending)
        sorted_collocations = dict(
            sorted(filtered_collocations.items(), key=lambda x: x[1], reverse=True)
        )
        
        # Save the collocations
        self._save_collocations(sorted_collocations)
        
        return sorted_collocations
    
    def _save_collocations(self, collocations: Dict[str, int]):
        """Save collocations to a JSON file."""
        with open(COLLOCATIONS_PATH, 'w') as f:
            json.dump(collocations, f, indent=2)
    
    def get_top_collocations(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get the top N most frequent collocations."""
        if not COLLOCATIONS_PATH.exists():
            raise FileNotFoundError("Collocations file not found. Extract collocations first.")
        
        with open(COLLOCATIONS_PATH, 'r') as f:
            collocations = json.load(f)
        
        return list(collocations.items())[:n]
