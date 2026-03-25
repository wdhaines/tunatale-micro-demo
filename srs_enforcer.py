"""
SRS Constraint Enforcement System for TunaTale.

This module implements two-pass content generation:
1. Pass 1: Generate content with positive SRS constraints
2. Pass 2: Enforce constraints by replacing English with known Filipino

Critical for fixing regressions like water/tubig where English appears 
even when Filipino equivalent is known.
"""

import re
import json
from typing import Dict, List, Tuple, Any, Optional
from srs_database import SRSDatabase


class SRSEnforcer:
    """Enforces SRS constraints by replacing English with known Filipino vocabulary."""
    
    def __init__(self, db: SRSDatabase):
        """Initialize the SRS enforcer.
        
        Args:
            db: SRSDatabase instance for accessing vocabulary data
        """
        self.db = db
        self.replacement_dict = self._build_replacement_dictionary()
        self.debug_mode = True  # Show replacement info
    
    def _build_replacement_dictionary(self) -> Dict[str, str]:
        """Build dictionary of English → Filipino replacements.
        
        Returns:
            Dictionary mapping English terms to Filipino equivalents
        """
        replacements = {}
        
        # Critical replacements based on known regressions
        critical_replacements = {
            # Water-related (highest priority - active regression)
            'water': 'tubig',
            'bottled water': 'tubig',
            'service water': 'libre pong tubig',
            'just water': 'tubig lang po',
            
            # Common courtesy (based on database analysis)
            'thank you': 'salamat po',
            'thanks': 'salamat',
            'excuse me': 'paumanhin po',
            
            # Questions/requests
            'how much': 'magkano po',
            'can you': 'pwede po ba',
            'may I': 'pwede po ba ako',
            'please': 'po',
            
            # Common words that often appear in English
            'yes': 'opo',
            'okay': 'sige',
            'good': 'maganda',
            'delicious': 'masarap',
            'expensive': 'mahal',
            
            # Numbers (common regression points)
            'thirty': 'tatlumpu',
            'sixty': 'animnapu', 
            'eighty': 'walumpu',
            'twenty': 'dalawampu',
            
            # Colors
            'blue': 'asul',
            'pink': 'rosas',
            'red': 'pula',
            'green': 'luntian',
            
            # Size/quantity
            'big': 'malaki',
            'small': 'maliit',
            'many': 'marami',
            'few': 'kaunti',
        }
        
        replacements.update(critical_replacements)
        
        # Add dynamic replacements from database
        # Look for Filipino phrases that have English equivalents
        try:
            all_collocations = self.db.get_all_collocations()
            
            for colloc in all_collocations:
                # Skip if no reviews (not established enough to block English)
                if colloc['review_count'] < 1:
                    continue
                
                text = colloc['text'].lower()
                
                # Add known patterns
                if 'salamat' in text and 'thank' not in replacements.values():
                    replacements['thank you'] = 'salamat po'
                
                if 'magkano' in text and 'how much' not in replacements.values():
                    replacements['how much'] = 'magkano po'
                
                if 'pwede' in text and 'can you' not in replacements.values():
                    replacements['can you'] = 'pwede po ba'
            
        except Exception as e:
            print(f"Warning: Could not load dynamic replacements: {e}")
        
        return replacements
    
    def enforce_constraints(self, content: str, day: int, context: str = "story") -> Tuple[str, List[Dict[str, Any]]]:
        """Enforce SRS constraints on content by replacing English with Filipino.
        
        Args:
            content: The content to process
            day: Current day number
            context: Context for logging (e.g., "story", "dialogue")
            
        Returns:
            Tuple of (enforced_content, list_of_violations_and_replacements)
        """
        if not content:
            return content, []
        
        # Save original content before any SRS enforcement
        self._save_original_backup(content, day, context)
        
        violations = []
        enforced_content = content
        
        print(f"\n🔍 SRS Enforcement - Day {day} ({context})")
        print("=" * 50)
        
        # Check for each potential replacement
        for english, filipino in self.replacement_dict.items():
            # Create word boundary pattern to avoid partial matches
            # Use case-insensitive matching
            pattern = r'\b' + re.escape(english) + r'\b'
            
            matches = re.findall(pattern, enforced_content, re.IGNORECASE)
            
            if matches:
                count = len(matches)
                
                # Record the violation
                violation = {
                    'english': english,
                    'filipino': filipino,
                    'count': count,
                    'day': day,
                    'context': context
                }
                violations.append(violation)
                
                # Perform the replacement
                enforced_content = re.sub(
                    pattern, 
                    filipino, 
                    enforced_content, 
                    flags=re.IGNORECASE
                )
                
                if self.debug_mode:
                    print(f"  🔧 Replaced '{english}' → '{filipino}' ({count}x)")
        
        # Record violations in database for tracking
        for violation in violations:
            try:
                self.db._record_violation(
                    day=day,
                    english_text=violation['english'],
                    known_filipino=violation['filipino'],
                    violation_type='constraint_enforcement',
                    was_replaced=True,
                    context=context
                )
            except Exception as e:
                print(f"Warning: Could not record violation: {e}")
        
        # Summary
        if violations:
            print(f"\n✅ SRS Enforcement Complete: {len(violations)} replacements made")
        else:
            print(f"\n✅ SRS Enforcement Complete: No violations found")
        
        return enforced_content, violations
    
    def test_enforcement(self, test_content: str) -> Dict[str, Any]:
        """Test enforcement on sample content for debugging.
        
        Args:
            test_content: Content to test
            
        Returns:
            Dictionary with test results
        """
        print("\n🧪 Testing SRS Enforcement")
        print("=" * 30)
        print(f"Original: {test_content}")
        
        enforced, violations = self.enforce_constraints(test_content, day=999, context="test")
        
        print(f"Enforced: {enforced}")
        
        return {
            'original': test_content,
            'enforced': enforced,
            'violations': violations,
            'total_replacements': len(violations)
        }
    
    def get_replacement_dictionary(self) -> Dict[str, str]:
        """Get the current replacement dictionary for inspection.
        
        Returns:
            Dictionary of English → Filipino replacements
        """
        return self.replacement_dict.copy()
    
    def add_replacement(self, english: str, filipino: str) -> None:
        """Add a new replacement rule.
        
        Args:
            english: English term to replace
            filipino: Filipino replacement
        """
        self.replacement_dict[english.lower()] = filipino
        print(f"Added replacement: '{english}' → '{filipino}'")
    
    def _save_original_backup(self, content: str, day: int, context: str):
        """Save original content before SRS enforcement is applied."""
        try:
            from pathlib import Path
            
            # Create backup directory if it doesn't exist
            backup_dir = Path("instance/data/stories/originals")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate backup filename with context for uniqueness
            if context and context != "story":
                backup_filename = f"story_day{day}_original_{context}.txt"
            else:
                backup_filename = f"story_day{day}_original.txt"
            
            backup_path = backup_dir / backup_filename
            
            # Only save if backup doesn't already exist (preserve first original)
            if not backup_path.exists():
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"📄 Original content saved to: {backup_path}")
            else:
                print(f"📄 Original backup already exists: {backup_path}")
                
        except Exception as e:
            print(f"⚠️ Could not save original backup: {e}")


