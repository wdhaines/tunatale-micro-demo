# TunaTale SRS Management Workflows

This document provides step-by-step workflows for common SRS vocabulary management tasks. Each workflow includes commands, expected outputs, and troubleshooting tips.

## Initial Setup (Fresh System)

### Scenario
You have a fresh TunaTale installation with existing story files but no populated SRS database.

### Workflow

#### 1. Clean Database Population
```bash
# Start with a clean slate
python main.py srs clean --backup
```
**Expected Output:**
```
✅ Database backup created
ℹ️  Found 12 corrupted entries:
  - 'tagalog-female-1'
  - '[narrator'
  - 'po\npo'
  ... and 9 more
✅ Removed 12 corrupted entries
```

#### 2. Populate from All Stories
```bash
# Populate database with all available story content
python main.py srs populate --all-stories --clean-first
```
**Expected Output:**
```
ℹ️  Starting SRS database population...
ℹ️  Found 17 story files
Processing stories: |██████████████████████████████| 17/17 (100.0%)
✅ Processed 17 files, added 1,234 collocations
✅ Database population completed!
```

#### 3. Verify Population Success
```bash
# Check database health and statistics
python main.py srs stats --detailed
```
**Expected Output:**
```
==================================================
SRS DATABASE STATISTICS
==================================================
Total Collocations................... 1234
Database File........................ instance/data/srs/tunatale_srs.db
Database Exists...................... True
Avg Review Count..................... 0.0
Max Review Count..................... 0
Min Day.............................. 1
Max Day.............................. 17
Unreviewed Count..................... 1234
==================================================
```

#### 4. Test Constraint Enforcement
```bash
# Verify enforcement is working with known vocabulary
python main.py test-enforcement "I need water and thank you very much" --show-details
```
**Expected Output:**
```
============================================================
CONSTRAINT ENFORCEMENT TEST RESULTS
============================================================

CONSTRAINT ENFORCEMENT:
------------------------------
✅ 3 replacements made

Replacements:
   1. 'water' → 'tubig' (1x)
   2. 'thank you' → 'salamat po' (1x)
   3. 'very much' → 'po talaga' (1x)

Original length: 39 characters
Enforced length: 43 characters
```

#### 5. Validate Setup
```bash
# Show enforcement rules and coverage
python main.py show-enforcement --stats
```
**Expected Output:**
```
Total enforcement rules: 28
Average English length: 6.2 characters
Average Filipino length: 8.1 characters
Database coverage: 18/28 (64.3%)

Uncovered enforcement rules:
  'fresh' → 'sariwang' (not in database)
  'grilled' → 'inihaw' (not in database)
```

---

## Adding New Story Content

### Scenario
You've generated a new story (Day 18) and need to extract its vocabulary and test enforcement.

### Workflow

#### 1. Preview Vocabulary Extraction
```bash
# First, see what vocabulary would be extracted
python main.py extract-vocab --day 18 --preview --limit 30
```
**Expected Output:**
```
Day 18: story_day18_beach_activities.txt
--------------------------------------------------
ℹ️  Extracted 52 collocations:
   1. 'magandang umaga po'
   2. 'pumunta sa beach'
   3. 'swimming po ba'
   4. 'snorkeling equipment'
   5. 'island hopping'
   ... and 47 more

Quality metrics:
  Total collocations: 52
  Short (≤3 chars): 3 (5.8%)
  Likely English: 12 (23.1%)
  Clean collocations: 37 (71.2%)
```

#### 2. Extract and Save Quality Vocabulary
```bash
# If extraction looks good, save filtered vocabulary
python main.py extract-vocab --day 18 --save --filter-noise
```
**Expected Output:**
```
ℹ️  Starting vocabulary extraction...
ℹ️  Extracting and saving for 1 day(s)
Processing day 18: |██████████████████████████████| 1/1 (100.0%)
✅ Processed 1 days, saved 37 collocations
```

#### 3. Test Enforcement on New Content
```bash
# Test how enforcement works on the new day's content
python main.py test-enforcement --day 18 --show-details --method both
```
**Expected Output:**
```
============================================================
CONSTRAINT ENFORCEMENT TEST RESULTS
============================================================

CONSTRAINT ENFORCEMENT:
------------------------------
✅ 8 replacements made

Replacements:
   1. 'good morning' → 'magandang umaga' (2x)
   2. 'swimming' → 'paglangoy' (1x)
   3. 'beach' → 'dalampasigan' (1x)
   ... and 5 more

LLM ENFORCEMENT:
------------------------------
✅ 12 replacements made

Replacements:
   1. 'equipment' → 'kagamitan' (1x)
   2. 'beautiful' → 'maganda' (3x)
   3. 'island' → 'isla' (2x)
   ... and 9 more
```

