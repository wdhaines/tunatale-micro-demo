#!/usr/bin/env python3
"""
SRS Usage Validator for TunaTale

Validates that collocations provided by SRS for review are actually used
in generated stories, addressing the feedback loop issue where items are
marked as "reviewed" upon generation rather than actual usage.
"""

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import logging
from datetime import datetime

from story_collocation_extractor import StoryCollocationExtractor
from srs_tracker import SRSTracker


@dataclass
class UsageAnalysis:
    """Analysis of SRS collocation usage in a generated story."""
    day: int
    story_file: str
    analysis_date: str
    
    # SRS data
    srs_provided_collocations: List[str]
    srs_total_provided: int
    
    # Story data  
    story_actual_collocations: List[str]
    story_total_found: int
    
    # Usage matching
    used_collocations: List[str]        # SRS collocations found in story
    unused_collocations: List[str]      # SRS collocations NOT found in story
    unexpected_collocations: List[str]  # Story collocations not from SRS
    
    # Statistics
    usage_rate: float                   # % of SRS collocations actually used
    match_rate: float                   # % of story collocations that came from SRS
    total_matches: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def print_summary(self) -> None:
        """Print a human-readable summary of the analysis."""
        print(f"\n=== SRS Usage Analysis for Day {self.day} ===")
        print(f"Story: {Path(self.story_file).name}")
        print(f"Analysis Date: {self.analysis_date}")
        
        print(f"\n📊 Statistics:")
        print(f"  SRS provided: {self.srs_total_provided} collocations for review")
        print(f"  Story contains: {self.story_total_found} actual collocations") 
        print(f"  Usage rate: {self.usage_rate:.1f}% (SRS collocations actually used)")
        print(f"  Match rate: {self.match_rate:.1f}% (story collocations from SRS)")
        print(f"  Total matches: {self.total_matches}")
        
        if self.used_collocations:
            print(f"\n✅ Used SRS Collocations ({len(self.used_collocations)}):")
            for colloc in self.used_collocations:
                print(f"  - {colloc}")
        
        if self.unused_collocations:
            print(f"\n❌ Unused SRS Collocations ({len(self.unused_collocations)}):")
            for colloc in self.unused_collocations:
                print(f"  - {colloc}")
                
        if self.unexpected_collocations:
            print(f"\n🆕 New Story Collocations ({len(self.unexpected_collocations)}):")
            for colloc in self.unexpected_collocations[:10]:  # Limit to first 10
                print(f"  - {colloc}")
            if len(self.unexpected_collocations) > 10:
                print(f"  ... and {len(self.unexpected_collocations) - 10} more")


