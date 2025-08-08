# TunaTale Go Wider vs Go Deeper Implementation Plan

## Project Overview
TunaTale is an audio-first Filipino language learning system focused on El Nido trip preparation. This plan implements a "Go Wider vs Go Deeper" content generation framework allowing users to either extend curriculum with new scenarios (wider) or enhance existing scenarios with sophisticated language (deeper).

## Current System Analysis

### Current CLI Commands
- `generate <goal>` - Create initial curriculum
- `extract` - Extract collocations from curriculum  
- `extend <days>` - Extend curriculum to N total days
- `generate-day <day>` - Generate story for specific day
- `continue` - Generate next day automatically
- `view`, `analyze`, `progress` - Utility commands

### Current Architecture
- **Curriculum**: JSON-based daily lesson plans with collocations
- **Stories**: Structured audio lessons (Key Phrases + Natural Speed + Slow Speed + Translated)
- **SRS**: Spaced repetition tracking for collocations with review scheduling
- **File Storage**: Instance-based with organized directories

### File Organization (Updated)
```
instance/data/
├── curricula/              # All curriculum files
│   ├── curriculum.json     # Main curriculum
│   ├── my_curriculum.json  # User-generated curricula
│   └── *.json             # Other curriculum variants
├── collocations.json       # Clean collocation data
├── curriculum.json         # Legacy curriculum (instance level)
├── stories/               # Generated story content
└── srs/                   # SRS tracking data
```
**Note**: Curriculum files should ONLY exist in `instance/data/` directories, never in project root.

### Current Limitations
1. **Data Quality Issues**: Broken collocation data with embedded syllables
2. **SRS Problems**: Review collocations return voice tags instead of phrases
3. **Format Inconsistencies**: Mixed dict/list structures in curriculum
4. **No Content Strategy**: Single balanced approach for all learners
5. **Limited File Organization**: No versioning or difficulty variants

## Implementation Plan

### PHASE 1: Critical Cleanup (Priority: HIGH)

#### 1.1 Fix Data Quality Issues
**Problem**: Collocation data contains embedded syllable breakdowns
```json
"ito po\npo\nito\nto\ni\nito\nito po\nito po"
```

**Solution**: 
- Create `cleanup_collocations.py` script to separate actual collocations from syllable data
- Update curriculum generation to properly separate content types
- Add validation to prevent mixed data formats

#### 1.2 Fix SRS Tracking Logic  
**Problem**: SRS returns nonsensical "review collocations" like voice tags
```
Review collocations: "**mango shake, they, the waiter, asks, tagalog-female-1"
```

**Solution**:
- Debug `SRSTracker.get_due_collocations()` method
- Fix collocation extraction from generated stories
- Ensure only valid phrases are stored in SRS

#### 1.3 Standardize Curriculum Format
**Problem**: Format inconsistencies between dict and list structures

**Solution**:
- Decide on list-based format (aligns with `CurriculumDay` dataclass)
- Update all loading methods to expect consistent format
- Migration script for existing curricula

#### 1.4 Clean Up Temporary Files
**Files to Remove**:
- `fix_curriculum.py` (temporary script)
- Backup files (`curriculum_processed.json.backup`)
- Unused mock responses

### PHASE 2: Architecture Enhancement (Priority: MEDIUM)

#### 2.1 Content Generation Strategy Framework

**New Enums**:
```python
class ContentStrategy(Enum):
    WIDER = "wider"     # New scenarios, same difficulty
    DEEPER = "deeper"   # Same scenarios, advanced language
    BALANCED = "balanced"  # Current approach

class DifficultyLevel(Enum):
    BASIC = "basic"         # Current level
    INTERMEDIATE = "intermediate"  # Enhanced Filipino
    ADVANCED = "advanced"   # Native-level expressions
```

#### 2.2 Enhanced File Organization
**New Directory Structure**:
```
instance/data/
├── curricula/
│   ├── base/              # Original curricula
│   ├── wider/             # Extended scenarios
│   └── deeper/            # Enhanced difficulty versions
├── stories/
│   ├── base/              # Original stories (days 1-8)
│   ├── wider/             # New scenarios (days 9+)
│   └── deeper/            # Enhanced versions (day-1-advanced, etc.)
├── srs/
│   ├── main.json          # Primary SRS tracking
│   └── strategy_{name}.json  # Strategy-specific tracking
```

#### 2.3 Enhanced SRS Architecture
**Strategy-Specific Parameters**:
```python
STRATEGY_CONFIGS = {
    ContentStrategy.WIDER: {
        'max_new_collocations': 8,
        'min_review_collocations': 2,  
        'review_interval_multiplier': 1.5,
        'difficulty_preference': 'expand_contexts'
    },
    ContentStrategy.DEEPER: {
        'max_new_collocations': 3,
        'min_review_collocations': 7,
        'review_interval_multiplier': 0.8,  
        'difficulty_preference': 'increase_complexity'
    }
}
```

### PHASE 3: CLI Enhancement (Priority: MEDIUM)

#### 3.1 New CLI Commands
```bash
# Go Wider - Generate new scenarios
tunatale generate --mode=wider --from-day=7 --scenarios=3
tunatale generate-day 9 --mode=wider --source-day=7

# Go Deeper - Enhance existing content  
tunatale generate --mode=deeper --day=7 --difficulty=advanced
tunatale enhance --day=7 --target=intermediate

# Strategy Management
tunatale strategy --set=wider --max-new=8 --min-review=2
tunatale analyze --strategy=deeper --vocabulary-complexity

# SRS Management
tunatale srs --strategy=wider --update-from-day=9
tunatale srs --review-due --strategy=deeper
```

