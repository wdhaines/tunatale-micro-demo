#!/usr/bin/env python3
"""Test curriculum format consistency across the system."""

import json
from pathlib import Path
from curriculum_models import Curriculum

def test_curriculum_format():
    """Test that the current curriculum can be loaded with the Curriculum dataclass."""
    
    curriculum_path = Path("instance/data/curriculum_processed.json")
    
    if not curriculum_path.exists():
        print("❌ Curriculum file not found")
        return False
    
    try:
        # Test loading with standard JSON
        print("=== Testing JSON Loading ===")
        with open(curriculum_path, 'r') as f:
            data = json.load(f)
        
        print(f"✓ JSON loaded successfully")
        print(f"Top-level keys: {list(data.keys())}")
        print(f"Days type: {type(data.get('days', None))}")
        print(f"Number of days: {len(data.get('days', []))}")
        
        if data.get('days'):
            first_day = data['days'][0]
            print(f"First day keys: {list(first_day.keys())}")
        
        # Test loading with Curriculum dataclass
        print(f"\n=== Testing Curriculum Dataclass Loading ===")
        curriculum = Curriculum.from_dict(data)
        
        print(f"✓ Curriculum loaded successfully")
        print(f"Learning objective: {curriculum.learning_objective}")
        print(f"Target language: {curriculum.target_language}")
        print(f"Learner level: {curriculum.learner_level}")
        print(f"Number of days: {len(curriculum.days)}")
        
        if curriculum.days:
            first_day = curriculum.days[0]
            print(f"First day: {first_day.day} - {first_day.title}")
            print(f"First day focus: {first_day.focus}")
            print(f"First day collocations: {first_day.collocations}")
        
        # Test get_day method
        day_1 = curriculum.get_day(1)
        if day_1:
            print(f"✓ get_day(1) works: {day_1.title}")
        
        day_7 = curriculum.get_day(7)
        if day_7:
            print(f"✓ get_day(7) works: {day_7.title}")
        
        print(f"\n=== SUCCESS: Curriculum format is consistent ===")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_curriculum_format()
    print(f"\nResult: {'✅ PASS' if success else '❌ FAIL'}")