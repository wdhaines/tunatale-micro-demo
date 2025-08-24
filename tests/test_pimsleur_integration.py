#!/usr/bin/env python3
"""
Quick test script to validate Pimsleur breakdown integration
"""

from utils.pimsleur_breakdown import generate_pimsleur_breakdown

def test_pimsleur_examples():
    """Test against known working examples"""
    
    # Test case 1: meron po ba kayo  
    expected_meron = [
        "meron po ba kayo",
        "yo", "ka", "kayo",
        "ba", "ba kayo", 
        "po", "po ba kayo",
        "ron", "me", "meron",
        "meron po ba kayo",
        "meron po ba kayo"
    ]
    
    actual_meron = generate_pimsleur_breakdown("meron po ba kayo")
    
    print("=== Test: meron po ba kayo ===")
    print("Expected steps:", len(expected_meron))
    print("Actual steps:  ", len(actual_meron))
    
    for i, (expected, actual) in enumerate(zip(expected_meron, actual_meron)):
        match = "✓" if expected == actual else "✗"
        print(f"{i+1:2d}. {match} Expected: '{expected}' | Actual: '{actual}'")
    
    if expected_meron == actual_meron:
        print("✅ PASS: Perfect match!")
    else:
        print("❌ FAIL: Mismatch detected")
    
    print()
    
    # Test case 2: tawad po
    expected_tawad = [
        "tawad po",
        "po", "wad", "ta", "tawad",
        "tawad po", "tawad po"
    ]
    
    actual_tawad = generate_pimsleur_breakdown("tawad po")
    
    print("=== Test: tawad po ===")
    print("Expected steps:", len(expected_tawad))
    print("Actual steps:  ", len(actual_tawad))
    
    for i, (expected, actual) in enumerate(zip(expected_tawad, actual_tawad)):
        match = "✓" if expected == actual else "✗"
        print(f"{i+1:2d}. {match} Expected: '{expected}' | Actual: '{actual}'")
    
    if expected_tawad == actual_tawad:
        print("✅ PASS: Perfect match!")
    else:
        print("❌ FAIL: Mismatch detected")

if __name__ == "__main__":
    test_pimsleur_examples()