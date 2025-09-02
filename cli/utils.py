"""
Shared utilities for CLI commands.
"""
import sys
from typing import Dict, List, Any
from pathlib import Path


def print_success(message: str) -> None:
    """Print success message in green."""
    print(f"✅ {message}")


def print_warning(message: str) -> None:
    """Print warning message in yellow."""
    print(f"⚠️  {message}")


def print_error(message: str) -> None:
    """Print error message in red."""
    print(f"❌ {message}")


def print_info(message: str) -> None:
    """Print info message."""
    print(f"ℹ️  {message}")


def format_stats_table(stats: Dict[str, Any]) -> str:
    """Format statistics as a readable table."""
    lines = []
    lines.append("=" * 50)
    lines.append("SRS DATABASE STATISTICS")
    lines.append("=" * 50)
    
    for key, value in stats.items():
        # Format key for display
        display_key = key.replace('_', ' ').title()
        lines.append(f"{display_key:.<30} {value}")
    
    lines.append("=" * 50)
    return '\n'.join(lines)


def confirm_action(message: str) -> bool:
    """Ask user for confirmation."""
    response = input(f"{message} (y/N): ").lower().strip()
    return response in ['y', 'yes']


def get_story_files() -> List[Path]:
    """Get all story files in the stories directory."""
    stories_dir = Path('instance/data/stories')
    if not stories_dir.exists():
        print_error(f"Stories directory not found: {stories_dir}")
        return []
    
    story_files = list(stories_dir.glob('*.txt'))
    story_files.sort()
    return story_files


def extract_day_number(filename: Path) -> int:
    """Extract day number from story filename."""
    import re
    patterns = [
        r'day(\d+)', 
        r'day-(\d+)', 
        r'demo-\d+\.\d+\.\d+-day-(\d+)'
    ]
    
    filename_str = str(filename)
    for pattern in patterns:
        match = re.search(pattern, filename_str, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    print_warning(f"Could not extract day number from {filename}, using day 1")
    return 1


def show_progress(current: int, total: int, message: str = "Processing") -> None:
    """Show a simple progress indicator."""
    percentage = (current / total) * 100 if total > 0 else 0
    bar_length = 30
    filled_length = int(bar_length * current // total) if total > 0 else 0
    
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f"\r{message}: |{bar}| {current}/{total} ({percentage:.1f}%)", end='', flush=True)
    
    if current == total:
        print()  # New line when complete