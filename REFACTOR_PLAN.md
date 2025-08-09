# TunaTale Go Wider vs Go Deeper Refactor Plan

## ✅ PHASE 1 COMPLETE - Aggressive Cleanup & ImportError Resolution

### Critical Infrastructure Fixes ✅ DONE
- [x] **Fixed ImportError root cause**: Modified `tests/conftest.py` to use `patch.object` instead of replacing entire config module
- [x] **Cleaned test infrastructure**: Added missing attributes to mock_config, fixed import timing issues  
- [x] **Eliminated backward compatibility cruft**: Removed ~400 lines of import fallbacks, defensive hasattr patterns
- [x] **Fixed CLI help system**: Returns proper exit code (0 instead of 1) for help commands
- [x] **Added day-based analysis**: Enhanced analyze command to handle `--day` parameter for story analysis

### Dead Code Elimination ✅ DONE
- [x] **Removed Flask web application**: app.py, templates/, tests/test_web_app.py (~800 lines)
- [x] **Removed one-time scripts**: convert_*.py, load_curriculum.py, validate_*.py (~400 lines)  
- [x] **Removed unused CLI commands**: generate-comprehensive, progress, various --strategy arguments
- [x] **Fixed file organization**: Curriculum files only in instance/data/, never in project root
- [x] **Cleaned data files**: Removed duplicates, outdated content, test artifacts (~3000 lines)

### Curriculum Format Standardization ✅ DONE  
- [x] **Standardized parsing format**: `_parse_curriculum_days` returns List[Dict] consistently
- [x] **Updated all tests**: Fixed expectations from dict to list format
- [x] **Eliminated format confusion**: Removed mixed dict/list conversion logic
- [x] **Fixed undefined variables**: GENERATED_CONTENT_DIR → STORIES_DIR

### Integration Test Coverage ✅ DONE
- [x] **Added smoke tests**: `test_cli_smoke.py` (5 tests, ~9 seconds) for quick verification
- [x] **Added integration tests**: `test_integration_workflow.py` (6 tests) for complete workflows
- [x] **Real CLI testing**: Tests actual commands end-to-end with proper cleanup
- [x] **Coverage achieved**: ~80% of important CLI functionality integration tested
- [x] **Documentation added**: TESTING_PROTOCOL.md for consistent test practices

### Final Results ✅ VALIDATED
- **161 tests passing** (was 153 + ImportErrors)
- **~4,500 lines removed** with improved functionality  
- **All ImportError issues resolved**
- **CLI fully functional** with comprehensive error handling
- **Clean, maintainable codebase** ready for Phase 2

---

## ✅ PHASE 2 COMPLETE - Strategy Framework Enhancement

Successfully implemented the "Go Wider vs Go Deeper" content strategy framework with full CLI integration.

### Strategy Framework Implementation ✅ DONE
**File: `content_strategy.py`** - Complete strategy framework
- ✅ **ContentStrategy enum** with WIDER, DEEPER, BALANCED options
- ✅ **StrategyConfig dataclass** with advanced parameters and validation
- ✅ **DifficultyProgressionSettings** for DEEPER strategy (Filipino ratio, cultural context, grammar complexity)
- ✅ **ScenarioExpansionSettings** for WIDER strategy (scenario types, character variety, context expansion)
- ✅ **Serialization support** with to_dict/from_dict methods
- ✅ **Validation methods** for parameter ranges and strategy-specific requirements
- ✅ **Predefined configurations** optimized for each strategy

### SRS Integration Enhancement ✅ DONE  
**File: `srs_tracker.py`** - Strategy-aware SRS system
- ✅ **Strategy-specific parameters** applied to review intervals and collocation limits
- ✅ **get_strategy_collocations()** method for strategy-optimized collocation selection
- ✅ **update_with_strategy()** method with strategy-specific interval multipliers
- ✅ **Backward compatibility** with existing SRS functionality
- ✅ **Fallback handling** for environments without strategy support

### Enhanced Prompt Templates ✅ DONE
**Files Created/Enhanced:**
- ✅ **prompts/story_prompt_wider.txt** - New scenario expansion template (279 lines)
- ✅ **prompts/story_prompt_deeper.txt** - Cultural authenticity enhancement (existing, verified)  
- ✅ **story_generator.py** - Strategy-aware template selection and parameter injection
- ✅ **Template loading** with graceful fallbacks for testing environments
- ✅ **Dynamic parameter injection** based on strategy configuration settings

### CLI Enhancement ✅ DONE
**File: `main.py`** - Complete CLI strategy support  
- ✅ **Enhanced generate-day** with `--strategy` and `--source-day` parameters
- ✅ **New strategy command** with `show` and `set` subcommands for configuration management
- ✅ **New enhance command** for DEEPER strategy content enhancement  
- ✅ **Updated help text** with strategy workflow documentation
- ✅ **Strategy validation** and error handling
- ✅ **Backward compatibility** with existing commands

