# CLI Testing Plan: Strategy Commands & Analysis Features

## Current CLI Testing Gap Analysis

### What's Already Tested ✅
- Basic CLI help functionality (`test_main.py`)
- Generate command argument validation
- Legacy command functionality (`test_cli.py`)

### Critical Missing Tests 🚨

## High Priority CLI Tests Needed

### 1. Strategy Generation Commands
**Target**: `generate-day --strategy=wider/deeper` functionality
- Test WIDER strategy CLI: `generate-day 11 --strategy=wider`
- Test DEEPER strategy CLI: `generate-day 11 --strategy=deeper --source-day=6` 
- Test strategy parameter validation (invalid strategy names)
- Test source-day parameter handling
- Test curriculum extension through CLI
- Test error handling for missing curriculum/invalid days

### 2. Analysis Commands Testing
**Target**: New analysis features that lack comprehensive CLI tests
- `show-day-collocations <day>` - Extract collocations from specific days
- `show-srs-status <day>` - View SRS status for specific days  
- `debug-generation <day>` - Debug SRS vs generated content differences
- `analyze` command with various options

### 3. View Command Enhancements
**Target**: Recently updated view functionality
- `view curriculum` - Display curriculum overview
- `view collocations` - Show collocation data
- `view story --day=X` - Display specific day stories

### 4. Integration & Error Handling
**Target**: Real-world usage scenarios
- Test strategy chaining workflows via CLI
- Test invalid day numbers (beyond curriculum range)
- Test missing files/corrupted data scenarios
- Test cache clearing functionality
- Test help text for all new commands

## Specific Test Categories

### A. Strategy Generation CLI Tests
```bash
# Commands to test:
./venv/bin/python main.py generate-day 11 --strategy=wider
./venv/bin/python main.py generate-day 11 --strategy=deeper --source-day=6
./venv/bin/python main.py generate-day 15 --strategy=balanced
```

### B. Analysis Commands CLI Tests  
```bash
# Commands to test:
./venv/bin/python main.py show-day-collocations 6
./venv/bin/python main.py show-srs-status 8
./venv/bin/python main.py debug-generation 9
./venv/bin/python main.py analyze --day=5
```

### C. Enhanced View Commands
```bash
# Commands to test:
./venv/bin/python main.py view curriculum
./venv/bin/python main.py view collocations
./venv/bin/python main.py view story --day=6
```

## Implementation Approach

1. **Create Strategy CLI Test Suite** - New test file `test_strategy_cli.py`
2. **Enhance Analysis CLI Tests** - Extend `test_analyze_command.py`
3. **Add Integration CLI Tests** - Real workflow testing with actual files
4. **Error Handling Tests** - Edge cases and failure scenarios

## Expected Outcome
- Comprehensive CLI test coverage for all new strategy and analysis features
- Confidence in CLI robustness for production use
- Documentation of CLI behavior through tests
- Catch any CLI bugs before they reach users

---

**Status**: Plan saved for future implementation after fixing remaining 2 test failures
**Next Step**: Fix the 2 failing tests in strategy curriculum extension suite