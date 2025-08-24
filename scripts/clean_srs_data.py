#!/usr/bin/env python3
"""
Clean corrupted SRS data by removing voice tags, fragments, and nonsensical collocations.
"""

import json
import re
from pathlib import Path
from typing import Dict, Set

def is_corrupted_collocation(text: str) -> bool:
    """
    Identify corrupted collocations that should be removed from SRS.
    
    Uses the same logic as SRSTracker._is_valid_collocation() but inverted.
    Returns True if the collocation appears to be corrupted/invalid.
    """
    text_lower = text.lower().strip()
    
    # Skip empty or too short
    if len(text_lower) <= 1:
        return True
    
    # Voice tags and technical markers
    voice_tags = [
        'tagalog-female', 'tagalog-male', 'narrator', 
        '[narrator', ']', '[tagalog', 'female-1', 'female-2', 'male-1'
    ]
    if any(tag in text_lower for tag in voice_tags):
        return True
    
    # Known problematic phrases and patterns
    problematic_phrases = {
        'sip her mango shake', 'el nido maria', 'bring menus', 'ask pa pong specialty',
        'next time', 'flight', 'two-thirty po', 'pa pong specialty', 'your flight',
        'enjoy el nido', 'safe travels', 'airport', 'good morning', 'thank you'
    }
    if text_lower in problematic_phrases:
        return True
    
    # Mostly English phrases (more than 50% English words)
    english_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'can', 'may',
        'this', 'that', 'these', 'those', 'here', 'there', 'when', 'where',
        'what', 'who', 'how', 'why', 'which', 'bring', 'menus', 'table',
        'food', 'shake', 'enjoy', 'after', 'her', 'his', 'my', 'your',
        'next', 'time', 'flight', 'two', 'thirty', 'sip', 'mango', 'el', 'nido', 'maria'
    }
    words = text_lower.split()
    if len(words) > 1:
        english_count = sum(1 for word in words if word in english_words)
        if english_count / len(words) > 0.5:  # More strict threshold
            return True
    
    # Single words that are entirely English
    if len(words) == 1 and words[0] in english_words:
        return True
        
    # Names that shouldn't be collocations
    names = {'maria', 'juan', 'jose', 'ana', 'pedro', 'elena', 'carlos'}
    if any(name in text_lower for name in names):
        return True
        
    # Repetitive fragments (same word repeated)
    if len(words) > 1 and len(set(words)) == 1:
        return True
    
    # Nonsensical combinations or fragments
    nonsense_patterns = [
        r'.*kami po kami.*',    # Repetitive structure
        r'.*po kami mi.*',      # Fragment ending
        r'.*after tagalog.*',   # Voice tag fragments
        r'^[a-z]$',            # Single lowercase letters
        r'.*-[a-z]+$',         # Fragments ending with dash
    ]
    if any(re.match(pattern, text_lower) for pattern in nonsense_patterns):
        return True
        
    # Must contain at least one Filipino word or pattern
    filipino_indicators = [
        'po', 'ba', 'na', 'ng', 'sa', 'ay', 'ang', 'mga', 'ako', 'ko',
        'mo', 'ito', 'yan', 'yun', 'siya', 'niya', 'kayo', 'ninyo',
        'kami', 'namin', 'tayo', 'natin', 'sila', 'nila', 'magkano',
        'salamat', 'kumusta', 'paumanhin', 'opo', 'hindi', 'oo',
    ]
    if not any(indicator in text_lower for indicator in filipino_indicators):
        # Allow if it looks like a Filipino phrase pattern
        if not re.search(r'[aeiou]{2,}|ng|ny|ts', text_lower):
            return True
    
    return False


def clean_srs_data(srs_file_path: Path, backup: bool = True) -> Dict:
    """
    Clean corrupted collocations from SRS data file.
    """
    print(f"Loading SRS data from {srs_file_path}")
    
    with open(srs_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle nested structure
    if 'collocations' in data:
        collocations = data['collocations']
        other_data = {k: v for k, v in data.items() if k != 'collocations'}
    else:
        collocations = data
        other_data = {}
    
    original_count = len(collocations)
    corrupted_entries = []
    cleaned_collocations = {}
    
    print(f"Found {original_count} total collocations")
    print("Analyzing for corruption...")
    
    for key, value in collocations.items():
        text = value.get('text', key) if isinstance(value, dict) else key
        
        if is_corrupted_collocation(text):
            corrupted_entries.append(text)
            print(f"  🗑️  Removing corrupted: '{text}'")
        else:
            cleaned_collocations[key] = value
    
    print(f"\nCleaning summary:")
    print(f"  Original entries: {original_count}")
    print(f"  Corrupted entries removed: {len(corrupted_entries)}")
    print(f"  Clean entries kept: {len(cleaned_collocations)}")
    print(f"  Corruption rate: {len(corrupted_entries)/original_count*100:.1f}%")
    
    # Create backup if requested
    if backup:
        backup_path = srs_file_path.with_suffix('.backup.json')
        print(f"Creating backup at {backup_path}")
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Reconstruct the full data structure
    cleaned_data = other_data.copy()
    cleaned_data['collocations'] = cleaned_collocations
    
    # Write cleaned data
    print(f"Writing cleaned data to {srs_file_path}")
    with open(srs_file_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    
    print("✅ SRS data cleaning completed!")
    
    return {
        'original_count': original_count,
        'corrupted_count': len(corrupted_entries),
        'clean_count': len(cleaned_collocations),
        'corrupted_entries': corrupted_entries
    }

if __name__ == '__main__':
    import sys
    
    # Default path
    srs_path = Path('data/srs_status.json')
    
    # Allow custom path as argument
    if len(sys.argv) > 1:
        srs_path = Path(sys.argv[1])
    
    if not srs_path.exists():
        print(f"Error: SRS file not found at {srs_path}")
        sys.exit(1)
    
    try:
        result = clean_srs_data(srs_path)
        
        print(f"\nCorrupted entries removed:")
        for entry in result['corrupted_entries']:
            print(f"  - '{entry}'")
            
    except Exception as e:
        print(f"Error cleaning SRS data: {e}")
        sys.exit(1)