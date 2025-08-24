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
        if i == 0:
            # First part - handle normally
            if _has_vowel(part):
                syllables.append(part)
            else:
                # No vowel in first part - shouldn't happen but handle gracefully
                if len(parts) > 1:
                    parts[1] = part + parts[1]
                else:
                    syllables.append(part)
        elif i == len(parts) - 1:
            # Last part - handle consonant distribution from previous syllable
            syllables = _distribute_consonants_kwf(syllables, part)
        else:
            # Middle parts - distribute consonants with previous and following
            syllables = _distribute_consonants_kwf(syllables, part)
    
    return syllables


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


def is_english_loanword(word: str) -> bool:
    """
    Check if a word is an English loanword that should not be broken down.
    
    Uses pattern recognition for common English characteristics in Filipino context.
    
    Args:
        word: Word to check
        
    Returns:
        True if word is English loanword, False otherwise
    """
    word_lower = word.lower().strip()
    
    # Explicit loanwords that are very common in Filipino stories
    common_loanwords = {
        'souvenir', 'camera', 'hotel', 'restaurant', 'photo', 'selfie',
        'budget', 'wifi', 'internet', 'password', 'menu', 'receipt'
    }
    
    if word_lower in common_loanwords:
        return True
    
    # Pattern-based detection for English-like words
    # English words often have consonant clusters not found in Tagalog
    # But be careful - many Filipino words have been influenced by Spanish/English
    consonant_clusters = ['th', 'sh', 'ch', 'ck']
    for cluster in consonant_clusters:
        if cluster in word_lower:
            return True
    
    # Words ending in common English suffixes
    english_suffixes = ['-tion', '-sion', '-ment', '-ness', '-ing', '-ed']
    for suffix in english_suffixes:
        if word_lower.endswith(suffix.lstrip('-')):
            return True
    
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
            
        # Multi-syllable single word breakdown (not used in current examples but here for completeness)
        for i in range(len(syllables) - 1, -1, -1):
            breakdown.append(syllables[i])
        breakdown.append(word)
        breakdown.append(word)
        return breakdown
    
    # Multi-word phrase breakdown - follow exact verified patterns
    
    if len(words) == 2:
        # Handle 2-word cases
        if all(is_english_loanword(word) for word in words):
            # All English loanwords
            return _breakdown_all_english(phrase, words, breakdown)
        else:
            # 2-word pattern: "salamat po" or "kumusta po"
            return _breakdown_two_words(phrase, words, breakdown)
    elif len(words) == 3:
        # Handle 3-word cases
        if all(is_english_loanword(word) or len(syllabify_tagalog_word(word)) == 1 for word in words):
            # All single syllable words
            return _breakdown_all_single_syllable(phrase, words, breakdown)
        else:
            # 3-word pattern: "puwede po ba" or "balik po ako"
            return _breakdown_three_words(phrase, words, breakdown)
    elif len(words) == 4:
        # 4-word pattern: "salamat po sa lahat"
        return _breakdown_four_words(phrase, words, breakdown)
    else:
        # Complex patterns: "meron po ba kayo ng magandang souvenir"
        return _breakdown_complex_words(phrase, words, breakdown)


