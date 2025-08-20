"""
Content Post-Processing for TunaTale Story Generation

Handles algorithmic fixes to LLM-generated content, specifically:
- Pimsleur breakdown correction using algorithmic generation
- Content validation and quality checks
"""

import re
import logging
from typing import List, Tuple, Optional
from utils.pimsleur_breakdown import generate_pimsleur_breakdown


def extract_key_phrases_sections(content: str) -> List[Tuple[str, int, int]]:
    """
    Extract Key Phrases sections from story content.
    
    Args:
        content: Full story content
        
    Returns:
        List of (phrase, start_pos, end_pos) tuples for each key phrase section
    """
    phrases = []
    
    # Pattern to find key phrase sections:
    # [TAGALOG-FEMALE-1]: phrase
    # [NARRATOR]: translation  
    # [TAGALOG-FEMALE-1]: phrase
    # [breakdown lines...]
    # 
    # Until next [TAGALOG-X] or [NARRATOR]: (not translation)
    
    # Find all Tagalog phrases in Key Phrases sections
    lines = content.split('\n')
    in_key_phrases = False
    current_phrase = None
    phrase_start_line = 0
    breakdown_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Check if we're entering Key Phrases section
        if line == "Key Phrases:":
            in_key_phrases = True
            continue
            
        # Check if we're leaving Key Phrases section
        if in_key_phrases and (line.startswith("[NARRATOR]: Natural Speed") or 
                              line.startswith("[NARRATOR]: Slow Speed")):
            # Process any pending phrase
            if current_phrase and breakdown_lines:
                end_line = i - 1
                phrases.append((current_phrase, phrase_start_line, end_line, breakdown_lines[:]))
            in_key_phrases = False
            break
            
        if not in_key_phrases:
            continue
            
        # Look for Tagalog phrase pattern
        tagalog_match = re.match(r'\[TAGALOG-[FEMALE|MALE]+-\d+\]:\s*(.+)', line)
        if tagalog_match:
            # Save previous phrase if exists
            if current_phrase and breakdown_lines:
                end_line = i - 1
                phrases.append((current_phrase, phrase_start_line, end_line, breakdown_lines[:]))
                
            # Start new phrase
            current_phrase = tagalog_match.group(1).strip()
            phrase_start_line = i
            breakdown_lines = []
            continue
            
        # Look for narrator translation
        narrator_match = re.match(r'\[NARRATOR\]:\s*(.+)', line)
        if narrator_match and current_phrase:
            # This is the translation line - skip it
            continue
            
        # Look for phrase repetition (start of breakdown)
        if line == current_phrase:
            # This starts the breakdown section
            continue
            
        # Collect breakdown lines (everything else until next phrase)
        if current_phrase and line and not line.startswith('['):
            breakdown_lines.append(line)
    
    # Handle last phrase if we ended while still in key phrases
    if in_key_phrases and current_phrase and breakdown_lines:
        phrases.append((current_phrase, phrase_start_line, len(lines) - 1, breakdown_lines[:]))
        
    return phrases


def fix_pimsleur_breakdowns(content: str) -> str:
    """
    Replace LLM-generated Pimsleur breakdowns with algorithmically correct ones.
    Uses a simpler pattern-based approach.
    
    Args:
        content: Full story content with potentially incorrect breakdowns
        
    Returns:
        Content with corrected breakdowns
    """
    try:
        lines = content.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            result_lines.append(lines[i])
            
            # Look for Key Phrases section pattern:
            # [TAGALOG-FEMALE-1]: phrase
            # [NARRATOR]: translation  
            # [TAGALOG-FEMALE-1]: phrase (repetition)
            # [breakdown lines...]
            
            tagalog_match = re.match(r'\[TAGALOG-[FEMALE|MALE]+-\d+\]:\s*(.+)', line)
            if tagalog_match and i > 0 and "Key Phrases:" in '\n'.join(lines[max(0, i-10):i]):
                phrase = tagalog_match.group(1).strip()
                
                # Check if next line is narrator translation
                if (i + 1 < len(lines) and 
                    lines[i + 1].strip().startswith('[NARRATOR]:')):
                    
                    # Add the translation line
                    i += 1
                    result_lines.append(lines[i])
                    
                    # Check if next line is phrase repetition
                    if (i + 1 < len(lines) and 
                        lines[i + 1].strip() == f'[TAGALOG-FEMALE-1]: {phrase}' or
                        lines[i + 1].strip() == f'[TAGALOG-MALE-1]: {phrase}' or
                        lines[i + 1].strip() == f'[TAGALOG-FEMALE-2]: {phrase}' or  
                        lines[i + 1].strip() == f'[TAGALOG-MALE-2]: {phrase}'):
                        
                        # Add the repetition line
                        i += 1
                        result_lines.append(lines[i])
                        
                        # Skip old breakdown lines until we hit next section
                        breakdown_start = i + 1
                        while (breakdown_start < len(lines) and 
                               not lines[breakdown_start].strip().startswith('[TAGALOG-') and
                               not lines[breakdown_start].strip().startswith('[NARRATOR]: Natural Speed') and
                               not lines[breakdown_start].strip().startswith('[NARRATOR]: Slow Speed')):
                            breakdown_start += 1
                        
                        # Generate correct breakdown
                        logging.info(f"Correcting breakdown for phrase: '{phrase}'")
                        correct_breakdown = generate_pimsleur_breakdown(phrase)
                        
                        # Add correct breakdown lines
                        for breakdown_line in correct_breakdown:
                            result_lines.append(breakdown_line)
                        
                        # Skip to the next section (after old breakdown)
                        i = breakdown_start - 1  # -1 because the loop will increment
            
            i += 1
        
        return '\n'.join(result_lines)
        
    except Exception as e:
        logging.error(f"Error fixing Pimsleur breakdowns: {e}")
        logging.debug("Returning original content due to processing error")
        return content


def post_process_story_content(content: str) -> str:
    """
    Apply all post-processing fixes to story content.
    
    Args:
        content: Raw LLM-generated story content
        
    Returns:
        Post-processed content with algorithmic corrections
    """
    if not content:
        return content
        
    logging.info("Starting story content post-processing")
    
    # Apply Pimsleur breakdown corrections
    corrected_content = fix_pimsleur_breakdowns(content)
    
    # Future post-processing steps can be added here:
    # - Content validation
    # - Format standardization  
    # - Quality checks
    
    logging.info("Story content post-processing completed")
    return corrected_content


if __name__ == "__main__":
    # Test with sample content
    sample_content = """[NARRATOR]: Day 14: Shopping - Day 6 Revisited

Key Phrases:

[TAGALOG-FEMALE-1]: meron po ba kayo
[NARRATOR]: do you have
[TAGALOG-FEMALE-1]: meron po ba kayo
kayo
ba kayo
po ba kayo
ron po ba kayo
me
meron
meron po
meron po ba
meron po ba kayo
meron po ba kayo

[NARRATOR]: Natural Speed
"""
    
    print("=== Content Post-Processing Test ===")
    print("\nOriginal breakdown:")
    phrases = extract_key_phrases_sections(sample_content)
    for phrase, start, end, breakdown in phrases:
        print(f"Phrase: {phrase}")
        print(f"Breakdown: {breakdown}")
        
    print("\nCorrected content:")
    corrected = post_process_story_content(sample_content)
    print(corrected)