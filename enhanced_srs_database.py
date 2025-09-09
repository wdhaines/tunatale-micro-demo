"""
Enhanced SQLite database implementation for TunaTale SRS system with bidirectional mappings.
Extends the existing SRS database to support English↔Filipino translation pairs.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from srs_database import SRSDatabase


@dataclass
class TranslationPair:
    """Represents a detected English↔Filipino translation pair."""
    english: str
    filipino: str 
    confidence: float = 1.0
    
    def __post_init__(self):
        self.english = self.english.lower().strip()
        self.filipino = self.filipino.lower().strip()
    
    def __repr__(self):
        return f"TranslationPair('{self.english}' ↔ '{self.filipino}', confidence={self.confidence})"


@dataclass
class BilingualCollocation:
    """Represents a collocation that may have translation mappings."""
    text: str
    language: str  # 'filipino', 'english', 'mixed'
    first_seen_day: int
    last_seen_day: int
    appearances: List[int]
    review_count: int
    next_review_day: int
    stability: float
    english_equivalent: Optional[str] = None
    filipino_equivalent: Optional[str] = None
    confidence: Optional[float] = None


class EnhancedSRSDatabase(SRSDatabase):
    """Enhanced SRS database with bidirectional English↔Filipino mapping support."""
    
    def __init__(self, db_path: str = "instance/data/srs/enhanced_tunatale_srs.db"):
        """Initialize the enhanced SRS database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        
        # Ensure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize enhanced database schema
        self.init_enhanced_database()
    
    def init_enhanced_database(self):
        """Create enhanced database tables with bidirectional mapping support."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key support
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Enhanced collocations table with language detection and bidirectional mapping
            conn.execute("""
                CREATE TABLE IF NOT EXISTS enhanced_collocations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT UNIQUE NOT NULL,
                    
                    -- Language classification
                    language TEXT NOT NULL DEFAULT 'filipino',  -- 'filipino', 'english', 'mixed'
                    
                    -- Core SRS tracking (from existing JSON)
                    first_seen_day INTEGER NOT NULL,
                    last_seen_day INTEGER NOT NULL,
                    appearances TEXT NOT NULL,  -- JSON array of days
                    review_count INTEGER NOT NULL DEFAULT 0,
                    next_review_day INTEGER NOT NULL DEFAULT 0,
                    stability REAL NOT NULL DEFAULT 1.0,
                    
                    -- Bidirectional mapping
                    english_equivalent TEXT DEFAULT NULL,
                    filipino_equivalent TEXT DEFAULT NULL,
                    translation_confidence REAL DEFAULT NULL,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Constraints for bidirectional mapping
                    CONSTRAINT check_language CHECK (language IN ('filipino', 'english', 'mixed')),
                    CONSTRAINT check_confidence CHECK (translation_confidence IS NULL OR translation_confidence BETWEEN 0.0 AND 1.0)
                )
            """)
            
            # Translation pairs table for managing English↔Filipino mappings
            conn.execute("""
                CREATE TABLE IF NOT EXISTS translation_pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    english_text TEXT NOT NULL,
                    filipino_text TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    
                    -- Source tracking
                    source_day INTEGER NOT NULL,
                    extraction_method TEXT NOT NULL DEFAULT 'story_dialogue',  -- 'story_dialogue', 'manual', 'computed'
                    
                    -- Status
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    verified BOOLEAN NOT NULL DEFAULT 0,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Constraints
                    CONSTRAINT unique_pair UNIQUE (english_text, filipino_text),
                    CONSTRAINT check_confidence_range CHECK (confidence BETWEEN 0.0 AND 1.0)
                )
            """)
            
            # Create indexes for fast lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_enhanced_collocations_text 
                ON enhanced_collocations(text)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_enhanced_collocations_language 
                ON enhanced_collocations(language)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_enhanced_collocations_review 
                ON enhanced_collocations(next_review_day, review_count)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_enhanced_collocations_equivalents 
                ON enhanced_collocations(english_equivalent, filipino_equivalent)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_translation_pairs_english 
                ON translation_pairs(english_text)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_translation_pairs_filipino 
                ON translation_pairs(filipino_text)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_translation_pairs_active 
                ON translation_pairs(is_active, confidence DESC)
            """)
            
            # Inherit violations table from parent class
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
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_violations_day 
                ON srs_violations(day, created_at)
            """)
    
    def add_translation_pair(self, english_text: str, filipino_text: str, 
                           confidence: float = 1.0, source_day: int = 0,
                           extraction_method: str = 'story_dialogue') -> bool:
        """Add a translation pair to the database.
        
        Args:
            english_text: English text
            filipino_text: Filipino text
            confidence: Translation confidence (0.0-1.0)
            source_day: Day when this pair was first detected
            extraction_method: How this pair was discovered
            
        Returns:
            True if added successfully, False if duplicate
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO translation_pairs 
                    (english_text, filipino_text, confidence, source_day, extraction_method)
                    VALUES (?, ?, ?, ?, ?)
                """, (english_text, filipino_text, confidence, source_day, extraction_method))
                return True
        except sqlite3.IntegrityError:
            # Duplicate pair - update confidence if higher
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE translation_pairs 
                    SET confidence = MAX(confidence, ?), updated_at = CURRENT_TIMESTAMP
                    WHERE english_text = ? AND filipino_text = ?
                """, (confidence, english_text, filipino_text))
                return False
    
    def add_enhanced_collocation(self, text: str, language: str, first_seen_day: int, 
                               last_seen_day: int, appearances: List[int], 
                               review_count: int = 0, next_review_day: int = 0, 
                               stability: float = 1.0, english_equivalent: Optional[str] = None,
                               filipino_equivalent: Optional[str] = None, 
                               translation_confidence: Optional[float] = None) -> None:
        """Add an enhanced collocation with language and mapping information.
        
        Args:
            text: The collocation text
            language: Language classification ('filipino', 'english', 'mixed')
            first_seen_day: First day this collocation was seen
            last_seen_day: Most recent day this collocation was seen
            appearances: List of days when collocation appeared
            review_count: Number of times reviewed
            next_review_day: Next day for review
            stability: SRS stability score
            english_equivalent: English equivalent if available
            filipino_equivalent: Filipino equivalent if available
            translation_confidence: Confidence in the translation mapping
        """
        appearances_json = json.dumps(appearances)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO enhanced_collocations 
                (text, language, first_seen_day, last_seen_day, appearances, 
                 review_count, next_review_day, stability, english_equivalent, 
                 filipino_equivalent, translation_confidence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (text, language, first_seen_day, last_seen_day, appearances_json, 
                  review_count, next_review_day, stability, english_equivalent, 
                  filipino_equivalent, translation_confidence))
    
    def get_translation_pairs(self, active_only: bool = True) -> List[TranslationPair]:
        """Retrieve all translation pairs from the database.
        
        Args:
            active_only: Only return active (non-deleted) pairs
            
        Returns:
            List of TranslationPair objects
        """
        query = """
            SELECT english_text, filipino_text, confidence 
            FROM translation_pairs 
            WHERE is_active = 1
            ORDER BY confidence DESC
        """ if active_only else """
            SELECT english_text, filipino_text, confidence 
            FROM translation_pairs 
            ORDER BY confidence DESC
        """
        
        pairs = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query)
            for row in cursor.fetchall():
                pairs.append(TranslationPair(row[0], row[1], row[2]))
        
        return pairs
    
    def get_bilingual_collocations(self, language: Optional[str] = None) -> List[BilingualCollocation]:
        """Retrieve enhanced collocations with bidirectional mapping support.
        
        Args:
            language: Filter by language ('filipino', 'english', 'mixed') or None for all
            
        Returns:
            List of BilingualCollocation objects
        """
        if language:
            query = """
                SELECT text, language, first_seen_day, last_seen_day, appearances, 
                       review_count, next_review_day, stability, english_equivalent, 
                       filipino_equivalent, translation_confidence
                FROM enhanced_collocations 
                WHERE language = ?
                ORDER BY stability DESC, review_count ASC
            """
            params = (language,)
        else:
            query = """
                SELECT text, language, first_seen_day, last_seen_day, appearances, 
                       review_count, next_review_day, stability, english_equivalent, 
                       filipino_equivalent, translation_confidence
                FROM enhanced_collocations 
                ORDER BY stability DESC, review_count ASC
            """
            params = ()
        
        collocations = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            for row in cursor.fetchall():
                appearances = json.loads(row[4])
                collocations.append(BilingualCollocation(
                    text=row[0],
                    language=row[1],
                    first_seen_day=row[2],
                    last_seen_day=row[3],
                    appearances=appearances,
                    review_count=row[5],
                    next_review_day=row[6],
                    stability=row[7],
                    english_equivalent=row[8],
                    filipino_equivalent=row[9],
                    confidence=row[10]
                ))
        
        return collocations
    
    def find_english_equivalent(self, filipino_text: str) -> Optional[str]:
        """Find English equivalent for a Filipino text.
        
        Args:
            filipino_text: Filipino text to translate
            
        Returns:
            English equivalent if found, None otherwise
        """
        # First check enhanced collocations
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT english_equivalent 
                FROM enhanced_collocations 
                WHERE text = ? AND english_equivalent IS NOT NULL
            """, (filipino_text,))
            row = cursor.fetchone()
            if row:
                return row[0]
            
            # Check translation pairs
            cursor = conn.execute("""
                SELECT english_text 
                FROM translation_pairs 
                WHERE filipino_text = ? AND is_active = 1
                ORDER BY confidence DESC
                LIMIT 1
            """, (filipino_text,))
            row = cursor.fetchone()
            if row:
                return row[0]
        
        return None
    
    def find_filipino_equivalent(self, english_text: str) -> Optional[str]:
        """Find Filipino equivalent for an English text.
        
        Args:
            english_text: English text to translate
            
        Returns:
            Filipino equivalent if found, None otherwise
        """
        # First check enhanced collocations
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT filipino_equivalent 
                FROM enhanced_collocations 
                WHERE text = ? AND filipino_equivalent IS NOT NULL
            """, (english_text,))
            row = cursor.fetchone()
            if row:
                return row[0]
            
            # Check translation pairs
            cursor = conn.execute("""
                SELECT filipino_text 
                FROM translation_pairs 
                WHERE english_text = ? AND is_active = 1
                ORDER BY confidence DESC
                LIMIT 1
            """, (english_text,))
            row = cursor.fetchone()
            if row:
                return row[0]
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get enhanced database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            # Enhanced collocations by language
            cursor = conn.execute("""
                SELECT language, COUNT(*) 
                FROM enhanced_collocations 
                GROUP BY language
            """)
            language_counts = dict(cursor.fetchall())
            
            # Translation pairs stats
            cursor = conn.execute("""
                SELECT COUNT(*) FROM translation_pairs WHERE is_active = 1
            """)
            active_pairs = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT AVG(confidence) FROM translation_pairs WHERE is_active = 1
            """)
            avg_confidence = cursor.fetchone()[0] or 0.0
            
            # Bidirectional mappings stats
            cursor = conn.execute("""
                SELECT COUNT(*) FROM enhanced_collocations 
                WHERE english_equivalent IS NOT NULL OR filipino_equivalent IS NOT NULL
            """)
            mapped_collocations = cursor.fetchone()[0]
            
            return {
                'enhanced_collocations': language_counts,
                'total_collocations': sum(language_counts.values()),
                'active_translation_pairs': active_pairs,
                'average_translation_confidence': round(avg_confidence, 3),
                'mapped_collocations': mapped_collocations,
                'database_path': str(self.db_path)
            }


def main():
    """Test the enhanced database functionality."""
    db = EnhancedSRSDatabase()
    
    # Test adding translation pairs
    db.add_translation_pair("water", "tubig", 1.0, 7, "story_dialogue")
    db.add_translation_pair("delicious", "masarap", 0.95, 7, "story_dialogue")
    db.add_translation_pair("perfect", "perpekto", 1.0, 17, "story_dialogue")
    
    # Test adding enhanced collocations
    db.add_enhanced_collocation("tubig lang po", "filipino", 7, 7, [7], 
                              english_equivalent="just water", 
                              translation_confidence=0.9)
    
    db.add_enhanced_collocation("just water", "english", 7, 7, [7],
                              filipino_equivalent="tubig lang po",
                              translation_confidence=0.9)
    
    # Print statistics
    stats = db.get_stats()
    print("Enhanced SRS Database Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test lookups
    print(f"\nFinding equivalents:")
    print(f"  'tubig' -> '{db.find_english_equivalent('tubig')}'")
    print(f"  'water' -> '{db.find_filipino_equivalent('water')}'")


if __name__ == "__main__":
    main()