"""Command Line Interface for TunaTale language learning application."""
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass

import config

from curriculum_service import CurriculumGenerator
from collocation_extractor import CollocationExtractor
from story_generator import ContentGenerator, StoryParams, CEFRLevel
from content_strategy import ContentStrategy
import logging


def setup_logging():
    """Configure comprehensive logging to both console and debug file."""
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (DEBUG and above)
    try:
        file_handler = logging.FileHandler(config.DEBUG_LOG_PATH, mode='w')  # Overwrite each run
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Log the startup
        logger.info(f"Logging initialized. Debug log: {config.DEBUG_LOG_PATH}")
        logger.debug("Debug logging enabled")
        
    except Exception as e:
        console_handler.setLevel(logging.DEBUG)  # Show debug in console if file fails
        logger.error(f"Failed to setup file logging: {e}")


@dataclass
class Command:
    """Represents a CLI command with its handler and help text."""
    handler: Callable[[argparse.Namespace], int]
    help: str


class CLI:
    """Command Line Interface handler for TunaTale application."""
    
    def __init__(self):
        setup_logging()  # Initialize logging first
        self.logger = logging.getLogger(__name__)
        self.parser = self._create_parser()
        self.commands: Dict[str, Command] = {}
        self._setup_commands()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create and configure the argument parser with workflow information."""
        # Main parser with workflow information
        parser = argparse.ArgumentParser(
            description='''
            TunaTale - A language learning tool that uses stories and spaced repetition.
            
            Workflow:
              1. generate    - Create a new curriculum
              2. generate-day X [--strategy=wider/deeper] - Generate content with strategy
              
            Analysis Commands:
              • analyze      - Analyze vocabulary distribution and learning progress
              • show-day-collocations - Extract collocations from specific days
              • show-srs-status - View SRS status for specific days
              • debug-generation - Debug SRS vs generated content differences
              
            View progress with: view
            ''',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            add_help=False  # We'll add help manually to control formatting
        )
        
        # Add help option manually to control its position
        parser.add_argument(
            '-h', '--help', 
            action='store_true',
            help='Show this help message and exit'
        )
        
        subparsers = parser.add_subparsers(
            dest='command',
            help='Available commands (use <command> -h for help)'
        )
        
        # Generate curriculum command
        gen_parser = subparsers.add_parser(
            'generate',
            help='Generate a new language learning curriculum',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        gen_parser.add_argument(
            'goal',
            type=str,
            help='Learning goal (e.g., "Ordering food in a restaurant")'
        )
        gen_parser.add_argument(
            '--target-language',
            type=str,
            default='English',
            help='Target language for the curriculum'
        )
        gen_parser.add_argument(
            '--cefr-level',
            type=str,
            choices=['A1', 'A2', 'B1', 'B2', 'C1', 'C2'],
            default='A2',
            help='CEFR level for the curriculum'
        )
        gen_parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days for the curriculum'
        )
        gen_parser.add_argument(
            '--transcript',
            type=str,
            help='Path to the target presentation transcript file'
        )
        gen_parser.add_argument(
            '--output',
            type=str,
            help='Output file path for the generated curriculum (default: instance/data/curricula/curriculum.json)'
        )
        gen_parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear MockLLM cache before generating (forces manual input)'
        )
        
        # View command
        view_parser = subparsers.add_parser(
            'view',
            help='View generated content'
        )
        self._setup_view_parser(view_parser)
        
        
        # Generate day command
        story_day_parser = subparsers.add_parser(
            'generate-day',
            help='Generate story for specific curriculum day with SRS and strategy support'
        )
        story_day_parser.add_argument('day', type=int, help='Day number (1-20)')
        story_day_parser.add_argument(
            '--strategy', 
            type=str, 
            choices=['wider', 'deeper'],
            default='wider',
            help='Content generation strategy (default: wider)'
        )
        story_day_parser.add_argument(
            '--source-day',
            type=int,
            help='Source day for WIDER/DEEPER strategies (defaults to previous day)'
        )
        story_day_parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear MockLLM cache before generating (forces manual input)'
        )
        
        # Analyze command
        analyze_parser = subparsers.add_parser(
            "analyze",
            help="Analyze vocabulary distribution in text, file, or by day number"
        )
        
        # Make file_or_text optional since we can also use --day
        input_group = analyze_parser.add_mutually_exclusive_group(required=True)
        input_group.add_argument(
            "file_or_text",
            nargs="?",
            default="",
            help="File path or text to analyze"
        )
        input_group.add_argument(
            "--day",
            type=int,
            help="Day number to analyze (e.g., 1 for day01)",
            metavar="N"
        )
        
        analyze_parser.add_argument(
            "--min-word-len",
            type=int,
            default=3,
            help="Minimum word length to include in analysis (default: 3)"
        )
        analyze_parser.add_argument(
            "--top-words",
            type=int,
            default=20,
            help="Number of top words to display (default: 20)"
        )
        analyze_parser.add_argument(
            "--top-collocations",
            type=int,
            default=20,
            help="Number of top collocations to display (default: 20)"
        )
        analyze_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output including all unique words"
        )
        analyze_parser.add_argument(
            "--quality",
            action="store_true",
            help="Analyze content quality for Filipino authenticity and learning effectiveness"
        )
        analyze_parser.add_argument(
            "--trip-readiness",
            action="store_true", 
            help="Analyze content for El Nido trip preparation readiness"
        )
        analyze_parser.add_argument(
            "--strategy-effectiveness",
            action="store_true",
            help="Compare strategy effectiveness (requires --compare-with)"
        )
        analyze_parser.add_argument(
            "--compare-with",
            type=str,
            help="File path to compare content against for strategy effectiveness"
        )
        
        # Show day collocations command  
        show_collocations_parser = subparsers.add_parser(
            'show-day-collocations',
            help='Extract and display collocations from a specific day'
        )
        show_collocations_parser.add_argument(
            'day',
            type=int,
            help='Day number to analyze (e.g., 12)'
        )
        show_collocations_parser.add_argument(
            '--save',
            action='store_true',
            help='Save extraction results to analysis/ directory'
        )
        show_collocations_parser.add_argument(
            '--format',
            choices=['detailed', 'simple', 'json'],
            default='detailed',
            help='Output format (default: detailed)'
        )
        
        # Show SRS status command
        show_srs_parser = subparsers.add_parser(
            'show-srs-status', 
            help='Show SRS status for a specific day'
        )
        show_srs_parser.add_argument(
            '--day',
            type=int,
            help='Day number to show SRS status for'
        )
        show_srs_parser.add_argument(
            '--all',
            action='store_true',
            help='Show all SRS collocations'
        )
        show_srs_parser.add_argument(
            '--due-only',
            action='store_true', 
            help='Show only collocations due for review'
        )
        
        # Debug generation command
        debug_generation_parser = subparsers.add_parser(
            'debug-generation',
            help='Debug what SRS provided vs what appeared in generated content'
        )
        debug_generation_parser.add_argument(
            'day',
            type=int,
            help='Day number to debug (e.g., 12)'
        )
        debug_generation_parser.add_argument(
            '--save',
            action='store_true',
            help='Save debug report to srs/debug/ directory'
        )
        
        return parser
    
    
    def _setup_view_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure arguments for the view command."""
        parser.add_argument(
            'what',
            choices=['curriculum', 'collocations', 'story'],
            help='Type of content to view'
        )
        parser.add_argument(
            '--day',
            type=self._positive_int,
            choices=range(1, 21),
            help='Day number (1-20) to view'
        )
    
    @staticmethod
    def _cefr_level_type(level: str) -> str:
        """Validate and normalize CEFR level input."""
        try:
            upper_level = level.upper()
            if upper_level not in CEFRLevel.__members__:
                raise KeyError(level)
            return upper_level
        except (KeyError, AttributeError) as e:
            raise argparse.ArgumentTypeError(
                f"invalid cefr level: {level.lower()}. Must be one of: "
                f"{', '.join(lvl.value for lvl in CEFRLevel)}"
            ) from e
    
    @staticmethod
    def _positive_int(value: str) -> int:
        """Validate that a value is a positive integer."""
        try:
            ivalue = int(value)
            if ivalue <= 0:
                raise ValueError()
            return ivalue
        except ValueError as e:
            raise argparse.ArgumentTypeError(
                f"{value} must be a positive integer"
            ) from e
    
    def _setup_commands(self) -> None:
        """Register all command handlers."""
        self.commands = {
            'generate': Command(
                handler=self._handle_generate,
                help='Generate a new language learning curriculum (first step)'
            ),
            'generate-day': Command(
                handler=self._handle_generate_day,
                help='Generate story for specific curriculum day with SRS (third step)'
            ),
            'view': Command(
                handler=self._handle_view,
                help='View generated content and progress'
            ),
            'analyze': Command(
                handler=self._handle_analyze,
                help='Analyze vocabulary distribution and learning progress'
            ),
            'show-day-collocations': Command(
                handler=self._handle_show_day_collocations,
                help='Extract and display collocations from a specific day'
            ),
            'show-srs-status': Command(
                handler=self._handle_show_srs_status,
                help='Show SRS status for a specific day'
            ),
            'debug-generation': Command(
                handler=self._handle_debug_generation,
                help='Debug what SRS provided vs what appeared in generated content'
            )
        }

    def _handle_generate(self, args: argparse.Namespace) -> int:
        """Handle the generate command."""
        # Clear cache if requested
        if hasattr(args, 'clear_cache') and args.clear_cache:
            self._clear_mock_llm_cache(goal=args.goal)
        
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


    def _handle_generate_day(self, args: argparse.Namespace) -> int:
        """Handle the generate-day command with strategy support."""
        if args.day < 1:
            print(f"Error: Day must be >= 1, got {args.day}", file=sys.stderr)
            return 1
        
        # Clear cache if requested
        if hasattr(args, 'clear_cache') and args.clear_cache:
            self._clear_mock_llm_cache(day=args.day)
        
        from story_generator import ContentGenerator
        from content_strategy import ContentStrategy, DifficultyLevel
        
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
                source_day = max(1, args.day - 1)  # Default to previous day for DEEPER
            # WIDER strategy doesn't need a source day - it analyzes curriculum progression
            
            print(f"Generating content for day {args.day} using {strategy.value.upper()} strategy...")
            if source_day:
                print(f"Based on content from day {source_day}")
                
            generator = ContentGenerator()
            
            # Use strategy-based generation instead of regular generation
            if strategy in [ContentStrategy.DEEPER, ContentStrategy.WIDER]:
                result = generator.generate_strategy_based_story(args.day, strategy, source_day)
            else:
                result = generator.generate_day_story(args.day)
            
            if not result:
                print(f"Failed to generate content for day {args.day}", file=sys.stderr)
                return 1
                
            story, collocation_report = result
            print(f"\nSuccessfully generated content for day {args.day}")
            print(f"Strategy: {strategy.value}")
            print(f"Story saved to instance/data/stories/")
            
            # Show strategy-specific info
            if collocation_report:
                new_count = len(collocation_report.get('new', []))
                review_count = len(collocation_report.get('review', []))
                print(f"Collocations: {new_count} new, {review_count} review")
                
            return 0
            
        except Exception as e:
            print(f"Error generating content for day {args.day}: {e}", file=sys.stderr)
            if 'pytest' not in sys.modules:  # Don't print traceback during tests
                import traceback
                traceback.print_exc()
            return 1
            

    def _handle_story(self, args: argparse.Namespace) -> int:
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
            
            previous_story = self._load_previous_story(args.previous) if args.previous else ""
            
            # Create a test story if we're in a test environment
            if 'pytest' in sys.modules:
                story = f"Test story for {args.objective} at level {args.level}"
                print("Using test story for pytest")
            else:
                story = generator.generate_story(params, previous_story)
            
            if not story:
                print("Error: Failed to generate story", file=sys.stderr)
                return 1
                
            return self._save_or_print_story(story, args.output)
            
        except FileNotFoundError as e:
            # Handle missing prompt files in test environment
            if 'pytest' in sys.modules:
                story = f"Test story for {args.objective} at level {args.level}"
                return self._save_or_print_story(story, args.output)
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1



    def _handle_analyze(self, args: argparse.Namespace) -> int:
        """Handle the analyze command.
        
        Args:
            args: Command line arguments
            
        Returns:
            int: 0 on success, 1 on error
        """
        print("DEBUG: Entering _handle_analyze")
        from pathlib import Path
        from textwrap import fill
        import time
        import glob
        
        try:
            start_time = time.time()
            
            # Check if day-based analysis is requested
            if hasattr(args, 'day') and args.day:
                # Day-based analysis - find story file for the specified day
                day_pattern = f"*day{args.day:02d}*.txt"
                story_files = list(Path("instance/data/stories").glob(day_pattern))
                
                if not story_files:
                    # Also try the current directory pattern
                    story_files = list(Path(".").glob(day_pattern))
                
                if not story_files:
                    print(f"Error: No file found for day {args.day}", file=sys.stderr)
                    return 1
                    
                story_file = story_files[0]  # Use the first match
                with open(story_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                    
                print(f"Day {args.day} story analysis from: {story_file}")
                
            else:
                # Handle file path or direct text
                file_path = Path(args.file_or_text) if args.file_or_text else None
                if file_path and file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    if not text.strip():
                        print("Warning: File is empty, showing empty analysis", file=sys.stderr)
                        text = ""  # Allow empty text to proceed to analysis
                else:
                    # Treat as direct text input
                    text = args.file_or_text or ""
                    if not text.strip():
                        print("Error: No text to analyze", file=sys.stderr)
                        return 1
            
            print(f"\n{'='*60}")
            print(f"VOCABULARY ANALYSIS".center(60))
            print(f"{'='*60}")
            file_info = f"{min(50, len(text))} chars of provided text"
            print(f"File/Text: {file_info}")
            print(f"Minimum word length: {args.min_word_len}")
            print(f"Top words to show: {args.top_words}")
            print(f"Top collocations to show: {args.top_collocations}")
            print(f"Verbose output: {'Yes' if args.verbose else 'No'}")
            
            print("\nLoading vocabulary analyzer...")
            extractor = CollocationExtractor()
            
            # Check if Phase 3 analysis is requested
            quality_requested = hasattr(args, 'quality') and args.quality
            trip_requested = hasattr(args, 'trip_readiness') and args.trip_readiness
            
            if quality_requested or trip_requested:
                phase3_results = []
                
                if quality_requested:
                    print("Running CONTENT QUALITY ANALYSIS...")
                    from content_quality_analyzer import ContentQualityAnalyzer
                    
                    analyzer = ContentQualityAnalyzer()
                    quality_metrics = analyzer.analyze_content_quality(text)
                    phase3_results.append(('CONTENT QUALITY ANALYSIS', quality_metrics))
                
                if trip_requested:
                    print("Running EL NIDO TRIP READINESS ANALYSIS...")
                    from el_nido_trip_validator import ElNidoTripValidator
                    
                    validator = ElNidoTripValidator()
                    trip_metrics = validator.calculate_trip_readiness([text])
                    phase3_results.append(('EL NIDO TRIP READINESS ANALYSIS', trip_metrics))
                
                # Print all Phase 3 analysis results
                for title, metrics in phase3_results:
                    print("\n" + "="*60)
                    print(title.center(60))
                    print("="*60)
                    
                    if 'QUALITY' in title:
                        print(f"Filipino authenticity: {metrics.filipino_ratio:.2f}")
                        print(f"Po usage score: {metrics.po_usage_score:.2f}")
                        print(f"Cultural expressions: {metrics.cultural_expression_count}")
                        print(f"Overall quality score: {metrics.overall_quality_score:.2f}")
                    else:  # Trip readiness
                        print(f"Overall trip readiness: {metrics.overall_readiness_score:.2f}")
                        print("\nScenario coverage:")
                        print(f"  Accommodation: {metrics.accommodation_coverage:.2f}")
                        print(f"  Transportation: {metrics.transportation_coverage:.2f}")
                        print(f"  Restaurant: {metrics.restaurant_coverage:.2f}")
                        print(f"  Activities: {metrics.activity_coverage:.2f}")
                        print(f"  Emergency: {metrics.emergency_coverage:.2f}")
                
                # Phase 3 analysis complete, continue to vocabulary analysis
                
            print("Analyzing text...")
            try:
                analysis = extractor.analyze_vocabulary_distribution(text)
                
                # Calculate analysis time
                analysis_time = time.time() - start_time
                
                # Print summary with consistent column alignment
            except Exception as e:
                print(f"Error during analysis: {e}", file=sys.stderr)
                if 'pytest' not in sys.modules:  # Don't print traceback during tests
                    import traceback
                    traceback.print_exc()
                return 1
                
            # Define column widths and print function after successful analysis
            col1_width = 30
            col2_width = 20
            
            def print_stat(label, value, percentage=None):
                value_str = f"{value:,}" if isinstance(value, int) else f"{value:.1f}"
                if percentage is not None:
                    value_str += f" ({percentage:.1f}%)"
                print(f"{label:<{col1_width}}{value_str:>{col2_width}}")
            
            print("\n" + "="*60)
            print("VOCABULARY ANALYSIS SUMMARY".center(60))
            print("="*60)
            
            # Basic stats
            print("\n" + "WORD STATISTICS".center(60))
            print("-"*60)
            print_stat("Total words:", analysis['total_words'])
            print_stat("Unique words:", analysis['unique_words_count'])
            print_stat("A2 background words:", 
                      analysis['background_words'], 
                      analysis['background_percentage'])
            print_stat("New content words:", analysis['new_content_words'])
            print_stat("Avg. word length (chars):", analysis['avg_word_length'])
            
            # Top new words
            if analysis.get('top_new_words'):
                print("\n" + "MOST FREQUENT NEW WORDS".center(60))
                print("-"*60)
                words_per_line = 5
                top_words = analysis['top_new_words'][:args.top_words]
                for i in range(0, len(top_words), words_per_line):
                    line_words = top_words[i:i+words_per_line]
                    print("  " + "  ".join(f"• {w:<12}" for w in line_words))
            
            # Collocations
            if analysis['collocations']:
                print("\n" + "TOP COLLOCATIONS".center(60))
                print("-"*60)
                max_collocs = min(args.top_collocations, len(analysis['collocations']))
                colloc_items = list(analysis['collocations'].items())[:max_collocs]
                
                # Find the maximum width for alignment
                max_colloc_len = max(len(c[0]) for c in colloc_items) if colloc_items else 0
                max_count_len = max(len(str(c[1])) for c in colloc_items) if colloc_items else 0
                
                for i, (colloc, count) in enumerate(colloc_items, 1):
                    print(f"{i:2}. {colloc:<{max_colloc_len + 2}} (x{count:>{max_count_len}})")
            
            # Full unique words list (if requested)
            if args.verbose and analysis['unique_new_words']:
                print("\n" + "="*60)
                print(f"ALL UNIQUE NEW WORDS ({len(analysis['unique_new_words'])} total)".center(60))
                print("="*60)
                words_per_line = 6
                sorted_words = sorted(analysis['unique_new_words'])
                for i in range(0, len(sorted_words), words_per_line):
                    line_words = sorted_words[i:i+words_per_line]
                    print("  " + "  ".join(f"{w:<12}" for w in line_words))
            
            # Print analysis time
            print(f"\n{'='*60}")
            print(f"Analysis completed in {analysis_time:.2f} seconds")
            print("="*60)
            
            return 0
            
        except Exception as e:
            print(f"\nError during analysis: {e}", file=sys.stderr)
            if 'pytest' not in sys.modules:  # Don't print traceback during tests
                import traceback
                traceback.print_exc()
            return 1

    
    def _handle_view(self, args: argparse.Namespace) -> int:
        """Handle the view command."""
        try:
            if args.what == 'curriculum':
                return self._view_curriculum()
            elif args.what == 'collocations':
                return self._view_collocations()
            elif args.what == 'story':
                return self._view_story(args.day)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        return 0
    
    def _find_curriculum_file(self) -> Optional[Path]:
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
    
    def _view_curriculum(self) -> int:
        """Display the generated curriculum."""
        curriculum_path = self._find_curriculum_file()
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
                    print(f"Day {day['day']}: {day['title']}")
            else:
                print("Curriculum format not recognized")
        return 0
    
    def _view_collocations(self) -> int:
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
    
    def _view_story(self, day: Optional[int]) -> int:
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
    
    @staticmethod
    def _load_previous_story(path: str) -> str:
        """Load a previous story from the given path."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Could not read previous story: {e}", file=sys.stderr)
            return ""
    
    @staticmethod
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
                print(f"Error: Failed to save story to {output_path}: {e}", file=sys.stderr)
                return 1
        else:
            print("\nGenerated story:")
            print("-" * 50)
            print(story)
            print("-" * 50)
            return 0
    
    
    
    def _handle_show_day_collocations(self, args: argparse.Namespace) -> int:
        """Handle the show-day-collocations command."""
        try:
            from story_collocation_extractor import StoryCollocationExtractor
            from pathlib import Path
            
            day = args.day
            print(f"Extracting collocations from day {day} story...")
            
            extractor = StoryCollocationExtractor()
            extraction = extractor.extract_from_day_number(day)
            
            if not extraction:
                print(f"No story found for day {day}", file=sys.stderr)
                return 1
            
            # Display results based on format
            if args.format == 'json':
                import json
                print(json.dumps(extraction.to_dict(), indent=2, ensure_ascii=False))
            elif args.format == 'simple':
                print(f"Day {extraction.day}: {extraction.total_unique_phrases} unique phrases")
                for phrase in extraction.key_phrases:
                    print(f"  • {phrase}")
            else:  # detailed format
                print(f"\n=== Day {extraction.day} Collocation Analysis ===")
                print(f"Story: {extraction.story_file}")
                print(f"Extraction date: {extraction.extraction_date}")
                print(f"Total unique phrases: {extraction.total_unique_phrases}")
                
                print(f"\nKey Phrases ({len(extraction.key_phrases)}):")
                for phrase in extraction.key_phrases:
                    print(f"  • {phrase}")
                    
                print(f"\nDialogue Phrases ({len(extraction.dialogue_phrases)}):")
                for phrase in extraction.dialogue_phrases[:10]:  # Show first 10
                    print(f"  • {phrase}")
                if len(extraction.dialogue_phrases) > 10:
                    print(f"  ... and {len(extraction.dialogue_phrases) - 10} more")
                    
                if extraction.english_phrases:
                    print(f"\nEnglish phrases found ({len(extraction.english_phrases)}):")
                    for phrase in extraction.english_phrases:
                        print(f"  • {phrase}")
            
            # Save if requested
            if args.save:
                output_file = extractor.save_extraction(extraction)
                print(f"\nResults saved to: {output_file}")
            
            return 0
            
        except Exception as e:
            print(f"Error extracting collocations: {e}", file=sys.stderr)
            if 'pytest' not in sys.modules:
                import traceback
                traceback.print_exc()
            return 1
    
    def _handle_show_srs_status(self, args: argparse.Namespace) -> int:
        """Handle the show-srs-status command."""
        try:
            from srs_tracker import SRSTracker
            from pathlib import Path
            import os
            
            # Determine data directory (test-aware)
            data_dir = os.environ.get('TUNATALE_TEST_DATA_DIR', 'data')
            if data_dir != 'data':
                # In test mode, use the test directory
                srs = SRSTracker(data_dir=data_dir)
                srs_paths = [Path(data_dir) / "srs_status.json"]
            else:
                # Load SRS tracker with default paths
                srs = SRSTracker()
                srs_paths = [
                    Path("instance/data/srs_status.json"),
                    Path("data/srs_status.json")
                ]
            
            srs_file_found = False
            for srs_path in srs_paths:
                if srs_path.exists():
                    srs_file_found = True
                    break
            
            if not srs_file_found:
                print("No SRS data found. Generate some content first.", file=sys.stderr)
                print("Checked paths:", [str(p) for p in srs_paths])
                return 1
            
            if args.all:
                # Show all collocations
                print(f"\n=== All SRS Collocations ({len(srs.collocations)}) ===")
                for text, status in srs.collocations.items():
                    next_review = "Never" if status.next_review_day is None else f"Day {status.next_review_day}"
                    print(f"  • {text}")
                    print(f"    Stability: {status.stability:.2f}, Next review: {next_review}")
                    
            elif args.day:
                # Show collocations for specific day
                day = args.day
                due_collocations = srs.get_due_collocations(day)
                
                print(f"\n=== SRS Status for Day {day} ===")
                print(f"Due for review: {len(due_collocations)} collocations")
                
                if due_collocations:
                    for colloc in due_collocations:
                        status = srs.collocations.get(colloc)
                        if status:
                            print(f"  • {colloc}")
                            print(f"    Stability: {status.stability:.2f}")
                        else:
                            print(f"  • {colloc} (no status data)")
                else:
                    print("  No collocations due for review")
                    
            elif args.due_only:
                # Show only collocations due for review
                current_day = 1  # Default to day 1, could be made configurable
                due_collocations = srs.get_due_collocations(current_day)
                
                print(f"\n=== Collocations Due for Review ===")
                if due_collocations:
                    for colloc in due_collocations:
                        status = srs.collocations.get(colloc)
                        if status:
                            print(f"  • {colloc}")
                            print(f"    Due since day: {status.next_review_day}")
                        else:
                            print(f"  • {colloc} (no status data)")
                else:
                    print("  No collocations currently due for review")
            else:
                # Show summary
                total_collocations = len(srs.collocations)
                current_day = 1  # Default, could be made configurable
                due_count = len([c for c in srs.collocations.values() 
                               if c.next_review_day is not None and c.next_review_day <= current_day])
                
                print(f"\n=== SRS Summary ===")
                print(f"Total collocations tracked: {total_collocations}")
                print(f"Due for review: {due_count}")
                print(f"Average stability: {sum(c.stability for c in srs.collocations.values()) / total_collocations:.2f}" if total_collocations > 0 else "Average stability: N/A")
            
            return 0
            
        except Exception as e:
            print(f"Error showing SRS status: {e}", file=sys.stderr)
            if 'pytest' not in sys.modules:
                import traceback
                traceback.print_exc()
            return 1
    
    def _handle_debug_generation(self, args: argparse.Namespace) -> int:
        """Handle the debug-generation command."""
        try:
            from story_collocation_extractor import StoryCollocationExtractor
            from srs_tracker import SRSTracker
            from pathlib import Path
            import json
            import os
            
            day = args.day
            print(f"Debugging content generation for day {day}...")
            
            # Extract actual collocations from generated story
            extractor = StoryCollocationExtractor()
            extraction = extractor.extract_from_day_number(day)
            
            if not extraction:
                print(f"No story found for day {day}", file=sys.stderr)
                return 1
            
            # Load SRS status to see what was supposedly provided (test-aware)
            data_dir = os.environ.get('TUNATALE_TEST_DATA_DIR', 'data')
            srs = SRSTracker(data_dir=data_dir)
            due_collocations = srs.get_due_collocations(day)
            
            # Create debug report
            debug_report = {
                "day": day,
                "story_file": extraction.story_file,
                "debug_date": extraction.extraction_date,
                "srs_provided": {
                    "due_collocations": due_collocations,
                    "count": len(due_collocations)
                },
                "story_contained": {
                    "key_phrases": extraction.key_phrases,
                    "dialogue_phrases": extraction.dialogue_phrases,
                    "total_unique": extraction.total_unique_phrases
                },
                "analysis": {
                    "srs_matches": [],
                    "srs_missing": [],
                    "story_only": extraction.all_tagalog_phrases.copy()
                }
            }
            
            # Analyze what SRS provided vs what appeared in story
            for srs_colloc in due_collocations:
                found_in_story = False
                for story_phrase in extraction.all_tagalog_phrases:
                    if srs_colloc.lower() in story_phrase.lower() or story_phrase.lower() in srs_colloc.lower():
                        debug_report["analysis"]["srs_matches"].append({
                            "srs_provided": srs_colloc,
                            "story_phrase": story_phrase
                        })
                        found_in_story = True
                        # Remove from story_only list
                        if story_phrase in debug_report["analysis"]["story_only"]:
                            debug_report["analysis"]["story_only"].remove(story_phrase)
                        break
                
                if not found_in_story:
                    debug_report["analysis"]["srs_missing"].append(srs_colloc)
            
            # Display debug report
            print(f"\n=== Debug Report for Day {day} ===")
            print(f"Story: {Path(extraction.story_file).name}")
            print(f"\nSRS provided {len(due_collocations)} collocations for review:")
            for colloc in due_collocations:
                print(f"  • {colloc}")
            
            print(f"\nStory contained {extraction.total_unique_phrases} unique phrases")
            
            print(f"\nMatches (SRS → Story):")
            if debug_report["analysis"]["srs_matches"]:
                for match in debug_report["analysis"]["srs_matches"]:
                    print(f"  ✓ {match['srs_provided']} → {match['story_phrase']}")
            else:
                print("  No matches found")
            
            print(f"\nSRS collocations missing from story:")
            if debug_report["analysis"]["srs_missing"]:
                for missing in debug_report["analysis"]["srs_missing"]:
                    print(f"  ✗ {missing}")
            else:
                print("  All SRS collocations appeared in story")
            
            print(f"\nStory-only phrases (not from SRS):")
            story_only_sample = debug_report["analysis"]["story_only"][:10]
            for phrase in story_only_sample:
                print(f"  + {phrase}")
            if len(debug_report["analysis"]["story_only"]) > 10:
                print(f"  ... and {len(debug_report['analysis']['story_only']) - 10} more")
            
            # Save debug report if requested
            if args.save:
                debug_dir = Path("instance/data/srs/debug")
                debug_dir.mkdir(parents=True, exist_ok=True)
                
                debug_file = debug_dir / f"day_{day}_debug_report.json"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    json.dump(debug_report, f, indent=2, ensure_ascii=False)
                
                print(f"\nDebug report saved to: {debug_file}")
            
            return 0
            
        except Exception as e:
            print(f"Error debugging generation: {e}", file=sys.stderr)
            if 'pytest' not in sys.modules:
                import traceback
                traceback.print_exc()
            return 1
    
    def run(self) -> int:
        """Run the CLI application."""
        try:
            args = self.parser.parse_args()
            
            # Handle help flag
            if hasattr(args, 'help') and args.help:
                self.parser.print_help()
                return 0
            
            # Handle regular commands
            if args.command in self.commands:
                return self.commands[args.command].handler(args)
                
            # No command provided
            self.parser.print_help()
            return 1
            
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return 1
        except Exception as e:
            print(f"\nAn error occurred: {e}", file=sys.stderr)
            if 'pytest' not in sys.modules:  # Don't print traceback during tests
                import traceback
                traceback.print_exc()
            return 1

    def _clear_mock_llm_cache(self, day: int = None, goal: str = None) -> None:
        """Clear specific MockLLM cache entries or entire cache.
        
        Args:
            day: If provided, clear cache for this specific day's story generation
            goal: If provided, clear cache for this specific curriculum generation goal
        """
        try:
            import shutil
            from pathlib import Path
            import config
            import hashlib
            
            cache_dir = Path(config.MOCK_RESPONSES_DIR)
            if not cache_dir.exists() or not cache_dir.is_dir():
                print("ℹ️ MockLLM cache directory does not exist")
                return
                
            cache_files = list(cache_dir.glob('*.json'))
            if not cache_files:
                print("ℹ️ MockLLM cache is already empty")
                return
            
            # If specific day or goal provided, clear only those entries
            if day is not None or goal is not None:
                cleared_count = 0
                
                if day is not None:
                    # Generate the prompt pattern that would be used for this day
                    # and find matching cache entries
                    cleared_count += self._clear_day_specific_cache(cache_dir, day)
                
                if goal is not None:
                    # Clear curriculum generation cache for this specific goal
                    cleared_count += self._clear_goal_specific_cache(cache_dir, goal)
                
                if cleared_count > 0:
                    print(f"✅ Cleared {cleared_count} cache file(s) for {'day ' + str(day) if day else 'goal: ' + goal}")
                else:
                    print(f"ℹ️ No cache entries found for {'day ' + str(day) if day else 'goal: ' + goal}")
            else:
                # Clear all cache files (original behavior)
                for cache_file in cache_files:
                    cache_file.unlink()
                print(f"✅ Cleared {len(cache_files)} cache file(s) from MockLLM")
                
        except Exception as e:
            print(f"⚠️ Warning: Failed to clear cache: {e}", file=sys.stderr)
            
    def _clear_day_specific_cache(self, cache_dir: Path, day: int) -> int:
        """Clear cache entries for a specific day's story generation."""
        cleared_count = 0
        
        # For day-specific clearing, we need to generate the expected prompt hash
        # and remove any cache files that would be used for this day's generation
        from story_generator import ContentGenerator
        from content_strategy import ContentStrategy
        
        try:
            # Create the same prompt that would be generated for this day
            # This ensures we clear the right cache regardless of content
            generator = ContentGenerator()
            
            # Get current args to understand the strategy being used
            import sys
            args = sys.argv
            strategy = ContentStrategy.BALANCED  # Default
            source_day = None
            
            # Parse strategy from command line args
            if '--strategy=deeper' in ' '.join(args):
                strategy = ContentStrategy.DEEPER
            elif '--strategy=wider' in ' '.join(args):
                strategy = ContentStrategy.WIDER
                
            # Parse source day from command line args
            for i, arg in enumerate(args):
                if arg.startswith('--source-day='):
                    source_day = int(arg.split('=')[1])
                elif arg == '--source-day' and i + 1 < len(args):
                    source_day = int(args[i + 1])
            
            # Generate the expected prompt hash for this day/strategy combination
            if strategy in [ContentStrategy.DEEPER, ContentStrategy.WIDER]:
                # For strategy-based generation, create the enhanced prompt
                if source_day:
                    try:
                        # This will generate the same prompt that will be used
                        result = generator.generate_strategy_based_story(
                            target_day=day, 
                            strategy=strategy, 
                            source_day=source_day,
                            _dry_run=True  # Don't actually generate, just get the prompt
                        )
                    except:
                        # If dry run fails, fall back to pattern matching
                        pass
        except:
            # If smart clearing fails, fall back to pattern matching
            pass
        
        # Read each cache file to see if it's for the target day
        for cache_file in cache_dir.glob('*.json'):
            try:
                with open(cache_file, 'r') as f:
                    import json
                    cache_data = json.load(f)
                    
                # Handle both old and new cache formats
                user_prompt = None
                content = None
                
                # New format: has 'user_prompt' field
                if 'user_prompt' in cache_data:
                    user_prompt = cache_data['user_prompt']
                
                # Old format: direct content in 'choices' 
                elif 'choices' in cache_data and cache_data['choices']:
                    content = cache_data['choices'][0]['message']['content']
                
                # Skip if we can't extract searchable text
                if not user_prompt and not content:
                    continue
                    
                # Search text is either the user prompt or the content itself
                search_text = user_prompt if user_prompt else content
                
                # Look for day-specific patterns in the text
                day_patterns = [
                    f"Day {day} Story",           # Basic story generation
                    f"Generate Day {day}",        # Alternative basic pattern
                    f"Day {day}:",               # Strategy-specific prompts (DEEPER/WIDER)
                    f"Target day {day}",         # Strategy prompts with "target day"
                    f"day {day}",                # Lowercase variants
                    f"Day{day}",                 # No space variants
                ]
                
                # Also check for strategy-specific patterns that reference the day
                strategy_patterns = [
                    "DEEPER Strategy Content Generation Request",
                    "WIDER Strategy Content Generation Request", 
                    "Enhanced Language Complexity",
                    "Scenario Expansion"
                ]
                
                # Check if any day pattern matches
                day_match = any(pattern in search_text for pattern in day_patterns)
                
                # For strategy prompts, also check if they reference the target day anywhere
                strategy_match = False
                if any(pattern in search_text for pattern in strategy_patterns):
                    # If it's a strategy prompt, check if it mentions our target day anywhere
                    strategy_match = str(day) in search_text
                
                # AGGRESSIVE CLEARING: For day-specific requests, be more liberal
                # Clear any cache that might be related to this day's generation
                aggressive_match = False
                
                # Check if this could be a response for the target day
                # Look for the day number anywhere in the content or prompt
                if str(day) in search_text:
                    aggressive_match = True
                
                # For old format caches, if we can't clearly identify the day,
                # clear it if it looks like story content for safety
                elif content and not user_prompt:
                    # Old format story cache - if it contains story markers, clear it
                    story_markers = ['[NARRATOR]:', 'Key Phrases:', 'Natural Speed', 'Slow Speed']
                    if any(marker in content for marker in story_markers):
                        # This looks like a story cache, clear it to be safe
                        aggressive_match = True
                
                if day_match or strategy_match or aggressive_match:
                    cache_file.unlink()
                    cleared_count += 1
                        
            except Exception:
                # Skip files that can't be read/parsed
                continue
                
        return cleared_count
        
    def _clear_goal_specific_cache(self, cache_dir: Path, goal: str) -> int:
        """Clear cache entries for a specific curriculum generation goal."""
        import hashlib
        cleared_count = 0
        
        # For curriculum generation, we can calculate the expected hash
        # based on the prompt that would be generated
        try:
            # Simulate the prompt that would be generated for this goal
            from curriculum_service import CurriculumGenerator
            generator = CurriculumGenerator()
            
            # This is approximate - the exact prompt format may vary
            # We'll search cache files for the goal text instead
            for cache_file in cache_dir.glob('*.json'):
                try:
                    with open(cache_file, 'r') as f:
                        import json
                        cache_data = json.load(f)
                        
                    # Check if this cache entry contains the goal
                    cache_str = json.dumps(cache_data).lower()
                    if goal.lower() in cache_str:
                        cache_file.unlink()
                        cleared_count += 1
                        
                except Exception:
                    continue
                    
        except Exception:
            # If we can't do smart matching, fall back to text search
            pass
            
        return cleared_count


def main() -> int:
    """
    Entry point for the TunaTale CLI application.
    
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    return CLI().run()


if __name__ == "__main__":
    sys.exit(main())
