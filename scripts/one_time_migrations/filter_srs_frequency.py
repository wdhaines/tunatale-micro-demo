#!/usr/bin/env python3
"""
Frequency-based SRS filtering script for TunaTale.

Analyzes collocation frequencies across all story content and filters the SRS database
to keep only collocations that appear frequently enough to be pedagogically valuable.
"""

import argparse
import sys
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple, Set
import json

from srs_database import SRSDatabase
from story_collocation_extractor import StoryCollocationExtractor


class SRSFrequencyFilter:
    """Filters SRS collocations based on frequency analysis of story content."""
    
    def __init__(self):
        """Initialize the frequency filter."""
        self.db = SRSDatabase()
        self.story_extractor = StoryCollocationExtractor()
        
    def analyze_collocation_frequencies(self, verbose: bool = True) -> Counter:
        """Analyze frequency of collocations across all story content.
        
        Args:
            verbose: Whether to print progress information
            
        Returns:
            Counter with collocation frequencies across all stories
        """
        if verbose:
            print("🔍 Analyzing collocation frequencies across all stories...")
        
        # Find all story files
        stories_dir = Path("instance/data/stories")
        if not stories_dir.exists():
            raise FileNotFoundError(f"Stories directory not found: {stories_dir}")
        
        story_files = list(stories_dir.glob("*.txt"))
        if not story_files:
            raise FileNotFoundError(f"No story files found in {stories_dir}")
        
        # Extract collocations from each story and count frequencies
        all_collocations = Counter()
        
        for i, story_file in enumerate(story_files, 1):
            if verbose and i % 5 == 0:
                print(f"  Processing story {i}/{len(story_files)}: {story_file.name}")
            
            try:
                with open(story_file, 'r', encoding='utf-8') as f:
                    story_content = f.read()
                
                # Extract collocations from this story
                story_collocations = self.story_extractor.extract_collocations(story_content)
                
                # Update frequency counter
                all_collocations.update(story_collocations)
                
            except Exception as e:
                if verbose:
                    print(f"  ⚠️ Error processing {story_file.name}: {e}")
                continue
        
        if verbose:
            print(f"✅ Analyzed {len(story_files)} stories")
            print(f"📊 Found {len(all_collocations)} unique collocations")
            
        return all_collocations
    
    def generate_frequency_report(self, collocation_frequencies: Counter) -> Dict:
        """Generate detailed frequency analysis report.
        
        Args:
            collocation_frequencies: Counter with collocation frequencies
            
        Returns:
            Dictionary with frequency analysis statistics
        """
        total_collocations = len(collocation_frequencies)
        total_occurrences = sum(collocation_frequencies.values())
        
        # Frequency distribution
        freq_distribution = Counter(collocation_frequencies.values())
        
        # Most and least common items
        most_common = collocation_frequencies.most_common(20)
        least_common = [(item, freq) for item, freq in collocation_frequencies.most_common() 
                       if freq == min(collocation_frequencies.values())][:20]
        
        # Word length analysis
        length_stats = {}
        for collocation, freq in collocation_frequencies.items():
            word_count = len(collocation.split())
            if word_count not in length_stats:
                length_stats[word_count] = {'count': 0, 'total_freq': 0}
            length_stats[word_count]['count'] += 1
            length_stats[word_count]['total_freq'] += freq
        
        return {
            'total_unique_collocations': total_collocations,
            'total_occurrences': total_occurrences,
            'average_frequency': total_occurrences / total_collocations if total_collocations > 0 else 0,
            'frequency_distribution': dict(freq_distribution),
            'most_common': most_common,
            'least_common': least_common,
            'length_analysis': length_stats
        }
    
    def filter_by_frequency(self, collocation_frequencies: Counter, min_frequency: int = 3, 
                           verbose: bool = True) -> Tuple[Set[str], Dict]:
        """Filter collocations by minimum frequency threshold.
        
        Args:
            collocation_frequencies: Counter with collocation frequencies
            min_frequency: Minimum frequency threshold
            verbose: Whether to print progress information
            
        Returns:
            Tuple of (kept_collocations_set, filtering_stats)
        """
        if verbose:
            print(f"🔧 Filtering collocations with min_frequency = {min_frequency}")
        
        # Apply frequency filter
        kept_collocations = {
            collocation for collocation, freq in collocation_frequencies.items()
            if freq >= min_frequency
        }
        
        removed_collocations = {
            collocation for collocation, freq in collocation_frequencies.items()
            if freq < min_frequency
        }
        
        # Calculate statistics
        total_before = len(collocation_frequencies)
        total_kept = len(kept_collocations)
        total_removed = len(removed_collocations)
        
        kept_frequency_sum = sum(freq for colloc, freq in collocation_frequencies.items() 
                                if colloc in kept_collocations)
        removed_frequency_sum = sum(freq for colloc, freq in collocation_frequencies.items() 
                                   if colloc in removed_collocations)
        
        filtering_stats = {
            'min_frequency': min_frequency,
            'total_before': total_before,
            'total_kept': total_kept,
            'total_removed': total_removed,
            'kept_percentage': (total_kept / total_before * 100) if total_before > 0 else 0,
            'kept_frequency_sum': kept_frequency_sum,
            'removed_frequency_sum': removed_frequency_sum,
            'frequency_coverage': (kept_frequency_sum / (kept_frequency_sum + removed_frequency_sum) * 100) if (kept_frequency_sum + removed_frequency_sum) > 0 else 0
        }
        
        if verbose:
            print(f"  📋 Results:")
            print(f"    Collocations kept: {total_kept:,} ({filtering_stats['kept_percentage']:.1f}%)")
            print(f"    Collocations removed: {total_removed:,}")
            print(f"    Frequency coverage: {filtering_stats['frequency_coverage']:.1f}%")
        
        return kept_collocations, filtering_stats
    
    def apply_filtering_to_database(self, kept_collocations: Set[str], dry_run: bool = True, 
                                   verbose: bool = True) -> Dict:
        """Apply frequency filtering to the SRS database.
        
        Args:
            kept_collocations: Set of collocations to keep
            dry_run: If True, only show what would be changed
            verbose: Whether to print progress information
            
        Returns:
            Dictionary with database update statistics
        """
        if verbose:
            action = "Simulating" if dry_run else "Applying"
            print(f"🗃️ {action} database filtering...")
        
        # Get current SRS collocations
        current_collocations = self.db.get_all_collocations()
        current_texts = {colloc['text'] for colloc in current_collocations}
        
        # Check which collocations already have translations
        try:
            from enhanced_srs_database import EnhancedSRSDatabase
            enhanced_db = EnhancedSRSDatabase()
            translated_collocations = set()
            
            if verbose:
                print(f"  🔍 Checking for existing translations...")
            
            for text in current_texts:
                if enhanced_db.find_english_equivalent(text):
                    translated_collocations.add(text)
                    
            if verbose:
                print(f"  📝 Found {len(translated_collocations)} collocations with existing translations")
                
        except Exception as e:
            if verbose:
                print(f"  ⚠️ Could not check translations: {e}")
            translated_collocations = set()
        
        # Determine what to keep: frequent items OR items with existing translations
        db_kept = current_texts.intersection(kept_collocations) | translated_collocations
        db_removed = current_texts - db_kept
        
        # Calculate breakdown of kept items
        frequent_kept = current_texts.intersection(kept_collocations)
        translation_kept = translated_collocations - frequent_kept  # Items kept only for translations
        
        stats = {
            'current_total': len(current_texts),
            'kept_count': len(db_kept),
            'removed_count': len(db_removed),
            'kept_percentage': (len(db_kept) / len(current_texts) * 100) if current_texts else 0,
            'frequent_kept': len(frequent_kept),
            'translation_kept': len(translation_kept),
            'total_translated': len(translated_collocations)
        }
        
        if verbose:
            print(f"  📊 Database impact:")
            print(f"    Current collocations: {stats['current_total']:,}")
            print(f"    Would keep: {stats['kept_count']:,} ({stats['kept_percentage']:.1f}%)")
            print(f"      - Frequent items: {stats['frequent_kept']:,}")
            print(f"      - Already translated: {stats['translation_kept']:,}")
            print(f"    Would remove: {stats['removed_count']:,}")
        
        if not dry_run:
            if verbose:
                print(f"  🗑️ Removing {len(db_removed)} collocations from database...")
            
            # Remove low-frequency collocations from database
            for colloc_text in db_removed:
                try:
                    self.db.delete_collocation(colloc_text)
                except Exception as e:
                    if verbose:
                        print(f"    ⚠️ Error removing '{colloc_text}': {e}")
            
            if verbose:
                print(f"  ✅ Database filtering complete")
        
        return stats


