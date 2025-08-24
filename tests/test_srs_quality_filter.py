#!/usr/bin/env python3
"""Test SRS quality filtering."""

import sys
sys.path.append('.')

from srs_tracker import SRSTracker

def test_quality_filtering():
    """Test that quality filtering prevents bad collocations."""
    
    # Create a test SRS tracker
    tracker = SRSTracker(data_dir=".", filename="test_srs.json")
    
    # Test cases: bad collocations that should be filtered out
    bad_collocations = [
        "sip her mango shake",      # Mostly English
        "el nido maria",            # English + name
        "bring menus",              # All English
        "tagalog-female-1",         # Voice tag
        "[narrator",                # Technical marker
        "next time",                # All English
        "flight",                   # Single English word
        "two-thirty po",            # Mixed English-Filipino
        "kami po kami",             # Repetitive
        "po kami mi",               # Fragment
        "a",                        # Single letter
        "",                         # Empty
    ]
    
    # Test cases: good collocations that should be kept
    good_collocations = [
        "pwede po ba",              # Pure Filipino
        "magkano po ito",           # Filipino with common structure
        "salamat po sa inyo",       # Proper Filipino phrase
        "ano pong oras",            # Filipino question
        "kailangan po namin",       # Filipino need expression
        "paumanhin po",             # Filipino politeness
    ]
    
    print("Testing SRS quality filtering...")
    print(f"Testing {len(bad_collocations)} bad collocations (should be rejected)")
    print(f"Testing {len(good_collocations)} good collocations (should be accepted)")
    
    # Add all collocations
    all_collocations = bad_collocations + good_collocations
    tracker.add_collocations(all_collocations, day=1)
    
    # Check what was actually added
    added_count = len(tracker.collocations)
    expected_count = len(good_collocations)
    
    print(f"\nResults:")
    print(f"Expected to add: {expected_count} good collocations")
    print(f"Actually added: {added_count} collocations")
    
    print(f"\nAdded collocations:")
    for text in tracker.collocations.keys():
        print(f"  ✓ '{text}'")
    
    print(f"\nFiltered out:")
    for bad_col in bad_collocations:
        if bad_col not in tracker.collocations:
            print(f"  🗑️  '{bad_col}'")
    
    # Check success rate
    success_rate = (added_count / expected_count) * 100 if expected_count > 0 else 0
    filter_rate = ((len(all_collocations) - added_count) / len(all_collocations)) * 100
    
    print(f"\nFilter effectiveness:")
    print(f"  Good collocations kept: {added_count}/{expected_count} ({success_rate:.1f}%)")
    print(f"  Total filtered out: {len(all_collocations) - added_count}/{len(all_collocations)} ({filter_rate:.1f}%)")
    
    if added_count == expected_count:
        print("✅ Quality filtering working correctly!")
        return True
    else:
        print("❌ Quality filtering needs adjustment")
        return False

if __name__ == '__main__':
    test_quality_filtering()