# Testing Protocol for Code Changes

## Always Run Real Tests

When making code changes that could affect imports, tests, or functionality:

1. **Use the existing virtual environment**: `source venv/bin/activate`
2. **Run the specific failing test first**: 
   ```bash
   source venv/bin/activate && python -m pytest tests/specific_test.py::specific_test -v
   ```
3. **Run a broader test suite to check for regressions**:
   ```bash
   source venv/bin/activate && python -m pytest tests/ -x
   ```
4. **Don't just theorize or create debug scripts - actually run the tests!**

## Current Environment Setup

- Virtual environment: `venv/` (Python 3.13.5, pytest-8.4.1)
- Run tests with: `source venv/bin/activate && python -m pytest`
- Root directory: `/Users/wdhaines/CascadeProjects/tunatale/micro-demo-0.1`

## Memory Note

**ALWAYS verify fixes by running real tests, not theoretical debugging!**