"""
Analysis command handlers for TunaTale CLI.

Handles vocabulary analysis, collocation analysis, and debug commands.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def handle_analyze(args: argparse.Namespace) -> int:
    """Handle the analyze command and route to subcommands.

    Args:
        args: Command line arguments

    Returns:
        int: 0 on success, 1 on error
    """
    if args.analyze_type == 'vocab':
        return handle_analyze_vocab(args)
    elif args.analyze_type == 'collocations':
        return handle_show_day_collocations(args)
    elif args.analyze_type == 'debug':
        return handle_debug_generation(args)
    else:
        print("Error: Please specify what to analyze (vocab, collocations, or debug)", file=sys.stderr)
        return 1


def handle_analyze_vocab(args: argparse.Namespace) -> int:
    """Handle the analyze vocab subcommand.

    Args:
        args: Command line arguments

    Returns:
        int: 0 on success, 1 on error
    """
    print("DEBUG: Entering _handle_analyze_vocab")
    from textwrap import fill
    import time
    import glob

    try:
        start_time = time.time()

        # Check if day-based analysis is requested
        if hasattr(args, 'day') and args.day:
            # Day-based analysis - find story file for the specified day
            day_pattern = f"*day{args.day:02d}*.txt"
            story_files = list(Path("instance/data/stories").glob(day_pattern))

            if not story_files:
                # Also try the current directory pattern
                story_files = list(Path(".").glob(day_pattern))

            if not story_files:
                print(f"Error: No file found for day {args.day}", file=sys.stderr)
                return 1

            story_file = story_files[0]  # Use the first match
            with open(story_file, 'r', encoding='utf-8') as f:
                text = f.read()

            print(f"Day {args.day} story analysis from: {story_file}")

        else:
            # Handle file path or direct text
            file_path = Path(args.file_or_text) if args.file_or_text else None
            if file_path and file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                if not text.strip():
                    print("Warning: File is empty, showing empty analysis", file=sys.stderr)
                    text = ""  # Allow empty text to proceed to analysis
            else:
                # Check if input looks like a file path but doesn't exist
                input_text = args.file_or_text or ""
                looks_like_file_path = (
                    '/' in input_text or
                    '\\' in input_text or
                    input_text.endswith(('.txt', '.md', '.py', '.js', '.json', '.csv', '.log'))
                )

                if looks_like_file_path and input_text:
                    print(f"Warning: File '{input_text}' not found, analyzing as empty text", file=sys.stderr)
                    text = ""  # Analyze empty text when file path doesn't exist
                    # Don't return error for nonexistent file paths - allow empty analysis
                else:
                    # Treat as direct text input
                    text = input_text
                    if not text.strip():
                        print("Error: No text to analyze", file=sys.stderr)
                        return 1

        print(f"\n{'='*60}")
        print(f"VOCABULARY ANALYSIS".center(60))
        print(f"{'='*60}")
        file_info = f"{min(50, len(text))} chars of provided text"
        print(f"File/Text: {file_info}")
        print(f"Minimum word length: {args.min_word_len}")
        print(f"Top words to show: {args.top_words}")
        print(f"Top collocations to show: {args.top_collocations}")
        print(f"Verbose output: {'Yes' if args.verbose else 'No'}")

        print("\nLoading vocabulary analyzer...")
        from story_collocation_extractor import StoryCollocationExtractor
        extractor = StoryCollocationExtractor()

        # Check if Phase 3 analysis is requested
        quality_requested = hasattr(args, 'quality') and args.quality
        trip_requested = hasattr(args, 'trip_readiness') and args.trip_readiness

        if quality_requested or trip_requested:
            phase3_results = []

            if quality_requested:
                print("Running CONTENT QUALITY ANALYSIS...")
                from content_quality_analyzer import ContentQualityAnalyzer

                analyzer = ContentQualityAnalyzer()
                quality_metrics = analyzer.analyze_content_quality(text)
                phase3_results.append(('CONTENT QUALITY ANALYSIS', quality_metrics))

            if trip_requested:
                print("Running EL NIDO TRIP READINESS ANALYSIS...")
                from el_nido_trip_validator import ElNidoTripValidator

                validator = ElNidoTripValidator()
                trip_metrics = validator.calculate_trip_readiness([text])
                phase3_results.append(('EL NIDO TRIP READINESS ANALYSIS', trip_metrics))

            # Print all Phase 3 analysis results
            for title, metrics in phase3_results:
                print("\n" + "="*60)
                print(title.center(60))
                print("="*60)

                if 'QUALITY' in title:
                    print(f"Filipino authenticity: {metrics.filipino_ratio:.2f}")
                    print(f"Po usage score: {metrics.po_usage_score:.2f}")
                    print(f"Cultural expressions: {metrics.cultural_expression_count}")
                    print(f"Overall quality score: {metrics.overall_quality_score:.2f}")
                else:  # Trip readiness
                    print(f"Overall trip readiness: {metrics.overall_readiness_score:.2f}")
                    print("\nScenario coverage:")
                    print(f"  Accommodation: {metrics.accommodation_coverage:.2f}")
                    print(f"  Transportation: {metrics.transportation_coverage:.2f}")
                    print(f"  Restaurant: {metrics.restaurant_coverage:.2f}")
                    print(f"  Activities: {metrics.activity_coverage:.2f}")
                    print(f"  Emergency: {metrics.emergency_coverage:.2f}")

            # Phase 3 analysis complete, continue to vocabulary analysis

        # Run LLM-based translation extraction if requested
        if hasattr(args, 'extract_translations') and args.extract_translations:
            print("Running LLM-based translation pair extraction...")
            try:
                from llm_based_extraction_processor import LLMBasedExtractionProcessor
                extraction_processor = LLMBasedExtractionProcessor()

                # Create temporary file for extraction
                temp_path = Path("temp_analysis.txt")
                temp_path.write_text(text, encoding='utf-8')

                # Extract translation pairs
                day_number = args.day if hasattr(args, 'day') and args.day else 0
                report = extraction_processor.process_story_file(temp_path, day_number)

                # Clean up temp file
                if temp_path.exists():
                    temp_path.unlink()

                print(f"\n{'='*60}")
                print(f"TRANSLATION ANALYSIS RESULTS".center(60))
                print(f"{'='*60}")
                print(f"Translation pairs found: {report.translation_pairs_found}")
                print(f"High confidence pairs: {report.high_confidence_pairs}")
                print(f"Medium confidence pairs: {report.medium_confidence_pairs}")
                print(f"English terms found: {report.english_terms_found}")
                print(f"Key phrases found: {report.key_phrases_found}")
                print(f"SRS analysis found: {'Yes' if report.srs_analysis_found else 'No'}")

                # Show translation pairs if found
                if report.translation_pairs_found > 0:
                    from enhanced_srs_database import EnhancedSRSDatabase
                    db = EnhancedSRSDatabase()
                    pairs = db.get_translation_pairs()
                    recent_pairs = [p for p in pairs if p.confidence >= 0.8][:10]

                    print(f"\nHigh-Quality Translation Pairs:")
                    for pair in recent_pairs:
                        print(f"  {pair.english} ↔ {pair.filipino} (confidence: {pair.confidence})")

            except Exception as e:
                print(f"Translation extraction failed: {e}")

        print("Analyzing text...")
        try:
            analysis = extractor.analyze_vocabulary_distribution(text)

            # Calculate analysis time
            analysis_time = time.time() - start_time

            # Print summary with consistent column alignment
        except Exception as e:
            print(f"Error during analysis: {e}", file=sys.stderr)
            if 'pytest' not in sys.modules:  # Don't print traceback during tests
                import traceback
                traceback.print_exc()
            return 1

        # Define column widths and print function after successful analysis
        col1_width = 30
        col2_width = 20

        def print_stat(label, value, percentage=None):
            value_str = f"{value:,}" if isinstance(value, int) else f"{value:.1f}"
            if percentage is not None:
                value_str += f" ({percentage:.1f}%)"
            print(f"{label:<{col1_width}}{value_str:>{col2_width}}")

        print("\n" + "="*60)
        print("VOCABULARY ANALYSIS SUMMARY".center(60))
        print("="*60)

        # Basic stats
        print("\n" + "WORD STATISTICS".center(60))
        print("-"*60)
        print_stat("Total words:", analysis['total_words'])
        print_stat("Unique words:", analysis['unique_words_count'])
        print_stat("A2 background words:",
                  analysis['background_words'],
                  analysis['background_percentage'])
        print_stat("New content words:", analysis['new_content_words'])
        print_stat("Avg. word length (chars):", analysis['avg_word_length'])

        # Top new words
        if analysis.get('top_new_words'):
            print("\n" + "MOST FREQUENT NEW WORDS".center(60))
            print("-"*60)
            words_per_line = 5
            top_words = analysis['top_new_words'][:args.top_words]
            for i in range(0, len(top_words), words_per_line):
                line_words = top_words[i:i+words_per_line]
                print("  " + "  ".join(f"• {w:<12}" for w in line_words))

        # Collocations
        if analysis['collocations']:
            print("\n" + "TOP COLLOCATIONS".center(60))
            print("-"*60)
            max_collocs = min(args.top_collocations, len(analysis['collocations']))
            colloc_items = list(analysis['collocations'].items())[:max_collocs]

            # Find the maximum width for alignment
            max_colloc_len = max(len(c[0]) for c in colloc_items) if colloc_items else 0
            max_count_len = max(len(str(c[1])) for c in colloc_items) if colloc_items else 0

            for i, (colloc, count) in enumerate(colloc_items, 1):
                print(f"{i:2}. {colloc:<{max_colloc_len + 2}} (x{count:>{max_count_len}})")

        # Full unique words list (if requested)
        if args.verbose and analysis['unique_new_words']:
            print("\n" + "="*60)
            print(f"ALL UNIQUE NEW WORDS ({len(analysis['unique_new_words'])} total)".center(60))
            print("="*60)
            words_per_line = 6
            sorted_words = sorted(analysis['unique_new_words'])
            for i in range(0, len(sorted_words), words_per_line):
                line_words = sorted_words[i:i+words_per_line]
                print("  " + "  ".join(f"{w:<12}" for w in line_words))

        # Print analysis time
        print(f"\n{'='*60}")
        print(f"Analysis completed in {analysis_time:.2f} seconds")
        print("="*60)

        return 0

    except Exception as e:
        print(f"\nError during analysis: {e}", file=sys.stderr)
        if 'pytest' not in sys.modules:  # Don't print traceback during tests
            import traceback
            traceback.print_exc()
        return 1


def handle_show_day_collocations(args: argparse.Namespace) -> int:
    """Handle the show-day-collocations command."""
    try:
        from story_collocation_extractor import StoryCollocationExtractor

        day = args.day

        # Validate day parameter
        if day < 1:
            print(f"Error: Day must be >= 1, got {day}", file=sys.stderr)
            return 1

        print(f"Extracting collocations from day {day} story...")

        extractor = StoryCollocationExtractor()
        extraction = extractor.extract_from_day_number(day)

        if not extraction:
            print(f"No story found for day {day}", file=sys.stderr)
            return 1

        # Display results based on format
        if args.format == 'json':
            print(json.dumps(extraction.to_dict(), indent=2, ensure_ascii=False))
        elif args.format == 'simple':
            print(f"Day {extraction.day}: {extraction.total_unique_phrases} unique phrases")
            for phrase in extraction.key_phrases:
                print(f"  • {phrase}")
        else:  # detailed format
            print(f"\n=== Day {extraction.day} Collocation Analysis ===")
            print(f"Story: {extraction.story_file}")
            print(f"Extraction date: {extraction.extraction_date}")
            print(f"Total unique phrases: {extraction.total_unique_phrases}")

            print(f"\nKey Phrases ({len(extraction.key_phrases)}):")
            for phrase in extraction.key_phrases:
                print(f"  • {phrase}")

            print(f"\nDialogue Phrases ({len(extraction.dialogue_phrases)}):")
            for phrase in extraction.dialogue_phrases[:10]:  # Show first 10
                print(f"  • {phrase}")
            if len(extraction.dialogue_phrases) > 10:
                print(f"  ... and {len(extraction.dialogue_phrases) - 10} more")

            if extraction.english_phrases:
                print(f"\nEnglish phrases found ({len(extraction.english_phrases)}):")
                for phrase in extraction.english_phrases:
                    print(f"  • {phrase}")

        # Save if requested
        if args.save:
            output_file = extractor.save_extraction(extraction)
            print(f"\nResults saved to: {output_file}")

        return 0

    except Exception as e:
        print(f"Error extracting collocations: {e}", file=sys.stderr)
        if 'pytest' not in sys.modules:
            import traceback
            traceback.print_exc()
        return 1


def handle_debug_generation(args: argparse.Namespace) -> int:
    """Handle the debug-generation command."""
    try:
        from story_collocation_extractor import StoryCollocationExtractor
        from srs_adapter import SRSAdapter
        import os

        day = args.day

        # Validate day parameter
        if day < 1:
            print(f"Error: Day must be >= 1, got {day}", file=sys.stderr)
            return 1

        print(f"Debugging content generation for day {day}...")

        # Extract actual collocations from generated story
        extractor = StoryCollocationExtractor()
        extraction = extractor.extract_from_day_number(day)

        if not extraction:
            print(f"No story found for day {day}", file=sys.stderr)
            return 1

        # Load SRS status to see what was supposedly provided
        srs = SRSAdapter()
        due_collocations = srs.get_due_collocations(day)

        # Create debug report
        debug_report = {
            "day": day,
            "story_file": extraction.story_file,
            "debug_date": extraction.extraction_date,
            "srs_provided": {
                "due_collocations": due_collocations,
                "count": len(due_collocations)
            },
            "story_contained": {
                "key_phrases": extraction.key_phrases,
                "dialogue_phrases": extraction.dialogue_phrases,
                "total_unique": extraction.total_unique_phrases
            },
            "analysis": {
                "srs_matches": [],
                "srs_missing": [],
                "story_only": extraction.all_tagalog_phrases.copy()
            }
        }

        # Analyze what SRS provided vs what appeared in story
        for srs_colloc in due_collocations:
            found_in_story = False
            for story_phrase in extraction.all_tagalog_phrases:
                if srs_colloc.lower() in story_phrase.lower() or story_phrase.lower() in srs_colloc.lower():
                    debug_report["analysis"]["srs_matches"].append({
                        "srs_provided": srs_colloc,
                        "story_phrase": story_phrase
                    })
                    found_in_story = True
                    # Remove from story_only list
                    if story_phrase in debug_report["analysis"]["story_only"]:
                        debug_report["analysis"]["story_only"].remove(story_phrase)
                    break

            if not found_in_story:
                debug_report["analysis"]["srs_missing"].append(srs_colloc)

        # Display enhanced debug report with translation pairs
        print(f"\n=== Debug Report for Day {day} ===")
        print(f"Story: {Path(extraction.story_file).name}")

        # Show extracted story translation pairs
        print(f"\n📖 STORY TRANSLATION PAIRS ({len(extraction.key_phrase_pairs) + len(extraction.translated_pairs)} found):")

        if extraction.key_phrase_pairs:
            print("From Key Phrases:")
            for pair in extraction.key_phrase_pairs:
                print(f"  • {pair['tagalog']} → {pair['english']}")

        if extraction.translated_pairs:
            print("From Dialogue:")
            # Show first 10 dialogue pairs to avoid overwhelming output
            dialogue_sample = extraction.translated_pairs[:10]
            for pair in dialogue_sample:
                print(f"  • {pair['tagalog']} → {pair['english']}")
            if len(extraction.translated_pairs) > 10:
                print(f"  ... and {len(extraction.translated_pairs) - 10} more dialogue pairs")

        # Show SRS analysis
        print(f"\n🎯 SRS PROVIDED FOR REVIEW ({len(due_collocations)} collocations):")
        if due_collocations:
            for colloc in due_collocations:
                print(f"  • {colloc}")
        else:
            print("  None")

        print(f"\n✅ MATCHES: {len(debug_report['analysis']['srs_matches'])}/{len(due_collocations)} SRS collocations used")
        for match in debug_report["analysis"]["srs_matches"]:
            print(f"  ✓ {match['srs_provided']} ↔ {match['story_phrase']}")

        if debug_report["analysis"]["srs_missing"]:
            print(f"\n❌ UNUSED SRS COLLOCATIONS:")
            for missing in debug_report["analysis"]["srs_missing"]:
                print(f"  ✗ {missing}")

        # Show story innovations (phrases not from SRS)
        story_only_sample = debug_report["analysis"]["story_only"][:8]
        if story_only_sample:
            print(f"\nℹ️  STORY INNOVATIONS:")
            for phrase in story_only_sample:
                # Try to find the translation for this phrase
                translation = None
                for pair in extraction.key_phrase_pairs + extraction.translated_pairs:
                    if pair['tagalog'] == phrase:
                        translation = pair['english']
                        break

                if translation:
                    print(f"  + {phrase} → {translation}")
                else:
                    print(f"  + {phrase}")

            if len(debug_report["analysis"]["story_only"]) > 8:
                print(f"  ... and {len(debug_report['analysis']['story_only']) - 8} more")

        # Save debug report if requested
        if args.save:
            debug_dir = Path("instance/data/srs/debug")
            debug_dir.mkdir(parents=True, exist_ok=True)

            debug_file = debug_dir / f"day_{day}_debug_report.json"
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_report, f, indent=2, ensure_ascii=False)

            print(f"\nDebug report saved to: {debug_file}")

        return 0

    except Exception as e:
        print(f"Error debugging generation: {e}", file=sys.stderr)
        if 'pytest' not in sys.modules:
            import traceback
            traceback.print_exc()
        return 1
