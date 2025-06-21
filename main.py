import os
import sys
import json
import argparse
from pathlib import Path
from curriculum_generator import CurriculumGenerator
from collocation_extractor import CollocationExtractor
from content_generator import ContentGenerator, StoryParams, CEFRLevel
from config import CURRICULUM_PATH, COLLOCATIONS_PATH, DATA_DIR, DEFAULT_STORY_LENGTH

def setup_argparse():
    # Custom argument type for CEFR level that's case-insensitive
    def cefr_level(level):
        try:
            return CEFRLevel[level.upper()].value
        except (KeyError, AttributeError):
            raise argparse.ArgumentTypeError(
                f"Invalid CEFR level: {level}. Must be one of: "
                f"{', '.join(lvl.value for lvl in CEFRLevel)}")
    
    # Custom argument type for positive integers
    def positive_int(value):
        try:
            ivalue = int(value)
            if ivalue <= 0:
                raise ValueError()
            return ivalue
        except ValueError:
            raise argparse.ArgumentTypeError(f"{value} must be a positive integer")

    # Main parser setup
    parser = argparse.ArgumentParser(
        description='TunaTale Micro-Demo 0.1',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Subparsers for different commands
    subparsers = parser.add_subparsers(
        dest='command',
        required=True,
        help='Available commands (use <command> -h for help)'
    )
    
    # Generate curriculum command
    gen_parser = subparsers.add_parser(
        'generate',
        help='Generate a new language learning curriculum',
        description='Generate a new language learning curriculum',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    gen_parser.add_argument(
        'goal',
        type=str,
        help='Learning goal (e.g., "Ordering food in a restaurant")'
    )
    
    # Extract collocations command
    extract_parser = subparsers.add_parser(
        'extract',
        help='Extract collocations from curriculum',
        description='Extract collocations from the generated curriculum',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Generate story command
    story_parser = subparsers.add_parser(
        'story',
        help='Generate a story for language learning',
        description='Generate a story for language learning',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    story_parser.add_argument(
        'objective',
        type=str,
        help='Learning objective for the story (e.g., "ordering food")'
    )
    story_parser.add_argument(
        '--language',
        type=str,
        default='English',
        help='Target language for the story'
    )
    story_parser.add_argument(
        '--level',
        type=cefr_level,
        default='B1',
        help=f'CEFR level ({ "/".join(lvl.value for lvl in CEFRLevel) })'
    )
    story_parser.add_argument(
        '--phase',
        type=positive_int,
        choices=range(1, 6),
        default=1,
        help='Learning phase (1-5)'
    )
    story_parser.add_argument(
        '--length',
        type=positive_int,
        default=DEFAULT_STORY_LENGTH,
        help=f'Target word count (default: {DEFAULT_STORY_LENGTH})'
    )
    story_parser.add_argument(
        '--previous',
        type=str,
        help='Path to previous story file for context'
    )
    story_parser.add_argument(
        '--output',
        type=str,
        help='Output file path for the generated story (default: print to stdout)'
    )
    
    # View command
    view_parser = subparsers.add_parser(
        'view',
        help='View generated content',
        description='View generated curriculum, collocations, or stories',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    view_parser.add_argument(
        'what',
        choices=['curriculum', 'collocations', 'story'],
        help='Type of content to view'
    )
    view_parser.add_argument(
        '--day',
        type=positive_int,
        choices=range(1, 6),
        help='Day number (1-5) to view'
    )
    
    return parser.parse_args()

def validate_positive_int(value):
    """Validate that a value is a positive integer."""
    try:
        ivalue = int(value)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError(f"{value} is not a positive integer")
        return ivalue
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid integer")

def main():
    try:
        args = setup_argparse()
    except argparse.ArgumentError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    
    if args.command == 'generate':
        # Generate curriculum
        print(f"Generating curriculum for: {args.goal}")
        generator = CurriculumGenerator()
        curriculum = generator.generate_curriculum(args.goal)
        if curriculum:
            print("\nCurriculum generated successfully!")
            print("Run 'python main.py view curriculum' to see it.")
    
    elif args.command == 'extract':
        # Extract collocations
        print("Extracting collocations from curriculum...")
        extractor = CollocationExtractor()
        collocations = extractor.extract_from_curriculum()
        print(f"\nExtracted {len(collocations)} collocations.")
        print("Top collocations:")
        for i, (colloc, count) in enumerate(list(collocations.items())[:10], 1):
            print(f"{i}. {colloc} (x{count})")
    
    elif args.command == 'story':
        # Generate a story
        generator = ContentGenerator()
        
        # Validate required parameters
        if not all([args.objective, args.language, args.level, args.phase]):
            parser.parse_args([args.command, '--help'])
            return 0
            
        # Validate length is positive (should be handled by positive_int type, but double-check)
        if args.length <= 0:
            print("Error: Length must be a positive number", file=sys.stderr)
            return 2
            
        try:
            # Set up story parameters
            params = StoryParams(
                learning_objective=args.objective,
                language=args.language,
                cefr_level=args.level.upper(),  # Ensure uppercase for CEFR level
                phase=args.phase,
                length=args.length
            )
            
            # Load previous story if provided
            previous_story = ""
            if args.previous:
                try:
                    with open(args.previous, 'r', encoding='utf-8') as f:
                        previous_story = f.read()
                except Exception as e:
                    print(f"Warning: Could not read previous story: {e}", file=sys.stderr)
            
            # Generate the story
            story = generator.generate_story(params, previous_story)
            if not story:
                print("Error: Failed to generate story", file=sys.stderr)
                return 1
                
            # Save to output file if specified, otherwise print to stdout
            if args.output:
                try:
                    output_path = Path(args.output)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(story)
                    print(f"Story saved to: {output_path}")
                except IOError as e:
                    print(f"Error: Failed to save story to {args.output}: {e}", file=sys.stderr)
                    return 1
            else:
                print("\nGenerated story:")
                print("-" * 50)
                print(story)
                print("-" * 50)
                
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    elif args.command == 'view':
        # View generated content
        if args.what == 'curriculum':
            if not CURRICULUM_PATH.exists():
                print("No curriculum found. Generate one with 'python main.py generate <goal>'")
                return
                
            with open(CURRICULUM_PATH, 'r') as f:
                curriculum = json.load(f)
                print(f"\nLearning Goal: {curriculum['learning_goal']}\n")
                print(curriculum['content'])
        
        elif args.what == 'collocations':
            if not COLLOCATIONS_PATH.exists():
                print("No collocations found. Extract them with 'python main.py extract'")
                return
                
            with open(COLLOCATIONS_PATH, 'r') as f:
                collocations = json.load(f)
                print("\nTop Collocations:")
                for i, (colloc, count) in enumerate(list(collocations.items())[:20], 1):
                    print(f"{i}. {colloc} (x{count})")
        
        elif args.what == 'story':
            if not args.day:
                print("Please specify a day with --day")
                return
                
            story_path = DATA_DIR / 'generated_content' / f'day{args.day}_story.txt'
            if not story_path.exists():
                print(f"No story found for Day {args.day}")
                return
                
            with open(story_path, 'r') as f:
                print(f"\nDay {args.day} Story:\n")
                print(f.read())
    
    else:
        print("Please specify a command. Use --help for usage information.")

if __name__ == "__main__":
    main()
