#!/usr/bin/env python3
"""
One-time backfill script to populate phrase-level translations for existing stories.

This script extracts sentence pairs from story Translated sections and uses a single
LLM call per day to break them down into phrase-level translation mappings for 
better SRS translation coverage.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from story_collocation_extractor import StoryCollocationExtractor
from enhanced_srs_database import EnhancedSRSDatabase
from srs_database import SRSDatabase
from llm_mock import MockLLM


class PhraseTranslationExtractor:
    """Extracts phrase-level translations from sentence pairs using LLM."""
    
    def __init__(self):
        """Initialize the phrase translation extractor."""
        self.story_extractor = StoryCollocationExtractor()
        self.enhanced_db = EnhancedSRSDatabase()
        self.srs_db = SRSDatabase()
        self.llm = MockLLM()
    
    def extract_day_phrase_translations(self, day: int, verbose: bool = True, story_content: Optional[str] = None) -> Dict[str, Any]:
        """Extract phrase translations for a specific day using single LLM call with raw Translated section.
        
        Args:
            day: Day number to process
            verbose: Whether to print progress information
            story_content: Optional pre-loaded story content to use instead of reading from file
            
        Returns:
            Dictionary with extraction results and statistics
        """
        if verbose:
            print(f"\n🔍 Processing Day {day} phrase translations...")
        
        # Get story content either from parameter or file
        if story_content is None:
            # Find and read the complete story file
            story_file = self.story_extractor._find_story_file(day)
            if not story_file:
                if verbose:
                    print(f"❌ No story file found for Day {day}")
                return {
                    'day': day,
                    'translated_section_length': 0,
                    'phrase_translations_added': 0,
                    'error': 'No story file found'
                }
            
            # Read the complete story content
            try:
                with open(story_file, 'r', encoding='utf-8') as f:
                    story_content = f.read()
            except Exception as e:
                if verbose:
                    print(f"❌ Error reading story file: {e}")
                return {
                    'day': day,
                    'translated_section_length': 0,
                    'phrase_translations_added': 0,
                    'error': f'Error reading story file: {e}'
                }
        elif verbose:
            print(f"📖 Using provided story content ({len(story_content)} characters)")
        
        # Extract the complete raw Translated section
        translated_section = self._extract_translated_section(story_content)
        
        if not translated_section.strip():
            if verbose:
                print(f"❌ No Translated section found in Day {day} story")
            return {
                'day': day,
                'translated_section_length': 0,
                'phrase_translations_added': 0,
                'error': 'No Translated section found'
            }
        
        if verbose:
            print(f"📖 Found Translated section ({len(translated_section)} characters)")
        
        # Call LLM with the complete raw Translated section
        phrase_translations = self._call_llm_for_phrase_translations(
            day, translated_section, verbose
        )
        
        # Store results in enhanced database
        added_count = self._store_phrase_translations(day, phrase_translations, verbose)
        
        return {
            'day': day,
            'translated_section_length': len(translated_section),
            'phrase_translations_returned': len(phrase_translations),
            'phrase_translations_added': added_count,
            'success': True
        }
    
    def _extract_translated_section(self, story_content: str) -> str:
        """Extract the complete raw Translated section from story content.
        
        Args:
            story_content: Complete story file content
            
        Returns:
            Raw Translated section text with all TAGALOG-* and NARRATOR lines
        """
        # Find the start of the Translated section
        translated_start = story_content.find('[NARRATOR]: Translated')
        if translated_start == -1:
            return ""
        
        # Extract everything from the Translated section to the end of file
        # (or until another major section if present)
        translated_section = story_content[translated_start:]
        
        # Clean up but preserve the dialogue structure
        return translated_section.strip()
    
    def _call_llm_for_phrase_translations(self, day: int, translated_section: str, 
                                        verbose: bool) -> List[Dict[str, Any]]:
        """Call LLM once to extract both phrase AND collocation translations from raw Translated section.
        
        Args:
            day: Day number for context
            translated_section: Complete raw Translated section with TAGALOG-* and NARRATOR lines
            verbose: Whether to print progress
            
        Returns:
            List of phrase translation dictionaries (includes both phrases and collocations)
        """
        if verbose:
            print(f"🤖 Calling LLM for Day {day} comprehensive translation extraction...")
        
        # Build enhanced prompt that extracts multiple granularities
        prompt = self._build_comprehensive_translation_prompt(day, translated_section)
        
        try:
            # Call LLM with single request
            llm_response = self.llm.get_response(prompt, response_type="comprehensive_translations")
            
            # Handle different MockLLM response formats
            phrase_translations = self._extract_phrase_translations_from_response(llm_response, verbose)
            
            if phrase_translations:
                if verbose:
                    print(f"✅ LLM returned {len(phrase_translations)} comprehensive translations")
                return phrase_translations
            else:
                if verbose:
                    print("⚠️ No valid translations found in LLM response")
                return []
                
        except Exception as e:
            if verbose:
                print(f"❌ LLM call failed: {e}")
            return []
    
    def _build_phrase_translation_prompt(self, day: int, translated_section: str) -> str:
        """Build simplified prompt using complete raw Translated section.
        
        Args:
            day: Day number for context
            translated_section: Complete raw Translated section with all dialogue
            
        Returns:
            Formatted prompt string for LLM
        """
        prompt = f"""# Day {day} - Filipino Phrase Translation Extraction

