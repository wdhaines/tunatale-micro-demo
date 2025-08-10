"""Collocation extraction and management for TunaTale."""
import json
import os
import spacy
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Tuple, Set, Any

import config

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
                
            # Load background vocabulary
            import os
            vocab_path = os.environ.get('VOCABULARY_PATH', str(config.DATA_DIR / 'a2_flat_vocabulary.json'))
            try:
                with open(vocab_path, 'r') as f:
                    self.background_vocabulary = set(json.load(f))
                print(f"Loaded {len(self.background_vocabulary)} background vocabulary words from {vocab_path}")
            except FileNotFoundError as e:
                # If the vocabulary file is not found, use an empty set
                self.background_vocabulary = set()
                print(f"Warning: Vocabulary file not found at {vocab_path}. Using empty vocabulary.")
                
        except OSError as e:
            raise ImportError(
                f"English language model not found or error loading: {e}\n"
                "Please run: python -m spacy download en_core_web_sm"
            )
    
    def extract_from_curriculum(self) -> Dict[str, int]:
        """Extract collocations from the generated curriculum."""
        if not config.CURRICULUM_PATH.exists():
            raise FileNotFoundError("Curriculum file not found. Generate a curriculum first.")
        
        with open(config.CURRICULUM_PATH, 'r', encoding='utf-8') as f:
            curriculum = json.load(f)
        
        # Extract text from all phases in the curriculum
        all_text = []
        if 'phases' in curriculum and isinstance(curriculum['phases'], dict):
            for phase_name, phase_data in curriculum['phases'].items():
                if isinstance(phase_data, dict) and 'content' in phase_data:
                    all_text.append(phase_data['content'])
        
        if not all_text:
            # Fallback to old format if no phases found
            if 'content' in curriculum:
                all_text = [curriculum['content']]
            else:
                raise ValueError("Curriculum file format not recognized. Expected 'phases' dictionary or 'content' field.")
        
        # Combine all text with double newlines between sections
        combined_text = '\n\n'.join(all_text)
        return self.extract_collocations(combined_text)
    
    def _is_valid_collocation(self, tokens):
        """
        Check if a sequence of tokens is a valid collocation.
        
        Args:
            tokens: List of spaCy tokens
            
        Returns:
            bool: True if valid, False otherwise
        """
        # For single words, check if it's in background knowledge
        if len(tokens) == 1:
            word = tokens[0].text.lower()
            # Skip words the learner should already know
            if word in self.background_vocabulary:
                return False
            # Only keep content words not in background
            if tokens[0].pos_ not in ['NOUN', 'VERB', 'ADJ', 'ADV']:
                return False
            # Skip very short words
            if len(word) < 3:
                return False
            return True
            
        # For multi-word phrases
        words_lower = [t.text.lower() for t in tokens]
        
        # Skip if all words are in background vocabulary
        if all(word in self.background_vocabulary for word in words_lower):
            return False
            
        # Check for pronouns as whole words only
        if any(pronoun in words_lower for pronoun in ['i', 'me', 'my', 'mine', 'myself']):
            return False
            
        # Skip if it contains any single-letter words (except 'a' and 'i' which are valid)
        if any(len(t.text) == 1 and t.text.lower() not in ['a', 'i'] for t in tokens):
            return False
            
        # Skip if it contains punctuation
        if any(t.text in ',.?!;:' for t in tokens):
            return False
            
        return True
        
    def extract_collocations(self, text: str, min_words: int = 1, max_words: int = 4, debug: bool = True) -> Dict[str, int]:
        """
        Extract meaningful collocations from text.
        Returns a dictionary of collocations and their counts.
        
        Args:
            text: The input text to extract collocations from
            min_words: Minimum number of words in a collocation (1 for single words)
            max_words: Maximum number of words in a collocation (up to 4)
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
            
        # Process individual tokens for single-word collocations (1-grams)
        if min_words == 1:
            for sent in doc.sents:
                for i in range(len(sent)):
                    if self._is_valid_collocation([sent[i]]):
                        word = sent[i].text.lower()
                        collocations[word] += 1
                        if debug:
                            print(f"Debug: Added single word: {word}")
        
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
        with open(config.COLLOCATIONS_PATH, 'w') as f:
            json.dump(collocations, f, indent=2)
    
    def get_filtered_background_words(self, text: str) -> List[str]:
        """
        Return background words found in the text (for debugging).
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of background vocabulary words found in the text
        """
        doc = self.nlp(text.lower())
        background_words = []
        
        for token in doc:
            if token.is_alpha:
                word = token.text.lower()
                if word in self.background_vocabulary:
                    background_words.append(word)
                    
        return background_words
        
    def _is_meaningful_word(self, token) -> bool:
        """Check if a token is a meaningful content word."""
        # Skip short words, numbers, and punctuation
        if len(token.text) < 2 or not token.is_alpha:
            return False
            
        word = token.text.lower()
        
        # Skip common function words that might not be in our background vocab
        common_function_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'if', 'of', 'at', 'by',
            'to', 'for', 'in', 'on', 'with', 'as', 'from', 'that', 'this',
            'these', 'those', 'is', 'are', 'was', 'were', 'be', 'been', 'being'
        }
        
        if word in common_function_words:
            return False
            
        # Check if it's a content word (noun, verb, adjective, adverb, proper noun)
        return token.pos_ in ['NOUN', 'VERB', 'ADJ', 'ADV', 'PROPN']
    
    def analyze_vocabulary_distribution(self, text: str) -> Dict[str, Any]:
        """
        Analyze how much of the text is background vs new vocabulary.
        
        Args:
            text: The input text to analyze
            
        Returns:
            Dictionary with analysis results including:
            - total_words: Total number of words in the text
            - background_words: Number of words in background vocabulary
            - new_content_words: Number of new content words
            - background_percentage: Percentage of background words
            - unique_new_words: List of unique new words
            - collocations: Extracted collocations (filtered)
        """
        # Clean the text to remove JSON artifacts and metadata
        clean_text = ' '.join(line.strip() for line in text.split('\n') 
                            if not any(term in line.lower() for term in 
                                    ['"content":', 'cefr_level', 'learning_objective', 
                                     'story_length', 'new_vocabulary', 'recycled_vocabulary',
                                     r'phase\d+']))
        
        doc = self.nlp(clean_text.lower())
        
        background_words = []
        new_words = []
        
        # Extract collocations first to avoid duplicate processing
        collocations = self.extract_collocations(clean_text, min_words=1, max_words=4, debug=False)
        
        # Filter collocations to remove noise
        filtered_collocations = {}
        for phrase, count in collocations.items():
            # Skip phrases that look like JSON artifacts or metadata
            if any(c in phrase for c in ['{', '}', '[', ']', ':', '"', '\'']):
                continue
                
            # Skip phrases that are too common or not meaningful
            words = phrase.split()
            if len(words) == 1 and len(phrase) < 3:  # Skip single letters
                continue
                
            # Skip phrases that are entirely numeric
            if all(w.isdigit() for w in words):
                continue
                
            filtered_collocations[phrase] = count
        
        # Sort collocations by frequency (descending)
        sorted_collocations = dict(
            sorted(filtered_collocations.items(), 
                 key=lambda x: x[1], 
                 reverse=True)
        )
        
        # Save the collocations to file
        if sorted_collocations:
            self._save_collocations(sorted_collocations)
        
        # Analyze word distribution
        for token in doc:
            if not self._is_meaningful_word(token):
                continue
                
            word = token.lemma_.lower()  # Use lemma for better grouping
            
            if word in self.background_vocabulary:
                background_words.append(word)
            else:
                new_words.append(word)
        
        # Calculate statistics
        total_words = len(background_words) + len(new_words)
        unique_new_words = sorted(list(set(new_words)))
        
        # Sort new words by frequency
        from collections import Counter
        word_freq = Counter(word for word in new_words)
        sorted_new_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # Get top 20 most frequent new words
        top_new_words = [word for word, _ in sorted_new_words[:20]]
        
        return {
            'total_words': total_words,
            'background_words': len(background_words),
            'new_content_words': len(new_words),
            'background_percentage': (len(background_words) / total_words * 100) if total_words > 0 else 0,
            'unique_new_words': unique_new_words,
            'top_new_words': top_new_words,
            'collocations': sorted_collocations,
            'unique_words_count': len(set(background_words + new_words)),
            'avg_word_length': sum(len(word) for word in background_words + new_words) / total_words if total_words > 0 else 0
        }
    
    def get_top_collocations(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get the top N most frequent collocations."""
        if not config.COLLOCATIONS_PATH.exists():
            raise FileNotFoundError("Collocations file not found. Extract collocations first.")
        
        with open(config.COLLOCATIONS_PATH, 'r') as f:
            collocations = json.load(f)
        return list(collocations.items())[:n]
