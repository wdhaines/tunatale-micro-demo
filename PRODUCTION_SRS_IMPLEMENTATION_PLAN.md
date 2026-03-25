# Production SRS Implementation Plan
*TunaTale Filipino Language Learning System*

## Executive Summary
Upgrade TunaTale's SRS from JSON file storage to SQLite database with comprehensive listening feedback integration, two-pass constraint enforcement, and full debug visibility. This addresses critical failures identified in Days 12-14 testing where known vocabulary (tubig/water) wasn't blocking English equivalents.

## 🎯 Success Criteria
- [ ] Water/tubig test passes (no "water" when "tubig" known)
- [ ] Listening feedback updates real intervals (not just generation dates)
- [ ] Debug visibility shows complete SRS → content pipeline
- [ ] Two-pass architecture enforces constraints reliably
- [x] Migration preserves existing SRS data ✅

## 📊 Current Implementation Status (Updated: 2025-08-27)

### ✅ COMPLETED
- **Database Schema**: SQLite database with all tables created (`instance/data/srs/tunatale_srs.db`)
  - `collocations` table: 348 entries migrated
  - `srs_violations` table: 213 violation records tracked
  - All planned tables implemented and functional
- **Migration Infrastructure**: Complete migration from JSON to SQLite
  - Migration script (`migrate_srs_to_db.py`) implemented and tested
  - Data backup system working (`data/srs_status.json.backup.20250824_175831`)
- **Core SRS Framework**: Foundation files created
  - `srs_database.py` - Database interface layer
  - `srs_enforcer.py` - Constraint enforcement system
  - `srs_llm_enforcer.py` - LLM integration for constraints
- **Test Coverage**: 359 tests passing, comprehensive test suite maintained

### 🟡 IN PROGRESS
- **Two-Pass Architecture**: Core components exist but need integration testing
- **Constraint Enforcement**: Basic framework in place, needs water/tubig validation

### ❌ PENDING
- **Listening Feedback Integration**: Framework exists but no CLI command yet
- **Debug Dashboard**: SRS debug command not implemented
- **Critical Test Cases**: SRS enforcement tests missing

## Current System Analysis

### Existing Infrastructure
- **SRS Storage**: `data/srs_status.json` with 100+ collocations at day 12
- **Core Class**: `SRSTracker` with CollocationStatus dataclass
- **Feedback Data**: `srs-feedback/day-1.json` exists but not integrated
- **Problem**: water/tubig regression - English not blocked when Filipino known

### Current SRS Data Structure
```json
{
  "current_day": 12,
  "collocations": {
    "tubig": {
      "text": "tubig",
      "first_seen_day": 3,
      "review_count": 5,
      "stability": 2.8,
      "next_review_day": 15
    }
  }
}
```

---

## Phase 1: Database Schema & Migration (Priority 1)

### 1.1 Create SQLite Database Schema

**File**: `srs_database.py`

```python
import sqlite3
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict

class SRSDatabase:
    def __init__(self, db_path: str = "instance/data/srs/tunatale_srs.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            # Collocations table with enhanced tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collocations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT UNIQUE NOT NULL,
                    filipino_text TEXT,
                    english_equivalent TEXT,
                    
                    -- Generation tracking (from existing JSON)
                    first_seen_day INTEGER,
                    last_seen_day INTEGER,
                    appearances TEXT,  -- JSON array of days
                    
                    -- Review tracking (from existing JSON)
                    review_count INTEGER DEFAULT 0,
                    next_review_day INTEGER,
                    stability REAL DEFAULT 1.0,
                    
                    -- Real-world tracking (NEW)
                    last_real_date_reviewed TEXT,
                    last_listening_day INTEGER,
                    success_rate REAL DEFAULT 0.0,
                    component_clarity REAL DEFAULT 0.0,
                    automaticity REAL DEFAULT 0.0,
                    
                    -- Context and quality
                    context_category TEXT,  -- restaurant, beach, shopping, etc.
                    priority_level TEXT DEFAULT 'medium',  -- high, medium, low
                    acquisition_type TEXT DEFAULT 'targeted',  -- targeted, natural, avoid
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Listening feedback sessions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS listening_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_date TEXT NOT NULL,
                    day_listened INTEGER NOT NULL,
                    strategy TEXT,
                    completion_rate REAL,
                    
                    -- Session data (JSON)
                    recognized_collocations TEXT,
                    partial_collocations TEXT,
                    missed_collocations TEXT,
                    
                    -- Analysis
                    notes TEXT,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # SRS constraint violations tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS srs_violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day INTEGER,
                    english_text TEXT,
                    known_filipino TEXT,
                    violation_type TEXT,  -- regression, missing, incorrect
                    was_replaced BOOLEAN DEFAULT 0,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Generation debug information
            conn.execute("""
                CREATE TABLE IF NOT EXISTS generation_debug (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day INTEGER,
                    strategy TEXT,
                    
                    -- What SRS provided
                    provided_review_items TEXT,  -- JSON
                    provided_new_items TEXT,      -- JSON
                    blocked_english TEXT,         -- JSON
                    
                    -- What actually happened
                    items_used TEXT,              -- JSON
                    items_missed TEXT,            -- JSON
                    violations_found TEXT,        -- JSON
                    replacements_made TEXT,       -- JSON
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
```

