#!/usr/bin/env python3
"""
Non-interactive version of the production data cleanup.
Executes the cleanup without user prompts.
"""

from cleanup_production_data import ProductionDataCleaner

def main():
    print("🚀 EXECUTING PRODUCTION DATA CLEANUP")
    print("=" * 60)
    
    # Run cleanup without interactive prompts
    cleaner = ProductionDataCleaner(dry_run=False)
    results = cleaner.cleanup_all_production_data()
    cleaner.print_summary(results)
    
    print("\n✅ PRODUCTION DATA CLEANUP COMPLETED")

if __name__ == "__main__":
    main()