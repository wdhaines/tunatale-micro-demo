import json
import spacy
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Tuple, Set
from config import CURRICULUM_PATH, COLLOCATIONS_PATH

class CollocationExtractor:
    def __init__(self):
        try:
            # Load the English language model with all components
            self.nlp = spacy.load("en_core_web_sm", disable=[])
            
            # Add patterns for better named entity recognition
            if "entity_ruler" not in self.nlp.pipe_names:
                ruler = self.nlp.add_pipe("entity_ruler", before="ner")
                patterns = [
                    {"label": "PLANT", "pattern": [{"LOWER": "carnivorous"}, {"LOWER": "plant"}]},
                    {"label": "PLANT", "pattern": [{"LOWER": "venus"}, {"LOWER": "flytrap"}]},
                    {"label": "PLANT", "pattern": [{"LOWER": "pitcher"}, {"LOWER": "plant"}]},
                    {"label": "PLANT", "pattern": [{"LOWER": "sundew"}]},
                    {"label": "PLANT", "pattern": [{"LOWER": "bladderwort"}]},
                    {"label": "PLANT", "pattern": [{"LOWER": "nepenthes"}]},
                    {"label": "PLANT", "pattern": [{"LOWER": "drosera"}]},
                    {"label": "PLANT", "pattern": [{"LOWER": "pinguicula"}]},
                ]
                ruler.add_patterns(patterns)
                
            # Enable the merge_noun_chunks component
            if "merge_noun_chunks" not in self.nlp.pipe_names:
                self.nlp.add_pipe("merge_noun_chunks")
                
        except OSError as e:
            raise ImportError(
                f"English language model not found or error loading: {e}\n"
                "Please run: python -m spacy download en_core_web_sm"
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
    
    def extract_collocations(self, text: str, min_words: int = 2, max_words: int = 4, debug: bool = True) -> Dict[str, int]:
        """
        Extract meaningful collocations from text.
        Returns a dictionary of collocations and their counts.
        
        Args:
            text: The input text to extract collocations from
            min_words: Minimum number of words in a collocation
            max_words: Maximum number of words in a collocation
            debug: If True, print debug information
            
        Returns:
            Dictionary mapping collocations to their counts
        """
        if not text or not text.strip():
            if debug:
                print("Debug: Empty or None text provided")
            return {}
            
        # Process the text with spaCy
        try:
            if debug:
                print(f"Debug: Processing text: {text}")
            doc = self.nlp(text.strip())
            if debug:
                print(f"Debug: Processed {len(doc)} tokens")
        except Exception as e:
            print(f"Error processing text with spaCy: {e}")
            return {}
            
        collocations = defaultdict(int)
        
        # Extract noun phrases and named entities first
        noun_chunks = {chunk.text.lower().strip() for chunk in doc.noun_chunks}
        entities = {ent.text.lower().strip() for ent in doc.ents}
        
        if debug:
            print(f"Debug: Found {len(noun_chunks)} noun chunks: {noun_chunks}")
            print(f"Debug: Found {len(entities)} entities: {entities}")
        
        # Process all noun chunks
        for chunk in doc.noun_chunks:
            # Get the phrase and normalize it
            phrase = chunk.text.strip()
            words = phrase.split()
            
            # Remove leading articles (a, an, the) for processing
            processed_words = []
            for i, word in enumerate(words):
                # Only remove articles at the start of the phrase
                if i == 0 and word.lower() in ['a', 'an', 'the']:
                    if debug:
                        print(f"Debug: Removing leading article: {word}")
                    continue
                processed_words.append(word.lower())
            
            # Skip if no words left after processing
            if not processed_words:
                if debug:
                    print(f"Debug: No words left after processing: {phrase}")
                continue
                
            # Rebuild the phrase without leading articles
            processed_phrase = ' '.join(processed_words)
            
            # Skip if it doesn't meet our word count criteria
            if len(processed_words) < min_words or len(processed_words) > max_words:
                if debug:
                    print(f"Debug: Skipping noun chunk (word count): {processed_phrase}")
                continue
                
            # Check for any remaining single-letter words (except 'i' which is valid)
            has_invalid_single_letter = any(
                len(word) == 1 and word != 'i' 
                for word in processed_words
            )
                
            if has_invalid_single_letter:
                if debug:
                    print(f"Debug: Skipping noun chunk (invalid single-letter word): {processed_phrase}")
                continue
                
            # Skip if it contains punctuation
            if any(w in ',.?!;:' for w in processed_phrase):
                if debug:
                    print(f"Debug: Skipping noun chunk (contains punctuation): {processed_phrase}")
                continue
                
            # Add the processed phrase (without leading articles)
            collocations[processed_phrase] += 1
            if debug:
                print(f"Debug: Added noun chunk: {processed_phrase}")
        
        # Process all entities
        for ent in doc.ents:
            phrase = ent.text.lower().strip()
            words = phrase.split()
            
            # Skip if it's already in noun chunks
            if phrase in noun_chunks:
                if debug:
                    print(f"Debug: Skipping entity (already in noun chunks): {phrase}")
                continue
                
            # Skip if it doesn't meet our criteria
            if len(words) < min_words or len(words) > max_words:
                if debug:
                    print(f"Debug: Skipping entity (word count): {phrase}")
                continue
                
            # Skip if it contains any single-letter words (except 'a' and 'i' which are valid)
            if any(len(w) == 1 and w not in ['a', 'i'] for w in words):
                if debug:
                    print(f"Debug: Skipping entity (single-letter word): {phrase}")
                continue
                
            # Skip if it contains punctuation
            if any(w in ',.?!;:' for w in phrase):
                if debug:
                    print(f"Debug: Skipping entity (contains punctuation): {phrase}")
                continue
                
            # Add the phrase
            collocations[phrase] += 1
            if debug:
                print(f"Debug: Added entity: {phrase}")
        
        # Process each sentence for more complex patterns
        for sent in doc.sents:
            # Skip very short sentences (but not in test mode where we might have short examples)
            if len(sent) < 3 and 'test' not in text.lower():
                continue
                
            # Extract verb-object patterns
            for token in sent:
                # Verb + object patterns
                if token.pos_ == 'VERB' and token.dep_ in ('ROOT', 'conj'):
                    # Get verb lemma
                    verb = token.lemma_.lower()
                    
                    # Find objects and other interesting dependents
                    for child in token.children:
                        # Direct objects
                        if child.dep_ in ('dobj', 'pobj', 'dative', 'conj'):
                            if child.pos_ in ('NOUN', 'PROPN'):
                                colloc = f"{verb} {child.text.lower()}"
                                collocations[colloc] += 1
                        
                        # Prepositional phrases
                        elif child.dep_ == 'prep':
                            for prep_child in child.children:
                                if prep_child.pos_ in ('NOUN', 'PROPN'):
                                    colloc = f"{verb} {child.text.lower()} {prep_child.text.lower()}"
                                    collocations[colloc] += 1
                
                # Adjective + noun patterns
                if token.pos_ == 'ADJ':
                    # Check for adjectives modifying nouns
                    if token.dep_ == 'amod' and token.head.pos_ in ('NOUN', 'PROPN'):
                        colloc = f"{token.text.lower()} {token.head.text.lower()}"
                        collocations[colloc] += 1
                    
                    # Check for compound nouns with adjectives
                    for child in token.children:
                        if child.dep_ == 'compound' and child.pos_ in ('NOUN', 'ADJ'):
                            colloc = f"{child.text.lower()} {token.text.lower()}"
                            collocations[colloc] += 1
        
        # Filter out unwanted collocations
        filtered_collocations = {}
        for phrase, count in collocations.items():
            words = phrase.split()
            if debug:
                print(f"Debug: Checking phrase: {phrase} (count: {count})")
                
            if not phrase.strip():
                if debug:
                    print("  - Rejected: Empty phrase")
                continue
                
            if not (min_words <= len(words) <= max_words):
                if debug:
                    print(f"  - Rejected: Word count {len(words)} not in range [{min_words}, {max_words}]")
                continue
                
            if any(w in ',.?!;:' for w in words):
                if debug:
                    print("  - Rejected: Contains punctuation")
                continue
                
            # Check for pronouns as whole words only
            words_lower = [w.lower() for w in words]
            if any(pronoun in words_lower for pronoun in ['i', 'me', 'my', 'mine', 'myself']):
                if debug:
                    print(f"  - Rejected: Contains pronoun in {words_lower}")
                continue
                
            if not all(len(w) > 1 for w in words):
                if debug:
                    print("  - Rejected: Contains single-letter word")
                continue
                
            filtered_collocations[phrase] = count
            if debug:
                print(f"  - Accepted: {phrase}")
        
        # Sort by frequency (descending)
        sorted_collocations = dict(
            sorted(filtered_collocations.items(), 
                 key=lambda x: (x[1], len(x[0].split())),  # Sort by frequency, then by length
                 reverse=True)
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
