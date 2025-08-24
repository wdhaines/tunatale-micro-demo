#!/usr/bin/env python3

"""Debug script to test pattern matching in post-processing algorithm"""

import sys
sys.path.append('.')

from utils.content_post_processor import fix_pimsleur_breakdowns
import re

def debug_pattern_matching():
    """Debug pattern matching with actual Day 15 content"""
    
    # Sample from actual Day 15 content that should be detected and fixed
    day15_sample = """Key Phrases:

[TAGALOG-FEMALE-1]: salamat po
[NARRATOR]: thank you
[TAGALOG-FEMALE-1]: salamat po
[TAGALOG-FEMALE-1]: sa-la-mat po
[TAGALOG-FEMALE-1]: sa
[TAGALOG-FEMALE-1]: sa-la
[TAGALOG-FEMALE-1]: sa-la-mat


[TAGALOG-FEMALE-1]: kumusta po
[NARRATOR]: how are you
[TAGALOG-FEMALE-1]: kumusta po
[TAGALOG-FEMALE-1]: ku-mus-ta po
[TAGALOG-FEMALE-1]: ku
[TAGALOG-FEMALE-1]: ku-mus
[TAGALOG-FEMALE-1]: ku-mus-ta

[NARRATOR]: Natural Speed"""

    print("=== Pattern Matching Debug ===\n")
    print("INPUT CONTENT:")
    print(day15_sample)
    print("\n" + "="*50 + "\n")
    
    # Test the regex patterns used in the algorithm
    lines = day15_sample.split('\n')
    in_key_phrases = False
    
    print("LINE-BY-LINE ANALYSIS:")
    for i, line in enumerate(lines):
        line = line.strip()
        print(f"Line {i:2d}: '{line}'")
        
        # Check Key Phrases section detection
        if line == "Key Phrases:":
            in_key_phrases = True
            print("  → KEY PHRASES SECTION DETECTED")
            continue
            
        if in_key_phrases and line.startswith("[NARRATOR]: Natural Speed"):
            in_key_phrases = False
            print("  → LEAVING KEY PHRASES SECTION")
            continue
        
        if in_key_phrases:
            # Test Tagalog phrase pattern
            tagalog_match = re.match(r'\[TAGALOG-(?:FEMALE|MALE)-\d+\]:\s*(.+)', line)
            if tagalog_match:
                phrase = tagalog_match.group(1).strip()
                print(f"  → TAGALOG PHRASE FOUND: '{phrase}'")
                
            # Test narrator pattern
            narrator_match = re.match(r'\[NARRATOR\]:\s*(.+)', line)
            if narrator_match:
                translation = narrator_match.group(1).strip()
                print(f"  → NARRATOR TRANSLATION: '{translation}'")
    
    print("\n" + "="*50 + "\n")
    print("APPLYING POST-PROCESSING:")
    result = fix_pimsleur_breakdowns(day15_sample)
    print(result)
    
    print("\n" + "="*50 + "\n")
    print("COMPARISON:")
    if result == day15_sample:
        print("❌ NO CHANGES MADE - Pattern matching or replacement failed")
    else:
        print("✅ CHANGES MADE - Pattern matching worked")
        print(f"Original length: {len(day15_sample)} chars")
        print(f"Result length: {len(result)} chars")

if __name__ == "__main__":
    debug_pattern_matching()