### 1.2 Migration Script from JSON to Database

**File**: `migrate_srs_to_db.py`

```python
import json
from pathlib import Path
from srs_database import SRSDatabase
from srs_tracker import SRSTracker

def migrate_json_to_database():
    """Migrate existing JSON SRS data to SQLite database"""
    
    # Load existing JSON data
    json_path = Path("data/srs_status.json")
    if not json_path.exists():
        print("No existing SRS data to migrate")
        return
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    print(f"Migrating {len(data.get('collocations', {}))} collocations from day {data.get('current_day')}")
    
    # Initialize database
    db = SRSDatabase()
    
    # Migrate collocations
    for text, colloc_data in data.get('collocations', {}).items():
        db.add_or_update_collocation(
            text=text,
            first_seen_day=colloc_data.get('first_seen_day'),
            last_seen_day=colloc_data.get('last_seen_day'),
            appearances=colloc_data.get('appearances', []),
            review_count=colloc_data.get('review_count', 0),
            next_review_day=colloc_data.get('next_review_day'),
            stability=colloc_data.get('stability', 1.0)
        )
    
    # Backup JSON file
    backup_path = json_path.with_suffix('.json.backup')
    json_path.rename(backup_path)
    print(f"Migration complete. Original backed up to {backup_path}")
```

---

## Phase 2: Listening Feedback Integration (Priority 2)

### 2.1 Create Listening Feedback Processor

**File**: `listening_feedback_processor.py`

```python
from srs_database import SRSDatabase
from datetime import datetime
import json

class ListeningFeedbackProcessor:
    def __init__(self, db: SRSDatabase):
        self.db = db
    
    def process_feedback(self, feedback_json_path: str):
        """Process listening feedback and update SRS"""
        with open(feedback_json_path, 'r') as f:
            feedback = json.load(f)
        
        # Record listening session
        session_id = self.db.record_listening_session(
            session_date=feedback['date'],
            day_listened=feedback['sessions'][0]['day'],  # Assuming single session
            recognized=feedback.get('recognized', []),
            partial=feedback.get('partial', []),
            missed=feedback.get('missed', [])
        )
        
        # Update collocation performance
        for colloc in feedback.get('recognized', []):
            self.db.mark_successful_review(
                collocation=colloc,
                real_date=feedback['date'],
                listening_day=feedback['sessions'][0]['day']
            )
        
        for partial_data in feedback.get('partial', []):
            item = partial_data if isinstance(partial_data, str) else partial_data['item']
            self.db.mark_partial_review(
                collocation=item,
                success_rate=0.5,  # Partial success
                real_date=feedback['date']
            )
        
        for colloc in feedback.get('missed', []):
            self.db.mark_failed_review(
                collocation=colloc,
                real_date=feedback['date']
            )
        
        # Process SRS violations if any
        for violation in feedback.get('regression', []):
            self.db.record_violation(
                day=feedback['sessions'][0]['day'],
                english_text=violation,
                known_filipino="TBD"  # Would need mapping
            )
        
        return self.generate_update_report(session_id)
```

