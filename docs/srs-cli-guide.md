# TunaTale SRS CLI Commands Guide

## Overview

The TunaTale SRS (Spaced Repetition System) CLI provides comprehensive tools for managing vocabulary extraction, database population, and constraint enforcement testing. This guide covers all available commands and common workflows.

## Quick Start

### 1. Initial Database Setup
```bash
# Populate database from all existing stories
python main.py srs populate --all-stories --clean-first

# Check database status
python main.py srs stats
```

### 2. Test Constraint Enforcement
```bash
# Test enforcement on sample text
python main.py test-enforcement "I need water and thank you very much"

# Test enforcement on specific day's content
python main.py test-enforcement --day 16 --show-details
```

### 3. Extract Vocabulary from New Content
```bash
# Preview extraction without saving
python main.py extract-vocab --day 18 --preview

# Extract and save to database
python main.py extract-vocab --day 18 --save --filter-noise
```

## Command Reference

### SRS Database Management (`srs`)

#### `srs populate`
Populate the database with vocabulary from story content.

**Populate from all stories:**
```bash
python main.py srs populate --all-stories [options]
```

**Populate from specific day:**
```bash
python main.py srs populate --day 16 [options]
```

**Options:**
- `--clean-first`: Clean database before populating
- `--dry-run`: Show what would be done without making changes
- `--overwrite`: Overwrite existing entries
- `--filter-noise`: Filter out voice tags and noise (default: enabled)

**Examples:**
```bash
# Safe population with preview
python main.py srs populate --all-stories --dry-run

# Clean population of all stories
python main.py srs populate --all-stories --clean-first

# Add vocabulary from new day, overwriting conflicts
python main.py srs populate --day 18 --overwrite
```

#### `srs stats`
Show database statistics and health information.

```bash
python main.py srs stats [options]
```

**Options:**
- `--detailed`: Show detailed statistics including review patterns
- `--export-csv FILE`: Export statistics to CSV file

**Example Output:**
```
==================================================
SRS DATABASE STATISTICS
==================================================
Total Collocations................... 348
Database File........................ instance/data/srs/tunatale_srs.db
Database Exists...................... True
Avg Review Count..................... 1.2
Max Review Count..................... 5
Min Day.............................. 1
Max Day.............................. 17
Unreviewed Count..................... 250
==================================================
```

#### `srs clean`
Clean corrupted or noisy vocabulary entries from the database.

```bash
python main.py srs clean [options]
```

**Options:**
- `--dry-run`: Show what would be cleaned without making changes
- `--backup`: Create backup before cleaning

**Examples:**
```bash
# Preview cleaning
python main.py srs clean --dry-run

# Clean with backup
python main.py srs clean --backup
```

### Vocabulary Extraction (`extract-vocab`)

Extract collocations and vocabulary from story files.

#### Basic Usage
```bash
python main.py extract-vocab --day DAY --preview|--save [options]
```

#### Day Specification
- `--day 16`: Extract from specific day
- `--days 1-17`: Extract from day range
- `--days 1,3,5,7`: Extract from specific days

#### Action Modes
- `--preview`: Show what would be extracted without saving
- `--save`: Extract and save to database

#### Options
- `--filter-noise`: Remove voice tags and noise (default: enabled)
- `--limit N`: Limit preview results to N items (default: 20)
- `--overwrite`: Overwrite existing database entries

#### Examples
```bash
# Preview extraction from single day
python main.py extract-vocab --day 16 --preview

# Extract from multiple days and save
python main.py extract-vocab --days 1-5 --save --filter-noise

# Extract specific days with overwrite
python main.py extract-vocab --days 1,7,14 --save --overwrite
```

#### Preview Output Example
```
Day 16: story_day16_deeper_version_ask_cultural_qu_deeper_from7.txt
--------------------------------------------------
Extracted 45 collocations:
   1. 'paano po ba'
   2. 'bakit po ganyan'
   3. 'paumanhin po'
   4. 'ano pong masasabi'
   5. 'maraming salamat po'
   ... and 40 more

Quality metrics:
  Total collocations: 45
  Short (≤3 chars): 5 (11.1%)
  Likely English: 8 (17.8%)
  Clean collocations: 32 (71.1%)
```

### Constraint Enforcement Testing

#### `test-enforcement`
Test SRS constraint enforcement on text or story content.

**Test on custom text:**
```bash
python main.py test-enforcement "Your test text here" [options]
```

**Test on day content:**
```bash
python main.py test-enforcement --day 16 [options]
```

**Options:**
- `--show-details`: Show detailed replacement information
- `--method constraint|llm|both`: Choose enforcement method (default: both)
- `--context TEXT`: Set context for enforcement (default: cli_test)

