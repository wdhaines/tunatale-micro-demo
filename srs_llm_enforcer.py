"""LLM-based SRS constraint enforcement for grammar-aware vocabulary replacement."""

import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

from llm_mock import MockLLM
from srs_database import SRSDatabase


class SRSLLMEnforcer:
    """Uses LLM for grammar-aware SRS constraint enforcement instead of dictionary replacement."""
    
    def __init__(self, llm: MockLLM, srs_db: SRSDatabase):
        self.llm = llm
        self.srs_db = srs_db
        self.logger = logging.getLogger(__name__)
    
    def enforce_with_llm(self, content: str, day: int, context: str = "story") -> Tuple[str, List[Dict[str, Any]]]:
        """
        Use LLM for grammar-aware SRS enforcement that maintains proper Tagalog conjugation.
        
        Args:
            content: Story content to enforce
            day: Day number for context
            context: Generation context (e.g. "story", "strategy_deeper_generation")
            
        Returns:
            Tuple of (enforced_content, violations_list)
        """
        # Get high-stability vocabulary that should replace English
        replacements = self._get_high_stability_replacements()
        
        if not replacements:
            self.logger.info("No high-stability replacements available - skipping SRS enforcement")
            return content, []
        
        # Create prompt for LLM to intelligently replace
        prompt = self._create_enforcement_prompt(content, replacements, day)
        
        try:
            # Use LLM to do intelligent replacement
            self.logger.info("Requesting LLM-based SRS enforcement...")
            response = self.llm.chat_response(
                system_prompt="You are a Filipino language expert helping with vocabulary enforcement.",
                user_prompt=prompt,
                response_type="srs_enforcement"
            )
            
            # Extract the enforced content from LLM response
            enforced_content = self._extract_enforced_content(response)
            
            # Analyze what was replaced for logging
            violations = self._analyze_replacements(content, enforced_content, replacements, day, context)
            
            self.logger.info(f"LLM-based SRS enforcement complete: {len(violations)} intelligent replacements made")
            
            return enforced_content, violations
            
        except Exception as e:
            self.logger.error(f"LLM-based SRS enforcement failed: {e}")
            # Fallback to original content rather than crashing
            return content, []
    
    def _get_high_stability_replacements(self) -> Dict[str, str]:
        """Get English→Filipino replacements for vocabulary with high stability (learned well)."""
        replacements = {}
        
        try:
            # Query database for high-stability vocabulary
            # Use sqlite3 directly since SRSDatabase doesn't have get_connection method
            import sqlite3
            with sqlite3.connect(self.srs_db.db_path) as connection:
                cursor = connection.cursor()
                
                # Get collocations with stability >= 2.0 (well learned)
                # Note: Our current schema stores 'text' not separate filipino/english fields
                # For now, use fallback replacements
                cursor.execute("""
                    SELECT text, stability 
                    FROM collocations 
                    WHERE stability >= 2.0 
                    ORDER BY stability DESC
                    LIMIT 20
                """)
                
                # This would need enhancement to store English equivalents
                # For now, using fallback approach
                rows = cursor.fetchall()
                self.logger.debug(f"Found {len(rows)} high-stability collocations in database")
                
        except Exception as e:
            self.logger.warning(f"Could not load high-stability replacements: {e}")
            
        # Use hardcoded replacements for now until we enhance the database schema
        replacements = {
            "water": "tubig",
            "thank you": "salamat po", 
            "excuse me": "paumanhin po",
            "yes": "opo",
            "delicious": "masarap",
            "good": "maganda"
        }
            
        return replacements
    
    def _create_enforcement_prompt(self, content: str, replacements: Dict[str, str], day: int) -> str:
        """Create LLM prompt for grammar-aware vocabulary enforcement."""
        
        replacement_list = "\n".join([
            f"• '{english}' → '{filipino}'" 
            for english, filipino in replacements.items()
        ])
        
        return f"""You are helping enforce SRS vocabulary constraints on Filipino language learning content for Day {day}.

ORIGINAL CONTENT TO REVIEW:
{content}

VOCABULARY TO ENFORCE (English → Filipino):
{replacement_list}

SRS-SPECIFIC ENFORCEMENT RULES:

1. **GRAMMAR-AWARE REPLACEMENT:**
   - Maintain proper Tagalog grammar and conjugation
   - Consider context when replacing words:
     - "It's delicious" → "Masarap ito" (NOT "It's masarap") 
     - "The delicious food" → "Ang masarap na pagkain" (NOT "The masarap food")
     - "I need water" → "Kailangan ko ng tubig" (NOT "I need tubig")
   - Ensure replacements sound natural to Filipino speakers

2. **INTELLIGENT REPLACEMENT:**
   - Only replace when it improves authenticity without breaking comprehension
   - If unsure about a replacement, keep the original
   - Focus on high-frequency words that learners should know well

EXAMPLE TRANSFORMATIONS:

BEFORE:
[TAGALOG-FEMALE-1]: I need some water please
[NARRATOR]: I need some water please

AFTER: 
[TAGALOG-FEMALE-1]: Kailangan ko po ng tubig
[NARRATOR]: I need some water please

BEFORE:
[TAGALOG-MALE-1]: Thank you, that's very delicious!
[NARRATOR]: Thank you, that's very delicious!

AFTER:
[TAGALOG-MALE-1]: Salamat po, napaka-masarap naman!  
[NARRATOR]: Thank you, that's very delicious!

Return the complete content with intelligent, grammar-aware replacements applied only to Tagalog speaker lines."""
    
    def _extract_enforced_content(self, response: Dict) -> str:
        """Extract the enforced content from LLM response."""
        
        # Handle both direct and nested response formats from MockLLM
        if 'response' in response and 'choices' in response['response']:
            return response['response']['choices'][0]['message']['content'].strip()
        elif 'choices' in response:
            return response['choices'][0]['message']['content'].strip()
        elif isinstance(response, str):
            return response.strip()
        else:
            raise ValueError(f"Invalid LLM response format: {type(response)}")
    
    def _analyze_replacements(self, original: str, enforced: str, replacements: Dict[str, str], 
                            day: int, context: str) -> List[Dict[str, Any]]:
        """Analyze what replacements were made for logging and debugging."""
        violations = []
        
        # Simple analysis - compare original vs enforced for each replacement word
        for english, filipino in replacements.items():
            original_count = original.lower().count(english.lower())
            enforced_count = enforced.lower().count(english.lower())
            
            if original_count > enforced_count:
                replaced_count = original_count - enforced_count
                violations.append({
                    'english': english,
                    'filipino': filipino,
                    'count': replaced_count,
                    'method': 'llm_enforcement',
                    'day': day,
                    'context': context
                })
        
        # Store violations in database for analysis
        if violations:
            self._store_violations(violations, day, context)
        
        return violations
    
    def _store_violations(self, violations: List[Dict[str, Any]], day: int, context: str):
        """Store violation information in database for analysis."""
        try:
            # Use sqlite3 directly since SRSDatabase doesn't have get_connection method
            import sqlite3
            with sqlite3.connect(self.srs_db.db_path) as connection:
                cursor = connection.cursor()
                
                for violation in violations:
                    cursor.execute("""
                        INSERT INTO srs_violations 
                        (day, english_text, known_filipino, violation_type, was_replaced, context)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        day,
                        violation['english'],
                        violation['filipino'], 
                        'llm_enforcement',
                        1,  # was_replaced = True
                        context
                    ))
                
                connection.commit()
                self.logger.debug(f"Stored {len(violations)} violations in database")
                
        except Exception as e:
            self.logger.warning(f"Could not store violations in database: {e}")


def create_llm_enforcer(llm: MockLLM, srs_db: SRSDatabase) -> SRSLLMEnforcer:
    """Factory function to create SRS LLM enforcer."""
    return SRSLLMEnforcer(llm, srs_db)