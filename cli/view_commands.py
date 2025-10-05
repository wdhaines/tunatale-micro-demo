"""
View command handlers for TunaTale CLI.

Handles displaying curricula, collocations, and stories.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import config


def handle_view(args: argparse.Namespace) -> int:
    """Handle the view command."""
    try:
        if args.what == 'curriculum':
            return view_curriculum()
        elif args.what == 'collocations':
            return view_collocations()
        elif args.what == 'story':
            return view_story(args.day)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


def find_curriculum_file() -> Optional[Path]:
    """Find the most recent curriculum file."""
    curricula_dir = config.CURRICULA_DIR
    if not curricula_dir.exists():
        return None

    # Look for curriculum files
    curriculum_files = list(curricula_dir.glob('curriculum*.json'))
    if not curriculum_files:
        return None

    # Return the most recent one (by modification time)
    return max(curriculum_files, key=lambda p: p.stat().st_mtime)


def view_curriculum() -> int:
    """Display the generated curriculum."""
    curriculum_path = find_curriculum_file()
    if not curriculum_path:
        print("No curriculum found. Generate one with 'python main.py generate <goal>'")
        return 1

    with open(curriculum_path, 'r') as f:
        curriculum = json.load(f)
        learning_objective = curriculum.get('learning_objective', curriculum.get('learning_goal', 'Not specified'))
        print(f"\nLearning Objective: {learning_objective}\n")

        # Handle both old and new curriculum formats
        if 'content' in curriculum:
            print(curriculum['content'])
        elif 'days' in curriculum:
            print(f"Target Language: {curriculum.get('target_language', 'Not specified')}")
            print(f"Learner Level: {curriculum.get('learner_level', 'Not specified')}")
            print(f"\nCurriculum contains {len(curriculum['days'])} days")
            for day in curriculum['days']:
                # Check if title already starts with "Day N:" to avoid duplication
                title = day['title']
                if title.startswith(f"Day {day['day']}:"):
                    print(title)
                else:
                    print(f"Day {day['day']}: {title}")
        else:
            print("Curriculum format not recognized")
    return 0


def view_collocations() -> int:
    """Display the extracted collocations."""
    if not config.COLLOCATIONS_PATH.exists():
        print("No collocations found. Extract them with 'python main.py extract'")
        return 1

    with open(config.COLLOCATIONS_PATH, 'r') as f:
        collocations = json.load(f)
        print("\nTop Collocations:")
        for i, (colloc, count) in enumerate(list(collocations.items())[:20], 1):
            print(f"{i}. {colloc} (x{count})")
    return 0


def view_story(day: Optional[int]) -> int:
    """Display a generated story."""
    if not day:
        print("Please specify a day with --day")
        return 1

    story_path = Path(config.STORIES_DIR) / f'day{day}_story.txt'
    if not story_path.exists():
        print(f"No story found for Day {day}")
        return 1

    with open(story_path, 'r') as f:
        print(f"\nDay {day} Story:\n")
        print(f.read())
    return 0
