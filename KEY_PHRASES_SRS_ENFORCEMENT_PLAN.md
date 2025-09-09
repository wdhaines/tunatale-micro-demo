# Plan: Implement Key Phrases SRS Enforcement to Prevent Teaching Already-Known Vocabulary

## **Core Problem**
Key Phrases section currently includes Tagalog collocations that the learner may already know well (high SRS stability), violating the pedagogical principle that Key Phrases should teach **new** vocabulary.

## **Solution Strategy: Post-Generation SRS Enforcement**
Extend the existing SRS enforcement system to check Key Phrases collocations against the SRS database and flag/replace high-stability items.

## **Implementation Approach**

### **1. Extend SRS Analysis Section**
Add Key Phrases analysis to the story-generated SRS analysis JSON:

```json
{
  "english_terms": [...existing...],
  "key_phrases_analysis": {
    "phrases": ["magkano po ito", "pwede po bang tawad", "salamat po"],
    "stability_threshold": 2.0
  }
}
```

### **2. Add Key Phrases SRS Checking**
New method in `SRSLLMEnforcer`:

```python
def _check_key_phrases_against_srs(self, phrases: List[str], stability_threshold: float = 2.0) -> Dict:
    """Check Key Phrases against SRS database for already-known collocations."""
    results = {
        "already_known": [],      # High stability - violation
        "reinforcement_ok": [],   # Medium stability - acceptable  
        "truly_new": []          # Not in SRS - ideal
    }
    
    for phrase in phrases:
        matches = self._search_srs_database(phrase, min_stability=0.0)
        if matches:
            best_match = max(matches, key=lambda x: x['stability'])
            if best_match['stability'] >= stability_threshold:
                results["already_known"].append({
                    "phrase": phrase,
                    "stability": best_match['stability']
                })
            # ... categorize other cases
        else:
            results["truly_new"].append(phrase)
    
    return results
```

### **3. Parse Key Phrases from Generated Content**
```python
def _extract_key_phrases(self, content: str) -> List[str]:
    """Extract Tagalog phrases from Key Phrases section."""
    # Find Key Phrases section
    # Extract [TAGALOG-FEMALE-1]: phrases (skip English translations)
    # Return clean Tagalog collocations
```

### **4. Integrate with Existing SRS Enforcement**
Extend `enforce_with_llm()` method:

```python
# After existing English enforcement:
key_phrases = self._extract_key_phrases(content) 
key_phrases_analysis = self._check_key_phrases_against_srs(key_phrases)

if key_phrases_analysis["already_known"]:
    # Log Key Phrases violations
    kp_violations = self._create_key_phrases_violations(key_phrases_analysis, day, context)
    violations.extend(kp_violations)
    
    # Store in database for debug visibility
    self._store_key_phrases_violations(kp_violations)
```

### **5. Violation Recording and Debug Integration**
- Store Key Phrases violations in `srs_violations` table with type `key_phrases_redundancy`
- Extend `debug-srs` command to show Key Phrases violations
- Provide clear messaging: "Known vocabulary appeared in Key Phrases section"

## **Expected Debug Output**
```
=== SRS Debug for Day 15 ===

📋 Context: story_generation
   Total violations: 3

✅ English Replacements Made (2):
    1. 'Good afternoon' → 'Magandang hapon po' 
    2. 'excuse me' → 'paumanhin po'

⚠️ Key Phrases Violations (1):
    1. 'magkano po ito' - Already known (stability: 3.2)
       Should not appear in Key Phrases section
```

## **Implementation Steps**

### **Step 1: Update Story Generation Prompts**
Add Key Phrases analysis request to all story prompts:
- Include Key Phrases list in SRS analysis JSON
- Request stability threshold checking

### **Step 2: Extend SRSLLMEnforcer** 
- Add Key Phrases extraction method
- Add SRS stability checking for Key Phrases
- Add violation recording for Key Phrases issues

### **Step 3: Update SRS Database Schema (Optional)**
- Consider adding violation_type field to distinguish English vs Key Phrases violations
- Or use existing structure with clear violation_type values

### **Step 4: Extend Debug Command**
- Show Key Phrases violations in debug-srs output
- Provide actionable recommendations

## **Benefits**

1. **Pedagogical Accuracy** - Key Phrases section only teaches truly new vocabulary
2. **Learner Experience** - No redundant drilling of already-known collocations  
3. **SRS Integration** - Uses actual learner knowledge state from SRS database
4. **Debug Visibility** - Clear reporting of Key Phrases violations
5. **Simple Implementation** - Leverages existing SRS enforcement infrastructure

## **Success Criteria**
- ✅ Detects high-stability Tagalog phrases in Key Phrases section
- ✅ Records Key Phrases violations in database  
- ✅ Shows Key Phrases violations in debug-srs output
- ✅ Provides clear guidance on which phrases should be replaced
- ✅ Integrates seamlessly with existing English SRS enforcement

This approach ensures that Key Phrases sections focus on genuinely new vocabulary while leveraging the existing SRS enforcement architecture.