"""
SRS database management CLI commands.
"""
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from srs_database import SRSDatabase
from enhanced_srs_database import EnhancedSRSDatabase
# SRSTracker removed - using SRSDatabase directly
# from collocation_extractor import CollocationExtractor  # Removed - using LLM-based extraction
from story_collocation_extractor import StoryCollocationExtractor
from .utils import (
    print_success, print_warning, print_error, print_info,
    format_stats_table, confirm_action, get_story_files,
    extract_day_number, show_progress
)


def add_srs_commands(subparsers) -> None:
    """Add SRS management commands to the CLI parser."""
    srs_parser = subparsers.add_parser(
        'srs', 
        help='SRS database management commands',
        description='Manage the SRS (Spaced Repetition System) vocabulary database'
    )
    
    srs_subparsers = srs_parser.add_subparsers(dest='srs_action', help='SRS actions')
    
    # srs populate command (merged from extract-vocab)
    populate_parser = srs_subparsers.add_parser(
        'populate',
        help='Populate database from story content'
    )
    populate_group = populate_parser.add_mutually_exclusive_group(required=True)
    populate_group.add_argument('--all-stories', action='store_true',
                               help='Populate from all story files')
    populate_group.add_argument('--day', type=int,
                               help='Populate from specific day')
    populate_group.add_argument('--days', type=str,
                               help='Populate from day range (e.g., "1-17" or "1,3,5")')

    # Action options (preview or save)
    populate_parser.add_argument('--preview', action='store_true',
                                help='Preview extraction without saving (replaces --dry-run)')
    populate_parser.add_argument('--dry-run', action='store_true',
                                help='Show what would be done without making changes (deprecated, use --preview)')
    populate_parser.add_argument('--clean-first', action='store_true',
                                help='Clean database before populating')
    populate_parser.add_argument('--overwrite', action='store_true',
                                help='Overwrite existing entries')
    populate_parser.add_argument('--filter-noise', action='store_true', default=True,
                                help='Filter out voice tags and noise (default: True)')
    populate_parser.add_argument('--limit', type=int, default=20,
                                help='Limit number of collocations shown in preview (default: 20)')
    populate_parser.add_argument('--force', action='store_true',
                                help='Skip confirmation prompts')
    
    # srs stats command
    stats_parser = srs_subparsers.add_parser(
        'stats',
        help='Show database statistics'
    )
    stats_parser.add_argument('--detailed', action='store_true',
                             help='Show detailed statistics')
    stats_parser.add_argument('--export-csv', type=str,
                             help='Export statistics to CSV file')
    
    # srs status command
    status_parser = srs_subparsers.add_parser(
        'status',
        help='Show SRS collocation status'
    )
    status_group = status_parser.add_mutually_exclusive_group()
    status_group.add_argument('--all', action='store_true',
                             help='Show all collocations in database')
    status_group.add_argument('--day', type=int,
                             help='Show collocations due for specific day')
    status_group.add_argument('--due-only', action='store_true',
                             help='Show only collocations due for review')
    status_group.add_argument('--count', action='store_true',
                             help='Show summary statistics only')
    
    # srs clean command  
    clean_parser = srs_subparsers.add_parser(
        'clean',
        help='Clean corrupted vocabulary entries'
    )
    clean_parser.add_argument('--dry-run', action='store_true',
                             help='Show what would be cleaned without making changes')
    clean_parser.add_argument('--backup', action='store_true',
                             help='Create backup before cleaning')
    
    # srs translations command
    translations_parser = srs_subparsers.add_parser(
        'translations',
        help='Show translation coverage and status'
    )
    translations_parser.add_argument('--detailed', action='store_true',
                                   help='Show detailed translation information')
    translations_parser.add_argument('--coverage', action='store_true',
                                   help='Show coverage statistics only')
    translations_parser.add_argument('--untranslated', action='store_true',
                                   help='Show untranslated frequent items')
    translations_parser.add_argument('--samples', type=int, default=5,
                                   help='Number of sample translations to show (default: 5)')
    
    # Set command handlers
    srs_parser.set_defaults(func=handle_srs_command)