class SRSUsageValidator:
    """Validates that SRS-provided collocations are actually used in stories."""
    
    def __init__(self, data_dir: str = 'data', srs_filename: str = 'srs_status.json'):
        self.logger = logging.getLogger(__name__)
        self.srs_tracker = SRSTracker(data_dir=data_dir, filename=srs_filename)
        self.story_extractor = StoryCollocationExtractor()
    
    def validate_story_usage(self, day: int, story_path: Optional[Path] = None, 
                           srs_provided: Optional[List[str]] = None) -> UsageAnalysis:
        """
        Validate collocation usage for a specific day's story.
        
        Args:
            day: Day number to validate
            story_path: Optional path to story file (auto-detected if None)
            srs_provided: Optional list of SRS collocations (retrieved if None)
            
        Returns:
            UsageAnalysis with detailed usage statistics
        """
        # Get SRS provided collocations
        if srs_provided is None:
            srs_provided = self.srs_tracker.get_due_collocations(day, min_items=0, max_items=20)
        
        # Extract actual story collocations
        if story_path is None:
            story_extraction = self.story_extractor.extract_from_day_number(day)
            if story_extraction is None:
                raise FileNotFoundError(f"No story file found for day {day}")
            story_path = Path(story_extraction.story_file)
            story_collocations = story_extraction.all_tagalog_phrases
        else:
            story_extraction = self.story_extractor.extract_from_story_file(story_path)
            story_collocations = story_extraction.all_tagalog_phrases
        
        # Analyze usage
        return self._analyze_usage(
            day=day,
            story_file=str(story_path),
            srs_provided=srs_provided,
            story_actual=story_collocations
        )
    
    def _analyze_usage(self, day: int, story_file: str, 
                      srs_provided: List[str], story_actual: List[str]) -> UsageAnalysis:
        """Analyze usage between SRS provided and story actual collocations."""
        
        # Normalize for comparison (lowercase, stripped)
        srs_normalized = {self._normalize_collocation(c): c for c in srs_provided}
        story_normalized = {self._normalize_collocation(c): c for c in story_actual}
        
        # Find matches
        used_normalized = set(srs_normalized.keys()) & set(story_normalized.keys())
        used_collocations = [srs_normalized[norm] for norm in used_normalized]
        
        unused_normalized = set(srs_normalized.keys()) - set(story_normalized.keys())
        unused_collocations = [srs_normalized[norm] for norm in unused_normalized]
        
        unexpected_normalized = set(story_normalized.keys()) - set(srs_normalized.keys())
        unexpected_collocations = [story_normalized[norm] for norm in unexpected_normalized]
        
        # Calculate statistics
        usage_rate = (len(used_collocations) / len(srs_provided)) * 100 if srs_provided else 0
        match_rate = (len(used_collocations) / len(story_actual)) * 100 if story_actual else 0
        
        return UsageAnalysis(
            day=day,
            story_file=story_file,
            analysis_date=datetime.now().isoformat(),
            
            srs_provided_collocations=srs_provided,
            srs_total_provided=len(srs_provided),
            
            story_actual_collocations=story_actual,
            story_total_found=len(story_actual),
            
            used_collocations=used_collocations,
            unused_collocations=unused_collocations,
            unexpected_collocations=unexpected_collocations,
            
            usage_rate=usage_rate,
            match_rate=match_rate,
            total_matches=len(used_collocations)
        )
    
    def _normalize_collocation(self, collocation: str) -> str:
        """Normalize collocation for comparison (lowercase, stripped, punctuation removed)."""
        normalized = collocation.lower().strip()
        # Remove common punctuation but preserve Filipino characters
        normalized = re.sub(r'[.,!?;:"()[\]{}]', '', normalized)
        # Normalize whitespace
        normalized = ' '.join(normalized.split())
        return normalized
    
    def validate_recent_days(self, days: int = 5) -> List[UsageAnalysis]:
        """
        Validate usage for the most recent N days.
        
        Args:
            days: Number of recent days to validate
            
        Returns:
            List of UsageAnalysis objects
        """
        analyses = []
        current_day = self.srs_tracker.current_day
        
        for day in range(max(1, current_day - days + 1), current_day + 1):
            try:
                analysis = self.validate_story_usage(day)
                analyses.append(analysis)
                self.logger.info(f"Validated day {day}: {analysis.usage_rate:.1f}% usage rate")
            except Exception as e:
                self.logger.warning(f"Could not validate day {day}: {e}")
        
        return analyses
    
    def save_analysis(self, analysis: UsageAnalysis, output_dir: Optional[Path] = None) -> Path:
        """
        Save analysis results to JSON file.
        
        Args:
            analysis: UsageAnalysis to save
            output_dir: Output directory (defaults to instance/data/analysis)
            
        Returns:
            Path to saved file
        """
        if output_dir is None:
            output_dir = Path("instance/data/analysis")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"day_{analysis.day}_srs_usage.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis.to_dict(), f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved SRS usage analysis to {output_file}")
        return output_file
    
    def generate_usage_report(self, analyses: List[UsageAnalysis]) -> Dict[str, float]:
        """
        Generate aggregate usage statistics from multiple analyses.
        
        Args:
            analyses: List of UsageAnalysis objects
            
        Returns:
            Dictionary with aggregate statistics
        """
        if not analyses:
            return {}
        
        total_provided = sum(a.srs_total_provided for a in analyses)
        total_used = sum(len(a.used_collocations) for a in analyses)
        total_story_phrases = sum(a.story_total_found for a in analyses)
        total_matches = sum(a.total_matches for a in analyses)
        
        avg_usage_rate = sum(a.usage_rate for a in analyses) / len(analyses)
        avg_match_rate = sum(a.match_rate for a in analyses) / len(analyses)
        
        return {
            'total_days_analyzed': len(analyses),
            'total_srs_collocations_provided': total_provided,
            'total_srs_collocations_used': total_used,
            'total_story_collocations_found': total_story_phrases,
            'total_matches': total_matches,
            'overall_usage_rate': (total_used / total_provided) * 100 if total_provided > 0 else 0,
            'overall_match_rate': (total_matches / total_story_phrases) * 100 if total_story_phrases > 0 else 0,
            'average_usage_rate_per_day': avg_usage_rate,
            'average_match_rate_per_day': avg_match_rate,
        }


def main():
    """Command-line interface for SRS usage validation."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate SRS collocation usage in stories')
    parser.add_argument('day', type=int, nargs='?', help='Day number to validate (default: validate recent days)')
    parser.add_argument('--recent', type=int, default=5, help='Number of recent days to validate (default: 5)')
    parser.add_argument('--save', action='store_true', help='Save analysis to JSON file')
    parser.add_argument('--data-dir', default='data', help='SRS data directory')
    parser.add_argument('--srs-file', default='srs_status.json', help='SRS status filename')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        validator = SRSUsageValidator(data_dir=args.data_dir, srs_filename=args.srs_file)
        
        if args.day:
            # Validate specific day
            analysis = validator.validate_story_usage(args.day)
            analysis.print_summary()
            
            if args.save:
                output_file = validator.save_analysis(analysis)
                print(f"\nAnalysis saved to: {output_file}")
        else:
            # Validate recent days
            analyses = validator.validate_recent_days(args.recent)
            
            print(f"\n=== SRS Usage Report for Last {len(analyses)} Days ===")
            
            for analysis in analyses:
                print(f"\nDay {analysis.day}: {analysis.usage_rate:.1f}% usage, {analysis.match_rate:.1f}% match")
                if analysis.usage_rate < 50:
                    print(f"  ⚠️  Low usage rate! {len(analysis.unused_collocations)} unused SRS collocations")
            
            # Generate aggregate report
            report = validator.generate_usage_report(analyses)
            print(f"\n📈 Aggregate Statistics:")
            print(f"  Overall Usage Rate: {report.get('overall_usage_rate', 0):.1f}%")
            print(f"  Overall Match Rate: {report.get('overall_match_rate', 0):.1f}%") 
            print(f"  Total SRS Collocations Provided: {report.get('total_srs_collocations_provided', 0)}")
            print(f"  Total Actually Used: {report.get('total_srs_collocations_used', 0)}")
            
            if args.save:
                for analysis in analyses:
                    validator.save_analysis(analysis)
                print(f"\nAll analyses saved to instance/data/analysis/")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()