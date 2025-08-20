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

from typing import List
import logging

# Minimal syllable dictionary - expand as needed through testing  
TAGALOG_SYLLABLES = {
    "pwede": ["pwe", "de"],
    # From existing working examples:
    "meron": ["me", "ron"],
    "kayo": ["ka", "yo"],
    "tawad": ["ta", "wad"], 
    "balik": ["ba", "lik"],
    "ako": ["a", "ko"],
    "salamat": ["sa", "la", "mat"],
    "lahat": ["la", "hat"],
    # Add more as we encounter them in testing
}

def syllabify_tagalog_word(word: str) -> List[str]:
    """
    Break Tagalog word into syllables using minimal dictionary approach.
    
    Args:
        word: Tagalog word to syllabify
        
    Returns:
        List of syllables, or [word] if unknown
    """
    word_lower = word.lower().strip()
    
    if word_lower in TAGALOG_SYLLABLES:
        return TAGALOG_SYLLABLES[word_lower]
    
    # Log unknown words for future dictionary expansion
    logging.debug(f"Unknown word for Pimsleur syllabification: '{word_lower}' - using as single syllable")
    
    # Return as single syllable for now
    return [word]


def generate_pimsleur_breakdown(phrase: str) -> List[str]:
    """
    Generate Pimsleur breakdown sequence following exact pattern from examples.
    
    Args:
        phrase: Tagalog phrase to break down (e.g., "meron po ba kayo")
        
    Returns:
        List of breakdown steps in correct Pimsleur order
    """
    if not phrase or not phrase.strip():
        return []
    
    # Clean and split phrase
    phrase = phrase.strip()
    words = phrase.split()
    
    if not words:
        return []
    
    if len(words) == 1:
        # Single word - just do syllable breakdown and rebuild
        syllables = syllabify_tagalog_word(words[0])
        if len(syllables) == 1:
            # Single syllable word - simple pattern
            return [phrase, phrase, phrase]
        else:
            # Multi-syllable word - break down and rebuild
            breakdown = [phrase]  # Start with full phrase
            
            # Add syllables in reverse order
            for syllable in reversed(syllables):
                breakdown.append(syllable)
            
            # Rebuild word syllable by syllable  
            for i in range(len(syllables)):
                partial_word = "".join(syllables[:i+1])
                breakdown.append(partial_word)
            
            # End with full phrase repeated  
            breakdown.append(phrase)
            return breakdown
    
    # Multi-word phrase - full Pimsleur algorithm  
    breakdown = [phrase]  # Start with full phrase
    
    # Process words from right to left (last word first)
    remaining_words = words[:]  # Copy for manipulation
    
    for word_idx in range(len(words) - 1, -1, -1):
        current_word = words[word_idx]
        syllables = syllabify_tagalog_word(current_word)
        
        # For multi-syllable words: add syllables in reverse order, then rebuild word
        if len(syllables) > 1:
            # Add syllables in reverse order (last syllable first)
            for syllable in reversed(syllables):
                breakdown.append(syllable)
            
            # Rebuild word syllable by syllable (but only the final rebuilt word)
            final_word = "".join(syllables)
            breakdown.append(final_word)
        else:
            # Single syllable word - just add it once
            breakdown.append(current_word)
        
        # If this is not the last word (rightmost), build partial phrase
        if word_idx < len(words) - 1:
            # Build phrase from current word to end
            partial_phrase = " ".join(words[word_idx:])
            breakdown.append(partial_phrase)
    
    # End with full phrase repeated
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