"""
Constraint enforcement testing CLI commands.
"""
import argparse
import json
from typing import Dict, List, Any, Optional

from srs_database import SRSDatabase
from srs_enforcer import SRSEnforcer
from srs_llm_enforcer import create_llm_enforcer
from llm_mock import MockLLM
from .utils import (
    print_success, print_warning, print_error, print_info,
    get_story_files, extract_day_number
)


def add_enforcement_commands(subparsers) -> None:
    """Add constraint enforcement testing commands to the CLI parser."""
    
    # test-enforcement command
    test_parser = subparsers.add_parser(
        'test-enforcement',
        help='Test constraint enforcement on text',
        description='Test SRS constraint enforcement on sample text or story content'
    )
    
    # Input specification (mutually exclusive)
    input_group = test_parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('text', nargs='?',
                            help='Text to test enforcement on')
    input_group.add_argument('--day', type=int,
                            help='Test enforcement on specific day\'s content')
    
    # Options
    test_parser.add_argument('--show-details', action='store_true',
                            help='Show detailed replacement information')
    test_parser.add_argument('--method', choices=['constraint', 'llm', 'both'], 
                            default='both',
                            help='Enforcement method to test (default: both)')
    test_parser.add_argument('--context', type=str, default='cli_test',
                            help='Context for enforcement (default: cli_test)')
    
    test_parser.set_defaults(func=handle_test_enforcement)
    
    # show-enforcement command
    show_parser = subparsers.add_parser(
        'show-enforcement',
        help='Show current enforcement rules',
        description='Display current constraint enforcement mappings and statistics'
    )
    
    show_parser.add_argument('--format', choices=['table', 'json'], default='table',
                            help='Output format (default: table)')
    show_parser.add_argument('--filter', type=str,
                            help='Filter rules by substring')
    show_parser.add_argument('--stats', action='store_true',
                            help='Show enforcement statistics')
    
    show_parser.set_defaults(func=handle_show_enforcement)


def handle_test_enforcement(args) -> None:
    """Handle constraint enforcement testing."""
    print_info("Testing constraint enforcement...")
    
    try:
        # Get test text
        if args.text:
            test_text = args.text
            print_info(f"Testing on provided text: '{test_text}'")
        else:
            test_text = _get_day_content(args.day)
            if not test_text:
                print_error(f"Could not load content for day {args.day}")
                return
            print_info(f"Testing on day {args.day} content ({len(test_text)} characters)")
        
        # Initialize enforcement components
        db = SRSDatabase()
        
        results = {}
        
        # Test constraint enforcement
        if args.method in ['constraint', 'both']:
            results['constraint'] = _test_constraint_enforcement(db, test_text, args)
        
        # Test LLM enforcement
        if args.method in ['llm', 'both']:
            results['llm'] = _test_llm_enforcement(db, test_text, args)
        
        # Display results
        _display_enforcement_results(results, test_text, args)
        
    except Exception as e:
        print_error(f"Error during enforcement testing: {e}")


def handle_show_enforcement(args) -> None:
    """Handle showing enforcement rules."""
    try:
        db = SRSDatabase()
        enforcer = SRSEnforcer(db)
        
        # Get enforcement rules
        rules = enforcer.replacement_dict
        
        if args.filter:
            rules = {k: v for k, v in rules.items() 
                    if args.filter.lower() in k.lower() or args.filter.lower() in v.lower()}
        
        if args.format == 'json':
            print(json.dumps(rules, indent=2, ensure_ascii=False))
        else:
            _display_rules_table(rules)
        
        if args.stats:
            _display_enforcement_stats(rules, db)
            
    except Exception as e:
        print_error(f"Error showing enforcement rules: {e}")


