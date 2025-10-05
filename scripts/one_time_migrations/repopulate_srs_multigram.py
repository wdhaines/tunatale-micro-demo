#!/usr/bin/env python3
"""
Re-populate SRS database with multi-granularity collocations.

This script re-extracts collocations from existing stories using the updated
StoryCollocationExtractor that now extracts single words, 2-word phrases, 
and 3-word phrases, then rebuilds the SRS database.
"""

import sys
from pathlib import Path
from srs_database import SRSDatabase
from story_collocation_extractor import StoryCollocationExtractor


def main():
    """Re-populate SRS database with multi-granularity collocations."""
    print("🔄 Re-populating SRS database with multi-granularity collocations...")
    
    # Initialize components - use SRSDatabase directly
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
    
    # Clear existing collocations (optional - comment out to keep existing)
    print("🗑️ Clearing existing SRS collocations...")
    existing_collocations = srs_db.get_all_collocations()
    for collocation in existing_collocations:
        srs_db.delete_collocation(collocation['text'])
    print(f"  Removed {len(existing_collocations)} existing collocations")
    
    # Process each story
    total_collocations_added = 0
    
    for i, story_file in enumerate(sorted(story_files), 1):
        print(f"📄 Processing {i}/{len(story_files)}: {story_file.name}")
        
        try:
            # Read story content
            with open(story_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract Filipino dialogue from natural speed section
            filipino_dialogue = extract_filipino_dialogue(content)
            if not filipino_dialogue:
                print(f"  ⚠️ No Filipino dialogue found, skipping...")
                continue
            
            # Extract multi-granularity collocations from Filipino text only
            collocations_dict = extractor.extract_collocations(filipino_dialogue)
            collocations_list = list(collocations_dict.keys())
            
            if collocations_list:
                # Add each collocation individually to SRS database with comprehensive quality filtering
                added_count = 0
                for collocation in collocations_list:
                    # Apply comprehensive quality filtering from SRSTracker logic
                    if _is_valid_collocation(collocation.strip()):
                        srs_db.add_collocation(
                            text=collocation.strip(),
                            first_seen_day=i,
                            last_seen_day=i,
                            appearances=[i],
                            review_count=0,
                            next_review_day=i,
                            stability=1.0
                        )
                        added_count += 1
                
                total_collocations_added += added_count
                print(f"  ✅ Added {added_count} valid collocations (from {len(collocations_list)} extracted)")
            else:
                print(f"  ⚠️ No collocations extracted")
                
        except Exception as e:
            print(f"  ❌ Error processing {story_file.name}: {e}")
            continue
    
    # Final statistics
    print(f"\n✅ SRS Re-population Complete!")
    print(f"  Total collocations added: {total_collocations_added:,}")
    
    # Get updated SRS stats
    all_collocations = srs_db.get_all_collocations()
    print(f"  Total SRS collocations: {len(all_collocations):,}")
    
    # Show word length distribution
    by_word_count = {}
    for colloc in all_collocations:
        word_count = len(colloc['text'].split())
        by_word_count[word_count] = by_word_count.get(word_count, 0) + 1
    
    print(f"\n📊 Word length distribution:")
    for word_count in sorted(by_word_count.keys()):
        count = by_word_count[word_count]
        percentage = (count / len(all_collocations)) * 100
        print(f"  {word_count} word(s): {count:,} items ({percentage:.1f}%)")
    
    return 0


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


def _is_valid_collocation(text: str) -> bool:
    """
    Validate collocation quality using the same logic as SRSTracker.
    
    Returns True if the collocation is valid for SRS tracking.
    """
    text_lower = text.lower().strip()
    
    # Skip empty or too short
    if len(text_lower) <= 1:
        return False
    
    # Voice tags and technical markers
    voice_tags = [
        'tagalog-female', 'tagalog-male', 'narrator', 
        '[narrator', ']', '[tagalog', 'female-1', 'female-2', 'male-1'
    ]
    if any(tag in text_lower for tag in voice_tags):
        return False
    
    # Known problematic phrases and patterns
    problematic_phrases = {
        'sip her mango shake', 'el nido maria', 'bring menus', 'ask pa pong specialty',
        'next time', 'flight', 'two-thirty po', 'pa pong specialty'
    }
    if text_lower in problematic_phrases:
        return False
    
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
    english_count = sum(1 for word in words if word in english_words)
    if len(words) > 0 and (english_count / len(words)) > 0.5:
        return False
    
    # Skip very short fragments
    if len(text_lower) < 3:
        return False
    
    return True


if __name__ == "__main__":
    sys.exit(main())