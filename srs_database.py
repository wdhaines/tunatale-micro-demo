"""
SQLite database implementation for TunaTale SRS system.
Provides database storage for collocations with migration from JSON.
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class SRSDatabase:
    """SQLite database interface for SRS collocation storage."""
    
    def __init__(self, db_path: str = "instance/data/srs/tunatale_srs.db"):
        """Initialize the SRS database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        
        # Ensure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema
        self.init_database()
    
    def init_database(self):
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key support
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create collocations table matching existing JSON structure
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collocations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT UNIQUE NOT NULL,
                    
                    -- Core SRS tracking (from existing JSON)
                    first_seen_day INTEGER NOT NULL,
                    last_seen_day INTEGER NOT NULL,
                    appearances TEXT NOT NULL,  -- JSON array of days
                    review_count INTEGER NOT NULL DEFAULT 0,
                    next_review_day INTEGER NOT NULL DEFAULT 0,
                    stability REAL NOT NULL DEFAULT 1.0,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on text for fast lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_collocations_text 
                ON collocations(text)
            """)
            
            # Create index on review scheduling
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_collocations_review 
                ON collocations(next_review_day, review_count)
            """)
            
            # Add frequency tracking columns if they don't exist (migration)
            self._add_frequency_tracking_columns(conn)
            
            # Create violations table for tracking constraint enforcement
            conn.execute("""
                CREATE TABLE IF NOT EXISTS srs_violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day INTEGER NOT NULL,
                    english_text TEXT NOT NULL,
                    known_filipino TEXT NOT NULL,
                    violation_type TEXT DEFAULT 'constraint_enforcement',
                    was_replaced BOOLEAN DEFAULT 1,
                    context TEXT DEFAULT 'story',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on violations for reporting
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_violations_day 
                ON srs_violations(day, created_at)
            """)
    
    def _add_frequency_tracking_columns(self, conn):
        """Add frequency tracking columns to existing database (migration)."""
        # Check if columns already exist
        cursor = conn.execute("PRAGMA table_info(collocations)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        # Add corpus_frequency column if it doesn't exist
        if 'corpus_frequency' not in existing_columns:
            conn.execute("""
                ALTER TABLE collocations 
                ADD COLUMN corpus_frequency INTEGER DEFAULT 0
            """)
        
        # Add ready_for_translation column if it doesn't exist  
        if 'ready_for_translation' not in existing_columns:
            conn.execute("""
                ALTER TABLE collocations 
                ADD COLUMN ready_for_translation BOOLEAN DEFAULT FALSE
            """)
        
        # Create index on frequency fields for efficient querying
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_collocations_frequency 
            ON collocations(corpus_frequency, ready_for_translation)
        """)
    
    def add_collocation(self, text: str, first_seen_day: int, last_seen_day: int, 
                       appearances: List[int], review_count: int = 0, 
                       next_review_day: int = 0, stability: float = 1.0) -> None:
        """Add a new collocation to the database.
        
        Args:
            text: The collocation text
            first_seen_day: First day this collocation was seen
            last_seen_day: Most recent day this collocation was seen
            appearances: List of days when collocation appeared
            review_count: Number of times reviewed
            next_review_day: Day when next review is due
            stability: SRS stability factor
        """
        appearances_json = json.dumps(appearances)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO collocations 
                (text, first_seen_day, last_seen_day, appearances, 
                 review_count, next_review_day, stability, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (text, first_seen_day, last_seen_day, appearances_json, 
                  review_count, next_review_day, stability))
    
    def get_collocation(self, text: str) -> Optional[Dict[str, Any]]:
        """Get a specific collocation by text.
        
        Args:
            text: The collocation text to look up
            
        Returns:
            Dictionary with collocation data or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT text, first_seen_day, last_seen_day, appearances,
                       review_count, next_review_day, stability,
                       created_at, updated_at
                FROM collocations 
                WHERE text = ?
            """, (text,))
            
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # Parse appearances JSON back to list
                result['appearances'] = json.loads(result['appearances'])
                return result
            return None
    
    def get_all_collocations(self) -> List[Dict[str, Any]]:
        """Get all collocations from the database.
        
        Returns:
            List of dictionaries with collocation data
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT text, first_seen_day, last_seen_day, appearances,
                       review_count, next_review_day, stability,
                       created_at, updated_at
                FROM collocations 
                ORDER BY text
            """)
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                # Parse appearances JSON back to list
                result['appearances'] = json.loads(result['appearances'])
                results.append(result)
            
            return results
    
    def get_collocations_count(self) -> int:
        """Get the total number of collocations in the database.
        
        Returns:
            Number of collocations
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM collocations")
            return cursor.fetchone()[0]
    
    def get_due_collocations(self, current_day: int) -> List[Dict[str, Any]]:
        """Get collocations that are due for review.
        
        Args:
            current_day: The current day number
            
        Returns:
            List of collocations due for review
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT text, first_seen_day, last_seen_day, appearances,
                       review_count, next_review_day, stability,
                       created_at, updated_at
                FROM collocations 
                WHERE next_review_day <= ?
                ORDER BY next_review_day, review_count
            """, (current_day,))
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                # Parse appearances JSON back to list
                result['appearances'] = json.loads(result['appearances'])
                results.append(result)
            
            return results
    
    def update_collocation_review(self, text: str, new_review_count: int, 
                                 new_next_review_day: int, new_stability: float) -> None:
        """Update collocation review data after a review session.
        
        Args:
            text: The collocation text
            new_review_count: Updated review count
            new_next_review_day: Updated next review day
            new_stability: Updated stability factor
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE collocations 
                SET review_count = ?, next_review_day = ?, stability = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE text = ?
            """, (new_review_count, new_next_review_day, new_stability, text))
    
    def delete_collocation(self, text: str) -> bool:
        """Delete a collocation from the database.
        
        Args:
            text: The collocation text to delete
            
        Returns:
            True if collocation was deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM collocations WHERE text = ?", (text,))
            return cursor.rowcount > 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get basic statistics about the SRS database.
        
        Returns:
            Dictionary with statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total collocations
            cursor = conn.execute("SELECT COUNT(*) FROM collocations")
            stats['total_collocations'] = cursor.fetchone()[0]
            
            # Review count distribution
            cursor = conn.execute("""
                SELECT 
                    COUNT(CASE WHEN review_count = 0 THEN 1 END) as new,
                    COUNT(CASE WHEN review_count BETWEEN 1 AND 3 THEN 1 END) as learning,
                    COUNT(CASE WHEN review_count > 3 THEN 1 END) as well_known
                FROM collocations
            """)
            row = cursor.fetchone()
            stats['new'] = row[0]
            stats['learning'] = row[1]
            stats['well_known'] = row[2]
            
            # Average stability
            cursor = conn.execute("SELECT AVG(stability) FROM collocations")
            avg_stability = cursor.fetchone()[0]
            stats['average_stability'] = round(avg_stability, 2) if avg_stability else 0.0
            
            return stats
    
    def update_corpus_frequency(self, text: str, frequency: int) -> bool:
        """Update the corpus frequency for a collocation.
        
        Args:
            text: The collocation text
            frequency: New frequency count across the corpus
            
        Returns:
            True if update was successful, False if collocation not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE collocations 
                SET corpus_frequency = ?, 
                    ready_for_translation = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE text = ?
            """, (frequency, frequency >= 3, text))
            
            return cursor.rowcount > 0
    
    def get_collocations_ready_for_translation(self) -> List[Dict[str, Any]]:
        """Get all collocations that are ready for translation (frequency >= 3).
        
        Returns:
            List of collocation dictionaries ready for translation
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT text, corpus_frequency, first_seen_day, last_seen_day,
                       appearances, review_count, next_review_day, stability
                FROM collocations 
                WHERE ready_for_translation = TRUE
                ORDER BY corpus_frequency DESC, text
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_untranslated_frequent_collocations(self) -> List[str]:
        """Get collocations that are frequent (>=3) but don't have translations yet.
        
        Returns:
            List of collocation texts ready for batch translation
        """
        try:
            from enhanced_srs_database import EnhancedSRSDatabase
            enhanced_db = EnhancedSRSDatabase()
            
            # Get all frequent collocations
            frequent_collocations = self.get_collocations_ready_for_translation()
            
            # Filter out ones that already have translations
            untranslated = []
            for colloc in frequent_collocations:
                if not enhanced_db.find_english_equivalent(colloc['text']):
                    untranslated.append(colloc['text'])
            
            return untranslated
            
        except ImportError:
            # Fallback if enhanced database not available
            return [colloc['text'] for colloc in self.get_collocations_ready_for_translation()]
    
    def close(self):
        """Close database connection. (SQLite connections are per-operation, so this is a no-op)"""
        pass