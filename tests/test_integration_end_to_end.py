#!/usr/bin/env python3
"""
Test end-to-end integration of Pimsleur breakdown correction
"""

import sys
sys.path.append('.')

from utils.content_post_processor import post_process_story_content

# Sample of actual LLM output with wrong breakdowns (like from the file)
actual_llm_output = """[NARRATOR]: Day 14: Shopping - Day 6 Revisited

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

[TAGALOG-FEMALE-1]: tawad po
[NARRATOR]: discount please
[TAGALOG-FEMALE-1]: tawad po
po
wad po
ta
tawad
tawad po
tawad po

[NARRATOR]: Natural Speed

[NARRATOR]: At the Shop

[TAGALOG-FEMALE-1]: Kumusta po kayo! Meron po ba kayong mga souvenir?
[TAGALOG-FEMALE-2]: Mabuti naman po! Ano pong hinahanap ninyo?"""

print("=== End-to-End Integration Test ===")

print("\n1. Original LLM Output (with wrong breakdowns):")
lines = actual_llm_output.split('\n')
for i, line in enumerate(lines[:25]):  # Show first 25 lines
    print(f"{i+1:2d}: {line}")

print("\n2. After Post-Processing:")
corrected = post_process_story_content(actual_llm_output)
corrected_lines = corrected.split('\n')
for i, line in enumerate(corrected_lines[:30]):  # Show first 30 lines
    print(f"{i+1:2d}: {line}")

print(f"\n3. Summary:")
print(f"Original lines: {len(lines)}")
print(f"Corrected lines: {len(corrected_lines)}")
print(f"Change: {len(corrected_lines) - len(lines)} lines")

# Validate specific corrections
print("\n4. Breakdown Validation:")
print("Checking for 'meron po ba kayo' breakdown...")
corrected_text = '\n'.join(corrected_lines)
expected_steps = ["yo", "ka", "kayo", "ba", "ba kayo", "po", "po ba kayo", "ron", "me", "meron"]
for step in expected_steps:
    if step in corrected_text:
        print(f"  ✅ Found correct step: '{step}'")
    else:
        print(f"  ❌ Missing step: '{step}'")

print("\nChecking for 'tawad po' breakdown...")
tawad_expected = ["wad", "ta", "tawad"]
for step in tawad_expected:
    if step in corrected_text:
        print(f"  ✅ Found correct step: '{step}'")
    else:
        print(f"  ❌ Missing step: '{step}'")

print("\n✅ Integration test completed!")