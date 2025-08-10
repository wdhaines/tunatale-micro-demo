#!/usr/bin/env python3
"""Test script for strategy-based content generation."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from story_generator import ContentGenerator
from content_strategy import ContentStrategy
import logging

# Configure logging to see the strategy output
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_strategy_generation():
    """Test strategy-based content generation."""
    print("🧪 Testing Strategy-Based Content Generation")
    print("=" * 50)
    
    generator = ContentGenerator()
    
    # Test DEEPER strategy
    print("\n📈 Testing DEEPER Strategy (Day 10 based on Day 2)")
    print("-" * 40)
    
    try:
        result = generator.generate_strategy_based_story(
            target_day=10, 
            strategy=ContentStrategy.DEEPER, 
            source_day=2
        )
        
        if result:
            story, collocation_report = result
            print("✅ DEEPER strategy generation successful!")
            print(f"📊 Collocation Report:")
            print(f"   - New: {len(collocation_report['new'])} items")
            print(f"   - Reviewed: {len(collocation_report['reviewed'])} items")
            print(f"   - Enhanced collocations: {collocation_report['new'][:3]}")
            print(f"📖 Story preview (first 200 chars): {story[:200]}...")
        else:
            print("❌ DEEPER strategy generation failed")
            
    except Exception as e:
        print(f"❌ DEEPER strategy error: {e}")
    
    # Test WIDER strategy  
    print("\n📊 Testing WIDER Strategy (Day 11 based on Day 3)")
    print("-" * 40)
    
    try:
        result = generator.generate_strategy_based_story(
            target_day=11,
            strategy=ContentStrategy.WIDER, 
            source_day=3
        )
        
        if result:
            story, collocation_report = result
            print("✅ WIDER strategy generation successful!")
            print(f"📊 Collocation Report:")
            print(f"   - New: {len(collocation_report['new'])} items") 
            print(f"   - Reviewed: {len(collocation_report['reviewed'])} items")
            print(f"   - Wider collocations: {collocation_report['new'][:3]}")
            print(f"📖 Story preview (first 200 chars): {story[:200]}...")
        else:
            print("❌ WIDER strategy generation failed")
            
    except Exception as e:
        print(f"❌ WIDER strategy error: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Strategy testing complete!")

if __name__ == "__main__":
    test_strategy_generation()