### 2.2 CLI Command for Listening Feedback

**File**: `main.py` (addition)

```python
@cli.command()
@click.argument('feedback_file', type=click.Path(exists=True))
def update_srs_from_listening(feedback_file):
    """Update SRS based on listening feedback JSON"""
    click.echo(f"Processing listening feedback from {feedback_file}")
    
    db = SRSDatabase()
    processor = ListeningFeedbackProcessor(db)
    
    try:
        report = processor.process_feedback(feedback_file)
        
        click.echo("\n=== SRS Update Report ===")
        click.echo(f"✅ Recognized: {len(report['recognized'])} items")
        click.echo(f"⚠️  Partial: {len(report['partial'])} items")
        click.echo(f"❌ Missed: {len(report['missed'])} items")
        click.echo(f"🔴 Violations: {len(report['violations'])} found")
        
        if report['violations']:
            click.echo("\nCritical Violations:")
            for v in report['violations'][:5]:
                click.echo(f"  - '{v['english']}' should be '{v['filipino']}'")
        
        click.echo("\n✅ SRS updated successfully")
        
    except Exception as e:
        click.echo(f"❌ Error processing feedback: {e}", err=True)
        raise
```

---

## Phase 3: Two-Pass Architecture with Constraint Enforcement (Priority 3)

### 3.1 Implement Two-Pass Generation

**File**: `srs_enforcer.py`

```python
from srs_database import SRSDatabase
import re

class SRSEnforcer:
    def __init__(self, db: SRSDatabase):
        self.db = db
        self.replacement_dict = self._build_replacement_dict()
    
    def _build_replacement_dict(self) -> Dict[str, str]:
        """Build dictionary of English → Filipino replacements"""
        replacements = {}
        
        # Get all known Filipino vocabulary with English equivalents
        known_vocab = self.db.get_known_vocabulary_with_equivalents()
        
        for row in known_vocab:
            if row['english_equivalent'] and row['filipino_text']:
                replacements[row['english_equivalent'].lower()] = row['filipino_text']
        
        # Add critical replacements from testing
        critical_replacements = {
            'water': 'tubig',
            'bottled water': 'tubig',
            'beach': 'dalampasigan',
            'size': 'laki',
            'pink': 'rosas',
            'blue': 'asul',
            'each': 'bawat',
            'thirty': 'tatlumpu',
            'sixty': 'animnapu',
            'eighty': 'walumpu'
        }
        
        replacements.update(critical_replacements)
        return replacements
    
    def enforce_constraints(self, content: str, day: int) -> tuple[str, list]:
        """
        Pass 2: Enforce SRS constraints on generated content
        Returns: (enforced_content, list_of_replacements)
        """
        violations = []
        enforced_content = content
        
        # Check for each known replacement
        for english, filipino in self.replacement_dict.items():
            # Use word boundaries to avoid partial replacements
            pattern = r'\b' + re.escape(english) + r'\b'
            
            if re.search(pattern, enforced_content, re.IGNORECASE):
                # Found violation
                violations.append({
                    'english': english,
                    'filipino': filipino,
                    'count': len(re.findall(pattern, enforced_content, re.IGNORECASE))
                })
                
                # Replace all occurrences
                enforced_content = re.sub(
                    pattern, 
                    filipino, 
                    enforced_content, 
                    flags=re.IGNORECASE
                )
        
        # Record violations in database
        for v in violations:
            self.db.record_violation(
                day=day,
                english_text=v['english'],
                known_filipino=v['filipino'],
                was_replaced=True
            )
        
        return enforced_content, violations
```

### 3.2 Integrate Two-Pass into Story Generation

**File**: `story_generator.py` (modification)

