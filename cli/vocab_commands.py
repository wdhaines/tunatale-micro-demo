"""
Vocabulary extraction CLI commands.
"""
import argparse
from pathlib import Path
from typing import List, Optional, Any

# from collocation_extractor import CollocationExtractor  # Removed - using LLM-based extraction
from srs_database import SRSDatabase
from .utils import (
    print_success, print_warning, print_error, print_info,
    get_story_files, extract_day_number, show_progress
)


def add_vocab_commands(subparsers) -> None:
    """Add vocabulary extraction commands to the CLI parser."""
    vocab_parser = subparsers.add_parser(
        'extract-vocab', 
        help='Extract vocabulary from story content',
        description='Extract collocations and vocabulary from story files'
    )
    
    # Day specification (mutually exclusive)
    day_group = vocab_parser.add_mutually_exclusive_group(required=True)
    day_group.add_argument('--day', type=int,
                          help='Extract from specific day')
    day_group.add_argument('--days', type=str,
                          help='Extract from day range (e.g., "1-17" or "1,3,5")')
    
    # Action specification
    action_group = vocab_parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--preview', action='store_true',
                             help='Preview extraction without saving')
    action_group.add_argument('--save', action='store_true',
                             help='Extract and save to database')
    
    # Options
    vocab_parser.add_argument('--filter-noise', action='store_true', default=True,
                             help='Filter out voice tags and noise (default: True)')
    vocab_parser.add_argument('--limit', type=int, default=20,
                             help='Limit number of collocations shown in preview (default: 20)')
    vocab_parser.add_argument('--overwrite', action='store_true',
                             help='Overwrite existing database entries')
    
    vocab_parser.set_defaults(func=handle_vocab_command)


def handle_vocab_command(args) -> None:
    """Handle vocabulary extraction command."""
    print_info("Starting vocabulary extraction...")
    
    try:
        # TODO: CollocationExtractor removed - implement new vocabulary extraction approach
        # For now, create a simple extractor stub
        class SimpleExtractor:
            def extract_collocations(self, text):
                return {}
        extractor = SimpleExtractor()
        
        # Parse day specification
        target_days = _parse_day_specification(args)
        
        if args.preview:
            _handle_preview_extraction(extractor, target_days, args)
        elif args.save:
            _handle_save_extraction(extractor, target_days, args)
            
    except Exception as e:
        print_error(f"Error during vocabulary extraction: {e}")


def _parse_day_specification(args) -> List[int]:
    """Parse day specification from arguments."""
    if args.day:
        return [args.day]
    
    if args.days:
        days = []
        parts = args.days.split(',')
        
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
    
    return []


def _handle_preview_extraction(extractor, target_days: List[int], args) -> None:
    """Handle preview extraction without saving."""
    story_files = get_story_files()
    
    print_info(f"Previewing extraction for {len(target_days)} day(s)")
    
    for day in target_days:
        story_file = _find_story_file_for_day(story_files, day)
        if not story_file:
            print_warning(f"No story file found for day {day}")
            continue
        
        print_info(f"\nDay {day}: {story_file.name}")
        print("-" * 50)
        
        collocations = _extract_from_file(extractor, story_file, args.filter_noise)
        
        if not collocations:
            print_warning("No collocations extracted")
            continue
        
        print_info(f"Extracted {len(collocations)} collocations:")
        
        # Show limited number for preview
        display_count = min(len(collocations), args.limit)
        for i, colloc in enumerate(collocations[:display_count]):
            print(f"  {i+1:2d}. '{colloc}'")
        
        if len(collocations) > display_count:
            print(f"  ... and {len(collocations) - display_count} more")
        
        # Show quality metrics
        _show_extraction_quality(collocations)


def _handle_save_extraction(extractor: Any, target_days: List[int], args) -> None:
    """Handle extraction with saving to database."""
    story_files = get_story_files()
    db = SRSDatabase()
    
    print_info(f"Extracting and saving for {len(target_days)} day(s)")
    
    total_saved = 0
    processed_days = 0
    
    for i, day in enumerate(target_days):
        show_progress(i, len(target_days), f"Processing day {day}")
        
        story_file = _find_story_file_for_day(story_files, day)
        if not story_file:
            print_warning(f"No story file found for day {day}")
            continue
        
        collocations = _extract_from_file(extractor, story_file, args.filter_noise)
        
        if not collocations:
            continue
        
        # Save to database
        saved_count = _save_collocations_to_db(db, collocations, day, args.overwrite)
        total_saved += saved_count
        processed_days += 1
    
    show_progress(len(target_days), len(target_days), "Processing")
    
    print_success(f"Processed {processed_days} days, saved {total_saved} collocations")


def _find_story_file_for_day(story_files: List[Path], day: int) -> Optional[Path]:
    """Find story file for specific day."""
    for story_file in story_files:
        if extract_day_number(story_file) == day:
            return story_file
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


def _extract_from_file(extractor: Any, story_file: Path, filter_noise: bool) -> List[str]:
    """Extract collocations from a story file."""
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
        collocations = list(collocations_dict.keys())
        
        if filter_noise:
            collocations = _filter_noisy_collocations(collocations)
        
        return collocations
        
    except Exception as e:
        print_warning(f"Error extracting from {story_file.name}: {e}")
        return []


