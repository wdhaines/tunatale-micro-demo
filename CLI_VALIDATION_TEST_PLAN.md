# Manual CLI Validation Test Plan

**CLI Cleanup Refactor Validation** - Complete test sequence to verify all functionality after removing 7 legacy commands and unifying MockLLM API.

## 🧪 **Phase 1: Test with Existing Data (Safe)**

### **1. View & Strategy Tests**
```bash
# Test 1: View existing curriculum
./venv/bin/python main.py view curriculum

# Test 2: Generate story for existing day with BALANCED strategy
./venv/bin/python main.py generate-day 6 --strategy=balanced

# Test 3: Generate DEEPER strategy story (🚨 KEY TEST for prompt separation)
./venv/bin/python main.py generate-day 7 --strategy=deeper --source-day=6

# Test 4: Generate WIDER strategy story  
./venv/bin/python main.py generate-day 8 --strategy=wider --source-day=6
```

### **2. Analysis Tests**
```bash
# Test 5: Basic vocabulary analysis
./venv/bin/python main.py analyze --day 1

# Test 6: Quality analysis (Phase 3 feature)
./venv/bin/python main.py analyze --day 1 --quality

# Test 7: Trip readiness analysis (Phase 3 feature)
./venv/bin/python main.py analyze --day 1 --trip-readiness

# Test 8: Text analysis
./venv/bin/python main.py analyze "Kumusta ka? Salamat sa pagtulong."
```

### **3. SRS & Collocation Testing**
```bash
# Test 9: Show day collocations (replaces old extract)
./venv/bin/python main.py show-day-collocations 1

# Test 10: Show SRS status
./venv/bin/python main.py show-srs-status 1

# Test 11: Debug generation (SRS integration)
./venv/bin/python main.py debug-generation 1
```

### **4. View Commands**
```bash
# Test 12: View collocations
./venv/bin/python main.py view collocations

# Test 13: View SRS progress
./venv/bin/python main.py view progress
```

## 🧪 **Phase 2: Safe New Curriculum Generation**

### **5. New Curriculum Tests (Safe - Won't Overwrite)**
```bash
# Test 14: Generate safe test curriculum 
./venv/bin/python main.py generate "Filipino validation test" --days 3 --cefr-level A2 --output instance/data/curricula/validation_test.json

# Test 15: Continue workflow with new curriculum
./venv/bin/python main.py continue
```

## 🎯 **Key Validation Points**

### **MockLLM System/Day Prompt Separation** 🚨 **CRITICAL**
- **MUST SEE**: All story generation should display **BOTH** system prompt and day-specific prompt
- **Verify**: DEEPER/WIDER strategies show enhanced prompts  
- **Confirm**: No single-prompt fallback occurs (this was the original bug)

### **Smart Filename Logic**  
- **BALANCED**: `story_dayX_balanced_[topic].txt`
- **DEEPER**: `story_dayX_deeper_version_[topic].txt`  
- **WIDER**: `story_dayX_wider_version_[topic].txt`

### **CLI Command Cleanup**
- **Removed commands** should NOT appear: `extract`, `enhance`, `recommend`, `validate`, `strategy`, `story`, `extend`
- **Remaining 6 commands** should work without errors: `generate`, `view`, `continue`, `generate-day`, `analyze`, `show-day-collocations`, `show-srs-status`, `debug-generation`
- **Help text** should be clean and accurate

### **SRS Integration**
- Collocations properly tracked across strategy generations
- Review collocations appear in new stories when appropriate  
- Debug tools show clear SRS vs generated content comparison

## 📋 **Expected Results Summary**

Each test should demonstrate:
- ✅ **Clean execution** - No crashes or errors
- ✅ **Prompt separation** - System + Day prompts visible in MockLLM output
- ✅ **File generation** - Appropriate files created with smart naming
- ✅ **SRS updates** - Collocation data updates correctly
- ✅ **Strategy differences** - Observable content variations between strategies
- ✅ **Analysis insights** - Tools provide meaningful vocabulary/quality data

## 🔍 **Troubleshooting Guide**

### If MockLLM shows single prompt instead of system + day:
- **Problem**: Regression in chat_response() implementation
- **Check**: story_generator.py methods using chat_response() correctly

### If filename patterns are wrong:
- **Problem**: Smart filename logic not working
- **Check**: generate-day command filename generation

### If commands crash:
- **Problem**: Missing handler or import issue
- **Check**: main.py command registration

### If SRS data seems wrong:
- **Problem**: SRS integration broken
- **Check**: show-srs-status and debug-generation output

---

**🎯 Success Criteria**: All 17 tests pass with expected behaviors, especially MockLLM prompt separation working correctly across all generation modes.