```python
def generate_story_for_day(self, day: int) -> Optional[str]:
    """Generate story with two-pass SRS enforcement"""
    
    # Pass 1: Generate with positive constraints
    srs_constraints = self._get_srs_constraints(day)
    
    # Debug: Log what we're providing
    debug_data = {
        'day': day,
        'provided_review_items': srs_constraints['review_items'],
        'provided_new_items': srs_constraints['new_items'],
        'blocked_english': list(srs_constraints['blocked_english'].keys())
    }
    
    # Generate story
    story = self._generate_with_constraints(day, srs_constraints)
    
    if not story:
        return None
    
    # Pass 2: Enforce constraints
    enforcer = SRSEnforcer(self.db)
    enforced_story, violations = enforcer.enforce_constraints(story, day)
    
    # Debug: Log what was replaced
    debug_data['violations_found'] = violations
    debug_data['replacements_made'] = [f"{v['english']}→{v['filipino']}" for v in violations]
    
    # Save debug info
    self.db.save_generation_debug(debug_data)
    
    # Print immediate feedback
    if violations:
        print("\n=== SRS ENFORCEMENT ===")
        print(f"Found {len(violations)} violations")
        for v in violations[:5]:
            print(f"  ✓ Replaced '{v['english']}' → '{v['filipino']}' ({v['count']}x)")
    
    return enforced_story
```

---

## Phase 4: Debug Visibility System (Priority 4)

### 4.1 Create Debug Dashboard Command

**File**: `main.py` (addition)

```python
@cli.command()
@click.option('--day', type=int, help='Show debug info for specific day')
def srs_debug(day):
    """Show SRS debug information and pipeline visibility"""
    db = SRSDatabase()
    
    if day:
        # Show specific day debug info
        debug_info = db.get_generation_debug(day)
        if debug_info:
            click.echo(f"\n=== Day {day} SRS Debug Info ===")
            click.echo(f"Strategy: {debug_info['strategy']}")
            click.echo(f"\n📤 PROVIDED TO LLM:")
            click.echo(f"  Review items: {debug_info['provided_review_items']}")
            click.echo(f"  New items: {debug_info['provided_new_items']}")
            click.echo(f"  Blocked English: {debug_info['blocked_english']}")
            
            click.echo(f"\n📥 ACTUAL RESULTS:")
            click.echo(f"  Items used: {debug_info['items_used']}")
            click.echo(f"  Items missed: {debug_info['items_missed']}")
            click.echo(f"  Violations: {debug_info['violations_found']}")
            click.echo(f"  Replacements: {debug_info['replacements_made']}")
    else:
        # Show overall SRS status
        stats = db.get_srs_statistics()
        click.echo("\n=== SRS System Status ===")
        click.echo(f"Total collocations: {stats['total']}")
        click.echo(f"Well-known (can block English): {stats['well_known']}")
        click.echo(f"Learning: {stats['learning']}")
        click.echo(f"New: {stats['new']}")
        
        # Show recent violations
        violations = db.get_recent_violations(limit=10)
        if violations:
            click.echo("\n🔴 Recent SRS Violations:")
            for v in violations:
                click.echo(f"  Day {v['day']}: '{v['english']}' should be '{v['filipino']}'")
```

---

## Phase 5: SRS Debug Analysis System (Priority 4)

### 5.1 Vocabulary Recognition State Analysis

**File**: `srs_debug_analyzer.py`

