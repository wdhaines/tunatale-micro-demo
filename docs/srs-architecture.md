# TunaTale SRS Vocabulary Pipeline Architecture

## Overview

The TunaTale SRS (Spaced Repetition System) manages vocabulary learning through an integrated pipeline that extracts, stores, and enforces Filipino vocabulary from story content. This document provides technical details of the architecture, data flow, and component interactions.

## Data Flow Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Story Files   │───▶│ CollocationExt   │───▶│  SRS Database   │
│   (.txt files)  │    │   (spacy/NLP)    │    │   (SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Generated Text  │◀───│ SRS Enforcers    │◀───│ Vocabulary Data │
│ (Filipino/Eng)  │    │ (Constraint+LLM) │    │ + Review State  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   CLI Commands   │───▶│ Manual Analysis │
                       │  (Management)    │    │ & Validation    │
                       └──────────────────┘    └─────────────────┘
```

## Core Components

### 1. CollocationExtractor (`collocation_extractor.py`)

**Purpose**: Extracts meaningful vocabulary phrases from story content using NLP.

**Dependencies**:
- spaCy with `en_core_web_sm` model
- Custom entity patterns for Filipino learning context
- Background vocabulary filtering

**Key Methods**:
```python
def extract_collocations(self, story: str) -> List[str]:
    """Extract collocations from story text using spaCy NLP"""
    
def _filter_collocations(self, collocations: List[str]) -> List[str]:
    """Filter out noise, voice tags, and non-pedagogical content"""
```

**Data Processing Pipeline**:
1. **Text Processing**: spaCy tokenization and parsing
2. **Noun Chunk Extraction**: Identify meaningful phrases
3. **Entity Recognition**: Custom patterns for learning content
4. **Noise Filtering**: Remove voice tags, fragments, common English words
5. **Quality Validation**: Length checks, format validation

### 2. SRSDatabase (`srs_database.py`)

**Purpose**: Persistent storage for vocabulary with SRS metadata.

**Database Schema**:
```sql
CREATE TABLE collocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT UNIQUE NOT NULL,
    
    -- SRS tracking
    first_seen_day INTEGER NOT NULL,
    last_seen_day INTEGER NOT NULL,
    appearances TEXT NOT NULL,      -- JSON array of days
    review_count INTEGER DEFAULT 0,
    next_review_day INTEGER DEFAULT 0,
    stability REAL DEFAULT 1.0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE srs_violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day INTEGER NOT NULL,
    english_text TEXT NOT NULL,
    known_filipino TEXT NOT NULL,
    violation_type TEXT DEFAULT 'constraint_enforcement',
    was_replaced BOOLEAN DEFAULT 1,
    context TEXT DEFAULT 'story',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Key Features**:
- **ACID Transactions**: SQLite ensures data consistency
- **Indexing**: Optimized for text lookups and review scheduling
- **Migration Support**: Handles upgrades from JSON-based storage
- **Violation Tracking**: Records constraint enforcement history

### 3. SRS Enforcement System

#### 3.1 SRSEnforcer (`srs_enforcer.py`)

**Purpose**: Rule-based English→Filipino constraint enforcement.

**Architecture**:
```python
class SRSEnforcer:
    def __init__(self, db: SRSDatabase):
        self.db = db
        self.replacement_dict = self._build_replacement_dictionary()
    
    def enforce_constraints(self, content: str, context: str) -> Tuple[str, List[Dict]]:
        """Apply hardcoded replacement rules to content"""
```

**Replacement Strategy**:
- **Hardcoded Mappings**: Critical vocabulary pairs (water→tubig, thank you→salamat po)
- **Priority-Based**: High-frequency learning words prioritized
- **Context-Aware**: Different rules for different content types
- **Violation Logging**: Tracks all replacements for analysis

#### 3.2 SRSLLMEnforcer (`srs_llm_enforcer.py`)

**Purpose**: AI-powered contextual vocabulary enforcement.

**Architecture**:
```python
class SRSLLMEnforcer:
    def enforce_with_llm(self, content: str, day: int, context: str) -> Tuple[str, List[Dict]]:
        """Use LLM to make contextual Filipino replacements"""
```

**LLM Integration**:
- **MockLLM Support**: Consistent responses for testing
- **Prompt Engineering**: Specialized prompts for vocabulary enforcement
- **Context Integration**: Uses story context and learning progression
- **Fallback Strategy**: Falls back to constraint enforcement if LLM fails

### 4. CLI Management Layer

#### 4.1 Command Structure (`cli/`)

**Architecture**:
```
cli/
├── __init__.py
├── utils.py              # Shared utilities and formatting
├── srs_commands.py       # Database management (populate, stats, clean)
├── vocab_commands.py     # Extraction commands
└── enforcement_commands.py # Testing and rule display
```

**Design Patterns**:
- **Command Pattern**: Each CLI command is a separate handler function
- **Dependency Injection**: Components passed to command handlers
- **Error Handling**: Comprehensive error reporting with actionable messages
- **Progress Reporting**: Visual progress indicators for long operations

#### 4.2 Shared Utilities (`cli/utils.py`)

**Common Functions**:
```python
def print_success(message: str) -> None:
    """Consistent success message formatting"""
    
def format_stats_table(stats: Dict[str, Any]) -> str:
    """Format database statistics as readable table"""
    
def extract_day_number(filename: Path) -> int:
    """Parse day numbers from various filename formats"""
    
def show_progress(current: int, total: int, message: str) -> None:
    """Display progress bar for long operations"""
```

## Data Management Patterns

### 1. Vocabulary Lifecycle

```
Story Content → Extraction → Validation → Storage → Retrieval → Enforcement
     ↑                                                              ↓
     └─────────────── Quality Feedback Loop ←──────────────────────┘
```

**Stages**:
1. **Extraction**: CollocationExtractor processes story files
2. **Validation**: Noise filtering and quality checks
3. **Storage**: SRSDatabase with metadata and relationships
4. **Retrieval**: Query interface for enforcement systems
5. **Enforcement**: Application of vocabulary rules in content generation
6. **Feedback**: Violation tracking informs vocabulary quality

### 2. Storage Strategy

**Dual Storage Approach**:
- **Primary Database**: SQLite for persistent, queryable storage
- **Legacy JSON**: Maintained for backward compatibility
- **Migration Path**: Automatic upgrade from JSON to database

**Data Normalization**:
- **Deduplication**: Unique constraints prevent duplicate entries
- **Standardization**: Consistent text formatting and metadata
- **Relationships**: Foreign key relationships between violations and vocabulary

### 3. Quality Assurance

**Multi-Layer Filtering**:
```python
# Layer 1: Basic validation
if len(collocation) <= 2 or '\n' in collocation:
    continue

# Layer 2: Noise detection
noise_indicators = ['tagalog-female', '[narrator', ...]
if any(indicator in collocation.lower() for indicator in noise_indicators):
    continue

# Layer 3: Pedagogical value
if _is_common_english_word(collocation) and not _has_filipino_elements(collocation):
    continue
```

## Performance Characteristics

### 1. Extraction Performance

**Bottlenecks**:
- spaCy model loading: ~2-3 seconds initial startup
- Text processing: ~100ms per 1000 words
- Database writes: ~10ms per collocation

**Optimizations**:
- Batch database operations
- Model reuse across extractions
- Progressive filtering to reduce processing

### 2. Database Performance

**Query Patterns**:
```sql
-- Fast lookups (indexed)
SELECT * FROM collocations WHERE text = ?

-- Review scheduling (indexed)
SELECT * FROM collocations WHERE next_review_day <= ? ORDER BY stability

-- Statistics queries (full table scan)
SELECT COUNT(*), AVG(review_count) FROM collocations
```

**Scaling Considerations**:
- SQLite suitable for <100K vocabulary entries
- Indexes on text and review_day columns
- WAL mode for concurrent read access

### 3. Enforcement Performance

**Rule Application**:
- Constraint enforcement: O(n×m) where n=content length, m=rules
- LLM enforcement: Network latency dependent (~500-2000ms)
- Caching: In-memory rule dictionary for fast lookups

## Integration Points

### 1. With Existing Story Generation

```python
# Story generation workflow integration
story_generator = StoryGenerator()
content = story_generator.generate_day_with_srs(day=16, strategy=ContentStrategy.DEEPER)

# Automatic vocabulary extraction
extractor = CollocationExtractor()
collocations = extractor.extract_collocations(content)

# SRS database update
db = SRSDatabase()
for collocation in collocations:
    db.add_collocation(collocation, day=16, ...)
```

### 2. With Validation Pipeline

```python
# Validation workflow integration
from srs_debug_analyzer import SRSDebugAnalyzer

analyzer = SRSDebugAnalyzer()
results = analyzer.validate_against_expected(
    day=16,
    validation_file="validation_datasets/day16_comprehensive_validation.json"
)
```

### 3. With CLI Interface

```python
# Main CLI integration
from cli.srs_commands import add_srs_commands
from cli.vocab_commands import add_vocab_commands
from cli.enforcement_commands import add_enforcement_commands

# Command registration
subparsers = parser.add_subparsers()
add_srs_commands(subparsers)
add_vocab_commands(subparsers)
add_enforcement_commands(subparsers)
```

## Error Handling Strategy

### 1. Graceful Degradation

**Component Failures**:
- **spaCy Model Missing**: Fallback to basic string processing
- **Database Locked**: Retry with exponential backoff
- **LLM Unavailable**: Use constraint enforcement only
- **File Access**: Continue processing available files

### 2. User Error Recovery

**Common Scenarios**:
- **Invalid Day Numbers**: Clear error messages with valid range
- **Missing Files**: List available files and suggest corrections
- **Database Corruption**: Automatic backup and recovery suggestions
- **Permission Issues**: Clear instructions for resolution

### 3. Data Integrity

**Protection Mechanisms**:
- **Transaction Rollback**: Atomic operations with SQLite transactions
- **Validation Checks**: Schema validation before database writes
- **Backup Creation**: Automatic backups before destructive operations
- **Corruption Detection**: Database integrity checks and repair

## Development and Testing

### 1. Component Testing

**Test Categories**:
- **Unit Tests**: Individual component functionality
- **Integration Tests**: Cross-component workflows
- **End-to-End Tests**: Full pipeline validation
- **Performance Tests**: Load testing and benchmarking

### 2. Mock Infrastructure

**Mock Components**:
```python
# MockLLM for consistent testing
class MockLLM:
    def generate_response(self, prompt: str) -> str:
        return self._get_cached_response(prompt)

# Test database with in-memory SQLite
test_db = SRSDatabase(":memory:")
```

### 3. Continuous Integration

**Validation Pipeline**:
1. **Code Quality**: Linting and type checking
2. **Unit Tests**: Component-level validation
3. **Integration Tests**: Workflow validation
4. **Documentation**: Automated documentation generation
5. **Performance Regression**: Benchmark comparison

## Future Architecture Considerations

### 1. Scalability

**Potential Improvements**:
- **Distributed Processing**: Parallel extraction across multiple workers
- **Caching Layer**: Redis for frequently accessed vocabulary
- **Database Sharding**: Partition by day or vocabulary category
- **API Interface**: REST API for remote vocabulary management

### 2. Intelligence Enhancement

**ML/AI Integration**:
- **Custom spaCy Models**: Filipino-specific NLP models
- **Learning Analytics**: Vocabulary difficulty prediction
- **Adaptive Enforcement**: Dynamic rule adjustment based on user progress
- **Quality Scoring**: Automatic pedagogical value assessment

### 3. User Experience

**Interface Improvements**:
- **Web Dashboard**: Visual vocabulary management interface
- **Real-time Updates**: Live progress monitoring
- **Collaborative Features**: Multi-user vocabulary curation
- **Mobile Support**: Cross-platform vocabulary management