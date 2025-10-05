#!/usr/bin/env python3
"""
Calculate and populate corpus frequencies for all SRS collocations.

This script analyzes the frequency of each collocation across the entire story corpus
and updates the SRS database with frequency counts and ready_for_translation status.
"""

import sys
from pathlib import Path
from collections import Counter
from srs_database import SRSDatabase
from story_collocation_extractor import StoryCollocationExtractor


def extract_filipino_dialogue(content: str) -> str:
    """Extract only Filipino dialogue from story content, excluding voice tags."""
    lines = content.split('\n')
    
    # Find Natural Speed section
    natural_start = -1
    slow_start = -1
    
    for i, line in enumerate(lines):
        if "[NARRATOR]: Natural Speed" in line:
            natural_start = i
        elif "[NARRATOR]: Slow Speed" in line:
            slow_start = i
            break
    
    if natural_start == -1:
        return ""
    
    # Extract content between Natural Speed and Slow Speed
    end_line = slow_start if slow_start != -1 else len(lines)
    natural_lines = lines[natural_start + 1:end_line]
    
    # Extract only Filipino dialogue (lines starting with [TAGALOG-*]:)
    filipino_sentences = []
    for line in natural_lines:
        line = line.strip()
        if line.startswith('[TAGALOG-') and ']:' in line:
            # Extract the Filipino text after the voice tag
            filipino_text = line.split(']: ', 1)[1].strip()
            if filipino_text:
                filipino_sentences.append(filipino_text)
    
    return ' '.join(filipino_sentences)


def main():
    """Calculate and populate corpus frequencies."""
    print("🔄 Calculating corpus frequencies for all SRS collocations...")
    
    # Initialize components
    srs_db = SRSDatabase("instance/data/srs/tunatale_srs.db")
    extractor = StoryCollocationExtractor()
    
    # Get all story files
    stories_dir = Path("instance/data/stories")
    if not stories_dir.exists():
        print("❌ Stories directory not found!")
        return 1
    
    story_files = list(stories_dir.glob("*.txt"))
    if not story_files:
        print("❌ No story files found!")
        return 1
    
    print(f"📖 Found {len(story_files)} story files")
    
    # Extract collocations from all stories to build frequency map
    print("🔍 Analyzing collocation frequencies across all stories...")
    all_collocations_counter = Counter()
    
    for i, story_file in enumerate(sorted(story_files), 1):
        print(f"  Processing story {i}/{len(story_files)}: {story_file.name}")
        
        try:
            with open(story_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            filipino_dialogue = extract_filipino_dialogue(content)
            if filipino_dialogue:
                collocations_dict = extractor.extract_collocations(filipino_dialogue)
                all_collocations_counter.update(collocations_dict)
        
        except Exception as e:
            print(f"    ⚠️ Error processing {story_file.name}: {e}")
            continue
    
    print(f"✅ Found {len(all_collocations_counter)} unique collocations in corpus")
    
    # Get current SRS collocations
    srs_collocations = srs_db.get_all_collocations()
    print(f"📊 Updating frequencies for {len(srs_collocations):,} SRS collocations...")
    
    # Update frequency for each SRS collocation
    updated_count = 0
    ready_for_translation_count = 0
    
    for collocation in srs_collocations:
        text = collocation['text']
        frequency = all_collocations_counter.get(text, 0)
        
        # Update frequency in database
        if srs_db.update_corpus_frequency(text, frequency):
            updated_count += 1
            if frequency >= 3:
                ready_for_translation_count += 1
    
    print(f"✅ Updated frequencies for {updated_count:,} collocations")
    print(f"🎯 {ready_for_translation_count:,} collocations are ready for translation (frequency ≥ 3)")
    
    # Show frequency distribution
    frequency_distribution = Counter()
    for collocation in srs_collocations:
        text = collocation['text']
        frequency = all_collocations_counter.get(text, 0)
        frequency_distribution[frequency] += 1
    
    print(f"\n📈 Frequency distribution:")
    for freq in sorted(frequency_distribution.keys(), reverse=True)[:10]:
        count = frequency_distribution[freq]
        print(f"  Frequency {freq}: {count:,} collocations")
    
    # Show some examples of frequent collocations
    frequent_examples = [(text, freq) for text, freq in all_collocations_counter.most_common(10) 
                        if any(srs_colloc['text'] == text for srs_colloc in srs_collocations)]
    
    if frequent_examples:
        print(f"\n🔝 Most frequent SRS collocations:")
        for text, frequency in frequent_examples:
            print(f"  {frequency:2d}x: {text}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())