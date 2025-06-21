import os
import json
import argparse
from curriculum_generator import CurriculumGenerator
from collocation_extractor import CollocationExtractor
from content_generator import ContentGenerator, StoryParams, CEFRLevel
from config import CURRICULUM_PATH, COLLOCATIONS_PATH, DATA_DIR, DEFAULT_STORY_LENGTH

def setup_argparse():
    parser = argparse.ArgumentParser(description="TunaTale Micro-Demo 0.1")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate curriculum command
    gen_parser = subparsers.add_parser('generate', help='Generate a new curriculum')
    gen_parser.add_argument('goal', type=str, help='Learning goal (e.g., "Ordering food in a restaurant")')
    
    # Extract collocations command
    subparsers.add_parser('extract', help='Extract collocations from curriculum')
    
    # Generate story command
    story_parser = subparsers.add_parser('story', help='Generate a story')
    story_parser.add_argument('objective', type=str, help='Learning objective for the story')
    story_parser.add_argument('--language', type=str, default='English', 
                            help=f'Target language (default: English)')
    story_parser.add_argument('--level', type=str, 
                            choices=[level.value for level in CEFRLevel], 
                            default='B1', 
                            help=f'CEFR level (default: B1)')
    story_parser.add_argument('--phase', type=int, 
                            choices=range(1, 6), 
                            default=1, 
                            help='Phase number (1-5, default: 1)')
    story_parser.add_argument('--length', 
                            type=int, 
                            default=DEFAULT_STORY_LENGTH, 
                            help=f'Target word count (default: {DEFAULT_STORY_LENGTH})')
    story_parser.add_argument('--previous', 
                            type=str, 
                            help='Path to previous story file for context')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View generated content')
    view_parser.add_argument('what', choices=['curriculum', 'collocations', 'story'])
    view_parser.add_argument('--day', type=int, help='Day number (for story)')
    
    return parser.parse_args()

def main():
    args = setup_argparse()
    
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
        # Generate story using the new simplified approach
        print(f"Generating story (Phase {args.phase}) for: {args.objective}")
        print(f"Language: {args.language}, Level: {args.level}, Length: {args.length} words")
        
        # Load previous story if provided
        previous_story = ""
        if args.previous:
            try:
                with open(args.previous, 'r') as f:
                    previous_story = f.read()
                print(f"Using previous story from: {args.previous}")
            except Exception as e:
                print(f"Warning: Could not read previous story: {e}")
        
        # Create story parameters
        story_params = StoryParams(
            learning_objective=args.objective,
            language=args.language,
            cefr_level=args.level,
            phase=args.phase,
            length=args.length
        )
        
        # Generate the story
        content_gen = ContentGenerator()
        story = content_gen.generate_story(story_params, previous_story)
        
        if story:
            print("\n=== STORY GENERATED ===\n")
            print(story)
            print("\n" + "="*50)
    
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
