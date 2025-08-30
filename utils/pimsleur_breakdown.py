"""
Pimsleur Breakdown Generation for Tagalog Phrases

Generates algorithmic Pimsleur breakdowns following the exact pattern:
1. Start with full phrase
2. Process words right-to-left (last word first)  
3. For each word: syllables backwards, then rebuild word
4. Build partial phrases as you add previous words
5. End with full phrase repeated

Example pattern for "meron po ba kayo":
- meron po ba kayo (full phrase)
- yo (last syllable of last word)
- ka (previous syllable)  
- kayo (rebuilt last word)
- ba (previous word)
- ba kayo (partial phrase)
- po (previous word)
- po ba kayo (partial phrase)
- ron (syllable from first word)
- me (syllable from first word)
- meron (rebuilt first word)
- meron po ba kayo (full phrase)
- meron po ba kayo (repeat)
"""

from typing import List, Dict, Any
import logging

# Core Tagalog syllable patterns for essential words
TAGALOG_SYLLABLES = {
    # Essential courtesy words for Pimsleur breakdown
    "salamat": ["sa", "la", "mat"],
    "kumusta": ["ku", "mus", "ta"],
    "magkano": ["mag", "ka", "no"],
    "puwede": ["pu", "we", "de"],
    "pwede": ["pwe", "de"],
    "magandang": ["ma", "gan", "dang"],
    
    # Core working examples
    "meron": ["me", "ron"],
    "kayo": ["ka", "yo"],
    "tawad": ["ta", "wad"], 
    "balik": ["ba", "lik"],
    "ako": ["a", "ko"],
    "lahat": ["la", "hat"],
    
    # Single syllable particles
    "nga": ["nga"],
    "lang": ["lang"],
    "po": ["po"],
    "ba": ["ba"]
}

def syllabify_tagalog_word(word: str) -> List[str]:
    """
    Break Tagalog word into syllables using official KWF syllabification rules.
    
    Based on Ortograpiyang Pambansa (2013) by Komisyon ng Wikang Filipino:
    - Rule 1: Each syllable must have exactly one vowel sound
    - Rule 2: Consecutive vowels are always separated into different syllables  
    - Rule 3: Single consonant between vowels goes with the following vowel
    - Rule 4: Multiple consonants are split (first with preceding, rest with following)
    - Rule 5: Consonant clusters that can start syllables stay together
    - Rule 6: "ng" is treated as a single consonant unit
    
    Args:
        word: Tagalog word to syllabify
        
    Returns:
        List of syllables following official KWF rules
    """
    word_lower = word.lower().strip()
    
    # Handle empty or very short words
    if not word_lower or len(word_lower) == 1:
        return [word_lower] if word_lower else []
    
    # Check if it's an English loanword - don't syllabify loanwords
    if is_english_loanword(word_lower):
        return [word_lower]
    
    # Apply official KWF syllabification rules
    return _syllabify_kwf_rules(word_lower)


def _syllabify_kwf_rules(word: str) -> List[str]:
    """
    Apply official KWF syllabification rules from Ortograpiyang Pambansa (2013).
    
    Implements the 6 core KWF rules:
    1. Each syllable must have exactly one vowel sound
    2. Consecutive vowels are always separated  
    3. Single consonant between vowels goes with following vowel (V-CV)
    4. Multiple consonants split (VC-CV)
    5. True consonant clusters stay together with following vowel
    6. "ng" treated as single consonant
    """
    if not word:
        return []
    
    # Step 1: Normalize "ng" sequences
    normalized = _normalize_ng_sequences(word)
    
    # Step 2: Apply KWF consecutive vowel separation (Rule 2)
    vowel_separated = _separate_consecutive_vowels(normalized)
    
    # Step 3: Apply core KWF syllable splitting rules
    syllables = _apply_kwf_splitting_rules(vowel_separated)
    
    # Step 4: Denormalize "ng" back
    syllables = _denormalize_ng_sequences(syllables)
    
    return syllables if syllables else [word]


