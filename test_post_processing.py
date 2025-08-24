#!/usr/bin/env python3

"""Debug script to test post-processing of Key Phrases"""

import sys
sys.path.append('.')

from utils.content_post_processor import post_process_story_content

def test_post_processing():
    """Test post-processing with Day 15 style Key Phrases"""
    
    # Sample content that mimics the Day 15 Key Phrases structure
    sample_content = """[NARRATOR]: Day 15: Sunset Photography Adventure

Key Phrases:

[TAGALOG-FEMALE-1]: salamat po
[NARRATOR]: thank you (formal)
[TAGALOG-FEMALE-1]: salamat po
[TAGALOG-FEMALE-1]: sa-la-mat po
[TAGALOG-FEMALE-1]: sa-la-mat
[TAGALOG-FEMALE-1]: sa-la
[TAGALOG-FEMALE-1]: sa

[TAGALOG-MALE-1]: kumusta po
[NARRATOR]: how are you (formal)
[TAGALOG-MALE-1]: kumusta po
[TAGALOG-MALE-1]: ku-mus-ta po
[TAGALOG-MALE-1]: ku-mus-ta
[TAGALOG-MALE-1]: ku-mus
[TAGALOG-MALE-1]: ku

[NARRATOR]: Natural Speed

[NARRATOR]: Late afternoon at the resort reception"""
    
    print("=== Post-Processing Debug Test ===\n")
    print("ORIGINAL CONTENT:")
    print(sample_content)
    print("\n" + "="*50 + "\n")
    
    print("PROCESSED CONTENT:")
    processed_content = post_process_story_content(sample_content)
    print(processed_content)
    
    print("\n" + "="*50 + "\n")
    print("CHANGES MADE:")
    if processed_content != sample_content:
        print("✅ Content was modified by post-processing")
        print(f"Original length: {len(sample_content)} chars")
        print(f"Processed length: {len(processed_content)} chars")
    else:
        print("❌ No changes made by post-processing")

if __name__ == "__main__":
    test_post_processing()