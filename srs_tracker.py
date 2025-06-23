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
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.status_file = self.data_dir / filename
        
        # Initialize with default values
        self.current_day: int = 1
        self.collocations: Dict[str, CollocationStatus] = {}
        
        # Create empty state file if it doesn't exist
        if not self.status_file.exists():
            self._save_state()
            
        self._load_state()

    def _load_state(self) -> None:
        """Load the tracker state from JSON file."""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r', encoding='utf-8') as f:
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
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving SRS state: {e}")

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

    def get_due_collocations(self, day: int, max_items: int = 5) -> List[str]:
        """Get collocations that are due for review on the given day.
        
        Args:
            day: The current day
            max_items: Maximum number of collocations to return
            
        Returns:
            List of collocation texts that are due for review
        """
        due_collocations = [
            colloc for colloc in self.collocations.values() 
            if colloc.next_review_day <= day
        ]
        # Sort by next_review_day (earliest first) and then by stability (lowest first)
        due_collocations.sort(key=lambda x: (x.next_review_day, x.stability))
        
        # Return just the text of the collocations
        return [colloc.text for colloc in due_collocations[:max_items]]

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._save_state()