def _normalize_ng_sequences(word: str) -> str:
    """Replace 'ng' with placeholder to treat as single consonant."""
    return word.replace('ng', '§')  # Use § as placeholder for ng


def _denormalize_ng_sequences(syllables: List[str]) -> List[str]:
    """Replace placeholder back with 'ng'."""
    return [syl.replace('§', 'ng') for syl in syllables]


def _separate_consecutive_vowels(word: str) -> str:
    """Apply KWF Rule 2: Consecutive vowels are always separated."""
    vowels = set('aeiou§')  # Include § as vowel-like for ng handling
    result = []
    
    i = 0
    while i < len(word):
        char = word[i]
        result.append(char)
        
        # Check for consecutive vowels
        if (char in vowels and 
            i + 1 < len(word) and 
            word[i + 1] in vowels and 
            char != '§' and word[i + 1] != '§'):  # Don't split on § (ng marker)
            # Insert syllable boundary marker between consecutive vowels
            result.append('|')
        
        i += 1
    
    return ''.join(result)


def _apply_kwf_splitting_rules(word: str) -> List[str]:
    """Apply core KWF syllable splitting rules to word with vowel boundaries marked."""
    # First split on vowel boundary markers
    parts = word.split('|')
    if len(parts) == 1:
        # No consecutive vowel boundaries - apply general syllabification
        return _split_by_kwf_consonant_rules(word)
    
    syllables = []
    
    for i, part in enumerate(parts):
        if not part:  # Skip empty parts
            continue
            
        # Each part separated by | should be syllabified independently
        # This handles cases like "pa|ano" where "ano" needs further syllabification
        part_syllables = _split_by_kwf_consonant_rules(part)
        
        if i == 0:
            # First part - add all syllables
            syllables.extend(part_syllables)
        else:
            # Subsequent parts - distribute consonants with previous syllable if needed
            if part_syllables:
                # Check if we need to distribute consonants between last syllable and first new syllable
                if syllables and part_syllables[0]:
                    # Apply consonant distribution rules between last existing syllable and first new syllable
                    combined_syllables = _distribute_consonants_between_syllables(
                        syllables[-1], part_syllables[0]
                    )
                    # Replace last syllable and add the distributed result
                    syllables[-1] = combined_syllables[0]
                    if len(combined_syllables) > 1:
                        syllables.append(combined_syllables[1])
                    # Add remaining syllables from this part
                    syllables.extend(part_syllables[1:])
                else:
                    syllables.extend(part_syllables)
    
    return syllables


def _distribute_consonants_between_syllables(syl1: str, syl2: str) -> List[str]:
    """
    Distribute consonants between two syllables according to KWF rules.
    This handles the boundary between syllables separated by consecutive vowels.
    
    Args:
        syl1: First syllable (e.g., "pa")
        syl2: Second syllable (e.g., "ano")
        
    Returns:
        List of syllables after consonant distribution
    """
    # For consecutive vowel boundaries, each part is already correctly separated
    # We don't need to redistribute consonants across the vowel boundary
    # Return them as separate syllables
    return [syl1, syl2]