def main():
    """Main function for the SRS frequency filtering script."""
    parser = argparse.ArgumentParser(
        description="Filter SRS collocations by frequency analysis"
    )
    parser.add_argument(
        '--min-frequency', 
        type=int, 
        default=3,
        help='Minimum frequency threshold (default: 3)'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be filtered without making changes'
    )
    parser.add_argument(
        '--save-report', 
        type=str,
        help='Save detailed frequency report to JSON file'
    )
    parser.add_argument(
        '--quiet', 
        action='store_true',
        help='Suppress verbose output'
    )
    
    args = parser.parse_args()
    
    print(f"🚀 SRS Frequency-Based Filtering")
    if args.dry_run:
        print(f"🧪 DRY RUN MODE - No changes will be made")
    print(f"📊 Minimum frequency threshold: {args.min_frequency}")
    
    try:
        # Initialize filter
        filter_tool = SRSFrequencyFilter()
        
        # Step 1: Analyze collocation frequencies
        collocation_frequencies = filter_tool.analyze_collocation_frequencies(verbose=not args.quiet)
        
        # Step 2: Generate frequency report
        if not args.quiet:
            print(f"\n📋 Generating frequency analysis report...")
        report = filter_tool.generate_frequency_report(collocation_frequencies)
        
        # Display key statistics
        print(f"\n📊 Frequency Analysis Results:")
        print(f"  Total unique collocations: {report['total_unique_collocations']:,}")
        print(f"  Total occurrences: {report['total_occurrences']:,}")
        print(f"  Average frequency: {report['average_frequency']:.2f}")
        
        # Show frequency distribution
        print(f"\n📈 Frequency Distribution:")
        freq_dist = report['frequency_distribution']
        for freq in sorted(freq_dist.keys())[:10]:  # Show first 10
            count = freq_dist[freq]
            print(f"    Items appearing {freq}x: {count:,}")
        if len(freq_dist) > 10:
            print(f"    ... and {len(freq_dist) - 10} more frequency levels")
        
        # Show top frequent items
        print(f"\n🔝 Most Frequent Collocations:")
        for i, (item, freq) in enumerate(report['most_common'][:10], 1):
            print(f"    {i:2d}. {item} ({freq}x)")
        
        # Step 3: Apply frequency filtering
        kept_collocations, filtering_stats = filter_tool.filter_by_frequency(
            collocation_frequencies, 
            args.min_frequency, 
            verbose=not args.quiet
        )
        
        # Step 4: Apply to database
        db_stats = filter_tool.apply_filtering_to_database(
            kept_collocations, 
            dry_run=args.dry_run,
            verbose=not args.quiet
        )
        
        # Final summary
        print(f"\n✅ Frequency Filtering {'Simulation' if args.dry_run else 'Complete'}!")
        print(f"  Collocations: {db_stats['current_total']:,} → {db_stats['kept_count']:,} ({db_stats['kept_percentage']:.1f}% kept)")
        print(f"  Frequency coverage: {filtering_stats['frequency_coverage']:.1f}%")
        
        # Save report if requested
        if args.save_report:
            report_data = {
                'frequency_analysis': report,
                'filtering_stats': filtering_stats,
                'database_stats': db_stats,
                'parameters': {
                    'min_frequency': args.min_frequency,
                    'dry_run': args.dry_run
                }
            }
            
            with open(args.save_report, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            print(f"📄 Detailed report saved to: {args.save_report}")
        
        return 0 if not args.dry_run else 0
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Filtering interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())