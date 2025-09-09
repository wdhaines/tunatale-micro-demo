"""
LLM-Based Extraction Processor for TunaTale SRS System.

Clean implementation that extracts translation pairs from LLM-generated content
without spaCy dependencies. Uses the enhanced story generation prompt that includes
translation pair extraction in the SRS Enforcement Analysis section.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

from enhanced_srs_database import EnhancedSRSDatabase, TranslationPair


@dataclass
class LLMExtractionReport:
    """Report of LLM-based extraction results from a story."""
    day: int
    story_file: str
    processing_date: str
    
    # Extraction results
    translation_pairs_found: int
    english_terms_found: int
    key_phrases_found: int
    
    # Quality metrics  
    high_confidence_pairs: int  # confidence > 0.95
    medium_confidence_pairs: int  # 0.8 <= confidence <= 0.95
    
    # Processing status
    srs_analysis_found: bool
    json_parse_success: bool


class LLMBasedExtractionProcessor:
    """Processes LLM-generated story files to extract translation pairs and store in SQLite."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the LLM-based extraction processor.
        
        Args:
            db_path: Path to enhanced database (creates new if None)
        """
        self.db = EnhancedSRSDatabase(db_path) if db_path else EnhancedSRSDatabase()
    
    def extract_srs_analysis(self, story_content: str) -> Optional[Dict]:
        """Extract SRS Enforcement Analysis JSON from story content.
        
        Args:
            story_content: Full story content with SRS analysis section
            
        Returns:
            Parsed SRS analysis dictionary or None if not found/invalid
        """
        # Look for the SRS analysis section
        analysis_match = re.search(
            r'\[NARRATOR\]:\s*SRS Enforcement Analysis\s*\n(.*?)(?=\n\[|$)',
            story_content, 
            re.DOTALL | re.MULTILINE
        )
        
        if not analysis_match:
            return None
        
        analysis_content = analysis_match.group(1).strip()
        
        # Extract JSON from the analysis content
        # Look for JSON blocks (content between { and })
        json_matches = re.findall(r'\{.*?\}', analysis_content, re.DOTALL)
        
        if not json_matches:
            return None
        
        # Try to parse the largest JSON block (usually the complete analysis)
        largest_json = max(json_matches, key=len)
        
        try:
            # Clean up common formatting issues
            cleaned_json = largest_json.replace('\\n', '\\n').replace('\\"', '"')
            # Handle nested braces correctly
            analysis_data = json.loads(cleaned_json)
            return analysis_data
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse SRS analysis JSON: {e}")
            print(f"JSON content: {cleaned_json[:200]}...")
            return None
    
    def process_translation_pairs(self, analysis_data: Dict, day: int) -> List[TranslationPair]:
        """Process translation pairs from SRS analysis data.
        
        Args:
            analysis_data: Parsed SRS analysis dictionary
            day: Day number for source tracking
            
        Returns:
            List of processed TranslationPair objects
        """
        translation_pairs = []
        
        # Extract translation pairs from analysis
        if 'translation_pairs' in analysis_data:
            for pair_data in analysis_data['translation_pairs']:
                if all(key in pair_data for key in ['english', 'filipino', 'confidence']):
                    # Create TranslationPair object
                    pair = TranslationPair(
                        english=pair_data['english'].strip(),
                        filipino=pair_data['filipino'].strip(),
                        confidence=float(pair_data['confidence'])
                    )
                    translation_pairs.append(pair)
                    
                    # Store in database
                    self.db.add_translation_pair(
                        pair.english, 
                        pair.filipino, 
                        pair.confidence, 
                        day, 
                        'llm_analysis'
                    )
        
        return translation_pairs
    
    def process_english_terms(self, analysis_data: Dict, day: int) -> int:
        """Process English terms from SRS analysis data.
        
        Args:
            analysis_data: Parsed SRS analysis dictionary
            day: Day number for source tracking
            
        Returns:
            Number of English terms processed
        """
        english_terms_count = 0
        
        # Extract English terms that need replacement
        if 'english_terms' in analysis_data:
            for term_data in analysis_data['english_terms']:
                if 'english' in term_data and 'srs_queries' in term_data:
                    english_text = term_data['english'].strip()
                    srs_queries = term_data['srs_queries']
                    
                    # For each SRS query, try to create translation pairs
                    for query in srs_queries:
                        if query.strip() != english_text:  # Avoid self-references
                            # Create medium-confidence translation pair
                            self.db.add_translation_pair(
                                english_text,
                                query.strip(),
                                0.85,  # Medium confidence for inferred pairs
                                day,
                                'llm_english_terms'
                            )
                            english_terms_count += 1
        
        return english_terms_count
    
    def process_key_phrases(self, analysis_data: Dict) -> int:
        """Process key phrases from SRS analysis data.
        
        Args:
            analysis_data: Parsed SRS analysis dictionary
            
        Returns:
            Number of key phrases processed
        """
        key_phrases_count = 0
        
        # Extract key phrases analysis
        if 'key_phrases_analysis' in analysis_data:
            phrases_analysis = analysis_data['key_phrases_analysis']
            
            if 'phrases' in phrases_analysis:
                phrases = phrases_analysis['phrases']
                key_phrases_count = len(phrases)
                
                # Store key phrases as Filipino collocations in database
                for phrase in phrases:
                    self.db.add_enhanced_collocation(
                        text=phrase.strip(),
                        language='filipino',
                        first_seen_day=0,  # Key phrases are always available
                        last_seen_day=0,
                        appearances=[0],
                        stability=1.0  # Default stability for key phrases
                    )
        
        return key_phrases_count
    
    def process_story_file(self, story_path: Path, day: Optional[int] = None) -> LLMExtractionReport:
        """Process a single LLM-generated story file.
        
        Args:
            story_path: Path to the story file
            day: Day number (extracted from filename if None)
            
        Returns:
            LLMExtractionReport with processing results
        """
        if not story_path.exists():
            raise FileNotFoundError(f"Story file not found: {story_path}")
        
        # Extract day number if not provided
        if day is None:
            day = self._extract_day_from_filename(story_path)
        
        story_content = story_path.read_text(encoding='utf-8')
        
        # Extract SRS analysis from LLM-generated content
        analysis_data = self.extract_srs_analysis(story_content)
        
        # Initialize report
        report = LLMExtractionReport(
            day=day,
            story_file=str(story_path),
            processing_date=datetime.now().isoformat(),
            translation_pairs_found=0,
            english_terms_found=0,
            key_phrases_found=0,
            high_confidence_pairs=0,
            medium_confidence_pairs=0,
            srs_analysis_found=analysis_data is not None,
            json_parse_success=analysis_data is not None
        )
        
        if not analysis_data:
            print(f"Warning: No valid SRS analysis found in {story_path.name} - using fallback pattern extraction")
            # Fallback: extract basic translation pairs from story structure
            fallback_pairs = self._extract_fallback_translation_pairs(story_content, day)
            report.translation_pairs_found = len(fallback_pairs)
            
            # Count confidence levels for fallback pairs
            for pair in fallback_pairs:
                if pair.confidence > 0.95:
                    report.high_confidence_pairs += 1
                elif pair.confidence >= 0.8:
                    report.medium_confidence_pairs += 1
            
            return report
        
        # Process translation pairs
        translation_pairs = self.process_translation_pairs(analysis_data, day)
        report.translation_pairs_found = len(translation_pairs)
        
        # Count confidence levels
        for pair in translation_pairs:
            if pair.confidence > 0.95:
                report.high_confidence_pairs += 1
            elif pair.confidence >= 0.8:
                report.medium_confidence_pairs += 1
        
        # Process English terms
        report.english_terms_found = self.process_english_terms(analysis_data, day)
        
        # Process key phrases
        report.key_phrases_found = self.process_key_phrases(analysis_data)
        
        return report
    
    def process_all_stories(self, stories_dir: Optional[Path] = None) -> List[LLMExtractionReport]:
        """Process all LLM-generated story files in a directory.
        
        Args:
            stories_dir: Directory containing story files (defaults to instance/data/stories)
            
        Returns:
            List of LLMExtractionReport objects
        """
        if stories_dir is None:
            stories_dir = Path("instance/data/stories")
        
        if not stories_dir.exists():
            raise FileNotFoundError(f"Stories directory not found: {stories_dir}")
        
        # Find all story files
        story_files = list(stories_dir.glob("*.txt"))
        
        if not story_files:
            raise FileNotFoundError(f"No story files found in {stories_dir}")
        
        reports = []
        
        for story_file in sorted(story_files):
            try:
                report = self.process_story_file(story_file)
                reports.append(report)
                
                status = "✓" if report.srs_analysis_found else "⚠"
                print(f"{status} Processed {story_file.name}: "
                      f"{report.translation_pairs_found} translation pairs, "
                      f"{report.english_terms_found} English terms, "
                      f"{report.key_phrases_found} key phrases")
            except Exception as e:
                print(f"✗ Error processing {story_file.name}: {e}")
        
        return reports
    
    def _extract_fallback_translation_pairs(self, story_content: str, day: int) -> List[TranslationPair]:
        """Extract translation pairs from story structure without LLM analysis (fallback).
        
        Args:
            story_content: Full story content
            day: Day number for source tracking
            
        Returns:
            List of basic TranslationPair objects from pattern matching
        """
        pairs = []
        
        # Look for Translated section with [TAGALOG-*] → [NARRATOR] pairs
        translated_section_match = re.search(
            r'\[NARRATOR\]:\s*Translated\s*\n(.*)', 
            story_content, 
            re.DOTALL | re.MULTILINE
        )
        
        if not translated_section_match:
            return pairs
        
        translated_content = translated_section_match.group(1)
        lines = translated_content.split('\n')
        
        # Simple known word mappings for fallback
        known_mappings = {
            'water': 'tubig',
            'delicious': 'masarap', 
            'thank you': 'salamat po',
            'good morning': 'magandang umaga',
            'excuse me': 'paumanhin po',
            'perfect': 'perpekto',
            'beautiful': 'maganda',
            'fresh': 'sariwa'
        }
        
        # Extract pairs from consecutive [TAGALOG-*] → [NARRATOR] lines
        i = 0
        while i < len(lines) - 1:
            current_line = lines[i].strip()
            next_line = lines[i + 1].strip()
            
            if (current_line.startswith('[TAGALOG-') and 
                next_line.startswith('[NARRATOR]:')):
                
                # Extract text content
                tagalog_text = re.sub(r'\[TAGALOG-[^\]]+\]:\s*', '', current_line)
                english_text = re.sub(r'\[NARRATOR\]:\s*', '', next_line)
                
                # Look for known mappings in the text pair
                for english_term, filipino_term in known_mappings.items():
                    if (english_term.lower() in english_text.lower() and 
                        filipino_term.lower() in tagalog_text.lower()):
                        
                        pair = TranslationPair(english_term, filipino_term, 0.9)
                        pairs.append(pair)
                        
                        # Store in database
                        self.db.add_translation_pair(
                            pair.english, 
                            pair.filipino, 
                            pair.confidence, 
                            day, 
                            'fallback_pattern'
                        )
            
            i += 1
        
        return pairs
    
    def _extract_day_from_filename(self, story_path: Path) -> int:
        """Extract day number from story filename."""
        filename = story_path.name
        
        # Try different patterns
        patterns = [
            r'day[-_]?(\d+)',
            r'story[-_]?day(\d+)',
            r'demo-[\d.]+-day-(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        # Fallback: extract any number
        match = re.search(r'(\d+)', filename)
        if match:
            return int(match.group(1))
        
        return 0  # Default day
    
    def generate_summary_report(self, reports: List[LLMExtractionReport]) -> Dict:
        """Generate a summary report from multiple extraction reports.
        
        Args:
            reports: List of extraction reports
            
        Returns:
            Summary statistics dictionary
        """
        if not reports:
            return {"error": "No reports to summarize"}
        
        total_translation_pairs = sum(r.translation_pairs_found for r in reports)
        total_english_terms = sum(r.english_terms_found for r in reports)
        total_key_phrases = sum(r.key_phrases_found for r in reports)
        total_high_confidence = sum(r.high_confidence_pairs for r in reports)
        total_medium_confidence = sum(r.medium_confidence_pairs for r in reports)
        
        successful_analyses = sum(1 for r in reports if r.srs_analysis_found)
        
        # Database statistics
        db_stats = self.db.get_stats()
        
        summary = {
            "extraction_summary": {
                "total_stories_processed": len(reports),
                "successful_srs_analyses": successful_analyses,
                "analysis_success_rate": round(successful_analyses / len(reports), 3),
                "total_translation_pairs": total_translation_pairs,
                "total_english_terms": total_english_terms,
                "total_key_phrases": total_key_phrases,
                "high_confidence_pairs": total_high_confidence,
                "medium_confidence_pairs": total_medium_confidence,
            },
            "database_statistics": db_stats,
            "quality_metrics": {
                "high_confidence_ratio": round(total_high_confidence / total_translation_pairs, 3) if total_translation_pairs > 0 else 0,
                "avg_pairs_per_story": round(total_translation_pairs / len(reports), 1),
                "avg_terms_per_story": round(total_english_terms / len(reports), 1)
            }
        }
        
        return summary
    
    def save_reports(self, reports: List[LLMExtractionReport], output_dir: Optional[Path] = None) -> Path:
        """Save extraction reports to JSON file.
        
        Args:
            reports: List of extraction reports
            output_dir: Directory to save to (defaults to instance/data/analysis)
            
        Returns:
            Path to saved file
        """
        if output_dir is None:
            output_dir = Path("instance/data/analysis")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert reports to dictionaries
        reports_data = []
        for report in reports:
            report_dict = {
                "day": report.day,
                "story_file": report.story_file,
                "processing_date": report.processing_date,
                "translation_pairs_found": report.translation_pairs_found,
                "english_terms_found": report.english_terms_found,
                "key_phrases_found": report.key_phrases_found,
                "high_confidence_pairs": report.high_confidence_pairs,
                "medium_confidence_pairs": report.medium_confidence_pairs,
                "srs_analysis_found": report.srs_analysis_found,
                "json_parse_success": report.json_parse_success
            }
            reports_data.append(report_dict)
        
        # Generate summary
        summary = self.generate_summary_report(reports)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"llm_extraction_report_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "reports": reports_data,
                "summary": summary
            }, f, indent=2, ensure_ascii=False)
        
        return output_file


def main():
    """Command-line interface for LLM-based extraction."""
    import sys
    
    processor = LLMBasedExtractionProcessor()
    
    if len(sys.argv) > 1:
        # Process specific story file
        story_file = Path(sys.argv[1])
        report = processor.process_story_file(story_file)
        
        status = "✓" if report.srs_analysis_found else "⚠"
        print(f"{status} Processed {story_file.name}:")
        print(f"  Translation pairs: {report.translation_pairs_found}")
        print(f"  English terms: {report.english_terms_found}")
        print(f"  Key phrases: {report.key_phrases_found}")
        print(f"  High confidence: {report.high_confidence_pairs}")
        print(f"  SRS analysis found: {report.srs_analysis_found}")
    else:
        # Process all stories
        print("Processing all LLM-generated story files...")
        reports = processor.process_all_stories()
        
        # Generate and save reports
        output_file = processor.save_reports(reports)
        print(f"\\nReports saved to: {output_file}")
        
        # Print summary
        summary = processor.generate_summary_report(reports)
        print(f"\\nSUMMARY:")
        print(f"  Stories processed: {summary['extraction_summary']['total_stories_processed']}")
        print(f"  Successful analyses: {summary['extraction_summary']['successful_srs_analyses']}")
        print(f"  Translation pairs: {summary['extraction_summary']['total_translation_pairs']}")
        print(f"  High confidence pairs: {summary['extraction_summary']['high_confidence_pairs']}")
        print(f"  Database: {summary['database_statistics']['total_collocations']} enhanced collocations")


if __name__ == "__main__":
    main()