```python
from srs_database import SRSDatabase
from pathlib import Path
import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class RecognitionState(Enum):
    """Vocabulary recognition states in TunaTale SRS system."""
    UNKNOWN = "unknown"                    # Not in SRS at all
    DORMANT = "dormant"                   # Not seen in 7+ days  
    UNSTABLE = "unstable"                 # stability < 1.0
    NATURALLY_ACQUIRING = "naturally_acquiring"  # Learning through exposure
    EXPLICITLY_LEARNED = "explicitly_learned"   # Targeted learning pattern
    HIGH_STABILITY = "high_stability"     # stability > 3.0 and review_count > 5

@dataclass
class VocabularyAnalysis:
    """Analysis result for a single vocabulary item."""
    word: str
    recognition_state: RecognitionState
    srs_data: Optional[Dict[str, Any]]
    context_appearances: List[str]
    learning_pattern: Optional[str]

class SRSDebugAnalyzer:
    """Analyzes vocabulary recognition states from story files and SRS data."""
    
    def __init__(self, db_path: str = "instance/data/srs/tunatale_srs.db"):
        """Initialize analyzer with SRS database connection."""
        self.db = SRSDatabase(db_path)
    
    def analyze_day_vocabulary(self, day: int) -> Dict[str, Any]:
        """
        Analyze vocabulary recognition states for a specific day.
        
        Args:
            day: Day number to analyze
            
        Returns:
            Comprehensive vocabulary analysis report
        """
        # Load story file for the day
        story_content = self._load_story_file(day)
        if not story_content:
            return {"error": f"No story file found for day {day}"}
        
        # Extract Tagalog vocabulary
        vocabulary = self._extract_tagalog_vocabulary(story_content)
        
        # Analyze each word
        analyses = []
        for word in vocabulary:
            analysis = self._analyze_word(word, day)
            analyses.append(analysis)
        
        # Generate summary statistics
        state_counts = self._calculate_state_distribution(analyses)
        
        return {
            "day": day,
            "story_file": self._get_story_filename(day),
            "total_vocabulary": len(vocabulary),
            "vocabulary_analyses": [self._serialize_analysis(a) for a in analyses],
            "recognition_state_distribution": state_counts,
            "srs_effectiveness_metrics": self._calculate_effectiveness_metrics(analyses),
            "generated_at": self._get_current_timestamp()
        }
    
    def _load_story_file(self, day: int) -> Optional[str]:
        """Load story content for the specified day."""
        story_dir = Path("instance/data/stories")
        
        # Look for story files matching day pattern
        patterns = [
            f"story_day{day}_*.txt",
            f"*day{day}*.txt", 
            f"*day_{day}_*.txt"
        ]
        
        for pattern in patterns:
            matches = list(story_dir.glob(pattern))
            if matches:
                # Use first match (could be refined with strategy preference)
                with open(matches[0], 'r', encoding='utf-8') as f:
                    return f.read()
        
        return None
    
    def _extract_tagalog_vocabulary(self, story_content: str) -> List[str]:
        """Extract all unique Tagalog words from TAGALOG-FEMALE/MALE speaker lines."""
        # Pattern to match Tagalog speaker lines
        tagalog_pattern = r'\[TAGALOG-(?:FEMALE|MALE)-\d+\]:\s*([^\n\[]+)'
        matches = re.findall(tagalog_pattern, story_content)
        
        # Extract individual words, filtering out common artifacts
        vocabulary = set()
        for phrase in matches:
            # Clean and split phrase
            clean_phrase = re.sub(r'[^\w\s]', ' ', phrase.strip().lower())
            words = clean_phrase.split()
            
            # Filter out breakdown artifacts and very short words
            for word in words:
                if len(word) >= 2 and not word.isdigit():
                    vocabulary.add(word)
        
        return sorted(list(vocabulary))
    
    def _analyze_word(self, word: str, current_day: int) -> VocabularyAnalysis:
        """Analyze recognition state for a single word."""
        # Get SRS data for this word
        srs_data = self._get_srs_data(word)
        
        # Determine recognition state
        state = self._categorize_word(word, srs_data, current_day)
        
        # Analyze learning pattern if available
        learning_pattern = self._analyze_learning_pattern(srs_data) if srs_data else None
        
        return VocabularyAnalysis(
            word=word,
            recognition_state=state,
            srs_data=srs_data,
            context_appearances=[],  # Could be enhanced to track contexts
            learning_pattern=learning_pattern
        )
    
    def _categorize_word(self, word: str, srs_data: Optional[Dict], current_day: int) -> RecognitionState:
        """
        Categorize word into recognition states based on SRS data.
        
        Recognition state logic:
        - high_stability: stability > 3.0 AND review_count > 5 (enforced)
        - unstable: stability < 1.0
        - dormant: not seen in 7+ days (current_day - last_seen_day > 7)
        - unknown: not in SRS at all
        - explicitly_learned/naturally_acquiring: based on learning patterns
        """
        if not srs_data:
            return RecognitionState.UNKNOWN
        
        stability = srs_data.get('stability', 1.0)
        review_count = srs_data.get('review_count', 0)
        last_seen_day = srs_data.get('last_seen_day', current_day)
        
        # Check high stability first (enforced state)
        if stability > 3.0 and review_count > 5:
            return RecognitionState.HIGH_STABILITY
        
        # Check dormant (not seen recently)
        if current_day - last_seen_day > 7:
            return RecognitionState.DORMANT
        
        # Check unstable
        if stability < 1.0:
            return RecognitionState.UNSTABLE
        
        # Distinguish explicit vs natural learning
        if review_count > 2:
            return RecognitionState.EXPLICITLY_LEARNED
        else:
            return RecognitionState.NATURALLY_ACQUIRING
```

