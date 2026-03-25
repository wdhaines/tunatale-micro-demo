#!/usr/bin/env python3
"""
Script to populate EnhancedSRSDatabase with translation pairs from all story files.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict

from enhanced_srs_database import EnhancedSRSDatabase
from story_collocation_extractor import StoryCollocationExtractor


def get_all_story_files() -> List[Path]:
    """Find all story files in the data directory."""
    story_dirs = [
        Path("instance/data/stories"),
        Path("data/stories")
    ]
    
    story_files = []
    for story_dir in story_dirs:
        if story_dir.exists():
            story_files.extend(story_dir.glob("*.txt"))
    
    return sorted(story_files)


def extract_day_number_from_filename(filename: str) -> int:
    """Extract day number from story filename."""
    # Handle patterns like: story_day19_*.txt, story_day1_*.txt, demo-0.0.3-day-8.txt
    import re
    patterns = [
        r'day(\d+)',  # day19, day1, etc.
        r'day-(\d+)', # day-8, day-19, etc.
        r'(\d+)'      # fallback for any number
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            return int(match.group(1))
    
    return 0  # fallback


def populate_translation_pairs(enhanced_db: EnhancedSRSDatabase, 
                             extractor: StoryCollocationExtractor,
                             story_files: List[Path],
                             verbose: bool = True) -> Dict[str, int]:
    """Populate enhanced database with translation pairs from story files."""
    
    stats = {
        'files_processed': 0,
        'total_pairs_found': 0,
        'pairs_added': 0,
        'pairs_updated': 0,
        'errors': 0
    }
    
    for story_file in story_files:
        if verbose:
            print(f"Processing {story_file.name}...")
        
        try:
            day_num = extract_day_number_from_filename(story_file.name)
            
            # Extract translation pairs from the story
            extraction = extractor.extract_from_day_number(day_num)
            
            if not extraction or extraction.total_unique_phrases == 0:
                if verbose:
                    print(f"  No translation pairs found in {story_file.name}")
                continue
            
            # Add Key Phrases pairs
            for pair in extraction.key_phrase_pairs:
                tagalog = pair['tagalog']
                english = pair['english']
                
                # Add to enhanced database
                was_new = enhanced_db.add_translation_pair(
                    english_text=english,
                    filipino_text=tagalog,
                    confidence=1.0,  # Key phrases are high confidence
                    source_day=day_num,
                    extraction_method='story_key_phrases'
                )
                
                if was_new:
                    stats['pairs_added'] += 1
                else:
                    stats['pairs_updated'] += 1
                
                stats['total_pairs_found'] += 1
            
            # Add Translated dialogue pairs
            for pair in extraction.translated_pairs:
                tagalog = pair['tagalog']
                english = pair['english']
                
                # Add to enhanced database
                was_new = enhanced_db.add_translation_pair(
                    english_text=english,
                    filipino_text=tagalog,
                    confidence=0.9,  # Dialogue pairs are slightly lower confidence
                    source_day=day_num,
                    extraction_method='story_dialogue'
                )
                
                if was_new:
                    stats['pairs_added'] += 1
                else:
                    stats['pairs_updated'] += 1
                
                stats['total_pairs_found'] += 1
            
            stats['files_processed'] += 1
            
            if verbose:
                key_count = len(extraction.key_phrase_pairs)
                dialogue_count = len(extraction.translated_pairs)
                print(f"  ✓ Added {key_count} key phrases + {dialogue_count} dialogue pairs from day {day_num}")
        
        except Exception as e:
            stats['errors'] += 1
            if verbose:
                print(f"  ✗ Error processing {story_file.name}: {e}")
            continue
    
    return stats


def main():
    """Main function to populate enhanced SRS database with translation pairs."""
    print("🚀 Populating EnhancedSRSDatabase with story translation pairs...")
    
    # Initialize components
    enhanced_db = EnhancedSRSDatabase()
    extractor = StoryCollocationExtractor()
    
    # Get all story files
    story_files = get_all_story_files()
    
    if not story_files:
        print("❌ No story files found!")
        print("   Expected directories: instance/data/stories/ or data/stories/")
        return 1
    
    print(f"📚 Found {len(story_files)} story files")
    
    # Check current state
    current_stats = enhanced_db.get_stats()
    print(f"📊 Current EnhancedSRSDatabase state:")
    print(f"   Translation pairs: {current_stats['active_translation_pairs']}")
    print(f"   Avg confidence: {current_stats['average_translation_confidence']:.3f}")
    print()
    
    # Populate with translation pairs
    stats = populate_translation_pairs(enhanced_db, extractor, story_files, verbose=True)
    
    # Show results
    print("\n✅ Population Complete!")
    print(f"   Files processed: {stats['files_processed']}")
    print(f"   Translation pairs found: {stats['total_pairs_found']}")
    print(f"   New pairs added: {stats['pairs_added']}")
    print(f"   Existing pairs updated: {stats['pairs_updated']}")
    print(f"   Errors: {stats['errors']}")
    
    # Show updated database stats
    updated_stats = enhanced_db.get_stats()
    print(f"\n📈 Updated EnhancedSRSDatabase state:")
    print(f"   Translation pairs: {updated_stats['active_translation_pairs']} (+{updated_stats['active_translation_pairs'] - current_stats['active_translation_pairs']})")
    print(f"   Avg confidence: {updated_stats['average_translation_confidence']:.3f}")
    
    # Test a few Day 19 lookups
    print("\n🧪 Testing Day 19 translation lookups:")
    day19_phrases = ['salamat sa lahat', 'paalam po', 'babalik po ako', 'ingat po kayo', 'miss ko na kayo']
    for phrase in day19_phrases:
        translation = enhanced_db.find_english_equivalent(phrase)
        status = "✓" if translation else "✗"
        print(f"   {status} \"{phrase}\" → \"{translation}\"")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())