"""Command Line Interface for TunaTale language learning application."""
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass

import config
from cli.utils import validate_day_parameter

from curriculum_service import CurriculumGenerator
# from collocation_extractor import CollocationExtractor  # Disabled - no longer needed
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
        
        # Generate command with subcommands (curriculum, day)
        gen_parser = subparsers.add_parser(
            'generate',
            help='Generate curriculum or daily content',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        gen_subparsers = gen_parser.add_subparsers(dest='generate_type', help='What to generate')

        # generate curriculum subcommand
        gen_curriculum_parser = gen_subparsers.add_parser(
            'curriculum',
            help='Generate a new language learning curriculum'
        )
        gen_curriculum_parser.add_argument(
            'goal',
            type=str,
            help='Learning goal (e.g., "Ordering food in a restaurant")'
        )
        gen_curriculum_parser.add_argument(
            '--target-language',
            type=str,
            default='English',
            help='Target language for the curriculum'
        )
        gen_curriculum_parser.add_argument(
            '--cefr-level',
            type=str,
            choices=['A1', 'A2', 'B1', 'B2', 'C1', 'C2'],
            default='A2',
            help='CEFR level for the curriculum'
        )
        gen_curriculum_parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days for the curriculum'
        )
        gen_curriculum_parser.add_argument(
            '--transcript',
            type=str,
            help='Path to the target presentation transcript file'
        )
        gen_curriculum_parser.add_argument(
            '--output',
            type=str,
            help='Output file path for the generated curriculum (default: instance/data/curricula/curriculum.json)'
        )
        gen_curriculum_parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear MockLLM cache before generating (forces manual input)'
        )

        # generate day subcommand
        gen_day_parser = gen_subparsers.add_parser(
            'day',
            help='Generate story for specific curriculum day with SRS and strategy support'
        )
        gen_day_parser.add_argument('day_number', type=int, help='Day number (1-20)', metavar='DAY')
        gen_day_parser.add_argument(
            '--strategy',
            type=str,
            choices=['wider', 'deeper'],
            default='wider',
            help='Content generation strategy (default: wider)'
        )
        gen_day_parser.add_argument(
            '--source-day',
            type=int,
            help='Source day for WIDER/DEEPER strategies (defaults to previous day)'
        )
        gen_day_parser.add_argument(
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
        
        # Analyze command with subcommands
        analyze_parser = subparsers.add_parser(
            "analyze",
            help="Analyze vocabulary, collocations, and content"
        )
        analyze_subparsers = analyze_parser.add_subparsers(dest='analyze_type', help='What to analyze')

        # analyze vocab subcommand
        analyze_vocab_parser = analyze_subparsers.add_parser(
            'vocab',
            help='Analyze vocabulary distribution in text, file, or by day number'
        )

        # Make file_or_text optional since we can also use --day
        input_group = analyze_vocab_parser.add_mutually_exclusive_group(required=True)
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

        analyze_vocab_parser.add_argument(
            "--min-word-len",
            type=int,
            default=3,
            help="Minimum word length to include in analysis (default: 3)"
        )
        analyze_vocab_parser.add_argument(
            "--top-words",
            type=int,
            default=20,
            help="Number of top words to display (default: 20)"
        )
        analyze_vocab_parser.add_argument(
            "--top-collocations",
            type=int,
            default=20,
            help="Number of top collocations to display (default: 20)"
        )
        analyze_vocab_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output including all unique words"
        )
        analyze_vocab_parser.add_argument(
            "--quality",
            action="store_true",
            help="Analyze content quality for Filipino authenticity and learning effectiveness"
        )
        analyze_vocab_parser.add_argument(
            "--trip-readiness",
            action="store_true",
            help="Analyze content for El Nido trip preparation readiness"
        )
        analyze_vocab_parser.add_argument(
            "--strategy-effectiveness",
            action="store_true",
            help="Compare strategy effectiveness (requires --compare-with)"
        )
        analyze_vocab_parser.add_argument(
            "--compare-with",
            type=str,
            help="File path to compare content against for strategy effectiveness"
        )
        analyze_vocab_parser.add_argument(
            "--extract-translations",
            action="store_true",
            help="Extract English↔Filipino translation pairs using LLM-based analysis"
        )

        # analyze collocations subcommand (was show-day-collocations)
        analyze_collocations_parser = analyze_subparsers.add_parser(
            'collocations',
            help='Extract and display collocations from a specific day'
        )
        analyze_collocations_parser.add_argument(
            '--day',
            type=int,
            required=True,
            help='Day number to analyze (e.g., 12)'
        )
        analyze_collocations_parser.add_argument(
            '--save',
            action='store_true',
            help='Save extraction results to analysis/ directory'
        )
        analyze_collocations_parser.add_argument(
            '--format',
            choices=['detailed', 'simple', 'json'],
            default='detailed',
            help='Output format (default: detailed)'
        )

        # analyze debug subcommand (was debug-generation)
        analyze_debug_parser = analyze_subparsers.add_parser(
            'debug',
            help='Debug what SRS provided vs what appeared in generated content'
        )
        analyze_debug_parser.add_argument(
            '--day',
            type=int,
            required=True,
            help='Day number to debug (e.g., 12)'
        )
        


        # Enforce command with subcommands
        enforce_parser = subparsers.add_parser(
            "enforce",
            help="SRS constraint enforcement and debugging"
        )
        enforce_subparsers = enforce_parser.add_subparsers(dest='enforce_type', help='Enforcement operations')

        # enforce apply subcommand (was enforce-srs)
        enforce_apply_parser = enforce_subparsers.add_parser(
            'apply',
            help='Apply SRS constraint enforcement to existing story files'
        )
        enforce_apply_parser.add_argument(
            '--day',
            type=int,
            help='Specific day to enforce (if not provided, enforces all stories)'
        )
        enforce_apply_parser.add_argument(
            '--save',
            action='store_true',
            help='Save enforced version to new file'
        )

        # enforce debug subcommand (was debug-srs)
        enforce_debug_parser = enforce_subparsers.add_parser(
            'debug',
            help='Debug SRS enforcement and vocabulary recognition states for a day'
        )
        enforce_debug_parser.add_argument(
            'day',
            type=int,
            nargs='?',
            help='Day number to show SRS debug information for (not required for --generate-template)'
        )
        enforce_debug_parser.add_argument(
            '--vocabulary-analysis',
            action='store_true',
            help='Analyze vocabulary recognition states from story content'
        )
        enforce_debug_parser.add_argument(
            '--export',
            type=str,
            help='Export vocabulary analysis to JSON file (e.g., debug.json)'
        )
        enforce_debug_parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate vocabulary analysis against expected states'
        )
        enforce_debug_parser.add_argument(
            '--validation-file',
            type=str,
            help='Path to validation JSON file (default: day{N}_validation.json)'
        )
        enforce_debug_parser.add_argument(
            '--error-tolerance',
            choices=['strict', 'medium', 'permissive'],
            default='medium',
            help='Error tolerance for validation parsing (default: medium)'
        )
        enforce_debug_parser.add_argument(
            '--generate-template',
            choices=['simple', 'comprehensive'],
            help='Generate validation template for LLM and exit'
        )
        enforce_debug_parser.add_argument(
            '--show-pre-enforcement',
            action='store_true',
            help='Show reconstructed content before SRS enforcement was applied'
        )
        enforce_debug_parser.add_argument(
            '--test-words',
            type=str,
            help='Test specific vocabulary terms (comma-separated) against SRS system'
        )
        enforce_debug_parser.add_argument(
            '--test-json',
            type=str,
            help='Test vocabulary from JSON validation file against SRS system'
        )
        enforce_debug_parser.add_argument(
            '--category',
            type=str,
            help='Filter JSON vocabulary by category (e.g., CRITICAL_SRS_ENFORCEMENT_FAILURES)'
        )

        # enforce test subcommand (was test-enforcement)
        enforce_test_parser = enforce_subparsers.add_parser(
            'test',
            help='Test constraint enforcement on text'
        )
        # Input specification (mutually exclusive)
        test_input_group = enforce_test_parser.add_mutually_exclusive_group(required=True)
        test_input_group.add_argument('text', nargs='?',
                                help='Text to test enforcement on')
        test_input_group.add_argument('--day', type=int,
                                help='Test enforcement on specific day\'s content')
        # Options
        enforce_test_parser.add_argument('--show-details', action='store_true',
                                help='Show detailed replacement information')
        enforce_test_parser.add_argument('--method', choices=['constraint', 'llm', 'both'],
                                default='both',
                                help='Enforcement method to test (default: both)')
        enforce_test_parser.add_argument('--context', type=str, default='cli_test',
                                help='Context for enforcement (default: cli_test)')

        # enforce show subcommand (was show-enforcement)
        enforce_show_parser = enforce_subparsers.add_parser(
            'show',
            help='Show current enforcement rules'
        )
        enforce_show_parser.add_argument('--format', choices=['table', 'json'], default='table',
                                help='Output format (default: table)')
        enforce_show_parser.add_argument('--filter', type=str,
                                help='Filter rules by substring')
        enforce_show_parser.add_argument('--stats', action='store_true',
                                help='Show enforcement statistics')

        # Import and add new SRS management commands
        from cli.srs_commands import add_srs_commands
        from cli.vocab_commands import add_vocab_commands

        # Add new SRS management command groups
        add_srs_commands(subparsers)
        add_vocab_commands(subparsers)
        self._add_translation_commands(subparsers)
        
        return parser
    
    def _add_translation_commands(self, subparsers) -> None:
        """Add translation management commands to the parser."""


        # Translate command with subcommands
        translate_parser = subparsers.add_parser(
            "translate",
            help="Manage translation pairs and database"
        )
        translate_subparsers = translate_parser.add_subparsers(dest='translate_type', help='Translation operations')

        # translate extract subcommand (was extract-translations)
        translate_extract_parser = translate_subparsers.add_parser(
            'extract',
            help='Extract translation pairs from all story files'
        )
        translate_extract_parser.add_argument(
            "--stories-dir",
            type=str,
            default="instance/data/stories",
            help="Directory containing story files (default: instance/data/stories)"
        )
        translate_extract_parser.add_argument(
            "--output-report",
            action="store_true",
            help="Save detailed extraction report to analysis/ directory"
        )

        # translate show subcommand (was show-translations)
        translate_show_parser = translate_subparsers.add_parser(
            'show',
            help='Show current translation pairs in enhanced database'
        )
        translate_show_parser.add_argument(
            "--min-confidence",
            type=float,
            default=0.8,
            help="Minimum confidence score to display (default: 0.8)"
        )
        translate_show_parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Maximum number of pairs to display (default: 20)"
        )

        # translate lookup subcommand (was lookup-translation)
        translate_lookup_parser = translate_subparsers.add_parser(
            'lookup',
            help='Test bidirectional English↔Filipino lookup'
        )
        translate_lookup_parser.add_argument(
            "word",
            help="English or Filipino word/phrase to lookup"
        )
        translate_lookup_parser.add_argument(
            "--reverse",
            action="store_true",
            help="Force reverse lookup (Filipino→English)"
        )

        # translate stats subcommand (was translation-stats)
        translate_stats_parser = translate_subparsers.add_parser(
            'stats',
            help='Show enhanced database statistics'
        )
    
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
    
    @staticmethod
    def _validate_day_parameter(day: int, command_name: str) -> bool:
        """Validate that day parameter is a positive integer.
        DEPRECATED: Use cli.utils.validate_day_parameter() instead.
        """
        return validate_day_parameter(day, command_name)
    
    def _setup_commands(self) -> None:
        """Register all command handlers."""
        self.commands = {
            'generate': Command(
                handler=self._handle_generate,
                help='Generate a new language learning curriculum (first step)'
            ),
            'view': Command(
                handler=self._handle_view,
                help='View generated content and progress'
            ),
            'analyze': Command(
                handler=self._handle_analyze,
                help='Analyze vocabulary distribution and learning progress'
            ),
            'enforce': Command(
                handler=self._handle_enforce,
                help='SRS constraint enforcement and debugging'
            ),
            'translate': Command(
                handler=self._handle_translate,
                help='Manage translation pairs and database'
            )
        }

    def _handle_generate(self, args: argparse.Namespace) -> int:
        """Handle the generate command and route to subcommands."""
        from cli.generation_commands import handle_generate
        return handle_generate(args)




    def _handle_analyze(self, args: argparse.Namespace) -> int:
        """Handle the analyze command and route to subcommands."""
        from cli.analysis_commands import handle_analyze
        return handle_analyze(args)

    def _handle_view(self, args: argparse.Namespace) -> int:
        """Handle the view command."""
        from cli.view_commands import handle_view
        return handle_view(args)

    def _find_curriculum_file(self) -> Optional[Path]:
        """Find the most recent curriculum file."""
        from cli.view_commands import find_curriculum_file
        return find_curriculum_file()

    def _view_curriculum(self) -> int:
        """Display the generated curriculum."""
        from cli.view_commands import view_curriculum
        return view_curriculum()

    def _handle_enforce(self, args: argparse.Namespace) -> int:
        """Handle the enforce command and route to subcommands."""
        # Note: apply and debug subcommands still in main.py due to complexity
        # test and show subcommands are in cli.enforcement_commands
        if args.enforce_type == 'apply':
            return self._handle_enforce_srs(args)
        elif args.enforce_type == 'debug':
            return self._handle_debug_srs(args)
        elif args.enforce_type == 'test':
            from cli.enforcement_commands import handle_test_enforcement
            return handle_test_enforcement(args) or 0
        elif args.enforce_type == 'show':
            from cli.enforcement_commands import handle_show_enforcement
            return handle_show_enforcement(args) or 0
        else:
            print("Error: Please specify enforcement operation (apply, debug, test, or show)", file=sys.stderr)
            return 1

    def _handle_enforce_srs(self, args: argparse.Namespace) -> int:
        """Handle the enforce-srs command to apply constraint enforcement to stories."""
        try:
            from srs_enforcer import SRSEnforcer
            from srs_database import SRSDatabase
            from pathlib import Path
            
            # Initialize SRS enforcer
            try:
                db = SRSDatabase()
                enforcer = SRSEnforcer(db)
            except Exception as e:
                print(f"Error initializing SRS enforcer: {e}", file=sys.stderr)
                return 1
            
            # Handle specific day or all stories
            if hasattr(args, 'day') and args.day:
                # Enforce specific day
                day = args.day
                print(f"Applying SRS constraint enforcement to day {day}...")
                
                # Find the story file for this day
                stories_dir = Path("instance/data/stories")
                possible_patterns = [
                    f"story_day{day}_*.txt",
                    f"day{day}_*.txt", 
                    f"demo-0.0.3-day-{day}.txt",
                    f"*day{day}*.txt"
                ]
                
                story_file = None
                for pattern in possible_patterns:
                    matches = list(stories_dir.glob(pattern))
                    if matches:
                        story_file = matches[0]  # Use first match
                        break
                
                if not story_file:
                    print(f"No story file found for day {day}", file=sys.stderr)
                    return 1
                
                # Read and enforce
                with open(story_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                print(f"Processing: {story_file.name}")
                enforced_content, violations = enforcer.enforce_constraints(
                    content=content,
                    day=day,
                    context=f"cli_enforcement_day{day}"
                )
                
                if violations:
                    print(f"\n📊 Summary: {len(violations)} violations found and corrected")
                    
                    # Save enforced version if requested
                    if hasattr(args, 'save') and args.save:
                        enforced_file = story_file.with_stem(f"{story_file.stem}_enforced")
                        with open(enforced_file, 'w', encoding='utf-8') as f:
                            f.write(enforced_content)
                        print(f"💾 Enforced version saved to: {enforced_file}")
                    
                    # Show before/after examples
                    print("\n📝 Example changes:")
                    for i, v in enumerate(violations[:3], 1):
                        print(f"  {i}. '{v['english']}' → '{v['filipino']}' ({v['count']}x)")
                    if len(violations) > 3:
                        print(f"  ... and {len(violations) - 3} more")
                else:
                    print("✅ No violations found - story already complies with SRS constraints")
                
                return 0
            
            else:
                # Enforce all stories
                print("Applying SRS constraint enforcement to all stories...")
                
                stories_dir = Path("instance/data/stories")
                story_files = list(stories_dir.glob("*.txt"))
                
                if not story_files:
                    print("No story files found", file=sys.stderr)
                    return 1
                
                total_violations = 0
                processed_count = 0
                
                for story_file in story_files:
                    try:
                        with open(story_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Try to extract day number from filename
                        day_num = 1
                        for part in story_file.name.split('_'):
                            if 'day' in part.lower():
                                try:
                                    day_num = int(''.join(filter(str.isdigit, part)))
                                    break
                                except ValueError:
                                    pass
                        
                        enforced_content, violations = enforcer.enforce_constraints(
                            content=content,
                            day=day_num,
                            context=f"cli_bulk_enforcement"
                        )
                        
                        if violations:
                            total_violations += len(violations)
                            print(f"  ✓ {story_file.name}: {len(violations)} violations corrected")
                        
                        processed_count += 1
                        
                    except Exception as e:
                        print(f"  ❌ Error processing {story_file.name}: {e}")
                        continue
                
                print(f"\n📊 Summary:")
                print(f"  Files processed: {processed_count}")
                print(f"  Total violations corrected: {total_violations}")
                print(f"  Violations recorded in database for analysis")
                
                return 0
            
        except Exception as e:
            print(f"Error in SRS enforcement: {e}", file=sys.stderr)
            if 'pytest' not in sys.modules:
                import traceback
                traceback.print_exc()
            return 1
    
    def _handle_debug_srs(self, args: argparse.Namespace) -> int:
        """Handle the debug-srs command to show what SRS enforcement did for a day."""
        try:
            # Handle template generation first (no day required)
            if hasattr(args, 'generate_template') and args.generate_template:
                return self._handle_template_generation(args.generate_template)
            
            # Handle vocabulary testing (no day required)
            if hasattr(args, 'test_words') and args.test_words and args.test_words.strip():
                return self._handle_vocabulary_testing(args.test_words, None, args.category)
            
            if hasattr(args, 'test_json') and args.test_json and args.test_json.strip():
                return self._handle_vocabulary_testing(None, args.test_json, args.category)
            
            # Ensure day is provided for other operations
            if args.day is None:
                print("Error: Day number is required for SRS debug operations", file=sys.stderr)
                return 1
            
            from srs_database import SRSDatabase
            import sqlite3
            import json
            
            day = args.day
            print(f"\n=== SRS Debug for Day {day} ===")
            
            # Load violations from database
            try:
                db = SRSDatabase()
                # Use sqlite3 directly since SRSDatabase doesn't have get_connection method
                with sqlite3.connect(db.db_path) as connection:
                    cursor = connection.cursor()
                    
                    # Get violations for this day
                cursor.execute("""
                    SELECT english_text, known_filipino, violation_type, was_replaced, context, created_at
                    FROM srs_violations 
                    WHERE day = ?
                    ORDER BY created_at DESC
                    LIMIT 50
                """, (day,))
                
                violations = cursor.fetchall()
                
                if not violations:
                    print(f"No SRS enforcement data found for day {day}")
                    print("This could mean:")
                    print("  • No story was generated for this day with SRS enforcement")
                    print("  • No violations were found (all content was already properly Filipino)")
                    print("  • SRS enforcement failed or was disabled")
                    return 1
                
                # Group violations by context and type
                by_context = {}
                for violation in violations:
                    english, filipino, v_type, was_replaced, context, created_at = violation
                    if context not in by_context:
                        by_context[context] = []
                    by_context[context].append({
                        'english': english,
                        'filipino': filipino,
                        'type': v_type,
                        'replaced': bool(was_replaced),
                        'timestamp': created_at
                    })
                
                # Display violations by context
                for context, context_violations in by_context.items():
                    print(f"\n📋 Context: {context}")
                    print(f"   Total violations: {len(context_violations)}")
                    
                    # Separate violations by type
                    english_violations = [v for v in context_violations if v['type'] != 'key_phrases_redundancy']
                    key_phrases_violations = [v for v in context_violations if v['type'] == 'key_phrases_redundancy']
                    
                    # Show English replacements made
                    replaced = [v for v in english_violations if v['replaced']]
                    if replaced:
                        print(f"\n✅ English Replacements Made ({len(replaced)}):")
                        for i, v in enumerate(replaced, 1):
                            print(f"   {i:2}. '{v['english']}' → '{v['filipino']}'")
                            print(f"       Method: {v['type']}")
                    
                    # Show what wasn't replaced (if any)
                    not_replaced = [v for v in english_violations if not v['replaced']]
                    if not_replaced:
                        print(f"\n⏭️ English Not Replaced ({len(not_replaced)}):")
                        for i, v in enumerate(not_replaced, 1):
                            print(f"   {i:2}. '{v['english']}' (would be '{v['filipino']}')")
                    
                    # Show Key Phrases violations (separate replaced vs flagged)
                    if key_phrases_violations:
                        replaced_kp = [v for v in key_phrases_violations if v['replaced']]
                        flagged_kp = [v for v in key_phrases_violations if not v['replaced']]
                        
                        if replaced_kp:
                            print(f"\n🔄 Key Phrases Replaced ({len(replaced_kp)}):")
                            for i, v in enumerate(replaced_kp, 1):
                                print(f"   {i:2}. '{v['english']}' → '{v['filipino']}'")
                                print(f"       Replaced with new vocabulary")
                        
                        if flagged_kp:
                            print(f"\n⚠️ Key Phrases Violations ({len(flagged_kp)}):")
                            for i, v in enumerate(flagged_kp, 1):
                                print(f"   {i:2}. '{v['english']}' - Already known")
                                print(f"       Matches SRS: '{v['filipino']}'")
                                print(f"       Should not appear in Key Phrases section")
                
                # Show recent enforcement activity
                print(f"\n🕐 Most Recent Enforcement:")
                latest = violations[0] if violations else None
                if latest:
                    print(f"   Date: {latest[5]}")
                    print(f"   Context: {latest[4]}")
                    print(f"   Method: {latest[2]}")
                
                # Check if pre-enforcement content was requested
                if hasattr(args, 'show_pre_enforcement') and args.show_pre_enforcement:
                    print(f"\n" + "="*60)
                    print(f"PRE-ENFORCEMENT CONTENT RECONSTRUCTION FOR DAY {day}")
                    print(f"="*60)
                    
                    pre_enforcement_content = self._reconstruct_pre_enforcement_content(violations)
                    if pre_enforcement_content:
                        print(f"\n📄 Reconstructed Original Content:")
                        print(f"{'─' * 50}")
                        print(pre_enforcement_content)
                        print(f"{'─' * 50}")
                        
                        # Option to save to file
                        pre_enforcement_file = f"story_day{day}_pre_enforcement.txt"
                        with open(pre_enforcement_file, 'w', encoding='utf-8') as f:
                            f.write(pre_enforcement_content)
                        print(f"✅ Pre-enforcement content saved to: {pre_enforcement_file}")
                    else:
                        print("❌ Could not reconstruct pre-enforcement content")
                        
                        # Check if original backup exists
                        from pathlib import Path
                        backup_dir = Path("instance/data/stories/originals")
                        backup_files = list(backup_dir.glob(f"*day{day}_original*.txt"))
                        if backup_files:
                            print(f"💡 However, original backups are available:")
                            for backup_file in backup_files:
                                print(f"  📄 {backup_file}")
                        else:
                            print("💡 No original backups found. Future story generations will automatically save originals.")
                
                # Check if vocabulary analysis was requested
                if hasattr(args, 'vocabulary_analysis') and args.vocabulary_analysis:
                    print(f"\n" + "="*50)
                    print(f"VOCABULARY ANALYSIS FOR DAY {day}")
                    print(f"="*50)
                    
                    from srs_debug_analyzer import SRSDebugAnalyzer
                    analyzer = SRSDebugAnalyzer()
                    
                    # Handle validation if requested
                    if hasattr(args, 'validate') and args.validate:
                        validation_file = args.validation_file
                        if not validation_file:
                            validation_file = f"day{day}_validation.json"
                        
                        error_tolerance = getattr(args, 'error_tolerance', 'medium')
                        
                        print(f"🔍 Running validation against: {validation_file}")
                        print(f"📊 Error tolerance: {error_tolerance}")
                        
                        validation_results = analyzer.validate_against_expected(
                            day, validation_file, error_tolerance
                        )
                        
                        if 'error' in validation_results:
                            print(f"❌ Validation Error: {validation_results['error']}")
                        else:
                            # Export validation results if requested
                            if hasattr(args, 'export') and args.export:
                                import json
                                with open(args.export, 'w', encoding='utf-8') as f:
                                    json.dump(validation_results, f, indent=2, ensure_ascii=False)
                                print(f"✅ Validation results exported to {args.export}")
                            
                            # Display validation results
                            self._display_validation_results(validation_results)
                    else:
                        # Regular vocabulary analysis
                        report = analyzer.analyze_day_vocabulary(day)
                        
                        if 'error' in report:
                            print(f"❌ Error: {report['error']}")
                        else:
                            # Export if requested
                            if hasattr(args, 'export') and args.export:
                                import json
                                with open(args.export, 'w', encoding='utf-8') as f:
                                    json.dump(report, f, indent=2, ensure_ascii=False)
                                print(f"✅ Vocabulary analysis exported to {args.export}")
                            
                            # Display summary
                            self._display_vocabulary_analysis(report)
                
                return 0
                
            except Exception as e:
                print(f"Error accessing SRS database: {e}")
                print("Make sure the SRS database has been initialized.")
                return 1
                
        except Exception as e:
            print(f"Error in SRS debug: {e}", file=sys.stderr)
            if 'pytest' not in sys.modules:
                import traceback
                traceback.print_exc()
            return 1

    def _handle_vocabulary_testing(self, test_words: str, test_json: str, category: str) -> int:
        """Handle vocabulary testing against SRS system."""
        try:
            from srs_database import SRSDatabase
            from srs_llm_enforcer import create_llm_enforcer
            from llm_mock import MockLLM
            import json

            # Initialize SRS system
            db = SRSDatabase()
            llm = MockLLM()  # We don't actually need LLM responses, just the enforcer
            enforcer = create_llm_enforcer(llm, db)

            vocabulary_terms = []

            # Parse vocabulary terms from different sources
            if test_words:
                vocabulary_terms = [term.strip() for term in test_words.split(',')]
                print(f"\n=== SRS Vocabulary Test ===")
                print(f"Testing {len(vocabulary_terms)} terms from command line")
            elif test_json:
                try:
                    with open(test_json, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    
                    vocabulary_terms = self._extract_vocabulary_from_json(json_data, category)
                    print(f"\n=== SRS Vocabulary Test ===")
                    print(f"Testing {len(vocabulary_terms)} terms from {test_json}")
                    if category:
                        print(f"Category filter: {category}")
                        
                except FileNotFoundError:
                    print(f"Error: JSON file '{test_json}' not found", file=sys.stderr)
                    return 1
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON file: {e}", file=sys.stderr)
                    return 1

            if not vocabulary_terms:
                print("No vocabulary terms to test", file=sys.stderr)
                return 1

            # Test each term against SRS system
            matches_found = []
            no_matches = []

            for term in vocabulary_terms:
                # Create analysis format that the enforcer expects
                analysis = [{"english": term, "srs_queries": [term.lower(), term]}]
                
                # Query SRS with the term
                replacements = enforcer._query_srs_with_analysis(analysis)
                
                if replacements and term in replacements:
                    filipino_equivalent = replacements[term]
                    matches_found.append({
                        'english': term,
                        'filipino': filipino_equivalent,
                        'stability': 'unknown',  # Method doesn't return stability info
                        'method': 'srs_query'
                    })
                else:
                    no_matches.append(term)

            # Display results in familiar format
            if matches_found:
                print(f"\n✅ Matches Found ({len(matches_found)}):")
                for i, match in enumerate(matches_found, 1):
                    stability = match['stability']
                    if isinstance(stability, (int, float)):
                        stability_str = f"stability: {stability:.1f}"
                    else:
                        stability_str = f"stability: {stability}"
                    print(f"    {i}. '{match['english']}' → '{match['filipino']}' ({stability_str})")

            if no_matches:
                print(f"\n❌ No Matches ({len(no_matches)}):")
                for i, term in enumerate(no_matches, 1):
                    print(f"    {i}. '{term}' - No SRS equivalent found")

            # Summary
            total_terms = len(vocabulary_terms)
            success_count = len(matches_found)
            success_rate = (success_count / total_terms * 100) if total_terms > 0 else 0

            print(f"\n📊 Success Rate: {success_rate:.0f}% ({success_count}/{total_terms} terms would be enforced)")

            return 0

        except Exception as e:
            print(f"Error in vocabulary testing: {e}", file=sys.stderr)
            if 'pytest' not in sys.modules:
                import traceback
                traceback.print_exc()
            return 1

    def _handle_translate(self, args: argparse.Namespace) -> int:
        """Handle the translate command and route to subcommands."""
        from cli.translation_commands import handle_translate
        return handle_translate(args)

    def _extract_vocabulary_from_json(self, json_data: dict, category_filter: str) -> list:
        """Extract vocabulary terms from JSON validation data."""
        terms = []
        
        # Navigate the JSON structure based on the format you provided
        if 'priority_classification' in json_data:
            priority_class = json_data['priority_classification']
            
            # If category filter specified, only process that category
            if category_filter and category_filter in priority_class:
                categories = {category_filter: priority_class[category_filter]}
            else:
                categories = priority_class
            
            # Extract terms from each category
            for category_name, category_data in categories.items():
                if isinstance(category_data, dict):
                    for term_key, term_data in category_data.items():
                        # Convert underscores back to spaces for testing
                        term = term_key.replace('_', ' ')
                        terms.append(term)
        
        return terms
    
    def _display_vocabulary_analysis(self, report: Dict[str, Any]) -> None:
        """Display formatted vocabulary analysis report."""
        print(f"Story file: {report['story_file']}")
        print(f"Total vocabulary: {report['total_vocabulary']} words")
        
        # Show recognition state distribution
        distribution = report['recognition_state_distribution']
        print(f"\n📊 Recognition State Distribution:")
        for state, count in distribution.items():
            if count > 0:
                percentage = (count / report['total_vocabulary']) * 100
                print(f"  {state.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
        
        # Show effectiveness metrics
        metrics = report['srs_effectiveness_metrics']
        print(f"\n⚡ SRS Effectiveness Metrics:")
        for metric, value in metrics.items():
            formatted_metric = metric.replace('_', ' ').title()
            print(f"  {formatted_metric}: {value}")
        
        # Show sample vocabulary by state
        print(f"\n📝 Sample Vocabulary by Recognition State:")
        analyses = report['vocabulary_analyses']
        states_shown = set()
        
        for analysis in analyses[:20]:  # Limit to first 20 for readability
            state = analysis['recognition_state']
            if state not in states_shown:
                formatted_state = state.replace('_', ' ').title()
                print(f"  {formatted_state}: {analysis['word']}")
                states_shown.add(state)
                if len(states_shown) >= 6:  # Show max 6 different states
                    break
    
    def _handle_template_generation(self, template_type: str) -> int:
        """Handle validation template generation."""
        try:
            from validation_schema import generate_validation_template, generate_simple_validation_template
            
            if template_type == "simple":
                template = generate_simple_validation_template()
            else:  # comprehensive
                template = generate_validation_template()
            
            print(template)
            return 0
            
        except Exception as e:
            print(f"Error generating template: {e}", file=sys.stderr)
            return 1
    
    def _display_validation_results(self, results: Dict[str, Any]) -> None:
        """Display formatted validation results."""
        summary = results['validation_summary']
        detailed = results['detailed_results']
        quality = results['data_quality_report']
        
        # Display summary metrics
        print(f"\n📊 VALIDATION SUMMARY:")
        print(f"  Total Expected: {summary['total_expected']}")
        print(f"  Total Found in Analysis: {summary['total_actual']}")
        print(f"  Matches: {summary['matches']} ({summary['match_percentage']}%)")
        print(f"  Mismatches: {summary['mismatches']}")
        print(f"  Missing from Actual: {summary['missing_from_actual']}")
        print(f"  Coverage: {summary['coverage_percentage']}%")
        
        # Display data quality
        print(f"\n🔍 DATA QUALITY REPORT:")
        print(f"  Validation Confidence: {quality['validation_confidence']:.1f}%")
        print(f"  Error Tolerance: {quality['error_tolerance']}")
        
        if quality['parsing_warnings']:
            print(f"\n⚠️ PARSING WARNINGS ({len(quality['parsing_warnings'])}):")
            for warning in quality['parsing_warnings'][:5]:  # Show first 5
                print(f"  • {warning}")
            if len(quality['parsing_warnings']) > 5:
                print(f"  ... and {len(quality['parsing_warnings']) - 5} more")
        
        # Show matches (sample)
        if detailed['matches']:
            print(f"\n✅ MATCHES (sample):")
            for match in detailed['matches'][:5]:
                print(f"  ✓ {match['word']} → {match['actual']}")
        
        # Show mismatches  
        if detailed['mismatches']:
            print(f"\n❌ MISMATCHES ({len(detailed['mismatches'])}):")
            for mismatch in detailed['mismatches'][:10]:
                print(f"  ✗ {mismatch['word']}: expected '{mismatch['expected']}', got '{mismatch['actual']}'")
        
        # Show missing words
        if detailed['missing_from_actual']:
            print(f"\n🔍 MISSING FROM ANALYSIS ({len(detailed['missing_from_actual'])}):")
            for missing in detailed['missing_from_actual'][:10]:
                print(f"  ? {missing['word']} (expected: {missing['expected']})")
        
        # Show unexpected words (sample)
        if detailed['unexpected_in_actual']:
            print(f"\n🆕 UNEXPECTED IN ANALYSIS ({len(detailed['unexpected_in_actual'])}, showing sample):")
            for unexpected in detailed['unexpected_in_actual'][:5]:
                print(f"  + {unexpected['word']} → {unexpected['actual']}")
        
        # Performance assessment
        if summary['match_percentage'] >= 80:
            print(f"\n🎯 PERFORMANCE: Excellent ({summary['match_percentage']}% match)")
        elif summary['match_percentage'] >= 60:
            print(f"\n📊 PERFORMANCE: Good ({summary['match_percentage']}% match)")
        else:
            print(f"\n⚠️ PERFORMANCE: Needs improvement ({summary['match_percentage']}% match)")
        
        # Show performance summary
        if summary['match_percentage'] < 50:
            print(f"\n💡 IMPROVEMENT SUGGESTIONS:")
            print(f"  • Review story extraction patterns for missing words")
            print(f"  • Check SRS database for expected vocabulary")
            print(f"  • Verify recognition state categorization logic")
    
    def _reconstruct_pre_enforcement_content(self, violations) -> str:
        """Reconstruct original content before SRS enforcement was applied."""
        try:
            # Read the current (post-enforcement) story file
            from pathlib import Path
            story_dir = Path("instance/data/stories")
            
            # Get day from violations context or use current day
            day_num = 16  # Default fallback
            if violations:
                # Try to extract day from context names
                for violation in violations:
                    context = violation[4]  # context is at index 4
                    if 'day' in context.lower():
                        import re
                        match = re.search(r'day(\d+)', context.lower())
                        if match:
                            day_num = int(match.group(1))
                            break
            
            # Find the story file for this day
            day_patterns = [
                f"story_day{day_num}_*.txt",
                f"*day{day_num}*.txt"
            ]
            
            current_content = None
            for pattern in day_patterns:
                matches = list(story_dir.glob(pattern))
                if matches:
                    with open(matches[0], 'r', encoding='utf-8') as f:
                        current_content = f.read()
                    break
            
            if not current_content:
                return None
            
            # Apply reverse transformations based on violations
            pre_enforcement_content = current_content
            
            # Group violations by context to process in order
            violations_by_context = {}
            for violation in violations:
                english, filipino, v_type, was_replaced, context, created_at = violation
                if was_replaced:  # Only process actual replacements
                    if context not in violations_by_context:
                        violations_by_context[context] = []
                    violations_by_context[context].append((filipino, english))
            
            # Apply reverse transformations (Filipino back to English)
            for context, replacements in violations_by_context.items():
                print(f"  🔄 Reversing {len(replacements)} replacements from {context}")
                for filipino, english in replacements:
                    # Replace Filipino words back with English
                    pre_enforcement_content = pre_enforcement_content.replace(filipino, english)
            
            return pre_enforcement_content
            
        except Exception as e:
            print(f"Error reconstructing content: {e}")
            return None
    
    def run(self) -> int:
        """Run the CLI application."""
        try:
            args = self.parser.parse_args()
            
            # Handle help flag
            if hasattr(args, 'help') and args.help:
                self.parser.print_help()
                return 0
            
            # Handle subparser commands (like srs, extract-vocab, test-enforcement)
            if hasattr(args, 'func'):
                result = args.func(args)
                # If function returns an int, use it as exit code; otherwise default to 0
                return result if isinstance(result, int) else 0
            
            # Handle regular commands
            if hasattr(args, 'command') and args.command in self.commands:
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
        """Clear cache entries for a specific day's story generation AND SRS enforcement."""
        cleared_count = 0
        
        # For day-specific clearing, we need to find cache files that contain
        # references to this specific day in their prompts
        import json
        
        try:
            # Check all cache files for day-specific prompts
            for cache_file in cache_dir.glob('*.json'):
                try:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    # Check if this cache file contains prompts for the specified day
                    if self._cache_file_contains_day(cache_data, day):
                        cache_file.unlink()
                        cleared_count += 1
                        print(f"🗑️ Cleared cache file: {cache_file.name}")
                        
                except (json.JSONDecodeError, KeyError, OSError):
                    # Skip corrupted or inaccessible cache files
                    continue
                    
        except Exception as e:
            print(f"⚠️ Warning: Error during day-specific cache clearing: {e}", file=sys.stderr)
            
        return cleared_count
    
    def _cache_file_contains_day(self, cache_data: dict, day: int) -> bool:
        """Check if a cache file contains prompts related to the specified day."""
        try:
            # Check for user_prompt field (newer cache format)
            if 'user_prompt' in cache_data:
                prompt = cache_data['user_prompt']
                
                # Direct day references
                day_patterns = [
                    f"Day {day}",
                    f"day {day}",
                    f"for Day {day}",
                    f"content for Day {day}",
                    f"content for day {day}",
                    f"Day {day}:",
                    f"day {day}:"
                ]
                
                if any(pattern in prompt for pattern in day_patterns):
                    return True
                
                # For strategy-based generation, check if this might be for our target day
                # Since strategy prompts don't always contain explicit day numbers,
                # we'll be more aggressive and clear recent strategy caches when clearing day-specific cache
                strategy_indicators = [
                    "DEEPER Strategy Content Generation Request",
                    "WIDER Strategy Content Generation Request",
                    "Enhanced Filipino authenticity",
                    "Enhanced Language Complexity"
                ]
                
                if any(indicator in prompt for indicator in strategy_indicators):
                    # This looks like a strategy-based cache that might be for our target day
                    # Be aggressive and clear it
                    return True
                
                # Also clear test/debug caches that might interfere
                test_patterns = [
                    "Test user prompt",
                    "Test system prompt", 
                    "debug",
                    "Debug"
                ]
                
                if any(pattern in prompt for pattern in test_patterns):
                    return True
            
            # Check older cache format (direct response format)
            if 'choices' in cache_data:
                choices = cache_data.get('choices', [])
                for choice in choices:
                    if isinstance(choice, dict) and 'message' in choice:
                        content = choice['message'].get('content', '')
                        day_patterns = [
                            f"Day {day}",
                            f"day {day}"
                        ]
                        if any(pattern in content for pattern in day_patterns):
                            return True
                            
                # Also clear empty responses that might be from failed interactive attempts
                if choices and len(choices) == 1:
                    choice = choices[0]
                    if isinstance(choice, dict) and 'message' in choice:
                        content = choice['message'].get('content', '').strip()
                        if not content:  # Empty response
                            return True
                            
        except (KeyError, TypeError):
            pass
            
        return False
        
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