### 5.2 CLI Integration

**File**: `main.py` (addition)

```python
def debug_srs_command(args):
    """Debug SRS vocabulary recognition states for a given day."""
    from srs_debug_analyzer import SRSDebugAnalyzer
    
    analyzer = SRSDebugAnalyzer()
    report = analyzer.analyze_day_vocabulary(args.day)
    
    if 'error' in report:
        print(f"❌ Error: {report['error']}")
        return
    
    if args.export:
        # Export to JSON file
        with open(args.export, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"✅ Report exported to {args.export}")
    else:
        # Display formatted console output
        _display_srs_debug_report(report)

def _display_srs_debug_report(report: Dict[str, Any]):
    """Display formatted SRS debug report to console."""
    print(f"\n=== SRS Debug Analysis: Day {report['day']} ===")
    print(f"Story file: {report['story_file']}")
    print(f"Total vocabulary: {report['total_vocabulary']} words")
    
    # Show recognition state distribution
    distribution = report['recognition_state_distribution']
    print(f"\n📊 Recognition State Distribution:")
    for state, count in distribution.items():
        percentage = (count / report['total_vocabulary']) * 100
        print(f"  {state}: {count} ({percentage:.1f}%)")
    
    # Show effectiveness metrics
    metrics = report['srs_effectiveness_metrics']
    print(f"\n⚡ SRS Effectiveness Metrics:")
    for metric, value in metrics.items():
        print(f"  {metric}: {value}")
    
    # Show sample vocabulary by state
    print(f"\n📝 Sample Vocabulary by Recognition State:")
    analyses = report['vocabulary_analyses']
    states_shown = set()
    
    for analysis in analyses[:20]:  # Limit to first 20 for readability
        state = analysis['recognition_state']
        if state not in states_shown:
            print(f"  {state}: {analysis['word']}")
            states_shown.add(state)
            if len(states_shown) >= 6:  # Show max 6 different states
                break

# Add to CLI parser setup
def setup_debug_srs_parser(subparsers):
    """Setup debug-srs command parser."""
    parser = subparsers.add_parser(
        'debug-srs',
        help='Debug SRS vocabulary recognition states for a day'
    )
    parser.add_argument(
        '--day', 
        type=int, 
        required=True,
        help='Day number to analyze (15-18 supported)'
    )
    parser.add_argument(
        '--export',
        type=str,
        help='Export report to JSON file (e.g., debug.json)'
    )
    parser.set_defaults(func=debug_srs_command)
```

---

## Phase 5: Testing Strategy

### 5.1 Critical Test Cases

**File**: `tests/test_srs_enforcement.py`

```python
def test_water_tubig_regression():
    """Test that water is replaced with tubig when known"""
    db = SRSDatabase(':memory:')  # In-memory for testing
    
    # Add tubig as known vocabulary
    db.add_or_update_collocation(
        text='tubig',
        english_equivalent='water',
        review_count=5,  # Well-known
        stability=3.0
    )
    
    # Test content with water
    test_content = "I need some bottled water please."
    
    enforcer = SRSEnforcer(db)
    enforced, violations = enforcer.enforce_constraints(test_content, day=1)
    
    # Verify replacement
    assert 'water' not in enforced.lower()
    assert 'tubig' in enforced.lower()
    assert len(violations) > 0
    assert violations[0]['english'] == 'water'

def test_listening_feedback_updates_intervals():
    """Test that listening feedback properly updates review intervals"""
    db = SRSDatabase(':memory:')
    processor = ListeningFeedbackProcessor(db)
    
    # Process test feedback
    feedback = {
        'date': '2025-01-15',
        'sessions': [{'day': 13}],
        'recognized': ['tsinelas'],
        'missed': ['wala na pala kami']
    }
    
    processor.process_feedback_dict(feedback)
    
    # Verify intervals updated
    tsinelas = db.get_collocation('tsinelas')
    assert tsinelas['last_real_date_reviewed'] == '2025-01-15'
    assert tsinelas['success_rate'] > 0
    
    wala = db.get_collocation('wala na pala kami')
    assert wala['next_review_day'] < tsinelas['next_review_day']
```

