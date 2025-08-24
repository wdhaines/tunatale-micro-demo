#!/usr/bin/env python3

"""Debug script to test Pimsleur breakdown generation"""

import sys
sys.path.append('.')

from utils.pimsleur_breakdown import generate_pimsleur_breakdown

def test_phrases():
    """Test Pimsleur breakdown generation for Day 15 phrases"""
    
    test_phrases = [
        "salamat po",
        "kumusta po", 
        "magkano po",
        "puwede po ba",
        "sarap naman",
        "nakakamangha talaga"
    ]
    
    print("=== Pimsleur Breakdown Debug Test ===\n")
    
    for phrase in test_phrases:
        print(f"Testing phrase: '{phrase}'")
        try:
            breakdown = generate_pimsleur_breakdown(phrase)
            print(f"Generated breakdown ({len(breakdown)} steps):")
            for i, step in enumerate(breakdown, 1):
                print(f"  {i:2d}. {step}")
            print()
        except Exception as e:
            print(f"  ERROR: {e}")
            print()

if __name__ == "__main__":
    test_phrases()