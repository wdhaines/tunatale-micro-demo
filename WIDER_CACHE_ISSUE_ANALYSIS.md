# WIDER Strategy Cache Miss Issue - Root Cause Analysis

## Issue Description
When running `python main.py generate-day 15 --strategy=wider`, the MockLLM cache is never hit, while the DEEPER strategy works fine with caching.

## Root Cause Analysis

### Why WIDER Strategy Doesn't Hit Cache
The WIDER strategy generates different prompts each time due to dynamic content generation:

1. **`_analyze_curriculum_progression(curriculum)`** - Analyzes current curriculum state which may vary
2. **`_generate_new_scenario_focus(curriculum_analysis, target_day)`** - Depends on curriculum analysis results
3. **Dynamic learning objectives** - "Day 15: [dynamic_focus] - Building on curriculum foundation" 
4. **`_generate_progressive_collocations(curriculum_analysis, target_day)`** - Creates different advanced collocations based on analysis

### Why DEEPER Strategy Hits Cache
The DEEPER strategy uses static source day data:
- `source_data.title`, `source_data.focus`, `source_data.collocations`
- Learning objective: "DEEPER VERSION: {source_data.learning_objective} with enhanced Filipino authenticity"
- All parameters come from existing, unchanging curriculum data → consistent prompts → cache hits

### Technical Details

**MockLLM Caching Mechanism:**
- Cache key: MD5 hash of `user_prompt` in `chat_response()` method (`llm_mock.py:337`)
- Location: `llm_mock.py:21-25` (`_get_cache_path()`)

**WIDER Strategy Prompt Generation Flow:**
1. `story_generator.py:920` - `_analyze_curriculum_progression(curriculum)`
2. `story_generator.py:923` - `_generate_new_scenario_focus(curriculum_analysis, target_day)`
3. `story_generator.py:926` - `_generate_progressive_collocations(curriculum_analysis, target_day)`
4. `story_generator.py:932` - Dynamic learning objective creation
5. Result: Different prompts each time → cache misses

**DEEPER Strategy Prompt Generation Flow:**
1. `story_generator.py:843` - `curriculum.get_day(source_day)` (static data)
2. `story_generator.py:870` - Static learning objective based on source day
3. Result: Consistent prompts → cache hits

## Solution: Make Curriculum Analysis Deterministic

### Implementation Plan

1. **Make `_analyze_curriculum_progression()` deterministic:**
   - Sort curriculum data consistently
   - Use deterministic selection algorithms
   - Cache analysis results based on curriculum content hash

2. **Files to modify:**
   - `story_generator.py` lines 990-1011 (`_analyze_curriculum_progression`)
   - `story_generator.py` lines 1013-1031 (`_generate_new_scenario_focus`)
   - `story_generator.py` lines 1033-1051 (`_generate_progressive_collocations`)

3. **Specific changes needed:**
   ```python
   def _analyze_curriculum_progression(self, curriculum) -> Dict[str, Any]:
       """Analyze curriculum to understand difficulty progression and common themes."""
       # Make deterministic by sorting data
       analysis = {
           'total_days': len(curriculum.days),
           'common_themes': [],
           'vocabulary_progression': [],
           'complexity_level': curriculum.learner_level,
           'presentation_length': curriculum.presentation_length
       }
       
       # Sort days by day number for consistency
       sorted_days = sorted(curriculum.days, key=lambda d: d.day)
       
       # Extract themes deterministically
       for day in sorted_days:
           if hasattr(day, 'focus'):
               analysis['common_themes'].append(day.focus)
           if hasattr(day, 'collocations'):
               # Sort collocations for consistency
               sorted_collocations = sorted(day.collocations)
               analysis['vocabulary_progression'].extend(sorted_collocations[:3])
       
       # Remove duplicates while preserving sorted order
       analysis['common_themes'] = sorted(list(set(analysis['common_themes'])))
       analysis['vocabulary_progression'] = sorted(list(set(analysis['vocabulary_progression'])))
       
       return analysis
   ```

### Expected Outcome
After implementing these changes:
- WIDER strategy will generate consistent prompts for the same input
- MockLLM cache will work for both WIDER and DEEPER strategies
- No change in functionality, only deterministic behavior

## Status
- **Analysis:** Complete
- **Implementation:** Pending
- **Priority:** Stored for later implementation

## Files Referenced
- `/Users/wdhaines/CascadeProjects/tunatale/micro-demo-0.1/story_generator.py`
- `/Users/wdhaines/CascadeProjects/tunatale/micro-demo-0.1/llm_mock.py`
- `/Users/wdhaines/CascadeProjects/tunatale/micro-demo-0.1/prompts/story_prompt_wider.txt`
- `/Users/wdhaines/CascadeProjects/tunatale/micro-demo-0.1/prompts/story_prompt_deeper.txt`

---
*Analysis completed: 2025-01-24*
*Ready for implementation when prioritized*