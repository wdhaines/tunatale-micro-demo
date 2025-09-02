"""
SRS Debug Analysis System for TunaTale

Analyzes vocabulary recognition states from story files and SRS database data.
Provides comprehensive debugging capabilities for the Spaced Repetition System.
"""

from srs_database import SRSDatabase
from pathlib import Path
import re
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from validation_schema import (
    VALIDATION_SCHEMA, 
    validate_schema, 
    normalize_validation_data,
    clean_voice_artifacts
)


class RecognitionState(Enum):
    """Vocabulary recognition states in TunaTale SRS system."""
    UNKNOWN = "unknown"                    # Not in SRS at all
    DORMANT = "dormant"                   # Not seen in 7+ days  
    UNSTABLE = "unstable"                 # stability < 1.0
    NATURALLY_ACQUIRING = "naturally_acquiring"  # Learning through exposure
    EXPLICITLY_LEARNED = "explicitly_learned"   # Targeted learning pattern
    HIGH_STABILITY = "high_stability"     # stability > 3.0 and review_count > 5


@dataclass
class VocabularyAnalysis:
    """Analysis result for a single vocabulary item."""
    word: str
    recognition_state: RecognitionState
    srs_data: Optional[Dict[str, Any]]
    context_appearances: List[str]
    learning_pattern: Optional[str]


