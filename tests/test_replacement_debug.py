#!/usr/bin/env python3
"""
Debug the replacement logic specifically
"""

import sys
sys.path.append('.')

from utils.pimsleur_breakdown import generate_pimsleur_breakdown

def debug_replacement():
    sample_lines = [
        '[NARRATOR]: Day 14: Shopping - Day 6 Revisited',
        '',
        'Key Phrases:',
        '',
        '[TAGALOG-FEMALE-1]: meron po ba kayo',
        '[NARRATOR]: do you have',
        '[TAGALOG-FEMALE-1]: meron po ba kayo',  # line 6
        'kayo',                                  # line 7 - breakdown start
        'ba kayo',                               # line 8
        'po ba kayo',                            # line 9  
        'ron po ba kayo',                        # line 10
        'me',                                    # line 11
        'meron',                                 # line 12
        'meron po',                              # line 13
        'meron po ba',                           # line 14
        'meron po ba kayo',                      # line 15
        'meron po ba kayo',                      # line 16
        '',                                      # line 17
        '[NARRATOR]: Natural Speed'              # line 18
    ]
    
    print("Original lines:")
    for i, line in enumerate(sample_lines):
        print(f"{i:2d}: '{line}'")
    
    # Test replacement logic
    phrase = "meron po ba kayo"
    breakdown_start = 7  # After the phrase repetition
    breakdown_end = 17   # Before empty line
    
    print(f"\nReplacing lines {breakdown_start} to {breakdown_end-1}")
    print("Lines to remove:")
    for i in range(breakdown_start, breakdown_end):
        print(f"  {i}: '{sample_lines[i]}'")
    
    # Generate correct breakdown
    correct_breakdown = generate_pimsleur_breakdown(phrase)
    print(f"\nCorrect breakdown ({len(correct_breakdown)} steps):")
    for i, step in enumerate(correct_breakdown):
        print(f"  {i}: '{step}'")
    
    # Perform replacement
    corrected_lines = sample_lines[:]
    
    print(f"\nBefore replacement: {len(corrected_lines)} lines")
    
    # Remove old lines
    num_lines_to_remove = breakdown_end - breakdown_start
    print(f"Removing {num_lines_to_remove} lines starting at {breakdown_start}")
    
    for i in range(num_lines_to_remove):
        if breakdown_start < len(corrected_lines):
            removed = corrected_lines.pop(breakdown_start)
            print(f"  Removed line {breakdown_start}: '{removed}'")
    
    print(f"After removal: {len(corrected_lines)} lines")
    
    # Insert new lines
    print(f"Inserting {len(correct_breakdown)} breakdown lines at position {breakdown_start}")
    for j, breakdown_line in enumerate(correct_breakdown):
        corrected_lines.insert(breakdown_start + j, breakdown_line)
        print(f"  Inserted at {breakdown_start + j}: '{breakdown_line}'")
    
    print(f"After insertion: {len(corrected_lines)} lines")
    
    print("\nFinal result:")
    for i, line in enumerate(corrected_lines):
        marker = " <-- NEW" if breakdown_start <= i < breakdown_start + len(correct_breakdown) else ""
        print(f"{i:2d}: '{line}'{marker}")

if __name__ == "__main__":
    debug_replacement()