def _has_filipino_indicators(text: str) -> bool:
    """Check if text contains Filipino language indicators."""
    filipino_markers = {
        'po', 'ba', 'na', 'ng', 'sa', 'ay', 'ang', 'mga', 'ako', 'ko',
        'mo', 'ito', 'yan', 'yun', 'siya', 'niya', 'kayo', 'ninyo',
        'kami', 'namin', 'tayo', 'natin', 'sila', 'nila', 'magkano',
        'salamat', 'kumusta', 'paumanhin', 'opo', 'hindi', 'oo',
        'umaga', 'hapon', 'gabi', 'maganda', 'masarap'  # Common Filipino words
    }
    words = text.lower().split()
    return any(word in filipino_markers for word in words)


def _is_mostly_english(words: List[str]) -> bool:
    """Check if word list is mostly English."""
    common_english_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had',
        'it', 'this', 'that', 'these', 'those', 'here', 'there'
    }
    if not words:
        return False
    english_count = sum(1 for word in words if word in common_english_words)
    return english_count / len(words) > 0.7  # More than 70% English


def _filter_noisy_collocations(collocations: List[str]) -> List[str]:
    """Filter out noisy/invalid collocations."""
    clean_collocations = []
    
    # Technical noise indicators (exact matches or substrings)
    technical_noise = {
        'tagalog-female', 'tagalog-male', '[narrator', 'narrator]', '-male-', '-female-'
    }
    
    # Pure English words that should be filtered when standing alone
    pure_english_filter = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had',
        'it', 'this', 'that', 'these', 'those', 'here', 'there'
    }
    
    for colloc in collocations:
        # Basic length check
        if len(colloc) <= 2:
            continue
        
        colloc_lower = colloc.lower()
        
        # Skip if contains technical noise
        if any(noise in colloc_lower for noise in technical_noise):
            continue
        
        # Skip if contains newlines or other problematic characters
        if '\n' in colloc or colloc.startswith('-') or colloc.endswith('-'):
            continue
        
        # Skip pure numbers or single letters
        if colloc.isdigit() or (len(colloc) == 1 and colloc.isalpha()):
            continue
        
        # Skip if starts with brackets (markup)
        if colloc.startswith('[') or colloc.startswith(']'):
            continue
        
        words = colloc_lower.split()
        
        # If it has Filipino indicators, keep it regardless of English content
        if _has_filipino_indicators(colloc_lower):
            clean_collocations.append(colloc)
            continue
        
        # If it's a single word that's pure English, filter it
        if len(words) == 1 and words[0] in pure_english_filter:
            continue
        
        # If it's mostly English words (and no Filipino), filter it
        if _is_mostly_english(words):
            continue
        
        # Otherwise keep it
        clean_collocations.append(colloc)
    
    return clean_collocations


# Make the function available for testing
vocab_filter_noise = _filter_noisy_collocations


def _save_collocations_to_db(db: SRSDatabase, collocations: List[str], day: int, overwrite: bool) -> int:
    """Save collocations to database."""
    saved_count = 0
    
    for colloc in collocations:
        try:
            # Check if already exists
            existing = db.get_collocation(colloc)
            if existing and not overwrite:
                continue
            
            # Add to database
            db.add_collocation(
                text=colloc,
                first_seen_day=day,
                last_seen_day=day,
                appearances=[day]
            )
            saved_count += 1
            
        except Exception as e:
            # Log error but continue with other collocations
            print_warning(f"Could not save '{colloc}': {e}")
    
    return saved_count


def _show_extraction_quality(collocations: List[str]) -> None:
    """Show quality metrics for extracted collocations."""
    if not collocations:
        return
    
    # Analyze quality indicators
    total = len(collocations)
    
    # Count potential issues
    short_count = sum(1 for c in collocations if len(c) <= 3)
    english_count = sum(1 for c in collocations if _looks_like_english(c))
    fragment_count = sum(1 for c in collocations if c.startswith('-') or c.endswith('-'))
    
    print_info("Quality metrics:")
    print(f"  Total collocations: {total}")
    
    if short_count > 0:
        print_warning(f"  Short (≤3 chars): {short_count} ({short_count/total*100:.1f}%)")
    
    if english_count > 0:
        print_warning(f"  Likely English: {english_count} ({english_count/total*100:.1f}%)")
    
    if fragment_count > 0:
        print_warning(f"  Fragments: {fragment_count} ({fragment_count/total*100:.1f}%)")
    
    clean_count = total - short_count - english_count - fragment_count
    if clean_count > 0:
        print_success(f"  Clean collocations: {clean_count} ({clean_count/total*100:.1f}%)")


def _looks_like_english(text: str) -> bool:
    """Check if text looks like English."""
    common_english_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'can', 'may',
        'this', 'that', 'these', 'those', 'here', 'there', 'when', 'where',
        'what', 'who', 'how', 'why', 'which', 'you', 'me', 'we', 'they', 'it'
    }
    
    words = text.lower().split()
    if not words:
        return False
    
    english_word_count = sum(1 for word in words if word in common_english_words)
    return english_word_count / len(words) > 0.6  # More than 60% English words