#### 4. Verify Database Update
```bash
# Check updated statistics
python main.py srs stats
```
**Expected Output:**
```
==================================================
SRS DATABASE STATISTICS
==================================================
Total Collocations................... 1271
Database File........................ instance/data/srs/tunatale_srs.db
Database Exists...................... True
==================================================
```

---

## Investigating Enforcement Issues

### Scenario
You notice that Day 16 content isn't being properly enforced - English words that should be replaced with Filipino are remaining unchanged.

### Workflow

#### 1. Check Current Enforcement Rules
```bash
# Review what rules are available
python main.py show-enforcement --stats
```
**Expected Output:**
```
==================================================
ENFORCEMENT STATISTICS
==================================================
Total enforcement rules: 28
Average English length: 6.2 characters
Average Filipino length: 8.1 characters
Database coverage: 18/28 (64.3%)

10 enforcement rules not covered by database
==================================================
```

#### 2. Test Enforcement on Problematic Content
```bash
# Test both constraint and LLM enforcement on Day 16
python main.py test-enforcement --day 16 --show-details --method both
```
**Expected Output:**
```
CONSTRAINT ENFORCEMENT:
------------------------------
⚠️  2 replacements made

Replacements:
   1. 'water' → 'tubig' (1x)
   2. 'thank you' → 'salamat po' (1x)

LLM ENFORCEMENT:
------------------------------
❌ Failed: MockLLM timeout error
```

#### 3. Investigate Database Vocabulary Coverage
```bash
# Check what Filipino vocabulary exists in database
python main.py srs stats --detailed
```
**Expected Output:**
```
==================================================
SRS DATABASE STATISTICS
==================================================
Total Collocations................... 1271
Avg Review Count..................... 0.2
Unreviewed Count..................... 1180
==================================================
```

#### 4. Check for Database Corruption
```bash
# Look for corrupted entries that might affect performance
python main.py srs clean --dry-run
```
**Expected Output:**
```
ℹ️  Found 45 corrupted entries:
  - 'tagalog-female-1'
  - '[narrator]: good morning'
  - 'po\npo\npo'
  ... and 42 more
ℹ️  DRY RUN: Would remove these corrupted entries
```

#### 5. Clean Database and Re-test
```bash
# Clean corrupted entries
python main.py srs clean --backup

# Re-test enforcement
python main.py test-enforcement --day 16 --show-details
```
**Expected Output:**
```
✅ Database backup created
✅ Removed 45 corrupted entries

CONSTRAINT ENFORCEMENT:
------------------------------
✅ 8 replacements made

Replacements:
   1. 'water' → 'tubig' (2x)
   2. 'thank you' → 'salamat po' (1x)
   3. 'excuse me' → 'paumanhin po' (1x)
   ... and 5 more
```

---

## Batch Processing Multiple Days

### Scenario
You need to extract vocabulary from Days 10-17 that were previously not processed, and ensure enforcement works across all of them.

### Workflow

#### 1. Batch Vocabulary Extraction
```bash
# Extract from range of days
python main.py extract-vocab --days 10-17 --save --filter-noise
```
**Expected Output:**
```
ℹ️  Starting vocabulary extraction...
ℹ️  Extracting and saving for 8 day(s)
Processing day 10: |████                          | 1/8 (12.5%)
Processing day 11: |████████                      | 2/8 (25.0%)
...
Processing day 17: |██████████████████████████████| 8/8 (100.0%)
✅ Processed 8 days, saved 312 collocations
```

#### 2. Verify Database Growth
```bash
# Check before and after statistics
python main.py srs stats --detailed
```
**Expected Output:**
```
==================================================
SRS DATABASE STATISTICS
==================================================
Total Collocations................... 1583
Database File........................ instance/data/srs/tunatale_srs.db
Min Day.............................. 1
Max Day.............................. 17
==================================================
```

#### 3. Test Enforcement Across Multiple Days
```bash
# Test enforcement on several days
python main.py test-enforcement --day 10 --show-details | head -20
python main.py test-enforcement --day 13 --show-details | head -20
python main.py test-enforcement --day 17 --show-details | head -20
```
**Expected Pattern:**
```
# Day 10 - Early content, basic vocabulary
✅ 4 replacements made

# Day 13 - Mid-series, more complex
✅ 12 replacements made  

# Day 17 - Advanced content, comprehensive enforcement
✅ 18 replacements made
```