def handle_srs_command(args) -> int:
    """Handle SRS command routing."""
    if args.srs_action == 'populate':
        return handle_populate_command(args)
    elif args.srs_action == 'stats':
        return handle_stats_command(args)
    elif args.srs_action == 'status':
        return handle_status_command(args)
    elif args.srs_action == 'clean':
        return handle_clean_command(args)
    elif args.srs_action == 'translations':
        return handle_translations_command(args)
    else:
        print_error("Unknown SRS action. Use --help for available commands.")
        return 1


def handle_populate_command(args) -> int:
    """Handle database population command."""
    # Handle --dry-run as alias for --preview
    is_preview = args.preview or args.dry_run

    if is_preview:
        print_info("Preview mode: extraction without saving...")
    else:
        print_info("Starting SRS database population...")

    try:
        # Initialize components
        db = SRSDatabase()
        extractor = StoryCollocationExtractor()

        if args.clean_first:
            if is_preview:
                print_info("PREVIEW: Would clean database first")
            else:
                if args.force or confirm_action("Clean database before populating?"):
                    _clean_database(db)

        # Parse day specification
        if args.all_stories:
            _populate_from_all_stories(db, extractor, args, is_preview)
        elif hasattr(args, 'days') and args.days is not None:
            # Handle day range (e.g., "1-17" or "1,3,5")
            target_days = _parse_day_specification(args.days)
            if not target_days:
                print_error("Invalid day specification")
                return 1
            _populate_from_multiple_days(db, extractor, target_days, args, is_preview)
        elif hasattr(args, 'day') and args.day is not None:
            _populate_from_day(db, extractor, args.day, args, is_preview)
        else:
            print_error("Must specify --day, --days, or --all-stories")
            return 1

        if not is_preview:
            print_success("Database population completed!")
        else:
            print_info("PREVIEW completed - no changes made")

        return 0

    except Exception as e:
        print_error(f"Error during population: {e}")
        return 1


def handle_stats_command(args) -> None:
    """Handle database statistics command."""
    try:
        db = SRSDatabase()
        stats = _get_database_stats(db, detailed=args.detailed)
        
        print(format_stats_table(stats))
        
        if args.export_csv:
            _export_stats_csv(stats, args.export_csv)
            print_success(f"Statistics exported to {args.export_csv}")
            
    except Exception as e:
        print_error(f"Error getting statistics: {e}")