You are helping create phrase-level translations for a Filipino language learning system. Below is the complete Translated section from a Filipino story, which contains Filipino dialogue followed by English translations.

## Complete Translated Section:

{translated_section}

## Task:
Extract meaningful Filipino-to-English phrase translation pairs from the dialogue above. Focus on:
- Useful phrases and expressions that language learners would benefit from knowing
- Common greetings, polite forms, and everyday expressions  
- Complete phrases that have clear English equivalents
- Both short phrases and longer expressions

Return a JSON response with this structure:
{{
  "phrase_translations": [
    {{"filipino": "magandang umaga po", "english": "good morning (polite)", "confidence": 0.95}},
    {{"filipino": "salamat sa lahat", "english": "thank you for everything", "confidence": 0.90}},
    {{"filipino": "paalam po", "english": "goodbye (polite)", "confidence": 0.95}}
  ]
}}

## Guidelines:
- Only include translations with confidence >= 0.8
- Extract both simple phrases and complex expressions
- Include politeness markers in English (e.g., "po" → "(polite)")
- Look for patterns across multiple dialogue exchanges
- Prefer complete, meaningful phrases over fragments
- Extract phrases at multiple granularity levels (2-6 words typically)
- Focus on phrases that would be useful for language learning
"""
        
        return prompt
    
    def _build_comprehensive_translation_prompt(self, day: int, translated_section: str) -> str:
        """Build comprehensive prompt that extracts both phrases and collocations.
        
        Args:
            day: Day number for context
            translated_section: Complete raw Translated section with all dialogue
            
        Returns:
            Formatted prompt string for LLM that extracts multiple granularities
        """
        prompt = f"""# Day {day} - Comprehensive Filipino Translation Extraction

You are helping create comprehensive translations for a Filipino language learning system. Below is the complete Translated section from a Filipino story, which contains Filipino dialogue followed by English translations.

## Complete Translated Section:

{translated_section}

## Task:
Extract comprehensive Filipino-to-English translation pairs from the dialogue above at MULTIPLE GRANULARITIES:

### 1. Complete Phrases (High Priority)
- Useful phrases and expressions for language learning
- Common greetings, polite forms, and everyday expressions  
- Complete meaningful phrases that have clear English equivalents

### 2. Common Collocations (Medium Priority)  
- 2-3 word combinations that appear frequently
- Useful word patterns and constructions
- Partial phrases that teach grammar patterns

### 3. Individual Words (Lower Priority)
- Important vocabulary words
- Single words that provide learning value
- Common particles and function words

Return a JSON response with this structure:
{{
  "phrase_translations": [
    {{"filipino": "magandang umaga po", "english": "good morning (polite)", "confidence": 0.95}},
    {{"filipino": "salamat sa lahat", "english": "thank you for everything", "confidence": 0.90}},
    {{"filipino": "alas dos", "english": "two o'clock", "confidence": 0.95}},
    {{"filipino": "sukli mo", "english": "your change", "confidence": 0.85}},
    {{"filipino": "tubig", "english": "water", "confidence": 0.90}},
    {{"filipino": "po", "english": "(polite marker)", "confidence": 0.80}}
  ]
}}

