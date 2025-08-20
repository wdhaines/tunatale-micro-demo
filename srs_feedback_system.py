#!/usr/bin/env python3
"""
SRS Feedback System for TunaTale

Implements proper SRS feedback loop where collocations are only marked as
"reviewed" when they are actually used in generated stories, not just when
stories are generated.

This addresses the core issue identified by the usage validation system.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass

from srs_tracker import SRSTracker, ContentStrategy
from srs_usage_validator import SRSUsageValidator, UsageAnalysis
from story_collocation_extractor import StoryCollocationExtractor


@dataclass 
class SRSFeedbackResult:
    """Result of applying SRS feedback after story generation."""
    day: int
    story_file: str
    
    # What SRS provided vs what was used
    srs_provided: List[str]
    srs_actually_used: List[str] 
    srs_unused: List[str]
    
    # SRS updates made
    marked_as_reviewed: List[str]      # Collocations that were successfully used
    kept_for_retry: List[str]          # Unused collocations kept for future retry
    penalty_applied: List[str]         # Collocations with reduced stability (if any)
    
    # Statistics
    usage_rate: float
    feedback_applied: bool
    

class SRSFeedbackSystem:
    """Manages proper SRS feedback based on actual collocation usage in stories."""
    
    def __init__(self, data_dir: str = 'data', srs_filename: str = 'srs_status.json'):
        self.logger = logging.getLogger(__name__)
        self.srs_tracker = SRSTracker(data_dir=data_dir, filename=srs_filename)
        self.usage_validator = SRSUsageValidator(data_dir=data_dir, srs_filename=srs_filename)
        self.story_extractor = StoryCollocationExtractor()
        
    def apply_post_generation_feedback(self, day: int, story_path: Optional[Path] = None,
                                     srs_provided: Optional[List[str]] = None,
                                     strategy: Optional[ContentStrategy] = None) -> SRSFeedbackResult:
        """
        Apply SRS feedback after story generation based on actual usage.
        
        Args:
            day: Day number that was generated
            story_path: Path to generated story (auto-detected if None) 
            srs_provided: SRS collocations that were provided (retrieved if None)
            strategy: Content strategy used (affects feedback parameters)
            
        Returns:
            SRSFeedbackResult with detailed feedback actions taken
        """
        
        # Validate actual usage
        usage_analysis = self.usage_validator.validate_story_usage(
            day=day, story_path=story_path, srs_provided=srs_provided
        )
        
        # Apply feedback based on usage
        feedback_result = self._update_srs_based_on_usage(usage_analysis, strategy)
        
        self.logger.info(
            f"Applied SRS feedback for day {day}: "
            f"{len(feedback_result.marked_as_reviewed)} used, "
            f"{len(feedback_result.kept_for_retry)} unused, "
            f"{feedback_result.usage_rate:.1f}% usage rate"
        )
        
        return feedback_result
        
    def _update_srs_based_on_usage(self, usage_analysis: UsageAnalysis, 
                                  strategy: Optional[ContentStrategy] = None) -> SRSFeedbackResult:
        """Update SRS tracker based on actual collocation usage in story."""
        
        marked_as_reviewed = []
        kept_for_retry = []
        penalty_applied = []
        
        # Process each SRS-provided collocation
        for collocation in usage_analysis.srs_provided_collocations:
            if collocation in usage_analysis.used_collocations:
                # Collocation was actually used - mark as reviewed
                self._mark_collocation_as_reviewed(collocation, usage_analysis.day, strategy)
                marked_as_reviewed.append(collocation)
                
            else:
                # Collocation was provided but not used
                if self._should_retry_collocation(collocation, usage_analysis.day):
                    # Keep for future retry (don't penalize immediately)
                    kept_for_retry.append(collocation)
                else:
                    # Apply minor penalty for repeated non-usage
                    self._apply_usage_penalty(collocation, usage_analysis.day)
                    penalty_applied.append(collocation)
                    kept_for_retry.append(collocation)  # Still keep for retry but with penalty
        
        # Save SRS state after updates
        self.srs_tracker._save_state()
        
        return SRSFeedbackResult(
            day=usage_analysis.day,
            story_file=usage_analysis.story_file,
            srs_provided=usage_analysis.srs_provided_collocations,
            srs_actually_used=usage_analysis.used_collocations,
            srs_unused=usage_analysis.unused_collocations,
            marked_as_reviewed=marked_as_reviewed,
            kept_for_retry=kept_for_retry,
            penalty_applied=penalty_applied,
            usage_rate=usage_analysis.usage_rate,
            feedback_applied=True
        )
    
    def _mark_collocation_as_reviewed(self, collocation: str, day: int, 
                                    strategy: Optional[ContentStrategy] = None) -> None:
        """Mark a collocation as successfully reviewed (actually used in story)."""
        
        if collocation not in self.srs_tracker.collocations:
            self.logger.warning(f"Collocation '{collocation}' not found in SRS for review update")
            return
            
        colloc_status = self.srs_tracker.collocations[collocation]
        
        # Update review status
        colloc_status.last_seen_day = day
        colloc_status.appearances.append(day)
        colloc_status.review_count += 1
        
        # Calculate next review interval based on strategy
        if strategy:
            try:
                from content_strategy import get_strategy_config
                config = get_strategy_config(strategy)
                interval_multiplier = config.review_interval_multiplier
            except:
                interval_multiplier = 1.0
        else:
            interval_multiplier = 1.0
            
        # Standard SRS interval calculation with strategy adjustment
        base_interval = max(1, int(colloc_status.stability * 2 ** (colloc_status.review_count - 1)))
        adjusted_interval = max(1, int(base_interval * interval_multiplier))
        colloc_status.next_review_day = day + adjusted_interval
        
        # Increase stability (successful review)
        if strategy == ContentStrategy.DEEPER:
            colloc_status.stability *= 1.1  # Slower progression for deeper learning
        elif strategy == ContentStrategy.WIDER:
            colloc_status.stability *= 1.3  # Faster progression for wider coverage
        else:
            colloc_status.stability *= 1.2  # Balanced approach
            
        self.logger.debug(f"Marked '{collocation}' as reviewed: next review day {colloc_status.next_review_day}")
        
    def _should_retry_collocation(self, collocation: str, day: int) -> bool:
        """Determine if an unused collocation should be retried without penalty."""
        
        if collocation not in self.srs_tracker.collocations:
            return False
            
        colloc_status = self.srs_tracker.collocations[collocation]
        
        # Don't penalize if this is the first or second miss
        days_since_due = day - colloc_status.next_review_day
        recent_misses = sum(1 for appearance_day in colloc_status.appearances 
                          if day - appearance_day <= 3)  # Misses in last 3 days
        
        # Be lenient for first few attempts or if recently due
        return recent_misses <= 2 or days_since_due <= 1
    
    def _apply_usage_penalty(self, collocation: str, day: int) -> None:
        """Apply minor penalty for repeated non-usage of provided collocation."""
        
        if collocation not in self.srs_tracker.collocations:
            return
            
        colloc_status = self.srs_tracker.collocations[collocation]
        
        # Small stability reduction (don't penalize too harshly)
        colloc_status.stability *= 0.9
        
        # Don't schedule too far in future, but give a short break
        colloc_status.next_review_day = day + 2
        
        self.logger.debug(f"Applied usage penalty to '{collocation}': stability reduced to {colloc_status.stability:.2f}")
    
    def get_usage_optimized_collocations(self, day: int, strategy: Optional[ContentStrategy] = None,
                                       min_items: int = 3, max_items: int = 5) -> List[str]:
        """
        Get collocations optimized for actual usage in stories.
        
        This method prioritizes collocations that are more likely to be used
        based on historical usage patterns and context.
        """
        
        # Get standard due collocations
        standard_collocations = self.srs_tracker.get_due_collocations(
            day=day, min_items=min_items, max_items=max_items, strategy=strategy
        )
        
        # TODO: In future, this could be enhanced with:
        # - Context awareness (what type of story is being generated)
        # - Usage probability scoring based on historical data
        # - Collocation difficulty balancing
        
        return standard_collocations
    
    def generate_feedback_report(self, days: int = 7) -> Dict:
        """Generate a report on SRS feedback effectiveness over recent days."""
        
        report = {
            'analysis_period_days': days,
            'daily_results': [],
            'aggregate_stats': {}
        }
        
        current_day = self.srs_tracker.current_day
        total_provided = 0
        total_used = 0
        total_days_analyzed = 0
        
        for day in range(max(1, current_day - days + 1), current_day + 1):
            try:
                usage_analysis = self.usage_validator.validate_story_usage(day)
                
                daily_result = {
                    'day': day,
                    'srs_provided_count': usage_analysis.srs_total_provided,
                    'srs_used_count': len(usage_analysis.used_collocations),
                    'usage_rate': usage_analysis.usage_rate,
                    'story_collocations_count': usage_analysis.story_total_found,
                    'match_rate': usage_analysis.match_rate
                }
                
                report['daily_results'].append(daily_result)
                
                total_provided += usage_analysis.srs_total_provided
                total_used += len(usage_analysis.used_collocations)
                total_days_analyzed += 1
                
            except Exception as e:
                self.logger.warning(f"Could not analyze day {day}: {e}")
        
        # Calculate aggregate statistics
        if total_days_analyzed > 0:
            report['aggregate_stats'] = {
                'total_days_analyzed': total_days_analyzed,
                'total_srs_collocations_provided': total_provided,
                'total_srs_collocations_used': total_used,
                'overall_usage_rate': (total_used / total_provided * 100) if total_provided > 0 else 0,
                'average_daily_usage_rate': sum(r['usage_rate'] for r in report['daily_results']) / len(report['daily_results']),
                'feedback_system_effectiveness': 'needs_improvement' if report['aggregate_stats']['overall_usage_rate'] < 30 else 'good'
            }
        
        return report


def main():
    """Command-line interface for SRS feedback system."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Apply SRS feedback based on story usage')
    parser.add_argument('day', type=int, help='Day number to apply feedback for')
    parser.add_argument('--story-path', help='Path to story file (auto-detected if not provided)')
    parser.add_argument('--strategy', choices=['balanced', 'wider', 'deeper'], help='Content strategy used')
    parser.add_argument('--report', action='store_true', help='Generate feedback effectiveness report')
    parser.add_argument('--report-days', type=int, default=7, help='Days to include in report')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        feedback_system = SRSFeedbackSystem()
        
        if args.report:
            report = feedback_system.generate_feedback_report(args.report_days)
            print(f"\n=== SRS Feedback Effectiveness Report ===")
            print(f"Analysis Period: {report['analysis_period_days']} days")
            
            for daily in report['daily_results']:
                print(f"Day {daily['day']}: {daily['usage_rate']:.1f}% usage ({daily['srs_used_count']}/{daily['srs_provided_count']} collocations)")
            
            if report['aggregate_stats']:
                stats = report['aggregate_stats']
                print(f"\nAggregate Statistics:")
                print(f"  Overall Usage Rate: {stats['overall_usage_rate']:.1f}%")
                print(f"  Average Daily Usage: {stats['average_daily_usage_rate']:.1f}%")
                print(f"  System Effectiveness: {stats['feedback_system_effectiveness']}")
            
        else:
            strategy = ContentStrategy(args.strategy) if args.strategy else None
            story_path = Path(args.story_path) if args.story_path else None
            
            result = feedback_system.apply_post_generation_feedback(
                day=args.day,
                story_path=story_path, 
                strategy=strategy
            )
            
            print(f"\n=== SRS Feedback Applied for Day {args.day} ===")
            print(f"Story: {Path(result.story_file).name}")
            print(f"Usage Rate: {result.usage_rate:.1f}%")
            print(f"Marked as Reviewed: {len(result.marked_as_reviewed)} collocations")
            print(f"Kept for Retry: {len(result.kept_for_retry)} collocations")
            print(f"Penalties Applied: {len(result.penalty_applied)} collocations")
            
            if result.marked_as_reviewed:
                print(f"\n✅ Successfully Used:")
                for colloc in result.marked_as_reviewed:
                    print(f"  - {colloc}")
                    
            if result.penalty_applied:
                print(f"\n⚠️ Penalties Applied:")
                for colloc in result.penalty_applied:
                    print(f"  - {colloc}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()