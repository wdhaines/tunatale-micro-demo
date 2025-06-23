#!/usr/bin/env python3
"""
Script to convert the extracted curriculum data to the format expected by ContentGenerator.
"""

import json
from pathlib import Path
from typing import Dict, Any, List

def convert_curriculum(input_path: Path, output_path: Path) -> None:
    """Convert the curriculum data to the format expected by ContentGenerator.
    
    Args:
        input_path: Path to the extracted curriculum JSON file
        output_path: Path to save the converted curriculum JSON file
    """
    # Load the extracted curriculum data
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Initialize the output curriculum structure
    curriculum = {
        "language": "English",
        "cefr_level": "A2",
        "phases": {}
    }
    
    # Convert days to phases
    days = data.get('days', {})
    for day_num, day_data in days.items():
        phase_num = int(day_num)
        curriculum["phases"][f"phase{phase_num}"] = {
            "learning_objective": day_data.get("title", f"Day {day_num} Learning"),
            "cefr_level": "A2",
            "story_length": day_data.get("word_count", 250),
            "new_vocabulary": day_data.get("target_collocations", []),
            "recycled_vocabulary": [],
            "content": day_data.get("content", "")
        }
    
    # Save the converted curriculum
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(curriculum, f, indent=2)
    
    print(f"Converted curriculum saved to: {output_path}")
    print(f"Converted {len(days)} days of curriculum.")

if __name__ == "__main__":
    # Define input and output paths
    base_dir = Path(__file__).parent.parent
    input_path = base_dir / "prompts" / "curriculum_data.json"
    output_path = base_dir / "data" / "curriculum.json"
    
    # Run the conversion
    convert_curriculum(input_path, output_path)