def handle_status_command(args) -> int:
    """Handle SRS status display command."""
    try:
        db = SRSDatabase()
        enhanced_db = EnhancedSRSDatabase()
        
        if args.all:
            # Show all collocations
            collocations = db.get_all_collocations()
            print(f"\n=== All SRS Collocations ({len(collocations)}) ===")
            
            if not collocations:
                print("  No collocations found in database.")
                print("  Use 'srs populate --all-stories' to populate from existing stories.")
                return
            
            for colloc in collocations:
                next_review = "Never" if colloc['next_review_day'] is None else f"Day {colloc['next_review_day']}"
                
                # Try to find translation pair
                translation = enhanced_db.find_english_equivalent(colloc['text'])
                if translation:
                    print(f"  • {colloc['text']} → {translation}")
                else:
                    print(f"  • {colloc['text']}")
                print(f"    Stability: {colloc['stability']:.2f}, Next review: {next_review}")
                
        elif args.day is not None:
            # Show collocations for specific day
            day = args.day
            
            # Validate day parameter
            if day < 1:
                print_error(f"Day must be a positive integer (≥ 1), got {day}")
                return 1
            
            due_collocations = db.get_due_collocations(day)
            
            print(f"\n=== SRS Status for Day {day} ===")
            print(f"Due for review: {len(due_collocations)} collocations")
            
            if due_collocations:
                for colloc in due_collocations:
                    # Try to find translation pair
                    translation = enhanced_db.find_english_equivalent(colloc['text'])
                    if translation:
                        print(f"  • {colloc['text']} → {translation}")
                    else:
                        print(f"  • {colloc['text']}")
                    print(f"    Stability: {colloc['stability']:.2f}")
            else:
                print("  No collocations due for review")
                
        elif args.due_only:
            # Show only collocations due for review (use current day 1 as default)
            current_day = 1  # Could be made configurable
            due_collocations = db.get_due_collocations(current_day)
            
            print(f"\n=== Collocations Due for Review ===")
            if due_collocations:
                for colloc in due_collocations:
                    # Try to find translation pair
                    translation = enhanced_db.find_english_equivalent(colloc['text'])
                    if translation:
                        print(f"  • {colloc['text']} → {translation}")
                    else:
                        print(f"  • {colloc['text']}")
                    print(f"    Due since day: {colloc['next_review_day']}")
            else:
                print("  No collocations currently due for review")
                
        elif args.count:
            # Show summary statistics only
            total_collocations = db.get_collocations_count()
            current_day = 1  # Default, could be made configurable
            due_collocations = db.get_due_collocations(current_day)
            
            print(f"\n=== SRS Summary ===")
            print(f"Total collocations tracked: {total_collocations}")
            print(f"Due for review: {len(due_collocations)}")
            
            if total_collocations > 0:
                all_collocations = db.get_all_collocations()
                avg_stability = sum(c['stability'] for c in all_collocations) / total_collocations
                print(f"Average stability: {avg_stability:.2f}")
            else:
                print("Average stability: N/A")
                
        else:
            # Default: show summary if no specific option provided
            total_collocations = db.get_collocations_count()
            current_day = 1  # Default, could be made configurable
            due_collocations = db.get_due_collocations(current_day)
            
            print(f"\n=== SRS Summary ===")
            print(f"Total collocations tracked: {total_collocations}")
            print(f"Due for review: {len(due_collocations)}")
            
            if total_collocations > 0:
                all_collocations = db.get_all_collocations()
                avg_stability = sum(c['stability'] for c in all_collocations) / total_collocations
                print(f"Average stability: {avg_stability:.2f}")
            else:
                print("Average stability: N/A")
                print("Use 'srs populate --all-stories' to populate from existing stories.")
        
        return 0
        
    except Exception as e:
        print_error(f"Error showing SRS status: {e}")
        import sys
        if 'pytest' not in sys.modules:
            import traceback
            traceback.print_exc()
        return 1


def handle_clean_command(args) -> None:
    """Handle database cleaning command."""
    try:
        db = SRSDatabase()
        
        if args.backup and not args.dry_run:
            _backup_database(db)
            print_success("Database backup created")
        
        corrupted_entries = _identify_corrupted_entries(db)
        
        if not corrupted_entries:
            print_success("No corrupted entries found!")
            return
        
        print_info(f"Found {len(corrupted_entries)} corrupted entries:")
        for entry in corrupted_entries[:10]:  # Show first 10
            print(f"  - '{entry}'")
        if len(corrupted_entries) > 10:
            print(f"  ... and {len(corrupted_entries) - 10} more")
        
        if args.dry_run:
            print_info("DRY RUN: Would remove these corrupted entries")
        else:
            if confirm_action(f"Remove {len(corrupted_entries)} corrupted entries?"):
                _remove_corrupted_entries(db, corrupted_entries)
                print_success(f"Removed {len(corrupted_entries)} corrupted entries")
            
    except Exception as e:
        print_error(f"Error during cleaning: {e}")