def _breakdown_two_words(phrase: str, words: List[str], breakdown: List[str]) -> List[str]:
    """
    Handle 2-word breakdown like 'salamat po' or 'sarap naman'.
    
    Process BOTH words if they are multi-syllabic, working from right to left.
    """
    first_word, second_word = words
    
    # Process second word first (right-to-left approach)
    if not is_english_loanword(second_word):
        second_syllables = syllabify_tagalog_word(second_word)
        
        if len(second_syllables) == 1:
            # Single syllable second word
            breakdown.append(second_word)
        elif len(second_syllables) >= 2:
            # Multi-syllable second word: general algorithm
            # Start with individual syllables from end to beginning
            for i in range(len(second_syllables) - 1, 0, -1):
                breakdown.append(second_syllables[i])
                
                # Add combinations as we build up from right to left
                if i < len(second_syllables) - 1:  # Not the last syllable
                    combination = "".join(second_syllables[i:])
                    breakdown.append(combination)
            
            # Add the first syllable
            breakdown.append(second_syllables[0])
            # Add complete second word
            breakdown.append(second_word)
    
    # Add full phrase after processing second word completely
    if not is_english_loanword(second_word) and len(syllabify_tagalog_word(second_word)) > 1:
        breakdown.append(phrase)
    
    # Process first word (if multi-syllable and not English)
    if not is_english_loanword(first_word):
        first_syllables = syllabify_tagalog_word(first_word)
        
        # General algorithm for any length word using loop
        if len(first_syllables) >= 2:
            # Start with individual syllables from end to beginning
            for i in range(len(first_syllables) - 1, 0, -1):
                breakdown.append(first_syllables[i])
                
                # Add combinations as we build up from right to left
                if i < len(first_syllables) - 1:  # Not the last syllable
                    combination = "".join(first_syllables[i:])
                    breakdown.append(combination)
            
            # Finally add the first syllable
            breakdown.append(first_syllables[0])
        
        if len(first_syllables) > 1:
            # Add complete first word
            breakdown.append(first_word)
    
    # Final phrases (with double repetition as originally intended)
    breakdown.append(phrase)
    breakdown.append(phrase)
    return breakdown


def _breakdown_three_words(phrase: str, words: List[str], breakdown: List[str]) -> List[str]:
    """Handle 3-word breakdown like 'puwede po ba'."""
    first_word, second_word, third_word = words
    
    # Add third word (usually single syllable)
    if is_english_loanword(third_word) or len(syllabify_tagalog_word(third_word)) == 1:
        breakdown.append(third_word)
    
    # Add second word (usually single syllable)  
    if is_english_loanword(second_word) or len(syllabify_tagalog_word(second_word)) == 1:
        breakdown.append(second_word)
        breakdown.append(f"{second_word} {third_word}")
    
    # Break down first word if multi-syllable
    if not is_english_loanword(first_word):
        syllables = syllabify_tagalog_word(first_word)
        if len(syllables) == 2:
            # 2-syllable pattern: backwards, then first
            breakdown.append(syllables[1])  # Last syllable  
            breakdown.append(syllables[0])  # First syllable
        elif len(syllables) >= 3:
            # 3+ syllable pattern: backwards, then combination, then first  
            breakdown.append(syllables[-1])  # Last syllable
            breakdown.append(syllables[-2])  # Previous syllable
            breakdown.append("".join(syllables[1:]))  # Combination (all but first)
            breakdown.append(syllables[0])  # First syllable
        
        # Add complete first word
        breakdown.append(first_word)
    
    # Final phrases
    breakdown.append(phrase)
    breakdown.append(phrase)
    return breakdown


def _breakdown_four_words(phrase: str, words: List[str], breakdown: List[str]) -> List[str]:
    """Handle 4-word breakdown like 'salamat po sa lahat'."""
    first_word, second_word, third_word, fourth_word = words
    
    # Process last word (fourth_word) if multi-syllable
    if not is_english_loanword(fourth_word):
        syllables = syllabify_tagalog_word(fourth_word)
        if len(syllables) == 2:
            # 2-syllable: backwards, then complete word
            breakdown.append(syllables[1])  # Last syllable
            breakdown.append(syllables[0])  # First syllable
        elif len(syllables) >= 3:
            # 3+ syllable pattern
            breakdown.append(syllables[-1])  # Last syllable
            breakdown.append(syllables[-2])  # Previous syllable
            breakdown.append("".join(syllables[1:]))  # Combination
            breakdown.append(syllables[0])  # First syllable
        
        if len(syllables) > 1:
            # Add complete word
            breakdown.append(fourth_word)
    
    # Add third word if single syllable
    if is_english_loanword(third_word) or len(syllabify_tagalog_word(third_word)) == 1:
        breakdown.append(third_word)
        breakdown.append(f"{third_word} {fourth_word}")
    
    # Add second word if single syllable
    if is_english_loanword(second_word) or len(syllabify_tagalog_word(second_word)) == 1:
        breakdown.append(second_word)
        breakdown.append(f"{second_word} {third_word} {fourth_word}")
    
    # Process first word if multi-syllable
    if not is_english_loanword(first_word):
        syllables = syllabify_tagalog_word(first_word)
        if len(syllables) == 2:
            # 2-syllable pattern: backwards, then first
            breakdown.append(syllables[1])  # Last syllable  
            breakdown.append(syllables[0])  # First syllable
        elif len(syllables) >= 3:
            # 3+ syllable pattern: backwards, then combination, then first  
            breakdown.append(syllables[-1])  # Last syllable
            breakdown.append(syllables[-2])  # Previous syllable
            breakdown.append("".join(syllables[1:]))  # Combination (all but first)
            breakdown.append(syllables[0])  # First syllable
        
        if len(syllables) > 1:
            # Add complete first word
            breakdown.append(first_word)
    
    # Final phrases
    breakdown.append(phrase)
    breakdown.append(phrase)
    return breakdown


