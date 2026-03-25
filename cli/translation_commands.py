"""
Translation command handlers for TunaTale CLI.

Handles translation extraction, display, lookup, and statistics.
"""
import argparse
import sys
from pathlib import Path


def handle_translate(args: argparse.Namespace) -> int:
    """Handle the translate command and route to subcommands.

    Args:
        args: Command line arguments

    Returns:
        int: 0 on success, 1 on error
    """
    if args.translate_type == 'extract':
        return handle_extract_translations(args)
    elif args.translate_type == 'show':
        return handle_show_translations(args)
    elif args.translate_type == 'lookup':
        return handle_lookup_translation(args)
    elif args.translate_type == 'stats':
        return handle_translation_stats(args)
    else:
        print("Error: Please specify translation operation (extract, show, lookup, or stats)", file=sys.stderr)
        return 1


def handle_extract_translations(args: argparse.Namespace) -> int:
    """Handle the extract-translations command."""
    try:
        from llm_based_extraction_processor import LLMBasedExtractionProcessor

        stories_dir = Path(args.stories_dir)
        if not stories_dir.exists():
            print(f"Error: Stories directory not found: {stories_dir}", file=sys.stderr)
            return 1

        print(f"Extracting translation pairs from stories in: {stories_dir}")
        processor = LLMBasedExtractionProcessor()

        # Process all stories
        reports = processor.process_all_stories(stories_dir)

        if args.output_report:
            # Save detailed report
            output_file = processor.save_reports(reports)
            print(f"Detailed report saved to: {output_file}")

        # Print summary
        summary = processor.generate_summary_report(reports)
        print(f"\n{'='*60}")
        print(f"EXTRACTION SUMMARY".center(60))
        print(f"{'='*60}")
        print(f"Stories processed: {summary['extraction_summary']['total_stories_processed']}")
        print(f"Translation pairs: {summary['extraction_summary']['total_translation_pairs']}")
        print(f"High confidence pairs: {summary['extraction_summary']['high_confidence_pairs']}")
        print(f"Database entries: {summary['database_statistics']['total_collocations']}")

        return 0

    except Exception as e:
        print(f"Error extracting translations: {e}", file=sys.stderr)
        return 1


def handle_show_translations(args: argparse.Namespace) -> int:
    """Handle the show-translations command."""
    try:
        from enhanced_srs_database import EnhancedSRSDatabase

        db = EnhancedSRSDatabase()
        pairs = db.get_translation_pairs()

        # Filter by confidence
        filtered_pairs = [p for p in pairs if p.confidence >= args.min_confidence]

        # Limit results
        display_pairs = filtered_pairs[:args.limit]

        print(f"\n{'='*60}")
        print(f"TRANSLATION PAIRS (min confidence: {args.min_confidence})".center(60))
        print(f"{'='*60}")
        print(f"Showing {len(display_pairs)} of {len(filtered_pairs)} pairs")

        for i, pair in enumerate(display_pairs, 1):
            print(f"{i:2d}. {pair.english} ↔ {pair.filipino} (confidence: {pair.confidence})")

        if len(filtered_pairs) > args.limit:
            print(f"\n... and {len(filtered_pairs) - args.limit} more pairs")

        return 0

    except Exception as e:
        print(f"Error showing translations: {e}", file=sys.stderr)
        return 1


def handle_lookup_translation(args: argparse.Namespace) -> int:
    """Handle the lookup-translation command."""
    try:
        from enhanced_srs_database import EnhancedSRSDatabase

        db = EnhancedSRSDatabase()
        word = args.word.strip()

        print(f"\n{'='*50}")
        print(f"TRANSLATION LOOKUP: '{word}'".center(50))
        print(f"{'='*50}")

        if args.reverse:
            # Force Filipino → English
            english = db.find_english_equivalent(word)
            if english:
                print(f"Filipino → English: {word} → {english}")
            else:
                print(f"No English equivalent found for: {word}")
        else:
            # Try both directions
            filipino = db.find_filipino_equivalent(word)
            english = db.find_english_equivalent(word)

            if filipino:
                print(f"English → Filipino: {word} → {filipino}")
            if english:
                print(f"Filipino → English: {word} → {english}")

            if not filipino and not english:
                print(f"No translation found for: {word}")

        return 0

    except Exception as e:
        print(f"Error in translation lookup: {e}", file=sys.stderr)
        return 1


def handle_translation_stats(args: argparse.Namespace) -> int:
    """Handle the translation-stats command."""
    try:
        from enhanced_srs_database import EnhancedSRSDatabase

        db = EnhancedSRSDatabase()
        stats = db.get_stats()

        print(f"\n{'='*60}")
        print(f"ENHANCED DATABASE STATISTICS".center(60))
        print(f"{'='*60}")

        print(f"Database location: {stats['database_path']}")
        print(f"Total enhanced collocations: {stats['total_collocations']:,}")

        if 'enhanced_collocations' in stats:
            print(f"\nCollocations by language:")
            for language, count in stats['enhanced_collocations'].items():
                print(f"  {language.capitalize()}: {count:,}")

        print(f"\nTranslation pairs: {stats['active_translation_pairs']:,}")
        print(f"Average confidence: {stats['average_translation_confidence']:.3f}")
        print(f"Bidirectional mappings: {stats['mapped_collocations']:,}")

        # Show critical mappings
        critical_words = ['water', 'delicious', 'perfect', 'beautiful', 'fresh', 'thank you']
        print(f"\nCritical mapping status:")
        for word in critical_words:
            filipino = db.find_filipino_equivalent(word)
            status = "✓" if filipino else "✗"
            result = filipino if filipino else "Not found"
            print(f"  {status} {word} → {result}")

        return 0

    except Exception as e:
        print(f"Error getting translation stats: {e}", file=sys.stderr)
        return 1
