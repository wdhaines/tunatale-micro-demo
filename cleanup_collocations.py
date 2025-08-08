#!/usr/bin/env python3
"""
Phase 1.1: Fix Data Quality Issues - Collocation Cleanup
Clean up curriculum collocations by separating actual phrases from embedded syllable breakdowns.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any

def is_syllable_breakdown(text: str) -> bool:
    """
    Determine if a text string is a syllable breakdown rather than a proper collocation.
    
    Syllable breakdowns contain:
    - Embedded newlines (\n) - this is the primary indicator
    - Single syllables (1-2 chars) as standalone entries
    """
    # Contains newlines (clear indicator of syllable breakdown)
    if '\n' in text:
        return True
    
    # Very short standalone entries (1-2 characters) are likely syllables
    if len(text.strip()) <= 2:
        return True
        
    # Everything else is considered a valid collocation
    return False

def clean_collocation_entry(text: str) -> List[str]:
    """
    Clean a collocation entry, extracting actual phrases and discarding syllable data.
    
    For entries like: "ito po\npo\nito\nto\ni\nito\nito po\nito po"
    Extract the meaningful phrase: "ito po"
    """
    if not is_syllable_breakdown(text):
        return [text.strip()]
    
    # Split by newlines and find the longest meaningful phrase
    parts = [part.strip() for part in text.split('\n') if part.strip()]
    
    # Filter out single characters and very short syllables
    meaningful_parts = [part for part in parts if len(part) > 2 and ' ' in part]
    
    if meaningful_parts:
        # Return the longest phrase (likely the complete collocation)
        longest = max(meaningful_parts, key=len)
        return [longest]
    
    # Fallback: look for repeated complete phrases
    phrase_counts = {}
    for part in parts:
        if len(part) > 2:
            phrase_counts[part] = phrase_counts.get(part, 0) + 1
    
    if phrase_counts:
        # Return the most frequent non-trivial phrase
        best_phrase = max(phrase_counts.keys(), key=lambda x: (phrase_counts[x], len(x)))
        return [best_phrase]
    
    # Last resort: return the original if we can't parse it
    return [text.strip()]

def clean_curriculum_collocations(curriculum_path: Path) -> Dict[str, Any]:
    """
    Clean all collocation data in the curriculum file.
    """
    print(f"Loading curriculum from: {curriculum_path}")
    
    with open(curriculum_path, 'r', encoding='utf-8') as f:
        curriculum = json.load(f)
    
    stats = {
        'days_processed': 0,
        'collocations_cleaned': 0,
        'presentation_phrases_cleaned': 0,
        'broken_entries_found': 0
    }
    
    for day_data in curriculum['days']:
        day_num = day_data['day']
        stats['days_processed'] += 1
        
        print(f"\nProcessing Day {day_num}: {day_data['title']}")
        
        # Clean collocations
        if 'collocations' in day_data:
            original_collocations = day_data['collocations'][:]
            cleaned_collocations = []
            
            for colloc in original_collocations:
                if is_syllable_breakdown(colloc):
                    stats['broken_entries_found'] += 1
                    print(f"  ⚠️  Found broken collocation: {repr(colloc[:50])}...")
                    
                cleaned_phrases = clean_collocation_entry(colloc)
                cleaned_collocations.extend(cleaned_phrases)
                stats['collocations_cleaned'] += len(cleaned_phrases)
            
            # Remove duplicates while preserving order
            seen = set()
            day_data['collocations'] = [
                colloc for colloc in cleaned_collocations 
                if not (colloc in seen or seen.add(colloc))
            ]
            
            print(f"  ✅ Collocations: {len(original_collocations)} → {len(day_data['collocations'])}")
        
        # Clean presentation_phrases
        if 'presentation_phrases' in day_data:
            original_phrases = day_data['presentation_phrases'][:]
            cleaned_phrases = []
            
            for phrase in original_phrases:
                if is_syllable_breakdown(phrase):
                    stats['broken_entries_found'] += 1
                    
                cleaned = clean_collocation_entry(phrase)
                cleaned_phrases.extend(cleaned)
                stats['presentation_phrases_cleaned'] += len(cleaned)
            
            # Remove duplicates
            seen = set()
            day_data['presentation_phrases'] = [
                phrase for phrase in cleaned_phrases 
                if not (phrase in seen or seen.add(phrase))
            ]
            
            print(f"  ✅ Presentation phrases: {len(original_phrases)} → {len(day_data['presentation_phrases'])}")
    
    return curriculum, stats

def validate_cleaned_data(curriculum: Dict[str, Any]) -> bool:
    """
    Validate that the cleaned curriculum data is properly formatted.
    """
    print("\n🔍 Validating cleaned curriculum...")
    
    issues = []
    
    for day_data in curriculum['days']:
        day_num = day_data['day']
        
        # Check for remaining broken collocations
        for colloc in day_data.get('collocations', []):
            if is_syllable_breakdown(colloc):
                issues.append(f"Day {day_num}: Still has broken collocation: {repr(colloc)}")
        
        # Check for remaining broken presentation phrases  
        for phrase in day_data.get('presentation_phrases', []):
            if is_syllable_breakdown(phrase):
                issues.append(f"Day {day_num}: Still has broken presentation phrase: {repr(phrase)}")
        
        # Ensure we have some collocations
        if not day_data.get('collocations'):
            issues.append(f"Day {day_num}: No collocations remaining after cleanup")
    
    if issues:
        print("❌ Validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ Validation passed - all data appears clean")
        return True

def backup_original_file(file_path: Path) -> Path:
    """Create a timestamped backup of the original file."""
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.parent / f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
    
    print(f"📋 Creating backup: {backup_path}")
    
    with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
        dst.write(src.read())
    
    return backup_path

def main():
    """Main cleanup process."""
    curriculum_path = Path("instance/data/curriculum_processed.json")
    
    if not curriculum_path.exists():
        print(f"❌ Curriculum file not found: {curriculum_path}")
        return 1
    
    print("🧹 TunaTale Collocation Data Cleanup")
    print("=" * 50)
    
    # Create backup
    backup_path = backup_original_file(curriculum_path)
    
    try:
        # Clean the curriculum
        cleaned_curriculum, stats = clean_curriculum_collocations(curriculum_path)
        
        # Validate results
        if not validate_cleaned_data(cleaned_curriculum):
            print("❌ Validation failed - not saving changes")
            return 1
        
        # Save cleaned curriculum
        print(f"\n💾 Saving cleaned curriculum to: {curriculum_path}")
        with open(curriculum_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_curriculum, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print("\n📊 Cleanup Summary:")
        print(f"  Days processed: {stats['days_processed']}")
        print(f"  Broken entries found: {stats['broken_entries_found']}")
        print(f"  Collocations cleaned: {stats['collocations_cleaned']}")
        print(f"  Presentation phrases cleaned: {stats['presentation_phrases_cleaned']}")
        print(f"  Backup saved to: {backup_path}")
        
        print("\n✅ Collocation cleanup completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        print(f"Original file preserved as: {backup_path}")
        return 1

if __name__ == "__main__":
    exit(main())