**Example Output:**
```
============================================================
CONSTRAINT ENFORCEMENT TEST RESULTS
============================================================

CONSTRAINT ENFORCEMENT:
------------------------------
✅ 6 replacements made

Replacements:
   1. 'water' → 'tubig' (2x)
   2. 'thank you' → 'salamat po' (1x)
   3. 'excuse me' → 'paumanhin po' (1x)
   4. 'good' → 'maganda' (1x)
   5. 'delicious' → 'masarap' (1x)

Original length: 45 characters
Enforced length: 52 characters
```

#### `show-enforcement`
Display current constraint enforcement rules and statistics.

```bash
python main.py show-enforcement [options]
```

**Options:**
- `--format table|json`: Output format (default: table)
- `--filter TEXT`: Filter rules by substring
- `--stats`: Show enforcement statistics

**Examples:**
```bash
# Show all rules in table format
python main.py show-enforcement

# Show rules containing 'water'
python main.py show-enforcement --filter water

# Show rules with statistics
python main.py show-enforcement --stats

# Export rules as JSON
python main.py show-enforcement --format json
```

## Common Workflows

### Setting Up a New System

```bash
# 1. Populate database from all existing stories
python main.py srs populate --all-stories --clean-first

# 2. Verify population was successful
python main.py srs stats --detailed

# 3. Test enforcement is working
python main.py test-enforcement "I need water and thank you" --show-details

# 4. Show available enforcement rules
python main.py show-enforcement --stats
```

### Adding New Story Content

```bash
# 1. Preview vocabulary extraction
python main.py extract-vocab --day 18 --preview --limit 30

# 2. If extraction looks good, save to database
python main.py extract-vocab --day 18 --save --filter-noise

# 3. Test enforcement on new content
python main.py test-enforcement --day 18 --show-details

# 4. Check updated database stats
python main.py srs stats
```

### Investigating Enforcement Issues

```bash
# 1. Check current enforcement rules
python main.py show-enforcement --stats

# 2. Test enforcement on problematic content
python main.py test-enforcement --day 16 --show-details --method both

# 3. Check database vocabulary coverage
python main.py srs stats --detailed

# 4. Clean database if needed
python main.py srs clean --dry-run
```

### Batch Processing Multiple Days

```bash
# 1. Extract from multiple days
python main.py extract-vocab --days 10-17 --save --filter-noise

# 2. Check what was added
python main.py srs stats --detailed

# 3. Test enforcement across different days
python main.py test-enforcement --day 10 --show-details
python main.py test-enforcement --day 15 --show-details
python main.py test-enforcement --day 17 --show-details
```

## Troubleshooting

### Common Issues

**"No story files found"**
- Ensure you're running commands from the project root directory
- Check that `instance/data/stories/` contains `.txt` files
- Verify file naming follows expected patterns (day1, day-1, demo-0.0.3-day-1, etc.)

**"Database connection error"**
- Check that `instance/data/srs/` directory exists
- Ensure database file isn't locked by another process
- Try running with elevated permissions if needed

**"CollocationExtractor failed"**
- Ensure spacy is installed: `pip install spacy`
- Install required model: `python -m spacy download en_core_web_sm`
- Check that story files contain valid UTF-8 text

**"No replacements made"**
- Use `show-enforcement --stats` to check rule coverage
- Verify target text contains words in enforcement rules
- Test with simple known phrases: `python main.py test-enforcement "water"`

### Getting Help

```bash
# Show help for main commands
python main.py --help

# Show help for specific command groups
python main.py srs --help
python main.py extract-vocab --help
python main.py test-enforcement --help

# Show help for specific subcommands
python main.py srs populate --help
python main.py srs stats --help
```

### Debugging Output

Add `-v` or `--verbose` to commands for detailed logging:

```bash
# Verbose population
python main.py -v srs populate --day 16 --save

# Verbose extraction
python main.py -v extract-vocab --day 16 --preview
```

## Performance Tips

### For Large Datasets
- Use `--dry-run` first to estimate processing time
- Process days in smaller batches instead of all at once
- Use `--filter-noise` to reduce processing overhead
- Monitor database size with `srs stats`

### For Development
- Use `--preview` mode for testing extraction parameters
- Keep backups when cleaning: `srs clean --backup`
- Test enforcement on small text samples first
- Use `--limit` to reduce preview output size

## Integration with Existing Workflows

### With Existing Debug Commands
The new CLI commands complement existing debug commands:

```bash
# Use new commands for setup
python main.py srs populate --all-stories
python main.py extract-vocab --day 16 --save

# Use existing commands for validation
python main.py debug-srs 16 --vocabulary-analysis --validate --validation-file validation_datasets/day16_comprehensive_validation.json
```

### With Story Generation
After generating new stories, add their vocabulary:

```bash
# After story generation
python main.py generate-day 18 --strategy wider

# Extract and add vocabulary
python main.py extract-vocab --day 18 --save --filter-noise

# Test enforcement
python main.py test-enforcement --day 18
```