#### 4. Quality Assessment
```bash
# Check overall enforcement coverage
python main.py show-enforcement --stats
```
**Expected Output:**
```
==================================================
ENFORCEMENT STATISTICS
==================================================
Total enforcement rules: 28
Database coverage: 24/28 (85.7%)

Uncovered enforcement rules:
  'grilled' → 'inihaw' (not in database)
  'separate' → 'hiwalay' (not in database)
==================================================
```

#### 5. Address Coverage Gaps
```bash
# Extract from specific days that might have missing vocabulary
python main.py extract-vocab --days 12,14,16 --save --overwrite
```

---

## Maintenance and Cleanup

### Scenario
Your SRS database has grown large and contains noise from earlier extractions. You need to clean it up while preserving valuable vocabulary.

### Workflow

#### 1. Assess Current Database Health
```bash
# Get detailed statistics
python main.py srs stats --detailed --export-csv srs_stats_before.csv
```

#### 2. Identify Cleanup Targets
```bash
# Preview what would be cleaned
python main.py srs clean --dry-run
```
**Expected Output:**
```
ℹ️  Found 127 corrupted entries:
  - 'tagalog-female-1' (voice tag)
  - '[narrator' (markup fragment)
  - 'po\n\npo' (formatting artifact)
  - 'a' (single letter)
  - 'the' (common English word)
  ... and 122 more

ℹ️  DRY RUN: Would remove these corrupted entries
```

#### 3. Create Backup Before Cleaning
```bash
# Clean with backup
python main.py srs clean --backup
```
**Expected Output:**
```
ℹ️  Database backed up to: instance/data/srs/tunatale_srs.backup_20231201_143022.db
✅ Removed 127 corrupted entries
```

#### 4. Re-populate with Clean Extraction
```bash
# Re-extract with better filtering
python main.py extract-vocab --days 1-17 --save --filter-noise --overwrite
```

#### 5. Verify Cleanup Results
```bash
# Compare before/after statistics
python main.py srs stats --detailed --export-csv srs_stats_after.csv
```
**Expected Improvements:**
- Reduced total collocations (noise removed)
- Higher quality score (fewer short/English entries)
- Better enforcement coverage

---

## Development and Testing Workflow

### Scenario
You're developing new features and need to test them against known-good vocabulary data.

### Workflow

#### 1. Create Test Environment
```bash
# Use a test database
export SRS_DB_PATH="test_srs.db"

# Populate with clean test data
python main.py srs populate --day 16 --clean-first
```

#### 2. Test New Features
```bash
# Test extraction with new parameters
python main.py extract-vocab --day 16 --preview --limit 50

# Test enforcement modifications
python main.py test-enforcement "custom test text" --show-details
```

#### 3. Validate Against Known Good Data
```bash
# Compare with validation files
python main.py debug-srs 16 --vocabulary-analysis --validate --validation-file validation_datasets/day16_comprehensive_validation.json
```

#### 4. Performance Testing
```bash
# Time batch operations
time python main.py extract-vocab --days 1-17 --preview

# Monitor database growth
watch -n 1 'python main.py srs stats | grep "Total Collocations"'
```

#### 5. Reset Test Environment
```bash
# Clean up test database
unset SRS_DB_PATH
rm test_srs.db
```

---

## Troubleshooting Common Issues

### Issue: "CollocationExtractor failed" 

#### Diagnostic Commands:
```bash
# Check spaCy installation
python -c "import spacy; print(spacy.__version__)"

# Check model availability  
python -c "import spacy; spacy.load('en_core_web_sm')"
```

#### Resolution:
```bash
# Install missing dependencies
pip install spacy
python -m spacy download en_core_web_sm
```

### Issue: "No replacements made" in enforcement

#### Diagnostic Commands:
```bash
# Check enforcement rules
python main.py show-enforcement --filter water

# Test with known vocabulary
python main.py test-enforcement "water" --show-details
```

#### Resolution:
```bash
# Verify database has Filipino equivalents
python main.py srs stats --detailed

# Re-populate if needed
python main.py srs populate --day 1 --overwrite
```

### Issue: Database performance degradation

#### Diagnostic Commands:
```bash
# Check database size and corruption
python main.py srs stats --detailed
python main.py srs clean --dry-run
```

#### Resolution:
```bash
# Clean and optimize database
python main.py srs clean --backup
# SQLite VACUUM would be run automatically
```