def _get_day_content(day: int) -> Optional[str]:
    """Get content from specific day's story file."""
    story_files = get_story_files()
    
    for story_file in story_files:
        if extract_day_number(story_file) == day:
            try:
                with open(story_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print_warning(f"Error reading {story_file.name}: {e}")
                return None
    
    return None


def _test_constraint_enforcement(db: SRSDatabase, test_text: str, args) -> Dict[str, Any]:
    """Test constraint-based enforcement."""
    enforcer = SRSEnforcer(db)
    
    try:
        # Apply constraint enforcement
        enforced_text, violations = enforcer.enforce_constraints(test_text, context=args.context)
        
        return {
            'success': True,
            'original_text': test_text,
            'enforced_text': enforced_text,
            'violations': violations,
            'replacement_count': len(violations),
            'method': 'constraint'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'method': 'constraint'
        }


def _test_llm_enforcement(db: SRSDatabase, test_text: str, args) -> Dict[str, Any]:
    """Test LLM-based enforcement."""
    try:
        llm = MockLLM()
        llm_enforcer = create_llm_enforcer(llm, db)
        
        # Apply LLM enforcement
        enforced_text, violations, phrase_translations = llm_enforcer.enforce_with_llm(
            content=test_text,
            day=args.day if hasattr(args, 'day') and args.day else 1,
            context=args.context
        )
        
        return {
            'success': True,
            'original_text': test_text,
            'enforced_text': enforced_text,
            'violations': violations,
            'replacement_count': len(violations),
            'method': 'llm'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'method': 'llm'
        }


def _display_enforcement_results(results: Dict[str, Dict[str, Any]], original_text: str, args) -> None:
    """Display enforcement test results."""
    print("\n" + "=" * 60)
    print("CONSTRAINT ENFORCEMENT TEST RESULTS")
    print("=" * 60)
    
    for method, result in results.items():
        print(f"\n{method.upper()} ENFORCEMENT:")
        print("-" * 30)
        
        if not result['success']:
            print_error(f"Failed: {result['error']}")
            continue
        
        replacement_count = result['replacement_count']
        if replacement_count == 0:
            print_info("No replacements made")
        else:
            print_success(f"{replacement_count} replacements made")
        
        if args.show_details and replacement_count > 0:
            print("\nReplacements:")
            violations = result['violations']
            for i, violation in enumerate(violations[:10], 1):  # Show first 10
                english = violation.get('english', violation.get('original', 'unknown'))
                filipino = violation.get('filipino', violation.get('replacement', 'unknown'))
                count = violation.get('count', 1)
                print(f"  {i:2d}. '{english}' → '{filipino}' ({count}x)")
            
            if len(violations) > 10:
                print(f"  ... and {len(violations) - 10} more")
        
        if args.show_details:
            print(f"\nOriginal length: {len(original_text)} characters")
            print(f"Enforced length: {len(result['enforced_text'])} characters")
            
            # Show a sample of the enforced text
            enforced_sample = result['enforced_text'][:200]
            if len(result['enforced_text']) > 200:
                enforced_sample += "..."
            print(f"\nEnforced text sample:\n{enforced_sample}")


def _display_rules_table(rules: Dict[str, str]) -> None:
    """Display enforcement rules as a formatted table."""
    print("\n" + "=" * 70)
    print("CONSTRAINT ENFORCEMENT RULES")
    print("=" * 70)
    print(f"{'English':<25} {'Filipino':<25} {'Length':<10}")
    print("-" * 70)
    
    for english, filipino in sorted(rules.items()):
        english_display = english[:22] + "..." if len(english) > 25 else english
        filipino_display = filipino[:22] + "..." if len(filipino) > 25 else filipino
        length_diff = len(filipino) - len(english)
        length_str = f"{length_diff:+d}" if length_diff != 0 else "="
        
        print(f"{english_display:<25} {filipino_display:<25} {length_str:<10}")
    
    print("-" * 70)
    print(f"Total rules: {len(rules)}")


def _display_enforcement_stats(rules: Dict[str, str], db: SRSDatabase) -> None:
    """Display enforcement statistics."""
    print("\n" + "=" * 50)
    print("ENFORCEMENT STATISTICS")
    print("=" * 50)
    
    # Basic rule stats
    total_rules = len(rules)
    avg_english_length = sum(len(k) for k in rules.keys()) / total_rules if total_rules > 0 else 0
    avg_filipino_length = sum(len(v) for v in rules.values()) / total_rules if total_rules > 0 else 0
    
    print(f"Total enforcement rules: {total_rules}")
    print(f"Average English length: {avg_english_length:.1f} characters")
    print(f"Average Filipino length: {avg_filipino_length:.1f} characters")
    
    # Check database coverage
    all_collocations = db.get_all_collocations()
    db_filipino_words = {colloc['text'] for colloc in all_collocations}
    
    # Count how many enforcement Filipino words are in database
    covered_count = sum(1 for filipino in rules.values() if filipino in db_filipino_words)
    coverage_percentage = (covered_count / total_rules * 100) if total_rules > 0 else 0
    
    print(f"Database coverage: {covered_count}/{total_rules} ({coverage_percentage:.1f}%)")
    
    # Show uncovered enforcement rules
    uncovered_rules = [
        (eng, fil) for eng, fil in rules.items() 
        if fil not in db_filipino_words
    ]
    
    if uncovered_rules and len(uncovered_rules) <= 5:
        print("\nUncovered enforcement rules:")
        for eng, fil in uncovered_rules:
            print(f"  '{eng}' → '{fil}' (not in database)")
    elif len(uncovered_rules) > 5:
        print(f"\n{len(uncovered_rules)} enforcement rules not covered by database")
    
    print("=" * 50)