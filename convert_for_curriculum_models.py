#!/usr/bin/env python3
"""
Convert the El Nido curriculum to match curriculum_models.py format.

This script takes the converted curriculum and reformats it to match
the CurriculumDay and Curriculum dataclass structure.
"""

import json
from pathlib import Path

def convert_to_curriculum_models_format():
    """Convert the El Nido curriculum to match curriculum_models format."""
    
    # Read the converted curriculum
    input_path = Path("instance/data/curricula/curriculum_processed.json")
    output_path = Path("instance/data/curriculum_processed.json")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        old_format = json.load(f)
    
    # Extract vocabulary items for presentation phrases
    def extract_presentation_phrases(vocabulary_list):
        """Extract key phrases from vocabulary for presentation."""
        phrases = []
        for item in vocabulary_list:
            word = item.get("word", "")
            # Skip items that look like system artifacts
            if ("\\n" not in word and 
                not word.startswith("Natural Speed") and
                len(word.split()) <= 4):  # Keep shorter phrases
                phrases.append(word)
        return phrases[:8]  # Limit to 8 phrases per day
    
    # Create new format
    new_format = {
        "learning_objective": old_format.get("learning_goal", "Learn Filipino for travel"),
        "target_language": old_format.get("target_language", "Filipino/Tagalog"),
        "learner_level": old_format.get("cefr_level", "A2"),
        "presentation_length": 15,  # Default 15 minutes
        "days": [],
        "metadata": old_format.get("metadata", {})
    }
    
    # Convert each day
    days_data = old_format.get("days", {})
    for day_key in sorted(days_data.keys()):
        day_data = days_data[day_key]
        day_number = int(day_key.split("_")[1])
        
        # Extract presentation phrases from vocabulary
        vocabulary = day_data.get("vocabulary", [])
        presentation_phrases = extract_presentation_phrases(vocabulary)
        
        # Create curriculum day
        curriculum_day = {
            "day": day_number,
            "title": day_data.get("title", f"Day {day_number}"),
            "focus": day_data.get("focus", f"Travel Filipino - Day {day_number}"),
            "collocations": day_data.get("collocations", [])[:5],  # Limit to 5
            "presentation_phrases": presentation_phrases,
            "learning_objective": f"Master practical Filipino phrases for Day {day_number} travel scenarios",
            "story_guidance": f"Create an engaging story that incorporates the Day {day_number} vocabulary and collocations in realistic El Nido travel contexts."
        }
        
        new_format["days"].append(curriculum_day)
    
    # Save the new format
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_format, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Converted curriculum to curriculum_models format")
    print(f"📁 Saved to: {output_path}")
    print(f"📚 Days: {len(new_format['days'])}")
    
    # Show sample of first day
    if new_format["days"]:
        first_day = new_format["days"][0]
        print(f"\n📖 Sample - Day 1:")
        print(f"   Title: {first_day['title']}")
        print(f"   Focus: {first_day['focus']}")
        print(f"   Collocations: {len(first_day['collocations'])}")
        print(f"   Phrases: {len(first_day['presentation_phrases'])}")

if __name__ == "__main__":
    convert_to_curriculum_models_format()