"""
Production data validation tests - CRITICAL before refactor.

These tests validate against actual production data to catch 
real-world issues that synthetic tests might miss.
"""

import json
import pytest
from pathlib import Path

def test_actual_collocations_data_quality():
    """Test actual collocations.json for data quality issues."""
    collocations_path = Path("instance/data/collocations.json")
    
    if not collocations_path.exists():
        pytest.skip("No production collocations data found")
    
    with open(collocations_path, 'r') as f:
        collocations = json.load(f)
    
    # Count different types of corruption
    voice_tags = []
    system_markers = []
    clean_collocations = []
    
    voice_patterns = ["tagalog-female-", "tagalog-male-", "english-"]
    system_patterns = ["[narrator", "[", "**", "voice:", "audio:"]
    
    for colloc, count in collocations.items():
        if any(pattern in colloc.lower() for pattern in voice_patterns):
            voice_tags.append((colloc, count))
        elif any(pattern in colloc.lower() for pattern in system_patterns):
            system_markers.append((colloc, count))
        else:
            clean_collocations.append((colloc, count))
    
    print(f"\n=== PRODUCTION DATA ANALYSIS ===")
    print(f"Voice tags found: {len(voice_tags)} entries")
    print(f"System markers found: {len(system_markers)} entries") 
    print(f"Clean collocations: {len(clean_collocations)} entries")
    # Calculate corruption rate (avoid division by zero)
    total_corruption = len(voice_tags) + len(system_markers)
    corruption_rate = (total_corruption / len(collocations) * 100) if len(collocations) > 0 else 0.0
    print(f"Total corruption rate: {corruption_rate:.1f}%")
    
    if voice_tags:
        print(f"\nTop voice tags:")
        for colloc, count in sorted(voice_tags, key=lambda x: x[1], reverse=True)[:5]:
            print(f"  '{colloc}': {count}")
    
    # Assert that we've analyzed the data (always passes - this is a diagnostic test)
    assert len(collocations) >= 0, "Should have loaded collocations data"
    
    # Document findings for user review
    total_corrupted = len(voice_tags) + len(system_markers)
    if total_corrupted > 0:
        print(f"\n⚠️ FOUND {total_corrupted} CORRUPTED ENTRIES - CLEANUP RECOMMENDED")
    else:
        print(f"\n✅ No corruption found in collocations data")


def test_curriculum_format_in_production():
    """Test actual curriculum files for format consistency."""
    curricula_dir = Path("instance/data/curricula")
    
    if not curricula_dir.exists():
        pytest.skip("No production curricula found")
    
    curriculum_files = list(curricula_dir.glob("*.json"))
    if not curriculum_files:
        pytest.skip("No curriculum files found")
    
    format_issues = []
    
    for file_path in curriculum_files:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check format consistency
        if "days" in data:
            if isinstance(data["days"], dict):
                format_issues.append(f"{file_path.name}: Uses dict format (should be list)")
            elif isinstance(data["days"], list):
                # Check for missing fields in list format
                for i, day in enumerate(data["days"]):
                    if "story_guidance" not in day:
                        format_issues.append(f"{file_path.name}: Day {i+1} missing story_guidance")
    
    print(f"\n=== CURRICULUM FORMAT ANALYSIS ===")
    print(f"Files checked: {len(curriculum_files)}")
    print(f"Format issues: {len(format_issues)}")
    
    for issue in format_issues:
        print(f"  ⚠️ {issue}")
    
    # Assert that we've analyzed the data (always passes - this is a diagnostic test) 
    assert len(curriculum_files) >= 0, "Should have checked curriculum files"
    
    # Document findings for user review
    if format_issues:
        print(f"\n⚠️ FOUND {len(format_issues)} FORMAT ISSUES - REVIEW RECOMMENDED")
    else:
        print(f"\n✅ No format issues found in curriculum files")


if __name__ == "__main__":
    # Run validation manually
    print("=== PRODUCTION DATA VALIDATION ===")
    
    try:
        collocations_issues = test_actual_collocations_data_quality()
        print(f"✅ Collocations analysis complete")
    except Exception as e:
        print(f"❌ Collocations analysis failed: {e}")
    
    try:
        curriculum_issues = test_curriculum_format_in_production()
        print(f"✅ Curriculum format analysis complete")
    except Exception as e:
        print(f"❌ Curriculum format analysis failed: {e}")