"""
SRS Adapter to provide SRSTracker-compatible interface for SRSDatabase.

This adapter allows existing code to use SRSDatabase without changing the interface.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from dataclasses import dataclass

from srs_database import SRSDatabase
from content_strategy import ContentStrategy, get_strategy_config

logger = logging.getLogger(__name__)


@dataclass
class CollocationStatus:
    """
    Status tracking for individual collocations in SRS.
    
    This class maintains compatibility with test fixtures that expect
    the CollocationStatus interface from the old SRSTracker system.
    """
    text: str
    first_seen_day: int
    last_seen_day: int
    appearances: List[int]
    review_count: int
    next_review_day: int
    stability: float


class SRSAdapter:
    """
    Adapter that provides SRSTracker-compatible interface using SRSDatabase backend.
    
    This allows existing code to work with the new SRSDatabase system without 
    changing the interface calls.
    """
    
    def __init__(self, db_path: Optional[str] = None, test_mode: bool = False):
        """Initialize the adapter with an SRSDatabase backend."""
        if test_mode:
            # Use in-memory database for tests (isolated)
            self.db = SRSDatabase(":memory:")
            # Ensure database is properly initialized for in-memory usage
            self.db.init_database()
            logger.debug("SRSAdapter initialized in test mode (in-memory database)")
        elif db_path:
            # Use specific database path
            self.db = SRSDatabase(db_path)
            logger.debug(f"SRSAdapter initialized with custom database: {db_path}")
        else:
            # Use production database (default behavior)
            db_path = "instance/data/srs/tunatale_srs.db"
            self.db = SRSDatabase(db_path)
            logger.info(f"SRSAdapter initialized with production database: {db_path}")
    
    def get_due_collocations(self, day: int, min_items: int = 3, max_items: int = 5, 
                           strategy: Optional[ContentStrategy] = None) -> List[str]:
        """
        Get collocations that are due for review on the given day.
        
        This method provides the same interface as SRSTracker but uses SRSDatabase backend.
        
        Args:
            day: The current day
            min_items: Minimum number of collocations to return if available
            max_items: Maximum number of collocations to return
            strategy: Optional strategy to adjust parameters
            
        Returns:
            List of collocation texts (strings) that are due for review
        """
        # Apply strategy-specific parameters if provided
        if strategy:
            try:
                config = get_strategy_config(strategy)
                min_items = config.min_review_collocations
                max_items = config.max_new_collocations + config.min_review_collocations
            except:
                pass  # Use default values if strategy config fails
        
        # Get due collocations from database
        due_items = self.db.get_due_collocations(day)
        
        # Filter out invalid collocations and extract text
        valid_collocations = []
        for item in due_items:
            collocation = item['text'] if isinstance(item, dict) else item
            
            # Skip voice tags and other invalid items
            if self._is_valid_collocation(collocation):
                valid_collocations.append(collocation)
        
        # Sort by priority (days overdue, then by stability)
        prioritized = self._prioritize_collocations(valid_collocations, due_items, day)
        
        # Return appropriate number of items
        result_count = min(max(min_items, len(prioritized)), max_items)
        result = prioritized[:result_count]
        
        logger.debug(f"Returning {len(result)} due collocations for day {day} (strategy: {strategy})")
        return result
    
    def add_collocations(self, collocations: List[str], day: int) -> None:
        """
        Add collocations to the SRS system.
        
        Args:
            collocations: List of collocation texts to add
            day: Day when these collocations were encountered
        """
        valid_collocations = [c for c in collocations if self._is_valid_collocation(c)]
        
        if valid_collocations:
            # Delegate to SRSDatabase.add_collocation() (singular) for each collocation
            for collocation in valid_collocations:
                self.db.add_collocation(
                    text=collocation,
                    first_seen_day=day,
                    last_seen_day=day,
                    appearances=[day],
                    review_count=0,
                    next_review_day=day,  # Due for review immediately
                    stability=1.0
                )
            logger.debug(f"Added {len(valid_collocations)} collocations for day {day}")
    
    def get_all_collocations(self) -> List[str]:
        """
        Get all collocations in the system.
        
        Returns:
            List of all collocation texts
        """
        try:
            # Get all collocations from database
            all_items = self.db.get_all_collocations()
            
            # Extract text and filter valid ones
            all_collocations = []
            for item in all_items:
                collocation = item['text'] if isinstance(item, dict) else item
                if self._is_valid_collocation(collocation):
                    all_collocations.append(collocation)
            
            return all_collocations
        except Exception as e:
            logger.warning(f"Failed to get all collocations: {e}")
            return []
    
    def get_strategy_collocations(self, day: int, strategy: ContentStrategy) -> Dict[str, List[str]]:
        """
        Get collocations organized by strategy requirements.
        
        Args:
            day: Current day
            strategy: Content strategy to use
            
        Returns:
            Dictionary with 'new' and 'review' collocation lists optimized for the strategy
        """
        try:
            config = get_strategy_config(strategy)
        except:
            # Fallback to default behavior
            return {
                'new': [],
                'review': self.get_due_collocations(day, 3, 5)
            }
        
        # Get due collocations with strategy-specific parameters
        review_collocations = self.get_due_collocations(
            day, 
            config.min_review_collocations,
            config.min_review_collocations + 2,  # Allow slight overflow
            strategy
        )
        
        # For now, new collocations are handled by the story generator
        return {
            'new': [],  # Will be filled by story generation process
            'review': review_collocations
        }
    
    def update_with_strategy(self, collocations: List[str], day: int, strategy: ContentStrategy) -> None:
        """
        Update collocations using strategy-specific intervals.
        
        Args:
            collocations: List of collocations to update
            day: Current day
            strategy: Strategy to use for interval calculations
        """
        try:
            config = get_strategy_config(strategy)
            multiplier = config.review_interval_multiplier
        except:
            multiplier = 1.0  # Fallback to default
        
        # Update each collocation with strategy-specific intervals
        for collocation in collocations:
            if self._is_valid_collocation(collocation):
                # For now, we'll use basic update logic
                # In the future, this could be enhanced with more sophisticated SRS algorithms
                try:
                    # Get current state and update with multiplier
                    # This is a simplified implementation
                    next_review_day = int(day + (3 * multiplier))  # Basic interval
                    self.db.update_collocation_review(collocation, 1, next_review_day, 1.0)
                except Exception as e:
                    logger.debug(f"Failed to update collocation {collocation}: {e}")
    
    def _is_valid_collocation(self, text: str) -> bool:
        """
        Check if a text is a valid collocation (not a voice tag or malformed data).
        
        Args:
            text: Text to validate
            
        Returns:
            True if text is a valid collocation
        """
        if not text or not isinstance(text, str):
            return False
        
        text = text.strip()
        
        # Skip voice tags
        if any(tag in text.lower() for tag in ['[narrator', 'tagalog-', '[tagalog', 'female-', 'male-']):
            return False
        
        # Skip single characters or very short items
        if len(text) < 2:
            return False
        
        # Skip items that are just numbers or punctuation
        if text.isdigit() or not any(c.isalpha() for c in text):
            return False
        
        # Skip standalone English articles and pronouns
        if text.lower() in ['the', 'a', 'an', 'you', 'we', 'it', 'this', 'that']:
            return False
        
        return True
    
    def _prioritize_collocations(self, collocations: List[str], due_items: List[Dict], day: int) -> List[str]:
        """
        Prioritize collocations by overdue status and stability.
        
        Args:
            collocations: List of valid collocation texts
            due_items: Original due items with metadata
            day: Current day
            
        Returns:
            Prioritized list of collocations
        """
        # Create lookup for metadata
        metadata_lookup = {}
        for item in due_items:
            text = item['text'] if isinstance(item, dict) else item
            if text in collocations:
                metadata_lookup[text] = item
        
        # Sort by priority
        def priority_key(collocation):
            if collocation in metadata_lookup:
                item = metadata_lookup[collocation]
                days_overdue = day - item.get('next_review_day', day)
                stability = item.get('stability', 1.0)
                return (-days_overdue, stability)  # Most overdue first, then least stable
            return (0, 1.0)  # Default priority
        
        return sorted(collocations, key=priority_key)
    
    @property
    def collocations(self) -> Dict[str, CollocationStatus]:
        """
        Get all collocations as dict for backward compatibility with old SRSTracker interface.
        
        Returns:
            Dictionary mapping collocation text to CollocationStatus objects
        """
        result = {}
        try:
            # Get all collocations from database
            all_items = self.db.get_all_collocations()
            
            for item in all_items:
                collocation = item['text']
                if self._is_valid_collocation(collocation):
                    # Convert database format to CollocationStatus
                    result[collocation] = CollocationStatus(
                        text=collocation,
                        first_seen_day=item.get('first_seen_day', 1),
                        last_seen_day=item.get('last_seen_day', 1),
                        appearances=item.get('appearances', [1]),
                        review_count=item.get('review_count', 0),
                        next_review_day=item.get('next_review_day', 2),
                        stability=item.get('stability', 1.0)
                    )
        except Exception as e:
            logger.warning(f"Failed to get collocations dict: {e}")
            
        return result
    
    def _save_state(self) -> None:
        """
        Compatibility method for old SRSTracker interface.
        
        The database backend saves automatically, so this is a no-op
        but maintains compatibility with tests that expect this method.
        """
        # Database persists automatically - no action needed
        logger.debug("_save_state() called - database auto-saves, no action needed")