def _split_by_kwf_consonant_rules(word: str) -> List[str]:
    """Split word by general KWF consonant distribution rules."""
    vowels = set('aeiou')  # § is a consonant placeholder, not a vowel
    
    # Find all vowel positions
    vowel_positions = []
    for i, char in enumerate(word):
        if char in vowels:
            vowel_positions.append(i)
    
    if len(vowel_positions) <= 1:
        return [word]  # Single or no vowel - can't split
    
    # Split between vowels according to KWF rules
    syllables = []
    start = 0
    
    for i in range(len(vowel_positions) - 1):
        current_vowel = vowel_positions[i]
        next_vowel = vowel_positions[i + 1]
        
        # Find consonants between vowels
        consonants_between = word[current_vowel + 1:next_vowel]
        
        if not consonants_between:
            # Adjacent vowels - already handled by consecutive vowel separation
            # This shouldn't happen in this context
            syllable = word[start:current_vowel + 1]
            syllables.append(syllable)
            start = current_vowel + 1
        elif len(consonants_between) == 1:
            # Single consonant - goes with following vowel (KWF Rule 3: V-CV)
            syllable = word[start:current_vowel + 1]
            syllables.append(syllable)
            start = current_vowel + 1
        else:
            # Multiple consonants - split them (KWF Rule 4: VC-CV)
            # Check for consonant clusters first
            if len(consonants_between) == 2 and _is_true_consonant_cluster(consonants_between):
                # True cluster - keep together with following vowel
                syllable = word[start:current_vowel + 1]
                syllables.append(syllable)
                start = current_vowel + 1
            elif '§' in consonants_between:
                # Special handling for ng (§) - treat as single consonant
                ng_pos = consonants_between.find('§')
                if ng_pos == 0:
                    # ng at start - take with current vowel (like V§ pattern)
                    split_point = current_vowel + 2  # vowel + § (ng)
                    syllable = word[start:split_point]
                    syllables.append(syllable)
                    start = split_point
                else:
                    # ng not at start - split after first consonant
                    split_point = current_vowel + 2  # vowel + 1 consonant
                    syllable = word[start:split_point]
                    syllables.append(syllable)
                    start = split_point
            else:
                # Split after first consonant
                split_point = current_vowel + 2  # vowel + 1 consonant
                syllable = word[start:split_point]
                syllables.append(syllable)
                start = split_point
    
    # Add the final syllable
    syllables.append(word[start:])
    
    return syllables


def _distribute_consonants_kwf(existing_syllables: List[str], new_part: str) -> List[str]:
    """Distribute consonants between syllables according to KWF rules."""
    if not existing_syllables:
        return [new_part] if new_part else []
    
    # Find consonants at the beginning of new_part and vowel content
    vowels = set('aeiou§')
    consonant_start = ''
    vowel_content = new_part
    
    # Extract leading consonants
    for i, char in enumerate(new_part):
        if char in vowels:
            consonant_start = new_part[:i]
            vowel_content = new_part[i:]
            break
    
    if not consonant_start:
        # No leading consonants - just add the part
        existing_syllables.append(new_part)
        return existing_syllables
    
    # Apply KWF consonant distribution rules
    if len(consonant_start) == 1:
        # Single consonant - goes with following vowel (KWF Rule 3)
        existing_syllables.append(new_part)
    elif len(consonant_start) == 2:
        # Two consonants - check if it's a true consonant cluster
        if _is_true_consonant_cluster(consonant_start):
            # True cluster - keep together with following vowel
            existing_syllables.append(new_part)
        else:
            # Split consonants (KWF Rule 4)
            existing_syllables[-1] += consonant_start[0]
            existing_syllables.append(consonant_start[1:] + vowel_content)
    else:
        # Multiple consonants (3+) - split after first consonant
        existing_syllables[-1] += consonant_start[0]
        existing_syllables.append(consonant_start[1:] + vowel_content)
    
    return existing_syllables


def _has_vowel(text: str) -> bool:
    """Check if text contains a vowel."""
    vowels = set('aeiou')
    return any(c in vowels for c in text.lower())


def _is_true_consonant_cluster(cluster: str) -> bool:
    """Check if consonant cluster can legitimately start a syllable in Filipino.
    
    Based on KWF Rule 5 and Filipino phonotactics.
    True clusters can start syllables and should not be split.
    """
    # Common Filipino consonant clusters that can start syllables
    # Based on actual Filipino phonotactics, not all English clusters are valid in Filipino
    true_clusters = {
        'pr', 'pl', 'br', 'bl', 'tr', 'dr', 'kr', 'kl', 'gr', 'gl', 'fl', 'fr'
    }
    
    # ng is always treated as single unit (KWF Rule 6)
    if cluster == '§':  # Our marker for ng
        return True
        
    return cluster.lower() in true_clusters