## Guidelines:
- Extract 50-150 translations total (comprehensive coverage)
- Include translations at all granularities: complete phrases, collocations, single words
- Only include translations with confidence >= 0.75
- Include politeness markers in English (e.g., "po" → "(polite)")
- Prioritize frequent/useful items that would benefit language learners
- Provide contextual translations even for fragments ("sukli mo" → "your change")
- Focus on items that provide learning value at any granularity level"""
        
        return prompt
    
    def _extract_phrase_translations_from_response(self, llm_response: Dict[str, Any], 
                                                  verbose: bool) -> List[Dict[str, Any]]:
        """Extract phrase translations from various MockLLM response formats.
        
        Args:
            llm_response: Response from MockLLM in various possible formats
            verbose: Whether to print debug information
            
        Returns:
            List of phrase translation dictionaries
        """
        import json
        
        # Try direct access first (if response is already the right format)
        if 'phrase_translations' in llm_response:
            return llm_response['phrase_translations']
        
        # Try MockLLM choice format
        if 'choices' in llm_response and llm_response['choices']:
            choice_content = llm_response['choices'][0].get('message', {}).get('content', '')
            if choice_content:
                try:
                    # Try to parse the content as JSON
                    content_json = json.loads(choice_content)
                    if 'phrase_translations' in content_json:
                        return content_json['phrase_translations']
                except json.JSONDecodeError:
                    if verbose:
                        print(f"⚠️ Could not parse choice content as JSON: {choice_content[:100]}...")
        
        # Try to find JSON in the response content string (fallback)
        response_str = str(llm_response)
        if 'phrase_translations' in response_str:
            # Look for JSON blocks in the string
            import re
            json_blocks = re.findall(r'\{[^}]*"phrase_translations"[^}]*\}', response_str, re.DOTALL)
            for block in json_blocks:
                try:
                    content_json = json.loads(block)
                    if 'phrase_translations' in content_json:
                        return content_json['phrase_translations']
                except json.JSONDecodeError:
                    continue
        
        if verbose:
            print(f"🔍 Debug - LLM response format: {type(llm_response)}")
            print(f"🔍 Debug - Response keys: {list(llm_response.keys()) if isinstance(llm_response, dict) else 'Not a dict'}")
            if isinstance(llm_response, dict) and 'choices' in llm_response:
                print(f"🔍 Debug - Choice content preview: {str(llm_response['choices'][0])[:200]}...")
        
        return []
    
    def _store_phrase_translations(self, day: int, phrase_translations: List[Dict[str, Any]], 
                                 verbose: bool) -> int:
        """Store comprehensive translations in enhanced database with frequency filtering.
        
        Args:
            day: Day number for source tracking
            phrase_translations: List of translation dictionaries from LLM
            verbose: Whether to print progress
            
        Returns:
            Number of translations actually added to database
        """
        added_count = 0
        
        # Apply frequency filtering to extracted translations
        # Only keep items that would pass our frequency threshold
        frequency_filtered = self._apply_frequency_filtering(phrase_translations, verbose)
        
        for phrase_data in frequency_filtered:
            try:
                # Validate required fields
                if not all(key in phrase_data for key in ['filipino', 'english', 'confidence']):
                    if verbose:
                        print(f"⚠️ Skipping invalid phrase data: {phrase_data}")
                    continue
                
                filipino = phrase_data['filipino'].strip()
                english = phrase_data['english'].strip()
                confidence = float(phrase_data['confidence'])
                
                # Skip if confidence too low (lowered to 0.75 for comprehensive approach)
                if confidence < 0.75:
                    continue
                
                # Add to enhanced database
                was_added = self.enhanced_db.add_translation_pair(
                    english_text=english,
                    filipino_text=filipino,
                    confidence=confidence,
                    source_day=day,
                    extraction_method='llm_comprehensive_extraction'
                )
                
                if was_added:
                    added_count += 1
                    if verbose and added_count <= 8:  # Show first few additions
                        print(f"  ✅ \"{filipino}\" → \"{english}\" (conf: {confidence:.2f})")
                
            except Exception as e:
                if verbose:
                    print(f"⚠️ Error storing translation: {phrase_data} - {e}")
                continue
        
        if verbose and added_count > 8:
            print(f"  ... and {added_count - 8} more comprehensive translations added")
        
        return added_count
    
    def _apply_frequency_filtering(self, translations: List[Dict[str, Any]], verbose: bool) -> List[Dict[str, Any]]:
        """Apply frequency-based filtering to extracted translations.
        
        This ensures that we only add translations for collocations that would pass
        our frequency threshold, maintaining consistency with the SRS filtering.
        
        Args:
            translations: List of translation dictionaries
            verbose: Whether to print filtering info
            
        Returns:
            Filtered list of translations
        """
        # Get current SRS collocations (frequency-filtered set)
        current_srs = self.srs_db.get_all_collocations()
        valid_collocations = {colloc['text'] for colloc in current_srs}
        
        # Filter translations to only include items that exist in our frequency-filtered SRS
        filtered = [
            translation for translation in translations
            if translation.get('filipino', '').strip() in valid_collocations
        ]
        
        if verbose and len(filtered) != len(translations):
            filtered_out = len(translations) - len(filtered)
            print(f"  🔧 Frequency filtering: kept {len(filtered)}, filtered out {filtered_out} low-frequency items")
        
        return filtered
    
    def clear_day_cache(self, day: int, verbose: bool = True) -> bool:
        """Clear MockLLM cache for a specific day's phrase translation prompt.
        
        Args:
            day: Day number to clear cache for
            verbose: Whether to print progress information
            
        Returns:
            True if cache was cleared or didn't exist, False if error occurred
        """
        try:
            # Get story content to generate the same prompt that would be cached
            story_file = self.story_extractor._find_story_file(day)
            if not story_file:
                if verbose:
                    print(f"ℹ️ No story file found for Day {day}, no cache to clear")
                return True
            
            # Read the story content
            with open(story_file, 'r', encoding='utf-8') as f:
                story_content = f.read()
            
            # Extract the translated section
            translated_section = self._extract_translated_section(story_content)
            if not translated_section.strip():
                if verbose:
                    print(f"ℹ️ No Translated section found for Day {day}, no cache to clear")
                return True
            
            # Generate the same prompt that would be sent to LLM
            prompt = self._build_phrase_translation_prompt(day, translated_section)
            
            # Calculate cache file path using same logic as MockLLM
            import hashlib
            prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
            cache_file = self.llm.cache_dir / f"{prompt_hash}.json"
            
            # Remove cache file if it exists
            if cache_file.exists():
                cache_file.unlink()
                if verbose:
                    print(f"✅ Cleared cache for Day {day} ({cache_file.name})")
                return True
            else:
                if verbose:
                    print(f"ℹ️ No cache found for Day {day}")
                return True
                
        except Exception as e:
            if verbose:
                print(f"❌ Error clearing cache for Day {day}: {e}")
            return False


def main():
    """Main function for the phrase translation backfill script."""
    parser = argparse.ArgumentParser(
        description="Populate phrase-level translations for existing stories"
    )
    parser.add_argument(
        '--day', 
        type=int, 
        required=True,
        help='Day number to process (e.g., --day 19)'
    )
    parser.add_argument(
        '--quiet', 
        action='store_true',
        help='Suppress verbose output'
    )
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear the MockLLM cache for this day before processing'
    )
    
    args = parser.parse_args()
    
    print(f"🚀 Filipino Phrase Translation Backfill - Day {args.day}")
    
    # Check current enhanced database stats
    enhanced_db = EnhancedSRSDatabase()
    current_stats = enhanced_db.get_stats()
    print(f"📊 Current translation pairs in database: {current_stats['active_translation_pairs']}")
    
    # Initialize extractor and process the day
    extractor = PhraseTranslationExtractor()
    
    # Clear cache if requested
    if args.clear_cache:
        print(f"🗑️ Clearing cache for Day {args.day}...")
        cache_cleared = extractor.clear_day_cache(args.day, verbose=not args.quiet)
        if not cache_cleared:
            print(f"❌ Failed to clear cache for Day {args.day}")
            return 1
    
    try:
        result = extractor.extract_day_phrase_translations(args.day, verbose=not args.quiet)
        
        if result.get('success'):
            print(f"\n✅ Day {args.day} Processing Complete!")
            print(f"   Translated section processed: {result['translated_section_length']} characters")
            print(f"   Phrase translations returned by LLM: {result.get('phrase_translations_returned', 0)}")
            print(f"   Phrase translations added: {result['phrase_translations_added']}")
            
            # Show updated database stats
            updated_stats = enhanced_db.get_stats()
            new_pairs = updated_stats['active_translation_pairs'] - current_stats['active_translation_pairs']
            print(f"   Database now has: {updated_stats['active_translation_pairs']} translation pairs (+{new_pairs})")
            
            # Test a few lookups to verify
            print(f"\n🧪 Testing Day {args.day} translation lookups:")
            if args.day == 19:
                test_phrases = ['umalis na po ako', 'babalik po ako', 'paborito ko na']
            else:
                test_phrases = ['salamat po', 'magandang umaga', 'gusto ko po']
            
            for phrase in test_phrases:
                translation = enhanced_db.find_english_equivalent(phrase)
                status = "✅" if translation else "❌"
                print(f"   {status} \"{phrase}\" → \"{translation}\"")
            
            return 0
        else:
            print(f"\n❌ Failed to process Day {args.day}: {result.get('error', 'Unknown error')}")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Processing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())