def handle_translations_command(args) -> None:
    """Handle translation status and coverage command."""
    try:
        # Initialize databases
        srs_db = SRSDatabase()
        enhanced_db = EnhancedSRSDatabase()
        
        # Get core statistics
        enhanced_stats = enhanced_db.get_stats()
        total_pairs = enhanced_stats['active_translation_pairs']
        avg_confidence = enhanced_stats['average_translation_confidence']
        
        # Get SRS collocation data
        all_collocations = srs_db.get_all_collocations()
        frequent_collocations = srs_db.get_collocations_ready_for_translation()
        untranslated_frequent = srs_db.get_untranslated_frequent_collocations()
        
        # Calculate coverage
        frequent_count = len(frequent_collocations)
        untranslated_count = len(untranslated_frequent)
        translated_frequent = frequent_count - untranslated_count
        
        if args.coverage:
            # Show coverage statistics only
            print(f"\n=== SRS Translation Coverage ===")
            print(f"Total translation pairs: {total_pairs:,}")
            print(f"Frequent collocations (≥3): {frequent_count:,}")
            print(f"Translated frequent items: {translated_frequent:,}")
            print(f"Untranslated frequent items: {untranslated_count:,}")
            
            if frequent_count > 0:
                coverage_pct = (translated_frequent / frequent_count) * 100
                print(f"Frequent translation coverage: {coverage_pct:.1f}%")
            
            return
        
        if args.untranslated:
            # Show untranslated frequent items
            print(f"\n=== Untranslated Frequent Items ({untranslated_count}) ===")
            
            if untranslated_count == 0:
                print_success("🎉 All frequent collocations have translations!")
                return
                
            # Group by word count for better organization
            by_word_count = {}
            for item in untranslated_frequent:
                word_count = len(item.split())
                if word_count not in by_word_count:
                    by_word_count[word_count] = []
                by_word_count[word_count].append(item)
            
            for word_count in sorted(by_word_count.keys()):
                items = by_word_count[word_count]
                print(f"\n{word_count} word(s) ({len(items)} items):")
                for item in items[:10]:  # Show first 10
                    print(f"  • {item}")
                if len(items) > 10:
                    print(f"  ... and {len(items) - 10} more")
            
            return
        
        # Default: comprehensive status
        print(f"\n=== SRS Translation Status ===")
        print(f"Total translation pairs: {total_pairs:,}")
        print(f"Average confidence: {avg_confidence:.3f}")
        print(f"Database: {enhanced_stats['database_path']}")
        
        print(f"\n=== Collocation Coverage ===")
        print(f"Total SRS collocations: {len(all_collocations):,}")
        print(f"Frequent collocations (≥3): {frequent_count:,}")
        print(f"Translated frequent items: {translated_frequent:,}")
        print(f"Untranslated frequent items: {untranslated_count:,}")
        
        if frequent_count > 0:
            coverage_pct = (translated_frequent / frequent_count) * 100
            print(f"Frequent translation coverage: {coverage_pct:.1f}%")
            
            # Status indicator
            if untranslated_count == 0:
                print_success("Status: ✅ All frequent collocations translated")
            else:
                print_warning(f"Status: ⚠️ {untranslated_count} frequent items need translation")
        
        if args.detailed:
            # Show sample translations
            print(f"\n=== Sample Translations ===")
            translation_pairs = enhanced_db.get_translation_pairs(active_only=True)
            
            if translation_pairs:
                # Show highest confidence translations
                samples = sorted(translation_pairs, key=lambda x: x.confidence, reverse=True)[:args.samples]
                for pair in samples:
                    print(f"  {pair.filipino} → {pair.english} ({pair.confidence:.3f})")
            else:
                print("  No translations found")
                
            # Show database breakdown
            if 'enhanced_collocations' in enhanced_stats:
                print(f"\n=== Database Breakdown ===")
                for language, count in enhanced_stats['enhanced_collocations'].items():
                    print(f"  {language.capitalize()}: {count:,}")
        
        # Action suggestions
        if untranslated_count > 0:
            print(f"\n💡 Suggested Actions:")
            print(f"  • Run: python translate_srs_batch.py --batch-size 300")
            print(f"  • Check: python main.py srs translations --untranslated")
        
    except Exception as e:
        print_error(f"Error showing translation status: {e}")
        import sys
        if 'pytest' not in sys.modules:
            import traceback
            traceback.print_exc()


