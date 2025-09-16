"""
Tests for SRSLLMEnforcer prompt generation functionality.

Tests the fixed prompt generation that eliminated problematic database-driven 
pre-determined mappings and now provides clean English terms for LLM translation.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json

from srs_llm_enforcer import SRSLLMEnforcer
from srs_database import SRSDatabase
from llm_mock import MockLLM


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    return Mock(spec=MockLLM)

@pytest.fixture
def mock_srs_db():
    """Mock SRS database for testing."""
    return Mock(spec=SRSDatabase)

@pytest.fixture
def enforcer(mock_llm, mock_srs_db):
    """Create SRSLLMEnforcer instance for testing."""
    return SRSLLMEnforcer(mock_llm, mock_srs_db)


class TestPromptGeneration:
    """Test suite for SRS LLM Enforcer prompt generation."""


class TestEnglishTermsPromptGeneration:
    """Test prompt generation for English terms replacement."""
    
    def test_create_combined_enforcement_prompt_english_terms_only(self, enforcer):
        """Test prompt generation with only English terms, no Key Phrases."""
        content = "[TAGALOG-FEMALE-1]: Good morning po!"
        english_terms = ["good", "morning", "water", "thank you"]
        key_phrases_replacements = {}
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should contain the new instruction format
        assert "Replace these English terms with appropriate Filipino equivalents:" in prompt
        
        # Should list English terms without pre-determined mappings
        assert "• 'good'" in prompt
        assert "• 'morning'" in prompt
        assert "• 'water'" in prompt
        assert "• 'thank you'" in prompt
        
        # Should NOT contain any arrows indicating pre-determined mappings
        english_section = prompt[prompt.find("ENGLISH TERMS TO REPLACE"):prompt.find("## TASK")]
        assert " → " not in english_section
        assert " -> " not in english_section
    
    def test_create_combined_enforcement_prompt_no_predetermined_mappings(self, enforcer):
        """Test that prompts never contain problematic pre-determined mappings."""
        content = "[TAGALOG-FEMALE-1]: Good morning and thank you!"
        english_terms = ["good morning", "thank you"]
        key_phrases_replacements = {}
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should NEVER contain the problematic mappings that caused Day 19 issues
        assert "Good morning' → 'ito magandang umaga" not in prompt
        assert "Thank you' → 'salamat ito" not in prompt
        
        # Should contain clean English terms for LLM to translate
        assert "• 'good morning'" in prompt
        assert "• 'thank you'" in prompt
    
    def test_create_combined_enforcement_prompt_empty_english_terms(self, enforcer):
        """Test prompt generation with no English terms to replace."""
        content = "[TAGALOG-FEMALE-1]: Magandang umaga po!"
        english_terms = []
        key_phrases_replacements = {}
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should not contain English terms section when list is empty
        assert "ENGLISH TERMS TO REPLACE:" not in prompt
        assert "Replace these English terms with appropriate Filipino equivalents:" not in prompt
    
    def test_create_combined_enforcement_prompt_content_included(self, enforcer):
        """Test that original content is included in prompt."""
        content = """[NARRATOR]: Day 8: Test Story

