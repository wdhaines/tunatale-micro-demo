import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, TypedDict


class CollocationData(TypedDict):
    """Type hint for collocation data in JSON."""
    text: str
    first_seen_day: int
    last_seen_day: int
    appearances: List[int]
    review_count: int
    next_review_day: int
    stability: float


@dataclass
class CollocationStatus:
    """Tracks the status of a collocation in the SRS system."""
    text: str
    first_seen_day: int
    last_seen_day: int
    appearances: List[int] = field(default_factory=list)
    review_count: int = 0
    next_review_day: int = 0
    stability: float = 1.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'CollocationStatus':
        """Create from dictionary loaded from JSON."""
        return cls(**data)


class SRSTracker:
    """Spaced Repetition System tracker for collocations."""
    
    def __init__(self, data_dir: str = 'data', filename: str = 'srs_status.json'):
        """Initialize the SRS tracker.
        
        Args:
            data_dir: Directory to store the status file
            filename: Name of the status file
        """
        import sys
        from pathlib import Path
        
        self._is_test = 'pytest' in sys.modules
        self.data_dir = Path(data_dir)
        self.filename = filename
        self.filepath = self.data_dir / filename
        self.collocations: Dict[str, CollocationStatus] = {}
        self.current_day = 1
        
        # In test mode, ensure we're not using the main data directory
        if self._is_test:
            # Verify we're not writing to the main data directory
            main_data_dir = Path('data').resolve()
            if self.data_dir.resolve() == main_data_dir:
                raise RuntimeError(
                    "Attempted to write to main data directory in test mode. "
                    "Use a temporary directory for tests."
                )
        
        # Always create directory and initialize state, even in test mode
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if self.filepath.exists():
            self._load_state()
        else:
            self._save_state()

    def _load_state(self) -> None:
        """Load the tracker state from JSON file."""
        try:
            if self.filepath.exists():
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.current_day = data.get('current_day', 1)
                self.collocations = {
                    text: CollocationStatus.from_dict(colloc_data)
                    for text, colloc_data in data.get('collocations', {}).items()
                }
        except (json.JSONDecodeError, IOError) as e:
            # If file is corrupted, start fresh
            print(f"Warning: Could not load SRS state: {e}. Starting with fresh state.")
            self.collocations = {}
            self.current_day = 1

    def _save_state(self) -> None:
        """Save the current state to JSON file."""
        try:
            data = {
                'current_day': self.current_day,
                'collocations': {
                    colloc.text: colloc.to_dict()
                    for colloc in self.collocations.values()
                }
            }
            # In test mode, ensure the directory exists before writing
            if self._is_test:
                self.data_dir.mkdir(parents=True, exist_ok=True)
                
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            if not self._is_test:  # Only log errors in non-test mode
                print(f"Error saving SRS state: {e}")
            raise  # Re-raise the exception to fail tests

    def add_collocations(self, collocations: List[str], day: Optional[int] = None) -> None:
        """Add new collocations or update existing ones.
        
        Args:
            collocations: List of collocation strings to add/update
            day: Current day number. If None, uses current_day + 1
        """
        if day is None:
            day = self.current_day + 1
        
        self.current_day = day
        
        for text in collocations:
            text = text.strip()
            if not text:
                continue
                
            if text in self.collocations:
                # Update existing collocation
                colloc = self.collocations[text]
                colloc.last_seen_day = day
                colloc.appearances.append(day)
                colloc.review_count += 1
                
                # Simple algorithm: double the interval each time
                interval = max(1, int(colloc.stability * 2 ** (colloc.review_count - 1)))
                colloc.next_review_day = day + interval
                
                # Slight increase in stability
                colloc.stability *= 1.2
            else:
                # New collocation - make it due on the current day
                self.collocations[text] = CollocationStatus(
                    text=text,
                    first_seen_day=day,
                    last_seen_day=day,
                    appearances=[day],
                    review_count=0,  # Start with 0 reviews
                    next_review_day=day,  # Due immediately
                    stability=1.0
                )
                
                # Ensure it's immediately due by setting next_review_day to the current day
                self.collocations[text].next_review_day = day
        
        self._save_state()

    def get_all_collocations(self) -> List[str]:
        """Get all collocations in the tracker.
        
        Returns:
            List of all collocation texts in the tracker
        """
        return list(self.collocations.keys())
        
    def _categorize_collocation(self, collocation: str, current_day: int) -> str:
        """Categorize a collocation based on its review status.
        
        Args:
            collocation: The collocation text to categorize
            current_day: The current day in the curriculum
            
        Returns:
            str: One of "new", "learning", "reviewing", or "mastered"
            
        Raises:
            KeyError: If the collocation is not found in the tracker
        """
        if collocation not in self.collocations:
            raise KeyError(f"Collocation '{collocation}' not found in tracker")
            
        colloc = self.collocations[collocation]
        
        # A collocation is "new" if it has 0 reviews
        if colloc.review_count == 0:
            return "new"
            
        # A collocation is "mastered" if its next review is far in the future
        if colloc.next_review_day > current_day + 7:  # More than a week away
            return "mastered"
            
        # A collocation is in "reviewing" if it has 3 or more reviews
        if colloc.review_count >= 3:
            return "reviewing"
            
        # Otherwise, it's still in the "learning" phase
        return "learning"

    def get_due_collocations(self, day: int, min_items: int = 3, max_items: int = 5) -> List[str]:
        """Get collocations that are due for review on the given day.
        
        Args:
            day: The current day
            min_items: Minimum number of collocations to return if available
            max_items: Maximum number of collocations to return
            
        Returns:
            List of collocation texts that are due for review, prioritized by:
            1. Most overdue (days since due)
            2. Stability score (least stable first)
        """
        due_collocations = []
        
        # First get all due collocations with days overdue and sort
        for colloc in self.collocations.values():
            if colloc.next_review_day <= day:
                days_overdue = day - colloc.next_review_day
                due_collocations.append((days_overdue, colloc.stability, colloc.text, colloc))
        
        if not due_collocations:
            return []
            
        # Sort by most overdue first, then by stability (least stable first)
        due_collocations.sort(key=lambda x: (-x[0], x[1]))
        
        # Take up to max_items, but at least min_items if available
        result_count = min(max(min_items, len(due_collocations)), max_items)
        return [colloc[2] for colloc in due_collocations[:result_count]]

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._save_state()
