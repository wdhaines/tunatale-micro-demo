#!/usr/bin/env python3
"""
Debug script for content post-processor
"""

import sys
sys.path.append('.')

from utils.content_post_processor import extract_key_phrases_sections, fix_pimsleur_breakdowns
from utils.pimsleur_breakdown import generate_pimsleur_breakdown

sample_content = """[NARRATOR]: Day 14: Shopping - Day 6 Revisited

Key Phrases:

[TAGALOG-FEMALE-1]: meron po ba kayo
[NARRATOR]: do you have
[TAGALOG-FEMALE-1]: meron po ba kayo
kayo
ba kayo
po ba kayo
ron po ba kayo
me
meron
meron po
meron po ba
meron po ba kayo
meron po ba kayo

[NARRATOR]: Natural Speed"""

print("=== Debugging Content Processing ===")

# Test phrase extraction
print("\n1. Extract key phrases:")
phrases = extract_key_phrases_sections(sample_content)
for i, (phrase, start, end, breakdown) in enumerate(phrases):
    print(f"Phrase {i+1}: '{phrase}' (lines {start}-{end})")
    print(f"  Breakdown: {breakdown}")

# Test algorithmic generation
print("\n2. Algorithmic breakdown:")
if phrases:
    phrase = phrases[0][0]
    correct_breakdown = generate_pimsleur_breakdown(phrase)
    print(f"For '{phrase}':")
    for i, step in enumerate(correct_breakdown):
        print(f"  {i+1:2d}. {step}")

# Test line-by-line processing
print("\n3. Line analysis:")
lines = sample_content.split('\n')
for i, line in enumerate(lines):
    print(f"{i:2d}: '{line}'")

print("\n4. Detailed fix processing:")
# Step through the fix process manually
corrected = fix_pimsleur_breakdowns(sample_content)
print("Result:")
print(corrected)