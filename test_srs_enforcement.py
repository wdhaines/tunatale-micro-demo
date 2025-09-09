#!/usr/bin/env python3
"""Test script to verify SRS enforcement functionality."""

import logging
import sys
from pathlib import Path

# Set up logging to see what happens
logging.basicConfig(level=logging.INFO)

# Add the current directory to Python path
sys.path.insert(0, str(Path.cwd()))

from srs_database import SRSDatabase
from srs_llm_enforcer import create_llm_enforcer
from llm_mock import MockLLM

def test_srs_enforcement():
    """Test SRS enforcement on existing story content."""
    
    # Read an existing story file
    story_file = Path("instance/data/stories/story_day15_day_15_sunset_viewing_and_phot.txt")
    if not story_file.exists():
        print(f"Story file not found: {story_file}")
        return
    
    print(f"Reading story from: {story_file}")
    with open(story_file, 'r', encoding='utf-8') as f:
        story_content = f.read()
    
    print(f"Story content length: {len(story_content)} characters")
    print("First 200 characters:")
    print(story_content[:200])
    print()
    
    # Create SRS components
    srs_db = SRSDatabase()
    
    # Check current violations count
    import sqlite3
    with sqlite3.connect(srs_db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM srs_violations')
        before_count = cursor.fetchone()[0]
    
    print(f"Violations in database before test: {before_count}")
    
    # Create mock LLM that returns the same content (simulating no replacements needed)
    llm = MockLLM()
    
    # Override the chat_response to return a dummy response without requiring interaction
    def mock_chat_response(system_prompt, user_prompt, response_type):
        # Return the original content with minor modifications to simulate enforcement
        modified_content = story_content.replace("water", "tubig").replace("thank you", "salamat po")
        return {
            'choices': [{
                'message': {
                    'content': modified_content
                }
            }]
        }
    
    # Monkey patch the method for testing
    llm.chat_response = mock_chat_response
    
    enforcer = create_llm_enforcer(llm, srs_db)
    
    print("Testing SRS enforcement...")
    try:
        enforced_story, violations = enforcer.enforce_with_llm(
            content=story_content,
            day=15,
            context="test_enforcement"
        )
        
        print(f"Enforcement completed successfully!")
        print(f"Violations found: {len(violations)}")
        for violation in violations:
            print(f"  - '{violation['english']}' -> '{violation['filipino']}' ({violation['count']}x)")
        
        # Check violations count after
        with sqlite3.connect(srs_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM srs_violations')
            after_count = cursor.fetchone()[0]
        
        print(f"Violations in database after test: {after_count}")
        print(f"New violations recorded: {after_count - before_count}")
        
        if after_count > before_count:
            print("✅ SRS enforcement is working and recording violations!")
        else:
            print("❌ SRS enforcement ran but no violations were recorded")
            
    except Exception as e:
        print(f"❌ SRS enforcement failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_srs_enforcement()