def _populate_from_all_stories(db: SRSDatabase, extractor: Any, args, is_preview: bool = False) -> None:
    """Populate database from all story files."""
    story_files = get_story_files()

    if not story_files:
        print_error("No story files found!")
        return

    print_info(f"Found {len(story_files)} story files")

    total_added = 0
    processed_files = 0

    for i, story_file in enumerate(story_files):
        show_progress(i, len(story_files), "Processing stories")

        day_num = extract_day_number(story_file)
        added_count = _populate_from_story_file(db, extractor, story_file, day_num, args, is_preview)

        if added_count is not None:
            total_added += added_count
            processed_files += 1

    show_progress(len(story_files), len(story_files), "Processing stories")

    if not is_preview:
        print_success(f"Processed {processed_files} files, added {total_added} collocations")
    else:
        print_info(f"PREVIEW: Would process {processed_files} files, add {total_added} collocations")


def _populate_from_day(db: SRSDatabase, extractor: Any, day: int, args, is_preview: bool = False) -> None:
    """Populate database from specific day."""
    story_files = get_story_files()
    target_file = None

    for story_file in story_files:
        if extract_day_number(story_file) == day:
            target_file = story_file
            break

    if not target_file:
        print_error(f"No story file found for day {day}")
        return

    print_info(f"Processing day {day}: {target_file.name}")

    added_count = _populate_from_story_file(db, extractor, target_file, day, args, is_preview)

    if added_count is not None:
        if not is_preview:
            print_success(f"Added {added_count} collocations from day {day}")
        else:
            print_info(f"PREVIEW: Would add {added_count} collocations from day {day}")


def _populate_from_story_file(db: SRSDatabase, extractor: Any,
                             story_file: Path, day_num: int, args, is_preview: bool = False) -> Optional[int]:
    """Populate database from Natural Speed section of a single story file."""
    try:
        # Read story content
        with open(story_file, 'r', encoding='utf-8') as f:
            story = f.read()

        # Extract Natural Speed content only
        natural_speed_content = _extract_natural_speed_content(story)

        # Skip if no Natural Speed content found
        if not natural_speed_content.strip():
            print_warning(f"No Natural Speed content found in {story_file.name}")
            return 0

        # Extract collocations from Natural Speed content only
        collocations = extractor.extract_collocations(natural_speed_content)

        # Filter noise if requested
        if args.filter_noise:
            collocations = _filter_noisy_collocations(collocations)

        # Preview mode: show collocations with limit
        if is_preview:
            if collocations:
                print_info(f"\nDay {day_num}: {story_file.name}")
                print("-" * 50)
                print_info(f"Extracted {len(collocations)} collocations:")

                # Show limited number for preview
                limit = getattr(args, 'limit', 20)
                display_count = min(len(collocations), limit)
                for i, colloc in enumerate(collocations[:display_count]):
                    print(f"  {i+1:2d}. '{colloc}'")

                if len(collocations) > display_count:
                    print(f"  ... and {len(collocations) - display_count} more")
            return len(collocations)

        # Save mode: Add to database
        added_count = 0
        for colloc in collocations:
            try:
                existing = db.get_collocation(colloc)
                if existing and not args.overwrite:
                    continue  # Skip existing unless overwrite requested

                db.add_collocation(
                    text=colloc,
                    first_seen_day=day_num,
                    last_seen_day=day_num,
                    appearances=[day_num]
                )
                added_count += 1

            except Exception as e:
                # Skip individual collocation errors
                continue

        return added_count

    except Exception as e:
        print_warning(f"Error processing {story_file.name}: {e}")
        return None


