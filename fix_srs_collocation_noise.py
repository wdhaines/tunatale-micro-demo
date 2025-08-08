#!/usr/bin/env python3
"""Fix SRS collocation tracking by removing English noise and keeping only Filipino phrases."""

import json
import re
from pathlib import Path

def is_filipino_collocation(text):
    """
    Check if a text is likely a Filipino collocation we want to track.
    
    Returns True for:
    - Phrases containing 'po' (Filipino politeness marker)
    - Common Filipino words (ang, sa, na, ng, etc.)
    - Mixed Filipino-English phrases that are authentic
    """
    text_lower = text.lower().strip()
    
    # Empty or very short phrases
    if not text_lower or len(text_lower) < 3:
        return False
    
    # Contains Filipino politeness markers
    if ' po' in text_lower or text_lower.endswith(' po') or text_lower == 'po':
        return True
    
    # Common Filipino function words and authentic phrases
    filipino_indicators = [
        'ang ', 'sa ', 'na ', 'ng ', 'mga ', 'kay ', 'ni ', 'si ',
        'magandang', 'salamat', 'meron', 'wala', 'kumusta', 'paano',
        'saan', 'anong', 'ilan', 'dalawa', 'tatlo', 'apat', 'lima',
        'tubig', 'kwarto', 'oras', 'araw', 'gabi', 'umaga', 'hapon',
        'malapit', 'malayo', 'kaliwa', 'kanan', 'derecho', 'lakad',
        'bawal', 'meron', 'wala', 'gusto', 'ayaw', 'sukli', 'bayad',
        'flight', 'hotel', 'airport'  # Common in travel context
    ]
    
    # Check if contains any Filipino indicators
    for indicator in filipino_indicators:
        if indicator in text_lower:
            return True
    
    # Phrases that are clearly English names or common English words we don't want
    english_noise = [
        'carlos', 'maria', 'john', 'jane', 'the waiter', 'waiter', 
        'clerk', 'customer', 'person', 'man', 'woman', 'table',
        'restaurant', 'hotel', 'building', 'floor', 'room', 'door',
        'water', 'food', 'menu', 'bill', 'money', 'change',
        'time', 'day', 'night', 'morning', 'afternoon', 'evening',
        'left', 'right', 'straight', 'walk', 'go', 'come', 'here', 'there'
    ]
    
    # Don't track pure English noise
    if text_lower in english_noise:
        return False
    
    # Don't track single English words unless they're part of authentic mixed phrases
    words = text_lower.split()
    if len(words) == 1 and not any(indicator in text_lower for indicator in filipino_indicators):
        # Single word that doesn't contain Filipino indicators
        return False
    
    return True

def analyze_srs_collocations():
    """Analyze what's currently in the SRS file."""
    srs_path = Path("data/srs_status.json")
    
    if not srs_path.exists():
        print("No SRS file found")
        return
    
    with open(srs_path, 'r', encoding='utf-8') as f:
        srs_data = json.load(f)
    
    collocations = srs_data.get('collocations', {})
    
    filipino_collocations = {}
    english_noise = {}
    
    for text, data in collocations.items():
        if is_filipino_collocation(text):
            filipino_collocations[text] = data
        else:
            english_noise[text] = data
    
    print(f"=== SRS ANALYSIS ===")
    print(f"Total collocations: {len(collocations)}")
    print(f"Filipino collocations: {len(filipino_collocations)}")
    print(f"English noise: {len(english_noise)}")
    
    print(f"\n=== FILIPINO COLLOCATIONS (keeping these) ===")
    for text in sorted(filipino_collocations.keys()):
        print(f"  ✓ '{text}'")
    
    print(f"\n=== ENGLISH NOISE (removing these) ===")
    for text in sorted(list(english_noise.keys())[:20]):  # Show first 20
        print(f"  ✗ '{text}'")
    
    if len(english_noise) > 20:
        print(f"  ... and {len(english_noise) - 20} more")
    
    return filipino_collocations, english_noise, srs_data

def fix_srs_file():
    """Clean the SRS file by removing English noise."""
    filipino_collocations, english_noise, srs_data = analyze_srs_collocations()
    
    if not filipino_collocations:
        print("No Filipino collocations found. Something is wrong.")
        return
    
    # Create backup
    srs_path = Path("data/srs_status.json")
    backup_path = srs_path.with_suffix('.json.backup')
    
    import shutil
    shutil.copy2(srs_path, backup_path)
    print(f"\nBackup created: {backup_path}")
    
    # Create cleaned data
    cleaned_data = {
        'current_day': srs_data.get('current_day', 1),
        'collocations': filipino_collocations
    }
    
    # Write cleaned file
    with open(srs_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== SRS FILE CLEANED ===")
    print(f"Kept: {len(filipino_collocations)} Filipino collocations")
    print(f"Removed: {len(english_noise)} English noise entries")
    print(f"Cleaned file saved to: {srs_path}")

if __name__ == "__main__":
    fix_srs_file()