#### 3.2 Enhanced Story Generation Parameters
```python
@dataclass
class EnhancedStoryParams:
    # Existing params
    learning_objective: str
    language: str  
    cefr_level: Union[CEFRLevel, str]
    phase: int
    
    # New strategy params
    content_strategy: ContentStrategy = ContentStrategy.BALANCED
    difficulty_level: DifficultyLevel = DifficultyLevel.BASIC
    source_day: Optional[int] = None  # For "wider" mode
    complexity_target: Optional[str] = None  # For "deeper" mode
    
    # Enhanced SRS integration
    srs_strategy_config: Optional[Dict[str, Any]] = None
```

### PHASE 4: Content Generation Enhancement (Priority: HIGH)

#### 4.1 Enhanced Prompt Templates

**New Template: `story_prompt_deeper.txt`**
- Focus on replacing English with authentic Tagalog
- Cultural authenticity improvements
- Native speech patterns and expressions
- Advanced grammatical structures

**New Template: `story_prompt_wider.txt`**  
- Scenario expansion while maintaining difficulty
- Context variety (shopping, transportation, activities)
- Vocabulary reinforcement in new situations

#### 4.2 Content Strategy Implementation

**Wider Strategy Logic**:
```python
def generate_wider_content(self, source_day: int, new_day: int):
    # Extract successful patterns from source day
    source_data = self.curriculum.get_day(source_day)
    
    # Generate new scenario using same complexity
    new_context = self._expand_scenario(source_data.focus)
    
    # Maintain vocabulary level, change context
    params = self._create_wider_params(source_data, new_context)
    
    return self.generate_story(params)
```

**Deeper Strategy Logic**:
```python  
def generate_deeper_content(self, base_day: int, difficulty: DifficultyLevel):
    # Load base content
    base_data = self.curriculum.get_day(base_day)
    
    # Enhance language complexity
    enhanced_collocations = self._enhance_collocations(
        base_data.collocations, difficulty
    )
    
    # Generate sophisticated version
    params = self._create_deeper_params(base_data, enhanced_collocations)
    
    return self.generate_story(params)
```

### PHASE 5: SRS Integration (Priority: MEDIUM)

#### 5.1 Strategy-Aware SRS Tracking
```python
class StrategySRSTracker(SRSTracker):
    def get_due_collocations(self, day: int, strategy: ContentStrategy):
        config = STRATEGY_CONFIGS[strategy]
        
        return self._select_collocations(
            min_items=config['min_review_collocations'],
            max_items=config['max_review_collocations'],
            strategy=strategy
        )
        
    def update_review_intervals(self, strategy: ContentStrategy):
        multiplier = STRATEGY_CONFIGS[strategy]['review_interval_multiplier'] 
        # Apply strategy-specific interval adjustments
```

#### 5.2 Vocabulary Complexity Scoring
```python
class VocabularyComplexityAnalyzer:
    def score_complexity(self, collocation: str) -> float:
        # Length-based scoring
        # Grammatical complexity analysis  
        # Cultural context requirements
        # Frequency in native speech
        
    def recommend_strategy(self, learner_progress: Dict) -> ContentStrategy:
        # Analyze learner performance
        # Recommend wider vs deeper based on mastery
```

## Implementation Timeline

### Weekend 1: Critical Cleanup
- [ ] Fix collocation data quality issues
- [ ] Debug and fix SRS tracking logic
- [ ] Standardize curriculum format
- [ ] Clean up temporary files

### Weekend 2: Strategy Framework  
- [ ] Implement ContentStrategy enum and configs
- [ ] Create enhanced file organization
- [ ] Add basic strategy-aware content generation
- [ ] Test wider/deeper content generation

### Weekend 3: CLI Enhancement
- [ ] Add new CLI commands for strategies
- [ ] Implement enhanced story parameters
- [ ] Add strategy configuration management
- [ ] Integration testing

### Weekend 4: Polish & Integration
- [ ] Enhanced prompt templates
- [ ] SRS strategy integration
- [ ] Vocabulary complexity analysis
- [ ] User experience testing

## Success Criteria

### Technical Goals
- [ ] Clean, validated collocation data (no embedded syllables)
- [ ] Working SRS that returns actual phrases for review
- [ ] Consistent curriculum format across all operations
- [ ] Strategy-aware content generation working

### User Experience Goals  
- [ ] Clear CLI commands for both strategies
- [ ] Intuitive file organization preserving originals
- [ ] Content quality maintained while scaling complexity
- [ ] SRS prevents vocabulary overload through smart scheduling

### Content Quality Goals
- [ ] "Wider" generates new scenarios maintaining difficulty
- [ ] "Deeper" enhances existing content with authentic Filipino
- [ ] Cultural authenticity preserved and enhanced
- [ ] Progressive difficulty scaling works correctly

## Risk Mitigation

### Data Integrity
- Always backup before major changes
- Validate data formats before processing
- Test with small datasets first

### User Experience  
- Maintain backward compatibility with existing commands
- Provide clear error messages and guidance
- Document all new features and workflows

### Content Quality
- Test generation with multiple scenarios
- Validate Filipino language authenticity
- Ensure dialogue remains natural and practical

This plan provides a concrete roadmap for implementing the "Go Wider vs Go Deeper" framework while addressing current system limitations and maintaining the audio-first Filipino learning focus.