def _extract_natural_speed_content(story: str) -> str:
    """Extract only the Natural Speed section content with Filipino dialogue."""
    lines = story.split('\n')

    # Find Natural Speed section
    natural_speed_start = -1
    natural_speed_end = len(lines)

    for i, line in enumerate(lines):
        if '[NARRATOR]: Natural Speed' in line:
            natural_speed_start = i + 1
        elif natural_speed_start != -1 and '[NARRATOR]: Slow Speed' in line:
            natural_speed_end = i
            break

    if natural_speed_start == -1:
        print_warning("No Natural Speed section found in story")
        return ""

    # Extract Filipino dialogue lines only (ignore narrator lines)
    filipino_content = []
    for i in range(natural_speed_start, natural_speed_end):
        if i < len(lines):
            line = lines[i].strip()
            # Only include Tagalog speaker lines, skip narrator descriptions and empty lines
            if line.startswith('[TAGALOG-') and ']:' in line:
                # Extract just the dialogue content after the speaker tag
                dialogue_start = line.find(']:')
                if dialogue_start != -1:
                    dialogue = line[dialogue_start + 2:].strip()
                    if dialogue:  # Only add non-empty dialogue
                        filipino_content.append(dialogue)

    return ' '.join(filipino_content)


def _parse_day_specification(args_or_str) -> List[int]:
    """Parse day specification from arguments or string (e.g., "1-17" or "1,3,5").

    Args:
        args_or_str: Either an argparse.Namespace with 'day'/'days' attrs, or a string

    Returns:
        List of day numbers
    """
    # Handle args object (for backward compatibility)
    if hasattr(args_or_str, 'day') or hasattr(args_or_str, 'days'):
        if hasattr(args_or_str, 'day') and args_or_str.day:
            return [args_or_str.day]
        if hasattr(args_or_str, 'days') and args_or_str.days:
            days_str = args_or_str.days
        else:
            return []
    else:
        # Handle string directly
        days_str = args_or_str

    days = []
    parts = days_str.split(',')

    for part in parts:
        part = part.strip()
        if '-' in part:
            # Range specification (e.g., "1-17")
            start, end = part.split('-', 1)
            try:
                start_day = int(start.strip())
                end_day = int(end.strip())
                days.extend(range(start_day, end_day + 1))
            except ValueError:
                print_error(f"Invalid day range: {part}")
                return []
        else:
            # Single day
            try:
                days.append(int(part))
            except ValueError:
                print_error(f"Invalid day number: {part}")
                return []

    return sorted(list(set(days)))  # Remove duplicates and sort


def _populate_from_multiple_days(db: SRSDatabase, extractor: Any, target_days: List[int], args, is_preview: bool = False) -> None:
    """Populate database from multiple specific days."""
    story_files = get_story_files()

    print_info(f"Processing {len(target_days)} day(s)")

    total_added = 0
    processed_days = 0

    for i, day in enumerate(target_days):
        show_progress(i, len(target_days), f"Processing day {day}")

        target_file = None
        for story_file in story_files:
            if extract_day_number(story_file) == day:
                target_file = story_file
                break

        if not target_file:
            print_warning(f"No story file found for day {day}")
            continue

        added_count = _populate_from_story_file(db, extractor, target_file, day, args, is_preview)

        if added_count is not None:
            total_added += added_count
            processed_days += 1

    show_progress(len(target_days), len(target_days), "Processing")

    if not is_preview:
        print_success(f"Processed {processed_days} days, added {total_added} collocations")
    else:
        print_info(f"PREVIEW: Would process {processed_days} days, add {total_added} collocations")


