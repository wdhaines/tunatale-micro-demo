#!/usr/bin/env python3
"""
Efficient batch translation script for SRS collocations.

Translates all untranslated SRS items in large batches (300-500 items per LLM call)
to achieve high translation coverage with minimal API calls.
"""

import argparse
import sys
import json
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict

from srs_database import SRSDatabase
from enhanced_srs_database import EnhancedSRSDatabase
from llm_mock import MockLLM


class SRSBatchTranslator:
    """Efficiently translate remaining SRS items in large batches."""
    
    def __init__(self):
        """Initialize the batch translator."""
        self.srs_db = SRSDatabase()
        self.enhanced_db = EnhancedSRSDatabase()
        self.llm = MockLLM()
    
    def get_untranslated_collocations(self, verbose: bool = True) -> List[str]:
        """Get SRS collocations that are frequent (>=3) but don't have translations yet.
        
        Args:
            verbose: Whether to print progress information
            
        Returns:
            List of frequent untranslated collocation texts
        """
        if verbose:
            print("🔍 Finding frequent untranslated SRS collocations...")
        
        # Get untranslated frequent collocations using the new database method
        untranslated = self.srs_db.get_untranslated_frequent_collocations()
        
        if verbose:
            # Get stats for reporting
            all_srs_collocations = self.srs_db.get_all_collocations()
            frequent_collocations = self.srs_db.get_collocations_ready_for_translation()
            total_srs = len(all_srs_collocations)
            total_frequent = len(frequent_collocations)
            total_translated = total_frequent - len(untranslated)
            
            print(f"  Total SRS collocations: {total_srs:,}")
            print(f"  Frequent collocations (≥3): {total_frequent:,}")
            print(f"  Already translated: {total_translated:,}")
            print(f"  Need translation: {len(untranslated):,}")
            
            # Show coverage
            if total_frequent > 0:
                coverage = (total_translated / total_frequent * 100)
                print(f"  Frequent translation coverage: {coverage:.1f}%")
        
        return untranslated
    
    def organize_by_word_count(self, collocations: List[str]) -> Dict[int, List[str]]:
        """Organize collocations by word count for optimal batching.
        
        Args:
            collocations: List of collocation texts
            
        Returns:
            Dictionary mapping word_count -> list of collocations
        """
        by_word_count = defaultdict(list)
        
        for colloc in collocations:
            word_count = len(colloc.split())
            by_word_count[word_count].append(colloc)
        
        return dict(by_word_count)
    
    def create_batches(self, collocations: List[str], batch_size: int = 400) -> List[List[str]]:
        """Create batches of collocations for efficient processing.
        
        Args:
            collocations: List of collocation texts
            batch_size: Target size for each batch
            
        Returns:
            List of batches, each containing a list of collocations
        """
        batches = []
        for i in range(0, len(collocations), batch_size):
            batch = collocations[i:i + batch_size]
            batches.append(batch)
        return batches
    
    def translate_batch(self, batch: List[str], batch_num: int, total_batches: int, 
                       verbose: bool = True) -> List[Dict[str, Any]]:
        """Translate a batch of collocations using LLM.
        
        Args:
            batch: List of collocation texts to translate
            batch_num: Current batch number (for display)
            total_batches: Total number of batches (for display)
            verbose: Whether to print progress information
            
        Returns:
            List of translation dictionaries
        """
        if verbose:
            print(f"🤖 Translating Batch {batch_num}/{total_batches} ({len(batch)} items)...")
        
        # Create batch translation prompt
        prompt = self._create_batch_translation_prompt(batch)
        
        try:
            # Call LLM with batch request
            llm_response = self.llm.get_response(prompt, response_type="batch_translation")
            
            # Parse response
            translations = self._parse_batch_response(llm_response, verbose)
            
            if verbose:
                valid_count = len(translations)
                print(f"  ✅ LLM returned {valid_count} valid translations")
            
            return translations
            
        except Exception as e:
            if verbose:
                print(f"  ❌ Batch translation failed: {e}")
            return []
    
    def _create_batch_translation_prompt(self, batch: List[str]) -> str:
        """Create an efficient batch translation prompt.
        
        Args:
            batch: List of collocation texts to translate
            
        Returns:
            Formatted prompt for LLM
        """
        # Create numbered list
        numbered_items = []
        for i, colloc in enumerate(batch, 1):
            numbered_items.append(f"{i:3d}. {colloc}")
        
        items_text = "\\n".join(numbered_items)
        
        prompt = f"""# Batch Filipino-to-English Translation

Translate these {len(batch)} frequent Filipino words and phrases to English. These items appear 3+ times across the story corpus, making them pedagogically valuable for language learning.

Guidelines:
- Single words: provide direct translation ("tubig" → "water")  
- Phrases with "po": add "(polite)" marker ("salamat po" → "thank you (polite)")
- Fragments: provide contextual meaning ("sukli mo" → "your change")
- Particles: explain function ("na alis" → "(will) leave")
- If unsure, provide best contextual interpretation

Filipino items to translate:
{items_text}

Return JSON response with this exact structure:
{{
  "translations": [
    {{"filipino": "tubig", "english": "water", "confidence": 0.95}},
    {{"filipino": "salamat po", "english": "thank you (polite)", "confidence": 0.90}},
    {{"filipino": "sukli mo", "english": "your change", "confidence": 0.85}}
  ]
}}

Requirements:
- Include ALL {len(batch)} items in your response
- Only include translations with confidence >= 0.7
- Use descriptive English that helps language learning
- Be consistent with politeness markers and contextual cues"""
        
        return prompt
    
    def _parse_batch_response(self, llm_response: Dict, verbose: bool = True) -> List[Dict[str, Any]]:
        """Parse batch translation response from LLM.
        
        Args:
            llm_response: Response from MockLLM
            verbose: Whether to print debug information
            
        Returns:
            List of valid translation dictionaries
        """
        import json
        
        # Try to extract translations using same logic as phrase extraction
        # Try direct access first
        if 'translations' in llm_response:
            return llm_response['translations']
        
        # Try MockLLM choice format
        if 'choices' in llm_response and llm_response['choices']:
            choice_content = llm_response['choices'][0].get('message', {}).get('content', '')
            if choice_content:
                try:
                    content_json = json.loads(choice_content)
                    if 'translations' in content_json:
                        return content_json['translations']
                except json.JSONDecodeError:
                    if verbose:
                        print(f"  ⚠️ Could not parse choice content as JSON")
        
        # Try to find JSON in response string (fallback)
        response_str = str(llm_response)
        if 'translations' in response_str:
            import re
            json_blocks = re.findall(r'\\{[^}]*"translations"[^}]*\\}', response_str, re.DOTALL)
            for block in json_blocks:
                try:
                    content_json = json.loads(block)
                    if 'translations' in content_json:
                        return content_json['translations']
                except json.JSONDecodeError:
                    continue
        
        if verbose:
            print(f"  🔍 Debug - Could not extract translations from LLM response format")
        
        return []
    
    def store_translations(self, translations: List[Dict[str, Any]], verbose: bool = True) -> int:
        """Store batch translations in enhanced database.
        
        Args:
            translations: List of translation dictionaries from LLM
            verbose: Whether to print progress information
            
        Returns:
            Number of translations successfully stored
        """
        stored_count = 0
        debug_stats = {
            'total_received': len(translations),
            'invalid_format': 0,
            'low_confidence': 0,
            'duplicates': 0,
            'storage_errors': 0,
            'successfully_stored': 0
        }
        
        if verbose:
            print(f"    🔍 Debug: Processing {len(translations)} translations")
        
        for i, translation in enumerate(translations):
            try:
                # Validate required fields
                if not all(key in translation for key in ['filipino', 'english', 'confidence']):
                    debug_stats['invalid_format'] += 1
                    if verbose and i < 3:  # Show first 3 validation failures
                        print(f"    ⚠️ Invalid format [{i+1}]: {translation}")
                    continue
                
                filipino = translation['filipino'].strip()
                english = translation['english'].strip()
                confidence = float(translation['confidence'])
                
                # Skip if confidence too low
                if confidence < 0.7:
                    debug_stats['low_confidence'] += 1
                    if verbose and debug_stats['low_confidence'] <= 3:  # Show first 3 low confidence
                        print(f"    ⚠️ Low confidence [{i+1}]: {filipino} ({confidence})")
                    continue
                
                # Add to enhanced database (returns True for new, False for duplicate/updated)
                was_new = self.enhanced_db.add_translation_pair(
                    english_text=english,
                    filipino_text=filipino,
                    confidence=confidence,
                    source_day=0,  # Batch translation, no specific day
                    extraction_method='llm_batch_translation'
                )
                
                # For batch translation, both new additions AND duplicate updates are successful
                stored_count += 1
                
                if was_new:
                    debug_stats['successfully_stored'] += 1
                    if verbose and debug_stats['successfully_stored'] <= 3:  # Show first 3 new translations
                        print(f"    ✅ New [{i+1}]: '{filipino}' → '{english}' ({confidence})")
                else:
                    debug_stats['duplicates'] += 1
                    if verbose and debug_stats['duplicates'] <= 3:  # Show first 3 updates
                        print(f"    🔄 Updated [{i+1}]: '{filipino}' → '{english}' ({confidence})")
                
            except Exception as e:
                debug_stats['storage_errors'] += 1
                if verbose:
                    print(f"    ❌ Storage error [{i+1}]: {translation} - {e}")
                continue
        
        if verbose:
            total_processed = debug_stats['successfully_stored'] + debug_stats['duplicates']
            print(f"    📊 Storage Summary:")
            print(f"       Total received: {debug_stats['total_received']}")
            print(f"       Successfully processed: {total_processed}")
            print(f"         - New translations: {debug_stats['successfully_stored']}")
            print(f"         - Updated existing: {debug_stats['duplicates']}")
            print(f"       Skipped (low confidence): {debug_stats['low_confidence']}")
            print(f"       Skipped (invalid format): {debug_stats['invalid_format']}")
            print(f"       Errors: {debug_stats['storage_errors']}")
        
        return stored_count
    
    def run_batch_translation(self, batch_size: int = 400, max_batches: Optional[int] = None, 
                             verbose: bool = True) -> Dict[str, Any]:
        """Run complete batch translation process.
        
        Args:
            batch_size: Target size for each batch
            max_batches: Optional limit on number of batches to process
            verbose: Whether to print progress information
            
        Returns:
            Dictionary with processing statistics
        """
        if verbose:
            print(f"🚀 SRS Batch Translation Process")
            print(f"📦 Batch size: {batch_size}")
            if max_batches:
                print(f"📊 Max batches: {max_batches}")
        
        # Get current statistics
        initial_stats = self.enhanced_db.get_stats()
        initial_pairs = initial_stats['active_translation_pairs']
        
        # Get untranslated collocations
        untranslated = self.get_untranslated_collocations(verbose)
        
        if not untranslated:
            if verbose:
                print("✅ All SRS collocations already have translations!")
            
            # Get current database statistics for consistent reporting
            current_stats = self.enhanced_db.get_stats()
            current_pairs = current_stats['active_translation_pairs']
            
            return {
                'untranslated_found': 0,
                'batches_processed': 0,
                'translations_added': 0,
                'initial_translation_pairs': current_pairs,
                'final_translation_pairs': current_pairs,
                'success': True
            }
        
        # Organize by word count for better results
        by_word_count = self.organize_by_word_count(untranslated)
        
        if verbose:
            print(f"\\n📊 Collocation breakdown by word count:")
            for word_count in sorted(by_word_count.keys()):
                count = len(by_word_count[word_count])
                print(f"  {word_count} word(s): {count:,} items")
        
        # Create batches
        all_batches = []
        for word_count in sorted(by_word_count.keys()):
            collocations = by_word_count[word_count]
            word_batches = self.create_batches(collocations, batch_size)
            all_batches.extend(word_batches)
        
        # Apply max_batches limit if specified
        if max_batches:
            all_batches = all_batches[:max_batches]
            if verbose:
                total_items = sum(len(batch) for batch in all_batches)
                print(f"🔒 Limited to first {max_batches} batches ({total_items:,} items)")
        
        if verbose:
            total_items = sum(len(batch) for batch in all_batches)
            print(f"\\n🎯 Processing {len(all_batches)} batches ({total_items:,} items)")
        
        # Process each batch
        total_added = 0
        successful_batches = 0
        
        for i, batch in enumerate(all_batches, 1):
            try:
                translations = self.translate_batch(batch, i, len(all_batches), verbose)
                added_count = self.store_translations(translations, verbose)
                
                total_added += added_count
                successful_batches += 1
                
                if verbose:
                    print(f"    📝 Stored {added_count} new translations")
                
            except Exception as e:
                if verbose:
                    print(f"    ❌ Batch {i} failed: {e}")
                continue
        
        # Final statistics
        final_stats = self.enhanced_db.get_stats()
        final_pairs = final_stats['active_translation_pairs']
        net_increase = final_pairs - initial_pairs
        
        return {
            'untranslated_found': len(untranslated),
            'batches_processed': successful_batches,
            'translations_added': net_increase,
            'initial_translation_pairs': initial_pairs,
            'final_translation_pairs': final_pairs,
            'success': successful_batches > 0
        }