# Global dictionary caches for performance
_english_words_cache = None
_tagalog_words_cache = None

def _load_tagalog_dictionary():
    """Load Tagalog dictionary with caching and robust path resolution."""
    global _tagalog_words_cache
    
    if _tagalog_words_cache is not None:
        return _tagalog_words_cache
    
    import os
    
    # Only show detailed debugging when there are issues
    show_debug = False
    
    # Try multiple path resolution strategies for robustness
    potential_paths = [
        # Strategy 1: Relative to current module (original approach)
        os.path.join(os.path.dirname(__file__), '..', 'instance', 'data', 'dictionaries', 'tagalog_words.txt'),
        # Strategy 2: Relative to current working directory
        os.path.join(os.getcwd(), 'instance', 'data', 'dictionaries', 'tagalog_words.txt'),
        # Strategy 3: Relative to project root (assuming we're in utils/)
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'data', 'dictionaries', 'tagalog_words.txt'),
        # Strategy 4: Absolute path if we're in the right place
        'instance/data/dictionaries/tagalog_words.txt'
    ]
    
    for i, path in enumerate(potential_paths):
        try:
            # Normalize and make absolute
            normalized_path = os.path.abspath(os.path.normpath(path))
            
            if os.path.exists(normalized_path):
                with open(normalized_path, 'r', encoding='utf-8') as f:
                    _tagalog_words_cache = set(word.strip().lower() for word in f if word.strip())
                logging.info(f"Successfully loaded {len(_tagalog_words_cache)} Tagalog words from {normalized_path}")
                return _tagalog_words_cache
                
        except (FileNotFoundError, IOError) as e:
            continue
    
    # If all strategies failed - show detailed debugging automatically
    logging.error(f"DICTIONARY LOADING FAILED: All Tagalog dictionary loading strategies failed")
    logging.error(f"Current working directory: {os.getcwd()}")
    logging.error(f"Current module file: {__file__}")
    logging.error(f"Module directory: {os.path.dirname(__file__)}")
    logging.error(f"Tried paths: {[os.path.abspath(os.path.normpath(p)) for p in potential_paths]}")
    for i, path in enumerate(potential_paths):
        normalized_path = os.path.abspath(os.path.normpath(path))
        logging.error(f"  Strategy {i+1}: {normalized_path} - Exists: {os.path.exists(normalized_path)}")
    
    _tagalog_words_cache = set()
    return _tagalog_words_cache

def _load_english_dictionary():
    """Load English dictionary from system dict with caching and debugging."""
    global _english_words_cache
    
    if _english_words_cache is not None:
        return _english_words_cache
    
    import os
    
    # Try multiple common system dictionary locations
    potential_paths = [
        '/usr/share/dict/words',  # Standard Unix/Linux/macOS
        '/usr/dict/words',        # Some older Unix systems
        '/usr/share/dict/american-english',  # Ubuntu/Debian
        '/usr/share/dict/british-english'    # Ubuntu/Debian alternative
    ]
    
    for i, path in enumerate(potential_paths):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    _english_words_cache = set(word.strip().lower() for word in f if word.strip())
                logging.info(f"Successfully loaded {len(_english_words_cache)} English words from {path}")
                return _english_words_cache
                
        except (FileNotFoundError, IOError) as e:
            continue
    
    # If all system dictionaries failed - only show detailed info if Tagalog also failed
    logging.info(f"No system English dictionary found - this is expected on minimal CI environments")
    _english_words_cache = set()
    return _english_words_cache