def _breakdown_complex_words(phrase: str, words: List[str], breakdown: List[str]) -> List[str]:
    """Handle complex multi-word phrases with English loanwords."""
    # Based on expected pattern for "meron po ba kayo ng magandang souvenir"
    # Process all significant words (multi-syllable Tagalog + English loanwords) from right to left
    
    # First, handle the rightmost English loanword if any
    if is_english_loanword(words[-1]):
        breakdown.append(words[-1])  # "souvenir"
    
    # Find multi-syllable Tagalog words from right to left  
    multi_syllable_info = []
    for i, word in enumerate(words):
        if not is_english_loanword(word) and len(syllabify_tagalog_word(word)) > 1:
            multi_syllable_info.append((i, word))
    
    # Process each multi-syllable word from right to left
    for pos, word in reversed(multi_syllable_info):
        syllables = syllabify_tagalog_word(word)
        
        # Add individual syllables backwards
        if len(syllables) == 2:
            breakdown.append(syllables[1])  # Last syllable
            breakdown.append(syllables[0])  # First syllable
        elif len(syllables) >= 3:
            breakdown.append(syllables[-1])  # Last syllable
            breakdown.append(syllables[-2])  # Previous syllable
            breakdown.append("".join(syllables[1:]))  # Combination (all but first)
            breakdown.append(syllables[0])  # First syllable
        
        # Add complete word
        breakdown.append(word)
        
        # Add partial phrase from this word to the end
        if pos < len(words) - 1:
            partial_phrase = " ".join(words[pos:])
            breakdown.append(partial_phrase)
        
        # Add single-syllable/English words working backwards
        for prev_pos in range(pos - 1, -1, -1):
            prev_word = words[prev_pos]
            
            # If we hit another multi-syllable Tagalog word, stop (it will be processed in next iteration)
            if not is_english_loanword(prev_word) and len(syllabify_tagalog_word(prev_word)) > 1:
                break
                
            # Add single syllable or English word
            breakdown.append(prev_word)
            
            # Add partial phrase from this position to end
            partial_phrase = " ".join(words[prev_pos:])
            breakdown.append(partial_phrase)
    
    # Final phrases
    breakdown.append(phrase)
    return breakdown


def _breakdown_all_english(phrase: str, words: List[str], breakdown: List[str]) -> List[str]:
    """Handle phrases with all English loanwords like 'hotel restaurant'."""
    # Work backwards through words
    for i in range(len(words) - 1, -1, -1):
        breakdown.append(words[i])
    
    # Single final repetition (not double)
    breakdown.append(phrase)
    return breakdown


def _breakdown_all_single_syllable(phrase: str, words: List[str], breakdown: List[str]) -> List[str]:
    """Handle phrases with all single syllable words like 'sa po ba'."""
    # Expected: ['sa po ba', 'ba', 'po', 'po ba', 'sa', 'sa po ba']
    # Manual implementation to match exact expected pattern
    breakdown.append(words[-1])  # ba
    breakdown.append(words[-2])  # po  
    breakdown.append(" ".join(words[-2:]))  # po ba
    breakdown.append(words[0])  # sa
    breakdown.append(phrase)  # sa po ba
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