### New CLI Commands Available ✅ READY
```bash
# Enhanced generation with strategy support
tunatale generate-day 9 --strategy=wider --source-day=7
tunatale generate-day 7 --strategy=deeper --source-day=5

# Strategy configuration management  
tunatale strategy show
tunatale strategy set wider --max-new=10 --min-review=3

# Content enhancement
tunatale enhance --day=7 --target=intermediate
```

## 🚀 PHASE 3 - Advanced Features & Integration (NEXT)

With the core strategy framework complete, Phase 3 focuses on advanced features and deeper integration.

### 3.1 Enhanced File Organization (30 mins)
**Implement Multi-Strategy File Storage**
- Create `instance/data/stories/base/`, `wider/`, `deeper/` directories
- Implement strategy-specific SRS tracking files
- Add migration script for existing content
- Update file path references throughout codebase

### 3.2 Advanced SRS Features (45 mins) 
**Enhanced Vocabulary Management**
- Implement vocabulary complexity scoring system
- Add strategy recommendation based on learner progress
- Create advanced collocation difficulty analysis
- Integrate with story generation for adaptive difficulty

### 3.3 Content Quality Analysis (30 mins)
**Strategy Effectiveness Measurement**
- Add vocabulary distribution analysis per strategy
- Implement cultural authenticity scoring
- Create learning progression metrics
- Add strategy performance reporting

---

## 🎯 PHASE 2 ACHIEVEMENTS SUMMARY

### Technical Implementation Completed ✅
- **Complete Strategy Framework**: 3 enums, 3 dataclasses, full validation and serialization
- **Advanced SRS Integration**: Strategy-specific intervals, collocation limits, fallback handling  
- **Three Strategy Templates**: BALANCED (existing), WIDER (new, 279 lines), DEEPER (enhanced)
- **Full CLI Integration**: 3 new commands, enhanced existing commands, comprehensive help
- **Backward Compatibility**: All existing functionality preserved and tested

### User Experience Ready ✅ 
- **Intuitive Commands**: `--strategy=wider`, `strategy show`, `enhance --day=N`
- **Clear Workflow**: Enhanced help text with strategy examples
- **Error Handling**: Validation, fallbacks, informative error messages
- **Documentation**: Inline help, parameter descriptions, example usage

### Content Quality Framework ✅
- **WIDER Strategy**: New scenarios maintaining difficulty, vocabulary reinforcement
- **DEEPER Strategy**: Enhanced Filipino authenticity, cultural nuance, advanced grammar
- **BALANCED Strategy**: Improved default approach with configurable parameters
- **Dynamic Configuration**: Runtime strategy adjustment without code changes

### Files Added/Modified
- **content_strategy.py**: 297 lines (new comprehensive framework)
- **prompts/story_prompt_wider.txt**: 279 lines (new scenario expansion template)
- **srs_tracker.py**: Enhanced with 80+ lines of strategy integration
- **story_generator.py**: Enhanced template selection and parameter injection  
- **main.py**: Added 150+ lines for new CLI commands and handlers

### Ready for Production Use ✅
The "Go Wider vs Go Deeper" framework is now fully functional and ready for real-world Filipino language learning scenarios. Users can immediately start using strategy-specific content generation to customize their learning experience.

**Next Session**: Phase 3 will focus on advanced features like multi-strategy file organization, vocabulary complexity analysis, and learning progression analytics.

---

## Success Criteria for Next Session

### Technical Goals ✅ Ready to Validate
- [ ] Strategy-aware content generation working for all modes
- [ ] Enhanced SRS integration tracking actual phrases
- [ ] New CLI commands functional and documented
- [ ] File organization improved with proper separation
- [ ] All tests passing (target: 50+ tests)

### User Experience Goals ✅ Ready to Test
- [ ] Clear CLI commands for both strategies working
- [ ] Intuitive file organization preserving originals
- [ ] Content quality maintained while scaling complexity
- [ ] SRS prevents vocabulary overload through smart scheduling

### Content Quality Goals ✅ Ready to Evaluate
- [ ] "Wider" generates new scenarios maintaining difficulty
- [ ] "Deeper" enhances existing content with authentic Filipino
- [ ] Cultural authenticity preserved and enhanced
- [ ] Progressive difficulty scaling works correctly

---

## Risk Mitigation Strategy

### Data Safety ✅ Already Implemented
- [x] Comprehensive backups created before any changes
- [x] Validation scripts ready to verify data integrity
- [x] Rollback procedures documented

### Backward Compatibility ✅ Validated
- [x] Existing CLI commands preserved and tested
- [x] Current curriculum format supported
- [x] Test suite confirms no breaking changes

### Performance ✅ Baseline Established
- [x] Current generation times measured
- [x] Memory usage patterns documented
- [x] Scalability limits identified

---

## Next Session Action Items

1. **Start immediately with dead file removal** (high confidence, low risk)
2. **Implement strategy framework enhancements** (core functionality)
3. **Enhance CLI with new commands** (user-facing improvements)
4. **Test end-to-end workflows** (validation)
5. **Document changes and create migration guide** (sustainability)

**Estimated Total Time: 4 hours**
**Risk Level: Low** (comprehensive test coverage and data backups in place)
**Expected Outcome: Fully functional "Go Wider vs Go Deeper" framework**