[TAGALOG-FEMALE-1]: Good morning po!
[TAGALOG-MALE-1]: Thank you very much!"""
        
        english_terms = ["good", "morning", "thank", "you"]
        key_phrases_replacements = {}
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should include the original content
        assert "[NARRATOR]: Day 8: Test Story" in prompt
        assert "[TAGALOG-FEMALE-1]: Good morning po!" in prompt
        assert "[TAGALOG-MALE-1]: Thank you very much!" in prompt


class TestKeyPhrasesPromptGeneration:
    """Test prompt generation for Key Phrases replacement."""
    
    def test_create_combined_enforcement_prompt_with_key_phrases(self, enforcer):
        """Test prompt generation with Key Phrases replacements."""
        content = "[TAGALOG-FEMALE-1]: Test content"
        english_terms = ["test"]
        key_phrases_replacements = {
            "old phrase": "new phrase",
            "another old": "another new"
        }
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should contain both English terms and Key Phrases sections
        assert "ENGLISH TERMS TO REPLACE:" in prompt
        assert "KEY PHRASES TO REPLACE:" in prompt
        
        # Should include Key Phrases replacements
        assert "• 'old phrase' → 'new phrase'" in prompt
        assert "• 'another old' → 'another new'" in prompt
    
    def test_create_combined_enforcement_prompt_key_phrases_additions(self, enforcer):
        """Test prompt generation with Key Phrases additions."""
        content = "[TAGALOG-FEMALE-1]: Test content"
        english_terms = []
        key_phrases_replacements = {
            "__ADD_PHRASE_1__": "new phrase to add",
            "__ADD_PHRASE_2__": "another phrase to add",
            "regular replacement": "new version"
        }
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should separate additions from replacements
        assert "KEY PHRASES TO REPLACE:" in prompt
        assert "KEY PHRASES TO ADD:" in prompt
        
        # Should format additions correctly
        assert "• Add: 'new phrase to add'" in prompt
        assert "• Add: 'another phrase to add'" in prompt
        
        # Should format regular replacements correctly
        assert "• 'regular replacement' → 'new version'" in prompt
    
    def test_create_combined_enforcement_prompt_mixed_operations(self, enforcer):
        """Test prompt generation with both English terms and Key Phrases."""
        content = "[TAGALOG-FEMALE-1]: Good morning with old phrase!"
        english_terms = ["good", "morning"]
        key_phrases_replacements = {
            "old phrase": "new phrase",
            "__ADD_PHRASE_1__": "added phrase"
        }
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should contain all sections
        assert "ENGLISH TERMS TO REPLACE:" in prompt
        assert "KEY PHRASES TO REPLACE:" in prompt  
        assert "KEY PHRASES TO ADD:" in prompt
        
        # Should format each section correctly
        assert "• 'good'" in prompt
        assert "• 'morning'" in prompt
        assert "• 'old phrase' → 'new phrase'" in prompt
        assert "• Add: 'added phrase'" in prompt


class TestPromptStructureAndFormat:
    """Test overall prompt structure and formatting."""
    
    def test_create_combined_enforcement_prompt_includes_day_context(self, enforcer):
        """Test that prompts include day context for learning progression."""
        content = "[TAGALOG-FEMALE-1]: Test content"
        english_terms = ["test"]
        key_phrases_replacements = {}
        day = 15
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should include day number in context
        assert "Day 15" in prompt
        assert "for Day 15" in prompt
    
    def test_create_combined_enforcement_prompt_includes_enforcement_rules(self, enforcer):
        """Test that prompts include enforcement rules and guidelines."""
        content = "[TAGALOG-FEMALE-1]: Test content"
        english_terms = ["test"]
        key_phrases_replacements = {}
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should include task instructions
        assert "TASK 1: ENFORCEMENT RULES" in prompt
        assert "ENGLISH TERMS REPLACEMENT" in prompt
        assert "INTELLIGENT REPLACEMENT" in prompt
        
        # Should include translation extraction instructions
        assert "TASK 2: TRANSLATION EXTRACTION" in prompt
        assert "TRANSLATION GUIDELINES" in prompt
        
        # Should include response format instructions
        assert "RESPONSE FORMAT" in prompt
    
    def test_create_combined_enforcement_prompt_text_first_format_specified(self, enforcer):
        """Test that prompts specify the new text-first response format."""
        content = "[TAGALOG-FEMALE-1]: Test content"
        english_terms = ["test"]
        key_phrases_replacements = {}
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should specify text-first format
        assert "Return the enforced content as clean, copyable text" in prompt
        assert "COMPLETE_STORY_CONTENT_WITH_REPLACEMENTS_APPLIED_HERE" in prompt
        assert "PHRASE_TRANSLATIONS:" in prompt
        
        # Should NOT mention old JSON format
        assert "enforced_content" not in prompt.lower() or "enforced_content" in prompt  # Allow in examples
        assert '"enforced_content":' not in prompt  # But not as JSON structure
    
    def test_create_combined_enforcement_prompt_maintains_instructions(self, enforcer):
        """Test that prompts maintain important enforcement instructions."""
        content = "[TAGALOG-FEMALE-1]: Test content"
        english_terms = ["test"]
        key_phrases_replacements = {}
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should maintain grammar-aware replacement instructions
        assert "grammar" in prompt.lower()
        assert "conjugation" in prompt.lower()
        
        # Should maintain context awareness instructions
        assert "context" in prompt.lower()
        
        # Should maintain natural language instructions
        assert "natural" in prompt.lower()
        assert "Filipino speakers" in prompt or "Tagalog speaker" in prompt


class TestPromptRegressionPrevention:
    """Test that prompts prevent regression to problematic behavior."""
    
    def test_extract_english_terms_from_analysis_basic(self, enforcer):
        """Test extraction of English terms from SRS analysis."""
        srs_analysis = [
            {"english": "good morning", "srs_queries": ["magandang umaga", "morning"]},
            {"english": "water", "srs_queries": ["tubig", "water"]},
            {"english": "thank you", "srs_queries": ["salamat", "thank you"]}
        ]
        
        english_terms = enforcer._extract_english_terms_from_analysis(srs_analysis)
        
        # Should extract just the English terms, no mappings
        assert english_terms == ["good morning", "water", "thank you"]
    
    def test_extract_english_terms_from_analysis_handles_empty_terms(self, enforcer):
        """Test extraction handles analysis entries with missing English terms."""
        srs_analysis = [
            {"english": "good morning", "srs_queries": ["magandang umaga"]},
            {"english": "", "srs_queries": ["some query"]},  # Empty English term
            {"srs_queries": ["query without english"]},  # Missing English key
            {"english": "water", "srs_queries": ["tubig"]}
        ]
        
        english_terms = enforcer._extract_english_terms_from_analysis(srs_analysis)
        
        # Should only extract valid English terms
        assert english_terms == ["good morning", "water"]
    
    def test_prompt_never_contains_database_mappings(self, enforcer):
        """Test that prompts never contain problematic database-driven mappings."""
        content = "[TAGALOG-FEMALE-1]: Good morning, I need water and thank you!"
        
        # These are the types of terms that caused Day 19 issues
        problematic_english_terms = [
            "good morning", "water", "thank you", "next year", 
            "order", "meal", "mango", "shake", "specialty", "ready"
        ]
        
        key_phrases_replacements = {}
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, problematic_english_terms, key_phrases_replacements, day
        )
        
        # Should list English terms cleanly without mappings
        for term in problematic_english_terms:
            assert f"• '{term}'" in prompt
        
        # Should NEVER contain the problematic mappings that were generated by database search
        problematic_mappings = [
            "Good morning' → 'ito magandang umaga",
            "Thank you' → 'salamat ito", 
            "water' → 'tubig na",
            "next year' → 'susunod na taon na"
        ]
        
        for mapping in problematic_mappings:
            assert mapping not in prompt
    
    def test_prompt_encourages_llm_translation_choice(self, enforcer):
        """Test that prompts encourage LLM to choose appropriate translations."""
        content = "[TAGALOG-FEMALE-1]: Good morning!"
        english_terms = ["good morning"]
        key_phrases_replacements = {}
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should encourage LLM to make translation decisions
        assert "Replace these English terms with appropriate Filipino equivalents" in prompt
        assert "Maintain proper Tagalog grammar" in prompt
        assert "Consider context" in prompt
        
        # Should not provide predetermined answers
        english_section = prompt[prompt.find("ENGLISH TERMS TO REPLACE"):prompt.find("## TASK")]
        assert "magandang umaga" not in english_section  # No predetermined Filipino
        assert "salamat" not in english_section  # No predetermined Filipino


class TestPromptEdgeCases:
    """Test prompt generation edge cases and error scenarios."""
    
    def test_create_combined_enforcement_prompt_very_long_content(self, enforcer):
        """Test prompt generation with very long story content."""
        # Create long content to test prompt size limits
        long_content = "\n".join([
            f"[TAGALOG-FEMALE-1]: Line {i} with some English words like good morning."
            for i in range(100)
        ])
        
        english_terms = ["good", "morning", "english", "words"]
        key_phrases_replacements = {}
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            long_content, english_terms, key_phrases_replacements, day
        )
        
        # Should handle long content without errors
        assert len(prompt) > 1000  # Prompt should be substantial
        assert "Line 0" in prompt  # Should include beginning
        assert "Line 99" in prompt  # Should include end
        assert "ENGLISH TERMS TO REPLACE:" in prompt
    
    def test_create_combined_enforcement_prompt_special_characters(self, enforcer):
        """Test prompt generation with special characters in terms."""
        content = "[TAGALOG-FEMALE-1]: Test with special chars!"
        english_terms = ["it's", "don't", "won't", "can't"]  # Contractions
        key_phrases_replacements = {
            "phrase with 'quotes'": "new phrase",
            "phrase with \"double quotes\"": "another phrase"
        }
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should handle contractions and quotes properly
        assert "• 'it's'" in prompt
        assert "• 'don't'" in prompt
        assert "phrase with 'quotes'" in prompt
        assert 'phrase with "double quotes"' in prompt
    
    def test_create_combined_enforcement_prompt_unicode_content(self, enforcer):
        """Test prompt generation with Unicode content."""
        content = "[TAGALOG-FEMALE-1]: Test with émojis 😀 and áccénts!"
        english_terms = ["test", "with"]
        key_phrases_replacements = {}
        day = 8
        
        prompt = enforcer._create_combined_enforcement_prompt(
            content, english_terms, key_phrases_replacements, day
        )
        
        # Should handle Unicode characters properly
        assert "émojis 😀 and áccénts!" in prompt
        assert "• 'test'" in prompt
        assert "• 'with'" in prompt