def main():
    """Main function for the batch translation script."""
    parser = argparse.ArgumentParser(
        description="Efficiently translate remaining SRS collocations in batches"
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=400,
        help='Number of items per batch (default: 400)'
    )
    parser.add_argument(
        '--max-batches',
        type=int,
        help='Maximum number of batches to process (for testing)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress verbose output'
    )
    
    args = parser.parse_args()
    
    try:
        translator = SRSBatchTranslator()
        
        result = translator.run_batch_translation(
            batch_size=args.batch_size,
            max_batches=args.max_batches,
            verbose=not args.quiet
        )
        
        # Final summary
        if not args.quiet:
            print(f"\\n✅ Batch Translation Complete!")
            print(f"  Untranslated items found: {result['untranslated_found']:,}")
            print(f"  Batches processed: {result['batches_processed']}")
            print(f"  Translation pairs added: {result['translations_added']:,}")
            print(f"  Database: {result['initial_translation_pairs']:,} → {result['final_translation_pairs']:,}")
            
            # Calculate new coverage
            srs_total = len(translator.srs_db.get_all_collocations())
            if srs_total > 0:
                old_coverage = (result['initial_translation_pairs'] / srs_total) * 100
                new_coverage_estimate = ((result['final_translation_pairs']) / srs_total) * 100
                print(f"  Estimated coverage: {old_coverage:.1f}% → {new_coverage_estimate:.1f}%")
        
        return 0 if result['success'] else 1
        
    except KeyboardInterrupt:
        print(f"\\n⏹️ Translation interrupted by user")
        return 1
    except Exception as e:
        print(f"\\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())