# Extension to SRSDatabase for violation recording
def _record_violation(self, day: int, english_text: str, known_filipino: str, 
                     violation_type: str = 'constraint_enforcement', 
                     was_replaced: bool = True, context: str = 'story') -> None:
    """Record a constraint violation in the database.
    
    Args:
        day: Day number when violation occurred
        english_text: The English text that should have been Filipino
        known_filipino: The Filipino text it should have been
        violation_type: Type of violation
        was_replaced: Whether the violation was automatically fixed
        context: Context where violation occurred
    """
    with sqlite3.connect(self.db_path) as conn:
        conn.execute("""
            INSERT INTO srs_violations 
            (day, english_text, known_filipino, violation_type, was_replaced, context)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (day, english_text, known_filipino, violation_type, was_replaced, context))

# Monkey patch the method to SRSDatabase
import sqlite3
SRSDatabase._record_violation = _record_violation


def create_test_enforcer() -> SRSEnforcer:
    """Create an SRSEnforcer for testing purposes."""
    db = SRSDatabase()
    return SRSEnforcer(db)


if __name__ == "__main__":
    # Quick test
    enforcer = create_test_enforcer()
    
    # Test the critical regression
    test_cases = [
        "I need some water please",
        "Can you get me bottled water?",
        "Thank you for the service water",
        "How much does this cost?",
        "The food is delicious and water is free"
    ]
    
    print("🔧 Testing SRS Constraint Enforcement")
    print("=" * 40)
    
    for test in test_cases:
        result = enforcer.test_enforcement(test)
        print()