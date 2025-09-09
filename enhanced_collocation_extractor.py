"""
Enhanced Collocation Extractor with Bidirectional Mapping Support.

Extends the existing CollocationExtractor to detect and create English↔Filipino
translation pairs from story content, enabling proper SRS enforcement.
"""

import re
from typing import Dict, List, Tuple, Set
from collections import defaultdict
from collocation_extractor import CollocationExtractor


class TranslationPair:
    """Represents a detected English↔Filipino translation pair."""
    
    def __init__(self, english: str, filipino: str, confidence: float = 1.0):
        self.english = english.lower().strip()
        self.filipino = filipino.lower().strip()
        self.confidence = confidence
    
    def __repr__(self):
        return f"TranslationPair('{self.english}' ↔ '{self.filipino}', confidence={self.confidence})"


class EnhancedCollocationExtractor(CollocationExtractor):
    """Enhanced extractor that creates bidirectional English↔Filipino mappings."""
    
    def __init__(self):
        super().__init__()
        
        # Common English words that should map to Filipino equivalents
        self.target_english_words = {
            'water', 'drinks', 'welcome', 'rice', 'food', 'delicious', 
            'thank you', 'please', 'excuse me', 'how much', 'good morning',
            'good afternoon', 'fresh', 'perfect', 'beautiful', 'expensive',
            'cheap', 'hot', 'cold', 'spicy', 'sweet'
        }
        
    def extract_with_translation_pairs(self, story_content: str) -> Dict:
        """Extract collocations AND translation pairs from story content.
        
        Returns:
            Dict with keys: 'collocations', 'translation_pairs', 'enhanced_mappings'
        """
        # Get standard collocations first
        collocations = self.extract_collocations(story_content, debug=False)
        
        # Detect translation pairs from story structure
        translation_pairs = self.detect_translation_pairs(story_content, debug=False)
        
        # Create enhanced mappings that link English→Filipino
        enhanced_mappings = self.create_enhanced_mappings(collocations, translation_pairs)
        
        return {
            'collocations': collocations,
            'translation_pairs': translation_pairs,
            'enhanced_mappings': enhanced_mappings
        }
    
    def detect_translation_pairs(self, story_content: str, debug: bool = False) -> List[TranslationPair]:
        """Detect English↔Filipino translation pairs from story dialogue patterns."""
        pairs = []
        lines = story_content.split('\n')
        
        if debug:
            print(f"Processing {len(lines)} lines for translation pairs...")
        
        for i in range(len(lines) - 1):
            current_line = lines[i].strip()
            next_line = lines[i + 1].strip()
            
            if debug:
                print(f"Line {i}: {current_line}")
                print(f"Line {i+1}: {next_line}")
            
            # Pattern: [TAGALOG-*]: Filipino text
            #          [NARRATOR]: English translation
            is_tagalog = self._is_tagalog_speaker_line(current_line)
            is_narrator = self._is_narrator_line(next_line)
            
            if debug:
                print(f"  Tagalog: {is_tagalog}, Narrator: {is_narrator}")
            
            if is_tagalog and is_narrator:
                filipino_text = self._extract_dialogue_text(current_line)
                english_text = self._extract_dialogue_text(next_line)
                
                if debug:
                    print(f"  Filipino: '{filipino_text}'")
                    print(f"  English: '{english_text}'")
                
                if filipino_text and english_text:
                    # Find word-level translation pairs
                    word_pairs = self._extract_word_pairs(filipino_text, english_text)
                    pairs.extend(word_pairs)
                    
                    if debug:
                        print(f"  Found {len(word_pairs)} word pairs")
            
            if debug:
                print()
        
        return self._deduplicate_pairs(pairs)
    
    def _is_tagalog_speaker_line(self, line: str) -> bool:
        """Check if line is a Tagalog speaker dialogue."""
        return bool(re.match(r'\[TAGALOG-[A-Z]+-\d+\]:', line))
    
    def _is_narrator_line(self, line: str) -> bool:
        """Check if line is a narrator translation."""
        return line.startswith('[NARRATOR]:')
    
    def _extract_dialogue_text(self, line: str) -> str:
        """Extract the actual dialogue text from a speaker line."""
        # Remove speaker tag and return the text
        match = re.match(r'\[(NARRATOR|TAGALOG-[A-Z]+-\d+)\]:\s*(.*)', line)
        if match:
            return match.group(2).strip()
        return ""
    
    def _extract_word_pairs(self, filipino_text: str, english_text: str) -> List[TranslationPair]:
        """Extract individual word translation pairs from sentence pairs."""
        pairs = []
        
        # Normalize texts
        filipino_words = set(self._extract_meaningful_words(filipino_text))
        english_words = set(self._extract_meaningful_words(english_text))
        
        
        # Look for target English words that have Filipino equivalents
        for english_word in english_words:
            if english_word.lower() in self.target_english_words:
                # Find potential Filipino equivalent in the same sentence
                filipino_candidates = self._find_filipino_equivalent(english_word, filipino_words, filipino_text)
                for filipino_word in filipino_candidates:
                    confidence = self._calculate_confidence(english_word, filipino_word, filipino_text, english_text)
                    if confidence > 0.8:  # Higher threshold for quality
                        pairs.append(TranslationPair(english_word, filipino_word, confidence))
        
        return pairs
    
    def _extract_meaningful_words(self, text: str) -> List[str]:
        """Extract meaningful words from text, filtering out noise."""
        # Remove punctuation and split
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        # Filter out very short words and common stop words
        stop_words = {'po', 'na', 'sa', 'ng', 'si', 'ni', 'ka', 'ko', 'mo', 'to', 'mga', 'ang', 'ay', 'ba', 
                     'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'by', 'for', 'with', 'is', 'are', 'was', 'were'}
        
        return [word for word in words if len(word) > 2 and word not in stop_words]
    
    def _find_filipino_equivalent(self, english_word: str, filipino_words: Set[str], full_filipino_text: str) -> List[str]:
        """Find potential Filipino equivalent(s) for an English word."""
        candidates = []
        
        # Known mappings for common words
        known_mappings = {
            'water': ['tubig'],
            'drinks': ['inumin', 'softdrinks'],
            'welcome': ['maligayang pagdating', 'welcome'],
            'rice': ['kanin', 'bigas'],
            'delicious': ['masarap', 'sarap'],
            'thank you': ['salamat', 'maraming salamat'],
            'please': ['pakisuyo', 'please'],
            'how much': ['magkano'],
            'fresh': ['sariwa', 'sariwang'],
            'perfect': ['perpekto', 'sakto'],
            'beautiful': ['maganda', 'ganda'],
            'expensive': ['mahal'],
            'hot': ['mainit'],
            'cold': ['malamig'],
            'spicy': ['maanghang']
        }
        
        english_lower = english_word.lower()
        if english_lower in known_mappings:
            # Check if any known equivalent appears in the Filipino text
            for filipino_equiv in known_mappings[english_lower]:
                if filipino_equiv in full_filipino_text.lower():
                    candidates.append(filipino_equiv)
        
        # Also include any Filipino words that might be contextually related
        # (This is a simple heuristic - could be enhanced with semantic similarity)
        for filipino_word in filipino_words:
            if len(filipino_word) > 3:  # Avoid very short words
                candidates.append(filipino_word)
        
        return candidates
    
    def _calculate_confidence(self, english_word: str, filipino_word: str, filipino_text: str, english_text: str) -> float:
        """Calculate confidence score for a translation pair."""
        confidence = 0.5  # Base confidence
        
        # Known mappings get higher confidence
        known_mappings = {
            'water': ['tubig'],
            'drinks': ['inumin'],
            'delicious': ['masarap'],
            'thank you': ['salamat'],
            'welcome': ['welcome', 'maligayang'],
            'fresh': ['sariwa', 'sariwang'],
            'perfect': ['perpekto'],
            'how much': ['magkano']
        }
        
        english_lower = english_word.lower()
        if english_lower in known_mappings and filipino_word in known_mappings[english_lower]:
            confidence = 0.95
        
        # Contextual proximity bonus (if words appear close to each other)
        filipino_pos = filipino_text.lower().find(filipino_word)
        english_pos = english_text.lower().find(english_word.lower())
        if filipino_pos != -1 and english_pos != -1:
            # Words found in both texts
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _deduplicate_pairs(self, pairs: List[TranslationPair]) -> List[TranslationPair]:
        """Remove duplicate translation pairs, keeping highest confidence."""
        pair_dict = {}
        
        for pair in pairs:
            key = (pair.english, pair.filipino)
            if key not in pair_dict or pair.confidence > pair_dict[key].confidence:
                pair_dict[key] = pair
        
        return list(pair_dict.values())
    
    def create_enhanced_mappings(self, collocations: Dict[str, int], translation_pairs: List[TranslationPair]) -> Dict[str, Dict]:
        """Create enhanced mappings that include both collocations and translation pairs."""
        enhanced = {}
        
        # Add all collocations as individual entries
        for collocation, count in collocations.items():
            enhanced[collocation] = {
                'type': 'collocation',
                'count': count,
                'stability': 1.0,  # Default stability
                'english_equivalent': None,
                'filipino_equivalent': None
            }
        
        # Add translation pairs and link them
        for pair in translation_pairs:
            # Add English term if not already present
            if pair.english not in enhanced:
                enhanced[pair.english] = {
                    'type': 'english_term',
                    'count': 1,
                    'stability': 1.0,
                    'filipino_equivalent': pair.filipino,
                    'confidence': pair.confidence
                }
            
            # Add Filipino term if not already present  
            if pair.filipino not in enhanced:
                enhanced[pair.filipino] = {
                    'type': 'filipino_term',
                    'count': 1,
                    'stability': 1.0,
                    'english_equivalent': pair.english,
                    'confidence': pair.confidence
                }
            else:
                # Link existing Filipino term to English equivalent
                enhanced[pair.filipino]['english_equivalent'] = pair.english
                enhanced[pair.filipino]['confidence'] = pair.confidence
        
        return enhanced


def test_enhanced_extraction():
    """Test the enhanced extraction with sample story content."""
    sample_content = '''[NARRATOR]: Day 17: Exploring hidden lagoons and boat tours

Key Phrases:

[TAGALOG-FEMALE-1]: salamat po
[NARRATOR]: thank you

[NARRATOR]: Natural Speed

[NARRATOR]: Booking a Boat Tour

[TAGALOG-FEMALE-1]: Kuya, magkano po ang boat tour sa hidden lagoons?
[NARRATOR]: Brother, how much is the boat tour to the hidden lagoons?
[TAGALOG-MALE-1]: Dalawang libo po para sa buong araw, kasama na po ang lunch.
[NARRATOR]: Two thousand for the whole day, lunch included.

[TAGALOG-MALE-2]: Opo! Malinaw na malinaw po ang tubig. Perpekto po para sa pictures.
[NARRATOR]: Yes! The water is crystal clear. Perfect for pictures.'''
    
    extractor = EnhancedCollocationExtractor()
    result = extractor.extract_with_translation_pairs(sample_content)
    
    print("=== ENHANCED EXTRACTION TEST ===")
    print(f"Collocations found: {len(result['collocations'])}")
    print(f"Translation pairs found: {len(result['translation_pairs'])}")
    
    print("\\n--- TRANSLATION PAIRS ---")
    for pair in result['translation_pairs']:
        print(f"  {pair}")
    
    print("\\n--- ENHANCED MAPPINGS (first 10) ---")
    for i, (key, data) in enumerate(result['enhanced_mappings'].items()):
        if i >= 10:
            break
        print(f"  {key}: {data['type']}, equivalent: {data.get('filipino_equivalent') or data.get('english_equivalent', 'None')}")


if __name__ == "__main__":
    test_enhanced_extraction()