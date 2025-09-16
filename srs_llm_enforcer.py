"""LLM-based SRS constraint enforcement for grammar-aware vocabulary replacement."""

import logging
import json
import re
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

from llm_mock import MockLLM
from srs_database import SRSDatabase
from enhanced_srs_database import EnhancedSRSDatabase
from language_detector import LanguageDetector


class DeterministicEnglishDetector:
    """Deterministic English term detection with SRS database cross-reference."""
    
    def __init__(self, srs_db: SRSDatabase, enhanced_db: Optional[EnhancedSRSDatabase] = None):
        self.srs_db = srs_db
        self.enhanced_db = enhanced_db
        self.language_detector = LanguageDetector()
        self.logger = logging.getLogger(__name__)
        
    def extract_dialogue_content(self, story_content: str) -> List[str]:
        """Extract only [TAGALOG-*] dialogue lines for English detection."""
        dialogue_lines = []
        
        # Pattern to match [TAGALOG-*]: dialogue
        dialogue_pattern = r'\[TAGALOG-[^]]+\]:\s*(.+)'
        
        for line in story_content.split('\n'):
            match = re.match(dialogue_pattern, line.strip())
            if match:
                dialogue_text = match.group(1).strip()
                if dialogue_text:
                    dialogue_lines.append(dialogue_text)
        
        return dialogue_lines
    
    def detect_english_terms(self, story_content: str) -> Tuple[List[str], List[str]]:
        """
        Detect English terms in dialogue and categorize them.
        
        Returns:
            Tuple of (srs_backed_terms, future_candidate_terms)
        """
        dialogue_lines = self.extract_dialogue_content(story_content)
        
        all_english_terms = set()
        
        # Process each dialogue line
        for line in dialogue_lines:
            english_terms = self._find_english_in_line(line)
            all_english_terms.update(english_terms)
        
        # Categorize terms based on SRS availability
        srs_backed_terms = []
        future_candidate_terms = []
        
        for term in all_english_terms:
            if self._has_srs_equivalent(term):
                srs_backed_terms.append(term)
                self.logger.debug(f"SRS-backed English term detected: '{term}'")
            else:
                future_candidate_terms.append(term)
                self.logger.debug(f"Future candidate English term detected: '{term}'")
        
        return srs_backed_terms, future_candidate_terms
    
    def _find_english_in_line(self, line: str) -> List[str]:
        """Find English words and phrases in a dialogue line."""
        english_terms = []
        
        # Split into words for individual detection
        words = re.findall(r'\b\w+\b', line.lower())
        
        # Detect individual English words and loanwords that could be deepened
        for word in words:
            classification = self.language_detector.classify_word(word)
            
            # Include pure English words AND loan words (for deepening to more authentic Filipino)
            if classification in ['english', 'loan']:
                english_terms.append(word)
        
        # Detect English multi-word phrases using dictionary-based approach
        english_phrases = self._detect_english_phrases(line)
        english_terms.extend(english_phrases)
        
        return list(set(english_terms))  # Remove duplicates
    
    def _detect_english_phrases(self, line: str) -> List[str]:
        """Detect English multi-word phrases using dictionary-based approach."""
        english_phrases = []
        line_lower = line.lower()
        words = re.findall(r'\b\w+\b', line_lower)
        
        # Check for 2-word and 3-word combinations
        for i in range(len(words)):
            # 2-word phrases
            if i < len(words) - 1:
                two_word = f"{words[i]} {words[i+1]}"
                if self._is_english_phrase(two_word):
                    english_phrases.append(two_word)
            
            # 3-word phrases  
            if i < len(words) - 2:
                three_word = f"{words[i]} {words[i+1]} {words[i+2]}"
                if self._is_english_phrase(three_word):
                    english_phrases.append(three_word)
        
        return english_phrases
    
    def _is_english_phrase(self, phrase: str) -> bool:
        """Check if a phrase is likely English based on dictionary classification."""
        words = phrase.split()
        
        if len(words) < 2:
            return False
        
        # Check classification of each word
        pure_english_count = 0
        filipino_count = 0
        
        for word in words:
            classification = self.language_detector.classify_word(word)
            if classification in ['english', 'loan']:
                pure_english_count += 1
            elif classification == 'tagalog':
                filipino_count += 1
        
        # Phrase is English/loanword if:
        # 1. Majority of words are English or loanwords, AND
        # 2. No pure Filipino particles are present
        return (pure_english_count > filipino_count and 
                pure_english_count >= len(words) * 0.5 and
                not self.language_detector.has_filipino_context(phrase))
    
    def _has_srs_equivalent(self, english_term: str) -> bool:
        """Check if English term has Filipino equivalent in SRS database."""
        try:
            # Search for Filipino equivalents in SRS database
            matches = self._search_srs_for_equivalent(english_term)
            return len(matches) > 0
        except Exception as e:
            self.logger.error(f"Error checking SRS equivalent for '{english_term}': {e}")
            return False
    
    def _search_srs_for_equivalent(self, english_term: str) -> List[Dict]:
        """Search SRS database for Filipino equivalents of English term."""
        search_queries = self._generate_search_queries(english_term)
        
        matches = []
        for query in search_queries:
            try:
                import sqlite3
                with sqlite3.connect(self.srs_db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT text, stability FROM collocations 
                        WHERE text LIKE ? AND stability >= 0.0
                        ORDER BY stability DESC
                        LIMIT 5
                    """, (f'%{query}%',))
                    
                    for row in cursor.fetchall():
                        matches.append({'text': row[0], 'stability': row[1]})
                        
            except Exception as e:
                self.logger.error(f"Error searching SRS for '{query}': {e}")
                continue
        
        return matches
    
    def _generate_search_queries(self, english_term: str) -> List[str]:
        """Generate potential Filipino search queries for English term."""
        queries = []
        
        # Always include the original term for direct matches
        queries.append(english_term)
        
        # For multi-word terms, also try without spaces
        if ' ' in english_term:
            queries.append(english_term.replace(' ', ''))
            
            # Try searching for individual words that might be Filipino equivalents
            words = english_term.split()
            queries.extend(words)
        
        # Try to find existing translations in the enhanced database
        if self.enhanced_db:
            try:
                filipino_equiv = self.enhanced_db.find_filipino_equivalent(english_term)
                if filipino_equiv:
                    queries.append(filipino_equiv)
                    # Also try words from the Filipino equivalent
                    filipino_words = filipino_equiv.split()
                    queries.extend(filipino_words)
            except Exception as e:
                self.logger.debug(f"Could not search enhanced database for '{english_term}': {e}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for query in queries:
            if query.lower() not in seen:
                seen.add(query.lower())
                unique_queries.append(query)
        
        return unique_queries


class SRSLLMEnforcer:
    """Uses LLM for grammar-aware SRS constraint enforcement instead of dictionary replacement."""
    
    def __init__(self, llm: MockLLM, srs_db: SRSDatabase, enhanced_db: Optional[EnhancedSRSDatabase] = None):
        self.llm = llm
        self.srs_db = srs_db
        self.enhanced_db = enhanced_db or EnhancedSRSDatabase()
        self.english_detector = DeterministicEnglishDetector(srs_db, enhanced_db)
        self.logger = logging.getLogger(__name__)
    
    def enforce_with_llm(self, content: str, day: int, context: str = "story") -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Use LLM for grammar-aware SRS enforcement that maintains proper Tagalog conjugation.
        Uses story-generated SRS analysis for targeted enforcement.
        Also extracts phrase translations during enforcement for efficiency.
        
        Args:
            content: Story content to enforce (includes SRS analysis section)
            day: Day number for context
            context: Generation context (e.g. "story", "strategy_deeper_generation")
            
        Returns:
            Tuple of (clean_enforced_content, violations_list, phrase_translations_list)
        """
        # Save original content before any SRS enforcement
        self._save_original_backup(content, day, context)
        
        # Extract SRS analysis from story content
        srs_analysis, analysis_found = self._extract_srs_analysis(content)
        
        if not analysis_found:
            self.logger.info("No SRS analysis found - skipping English enforcement, checking Key Phrases only")
            # Still check Key Phrases even if no SRS analysis
            clean_content = self._remove_srs_analysis_section(content)
            key_phrases_violations = self._check_key_phrases_violations(clean_content, day, context)
            if key_phrases_violations:
                self.logger.info(f"Key Phrases violations found: {len(key_phrases_violations)} (no SRS analysis, no replacements made)")
                return clean_content, key_phrases_violations, []
            return clean_content, [], []
        
        # Analysis was found - check if English terms need replacement
        if not srs_analysis:
            self.logger.info("SRS analysis found but no English terms need replacement - proceeding with Key Phrases check")
        
        # Extract English terms from analysis for LLM replacement (no pre-determined mappings)
        srs_english_terms = self._extract_english_terms_from_analysis(srs_analysis)
        
        # Get Key Phrases replacements as well
        clean_content = self._remove_srs_analysis_section(content)
        key_phrases_info = self._check_key_phrases_violations_with_replacements(clean_content, day, context)
        key_phrases_replacements = key_phrases_info.get('replacements', {})
        key_phrases_violations = key_phrases_info.get('violations', [])
        
        # If no replacements needed at all, skip LLM enforcement
        if not srs_english_terms and not key_phrases_replacements:
            self.logger.info("No SRS English terms or Key Phrases replacements needed - skipping LLM enforcement")
            return clean_content, key_phrases_violations, []
        
        self.logger.info(f"Found {len(srs_english_terms)} English terms for LLM replacement")
        for english in srs_english_terms:
            self.logger.debug(f"  English term: '{english}'")
        
        # Create prompt for LLM to intelligently replace both English terms and Key Phrases
        prompt = self._create_combined_enforcement_prompt(content, srs_english_terms, key_phrases_replacements, day)
        
        try:
            # Use LLM to do intelligent replacement for both English terms and Key Phrases, AND extract translations
            self.logger.info("Requesting combined LLM-based SRS enforcement (English terms + Key Phrases) and translation extraction...")
            response = self.llm.chat_response(
                system_prompt="You are a Filipino language expert helping with vocabulary and Key Phrases enforcement and translation extraction.",
                user_prompt=prompt,
                response_type="combined_srs_enforcement_with_translations"
            )
            
            # Extract the enforced content from LLM response
            enforced_content = self._extract_enforced_content(response)
            
            # Extract phrase translations from LLM response
            phrase_translations = self._extract_phrase_translations(response)
            
            # Remove SRS Analysis section from final content
            final_content = self._remove_srs_analysis_section(enforced_content)
            
            # Analyze what was replaced for logging (both English terms and Key Phrases)
            violations = self._analyze_replacements(content, final_content, srs_english_terms, day, context)
            
            # Update Key Phrases violations to show they were processed in main enforcement
            for violation in key_phrases_violations:
                if violation['english_text'] in key_phrases_replacements:
                    violation['was_replaced'] = True
                    violation['known_filipino'] = key_phrases_replacements[violation['english_text']]
            
            violations.extend(key_phrases_violations)
            
            # Check Key Phrases violations (no separate LLM pass - already handled in main enforcement)
            key_phrases_violations = self._check_key_phrases_violations(final_content, day, context)
            if key_phrases_violations:
                violations.extend(key_phrases_violations)
                self.logger.info(f"Key Phrases violations found: {len(key_phrases_violations)} (already processed in main enforcement)")
            
            self.logger.info(f"SRS enforcement complete: {len(violations)} total violations found")
            if phrase_translations:
                self.logger.info(f"Translation extraction complete: {len(phrase_translations)} translations extracted")
            
            return final_content, violations, phrase_translations
            
        except Exception as e:
            self.logger.error(f"LLM-based SRS enforcement failed: {e}")
            # Fallback to cleaned original content rather than crashing
            clean_content = self._remove_srs_analysis_section(content)
            return clean_content, [], []
    
    def _get_high_stability_replacements(self) -> Dict[str, str]:
        """Get English→Filipino replacements from enhanced translation database."""
        replacements = {}
        
        try:
            # Query enhanced database for translation pairs
            translation_pairs = self.enhanced_db.get_translation_pairs(active_only=True)
            
            for pair in translation_pairs:
                # Only include high-confidence pairs for SRS enforcement
                if pair.confidence >= 0.9:
                    replacements[pair.english.lower()] = pair.filipino
            
            self.logger.info(f"Loaded {len(replacements)} high-confidence translation pairs from enhanced database")
            
            # Also check for bidirectional mappings in enhanced collocations
            collocations = self.enhanced_db.get_bilingual_collocations(language='english')
            for collocation in collocations:
                if (collocation.filipino_equivalent and 
                    collocation.confidence and 
                    collocation.confidence >= 0.9):
                    replacements[collocation.text.lower()] = collocation.filipino_equivalent
            
        except Exception as e:
            self.logger.warning(f"Could not load translations from enhanced database: {e}")
            
            # Fallback to basic known mappings if enhanced database fails
            replacements = {
                "water": "tubig",
                "thank you": "salamat po", 
                "delicious": "masarap"
            }
            
        return replacements
    
    def enforce_with_deterministic_detection(self, content: str, day: int, context: str = "story") -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Enhanced enforcement using deterministic English detection + LLM replacement.
        
        This method combines reliable English detection with grammar-aware LLM replacement.
        
        Args:
            content: Story content to enforce
            day: Day number for context
            context: Generation context
            
        Returns:
            Tuple of (enforced_content, violations_list, phrase_translations_list)
        """
        # Save original content before any SRS enforcement
        self._save_original_backup(content, day, context)
        
        # 1. Deterministic English detection
        self.logger.info("Running deterministic English detection on dialogue...")
        srs_backed_terms, future_candidate_terms = self.english_detector.detect_english_terms(content)
        
        # Log detection results
        if srs_backed_terms:
            self.logger.info(f"Found {len(srs_backed_terms)} English terms with SRS equivalents: {srs_backed_terms}")
        else:
            self.logger.info("No English terms with SRS equivalents detected")
            
        if future_candidate_terms:
            self.logger.info(f"Found {len(future_candidate_terms)} English terms without SRS equivalents (future deepening candidates): {future_candidate_terms}")
            # TODO: Store these for future deepening iterations
        
        # 2. Check for existing SRS analysis and merge if present
        existing_analysis, analysis_found = self._extract_srs_analysis(content)
        
        if analysis_found:
            self.logger.info("Found existing LLM-generated SRS analysis - merging with deterministic detection")
            # Merge deterministic detection with existing analysis
            merged_terms = self._merge_english_term_lists(srs_backed_terms, existing_analysis)
        else:
            self.logger.info("No existing SRS analysis found - using deterministic detection only")
            merged_terms = srs_backed_terms
        
        # 3. Generate complete SRS analysis for LLM replacement
        if merged_terms:
            complete_srs_analysis = self._build_srs_analysis_from_terms(merged_terms)
            enhanced_content = self._inject_srs_analysis(content, complete_srs_analysis)
        else:
            enhanced_content = content
            complete_srs_analysis = []
        
        # 4. Run LLM-based grammar-aware replacement using complete analysis
        if complete_srs_analysis:
            self.logger.info(f"Running LLM enforcement with {len(complete_srs_analysis)} detected terms...")
            enforced_content, violations, translations = self._run_llm_replacement(enhanced_content, day, context, complete_srs_analysis)
        else:
            self.logger.info("No English terms detected for enforcement - returning original content")
            enforced_content = self._remove_srs_analysis_section(content)
            violations = []
            translations = []
        
        return enforced_content, violations, translations
    
    def _merge_english_term_lists(self, deterministic_terms: List[str], existing_analysis: List[Dict]) -> List[str]:
        """Merge deterministic detection with existing LLM analysis."""
        existing_terms = [term.get("english", "") for term in existing_analysis if term.get("english")]
        
        # Combine and deduplicate
        all_terms = list(set(deterministic_terms + existing_terms))
        
        self.logger.debug(f"Merged {len(deterministic_terms)} deterministic + {len(existing_terms)} LLM terms = {len(all_terms)} total")
        return all_terms
    
    def _build_srs_analysis_from_terms(self, english_terms: List[str]) -> List[Dict]:
        """Build SRS analysis JSON structure from detected English terms."""
        srs_analysis = []
        
        for term in english_terms:
            search_queries = self.english_detector._generate_search_queries(term)
            srs_analysis.append({
                "english": term,
                "srs_queries": search_queries
            })
        
        return srs_analysis
    
    def _inject_srs_analysis(self, content: str, srs_analysis: List[Dict]) -> str:
        """Inject or replace SRS analysis section in content."""
        # Remove existing SRS analysis if present
        content_without_analysis = self._remove_srs_analysis_section(content)
        
        # Add new comprehensive analysis
        analysis_json = {
            "english_terms": srs_analysis,
            "key_phrases_analysis": {
                "phrases": [],  # Will be filled by existing logic if needed
                "stability_threshold": 2.0,
                "replacement_suggestions": {}
            }
        }
        
        analysis_section = f"\n\n[NARRATOR]: SRS Enforcement Analysis\n{json.dumps(analysis_json, indent=2)}"
        
        return content_without_analysis + analysis_section
    
    def _run_llm_replacement(self, content: str, day: int, context: str, srs_analysis: List[Dict]) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Run the LLM-based replacement logic with complete SRS analysis."""
        # Use existing LLM enforcement logic
        return self.enforce_with_llm(content, day, context)
    
    def _extract_srs_analysis(self, content: str) -> Tuple[List[Dict], bool]:
        """
        Extract SRS analysis JSON from generated story content.
        
        Returns:
            Tuple of (english_terms_list, analysis_found)
            - english_terms_list: List of English terms to replace (could be empty)
            - analysis_found: True if SRS analysis section was found, False otherwise
        """
        # Look for [NARRATOR]: SRS Enforcement Analysis section
        if "[NARRATOR]: SRS Enforcement Analysis" in content:
            english_terms = self._parse_srs_json(content)
            return english_terms, True  # Analysis section found, even if english_terms is empty
        else:
            # Fallback: Parse Translated section
            self.logger.warning("No SRS analysis found - parsing Translated section (results would be better with story re-generation)")
            english_terms = self._parse_translated_section_fallback(content)
            return english_terms, False  # No analysis section found
    
    def _parse_srs_json(self, content: str) -> List[Dict]:
        """Parse SRS analysis JSON from story content."""
        try:
            # Find the SRS Enforcement Analysis section and extract everything after it
            srs_start = content.find("[NARRATOR]: SRS Enforcement Analysis")
            if srs_start == -1:
                self.logger.warning("SRS Enforcement Analysis section header not found")
                return []
            
            # Get content after the SRS header
            remaining_content = content[srs_start:].split('\n', 1)
            if len(remaining_content) < 2:
                self.logger.warning("No content found after SRS Enforcement Analysis header")
                return []
            
            srs_content = remaining_content[1]
            
            # Find JSON block - look for opening brace and match braces
            json_start = srs_content.find('{')
            if json_start == -1:
                self.logger.warning("No JSON opening brace found in SRS section")
                return []
            
            # Find the matching closing brace
            brace_count = 0
            json_end = -1
            for i, char in enumerate(srs_content[json_start:], json_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            
            if json_end == -1:
                self.logger.warning("No matching closing brace found for SRS JSON")
                return []
            
            # Extract and parse JSON
            json_str = srs_content[json_start:json_end].strip()
            self.logger.debug(f"Extracted JSON string: {json_str[:200]}...")
            
            analysis_data = json.loads(json_str)
            return analysis_data.get("english_terms", [])
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse SRS analysis JSON: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error parsing SRS analysis: {e}")
            return []
    
    def _parse_translated_section_fallback(self, content: str) -> List[Dict]:
        """Parse Translated section when no SRS analysis available (fallback)."""
        try:
            # Extract English terms from Translated alternating pattern:
            # [TAGALOG-MALE-1]: Filipino text
            # [NARRATOR]: English translation
            
            translated_section = self._extract_translated_section(content)
            if not translated_section:
                return []
            
            english_terms = []
            lines = translated_section.split('\n')
            
            for i, line in enumerate(lines):
                # Look for [NARRATOR]: English translation lines
                if line.strip().startswith('[NARRATOR]:') and i > 0:
                    # Check if previous line was a Tagalog speaker
                    prev_line = lines[i-1].strip()
                    if re.match(r'\[TAGALOG-\w+-\d+\]:', prev_line):
                        english_text = line.replace('[NARRATOR]:', '').strip()
                        
                        # Extract individual English words/phrases that could be replaced
                        english_words = self._extract_replaceable_english(english_text)
                        for word in english_words:
                            english_terms.append({
                                "english": word,
                                "srs_queries": self._generate_fallback_queries(word)
                            })
            
            # Remove duplicates
            seen = set()
            unique_terms = []
            for term in english_terms:
                key = term["english"].lower()
                if key not in seen:
                    seen.add(key)
                    unique_terms.append(term)
            
            return unique_terms
            
        except Exception as e:
            self.logger.error(f"Error in translated section fallback parsing: {e}")
            return []
    
    def _extract_translated_section(self, content: str) -> str:
        """Extract the Translated section from story content."""
        # Find the Translated section
        pattern = r'\[NARRATOR\]: Translated\s*\n(.*?)(?=\n\[NARRATOR\]: SRS Enforcement Analysis|\n\*\*|$)'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        return ""
    
    def _extract_replaceable_english(self, english_text: str) -> List[str]:
        """Extract English words/phrases that could be replaced with Filipino."""
        # Simple approach: extract common replaceable patterns
        replaceable = []
        
        # Common phrases to look for
        common_phrases = [
            "good morning", "good afternoon", "good evening",
            "thank you", "excuse me", "how much", "how are you",
            "welcome", "fresh", "delicious", "drinks", "water"
        ]
        
        text_lower = english_text.lower()
        for phrase in common_phrases:
            if phrase in text_lower:
                replaceable.append(phrase)
        
        return replaceable
    
    def _generate_fallback_queries(self, english_word: str) -> List[str]:
        """Generate basic SRS query terms for fallback parsing."""
        # Simple mapping for common terms
        query_map = {
            "good morning": ["magandang umaga", "good morning", "umaga"],
            "good afternoon": ["magandang hapon", "good afternoon", "hapon"],
            "good evening": ["magandang gabi", "good evening", "gabi"],
            "thank you": ["salamat", "thank you", "thanks"],
            "excuse me": ["paumanhin", "excuse", "sorry"],
            "how much": ["magkano", "how much", "presyo"],
            "how are you": ["kumusta", "how are you", "musta"],
            "welcome": ["welcome", "maligayang pagdating", "pagdating"],
            "fresh": ["fresh", "sariwang", "sariwa"],
            "delicious": ["masarap", "delicious", "sarap"],
            "drinks": ["drinks", "inumin", "softdrinks"],
            "water": ["tubig", "water", "inumin"]
        }
        
        return query_map.get(english_word.lower(), [english_word, english_word.replace(" ", "")])
    
    def _extract_english_terms_from_analysis(self, srs_analysis: List[Dict]) -> List[str]:
        """Extract English terms from SRS analysis for LLM replacement."""
        english_terms = []
        
        for term_analysis in srs_analysis:
            english = term_analysis.get("english", "")
            if english:
                english_terms.append(english)
                self.logger.debug(f"Found English term for LLM replacement: '{english}'")
        
        return english_terms
    
    def _search_srs_database(self, search_term: str, min_stability: float = 0.0) -> List[Dict]:
        """Search SRS database for entries containing search term."""
        try:
            import sqlite3
            with sqlite3.connect(self.srs_db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT text, stability FROM collocations 
                    WHERE text LIKE ? AND stability >= ?
                    ORDER BY stability DESC
                    LIMIT 10
                """, (f'%{search_term}%', min_stability))
                
                return [{'text': row[0], 'stability': row[1]} for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Error searching SRS database for '{search_term}': {e}")
            return []
    
    def _remove_srs_analysis_section(self, content: str) -> str:
        """Remove SRS Analysis section from final content."""
        # Remove the SRS Enforcement Analysis section
        pattern = r'\n\[NARRATOR\]: SRS Enforcement Analysis.*?(?=\n\[NARRATOR\]:|$)'
        cleaned = re.sub(pattern, '', content, flags=re.DOTALL)
        
        # Also remove any trailing SRS analysis at the end of the file
        pattern2 = r'\n\[NARRATOR\]: SRS Enforcement Analysis.*$'
        cleaned = re.sub(pattern2, '', cleaned, flags=re.DOTALL)
        
        return cleaned.strip()
    
    def _extract_key_phrases(self, content: str) -> List[str]:
        """Extract Tagalog phrases from Key Phrases section."""
        try:
            # Find the Key Phrases section
            key_phrases_pattern = r'Key Phrases:\s*\n(.*?)(?=\n\[NARRATOR\]: Natural Speed|\n\*\*|$)'
            match = re.search(key_phrases_pattern, content, re.DOTALL | re.IGNORECASE)
            
            if not match:
                self.logger.debug("No Key Phrases section found")
                return []
            
            key_phrases_content = match.group(1).strip()
            phrases = []
            
            # Extract phrases from [TAGALOG-FEMALE-1]: pattern
            # Skip the syllable breakdown lines and English translations
            lines = key_phrases_content.split('\n')
            current_phrase = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for Tagalog speaker lines that contain actual phrases
                if re.match(r'\[TAGALOG-[A-Z]+-\d+\]:', line):
                    phrase_text = re.sub(r'\[TAGALOG-[A-Z]+-\d+\]:\s*', '', line).strip()
                    
                    # Skip if this is a single syllable or very short fragment
                    if len(phrase_text) > 2 and ' ' in phrase_text:
                        # This looks like a complete phrase
                        if phrase_text not in phrases:
                            phrases.append(phrase_text)
                            current_phrase = phrase_text
                            self.logger.debug(f"Extracted Key Phrase: '{phrase_text}'")
                elif line.startswith('[NARRATOR]:') and 'thank you' in line.lower():
                    # Skip English translations
                    continue
                elif current_phrase and line == current_phrase:
                    # Skip repeated phrase lines
                    continue
            
            self.logger.info(f"Extracted {len(phrases)} Key Phrases from content")
            return phrases
            
        except Exception as e:
            self.logger.error(f"Error extracting Key Phrases: {e}")
            return []
    
    def _check_key_phrases_against_srs(self, phrases: List[str], stability_threshold: float = 2.0) -> Dict:
        """Check Key Phrases against SRS database for already-known collocations."""
        results = {
            "already_known": [],      # High stability - violation
            "reinforcement_ok": [],   # Medium stability - acceptable  
            "truly_new": []          # Not in SRS - ideal
        }
        
        for phrase in phrases:
            # Search SRS database for this phrase or similar collocations
            matches = self._search_srs_database(phrase, min_stability=0.0)
            
            if matches:
                # Find the best match (highest stability)
                best_match = max(matches, key=lambda x: x['stability'])
                
                if best_match['stability'] >= stability_threshold:
                    results["already_known"].append({
                        "phrase": phrase,
                        "stability": best_match['stability'],
                        "matched_text": best_match['text']
                    })
                    self.logger.debug(f"Key Phrase violation: '{phrase}' matches '{best_match['text']}' (stability: {best_match['stability']})")
                else:
                    results["reinforcement_ok"].append({
                        "phrase": phrase,
                        "stability": best_match['stability'],
                        "matched_text": best_match['text']
                    })
            else:
                results["truly_new"].append(phrase)
                self.logger.debug(f"Key Phrase truly new: '{phrase}'")
        
        return results
    
    def _create_key_phrases_violations(self, key_phrases_analysis: Dict, day: int, context: str) -> List[Dict[str, Any]]:
        """Create violation records for Key Phrases that are already well-known."""
        violations = []
        
        for already_known in key_phrases_analysis.get("already_known", []):
            violation = {
                "day": day,
                "english_text": already_known["phrase"],  # Using the phrase as "english_text" 
                "known_filipino": already_known["matched_text"],
                "violation_type": "key_phrases_redundancy",
                "was_replaced": False,  # Key Phrases violations are flagged, not replaced
                "context": context,
                "stability": already_known["stability"]
            }
            violations.append(violation)
            
        return violations
    
    def _store_key_phrases_violations(self, violations: List[Dict[str, Any]]):
        """Store Key Phrases violations in the database."""
        try:
            import sqlite3
            with sqlite3.connect(self.srs_db.db_path) as conn:
                cursor = conn.cursor()
                
                for violation in violations:
                    cursor.execute("""
                        INSERT INTO srs_violations 
                        (day, english_text, known_filipino, violation_type, was_replaced, context)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        violation["day"],
                        violation["english_text"],
                        violation["known_filipino"],
                        violation["violation_type"],
                        violation["was_replaced"],
                        violation["context"]
                    ))
                
                self.logger.info(f"Stored {len(violations)} Key Phrases violations in database")
                
        except Exception as e:
            self.logger.error(f"Error storing Key Phrases violations: {e}")
    
    def _check_key_phrases_violations(self, content: str, day: int, context: str) -> List[Dict[str, Any]]:
        """Comprehensive Key Phrases violation checking workflow."""
        try:
            # First, try to extract Key Phrases analysis from SRS JSON
            key_phrases_from_analysis = self._extract_key_phrases_from_srs_analysis(content)
            
            # If not available, extract directly from content
            if not key_phrases_from_analysis:
                key_phrases_from_analysis = self._extract_key_phrases(content)
            
            if not key_phrases_from_analysis:
                self.logger.debug("No Key Phrases found for violation checking")
                return []
            
            # Check against SRS database for high stability
            stability_threshold = 2.0  # Default threshold from plan
            key_phrases_analysis = self._check_key_phrases_against_srs(key_phrases_from_analysis, stability_threshold)
            
            # Create violation records
            violations = self._create_key_phrases_violations(key_phrases_analysis, day, context)
            
            # Store violations in database
            if violations:
                self._store_key_phrases_violations(violations)
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Error in Key Phrases violation checking: {e}")
            return []
    
    def _extract_key_phrases_from_srs_analysis(self, content: str) -> List[str]:
        """Extract Key Phrases from SRS analysis JSON if available."""
        try:
            # Parse SRS analysis section
            srs_analysis_raw = self._parse_srs_json_raw(content)
            if not srs_analysis_raw:
                return []
            
            key_phrases_analysis = srs_analysis_raw.get("key_phrases_analysis", {})
            phrases = key_phrases_analysis.get("phrases", [])
            
            self.logger.debug(f"Extracted {len(phrases)} Key Phrases from SRS analysis")
            return phrases
            
        except Exception as e:
            self.logger.debug(f"Could not extract Key Phrases from SRS analysis: {e}")
            return []
    
    def _parse_srs_json_raw(self, content: str) -> Dict:
        """Parse complete SRS analysis JSON (not just english_terms)."""
        try:
            # Find the SRS Enforcement Analysis section and extract everything after it
            srs_start = content.find("[NARRATOR]: SRS Enforcement Analysis")
            if srs_start == -1:
                return {}
            
            # Get content after the SRS header
            remaining_content = content[srs_start:].split('\n', 1)
            if len(remaining_content) < 2:
                return {}
            
            srs_content = remaining_content[1]
            
            # Find JSON block - look for opening brace and match braces
            json_start = srs_content.find('{')
            if json_start == -1:
                return {}
            
            # Find the matching closing brace
            brace_count = 0
            json_end = -1
            for i, char in enumerate(srs_content[json_start:], json_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            
            if json_end == -1:
                return {}
            
            # Extract and parse JSON
            json_str = srs_content[json_start:json_end].strip()
            return json.loads(json_str)
                
        except json.JSONDecodeError as e:
            self.logger.debug(f"Failed to parse SRS analysis JSON: {e}")
            return {}
        except Exception as e:
            self.logger.debug(f"Error parsing SRS analysis: {e}")
            return {}
    
    def _find_key_phrases_alternatives(self, high_stability_phrases: List[str], max_alternatives: int = 3) -> Dict[str, List[str]]:
        """Find low-stability alternatives from SRS database for high-stability phrases, ensuring uniqueness."""
        alternatives = {}
        used_alternatives = set()  # Track used alternatives to prevent duplicates
        
        try:
            import sqlite3
            with sqlite3.connect(self.srs_db.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all available low-stability alternatives first
                cursor.execute("""
                    SELECT text, stability 
                    FROM collocations 
                    WHERE stability < 1.0 
                    ORDER BY stability ASC, RANDOM()
                """)
                low_stability_pool = cursor.fetchall()
                
                # If not enough low-stability alternatives, add medium stability ones
                if len(low_stability_pool) < len(high_stability_phrases) * max_alternatives:
                    cursor.execute("""
                        SELECT text, stability 
                        FROM collocations 
                        WHERE stability >= 1.0 AND stability < 1.8
                        ORDER BY stability ASC, RANDOM()
                    """)
                    medium_stability_pool = cursor.fetchall()
                    all_candidates = low_stability_pool + medium_stability_pool
                else:
                    all_candidates = low_stability_pool
                
                # Distribute unique alternatives to each phrase
                candidate_index = 0
                for phrase in high_stability_phrases:
                    phrase_alternatives = []
                    attempts = 0
                    max_attempts = len(all_candidates)  # Prevent infinite loops
                    
                    while len(phrase_alternatives) < max_alternatives and attempts < max_attempts:
                        if candidate_index >= len(all_candidates):
                            candidate_index = 0  # Wrap around if needed
                        
                        candidate_text, candidate_stability = all_candidates[candidate_index]
                        candidate_index += 1
                        attempts += 1
                        
                        # Skip if already used or is the same as the phrase we're replacing
                        if candidate_text not in used_alternatives and candidate_text != phrase:
                            phrase_alternatives.append(candidate_text)
                            used_alternatives.add(candidate_text)
                    
                    alternatives[phrase] = phrase_alternatives
                    if phrase_alternatives:
                        self.logger.debug(f"Found {len(phrase_alternatives)} unique alternatives for '{phrase}': {phrase_alternatives}")
                    else:
                        self.logger.warning(f"No unique alternatives found for '{phrase}'")
                            
        except Exception as e:
            self.logger.error(f"Error finding Key Phrases alternatives: {e}")
            
        return alternatives
    
    def _select_best_alternatives_from_suggestions(self, replacement_suggestions: Dict[str, List[str]], 
                                                 high_stability_phrases: List[str]) -> Dict[str, str]:
        """Select the best alternative from LLM suggestions based on SRS stability."""
        selected_replacements = {}
        
        try:
            import sqlite3
            with sqlite3.connect(self.srs_db.db_path) as conn:
                cursor = conn.cursor()
                
                for phrase in high_stability_phrases:
                    suggestions = replacement_suggestions.get(phrase, [])
                    if not suggestions:
                        continue
                    
                    # Find the suggestion with lowest stability
                    best_alternative = None
                    lowest_stability = float('inf')
                    
                    for suggestion in suggestions:
                        # Check stability of this suggestion
                        cursor.execute("""
                            SELECT stability FROM collocations 
                            WHERE text = ?
                        """, (suggestion,))
                        
                        result = cursor.fetchone()
                        if result:
                            stability = result[0]
                            if stability < lowest_stability:
                                lowest_stability = stability
                                best_alternative = suggestion
                        else:
                            # If not in SRS, it's truly new (stability 0.0)
                            lowest_stability = 0.0
                            best_alternative = suggestion
                            break
                    
                    if best_alternative:
                        selected_replacements[phrase] = best_alternative
                        self.logger.debug(f"Selected '{best_alternative}' (stability: {lowest_stability}) to replace '{phrase}'")
                    else:
                        self.logger.warning(f"No suitable alternative found for '{phrase}'")
                        
        except Exception as e:
            self.logger.error(f"Error selecting best alternatives: {e}")
            
        return selected_replacements
    
    def _create_key_phrases_replacement_prompt(self, content: str, key_phrases_replacements: Dict[str, str], day: int) -> str:
        """Create LLM prompt for Key Phrases replacement (second pass)."""
        
        replacement_list = "\n".join([
            f"• '{old_phrase}' → '{new_phrase}'" 
            for old_phrase, new_phrase in key_phrases_replacements.items()
        ])
        
        return f"""You are helping replace high-stability Key Phrases with new vocabulary for Day {day} Filipino language learning content.

TASK: Replace ONLY the specified phrases in the Key Phrases section with their alternatives.

CONTENT TO MODIFY:
{content}

KEY PHRASES REPLACEMENTS TO MAKE:
{replacement_list}

REPLACEMENT RULES:

1. **ONLY modify the Key Phrases section** - Do not change Natural Speed, Slow Speed, or Translated sections
2. **Replace specified phrases** - Replace only the main phrase and English translation lines
3. **Add new phrases if specified** - If replacements include "__ADD_PHRASE_X__" entries, add them as new Key Phrases
4. **Update English translations** - Provide appropriate English translations for new/replacement phrases
5. **Maintain format structure** - Keep the exact same format with [TAGALOG-FEMALE-1]: and [NARRATOR]: lines
6. **Preserve syllable breakdowns** - Keep all existing syllable breakdown lines unchanged (they will be regenerated automatically)
7. **Preserve other phrases** - Only replace the specified phrases, keep all others unchanged

EXAMPLE:

BEFORE:
[TAGALOG-FEMALE-1]: salamat po
[NARRATOR]: thank you
salamat po
po
mat
la
lamat
sa
salamat
salamat po
salamat po

AFTER (if replacing "salamat po" → "maraming salamat"):
[TAGALOG-FEMALE-1]: maraming salamat
[NARRATOR]: thank you very much
salamat po
po
mat
la
lamat
sa
salamat
salamat po
salamat po

EXAMPLE FOR ADDING NEW PHRASES (if "__ADD_PHRASE_0__" → "ingat po kayo"):

[TAGALOG-FEMALE-1]: ingat po kayo
[NARRATOR]: take care
ingat po kayo
yo
kayo
po
po kayo
gat
ingat
ingat po
ingat po kayo
ingat po kayo

Note: Syllable breakdowns will be automatically regenerated after replacement, so keep existing ones unchanged for now.

Return the complete story content with ONLY the Key Phrases section phrase and translation lines modified."""
    
    def _enforce_key_phrases_replacements(self, content: str, day: int, context: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Complete Key Phrases enforcement with replacement workflow."""
        try:
            # Step 1: Check for Key Phrases violations
            violations_info = self._check_key_phrases_violations_with_replacements(content, day, context)
            
            if not violations_info or not violations_info.get('replacements'):
                self.logger.debug("No Key Phrases replacements needed")
                return content, violations_info.get('violations', [])
            
            replacements = violations_info['replacements']
            violations = violations_info['violations']
            
            self.logger.info(f"Performing Key Phrases replacements for {len(replacements)} phrases")
            
            # Step 2: Create replacement prompt for second LLM pass
            replacement_prompt = self._create_key_phrases_replacement_prompt(content, replacements, day)
            
            # Step 3: Execute second LLM pass for Key Phrases replacement
            self.logger.info("Requesting Key Phrases replacement (second LLM pass)...")
            response = self.llm.chat_response(
                system_prompt="You are a Filipino language expert helping with Key Phrases replacement.",
                user_prompt=replacement_prompt,
                response_type="key_phrases_replacement"
            )
            
            # Step 4: Extract the modified content
            modified_content = self._extract_enforced_content(response)
            
            # Step 5: Update violation records to show successful replacements
            for violation in violations:
                if violation['english_text'] in replacements:
                    violation['was_replaced'] = True
                    violation['known_filipino'] = replacements[violation['english_text']]
            
            # Step 6: Update database records with replacement information
            self._update_key_phrases_violations_with_replacements(violations, replacements, day, context)
            
            self.logger.info(f"Key Phrases replacement complete: {len(replacements)} phrases replaced")
            
            return modified_content, violations
            
        except Exception as e:
            self.logger.error(f"Key Phrases replacement failed: {e}")
            # Fallback: still return violations for flagging, but no content modification
            fallback_violations = self._check_key_phrases_violations(content, day, context)
            return content, fallback_violations
    
    def _check_key_phrases_violations_with_replacements(self, content: str, day: int, context: str) -> Dict[str, Any]:
        """Enhanced Key Phrases violation checking that also prepares replacements."""
        try:
            # Get Key Phrases from content and SRS analysis
            key_phrases_from_analysis = self._extract_key_phrases_from_srs_analysis(content)
            
            if not key_phrases_from_analysis:
                key_phrases_from_analysis = self._extract_key_phrases(content)
            
            if not key_phrases_from_analysis:
                return {'violations': [], 'replacements': {}}
            
            # Check stability against SRS database
            stability_threshold = 2.0
            analysis = self._check_key_phrases_against_srs(key_phrases_from_analysis, stability_threshold)
            
            if not analysis.get('already_known'):
                return {'violations': [], 'replacements': {}}
            
            # Get high-stability phrases that need replacement
            high_stability_phrases = [item['phrase'] for item in analysis['already_known']]
            
            # Try to get replacement suggestions from SRS analysis first
            srs_analysis_raw = self._parse_srs_json_raw(content)
            replacement_suggestions = srs_analysis_raw.get('key_phrases_analysis', {}).get('replacement_suggestions', {})
            
            # Select best alternatives from LLM suggestions or SRS database
            replacements = {}
            if replacement_suggestions:
                replacements = self._select_best_alternatives_from_suggestions(
                    replacement_suggestions, high_stability_phrases
                )
            
            # For phrases without LLM suggestions, find alternatives from SRS
            phrases_without_replacements = [p for p in high_stability_phrases if p not in replacements]
            if phrases_without_replacements:
                srs_alternatives = self._find_key_phrases_alternatives(phrases_without_replacements)
                for phrase, alternatives in srs_alternatives.items():
                    if alternatives and phrase not in replacements:
                        replacements[phrase] = alternatives[0]  # Use the lowest stability alternative
            
            # Ensure Key Phrases count stays around 5 by adding more phrases if needed
            replacements = self._ensure_key_phrases_count(key_phrases_from_analysis, replacements)
            
            # Create violation records
            violations = []
            for item in analysis['already_known']:
                phrase = item['phrase']
                violation = {
                    "day": day,
                    "english_text": phrase,
                    "known_filipino": item['matched_text'],
                    "violation_type": "key_phrases_redundancy",
                    "was_replaced": phrase in replacements,  # Will be True if we're replacing it
                    "context": context,
                    "stability": item['stability']
                }
                violations.append(violation)
            
            # Store violations in database
            if violations:
                self._store_key_phrases_violations(violations)
            
            return {
                'violations': violations,
                'replacements': replacements
            }
            
        except Exception as e:
            self.logger.error(f"Error in Key Phrases violation checking with replacements: {e}")
            return {'violations': [], 'replacements': {}}
    
    def _update_key_phrases_violations_with_replacements(self, violations: List[Dict], replacements: Dict[str, str], 
                                                       day: int, context: str):
        """Update database records with Key Phrases replacement information."""
        try:
            import sqlite3
            with sqlite3.connect(self.srs_db.db_path) as conn:
                cursor = conn.cursor()
                
                for violation in violations:
                    if violation['english_text'] in replacements:
                        # Update the database record with replacement information
                        cursor.execute("""
                            UPDATE srs_violations 
                            SET known_filipino = ?, was_replaced = 1
                            WHERE day = ? AND english_text = ? AND violation_type = 'key_phrases_redundancy' 
                            AND context = ?
                        """, (
                            replacements[violation['english_text']],
                            day,
                            violation['english_text'],
                            context
                        ))
                
                updated_count = cursor.rowcount if hasattr(cursor, 'rowcount') else len([v for v in violations if v['english_text'] in replacements])
                self.logger.debug(f"Updated {updated_count} Key Phrases violation records with replacement info")
                
        except Exception as e:
            self.logger.error(f"Error updating Key Phrases violation records: {e}")
    
    def _ensure_key_phrases_count(self, current_phrases: List[str], replacements: Dict[str, str], 
                                 target_count: int = 5) -> Dict[str, str]:
        """Ensure Key Phrases section maintains target count by adding low-stability phrases if needed."""
        # Calculate final count after replacements
        final_count = len(current_phrases)  # All original phrases remain, some just get replaced
        
        if final_count >= target_count:
            self.logger.debug(f"Key Phrases count sufficient: {final_count} >= {target_count}")
            return replacements  # No need to add more phrases
        
        needed_count = target_count - final_count
        self.logger.info(f"Adding {needed_count} additional Key Phrases to reach target of {target_count}")
        
        try:
            import sqlite3
            with sqlite3.connect(self.srs_db.db_path) as conn:
                cursor = conn.cursor()
                
                # Find low-stability phrases that aren't already in the Key Phrases section
                excluded_phrases = current_phrases + list(replacements.values())
                placeholders = ','.join(['?' for _ in excluded_phrases])
                
                cursor.execute(f"""
                    SELECT text, stability 
                    FROM collocations 
                    WHERE stability < 1.5 
                    AND text NOT IN ({placeholders})
                    AND LENGTH(text) > 3
                    ORDER BY stability ASC, RANDOM()
                    LIMIT ?
                """, excluded_phrases + [needed_count])
                
                additional_phrases = cursor.fetchall()
                
                if additional_phrases:
                    # Add new phrases as "additions" (no replacement, just new entries)
                    extended_replacements = replacements.copy()
                    for i, (phrase, stability) in enumerate(additional_phrases):
                        # Use a placeholder key to indicate this is an addition
                        addition_key = f"__ADD_PHRASE_{i}__"
                        extended_replacements[addition_key] = phrase
                        self.logger.debug(f"Adding new Key Phrase: '{phrase}' (stability: {stability})")
                    
                    return extended_replacements
                else:
                    self.logger.warning(f"Could not find enough low-stability phrases to add ({needed_count} needed)")
                    return replacements
                    
        except Exception as e:
            self.logger.error(f"Error ensuring Key Phrases count: {e}")
            return replacements
    
    def _create_combined_enforcement_prompt(self, content: str, srs_english_terms: List[str], 
                                          key_phrases_replacements: Dict[str, str], day: int) -> str:
        """Create LLM prompt for combined English terms, Key Phrases enforcement, AND translation extraction."""
        
        # Build combined replacement list
        replacement_sections = []
        
        if srs_english_terms:
            english_list = "\n".join([
                f"• '{english}'" 
                for english in srs_english_terms
            ])
            replacement_sections.append(f"**ENGLISH TERMS TO REPLACE:**\nReplace these English terms with appropriate Filipino equivalents:\n{english_list}")
        
        if key_phrases_replacements:
            # Handle both regular replacements and new phrase additions
            key_phrases_list = []
            additions_list = []
            
            for old_phrase, new_phrase in key_phrases_replacements.items():
                if old_phrase.startswith("__ADD_PHRASE_"):
                    additions_list.append(f"• Add: '{new_phrase}'")
                else:
                    key_phrases_list.append(f"• '{old_phrase}' → '{new_phrase}'")
            
            if key_phrases_list:
                replacement_sections.append(f"**KEY PHRASES TO REPLACE:**\n" + "\n".join(key_phrases_list))
            if additions_list:
                replacement_sections.append(f"**KEY PHRASES TO ADD:**\n" + "\n".join(additions_list))
        
        all_replacements = "\n\n".join(replacement_sections)
        
        return f"""You are helping enforce SRS vocabulary and Key Phrases constraints AND extract comprehensive translations from Filipino language learning content for Day {day}.

ORIGINAL CONTENT TO REVIEW:
{content}

REPLACEMENTS TO MAKE:
{all_replacements}

## TASK 1: ENFORCEMENT RULES

1. **ENGLISH TERMS REPLACEMENT (in dialogue sections):**
   - Replace English terms with Filipino equivalents in Tagalog speaker lines
   - Maintain proper Tagalog grammar and conjugation
   - Consider context: "It's delicious" → "Masarap ito" (NOT "It's masarap")
   - Keep English translations in [NARRATOR]: lines unchanged

2. **KEY PHRASES REPLACEMENT (integrate throughout story):**
   - Replace specified phrases in the Key Phrases section AND integrate them into dialogue sections
   - In Key Phrases section: Replace phrase and English translation lines
   - In Natural Speed/Slow Speed/Translated sections: Use new Key Phrases in appropriate dialogue context
   - Add new phrases if specified with "__ADD_PHRASE_X__" entries
   - Keep syllable breakdown lines unchanged (they will be regenerated)
   - Maintain pedagogical flow: Key Phrases → Natural Speed reinforcement → Complete comprehension

3. **INTELLIGENT REPLACEMENT:**
   - Only replace when it improves authenticity without breaking comprehension
   - Ensure replacements sound natural to Filipino speakers
   - If unsure about a replacement, keep the original

## TASK 2: TRANSLATION EXTRACTION

Additionally, extract comprehensive Filipino-to-English translation pairs from the Translated section at MULTIPLE GRANULARITIES:

### 1. Complete Phrases (High Priority)
- Useful phrases and expressions for language learning
- Common greetings, polite forms, and everyday expressions  
- Complete meaningful phrases that have clear English equivalents

### 2. Common Collocations (Medium Priority)  
- 2-3 word combinations that appear frequently
- Useful word patterns and constructions
- Partial phrases that teach grammar patterns

### 3. Individual Words (Lower Priority)
- Important vocabulary words
- Single words that provide learning value
- Common particles and function words

## RESPONSE FORMAT

Return the enforced content as clean, copyable text followed by translations in JSON format:

COMPLETE_STORY_CONTENT_WITH_REPLACEMENTS_APPLIED_HERE

PHRASE_TRANSLATIONS:
{{
  "magandang umaga po": "good morning (polite)",
  "salamat sa lahat": "thank you for everything", 
  "alas dos": "two o'clock",
  "sukli mo": "your change",
  "tubig": "water",
  "po": "(polite marker)"
}}

## TRANSLATION GUIDELINES:
- Extract 50-150 translations total (comprehensive coverage)
- Include translations at all granularities: complete phrases, collocations, single words
- Include politeness markers in English (e.g., "po" → "(polite)")
- Prioritize frequent/useful items that would benefit language learners
- Provide contextual translations even for fragments ("sukli mo" → "your change")
- Focus on items that provide learning value at any granularity level

EXAMPLE ENFORCEMENT TRANSFORMATIONS:

**English Terms in Dialogue:**
BEFORE: [TAGALOG-FEMALE-1]: I need some water please
AFTER:  [TAGALOG-FEMALE-1]: Kailangan ko po ng tubig

**Key Phrases Integration:**
BEFORE Key Phrases: [TAGALOG-FEMALE-1]: salamat po
                    [NARRATOR]: thank you
AFTER Key Phrases:  [TAGALOG-FEMALE-1]: maraming salamat  
                    [NARRATOR]: thank you very much

BEFORE Dialogue: [TAGALOG-FEMALE-1]: Salamat po! Reserve po namin for tomorrow.
AFTER Dialogue:  [TAGALOG-FEMALE-1]: Maraming salamat! Reserve po namin for tomorrow.

This ensures learners study "maraming salamat" in Key Phrases and then hear it reinforced in Natural Speed dialogue."""

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
        """Extract the enforced content from LLM response (handles text-first and JSON formats)."""
        import json
        
        # First, get the raw response content
        raw_content = None
        if 'response' in response and 'choices' in response['response']:
            raw_content = response['response']['choices'][0]['message']['content'].strip()
        elif 'choices' in response:
            raw_content = response['choices'][0]['message']['content'].strip()
        elif isinstance(response, str):
            raw_content = response.strip()
        else:
            raise ValueError(f"Invalid LLM response format: {type(response)}")
        
        # Check for new text-first format with PHRASE_TRANSLATIONS: marker
        if "PHRASE_TRANSLATIONS:" in raw_content:
            # Split on PHRASE_TRANSLATIONS: marker and take everything before it
            content_parts = raw_content.split("PHRASE_TRANSLATIONS:")
            if len(content_parts) >= 2:
                return content_parts[0].strip()
        
        # Try to parse as JSON (old combined format)
        try:
            parsed_response = json.loads(raw_content)
            if 'enforced_content' in parsed_response:
                # Old JSON format with enforced_content
                return parsed_response['enforced_content']
        except (json.JSONDecodeError, TypeError):
            # Not JSON or doesn't have enforced_content, treat as direct content
            pass
        
        # Fallback to treating entire content as the story
        return raw_content
    
    def _extract_phrase_translations(self, response: Dict) -> List[Dict[str, Any]]:
        """Extract phrase translations from LLM response (handles text-first and JSON formats)."""
        import json
        
        # First, get the raw response content
        raw_content = None
        if 'response' in response and 'choices' in response['response']:
            raw_content = response['response']['choices'][0]['message']['content'].strip()
        elif 'choices' in response:
            raw_content = response['choices'][0]['message']['content'].strip()
        elif isinstance(response, str):
            raw_content = response.strip()
        else:
            self.logger.warning(f"Invalid LLM response format for translation extraction: {type(response)}")
            return []
        
        # Check for new text-first format with PHRASE_TRANSLATIONS: marker
        if "PHRASE_TRANSLATIONS:" in raw_content:
            # Split on PHRASE_TRANSLATIONS: marker and parse JSON from the second part
            content_parts = raw_content.split("PHRASE_TRANSLATIONS:")
            if len(content_parts) >= 2:
                json_part = content_parts[1].strip()
                try:
                    translations_dict = json.loads(json_part)
                    # Convert dictionary format to list format for consistency
                    translations = [
                        {"filipino": filipino, "english": english, "confidence": 0.9}
                        for filipino, english in translations_dict.items()
                    ]
                    self.logger.info(f"Extracted {len(translations)} phrase translations from text-first format")
                    return translations
                except (json.JSONDecodeError, TypeError) as e:
                    self.logger.warning(f"Could not parse PHRASE_TRANSLATIONS JSON: {e}")
        
        # Try to parse as JSON (old combined format)
        try:
            parsed_response = json.loads(raw_content)
            if 'phrase_translations' in parsed_response:
                translations = parsed_response['phrase_translations']
                self.logger.info(f"Extracted {len(translations)} phrase translations from JSON format")
                return translations
        except (json.JSONDecodeError, TypeError) as e:
            self.logger.debug(f"Could not parse combined response as JSON for translations: {e}")
        
        # No translations available in this response format
        return []
    
    def _analyze_replacements(self, original: str, enforced: str, english_terms: List[str], 
                            day: int, context: str) -> List[Dict[str, Any]]:
        """Analyze what replacements were made for logging and debugging."""
        violations = []
        
        # Simple analysis - compare original vs enforced for each English term
        for english in english_terms:
            original_count = original.lower().count(english.lower())
            enforced_count = enforced.lower().count(english.lower())
            
            if original_count > enforced_count:
                replaced_count = original_count - enforced_count
                violations.append({
                    'english': english,
                    'filipino': 'llm_determined',  # LLM chose the replacement
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
    
    def _save_original_backup(self, content: str, day: int, context: str):
        """Save original content before SRS enforcement is applied."""
        try:
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
                self.logger.info(f"Original content saved to: {backup_path}")
            else:
                self.logger.debug(f"Original backup already exists: {backup_path}")
                
        except Exception as e:
            self.logger.warning(f"Could not save original backup: {e}")


def create_llm_enforcer(llm: MockLLM, srs_db: SRSDatabase) -> SRSLLMEnforcer:
    """Factory function to create SRS LLM enforcer with enhanced database support."""
    try:
        enhanced_db = EnhancedSRSDatabase()
        return SRSLLMEnforcer(llm, srs_db, enhanced_db)
    except Exception as e:
        # Fallback to basic enforcer if enhanced database fails
        logging.warning(f"Enhanced database initialization failed, using basic enforcer: {e}")
        return SRSLLMEnforcer(llm, srs_db)