def is_english_loanword(word: str) -> bool:
    """
    Check if a word is an English loanword that should not be broken down.
    
    Uses dual dictionary approach with Tagalog priority:
    1. If word exists in Tagalog dictionary -> treat as Tagalog (allow breakdown)  
    2. If word exists in English dictionary -> treat as English loanword (prevent breakdown)
    3. Otherwise -> treat as Tagalog (allow breakdown)
    
    This prevents misclassifying Tagalog words like "ate", "po", "ba" as English loanwords.
    
    Args:
        word: Word to check
        
    Returns:
        True if word is English loanword, False otherwise
    """
    word_lower = word.lower().strip()
    
    if not word_lower:
        return False
    
    
    # Load dictionaries
    tagalog_words = _load_tagalog_dictionary()
    english_words = _load_english_dictionary()
    
    # Step 1: Check Tagalog dictionary first (priority)
    # If it's a Tagalog word, always allow breakdown regardless of English status
    if word_lower in tagalog_words:
        return False  # Tagalog word - allow Pimsleur breakdown
    
    # Step 2: Check English dictionary second
    # Only consider it an English loanword if NOT found in Tagalog
    if word_lower in english_words:
        return True
    
    # Try inflected forms for English detection
    english_suffixes = ['ed', 'ing', 's', 'es', 'er', 'est', 'ly', 'tion', 'sion', 'ment', 'ness']
    for suffix in english_suffixes:
        if word_lower.endswith(suffix) and len(suffix) < len(word_lower):
            base_form = word_lower[:-len(suffix)]
            if len(base_form) > 2 and base_form in english_words:
                return True  # English loanword via inflection
    
    # Enhanced error reporting for dictionary failures - show detailed debugging automatically
    if not tagalog_words and not english_words:
        import os
        logging.error(f"CRITICAL: No language dictionaries available for word '{word_lower}'")
        logging.error(f"Dictionary status: Tagalog={len(tagalog_words)} words, English={len(english_words)} words")
        logging.error(f"Current working directory: {os.getcwd()}")
        logging.error(f"Module path: {__file__}")
        
        # Show which dictionary loading attempts were made
        tagalog_paths = [
            os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'instance', 'data', 'dictionaries', 'tagalog_words.txt'))),
            os.path.abspath(os.path.normpath(os.path.join(os.getcwd(), 'instance', 'data', 'dictionaries', 'tagalog_words.txt')))
        ]
        english_paths = ['/usr/share/dict/words', '/usr/dict/words', '/usr/share/dict/american-english']
        
        logging.error(f"Tagalog dictionary attempts:")
        for path in tagalog_paths:
            logging.error(f"  {path} - Exists: {os.path.exists(path)}")
        
        logging.error(f"English dictionary attempts:")
        for path in english_paths:
            logging.error(f"  {path} - Exists: {os.path.exists(path)}")
        
        error_msg = (f"No language dictionaries available - cannot determine loanword status for '{word_lower}'. "
                    f"See detailed path information in logs above.")
        raise RuntimeError(error_msg)
    
    # Default: treat as Tagalog word (allow breakdown)
    return False


def generate_pimsleur_breakdown(phrase: str) -> List[str]:
    """
    Generate traditional Pimsleur breakdown sequence.
    
    Implements the exact pattern from verified examples by manually coding each case.
    This approach ensures perfect matching with the traditional Pimsleur method.
    
    Args:
        phrase: Tagalog phrase to break down
        
    Returns:
        List of breakdown steps for voice assignment
    """
    if not phrase or not phrase.strip():
        return []
    
    # Clean phrase and normalize whitespace
    phrase = " ".join(phrase.strip().split())
    words = phrase.split()
    
    if not words:
        return []
    
    breakdown = []
    
    # Step 1: Always start with full phrase repetition
    breakdown.append(phrase)
    
    # Handle single word case
    if len(words) == 1:
        word = words[0]
        if is_english_loanword(word):
            return breakdown  # English loanwords not broken down
            
        syllables = syllabify_tagalog_word(word)
        if len(syllables) <= 1:
            return breakdown  # Single syllable words not broken down
            
        # Multi-syllable single word breakdown with Pimsleur buildup
        for i in range(len(syllables) - 1, -1, -1):
            # Add the current syllable
            breakdown.append(syllables[i])
            
            # Add progressive buildup combination (if not the first syllable)
            if i < len(syllables) - 1:
                buildup = "".join(syllables[i:])
                breakdown.append(buildup)
        
        # Add complete word
        breakdown.append(word)
        breakdown.append(word)
        return breakdown
    
    # Universal multi-word phrase breakdown
    return _breakdown_phrase_universal(phrase, words, breakdown)


