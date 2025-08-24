"""Tests for the story prompt template."""
from pathlib import Path
import re
from typing import Dict, List

import pytest

# Path to the story prompt template
PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent / 'prompts' / 'story_prompt_balanced.txt'

# Required template variables
REQUIRED_VARIABLES = {
    'learning_objective',
    'focus',
    'learner_level',
    'new_collocations',
    'review_collocations',
    'story_guidance'
}

# Required instruction sections
REQUIRED_INSTRUCTIONS = [
    "Mark new collocations with **double asterisks** like this: **new collocation**",
    "Mark review collocations with *single asterisks* like this: *review collocation*",
    "word count between 400-500 words",
    "Use 60% or more dialogue",
    "Keep paragraphs short (2-3 sentences max)",
    "Include a title at the top"
]

# Example collocation markers
REQUIRED_MARKERS = [
    r'\*\*[^*]+\*\*',  # Matches **double asterisks**
    r'\*[^*]+\*'      # Matches *single asterisks*
]


@pytest.fixture
def prompt_template() -> str:
    """Load and return the story prompt template content."""
    if not PROMPT_TEMPLATE_PATH.exists():
        pytest.fail(f"Story prompt template not found at {PROMPT_TEMPLATE_PATH}")
    
    with open(PROMPT_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return f.read()


def test_template_contains_all_required_variables(prompt_template: str) -> None:
    """Test that the template contains all required variables."""
    missing_vars = []
    for var in REQUIRED_VARIABLES:
        if f"{{{var}}}" not in prompt_template:
            missing_vars.append(var)
    
    assert not missing_vars, f"Missing template variables: {', '.join(missing_vars)}"


def test_template_contains_required_instructions(prompt_template: str) -> None:
    """Test that the template contains all required instructions."""
    missing_instructions = []
    for instruction in REQUIRED_INSTRUCTIONS:
        if instruction not in prompt_template:
            missing_instructions.append(instruction)
    
    assert not missing_instructions, f"Missing instructions: {', '.join(missing_instructions)}"


def test_template_contains_collocation_markers(prompt_template: str) -> None:
    """Test that the template contains example collocation markers."""
    for marker_pattern in REQUIRED_MARKERS:
        if not re.search(marker_pattern, prompt_template):
            pytest.fail(f"Missing required collocation marker pattern: {marker_pattern}")


def test_template_has_example_usage(prompt_template: str) -> None:
    """Test that the template includes an example of marked collocations in context."""
    example_text = "\"I think we should **make a decision** soon,\" said Maria. \"Remember when we had to *deal with* something similar last month?\""
    assert example_text in prompt_template, "Missing example of marked collocations in context"


def test_template_has_story_structure_guidelines(prompt_template: str) -> None:
    """Test that the template includes story structure guidelines."""
    structure_guidelines = [
        "clear beginning, middle, and end",
        "60% or more dialogue",
        "keep paragraphs short (2-3 sentences max)",
        "simple, clear language"
    ]
    
    missing_guidelines = []
    for guideline in structure_guidelines:
        if guideline not in prompt_template.lower():
            missing_guidelines.append(guideline)
    
    assert not missing_guidelines, f"Missing story structure guidelines: {', '.join(missing_guidelines)}"