def _filter_noisy_collocations(collocations: List[str]) -> List[str]:
    """Filter out noisy/invalid collocations."""
    clean_collocations = []

    for colloc in collocations:
        # Skip obvious noise
        if (len(colloc) <= 2 or
            colloc.startswith('[') or
            colloc.startswith('tagalog') or
            'narrator' in colloc.lower() or
            colloc.startswith('-') or
            colloc.count('\n') > 0):
            continue

        # Skip pure numbers or single letters
        if colloc.isdigit() or (len(colloc) == 1 and colloc.isalpha()):
            continue

        # Skip pure English words that are too common
        common_english = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had',
            'it', 'this', 'that', 'these', 'those', 'here', 'there', 'you', 'me'
        }
        if colloc.lower() in common_english:
            continue

        clean_collocations.append(colloc)

    return clean_collocations


def _get_database_stats(db: SRSDatabase, detailed: bool = False) -> Dict[str, Any]:
    """Get database statistics."""
    all_collocations = db.get_all_collocations()
    
    stats = {
        'total_collocations': len(all_collocations),
        'database_file': str(db.db_path),
        'database_exists': db.db_path.exists(),
    }
    
    if detailed and all_collocations:
        # Calculate additional detailed stats
        review_counts = [c.get('review_count', 0) for c in all_collocations]
        days = [c.get('first_seen_day', 1) for c in all_collocations]
        
        stats.update({
            'avg_review_count': sum(review_counts) / len(review_counts),
            'max_review_count': max(review_counts),
            'min_day': min(days),
            'max_day': max(days),
            'unreviewed_count': sum(1 for r in review_counts if r == 0),
        })
    
    return stats


def _export_stats_csv(stats: Dict[str, Any], filename: str) -> None:
    """Export statistics to CSV file."""
    import csv
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Metric', 'Value'])
        for key, value in stats.items():
            writer.writerow([key, value])


def _clean_database(db: SRSDatabase) -> None:
    """Clean the database by removing all entries."""
    # This would implement database cleaning logic
    print_info("Database cleaning not yet implemented")


def _backup_database(db: SRSDatabase) -> None:
    """Create a backup of the database."""
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db.db_path.with_suffix(f'.backup_{timestamp}.db')
    
    shutil.copy2(db.db_path, backup_path)
    print_info(f"Database backed up to: {backup_path}")


def _identify_corrupted_entries(db: SRSDatabase) -> List[str]:
    """Identify corrupted entries in the database."""
    all_collocations = db.get_all_collocations()
    corrupted = []
    
    for colloc in all_collocations:
        text = colloc.get('text', '')
        
        # Check for corruption indicators
        if (not text or 
            len(text) <= 1 or
            'tagalog-' in text.lower() or
            '[narrator' in text.lower() or
            '\n' in text or
            text.startswith('-')):
            corrupted.append(text)
    
    return corrupted


def _remove_corrupted_entries(db: SRSDatabase, corrupted_entries: List[str]) -> None:
    """Remove corrupted entries from the database."""
    for entry in corrupted_entries:
        try:
            db.delete_collocation(entry)
        except Exception as e:
            print_warning(f"Could not remove '{entry}': {e}")


# Backward compatibility functions for tests (migrated from vocab_commands)
def _extract_from_file(extractor: Any, story_file: Path, filter_noise: bool) -> List[str]:
    """Extract collocations from a story file.

    DEPRECATED: This function is kept for backward compatibility with tests.
    New code should use _populate_from_story_file instead.
    """
    try:
        with open(story_file, 'r', encoding='utf-8') as f:
            story = f.read()

        # Extract only Natural Speed Filipino dialogue content
        natural_speed_content = _extract_natural_speed_content(story)

        if not natural_speed_content:
            print_warning(f"No Natural Speed content found in {story_file.name}")
            return []

        # Extract collocations from the filtered content
        collocations_dict = extractor.extract_collocations(natural_speed_content)
        collocations = list(collocations_dict.keys()) if isinstance(collocations_dict, dict) else collocations_dict

        if filter_noise:
            collocations = _filter_noisy_collocations(collocations)

        return collocations

    except Exception as e:
        print_warning(f"Error extracting from {story_file.name}: {e}")
        return []


# Alias for backward compatibility with tests
vocab_filter_noise = _filter_noisy_collocations