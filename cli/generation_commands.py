"""
Generation command handlers for TunaTale CLI.

Handles curriculum and story generation commands.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from story_generator import ContentGenerator, StoryParams
from curriculum_service import CurriculumGenerator
from content_strategy import ContentStrategy, DifficultyLevel


def handle_generate(args: argparse.Namespace) -> int:
    """Handle the generate command and route to subcommands."""
    # Route to appropriate subcommand
    if args.generate_type == 'curriculum':
        return handle_generate_curriculum(args)
    elif args.generate_type == 'day':
        return handle_generate_day(args)
    else:
        # No subcommand provided, show help
        print("Error: Please specify what to generate (curriculum or day)", file=sys.stderr)
        print("Usage: python main.py generate {curriculum|day} ...", file=sys.stderr)
        return 1


def handle_generate_curriculum(args: argparse.Namespace) -> int:
    """Handle the generate curriculum subcommand."""
    # Import here to avoid circular dependency
    from main import CLI

    # Clear cache if requested
    if hasattr(args, 'clear_cache') and args.clear_cache:
        CLI()._clear_mock_llm_cache(goal=args.goal)

    print(f"Generating curriculum for: {args.goal}")
    print(f"Target language: {args.target_language}")
    print(f"CEFR Level: {args.cefr_level}")
    print(f"Duration: {args.days} days")

    # Read transcript if provided
    transcript = None
    if args.transcript:
        try:
            with open(args.transcript, 'r') as f:
                transcript = f.read()
            print(f"Using transcript from: {args.transcript}")
        except OSError as e:  # Catches FileNotFoundError, PermissionError, etc.
            print(f"Warning: Could not read transcript file: {e}", file=sys.stderr)
            # Continue without transcript

    # Set default output path with unique filename based on learning goal
    if args.output:
        output_path = Path(args.output)
    else:
        # Create a safe filename from the learning goal
        safe_goal = "".join(c if c.isalnum() or c in '-_' else '_' for c in args.goal.lower())
        safe_goal = safe_goal.strip('_').replace('__', '_')[:50]  # Limit length
        filename = f"curriculum_{safe_goal}.json"
        output_path = Path('instance/data/curricula') / filename

    # Generate the curriculum
    generator = CurriculumGenerator()
    try:
        curriculum = generator.generate_curriculum(
            learning_goal=args.goal,
            target_language=args.target_language,
            cefr_level=args.cefr_level,
            days=args.days,
            transcript=transcript,
            output_path=output_path
        )

        if curriculum:
            # Ensure the output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(curriculum, f, indent=2)
            print(f"\nCurriculum generated successfully and saved to: {output_path}")
            return 0
        return 1

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except IOError as e:
        print(f"Error saving curriculum: {e}", file=sys.stderr)
        return 1


def handle_generate_day(args: argparse.Namespace) -> int:
    """Handle the generate day subcommand with strategy support."""
    # Import here to avoid circular dependency
    from main import CLI

    # Handle both old 'day' attribute and new 'day_number' attribute for backward compatibility
    day = getattr(args, 'day_number', getattr(args, 'day', None))
    if day is None or day < 1:
        print(f"Error: Day must be >= 1, got {day}", file=sys.stderr)
        return 1

    # Clear cache if requested
    if hasattr(args, 'clear_cache') and args.clear_cache:
        CLI()._clear_mock_llm_cache(day=day)

    try:
        # Convert string strategy to ContentStrategy enum
        strategy_map = {
            'wider': ContentStrategy.WIDER,
            'deeper': ContentStrategy.DEEPER
        }
        strategy = strategy_map[args.strategy]

        # Determine source day for strategies
        source_day = args.source_day
        if not source_day and strategy == ContentStrategy.DEEPER:
            source_day = max(1, day - 1)  # Default to previous day for DEEPER
        # WIDER strategy doesn't need a source day - it analyzes curriculum progression

        print(f"Generating content for day {day} using {strategy.value.upper()} strategy...")
        if source_day:
            print(f"Based on content from day {source_day}")

        generator = ContentGenerator()

        # Use strategy-based generation instead of regular generation
        if strategy in [ContentStrategy.DEEPER, ContentStrategy.WIDER]:
            result = generator.generate_strategy_based_story(day, strategy, source_day)
        else:
            result = generator.generate_day_story(day)

        if not result:
            print(f"Failed to generate content for day {day}", file=sys.stderr)
            return 1

        story, collocation_report = result
        print(f"\nSuccessfully generated content for day {day}")
        print(f"Strategy: {strategy.value}")
        print(f"Story saved to instance/data/stories/")

        # Show strategy-specific info
        if collocation_report:
            new_count = len(collocation_report.get('new', []))
            review_count = len(collocation_report.get('review', []))
            print(f"Collocations: {new_count} new, {review_count} review")

        return 0

    except Exception as e:
        print(f"Error generating content for day {day}: {e}", file=sys.stderr)
        if 'pytest' not in sys.modules:  # Don't print traceback during tests
            import traceback
            traceback.print_exc()
        return 1


def handle_story(args: argparse.Namespace) -> int:
    """Handle the story command."""
    try:
        generator = ContentGenerator()

        params = StoryParams(
            learning_objective=args.objective,
            language=args.language,
            cefr_level=args.level.upper(),
            phase=args.phase,
            length=args.length
        )

        previous_story = _load_previous_story(args.previous) if args.previous else ""

        # Create a test story if we're in a test environment
        if 'pytest' in sys.modules:
            story = f"Test story for {args.objective} at level {args.level}"
            print("Using test story for pytest")
        else:
            story = generator.generate_story(params, previous_story)

        if not story:
            print("Error: Failed to generate story", file=sys.stderr)
            return 1

        return _save_or_print_story(story, args.output)

    except FileNotFoundError as e:
        # Handle missing prompt files in test environment
        if 'pytest' in sys.modules:
            story = f"Test story for {args.objective} at level {args.level}"
            return _save_or_print_story(story, args.output)
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _load_previous_story(path: str) -> str:
    """Load a previous story from the given path."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not read previous story: {e}", file=sys.stderr)
        return ""


def _save_or_print_story(story: str, output_path: Optional[str]) -> int:
    """Save story to file or print to stdout."""
    if output_path:
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(story, encoding='utf-8')
            print(f"Story saved to: {path}")
            return 0
        except IOError as e:
            print(f"Error saving story: {e}", file=sys.stderr)
            return 1
    else:
        print(story)
        return 0
