#!/usr/bin/env python3
"""
Test translation storage to debug why translations aren't being saved.
"""

import json
import sys
from translate_srs_batch import SRSBatchTranslator


def test_translation_storage():
    """Test the translation storage with existing test data."""
    print("🧪 Testing translation storage with test_batch_response.json...")
    
    # Load test translation data
    try:
        with open("test_batch_response.json", "r", encoding="utf-8") as f:
            test_data = json.load(f)
    except FileNotFoundError:
        print("❌ test_batch_response.json not found!")
        return 1
    
    if "translations" not in test_data:
        print("❌ No translations found in test data!")
        return 1
    
    print(f"📊 Test data contains {len(test_data['translations'])} translations")
    
    # Initialize the batch translator
    translator = SRSBatchTranslator()
    
    # Test storing just the first few translations for debugging
    test_translations = test_data["translations"][:10]  # First 10 for testing
    print(f"🔬 Testing storage of first {len(test_translations)} translations...")
    
    # Test the storage method directly
    stored_count = translator.store_translations(test_translations, verbose=True)
    
    print(f"\n✅ Test complete! Successfully stored: {stored_count}/{len(test_translations)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(test_translation_storage())