### 5.2 Migration Test

```bash
# Test migration preserves data
python migrate_srs_to_db.py
sqlite3 instance/data/srs/tunatale_srs.db "SELECT COUNT(*) FROM collocations"
```

---

## Implementation Checklist

### Week 1: Database & Migration ✅ COMPLETED
- [x] Create database schema (srs_database.py) ✅
- [x] Write migration script ✅
- [x] Test migration with existing `data/srs_status.json` ✅ (348 collocations migrated)
- [x] Update SRSTracker to use database ✅

### Week 2: Listening Feedback 🟡 PARTIAL
- [x] Implement ListeningFeedbackProcessor ✅ (in `srs_feedback_system.py`)
- [ ] Add CLI command for feedback processing ❌
- [ ] Test with `srs-feedback/day-1.json` ❌
- [ ] Verify intervals update correctly ❌

### Week 3: Two-Pass Architecture 🟡 PARTIAL  
- [x] Implement SRSEnforcer ✅
- [ ] Integrate into story generation ❌ (needs testing)
- [ ] Test water/tubig replacement ❌ (CRITICAL - needs test cases)
- [ ] Verify debug logging works ❌

### Week 4: Polish & Testing ❌ PENDING
- [ ] Add debug dashboard ❌
- [ ] Complete test suite ❌ (missing `tests/test_srs_enforcement.py`)
- [ ] Documentation ❌
- [ ] Performance optimization ❌

### Week 5: SRS Debug Analysis System 🟡 IN PROGRESS
- [x] Update implementation plan with Phase 5 ✅
- [ ] Implement SRSDebugAnalyzer class ❌
- [ ] Add CLI command for debug-srs ❌
- [ ] Test with days 15-18 stories ❌
- [ ] Validate recognition state categorization ❌

---

## Success Validation Commands

Run these commands to verify everything works:

```bash
# 1. Migrate existing data
python migrate_srs_to_db.py

# 2. Process listening feedback
tunatale update-srs-from-listening srs-feedback/day-1.json

# 3. Generate with enforcement
tunatale generate-day 14 --strategy=deeper --debug

# 4. Check for water/tubig fix
grep -i "water\|tubig" instance/data/stories/day14*.txt

# 5. View debug info
tunatale srs-debug --day 14
```

**Success Criteria**: If "water" is replaced with "tubig" and debug shows constraint violations, the system is working correctly.

---

## Risk Mitigation

### Data Integrity
- Always backup before migration (`data/srs_status.json.backup`)
- Validate data formats before processing
- Test with small datasets first

### User Experience
- Maintain backward compatibility with existing CLI commands
- Provide clear error messages and guidance
- Document all new features and workflows

### Content Quality
- Test generation with multiple scenarios
- Validate Filipino language authenticity
- Ensure dialogue remains natural and practical

---

## 🎯 RECOMMENDED NEXT STEP

**Priority 1: Create SRS Enforcement Test Suite**

The most critical missing piece is the test suite for SRS constraint enforcement, specifically the **water/tubig regression test**. This is the core validation that the entire system was designed to solve.

**Immediate Action Items:**
1. Create `tests/test_srs_enforcement.py` with water/tubig test case
2. Validate that `SRSEnforcer.enforce_constraints()` replaces "water" with "tubig"
3. Test integration with story generation workflow
4. Verify database violation tracking works

This test will prove the system solves the original problem and unlock the remaining implementation phases.

---

*This document serves as the comprehensive implementation guide for upgrading TunaTale's SRS system to production standards with database storage, real listening feedback integration, and robust constraint enforcement.*