class SRSDebugAnalyzer:
    """Analyzes vocabulary recognition states from story files and SRS data."""
    
    def __init__(self, db_path: str = "instance/data/srs/tunatale_srs.db"):
        """Initialize analyzer with SRS database connection."""
        self.db_path = db_path
        self.db = SRSDatabase(db_path) if Path(db_path).exists() else None
    
    def analyze_day_vocabulary(self, day: int) -> Dict[str, Any]:
        """
        Analyze vocabulary recognition states for a specific day.
        
        Args:
            day: Day number to analyze
            
        Returns:
            Comprehensive vocabulary analysis report
        """
        # Load story file for the day
        story_content, story_filename = self._load_story_file(day)
        if not story_content:
            return {"error": f"No story file found for day {day}"}
        
        # Extract Tagalog vocabulary
        vocabulary = self._extract_tagalog_vocabulary(story_content)
        
        # Analyze each word
        analyses = []
        for word in vocabulary:
            analysis = self._analyze_word(word, day)
            analyses.append(analysis)
        
        # Generate summary statistics
        state_counts = self._calculate_state_distribution(analyses)
        
        return {
            "day": day,
            "story_file": story_filename,
            "total_vocabulary": len(vocabulary),
            "vocabulary_analyses": [self._serialize_analysis(a) for a in analyses],
            "recognition_state_distribution": state_counts,
            "srs_effectiveness_metrics": self._calculate_effectiveness_metrics(analyses),
            "generated_at": self._get_current_timestamp()
        }
    
    def _load_story_file(self, day: int) -> tuple[Optional[str], Optional[str]]:
        """Load story content for the specified day."""
        story_dir = Path("instance/data/stories")
        
        if not story_dir.exists():
            return None, None
        
        # Look for story files matching day pattern
        patterns = [
            f"story_day{day}_*.txt",
            f"*day{day}*.txt", 
            f"*day_{day}_*.txt"
        ]
        
        for pattern in patterns:
            matches = list(story_dir.glob(pattern))
            if matches:
                # Use first match (could be refined with strategy preference)
                story_file = matches[0]
                with open(story_file, 'r', encoding='utf-8') as f:
                    return f.read(), story_file.name
        
        return None, None
    
    def _extract_tagalog_vocabulary(self, story_content: str) -> List[str]:
        """Extract all unique Tagalog words from TAGALOG-FEMALE/MALE speaker lines."""
        # Pattern to match Tagalog speaker lines
        tagalog_pattern = r'\[TAGALOG-(?:FEMALE|MALE)-\d+\]:\s*([^\n\[]+)'
        matches = re.findall(tagalog_pattern, story_content)
        
        # Extract individual words, filtering out common artifacts
        vocabulary = set()
        for phrase in matches:
            # Clean and split phrase
            clean_phrase = re.sub(r'[^\w\s]', ' ', phrase.strip().lower())
            words = clean_phrase.split()
            
            # Filter out breakdown artifacts and very short words
            for word in words:
                if len(word) >= 2 and not word.isdigit() and self._is_valid_tagalog_word(word):
                    vocabulary.add(word)
        
        return sorted(list(vocabulary))
    
    def _is_valid_tagalog_word(self, word: str) -> bool:
        """Check if word appears to be valid Tagalog vocabulary (not breakdown artifact)."""
        # Filter out single syllables that are likely breakdown artifacts
        if len(word) <= 2 and word in ['po', 'ba', 'sa', 'ng', 'na', 'ka', 'ma', 'ta', 'la', 'no', 'yo', 'ko', 'to']:
            return True  # These are valid Tagalog particles
        
        # Filter out pure syllable fragments
        if len(word) <= 2 and word in ['te', 'le', 'ro', 'mo', 'so', 'do', 're', 'mi', 'fa']:
            return False  # Likely syllable fragments
        
        return True
    
    def _analyze_word(self, word: str, current_day: int) -> VocabularyAnalysis:
        """Analyze recognition state for a single word."""
        # Get SRS data for this word
        srs_data = self._get_srs_data(word)
        
        # Determine recognition state
        state = self._categorize_word(word, srs_data, current_day)
        
        # Analyze learning pattern if available
        learning_pattern = self._analyze_learning_pattern(srs_data) if srs_data else None
        
        return VocabularyAnalysis(
            word=word,
            recognition_state=state,
            srs_data=srs_data,
            context_appearances=[],  # Could be enhanced to track contexts
            learning_pattern=learning_pattern
        )
    
    def _get_srs_data(self, word: str) -> Optional[Dict[str, Any]]:
        """Get SRS data for a word from the database."""
        if not self.db:
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                cursor = conn.cursor()
                
                # Query for the word
                cursor.execute("""
                    SELECT text, first_seen_day, last_seen_day, appearances, 
                           review_count, next_review_day, stability
                    FROM collocations 
                    WHERE text = ? COLLATE NOCASE
                """, (word,))
                
                row = cursor.fetchone()
                if row:
                    # Parse appearances JSON
                    appearances = json.loads(row['appearances']) if row['appearances'] else []
                    
                    return {
                        'text': row['text'],
                        'first_seen_day': row['first_seen_day'],
                        'last_seen_day': row['last_seen_day'],
                        'appearances': appearances,
                        'review_count': row['review_count'],
                        'next_review_day': row['next_review_day'],
                        'stability': row['stability']
                    }
        except (sqlite3.Error, json.JSONDecodeError) as e:
            print(f"Warning: Error querying SRS data for '{word}': {e}")
        
        return None
    
    def _categorize_word(self, word: str, srs_data: Optional[Dict], current_day: int) -> RecognitionState:
        """
        Categorize word into recognition states based on SRS data.
        
        Recognition state logic:
        - high_stability: stability > 3.0 AND review_count > 5 (enforced)
        - unstable: stability < 1.0
        - dormant: not seen in 7+ days (current_day - last_seen_day > 7)
        - unknown: not in SRS at all
        - explicitly_learned/naturally_acquiring: based on learning patterns
        """
        if not srs_data:
            return RecognitionState.UNKNOWN
        
        stability = srs_data.get('stability', 1.0)
        review_count = srs_data.get('review_count', 0)
        last_seen_day = srs_data.get('last_seen_day', current_day)
        
        # Check high stability first (enforced state)
        if stability > 3.0 and review_count > 5:
            return RecognitionState.HIGH_STABILITY
        
        # Check dormant (not seen recently)
        if current_day - last_seen_day > 7:
            return RecognitionState.DORMANT
        
        # Check unstable
        if stability < 1.0:
            return RecognitionState.UNSTABLE
        
        # Distinguish explicit vs natural learning
        if review_count > 2:
            return RecognitionState.EXPLICITLY_LEARNED
        else:
            return RecognitionState.NATURALLY_ACQUIRING
    
    def _analyze_learning_pattern(self, srs_data: Dict[str, Any]) -> Optional[str]:
        """Analyze the learning pattern for a word based on SRS history."""
        if not srs_data:
            return None
        
        appearances = srs_data.get('appearances', [])
        review_count = srs_data.get('review_count', 0)
        stability = srs_data.get('stability', 1.0)
        
        # Determine learning pattern based on data
        if len(appearances) > 5 and review_count < 3:
            return "exposure_based"  # Seen frequently but not reviewed much
        elif review_count > len(appearances):
            return "review_intensive"  # More reviews than appearances
        elif stability > 2.0 and review_count > 3:
            return "well_consolidated"
        elif stability < 1.5 and review_count > 2:
            return "struggling"  # High reviews but low stability
        else:
            return "developing"
    
    def _calculate_state_distribution(self, analyses: List[VocabularyAnalysis]) -> Dict[str, int]:
        """Calculate the distribution of recognition states."""
        distribution = {state.value: 0 for state in RecognitionState}
        
        for analysis in analyses:
            distribution[analysis.recognition_state.value] += 1
        
        return distribution
    
    def _calculate_effectiveness_metrics(self, analyses: List[VocabularyAnalysis]) -> Dict[str, Any]:
        """Calculate SRS effectiveness metrics."""
        total_words = len(analyses)
        if total_words == 0:
            return {}
        
        # Count words by state
        state_counts = self._calculate_state_distribution(analyses)
        
        # Calculate metrics
        srs_coverage = (total_words - state_counts['unknown']) / total_words * 100
        stability_ratio = (state_counts['high_stability'] + state_counts['explicitly_learned']) / total_words * 100
        learning_progress = (state_counts['naturally_acquiring'] + state_counts['explicitly_learned']) / total_words * 100
        
        # Count words needing attention
        needs_attention = state_counts['unstable'] + state_counts['dormant']
        
        return {
            "srs_coverage_percentage": round(srs_coverage, 1),
            "stability_ratio_percentage": round(stability_ratio, 1),
            "learning_progress_percentage": round(learning_progress, 1),
            "words_needing_attention": needs_attention,
            "high_stability_words": state_counts['high_stability'],
            "unknown_words": state_counts['unknown']
        }
    
    def _serialize_analysis(self, analysis: VocabularyAnalysis) -> Dict[str, Any]:
        """Serialize VocabularyAnalysis to JSON-compatible dict."""
        return {
            "word": analysis.word,
            "recognition_state": analysis.recognition_state.value,
            "srs_data": analysis.srs_data,
            "learning_pattern": analysis.learning_pattern
        }
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()
    
    def validate_against_expected(
        self, 
        day: int, 
        validation_file: str,
        error_tolerance: str = "medium"
    ) -> Dict[str, Any]:
        """
        Validate vocabulary analysis against expected states from validation file.
        
        Args:
            day: Day number to analyze
            validation_file: Path to validation JSON file
            error_tolerance: "strict", "medium", or "permissive"
            
        Returns:
            Validation results with error reporting
        """
        # Get actual analysis
        actual_analysis = self.analyze_day_vocabulary(day)
        if 'error' in actual_analysis:
            return {"error": f"Failed to analyze day {day}: {actual_analysis['error']}"}
        
        # Load and parse validation data
        try:
            validation_data = self._load_validation_data(validation_file, error_tolerance)
        except Exception as e:
            return {"error": f"Failed to load validation file: {e}"}
        
        # Perform validation comparison
        validation_results = self._compare_against_expected(
            actual_analysis, validation_data, error_tolerance
        )
        
        return validation_results
    
    def _load_validation_data(self, validation_file: str, error_tolerance: str) -> Dict[str, Any]:
        """Load and normalize validation data from file."""
        with open(validation_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # Validate schema
        warnings = validate_schema(raw_data)
        if error_tolerance == "strict" and warnings:
            raise ValueError(f"Schema validation failed: {warnings}")
        
        # Normalize data to handle inconsistencies
        normalized_data = normalize_validation_data(raw_data)
        
        return {
            "data": normalized_data,
            "warnings": warnings,
            "error_tolerance": error_tolerance
        }
    
    def _compare_against_expected(
        self, 
        actual_analysis: Dict[str, Any], 
        validation_data: Dict[str, Any],
        error_tolerance: str
    ) -> Dict[str, Any]:
        """Compare actual analysis against expected validation data."""
        expected = validation_data["data"]
        warnings = validation_data["warnings"]
        
        # Extract expected vocabulary states
        expected_states = self._extract_expected_states(expected)
        
        # Extract actual vocabulary states  
        actual_states = self._extract_actual_states(actual_analysis)
        
        # Perform comparison
        comparison_results = self._perform_state_comparison(expected_states, actual_states)
        
        # Calculate metrics
        metrics = self._calculate_validation_metrics(comparison_results, expected_states, actual_states)
        
        return {
            "validation_summary": metrics,
            "detailed_results": comparison_results,
            "data_quality_report": {
                "parsing_warnings": warnings,
                "error_tolerance": error_tolerance,
                "validation_confidence": self._calculate_confidence(warnings, error_tolerance)
            },
            "actual_analysis": actual_analysis,
            "expected_data": expected_states
        }
    
    def _extract_expected_states(self, validation_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract expected word->state mappings from validation data."""
        expected_states = {}
        
        # Handle both simple and comprehensive validation formats
        if "expected_states" in validation_data:
            # Simple format: {"expected_states": {"category": ["word1", "word2"]}}
            for category, words in validation_data["expected_states"].items():
                state = self._category_to_recognition_state(category)
                if isinstance(words, list):
                    for word in words:
                        word_clean = clean_voice_artifacts(str(word)).lower().strip()
                        if word_clean:  # Only add non-empty words
                            expected_states[word_clean] = state.value
                        
        elif "vocabulary_recognition_states" in validation_data:
            # Comprehensive format: {"vocabulary_recognition_states": {...}}
            states_data = validation_data["vocabulary_recognition_states"]
            for category, items in states_data.items():
                state = self._category_to_recognition_state(category)
                
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            # Extract word from dict format
                            word = self._extract_word_from_item(item)
                        else:
                            # Direct string format
                            word = str(item)
                        
                        if word:
                            word_clean = clean_voice_artifacts(word).lower().strip()
                            if word_clean:  # Only add non-empty words
                                expected_states[word_clean] = state.value
        
        return expected_states
    
    def _extract_actual_states(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        """Extract actual word->state mappings from analysis results."""
        actual_states = {}
        
        for vocab_item in analysis.get("vocabulary_analyses", []):
            word = vocab_item["word"].lower()
            state = vocab_item["recognition_state"]
            actual_states[word] = state
            
        return actual_states
    
    def _extract_word_from_item(self, item: Dict[str, Any]) -> Optional[str]:
        """Extract word/phrase from validation item using field aliases."""
        for primary_field in ["word", "phrase"]:
            if primary_field in item:
                return item[primary_field]
        
        # Try aliases
        for alias in VALIDATION_SCHEMA.field_aliases.get("word", []):
            if alias in item:
                return item[alias]
                
        return None
    
    def _category_to_recognition_state(self, category: str) -> RecognitionState:
        """Map validation categories to recognition states."""
        category_lower = category.lower().replace(" ", "_")
        
        mappings = {
            "unknown_vocabulary_gaps": RecognitionState.UNKNOWN,
            "high_priority_collocation_gaps": RecognitionState.UNKNOWN,
            "context_dependent_complexity": RecognitionState.UNSTABLE,  # Needs context work
            "dormant_but_recoverable": RecognitionState.DORMANT,
            "natural_acquisition_successes": RecognitionState.NATURALLY_ACQUIRING,
            "explicit_teaching_validation": RecognitionState.EXPLICITLY_LEARNED
        }
        
        # Try direct mapping first
        if category_lower in mappings:
            return mappings[category_lower]
            
        # Try fuzzy matching
        for pattern, state in mappings.items():
            # Check if key words from the pattern appear in category
            pattern_words = pattern.split('_')
            category_words = category_lower.split('_')
            if any(word in category_words for word in pattern_words):
                return state
        
        # Default fallback
        return RecognitionState.UNKNOWN
    
    def _perform_state_comparison(
        self, 
        expected_states: Dict[str, str], 
        actual_states: Dict[str, str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Perform detailed comparison between expected and actual states."""
        matches = []
        mismatches = []
        missing_from_actual = []
        unexpected_in_actual = []
        
        # Check each expected word
        for word, expected_state in expected_states.items():
            if word in actual_states:
                actual_state = actual_states[word]
                if expected_state == actual_state:
                    matches.append({
                        "word": word,
                        "expected": expected_state,
                        "actual": actual_state
                    })
                else:
                    mismatches.append({
                        "word": word,
                        "expected": expected_state,
                        "actual": actual_state
                    })
            else:
                missing_from_actual.append({
                    "word": word,
                    "expected": expected_state
                })
        
        # Check for unexpected words in actual
        for word, actual_state in actual_states.items():
            if word not in expected_states:
                unexpected_in_actual.append({
                    "word": word,
                    "actual": actual_state
                })
        
        return {
            "matches": matches,
            "mismatches": mismatches,
            "missing_from_actual": missing_from_actual,
            "unexpected_in_actual": unexpected_in_actual
        }
    
    def _calculate_validation_metrics(
        self, 
        comparison: Dict[str, List[Dict]], 
        expected_states: Dict[str, str],
        actual_states: Dict[str, str]
    ) -> Dict[str, Any]:
        """Calculate validation summary metrics."""
        total_expected = len(expected_states)
        total_actual = len(actual_states)
        matches = len(comparison["matches"])
        mismatches = len(comparison["mismatches"])
        missing = len(comparison["missing_from_actual"])
        
        match_percentage = (matches / total_expected * 100) if total_expected > 0 else 0
        
        return {
            "total_expected": total_expected,
            "total_actual": total_actual,
            "matches": matches,
            "mismatches": mismatches,
            "missing_from_actual": missing,
            "unexpected_in_actual": len(comparison["unexpected_in_actual"]),
            "match_percentage": round(match_percentage, 1),
            "coverage_percentage": round(((total_expected - missing) / total_expected * 100) if total_expected > 0 else 0, 1)
        }
    
    def _calculate_confidence(self, warnings: List[str], error_tolerance: str) -> float:
        """Calculate validation confidence score based on data quality."""
        base_confidence = 100.0
        
        # Reduce confidence based on warnings
        for warning in warnings:
            if "missing required section" in warning.lower():
                base_confidence -= 20.0
            elif "invalid priority" in warning.lower():
                base_confidence -= 5.0
            elif "voice artifact" in warning.lower():
                base_confidence -= 2.0
            else:
                base_confidence -= 1.0
        
        # Adjust for error tolerance
        if error_tolerance == "strict":
            base_confidence *= 1.0  # No adjustment
        elif error_tolerance == "medium":
            base_confidence = min(base_confidence + 10.0, 100.0)  # Slight boost
        elif error_tolerance == "permissive":
            base_confidence = min(base_confidence + 20.0, 100.0)  # Larger boost
        
        return max(0.0, min(100.0, base_confidence))


def main():
    """Test the analyzer with a sample day."""
    analyzer = SRSDebugAnalyzer()
    
    # Test with day 16
    report = analyzer.analyze_day_vocabulary(16)
    
    if 'error' in report:
        print(f"Error: {report['error']}")
        return
    
    print(f"=== SRS Debug Analysis: Day {report['day']} ===")
    print(f"Story file: {report['story_file']}")
    print(f"Total vocabulary: {report['total_vocabulary']} words")
    
    # Show recognition state distribution
    distribution = report['recognition_state_distribution']
    print(f"\n📊 Recognition State Distribution:")
    for state, count in distribution.items():
        if count > 0:
            percentage = (count / report['total_vocabulary']) * 100
            print(f"  {state}: {count} ({percentage:.1f}%)")
    
    # Show effectiveness metrics
    metrics = report['srs_effectiveness_metrics']
    print(f"\n⚡ SRS Effectiveness Metrics:")
    for metric, value in metrics.items():
        print(f"  {metric}: {value}")
    
    # Show sample vocabulary
    print(f"\n📝 Sample Vocabulary:")
    for analysis in report['vocabulary_analyses'][:10]:
        print(f"  {analysis['word']} -> {analysis['recognition_state']}")


if __name__ == "__main__":
    main()