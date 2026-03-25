#!/usr/bin/env python3
"""
Restore previously translated collocations to the SRS database.

This script finds collocations that have translations in the Enhanced SRS Database
but are missing from the main SRS database, and adds them back.
"""

import sys
from pathlib import Path
from srs_database import SRSDatabase
from enhanced_srs_database import EnhancedSRSDatabase


def main():
    """Restore previously translated collocations to SRS database."""
    print("🔄 Restoring previously translated collocations to SRS database...")
    
    # Initialize databases
    srs_db = SRSDatabase("instance/data/srs/tunatale_srs.db")
    enhanced_db = EnhancedSRSDatabase()
    
    # Get current SRS collocations
    current_collocations = srs_db.get_all_collocations()
    current_texts = {colloc['text'] for colloc in current_collocations}
    print(f"📊 Current SRS collocations: {len(current_texts):,}")
    
    # Get all existing translations
    all_translations = enhanced_db.get_translation_pairs(active_only=True)
    translated_texts = {trans.filipino for trans in all_translations}
    print(f"📚 Total existing translations: {len(translated_texts):,}")
    
    # Find missing translated collocations
    missing_translations = translated_texts - current_texts
    print(f"🔍 Found {len(missing_translations):,} translated collocations missing from SRS")
    
    if not missing_translations:
        print("✅ All translated collocations are already in SRS database!")
        return 0
    
    # Add missing translated collocations back to SRS
    added_count = 0
    
    print(f"📝 Adding missing translated collocations to SRS database...")
    for collocation_text in missing_translations:
        try:
            # Add with default SRS values since we're just tracking it for future frequency counting
            srs_db.add_collocation(
                text=collocation_text,
                first_seen_day=1,  # Default to day 1 since we don't know original day
                last_seen_day=1,
                appearances=[1],
                review_count=0,
                next_review_day=1,
                stability=1.0
            )
            added_count += 1
        except Exception as e:
            print(f"  ⚠️ Error adding '{collocation_text}': {e}")
            continue
    
    print(f"✅ Successfully added {added_count:,} missing translated collocations")
    
    # Final statistics
    final_collocations = srs_db.get_all_collocations()
    final_count = len(final_collocations)
    
    print(f"\n📊 Final SRS Database:")
    print(f"  Total collocations: {final_count:,}")
    print(f"  Previously in SRS: {len(current_texts):,}")
    print(f"  Restored translations: {added_count:,}")
    
    # Show word distribution
    by_words = {}
    for colloc in final_collocations:
        word_count = len(colloc['text'].split())
        by_words[word_count] = by_words.get(word_count, 0) + 1
    
    print(f"\n📈 Word length distribution:")
    for word_count in sorted(by_words.keys()):
        count = by_words[word_count]
        percentage = (count / final_count) * 100
        print(f"  {word_count} word(s): {count:,} items ({percentage:.1f}%)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())