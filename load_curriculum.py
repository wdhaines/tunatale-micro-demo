#!/usr/bin/env python3
"""
Script to load and display a curriculum from a JSON file.
"""
import json
from pathlib import Path
from curriculum_models import Curriculum, CurriculumDay

def load_custom_curriculum(path: Path) -> dict:
    """Load a curriculum from a JSON file with custom format."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Convert the custom format to our Curriculum model
    curriculum = {
        'learning_objective': data.get('learning_goal', 'No learning goal provided'),
        'target_language': data.get('target_language', 'English'),
        'learner_level': data.get('cefr_level', 'B1'),
        'presentation_length': 30,  # Default value
        'days': []
    }
    
    # Add days - handle both list and dict formats
    days_data = data.get('days', [])
    if isinstance(days_data, dict):
        days_data = days_data.values()
    
    for day_data in days_data:
        try:
            day_obj = {
                'day': day_data.get('day', 0),
                'title': day_data.get('title', ''),
                'focus': day_data.get('focus', ''),
                'collocations': day_data.get('collocations', []),
                'presentation_phrases': day_data.get('presentation_phrases', []),
                'learning_objective': day_data.get('learning_objective', '')
            }
            curriculum['days'].append(day_obj)
        except (ValueError, AttributeError) as e:
            print(f"Warning: Could not process {day_num}: {e}")
    
    return curriculum

def main():
    # Path to the test curriculum file
    test_file = Path("test.json")
    
    if not test_file.exists():
        print(f"Error: File not found: {test_file}")
        print("Please make sure the file exists in the current directory.")
        return
    
    try:
        # Load the curriculum in custom format
        curriculum_data = load_custom_curriculum(test_file)
        
        # Display basic information
        print(f"Curriculum: {curriculum_data['learning_objective']}")
        print(f"Target Language: {curriculum_data['target_language']}")
        print(f"CEFR Level: {curriculum_data['learner_level']}")
        print(f"Number of days: {len(curriculum_data['days'])}")
        
        # Display each day's information
        for day in sorted(curriculum_data['days'], key=lambda x: x['day']):
            print(f"\nDay {day['day']}: {day['title']}")
            if day['focus']:
                print(f"Focus: {day['focus']}")
            if day['learning_objective']:
                print(f"Learning Objective: {day['learning_objective']}")
            if day['collocations']:
                print("Collocations:", ", ".join(day['collocations']))
            
    except FileNotFoundError:
        print(f"Error: File not found: {test_file}")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file: {test_file}")
    except Exception as e:
        print(f"Error loading curriculum: {e}")

if __name__ == "__main__":
    main()
