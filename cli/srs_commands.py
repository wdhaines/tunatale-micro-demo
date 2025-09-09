"""
SRS database management CLI commands.
"""
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from srs_database import SRSDatabase
from srs_tracker import SRSTracker
# from collocation_extractor import CollocationExtractor  # Removed - using LLM-based extraction
from story_collocation_extractor import StoryCollocationExtractor
from .vocab_commands import _extract_natural_speed_content
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
    
    # srs populate command
    populate_parser = srs_subparsers.add_parser(
        'populate', 
        help='Populate database from story content'
    )
    populate_group = populate_parser.add_mutually_exclusive_group(required=True)
    populate_group.add_argument('--all-stories', action='store_true',
                               help='Populate from all story files')
    populate_group.add_argument('--day', type=int,
                               help='Populate from specific day')
    populate_parser.add_argument('--clean-first', action='store_true',
                                help='Clean database before populating')
    populate_parser.add_argument('--dry-run', action='store_true',
                                help='Show what would be done without making changes')
    populate_parser.add_argument('--overwrite', action='store_true',
                                help='Overwrite existing entries')
    populate_parser.add_argument('--filter-noise', action='store_true', default=True,
                                help='Filter out voice tags and noise (default: True)')
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
    
    # srs clean command  
    clean_parser = srs_subparsers.add_parser(
        'clean',
        help='Clean corrupted vocabulary entries'
    )
    clean_parser.add_argument('--dry-run', action='store_true',
                             help='Show what would be cleaned without making changes')
    clean_parser.add_argument('--backup', action='store_true',
                             help='Create backup before cleaning')
    
    # Set command handlers
    srs_parser.set_defaults(func=handle_srs_command)


def handle_srs_command(args) -> None:
    """Handle SRS command routing."""
    if args.srs_action == 'populate':
        handle_populate_command(args)
    elif args.srs_action == 'stats':
        handle_stats_command(args)
    elif args.srs_action == 'clean':
        handle_clean_command(args)
    else:
        print_error("Unknown SRS action. Use --help for available commands.")


def handle_populate_command(args) -> None:
    """Handle database population command."""
    print_info("Starting SRS database population...")
    
    try:
        # Initialize components
        db = SRSDatabase()
        extractor = StoryCollocationExtractor()
        
        if args.clean_first:
            if args.dry_run:
                print_info("DRY RUN: Would clean database first")
            else:
                if args.force or confirm_action("Clean database before populating?"):
                    _clean_database(db)
        
        if args.all_stories:
            _populate_from_all_stories(db, extractor, args)
        else:
            _populate_from_day(db, extractor, args.day, args)
            
        if not args.dry_run:
            print_success("Database population completed!")
        else:
            print_info("DRY RUN completed - no changes made")
            
    except Exception as e:
        print_error(f"Error during population: {e}")


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


def _populate_from_all_stories(db: SRSDatabase, extractor: Any, args) -> None:
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
        added_count = _populate_from_story_file(db, extractor, story_file, day_num, args)
        
        if added_count is not None:
            total_added += added_count
            processed_files += 1
    
    show_progress(len(story_files), len(story_files), "Processing stories")
    
    if not args.dry_run:
        print_success(f"Processed {processed_files} files, added {total_added} collocations")
    else:
        print_info(f"DRY RUN: Would process {processed_files} files, add {total_added} collocations")


def _populate_from_day(db: SRSDatabase, extractor: Any, day: int, args) -> None:
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
    
    added_count = _populate_from_story_file(db, extractor, target_file, day, args)
    
    if added_count is not None:
        if not args.dry_run:
            print_success(f"Added {added_count} collocations from day {day}")
        else:
            print_info(f"DRY RUN: Would add {added_count} collocations from day {day}")


def _populate_from_story_file(db: SRSDatabase, extractor: Any, 
                             story_file: Path, day_num: int, args) -> Optional[int]:
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
        
        if args.dry_run:
            return len(collocations)
        
        # Add to database
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