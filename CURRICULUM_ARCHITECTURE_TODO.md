# Curriculum Architecture Improvement TODO

## Current Problem: Unscalable Curriculum Selection

The current curriculum system has a fundamental scalability issue:

### Current Implementation
```python
def _find_curriculum_file(self) -> Optional[Path]:
    """Find the most recent curriculum file."""
    curriculum_files = list(curricula_dir.glob('curriculum*.json'))
    # ❌ PROBLEM: Selects by modification time, not user intent
    return max(curriculum_files, key=lambda p: p.stat().st_mtime)
```

### Issues
1. **No explicit curriculum selection** - Users can't choose which curriculum to work with
2. **"Most recent" heuristic fails** - Touching files accidentally changes active curriculum
3. **Single curriculum assumption** - All commands assume one active curriculum
4. **No curriculum management** - No way to list, switch, or organize curricula

### Impact on User Experience
- `view curriculum` shows random curriculum based on file timestamps
- `generate-day X` might work on wrong curriculum
- No way to maintain multiple learning tracks (e.g., Filipino + Spanish)
- Testing/development creates confusing curriculum conflicts

## Proposed Solution: Parameterized Curriculum System

### 1. CLI Parameter Support
```bash
# Explicit curriculum selection
./venv/bin/python main.py view curriculum --curriculum=el-nido
./venv/bin/python main.py generate-day 5 --curriculum=spanish-basics
./venv/bin/python main.py continue --curriculum=filipino-advanced

# File-based selection
./venv/bin/python main.py view curriculum --curriculum-file=instance/data/curricula/el_nido.json
```

### 2. Configuration-Based Defaults
```json
// config/settings.json
{
  "default_curriculum": "el-nido",
  "curricula": {
    "el-nido": "instance/data/curricula/curriculum.json",
    "spanish": "instance/data/curricula/spanish_basics.json",
    "test": "instance/data/curricula/test_curriculum.json"
  }
}
```

### 3. Curriculum Management Commands
```bash
# List available curricula
./venv/bin/python main.py curriculum list

# Set default curriculum
./venv/bin/python main.py curriculum set-default el-nido

# Create new curriculum with proper naming
./venv/bin/python main.py generate "Filipino for El Nido" --curriculum-name=el-nido-v2
```

### 4. Backward Compatibility
- If no `--curriculum` specified, use configured default
- If no default configured, fall back to current "most recent" logic
- Existing curriculum files continue to work

## Implementation Plan

### Phase 1: Add CLI Parameters
- Add `--curriculum` and `--curriculum-file` arguments to relevant commands
- Update `_find_curriculum_file()` to accept curriculum identifier
- Maintain backward compatibility

### Phase 2: Configuration System
- Add curriculum configuration file support
- Implement curriculum registry/lookup
- Add validation for curriculum references

### Phase 3: Management Commands
- Add `curriculum` command group for management
- Implement listing, switching, validation
- Add curriculum metadata support

### Phase 4: Enhanced Features
- Curriculum templates and inheritance
- Multi-language curriculum support
- Curriculum versioning and backup

## Files to Update
- `main.py` - CLI argument parsing and curriculum selection
- `config.py` - Configuration management
- `curriculum_service.py` - Curriculum loading/management logic
- Documentation and help text

## Additional Issue: Dual Curriculum Format Support

### Current Problem: Inconsistent Curriculum Formats
The system currently supports two different curriculum formats, leading to inconsistent user experience:

```python
# Legacy format (shows raw JSON dump)
if 'content' in curriculum:
    print(curriculum['content'])

# New structured format (shows clean formatted list)  
elif 'days' in curriculum:
    print(f"Target Language: {curriculum.get('target_language')}")
    # ... formatted display
```

### Issues with Dual Format
1. **Inconsistent UX** - Same command shows different output formats
2. **Code complexity** - Dual format handling in multiple places
3. **Legacy baggage** - Maintaining deprecated `content` field format
4. **Confusion** - Users see raw JSON vs formatted output unpredictably

### Solution: Standardize on `days` Array Format
The structured `days` format is superior because:
- **Better UX**: Clean, readable output format
- **More structured**: Proper day/title/focus organization
- **Extensible**: Easy to add new fields per day
- **Consistent**: Same format across all curricula

### Implementation Tasks
1. **Remove legacy support**: Delete `content` field handling from `_view_curriculum()`
2. **Convert existing curricula**: Migrate any legacy format curricula to `days` array
3. **Update generation**: Ensure all curriculum generation only produces `days` format
4. **Clean up code**: Remove dual-format handling throughout codebase
5. **Add validation**: Ensure all curricula follow consistent schema

### Files to Update
- `main.py` - Remove `content` field handling in `_view_curriculum()`
- `curriculum_service.py` - Remove legacy format support
- Test curricula - Convert to standard format
- Validation logic - Enforce single format

## Additional Issue: WIDER Strategy Prompt Development Needed

### Current Status
The WIDER strategy is implemented but requires significant prompt engineering work to be effective.

### Issues with Current WIDER Implementation
1. **Prompt Quality**: `story_prompt_wider.txt` may not provide clear guidance for scenario expansion
2. **Context Preservation**: Need better instructions to maintain difficulty level while expanding scenarios
3. **Content Variety**: Ensuring truly different scenarios vs superficial variations
4. **Cultural Authenticity**: Keeping expanded scenarios realistic and relevant to El Nido context
5. **Vocabulary Management**: Proper handling of vocabulary expansion in new scenarios

### Recommended Prompt Engineering Tasks
1. **Analyze Current WIDER Prompt**: Review `prompts/story_prompt_wider.txt` effectiveness
2. **Define WIDER Strategy Goals**: Clarify what "wider" means (new scenarios, contexts, situations)
3. **Create Scenario Templates**: Develop templates for different types of scenario expansion
4. **Test Scenario Quality**: Validate that expanded scenarios maintain learning objectives
5. **Cultural Validation**: Ensure new scenarios fit El Nido tourism context appropriately

### Implementation Priority
- **Priority**: Medium - Important for content strategy completeness
- **Complexity**: High - Requires careful prompt engineering and testing
- **Dependencies**: Content strategy framework completion

## Priority: Medium-Low
This is an architectural improvement that would greatly enhance usability for multi-curriculum workflows, but doesn't block current single-curriculum usage patterns.

---
*Created: 2025-08-16 - CLI Cleanup Refactor Phase*  
*Updated: 2025-08-16 - Added curriculum format standardization*
*Status: TODO - Architectural Improvement*