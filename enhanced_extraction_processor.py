"""
Enhanced Extraction Processor for TunaTale SRS System.

Combines the enhanced collocation extractor and enhanced database to create
a complete bidirectional mapping system from story files.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

from enhanced_collocation_extractor import EnhancedCollocationExtractor, TranslationPair
from enhanced_srs_database import EnhancedSRSDatabase, BilingualCollocation
from story_collocation_extractor import StoryCollocationExtractor


@dataclass
class ExtractionReport:
    """Report of extraction results from a story."""
    day: int
    story_file: str
    processing_date: str
    
    # Extraction results
    total_collocations: int
    filipino_collocations: int
    english_collocations: int
    mixed_collocations: int
    translation_pairs: int
    
    # Quality metrics
    high_confidence_pairs: int  # confidence > 0.9
    medium_confidence_pairs: int  # 0.7 < confidence <= 0.9
    bidirectional_mappings: int  # collocations with equivalents


class EnhancedExtractionProcessor:
    """Processes story files to create enhanced bidirectional collocation databases."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the enhanced extraction processor.
        
        Args:
            db_path: Path to enhanced database (creates new if None)
        """
        self.enhanced_extractor = EnhancedCollocationExtractor()
        self.story_extractor = StoryCollocationExtractor()
        self.db = EnhancedSRSDatabase(db_path) if db_path else EnhancedSRSDatabase()
        
        # Language detection patterns
        self.english_patterns = [
            r'\b(the|and|or|but|a|an|is|are|was|were|have|has|had|will|would|should|could)\b',
            r'\b(good|great|nice|beautiful|perfect|delicious|fresh|hot|cold|spicy|sweet)\b',
            r'\b(morning|afternoon|evening|night|today|tomorrow|yesterday)\b',
            r'\b(thank\s+you|please|excuse\s+me|sorry|welcome|hello|goodbye)\b',
            r'\b(how\s+much|how\s+are\s+you|what\s+is|where\s+is|when\s+is)\b'
        ]
        
        self.filipino_indicators = [
            r'\b(po|ang|ng|sa|na|ay|ba|mga|si|ni|ka|ko|mo|to)\b',
            r'\b(opo|hindi|tama|mali|salamat|pakisuyo|paumanhin)\b',
            r'\b(maganda|masarap|mahal|mura|mainit|malamig|maanghang)\b',
            r'\b(para|kasama|namin|ninyo|kayo|kami|tayo|sila)\b'
        ]
    
    def detect_language(self, text: str) -> str:
        """Detect the primary language of a collocation.
        
        Args:
            text: Text to analyze
            
        Returns:
            'filipino', 'english', or 'mixed'
        """
        text_lower = text.lower()
        
        english_score = 0
        filipino_score = 0
        
        # Check English patterns
        for pattern in self.english_patterns:
            if re.search(pattern, text_lower):
                english_score += 1
        
        # Check Filipino patterns
        for pattern in self.filipino_indicators:
            if re.search(pattern, text_lower):
                filipino_score += 1
        
        # Simple heuristic based on character patterns
        if re.search(r'[^a-zA-Z\s\-\']', text):  # Non-English characters
            filipino_score += 1
        
        if filipino_score > english_score:
            return 'filipino'
        elif english_score > filipino_score:
            return 'english'
        else:
            return 'mixed'
    
    def process_story_file(self, story_path: Path, day: Optional[int] = None) -> ExtractionReport:
        """Process a single story file and extract enhanced collocations.
        
        Args:
            story_path: Path to the story file
            day: Day number (extracted from filename if None)
            
        Returns:
            ExtractionReport with processing results
        """
        if not story_path.exists():
            raise FileNotFoundError(f"Story file not found: {story_path}")
        
        # Extract day number if not provided
        if day is None:
            day = self._extract_day_from_filename(story_path)
        
        story_content = story_path.read_text(encoding='utf-8')
        
        # Use enhanced extractor to get collocations and translation pairs
        enhanced_result = self.enhanced_extractor.extract_with_translation_pairs(story_content)
        
        collocations = enhanced_result['collocations']
        translation_pairs = enhanced_result['translation_pairs']
        enhanced_mappings = enhanced_result['enhanced_mappings']
        
        # Process translation pairs first
        high_confidence_pairs = 0
        medium_confidence_pairs = 0
        
        for pair in translation_pairs:
            # Add to database
            self.db.add_translation_pair(
                pair.english, pair.filipino, pair.confidence, day, 'story_dialogue'
            )
            
            # Count confidence levels
            if pair.confidence > 0.9:
                high_confidence_pairs += 1
            elif pair.confidence > 0.7:
                medium_confidence_pairs += 1
        
        # Process enhanced collocations with language detection and bidirectional mapping
        filipino_count = 0
        english_count = 0
        mixed_count = 0
        bidirectional_mappings = 0
        
        for collocation_text, collocation_data in enhanced_mappings.items():
            # Detect language
            language = self.detect_language(collocation_text)
            
            # Count by language
            if language == 'filipino':
                filipino_count += 1
            elif language == 'english':
                english_count += 1
            else:
                mixed_count += 1
            
            # Extract SRS data
            count = collocation_data.get('count', 1)
            stability = collocation_data.get('stability', 1.0)
            
            # Look for bidirectional mappings
            english_equivalent = None
            filipino_equivalent = None
            translation_confidence = None
            
            if 'english_equivalent' in collocation_data and collocation_data['english_equivalent']:
                english_equivalent = collocation_data['english_equivalent']
                translation_confidence = collocation_data.get('confidence', 1.0)
                bidirectional_mappings += 1
            
            if 'filipino_equivalent' in collocation_data and collocation_data['filipino_equivalent']:
                filipino_equivalent = collocation_data['filipino_equivalent']
                translation_confidence = collocation_data.get('confidence', 1.0)
                bidirectional_mappings += 1
            
            # Add to enhanced database
            self.db.add_enhanced_collocation(
                text=collocation_text,
                language=language,
                first_seen_day=day,
                last_seen_day=day,
                appearances=[day],
                review_count=0,
                next_review_day=0,
                stability=stability,
                english_equivalent=english_equivalent,
                filipino_equivalent=filipino_equivalent,
                translation_confidence=translation_confidence
            )
        
        # Create report
        report = ExtractionReport(
            day=day,
            story_file=str(story_path),
            processing_date=datetime.now().isoformat(),
            total_collocations=len(enhanced_mappings),
            filipino_collocations=filipino_count,
            english_collocations=english_count,
            mixed_collocations=mixed_count,
            translation_pairs=len(translation_pairs),
            high_confidence_pairs=high_confidence_pairs,
            medium_confidence_pairs=medium_confidence_pairs,
            bidirectional_mappings=bidirectional_mappings
        )
        
        return report
    
    def process_all_stories(self, stories_dir: Optional[Path] = None) -> List[ExtractionReport]:
        """Process all story files in a directory.
        
        Args:
            stories_dir: Directory containing story files (defaults to instance/data/stories)
            
        Returns:
            List of ExtractionReport objects
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
                print(f"Processed {story_file.name}: {report.total_collocations} collocations, "
                      f"{report.translation_pairs} translation pairs")
            except Exception as e:
                print(f"Error processing {story_file.name}: {e}")
        
        return reports
    
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
    
    def generate_summary_report(self, reports: List[ExtractionReport]) -> Dict:
        """Generate a summary report from multiple extraction reports.
        
        Args:
            reports: List of extraction reports
            
        Returns:
            Summary statistics dictionary
        """
        if not reports:
            return {"error": "No reports to summarize"}
        
        total_collocations = sum(r.total_collocations for r in reports)
        total_filipino = sum(r.filipino_collocations for r in reports)
        total_english = sum(r.english_collocations for r in reports)
        total_mixed = sum(r.mixed_collocations for r in reports)
        total_pairs = sum(r.translation_pairs for r in reports)
        total_high_confidence = sum(r.high_confidence_pairs for r in reports)
        total_medium_confidence = sum(r.medium_confidence_pairs for r in reports)
        total_bidirectional = sum(r.bidirectional_mappings for r in reports)
        
        # Database statistics
        db_stats = self.db.get_stats()
        
        summary = {
            "extraction_summary": {
                "total_stories_processed": len(reports),
                "days_covered": [r.day for r in reports],
                "total_collocations_extracted": total_collocations,
                "filipino_collocations": total_filipino,
                "english_collocations": total_english,
                "mixed_collocations": total_mixed,
                "total_translation_pairs": total_pairs,
                "high_confidence_pairs": total_high_confidence,
                "medium_confidence_pairs": total_medium_confidence,
                "bidirectional_mappings": total_bidirectional
            },
            "database_statistics": db_stats,
            "quality_metrics": {
                "translation_pair_ratio": round(total_pairs / total_collocations, 3) if total_collocations > 0 else 0,
                "bidirectional_mapping_ratio": round(total_bidirectional / total_collocations, 3) if total_collocations > 0 else 0,
                "high_confidence_ratio": round(total_high_confidence / total_pairs, 3) if total_pairs > 0 else 0
            }
        }
        
        return summary
    
    def save_reports(self, reports: List[ExtractionReport], output_dir: Optional[Path] = None) -> Path:
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
                "total_collocations": report.total_collocations,
                "filipino_collocations": report.filipino_collocations,
                "english_collocations": report.english_collocations,
                "mixed_collocations": report.mixed_collocations,
                "translation_pairs": report.translation_pairs,
                "high_confidence_pairs": report.high_confidence_pairs,
                "medium_confidence_pairs": report.medium_confidence_pairs,
                "bidirectional_mappings": report.bidirectional_mappings
            }
            reports_data.append(report_dict)
        
        # Generate summary
        summary = self.generate_summary_report(reports)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"enhanced_extraction_report_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "reports": reports_data,
                "summary": summary
            }, f, indent=2, ensure_ascii=False)
        
        return output_file


