"""
Validation Schema and LLM Prompt Generation for SRS Debug System

Provides structured templates and error-resilient parsing for LLM-generated
validation files with voice-to-text inconsistencies.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ValidationSchemaConfig:
    """Configuration for validation schema and parsing."""
    required_sections: List[str]
    optional_sections: List[str]
    field_aliases: Dict[str, List[str]]
    category_mappings: Dict[str, str]
    priority_values: List[str]
    voice_text_artifacts: List[str]


# Default validation schema configuration
VALIDATION_SCHEMA = ValidationSchemaConfig(
    required_sections=[
        "vocabulary_recognition_states"
    ],
    optional_sections=[
        "strategic_vocabulary_decisions",
        "debug_system_requirements", 
        "validation_expectations",
        "session_metadata"
    ],
    field_aliases={
        "word": ["word", "term", "vocabulary", "phrase", "item"],
        "meaning": ["meaning", "definition", "translation", "sense"],
        "priority": ["priority", "importance", "urgency", "level"],
        "category": ["category", "type", "classification", "group"],
        "srs_action": ["srs_action", "action", "recommendation", "next_step"],
        "context": ["context", "usage", "situation", "scenario"],
        "recognition_pattern": ["recognition_pattern", "pattern", "learning_pattern"],
        "current_status": ["current_status", "status", "state", "condition"]
    },
    category_mappings={
        # Normalize category names to standard format
        "unknown words": "unknown_vocabulary_gaps",
        "unknown vocabulary": "unknown_vocabulary_gaps", 
        "high priority collocations": "high_priority_collocation_gaps",
        "collocation gaps": "high_priority_collocation_gaps",
        "dormant vocabulary": "dormant_but_recoverable",
        "dormant words": "dormant_but_recoverable",
        "natural acquisition": "natural_acquisition_successes",
        "naturally acquired": "natural_acquisition_successes",
        "explicit teaching": "explicit_teaching_validation",
        "explicitly learned": "explicit_teaching_validation",
        "context dependent": "context_dependent_complexity",
        "contextual complexity": "context_dependent_complexity"
    },
    priority_values=["high", "medium", "low"],
    voice_text_artifacts=[
        "(unclear)", "[inaudible]", "(inaudible)", "[unclear]",
        "um,", "uh,", "like,", "you know,", "so,", "basically,"
    ]
)


def generate_validation_template() -> str:
    """Generate comprehensive prompt template for LLM validation file generation."""
    
    template = """# SRS Debug Validation File Generation

You are generating a validation file for TunaTale's SRS (Spaced Repetition System) debug analysis. This file will be used to validate vocabulary recognition states against expected learning outcomes.

## CRITICAL FORMATTING REQUIREMENTS

### 1. JSON Structure (REQUIRED)
```json
{
  "session_metadata": {
    "date": "YYYY-MM-DD",
    "day": <integer>,
    "version": "<string>", 
    "session_type": "srs_debugging_validation",
    "total_observations": <integer>
  },
  "vocabulary_recognition_states": {
    "unknown_vocabulary_gaps": [...],
    "high_priority_collocation_gaps": [...],
    "context_dependent_complexity": [...],
    "dormant_but_recoverable": [...],
    "natural_acquisition_successes": [...],
    "explicit_teaching_validation": [...]
  }
}
```

### 2. Field Naming Standards (STRICT)
- Use snake_case for all field names: "unknown_vocabulary_gaps" NOT "unknown vocabulary gaps"
- Use consistent field names across all entries:
  - "word" for single terms
  - "phrase" for multi-word expressions  
  - "meaning" for definitions/translations
  - "priority" for importance levels
  - "srs_action" for recommended actions

### 3. Priority Values (EXACT)
Only use these three values:
- "high"
- "medium" 
- "low"
DO NOT use: "HIGH", "Medium", "important", "critical", etc.

### 4. Required Fields per Entry
Each vocabulary item must include:
```json
{
  "word": "<string>",           // Required
  "meaning": "<string>",        // Required
  "priority": "<string>",       // Required: high/medium/low
  "category": "<string>",       // Optional
  "srs_action": "<string>"      // Required
}
```

## VOCABULARY CATEGORIZATION GUIDE

### unknown_vocabulary_gaps
Words/phrases completely unknown to learner:
- Not in SRS database at all
- Requires initial teaching
- Examples: new action verbs, unfamiliar cultural terms

### high_priority_collocation_gaps  
Essential phrases for communication:
- Complete functional phrases like "anything else", "can we get"
- High utility across multiple contexts
- Should be learned as complete units

### context_dependent_complexity
Known words used in unfamiliar ways:
- Same word, different contextual meanings
- Translation complexity (one word → multiple English meanings)
- Examples: "kaya" (can/able vs may I ask context)

### dormant_but_recoverable
Previously learned but forgotten:
- Was in SRS database but not recently accessed
- Recognition possible with minimal reinforcement
- "Aha moment" vocabulary

### natural_acquisition_successes
Learning through exposure without explicit teaching:
- Understanding developing through repetition
- Passive recognition emerging
- Avoid over-targeting with explicit instruction

### explicit_teaching_validation
Successfully learned through structured instruction:
- Pimsleur breakdown methodology working
- Rapid stability increase through focused practice
- Complex vocabulary responding to teaching

## CONTENT QUALITY STANDARDS

### Descriptions Should Be:
- Specific and actionable
- Based on observable learning behaviors  
- Free of voice-to-text artifacts
- Consistent in terminology

