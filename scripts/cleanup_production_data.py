#!/usr/bin/env python3
"""
Production Data Cleanup Script

This script addresses the critical data quality issues identified:
- Voice tags in collocations (tagalog-female-1, tagalog-male-1, etc.)
- System markers ([narrator, **, etc.)
- Embedded syllable data
- Format inconsistencies

CRITICAL: This script MODIFIES production data. Run with --dry-run first!
"""

import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

class ProductionDataCleaner:
    """Handles cleanup of production data with backup and validation."""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.backup_dir = Path("data_backup") / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.stats = {
            'collocations_cleaned': 0,
            'collocations_removed': 0,
            'curricula_migrated': 0,
            'story_guidance_added': 0,
            'files_processed': 0
        }
        
        if not dry_run:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, file_path: Path) -> Path:
        """Create backup of file before modification."""
        if self.dry_run:
            return file_path
        
        backup_path = self.backup_dir / file_path.name
        shutil.copy2(file_path, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return backup_path
    
    def clean_collocations(self, file_path: Path) -> Dict[str, Any]:
        """Clean collocation data removing voice tags and system markers."""
        print(f"\n=== CLEANING COLLOCATIONS: {file_path} ===")
        
        if not file_path.exists():
            print(f"⚠️ File not found: {file_path}")
            return {'status': 'not_found'}
        
        # Backup first
        self.create_backup(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            collocations = json.load(f)
        
        original_count = len(collocations)
        print(f"Original collocations: {original_count}")
        
        # Define patterns to remove
        voice_patterns = [
            'tagalog-female-', 'tagalog-male-', 'english-',
            'voice:', 'audio:', 'tts:'
        ]
        
        system_patterns = [
            '[narrator', '[', '**', '{{', '}}',
            'system:', 'pause:', 'break:'
        ]
        
        # Clean collocations
        cleaned_collocations = {}
        removed_entries = []
        cleaned_entries = []
        
        for collocation, count in collocations.items():
            # Check for voice tags
            if any(pattern in collocation.lower() for pattern in voice_patterns):
                removed_entries.append((collocation, count, 'voice_tag'))
                self.stats['collocations_removed'] += 1
                continue
            
            # Check for system markers
            if any(pattern in collocation.lower() for pattern in system_patterns):
                removed_entries.append((collocation, count, 'system_marker'))
                self.stats['collocations_removed'] += 1
                continue
            
            # Clean embedded syllables (e.g., "ito po\\npo\\nito\\nto")
            if '\\n' in collocation:
                # Extract main phrase (first line)
                main_phrase = collocation.split('\\n')[0].strip()
                if main_phrase and len(main_phrase) > 1:
                    cleaned_collocations[main_phrase] = cleaned_collocations.get(main_phrase, 0) + count
                    cleaned_entries.append((collocation, main_phrase, count))
                    self.stats['collocations_cleaned'] += 1
                else:
                    removed_entries.append((collocation, count, 'invalid_syllable_data'))
                    self.stats['collocations_removed'] += 1
                continue
            
            # Keep clean collocations
            cleaned_collocations[collocation] = count
        
        final_count = len(cleaned_collocations)
        removed_count = len(removed_entries)
        cleaned_count = len(cleaned_entries)
        
        print(f"\n📊 CLEANUP RESULTS:")
        print(f"  • Original entries: {original_count}")
        print(f"  • Clean entries kept: {final_count - cleaned_count}")
        print(f"  • Entries cleaned (syllables): {cleaned_count}")
        print(f"  • Entries removed (contaminated): {removed_count}")
        print(f"  • Final entries: {final_count}")
        print(f"  • Corruption removed: {removed_count + cleaned_count} ({(removed_count + cleaned_count)/original_count*100:.1f}%)")
        
        if removed_entries:
            print(f"\n🗑️ REMOVED ENTRIES (top 10):")
            for colloc, count, reason in sorted(removed_entries, key=lambda x: x[1], reverse=True)[:10]:
                print(f"  • '{colloc[:50]}{'...' if len(colloc) > 50 else ''}' (count: {count}, reason: {reason})")
        
        if cleaned_entries:
            print(f"\n🧹 CLEANED ENTRIES (top 10):")
            for original, cleaned, count in cleaned_entries[:10]:
                print(f"  • '{original[:30]}...' → '{cleaned}' (count: {count})")
        
        # Save cleaned data
        if not self.dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_collocations, f, indent=2, ensure_ascii=False)
            print(f"✅ Cleaned collocations saved to {file_path}")
        else:
            print(f"🔍 DRY RUN: Would save {final_count} cleaned collocations to {file_path}")
        
        self.stats['files_processed'] += 1
        
        return {
            'status': 'success',
            'original_count': original_count,
            'final_count': final_count,
            'removed_count': removed_count,
            'cleaned_count': cleaned_count,
            'corruption_rate': (removed_count + cleaned_count) / original_count if original_count > 0 else 0
        }
    
    def migrate_curriculum_format(self, file_path: Path) -> Dict[str, Any]:
        """Migrate curriculum from dict format to list format and add missing fields."""
        print(f"\n=== MIGRATING CURRICULUM: {file_path} ===")
        
        if not file_path.exists():
            print(f"⚠️ File not found: {file_path}")
            return {'status': 'not_found'}
        
        # Backup first
        self.create_backup(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            curriculum = json.load(f)
        
        migration_actions = []
        
        # Check if days is in dict format
        if 'days' in curriculum and isinstance(curriculum['days'], dict):
            print(f"📝 Converting days from dict to list format...")
            
            # Convert dict to list
            days_list = []
            for day_key, day_data in curriculum['days'].items():
                # Ensure required fields exist
                if 'story_guidance' not in day_data:
                    day_data['story_guidance'] = ""
                    self.stats['story_guidance_added'] += 1
                    migration_actions.append(f"Added story_guidance to {day_key}")
                
                days_list.append(day_data)
            
            # Sort by day number
            days_list.sort(key=lambda x: x.get('day', 0))
            curriculum['days'] = days_list
            migration_actions.append("Converted dict format to list format")
            
        elif 'days' in curriculum and isinstance(curriculum['days'], list):
            print(f"📝 Validating list format and adding missing fields...")
            
            # Check for missing story_guidance in list format
            for i, day in enumerate(curriculum['days']):
                if 'story_guidance' not in day:
                    day['story_guidance'] = ""
                    self.stats['story_guidance_added'] += 1
                    migration_actions.append(f"Added story_guidance to day {i+1}")
        
        print(f"\n📊 MIGRATION ACTIONS:")
        for action in migration_actions:
            print(f"  • {action}")
        
        # Save migrated data
        if not self.dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(curriculum, f, indent=2, ensure_ascii=False)
            print(f"✅ Migrated curriculum saved to {file_path}")
        else:
            print(f"🔍 DRY RUN: Would save migrated curriculum to {file_path}")
        
        if migration_actions:
            self.stats['curricula_migrated'] += 1
        self.stats['files_processed'] += 1
        
        return {
            'status': 'success',
            'actions': migration_actions,
            'migrations_needed': len(migration_actions) > 0
        }
    
    def cleanup_all_production_data(self) -> Dict[str, Any]:
        """Clean all production data files."""
        print(f"\n{'='*60}")
        print(f"PRODUCTION DATA CLEANUP - {'DRY RUN' if self.dry_run else 'LIVE RUN'}")
        print(f"{'='*60}")
        
        results = {}
        
        # 1. Clean collocations
        collocations_path = Path("instance/data/collocations.json")
        results['collocations'] = self.clean_collocations(collocations_path)
        
        # 2. Migrate curriculum files
        curricula_dir = Path("instance/data/curricula")
        if curricula_dir.exists():
            curriculum_files = list(curricula_dir.glob("*.json"))
            results['curricula'] = {}
            
            for file_path in curriculum_files:
                results['curricula'][file_path.name] = self.migrate_curriculum_format(file_path)
        
        # 3. Check other curriculum files in instance/data (not root)
        instance_curriculum_files = [
            Path("instance/data/curriculum.json"),
            Path("instance/data/curriculum_processed.json")
        ]
        
        for file_path in instance_curriculum_files:
            if file_path.exists():
                if 'curricula' not in results:
                    results['curricula'] = {}
                results['curricula'][file_path.name] = self.migrate_curriculum_format(file_path)
        
        return results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print cleanup summary."""
        print(f"\n{'='*60}")
        print(f"CLEANUP SUMMARY - {'DRY RUN' if self.dry_run else 'COMPLETED'}")
        print(f"{'='*60}")
        
        print(f"📁 Files processed: {self.stats['files_processed']}")
        print(f"🧹 Collocations cleaned: {self.stats['collocations_cleaned']}")
        print(f"🗑️ Collocations removed: {self.stats['collocations_removed']}")
        print(f"📄 Curricula migrated: {self.stats['curricula_migrated']}")
        print(f"📝 Story guidance fields added: {self.stats['story_guidance_added']}")
        
        if not self.dry_run and self.backup_dir.exists():
            print(f"💾 Backups saved to: {self.backup_dir}")
        
        # Detailed results
        if 'collocations' in results:
            colloc_result = results['collocations']
            if colloc_result['status'] == 'success':
                corruption_rate = colloc_result['corruption_rate'] * 100
                print(f"\n🎯 COLLOCATION CLEANUP SUCCESS:")
                print(f"   • Corruption rate eliminated: {corruption_rate:.1f}%")
                print(f"   • Clean collocations: {colloc_result['final_count']}")
        
        if 'curricula' in results:
            migrated_count = sum(1 for r in results['curricula'].values() 
                               if r.get('migrations_needed', False))
            print(f"\n📚 CURRICULUM MIGRATION SUCCESS:")
            print(f"   • Files requiring migration: {migrated_count}")
            print(f"   • All files now use standardized format")


def main():
    parser = argparse.ArgumentParser(description="Clean production data for TunaTale")
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    parser.add_argument('--force', action='store_true',
                       help='Actually perform the cleanup (removes dry-run protection)')
    
    args = parser.parse_args()
    
    # Safety: default to dry-run unless --force is specified
    dry_run = not args.force
    
    if dry_run:
        print("🔍 Running in DRY-RUN mode. Use --force to actually modify files.")
    else:
        print("⚠️ LIVE RUN MODE: Files will be modified!")
        response = input("Are you sure you want to modify production data? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Aborted.")
            return
    
    cleaner = ProductionDataCleaner(dry_run=dry_run)
    results = cleaner.cleanup_all_production_data()
    cleaner.print_summary(results)
    
    if dry_run:
        print(f"\n💡 To apply these changes, run: python {__file__} --force")


if __name__ == "__main__":
    main()