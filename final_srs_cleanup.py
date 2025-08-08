#!/usr/bin/env python3
"""Final cleanup to remove formatting artifacts and structural elements from SRS."""

import json
import re
from pathlib import Path

def is_clean_filipino_phrase(text):
    """
    Check if a phrase is a clean Filipino learning phrase without formatting artifacts.
    
    Returns True only for clean phrases that learners should actually review.
    """
    text_cleaned = text.strip()
    
    # Skip empty phrases
    if not text_cleaned:
        return False
    
    # Skip formatting artifacts
    if any(marker in text_cleaned for marker in [
        '"**', '*', '[tagalog-', '[narrator', ':', '\n',
        'natural speed', 'slow speed', 'translated', 'arriving', 'checkout',
        '...', '--', '**'
    ]):
        return False
    
    # Skip phrases that start with quotes or other formatting
    if text_cleaned.startswith(('"', '*', '[', '**')):
        return False
    
    # Focus on authentic Filipino phrases that contain:
    # 1. Filipino politeness markers (po, opo)
    # 2. Common Filipino words
    # 3. Mixed Filipino-English travel phrases
    
    # Must contain Filipino elements or be essential travel phrases
    filipino_indicators = [
        'po', 'opo', 'ang', 'sa', 'na', 'ng', 'mga', 
        'magandang', 'salamat', 'kumusta', 'paano', 'saan', 'anong',
        'meron', 'wala', 'gusto', 'ayaw', 'balik', 'kailangan',
        'tubig', 'dalawa', 'ilan', 'oras', 'ganda', 'sarap',
        'naman', 'lang', 'talaga', 'malapit', 'malayo'
    ]
    
    text_lower = text_cleaned.lower()
    has_filipino = any(indicator in text_lower for indicator in filipino_indicators)
    
    # Essential English travel phrases in Filipino context
    essential_english = [
        'good morning', 'good evening', 'good afternoon',
        'thank you', 'excuse me', 'no problem', 'flight', 'airport',
        'hotel', 'check', 'next time', 'el nido', 'mango shake'
    ]
    
    is_essential_english = any(phrase in text_lower for phrase in essential_english)
    
    # Pure English support words that aren't worth learning
    english_filler = [
        'the menu', 'the food', 'the prawns', 'the bill', 'the waiter',
        'their meal', 'their food', 'their hotel', 'another couple',
        'many tourists', 'lunch crowd', 'perfect choice', 'nice table',
        'best restaurant', 'popular restaurant', 'limestone cliffs',
        'raw fish', 'super delicious', 'thirty minutes lang',
        'just water', 'just thirty minutes', 'what drinks', 'what time',
        'other specialties', 'other drinks', 'last meal', 'rush order'
    ]
    
    is_english_filler = any(phrase in text_lower for phrase in english_filler)
    
    # Accept if contains Filipino OR is essential English, but not English filler
    return (has_filipino or is_essential_english) and not is_english_filler

def final_cleanup_srs():
    """Final cleanup to keep only clean Filipino learning phrases."""
    srs_path = Path("data/srs_status.json")
    
    if not srs_path.exists():
        print("No SRS file found")
        return
    
    with open(srs_path, 'r', encoding='utf-8') as f:
        srs_data = json.load(f)
    
    collocations = srs_data.get('collocations', {})
    
    # Filter to clean phrases only
    clean_collocations = {}
    removed_count = 0
    
    for text, data in collocations.items():
        if is_clean_filipino_phrase(text):
            clean_collocations[text] = data
        else:
            removed_count += 1
            print(f"Removing: '{text}'")
    
    print(f"\n=== FINAL SRS CLEANUP RESULTS ===")
    print(f"Original count: {len(collocations)}")
    print(f"Clean phrases kept: {len(clean_collocations)}")
    print(f"Artifacts removed: {removed_count}")
    
    # Show what we're keeping
    print(f"\n=== CLEAN FILIPINO PHRASES (first 20) ===")
    for i, phrase in enumerate(sorted(clean_collocations.keys())[:20]):
        print(f"  {i+1:2d}. '{phrase}'")
    
    if len(clean_collocations) > 20:
        print(f"  ... and {len(clean_collocations) - 20} more")
    
    # Create backup of previous version
    backup_path = srs_path.with_suffix('.json.after_first_cleanup')
    import shutil
    shutil.copy2(srs_path, backup_path)
    
    # Save final clean version
    cleaned_data = {
        'current_day': srs_data.get('current_day', 1),
        'collocations': clean_collocations
    }
    
    with open(srs_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nFinal cleaned SRS saved to: {srs_path}")
    print(f"Previous version backed up to: {backup_path}")

if __name__ == "__main__":
    final_cleanup_srs()