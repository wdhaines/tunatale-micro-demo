#!/usr/bin/env python3
"""
Convert El Nido curriculum from micro-demo-0.0 format to micro-demo-0.1 format.

This script reads the demo-0.0.3-full-week.txt file and converts it into
the JSON curriculum format expected by micro-demo-0.1.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

def extract_vocabulary_from_text(text: str) -> List[Dict[str, str]]:
    """Extract vocabulary items from a text section."""
    vocabulary = []
    
    # Pattern to match [TAGALOG-FEMALE-1]: phrase followed by [NARRATOR]: translation
    pattern = r'\[TAGALOG-FEMALE-1\]:\s*(.+?)\n\[NARRATOR\]:\s*(.+?)(?=\n|$)'
    
    matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
    
    for tagalog_phrase, english_translation in matches:
        # Clean up the phrases
        tagalog_phrase = tagalog_phrase.strip()
        english_translation = english_translation.strip()
        
        # Skip if either is empty or contains unwanted content
        if not tagalog_phrase or not english_translation:
            continue
        if '[' in tagalog_phrase or '[' in english_translation:
            continue
            
        vocabulary.append({
            "word": tagalog_phrase,
            "definition": english_translation
        })
    
    return vocabulary

def extract_collocations(vocabulary: List[Dict[str, str]]) -> List[str]:
    """Extract collocations from vocabulary items."""
    collocations = []
    
    for item in vocabulary:
        phrase = item["word"]
        # Add phrases that are more than one word as collocations
        if len(phrase.split()) > 1:
            collocations.append(phrase)
    
    # Limit to reasonable number of collocations per day
    return collocations[:5]

def parse_el_nido_curriculum(file_path: Path) -> Dict[str, Any]:
    """Parse the El Nido curriculum file and extract structured data."""
    
    if not file_path.exists():
        raise FileNotFoundError(f"Curriculum file not found: {file_path}")
    
    content = file_path.read_text(encoding='utf-8')
    
    # Split content by day
    day_sections = re.split(r'\[NARRATOR\]:\s*Day\s+(\d+):', content)
    
    curriculum_data = {
        "learning_goal": "Learn conversational Filipino for travel in El Nido",
        "target_language": "Filipino/Tagalog", 
        "cefr_level": "A2",
        "days": {},
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "transcript_used": False,
            "format": "converted_from_demo_0_0",
            "version": "1.0",
            "original_source": "demo-0.0.3-full-week.txt"
        }
    }
    
    # Process each day section
    for i in range(1, len(day_sections), 2):
        if i + 1 >= len(day_sections):
            break
            
        day_number = day_sections[i].strip()
        day_content = day_sections[i + 1]
        
        print(f"Processing Day {day_number}...")
        
        # Extract title from the day content
        title_match = re.search(r'([^\n]+)', day_content)
        title = f"Day {day_number}: El Nido Travel Experience"
        if title_match:
            title = f"Day {day_number}: {title_match.group(1).strip()}"
        
        # Extract vocabulary from key phrases section
        vocabulary = extract_vocabulary_from_text(day_content)
        
        # Generate collocations from vocabulary
        collocations = extract_collocations(vocabulary)
        
        # Create activities based on the content
        activities = [
            f"Practice key Filipino phrases for Day {day_number}",
            "Listen and repeat pronunciation exercises", 
            "Role-play travel scenarios in Filipino",
            "Review vocabulary with spaced repetition"
        ]
        
        # Create day entry
        day_key = f"day_{day_number}"
        curriculum_data["days"][day_key] = {
            "title": title,
            "content": f"Day {day_number} focuses on practical Filipino phrases for travelers in El Nido, covering essential conversational skills.",
            "focus": f"Travel Filipino - Day {day_number}",
            "collocations": collocations,
            "vocabulary": vocabulary,
            "activities": activities
        }
        
        print(f"  - Extracted {len(vocabulary)} vocabulary items")
        print(f"  - Generated {len(collocations)} collocations")
    
    return curriculum_data

def save_curriculum(curriculum_data: Dict[str, Any], output_path: Path) -> None:
    """Save the curriculum data to JSON file."""
    
    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(curriculum_data, f, indent=2, ensure_ascii=False)
    
    print(f"Curriculum saved to: {output_path}")

def main():
    """Main conversion function."""
    
    # File paths
    source_file = Path("../micro-demo-0.0/tagalog/demo-0.0.3-full-week.txt")
    output_file = Path("instance/data/curricula/curriculum_processed.json")
    
    print("Converting El Nido curriculum from micro-demo-0.0 to micro-demo-0.1 format...")
    print(f"Source: {source_file}")
    print(f"Output: {output_file}")
    print()
    
    try:
        # Parse the source file
        curriculum_data = parse_el_nido_curriculum(source_file)
        
        # Save to output format
        save_curriculum(curriculum_data, output_file)
        
        print()
        print("✅ Conversion completed successfully!")
        print(f"📚 Curriculum contains {len(curriculum_data['days'])} days")
        print(f"🎯 Learning goal: {curriculum_data['learning_goal']}")
        print(f"📊 CEFR level: {curriculum_data['cefr_level']}")
        print()
        print("You can now use:")
        print("  python main.py view curriculum")
        print("  python main.py generate-day 1")
        
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())