### Avoid These Voice Artifacts:
- (unclear), [inaudible], um, uh, like, you know
- Spelling errors: seperately → separate, definately → definitely
- Inconsistent capitalization or formatting

### SRS Action Recommendations:
Use standard verbs:
- "add_with_low_stability"
- "add_for_dining_contexts" 
- "reinforce_contextual_usage"
- "review_with_breakdown"
- "track_natural_progression"

## VALIDATION CHECKLIST

Before submitting, verify:
- [ ] Valid JSON format (no trailing commas, proper quotes)
- [ ] All required sections present
- [ ] Consistent field naming (snake_case)
- [ ] Priority values are exactly "high", "medium", or "low"
- [ ] No voice-to-text artifacts in descriptions
- [ ] Each item has required fields (word, meaning, priority, srs_action)
- [ ] Total observations match session_metadata count
- [ ] Categories align with learning observations

## EXAMPLE ENTRY (PERFECT FORMAT):
```json
{
  "word": "umupo",
  "meaning": "to sit (action verb)",
  "priority": "high",
  "category": "basic_action_verbs",
  "context": "where would you like to sit",
  "srs_action": "add_with_low_stability"
}
```

Generate your validation file following these exact specifications. Focus on accuracy, consistency, and adherence to the required structure."""

    return template


def generate_simple_validation_template() -> str:
    """Generate a simpler template for basic validation needs."""
    
    template = """# Simple SRS Validation File

Generate a validation file with this exact structure:

```json
{
  "day": 16,
  "expected_states": {
    "unknown_vocabulary_gaps": ["word1", "word2", "word3"],
    "high_priority_collocation_gaps": ["phrase1", "phrase2"], 
    "dormant_but_recoverable": ["word4", "word5"],
    "natural_acquisition_successes": ["word6", "word7"]
  }
}
```

**Rules:**
- Use snake_case for categories
- Include only the word/phrase text (no extra metadata)
- Each category should have 2-5 items
- Words should be lowercase, phrases use underscores: "anything_else"

**Categories:**
- unknown_vocabulary_gaps: Completely unknown words
- high_priority_collocation_gaps: Essential phrases for communication
- dormant_but_recoverable: Previously learned but forgotten  
- natural_acquisition_successes: Learning through exposure"""

    return template


def validate_schema(validation_data: Dict[str, Any]) -> List[str]:
    """
    Validate a validation file against the schema.
    
    Returns:
        List of warnings/errors found
    """
    warnings = []
    
    # Check required sections
    for section in VALIDATION_SCHEMA.required_sections:
        if section not in validation_data:
            warnings.append(f"Missing required section: {section}")
    
    # Check vocabulary recognition states structure
    if "vocabulary_recognition_states" in validation_data:
        states = validation_data["vocabulary_recognition_states"]
        
        # Check each category
        for category_name, items in states.items():
            if not isinstance(items, list):
                warnings.append(f"Category '{category_name}' should be a list")
                continue
                
            # Check items in category
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    # Check for priority field if present
                    if "priority" in item:
                        priority = item["priority"]
                        if priority not in VALIDATION_SCHEMA.priority_values:
                            warnings.append(f"Invalid priority '{priority}' in {category_name}[{i}]. Use: high/medium/low")
                    
                    # Check for voice artifacts
                    for field, value in item.items():
                        if isinstance(value, str):
                            for artifact in VALIDATION_SCHEMA.voice_text_artifacts:
                                if artifact.lower() in value.lower():
                                    warnings.append(f"Voice artifact '{artifact}' found in {category_name}[{i}].{field}")
    
    return warnings


def normalize_validation_data(validation_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize validation data to handle common inconsistencies.
    
    Returns:
        Cleaned and normalized validation data
    """
    normalized = {}
    
    for key, value in validation_data.items():
        # Normalize section names
        normalized_key = key
        if key in VALIDATION_SCHEMA.category_mappings:
            normalized_key = VALIDATION_SCHEMA.category_mappings[key]
        
        if isinstance(value, dict):
            normalized[normalized_key] = normalize_validation_data(value)
        elif isinstance(value, list):
            normalized[normalized_key] = [
                normalize_validation_data(item) if isinstance(item, dict) else item 
                for item in value
            ]
        else:
            normalized[normalized_key] = value
    
    return normalized


def clean_voice_artifacts(text: str) -> str:
    """Clean common voice-to-text artifacts from text."""
    if not isinstance(text, str):
        return text
        
    cleaned = text
    
    # Remove voice artifacts
    for artifact in VALIDATION_SCHEMA.voice_text_artifacts:
        cleaned = cleaned.replace(artifact, "")
    
    # Remove common trailing phrases
    trailing_phrases = [
        ", you know", " you know", ", like", " like",
        ", basically", " basically", ", so", " so"
    ]
    for phrase in trailing_phrases:
        cleaned = cleaned.replace(phrase, "")
    
    # Fix common spelling errors
    corrections = {
        "seperately": "separate",
        "definately": "definitely", 
        "occured": "occurred",
        "recieve": "receive"
    }
    
    for error, correction in corrections.items():
        cleaned = cleaned.replace(error, correction)
    
    # Clean up extra spaces and punctuation
    cleaned = " ".join(cleaned.split())
    cleaned = cleaned.strip(" ,.-")
    
    return cleaned


if __name__ == "__main__":
    # Generate and print template
    print("=== COMPREHENSIVE VALIDATION TEMPLATE ===")
    print(generate_validation_template())
    print("\n=== SIMPLE VALIDATION TEMPLATE ===")
    print(generate_simple_validation_template())