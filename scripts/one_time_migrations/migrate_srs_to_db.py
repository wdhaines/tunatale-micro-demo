#!/usr/bin/env python3
"""
Migration script to convert SRS data from JSON to SQLite database.
Preserves all existing collocation data and creates backup.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Import our database class
from srs_database import SRSDatabase


def migrate_json_to_database(json_path: str = "data/srs_status.json", 
                           db_path: str = "instance/data/srs/tunatale_srs.db") -> bool:
    """Migrate existing JSON SRS data to SQLite database.
    
    Args:
        json_path: Path to the source JSON file
        db_path: Path to the target database file
        
    Returns:
        True if migration successful, False otherwise
    """
    json_file = Path(json_path)
    
    # Check if source file exists
    if not json_file.exists():
        print(f"❌ Source file not found: {json_path}")
        print("No existing SRS data to migrate.")
        return False
    
    # Load and validate JSON data
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error reading JSON file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return False
    
    # Validate JSON structure
    if 'collocations' not in data:
        print("❌ Invalid JSON format: missing 'collocations' key")
        return False
    
    collocations_data = data['collocations']
    current_day = data.get('current_day', 1)
    
    print(f"📊 Found {len(collocations_data)} collocations at day {current_day}")
    
    # Initialize database
    try:
        db = SRSDatabase(db_path)
        print(f"✅ Database initialized at {db_path}")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False
    
    # Migrate each collocation
    migrated_count = 0
    error_count = 0
    
    for text, colloc_data in collocations_data.items():
        try:
            # Validate required fields
            required_fields = ['first_seen_day', 'last_seen_day', 'appearances', 
                             'review_count', 'next_review_day', 'stability']
            
            for field in required_fields:
                if field not in colloc_data:
                    print(f"⚠️  Skipping '{text}': missing field '{field}'")
                    error_count += 1
                    continue
            
            # Add to database
            db.add_collocation(
                text=text,
                first_seen_day=colloc_data['first_seen_day'],
                last_seen_day=colloc_data['last_seen_day'],
                appearances=colloc_data['appearances'],
                review_count=colloc_data['review_count'],
                next_review_day=colloc_data['next_review_day'],
                stability=colloc_data['stability']
            )
            
            migrated_count += 1
            
        except Exception as e:
            print(f"⚠️  Error migrating '{text}': {e}")
            error_count += 1
            continue
    
    # Verify migration
    db_count = db.get_collocations_count()
    
    if db_count == migrated_count:
        print(f"✅ Successfully migrated {migrated_count} collocations")
        
        # Create backup of original file
        backup_path = json_file.with_suffix('.json.backup')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = json_file.with_suffix(f'.json.backup.{timestamp}')
        
        try:
            json_file.rename(backup_path)
            print(f"💾 Original file backed up to: {backup_path}")
        except Exception as e:
            print(f"⚠️  Could not create backup: {e}")
        
        # Show statistics
        stats = db.get_statistics()
        print("\n📈 Migration Statistics:")
        print(f"  Total collocations: {stats['total_collocations']}")
        print(f"  New (0 reviews): {stats['new']}")
        print(f"  Learning (1-3 reviews): {stats['learning']}")
        print(f"  Well-known (4+ reviews): {stats['well_known']}")
        print(f"  Average stability: {stats['average_stability']}")
        
        if error_count > 0:
            print(f"\n⚠️  {error_count} collocations had errors and were skipped")
        
        return True
    
    else:
        print(f"❌ Migration verification failed!")
        print(f"  Expected: {migrated_count} collocations")
        print(f"  Found in DB: {db_count} collocations")
        return False


def validate_migration(db_path: str = "instance/data/srs/tunatale_srs.db") -> bool:
    """Validate that the migration was successful.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        True if validation passes
    """
    try:
        db = SRSDatabase(db_path)
        
        print("\n🔍 Validating migration...")
        
        # Basic count check
        total = db.get_collocations_count()
        if total == 0:
            print("❌ No collocations found in database")
            return False
        
        print(f"✅ Found {total} collocations in database")
        
        # Sample a few collocations to verify structure
        all_collocations = db.get_all_collocations()
        sample_size = min(5, len(all_collocations))
        
        print(f"📝 Validating structure of {sample_size} sample collocations:")
        
        for i, colloc in enumerate(all_collocations[:sample_size]):
            text = colloc['text']
            appearances = colloc['appearances']
            
            print(f"  {i+1}. '{text}': {len(appearances)} appearances, "
                  f"{colloc['review_count']} reviews, "
                  f"stability {colloc['stability']}")
            
            # Validate appearances is a list
            if not isinstance(appearances, list):
                print(f"❌ Invalid appearances format for '{text}'")
                return False
        
        print("✅ Migration validation passed!")
        return True
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False


def main():
    """Main migration function with command line interface."""
    print("🔄 TunaTale SRS JSON → SQLite Migration")
    print("=" * 40)
    
    # Check command line arguments
    json_path = "data/srs_status.json"
    db_path = "instance/data/srs/tunatale_srs.db"
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("Usage: python migrate_srs_to_db.py [json_path] [db_path]")
            print("  json_path: Path to source JSON file (default: data/srs_status.json)")
            print("  db_path: Path to target database (default: instance/data/srs/tunatale_srs.db)")
            return
        json_path = sys.argv[1]
    
    if len(sys.argv) > 2:
        db_path = sys.argv[2]
    
    print(f"Source: {json_path}")
    print(f"Target: {db_path}")
    print()
    
    # Perform migration
    success = migrate_json_to_database(json_path, db_path)
    
    if success:
        # Validate migration
        validate_migration(db_path)
        print("\n🎉 Migration completed successfully!")
        print(f"You can now use the database at: {db_path}")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()