def _breakdown_phrase_universal(phrase: str, words: List[str], breakdown: List[str]) -> List[str]:
    """
    Universal Pimsleur breakdown algorithm that works for any phrase length.
    
    Processes words from right-to-left (Pimsleur method). For each word:
    1. Complete ALL syllable breakdown first
    2. Then add partial phrases from current word to end of phrase
    
    Args:
        phrase: Complete phrase to break down
        words: List of words in the phrase  
        breakdown: Initial breakdown list (should contain the full phrase)
        
    Returns:
        Complete Pimsleur breakdown sequence
    """
    # Process words from right to left (last word first) - phrase building loop  
    for word_index in range(len(words) - 1, -1, -1):
        word = words[word_index]
        
        # STEP 1: Complete syllable breakdown for current word immediately
        if is_english_loanword(word):
            # For loanwords, just add the word itself
            breakdown.append(word)
        else:
            # Get syllables for this word
            syllables = syllabify_tagalog_word(word)
            
            # Only break down multi-syllable words
            if len(syllables) > 1:
                # Do complete syllable breakdown immediately
                for i in range(len(syllables) - 1, -1, -1):
                    # Add the current syllable
                    breakdown.append(syllables[i])
                    
                    # Add progressive buildup combination (including for first syllable)
                    if i < len(syllables) - 1:
                        buildup = "".join(syllables[i:])
                        breakdown.append(buildup)
                    elif i == 0:
                        # For the first syllable, the buildup is the complete word
                        complete_word = "".join(syllables[i:])
                        breakdown.append(complete_word)
            else:
                # Single syllable word - just add it
                breakdown.append(word)
        
        # STEP 2: Add partial phrases from current word to end of phrase
        # (but skip if this is the rightmost word or if it would create the full phrase)
        if word_index < len(words) - 1:  # Not the rightmost word
            # Add phrase from current word to end
            partial_phrase = " ".join(words[word_index:])
            if partial_phrase != phrase:  # Don't duplicate the full phrase
                breakdown.append(partial_phrase)
        
        # Add full phrase only after processing the first (leftmost) word
        if word_index == 0:
            breakdown.append(phrase)
    
    # Final repetition of the complete phrase
    breakdown.append(phrase)
    
    return breakdown


def extract_tagalog_phrases_for_breakdown(content: str) -> List[str]:
    """
    Extract Tagalog phrases from story content that need Pimsleur breakdown.
    
    Args:
        content: Story content containing [TAGALOG-FEMALE-1] markers
        
    Returns:
        List of Tagalog phrases that should get breakdowns
    """
    import re
    
    # Pattern to find [TAGALOG-FEMALE-1]: phrase patterns
    pattern = r'\[TAGALOG-FEMALE-1\]:\s*([^\n\[]+)'
    matches = re.findall(pattern, content)
    
    # Clean and filter phrases
    phrases = []
    for match in matches:
        phrase = match.strip()
        if phrase and len(phrase.split()) >= 2:  # Only multi-word phrases need breakdowns
            phrases.append(phrase)
    
    return phrases


if __name__ == "__main__":
    # Test with example phrases
    test_phrases = [
        "pwede po",
        "meron po ba kayo", 
        "tawad po",
        "balik po ako"
    ]
    
    print("=== Pimsleur Breakdown Testing ===")
    for phrase in test_phrases:
        print(f"\nPhrase: {phrase}")
        breakdown = generate_pimsleur_breakdown(phrase)
        for i, step in enumerate(breakdown):
            print(f"{i+1:2d}. {step}")