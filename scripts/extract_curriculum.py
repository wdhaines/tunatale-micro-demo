#!/usr/bin/env python3
"""
Script to extract curriculum information from the 30-day carnivorous plants curriculum file.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, TypedDict
from dataclasses import dataclass


@dataclass
class WeekInfo:
    """Data class to store weekly curriculum information."""
    week_num: int
    title: str
    focus: str
    key_collocations: List[str]
    presentation_skills: List[str]
    days: List[int]


@dataclass
class DayStory:
    """Data class to store daily story information."""
    day_num: int
    target_collocations: List[str]
    title: str
    content: str
    word_count: int


def parse_curriculum_file(file_path: Path) -> tuple[Dict[int, WeekInfo], Dict[int, DayStory]]:
    """Parse the curriculum file and extract weekly and daily information.
    
    Args:
        file_path: Path to the curriculum file
        
    Returns:
        Tuple of (weeks, days) where:
        - weeks is a dict mapping week number to WeekInfo
        - days is a dict mapping day number to DayStory
    """
    content = file_path.read_text(encoding='utf-8')
    
    # Parse weekly information
    week_pattern = r'### (Week \d+ \(Days (\d+-\d+)\): ([^\n]+))\n\*\*Focus\*\*: ([^\n]+)\n\*\*Key collocations\*\*: ([^\n]+)\n\*\*Presentation skills\*\*: ([^\n]+)'
    week_matches = re.findall(week_pattern, content)
    
    weeks = {}
    for match in week_matches:
        full_title, days_range, week_title, focus, collocations, skills = match
        week_num = int(re.search(r'Week (\d+)', full_title).group(1))
        start_day, end_day = map(int, days_range.split('-'))
        
        weeks[week_num] = WeekInfo(
            week_num=week_num,
            title=week_title.strip(),
            focus=focus.strip(),
            key_collocations=[c.strip(' "') for c in collocations.split(', ')],
            presentation_skills=[s.strip(' "') for s in skills.split(', ')],
            days=list(range(start_day, end_day + 1))
        )
    
    # Parse daily stories
    day_pattern = r'## Day (\d+) Story\n\*\*Target collocations\*\*: ([^\n]+)\n\n\*\*([^\*]+)\*\*\n\n([\s\S]*?)\n\*\*Word count\*\*: (\d+)'
    day_matches = re.findall(day_pattern, content)
    
    days = {}
    for match in day_matches:
        day_num, collocations, title, story, word_count = match
        day_num = int(day_num)
        
        days[day_num] = DayStory(
            day_num=day_num,
            target_collocations=[c.strip(' "') for c in collocations.split(' / ')],
            title=title.strip(),
            content=story.strip(),
            word_count=int(word_count)
        )
    
    return weeks, days


def print_curriculum_summary(weeks: Dict[int, WeekInfo], days: Dict[int, DayStory]):
    """Print a summary of the extracted curriculum information."""
    print(f"Extracted {len(weeks)} weeks and {len(days)} days of curriculum.")
    
    print("\nWeekly Overview:")
    for week_num, week in sorted(weeks.items()):
        print(f"\nWeek {week_num}: {week.title}")
        print(f"  Days: {week.days[0]}-{week.days[-1]}")
        print(f"  Focus: {week.focus}")
        print(f"  Key collocations: {', '.join(week.key_collocations)}")
        print(f"  Presentation skills: {', '.join(week.presentation_skills)}")
    
    print("\nDaily Stories:")
    for day_num, day in sorted(days.items()):
        print(f"\nDay {day_num}: {day.title}")
        print(f"  Target collocations: {', '.join(day.target_collocations)}")
        print(f"  Word count: {day.word_count}")


def main():
    # Path to the curriculum file
    curriculum_path = Path(__file__).parent.parent / 'prompts' / '30day_carnivorous_plants_curriculum.txt'
    
    if not curriculum_path.exists():
        print(f"Error: File not found: {curriculum_path}")
        return
    
    try:
        weeks, days = parse_curriculum_file(curriculum_path)
        print_curriculum_summary(weeks, days)
        
        # Save the extracted data to JSON for later use
        import json
        output = {
            'weeks': {
                week_num: {
                    'week_num': info.week_num,
                    'title': info.title,
                    'focus': info.focus,
                    'key_collocations': info.key_collocations,
                    'presentation_skills': info.presentation_skills,
                    'days': info.days
                } for week_num, info in weeks.items()
            },
            'days': {
                day_num: {
                    'day_num': day.day_num,
                    'title': day.title,
                    'target_collocations': day.target_collocations,
                    'word_count': day.word_count,
                    'content': day.content[:100] + '...'  # Just a preview
                } for day_num, day in days.items()
            }
        }
        
        output_path = curriculum_path.parent / 'curriculum_data.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        print(f"\nExtracted data saved to: {output_path}")
        
    except Exception as e:
        print(f"Error parsing curriculum: {e}")
        raise


if __name__ == "__main__":
    main()