def main():
    """Command-line interface for enhanced extraction."""
    import sys
    
    processor = EnhancedExtractionProcessor()
    
    if len(sys.argv) > 1:
        # Process specific story file
        story_file = Path(sys.argv[1])
        report = processor.process_story_file(story_file)
        print(f"Processed {story_file.name}:")
        print(f"  Total collocations: {report.total_collocations}")
        print(f"  Translation pairs: {report.translation_pairs}")
        print(f"  Bidirectional mappings: {report.bidirectional_mappings}")
    else:
        # Process all stories
        print("Processing all story files...")
        reports = processor.process_all_stories()
        
        # Generate and save reports
        output_file = processor.save_reports(reports)
        print(f"\\nReports saved to: {output_file}")
        
        # Print summary
        summary = processor.generate_summary_report(reports)
        print(f"\\nSUMMARY:")
        print(f"  Stories processed: {summary['extraction_summary']['total_stories_processed']}")
        print(f"  Total collocations: {summary['extraction_summary']['total_collocations_extracted']}")
        print(f"  Translation pairs: {summary['extraction_summary']['total_translation_pairs']}")
        print(f"  Bidirectional mappings: {summary['extraction_summary']['bidirectional_mappings']}")
        print(f"  Database: {summary['database_statistics']['total_collocations']} enhanced collocations")


if __name__ == "__main__":
    main()