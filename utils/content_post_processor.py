"""
Enhanced Content Post-Processing for TunaTale Story Generation

Handles algorithmic fixes to LLM-generated content, specifically:
- Always generates correct Pimsleur breakdowns algorithmically
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
    
    lines = content.split('\n')
    in_key_phrases = False
    current_phrase = None
    phrase_start_line = None
    breakdown_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Check if we're entering Key Phrases section
        if line == "Key Phrases:":
            in_key_phrases = True
            continue
            
        # Check if we're leaving Key Phrases section
        if in_key_phrases and line.startswith("[NARRATOR]: Natural Speed"):
            # Handle last phrase if we ended while still in key phrases
            if current_phrase and breakdown_lines:
                phrases.append((current_phrase, phrase_start_line, i - 1, breakdown_lines[:]))
            in_key_phrases = False
            break
            
        if not in_key_phrases:
            continue
            
        # Look for Tagalog phrase pattern: [TAGALOG-X]: phrase
        tagalog_match = re.match(r'\[TAGALOG-(?:FEMALE|MALE)-\d+\]:\s*(.+)', line)
        if tagalog_match:
            # Store previous phrase if we had one
            if current_phrase and breakdown_lines:
                phrases.append((current_phrase, phrase_start_line, i - 1, breakdown_lines[:]))
            
            # Start new phrase
            current_phrase = tagalog_match.group(1).strip()
            phrase_start_line = i
            breakdown_lines = []
            continue
            
        # Check if this is a translation line
        if re.match(r'\[NARRATOR\]:\s*(.+)', line):
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
    Generate algorithmic Pimsleur breakdowns for all Key Phrases, replacing any existing breakdowns.
    
    Args:
        content: Full story content that may or may not have breakdowns
        
    Returns:
        Content with correct algorithmic Pimsleur breakdowns added
    """
    try:
        lines = content.split('\n')
        result_lines = []
        i = 0
        in_key_phrases = False
        processed_phrases = set()  # Track processed phrases to avoid duplicates
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Check if we're entering Key Phrases section
            if line == "Key Phrases:":
                in_key_phrases = True
                processed_phrases.clear()  # Reset for each Key Phrases section
                result_lines.append(lines[i])
                i += 1
                continue
                
            # Check if we're leaving Key Phrases section  
            if in_key_phrases and line.startswith("[NARRATOR]: Natural Speed"):
                in_key_phrases = False
                result_lines.append(lines[i])
                i += 1
                continue
            
            # Process Key Phrases section
            if in_key_phrases:
                # Look for Tagalog phrase pattern: [TAGALOG-X]: phrase
                tagalog_match = re.match(r'\[TAGALOG-(?:FEMALE|MALE)-\d+\]:\s*(.+)', line)
                if tagalog_match:
                    phrase = tagalog_match.group(1).strip()
                    
                    # Skip if we've already processed this phrase
                    if phrase in processed_phrases:
                        logging.debug(f"Skipping duplicate phrase: '{phrase}'")
                        # Skip this entire phrase section
                        i += 1
                        # Skip narrator translation if present
                        if (i < len(lines) and 
                            re.match(r'\[NARRATOR\]:\s*(.+)', lines[i].strip())):
                            i += 1
                        # Skip all existing breakdown content
                        while (i < len(lines) and 
                               lines[i].strip() and 
                               not lines[i].strip().startswith('[') and
                               not lines[i].strip() == "Key Phrases:"):
                            i += 1
                        continue
                    
                    # Only process if this looks like a legitimate phrase (not a breakdown fragment)
                    # Legitimate phrases should be followed by a narrator translation
                    next_line_is_narrator = (i + 1 < len(lines) and 
                                           re.match(r'\[NARRATOR\]:\s*(.+)', lines[i + 1].strip()))
                    
                    if not next_line_is_narrator:
                        # This is likely a breakdown line with voice tags, skip it
                        logging.debug(f"Skipping voice-tagged breakdown line: '{phrase}'")
                        i += 1
                        continue
                    
                    # Process this phrase (first time we've seen it and has narrator translation)
                    processed_phrases.add(phrase)
                    result_lines.append(lines[i])  # Add the tagalog line
                    i += 1
                    
                    # Look for narrator translation (should be next)
                    if (i < len(lines) and 
                        re.match(r'\[NARRATOR\]:\s*(.+)', lines[i].strip())):
                        result_lines.append(lines[i])  # Add translation
                        i += 1
                    
                    # Skip ALL existing breakdown lines (anything that's not a voice tag or section marker)
                    # This includes any existing phrase repetitions
                    while (i < len(lines) and 
                           lines[i].strip() and 
                           not lines[i].strip().startswith('[') and
                           not lines[i].strip() == "Key Phrases:"):
                        i += 1
                    
                    # Generate correct algorithmic Pimsleur breakdown (includes proper phrase repetition)
                    logging.debug(f"Generating Pimsleur breakdown for phrase: '{phrase}'")
                    breakdown_lines = generate_pimsleur_breakdown(phrase)
                    for breakdown_line in breakdown_lines:
                        result_lines.append(breakdown_line)
                    
                    # Add blank line after breakdown if the next line isn't already blank
                    if i < len(lines) and lines[i].strip():
                        result_lines.append("")
                    continue
                    
                # Handle empty lines in key phrases section
                elif not line:
                    result_lines.append(lines[i])
                    i += 1
                    continue
            
            # Add line as-is if not in key phrases processing
            result_lines.append(lines[i])
            i += 1
            
        return '\n'.join(result_lines)
        
    except Exception as e:
        logging.error(f"Error in fix_pimsleur_breakdowns: {e}")
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
        logging.warning("Post-processing called with empty content")
        return content
        
    logging.info("🔧 Starting story content post-processing")
    logging.debug(f"Content length: {len(content)} characters")
    
    try:
        # Apply Pimsleur breakdown corrections
        logging.info("Applying algorithmic Pimsleur breakdown generation...")
        corrected_content = fix_pimsleur_breakdowns(content)
        
        # Check if any changes were made
        if corrected_content != content:
            logging.info("✅ Pimsleur breakdowns were generated algorithmically")
        else:
            logging.info("ℹ️ No Pimsleur breakdown changes needed")
        
        # Future post-processing steps can be added here:
        # - Content validation
        # - Format standardization  
        # - Quality checks
        
        logging.info("🔧 Story content post-processing completed")
        return corrected_content
        
    except Exception as e:
        logging.error(f"❌ Post-processing failed: {e}")
        logging.debug("Returning original content due to post-processing error")
        return content