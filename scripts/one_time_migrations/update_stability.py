#!/usr/bin/env python3
"""
Update SRS database with component-based stability values.

This script recalculates stability for all collocations in the SRS database
based on component word frequencies, replacing the unrealistic uniform
stability=1.0 values with more realistic difficulty-based scores.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

from srs_database import SRSDatabase
from component_difficulty import ComponentDifficultyCalculator, ComponentDifficultyConfig

logger = logging.getLogger(__name__)

@dataclass
class StabilityUpdateConfig:
    """Configuration for stability update process."""
    
    # Backup settings
    create_backup: bool = True
    backup_suffix: str = "_backup_before_stability_update"
    
    # Update settings  
    batch_size: int = 100
    min_stability: float = 0.1
    max_stability: float = 3.0
    
    # Validation settings
    validate_before_update: bool = True
    validate_after_update: bool = True
    
    # Reporting
    detailed_report: bool = True
    save_report: bool = True
    report_path: str = "instance/data/stability_update_report.json"


class StabilityUpdater:
    """Update SRS database with component-based stability values."""
    
    def __init__(self, 
                 srs_db_path: str = "instance/data/srs/tunatale_srs.db",
                 frequency_db_path: str = "instance/data/word_frequency.json",
                 config: StabilityUpdateConfig = None):
        """Initialize the stability updater."""
        self.config = config or StabilityUpdateConfig()
        self.srs_db_path = srs_db_path
        self.frequency_db_path = frequency_db_path
        
        # Initialize components
        self.srs_db = SRSDatabase(srs_db_path)
        self.difficulty_calculator = ComponentDifficultyCalculator(frequency_db_path)
        
        # Statistics tracking
        self.update_stats = {
            'total_collocations': 0,
            'updated_collocations': 0,
            'skipped_collocations': 0,
            'stability_changes': [],
            'errors': []
        }
    
    def create_backup(self) -> str:
        """Create backup of the SRS database before updating."""
        if not self.config.create_backup:
            return None
            
        backup_path = f"{self.srs_db_path}{self.config.backup_suffix}"
        
        try:
            import shutil
            shutil.copy2(self.srs_db_path, backup_path)
            logger.info(f"Created database backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def validate_database_state(self, stage: str = "before") -> Dict[str, Any]:
        """Validate database state and return statistics."""
        try:
            all_collocations = self.srs_db.get_all_collocations()
            
            stability_values = [item.get('stability', 0) for item in all_collocations]
            stability_counts = {}
            for stability in stability_values:
                stability_counts[stability] = stability_counts.get(stability, 0) + 1
            
            validation_result = {
                'stage': stage,
                'total_collocations': len(all_collocations),
                'stability_distribution': stability_counts,
                'min_stability': min(stability_values) if stability_values else 0,
                'max_stability': max(stability_values) if stability_values else 0,
                'avg_stability': sum(stability_values) / len(stability_values) if stability_values else 0,
                'uniform_stability_count': stability_counts.get(1.0, 0)  # Count of stability=1.0
            }
            
            logger.info(f"Database validation ({stage}): {validation_result['total_collocations']} "
                       f"collocations, avg stability: {validation_result['avg_stability']:.3f}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Database validation failed: {e}")
            return {'stage': stage, 'error': str(e)}
    
    def calculate_new_stability(self, collocation_text: str, current_stability: float) -> float:
        """Calculate new stability value for a collocation."""
        try:
            # Use component-based difficulty calculation
            difficulty_score = self.difficulty_calculator.calculate_difficulty_score(collocation_text)
            new_stability = self.difficulty_calculator.calculate_stability_from_difficulty(difficulty_score)
            
            # Clamp to configured bounds
            new_stability = max(self.config.min_stability, 
                              min(self.config.max_stability, new_stability))
            
            return new_stability
            
        except Exception as e:
            logger.warning(f"Failed to calculate stability for '{collocation_text}': {e}")
            return current_stability  # Return original value if calculation fails
    
    def update_collocation_stability(self, collocation: Dict[str, Any]) -> bool:
        """Update stability for a single collocation."""
        try:
            text = collocation['text']
            current_stability = collocation.get('stability', 1.0)
            
            # Calculate new stability
            new_stability = self.calculate_new_stability(text, current_stability)
            
            # Skip if no change needed (within small tolerance)
            if abs(new_stability - current_stability) < 0.01:
                self.update_stats['skipped_collocations'] += 1
                return False
            
            # Update in database
            success = self.srs_db.update_collocation_stability(text, new_stability)
            
            if success:
                # Track the change
                self.update_stats['stability_changes'].append({
                    'text': text,
                    'old_stability': current_stability,
                    'new_stability': new_stability,
                    'change': new_stability - current_stability
                })
                self.update_stats['updated_collocations'] += 1
                return True
            else:
                self.update_stats['errors'].append(f"Database update failed for '{text}'")
                return False
                
        except Exception as e:
            error_msg = f"Error updating '{collocation.get('text', 'unknown')}': {e}"
            self.update_stats['errors'].append(error_msg)
            logger.error(error_msg)
            return False
    
    def update_all_stabilities(self) -> Dict[str, Any]:
        """Update stability values for all collocations in the database."""
        logger.info("Starting stability update process...")
        
        # Validation before update
        before_validation = None
        if self.config.validate_before_update:
            before_validation = self.validate_database_state("before")
        
        # Create backup
        backup_path = self.create_backup()
        
        try:
            # Get all collocations
            all_collocations = self.srs_db.get_all_collocations()
            self.update_stats['total_collocations'] = len(all_collocations)
            
            logger.info(f"Updating stability for {len(all_collocations)} collocations...")
            
            # Process in batches
            for i in range(0, len(all_collocations), self.config.batch_size):
                batch = all_collocations[i:i + self.config.batch_size]
                
                for collocation in batch:
                    self.update_collocation_stability(collocation)
                
                # Log progress
                progress = min(i + self.config.batch_size, len(all_collocations))
                logger.info(f"Progress: {progress}/{len(all_collocations)} "
                           f"({progress/len(all_collocations)*100:.1f}%)")
            
            # Validation after update
            after_validation = None
            if self.config.validate_after_update:
                after_validation = self.validate_database_state("after")
            
            # Compile results
            update_result = {
                'success': True,
                'backup_path': backup_path,
                'before_validation': before_validation,
                'after_validation': after_validation,
                'statistics': self.update_stats.copy(),
                'config': self.config.__dict__
            }
            
            logger.info(f"Stability update completed successfully. "
                       f"Updated: {self.update_stats['updated_collocations']}, "
                       f"Skipped: {self.update_stats['skipped_collocations']}, "
                       f"Errors: {len(self.update_stats['errors'])}")
            
            return update_result
            
        except Exception as e:
            error_msg = f"Stability update failed: {e}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'backup_path': backup_path,
                'statistics': self.update_stats.copy()
            }
    
    def generate_detailed_report(self, update_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed report of the stability update process."""
        if not self.config.detailed_report:
            return {}
        
        report = {
            'timestamp': str(Path().stat().st_mtime),  # Current time approximation
            'update_success': update_result['success'],
            'summary': {
                'total_collocations': self.update_stats['total_collocations'],
                'updated_count': self.update_stats['updated_collocations'],
                'skipped_count': self.update_stats['skipped_collocations'],
                'error_count': len(self.update_stats['errors'])
            }
        }
        
        # Add validation comparisons
        if update_result.get('before_validation') and update_result.get('after_validation'):
            before = update_result['before_validation']
            after = update_result['after_validation']
            
            report['stability_change_summary'] = {
                'before_avg': before.get('avg_stability', 0),
                'after_avg': after.get('avg_stability', 0),
                'before_uniform_count': before.get('uniform_stability_count', 0),
                'after_uniform_count': after.get('uniform_stability_count', 0),
                'range_before': f"{before.get('min_stability', 0):.3f} - {before.get('max_stability', 0):.3f}",
                'range_after': f"{after.get('min_stability', 0):.3f} - {after.get('max_stability', 0):.3f}"
            }
        
        # Add sample changes (top 10 increases and decreases)
        if self.update_stats['stability_changes']:
            changes = self.update_stats['stability_changes']
            
            # Sort by change amount
            increases = sorted([c for c in changes if c['change'] > 0], 
                             key=lambda x: x['change'], reverse=True)[:10]
            decreases = sorted([c for c in changes if c['change'] < 0], 
                             key=lambda x: x['change'])[:10]
            
            report['sample_changes'] = {
                'largest_increases': increases,
                'largest_decreases': decreases
            }
        
        # Add error details if any
        if self.update_stats['errors']:
            report['errors'] = self.update_stats['errors'][:20]  # Limit to first 20 errors
        
        return report
    
    def save_report(self, report: Dict[str, Any]) -> str:
        """Save detailed report to JSON file."""
        if not self.config.save_report:
            return None
        
        try:
            # Ensure directory exists
            Path(self.config.report_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config.report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved detailed report to {self.config.report_path}")
            return self.config.report_path
            
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            return None


def main():
    """Main execution function."""
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create updater with default configuration
    config = StabilityUpdateConfig(
        detailed_report=True,
        save_report=True,
        validate_before_update=True,
        validate_after_update=True
    )
    
    updater = StabilityUpdater(config=config)
    
    print("=== SRS Database Stability Update ===")
    print("This will update all collocation stability values based on component word frequencies.")
    print(f"Database: {updater.srs_db_path}")
    print(f"Frequency DB: {updater.frequency_db_path}")
    print()
    
    # Check if databases exist
    srs_path = Path(updater.srs_db_path)
    freq_path = Path(updater.frequency_db_path)
    
    if not srs_path.exists():
        print(f"ERROR: SRS database not found: {srs_path}")
        return
    
    if not freq_path.exists():
        print(f"ERROR: Frequency database not found: {freq_path}")
        print("Please run 'python build_word_frequency.py' first.")
        return
    
    # Run the update
    try:
        update_result = updater.update_all_stabilities()
        
        if update_result['success']:
            print("\n✅ Stability update completed successfully!")
            
            # Generate and save detailed report
            detailed_report = updater.generate_detailed_report(update_result)
            report_path = updater.save_report(detailed_report)
            
            # Print summary
            stats = update_result['statistics']
            print(f"\nSummary:")
            print(f"  Total collocations: {stats['total_collocations']}")
            print(f"  Updated: {stats['updated_collocations']}")
            print(f"  Skipped (no change): {stats['skipped_collocations']}")
            print(f"  Errors: {len(stats['errors'])}")
            
            if update_result.get('before_validation') and update_result.get('after_validation'):
                before = update_result['before_validation']
                after = update_result['after_validation']
                print(f"\nStability Changes:")
                print(f"  Before - Avg: {before['avg_stability']:.3f}, "
                      f"Range: {before['min_stability']:.3f}-{before['max_stability']:.3f}")
                print(f"  After  - Avg: {after['avg_stability']:.3f}, "
                      f"Range: {after['min_stability']:.3f}-{after['max_stability']:.3f}")
                print(f"  Uniform (1.0) values: {before['uniform_stability_count']} → {after['uniform_stability_count']}")
            
            if report_path:
                print(f"\nDetailed report saved to: {report_path}")
                
            if update_result.get('backup_path'):
                print(f"Database backup created: {update_result['backup_path']}")
                
        else:
            print(f"\n❌ Stability update failed: {update_result.get('error', 'Unknown error')}")
            
            if update_result.get('backup_path'):
                print(f"Database backup available: {update_result['backup_path']}")
    
    except Exception as e:
        print(f"\n❌ Update process failed with error: {e}")
        logger.exception("Update process failed")


if __name__ == "__main__":
    main()