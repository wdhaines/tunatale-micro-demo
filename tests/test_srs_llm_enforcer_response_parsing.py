"""
Tests for SRSLLMEnforcer response parsing functionality.

Tests the new text-first response format that replaced the problematic 
JSON-wrapped format, ensuring clean copyable content extraction.
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


class TestResponseParsing:
    """Test suite for SRS LLM Enforcer response parsing."""


class TestTextFirstResponseFormat:
    """Test the new text-first response format parsing."""
    
    def test_extract_enforced_content_text_first_format(self, enforcer):
        """Test content extraction from new text-first format."""
        response = {
            'choices': [{
                'message': {
                    'content': """[NARRATOR]: Day 8: El Nido Breakfast

Key Phrases:

[TAGALOG-FEMALE-1]: magandang umaga po
[NARRATOR]: good morning
[TAGALOG-FEMALE-1]: magandang umaga po

[NARRATOR]: Natural Speed

[TAGALOG-FEMALE-1]: Magandang umaga po! Kailangan ko po ng tubig.
[TAGALOG-MALE-1]: Salamat po, napaka-masarap ng pagkain!

PHRASE_TRANSLATIONS:
{
  "magandang umaga po": "good morning (polite)",
  "kailangan ko po": "I need (polite)",
  "tubig": "water",
  "salamat po": "thank you (polite)",
  "napaka-masarap": "very delicious",
  "pagkain": "food"
}"""
                }
            }]
        }
        
        content = enforcer._extract_enforced_content(response)
        
        # Should extract clean content before PHRASE_TRANSLATIONS marker
        assert "magandang umaga po" in content
        assert "Magandang umaga po! Kailangan ko po ng tubig." in content
        assert "Salamat po, napaka-masarap ng pagkain!" in content
        
        # Should NOT include the PHRASE_TRANSLATIONS section
        assert "PHRASE_TRANSLATIONS:" not in content
        assert '"magandang umaga po": "good morning (polite)"' not in content
    
    def test_extract_enforced_content_no_translations_marker(self, enforcer):
        """Test content extraction when PHRASE_TRANSLATIONS marker is missing."""
        response = {
            'choices': [{
                'message': {
                    'content': """[NARRATOR]: Day 8: Test Story

[TAGALOG-FEMALE-1]: Magandang umaga po!
[TAGALOG-MALE-1]: Salamat po!"""
                }
            }]
        }
        
        content = enforcer._extract_enforced_content(response)
        
        # Should return entire content when no marker present
        assert "[NARRATOR]: Day 8: Test Story" in content
        assert "Magandang umaga po!" in content
        assert "Salamat po!" in content
    
    def test_extract_enforced_content_empty_translations(self, enforcer):
        """Test content extraction with empty translations section."""
        response = {
            'choices': [{
                'message': {
                    'content': """[TAGALOG-FEMALE-1]: Magandang umaga po!

PHRASE_TRANSLATIONS:
{}"""
                }
            }]
        }
        
        content = enforcer._extract_enforced_content(response)
        
        assert content.strip() == "[TAGALOG-FEMALE-1]: Magandang umaga po!"
        assert "PHRASE_TRANSLATIONS:" not in content
    
    def test_extract_enforced_content_multiple_markers(self, enforcer):
        """Test content extraction with multiple PHRASE_TRANSLATIONS markers (edge case)."""
        response = {
            'choices': [{
                'message': {
                    'content': """[TAGALOG-FEMALE-1]: First PHRASE_TRANSLATIONS: should be ignored.

PHRASE_TRANSLATIONS:
{"test": "value"}"""
                }
            }]
        }
        
        content = enforcer._extract_enforced_content(response)
        
        # Should split on first marker only
        assert "First PHRASE_TRANSLATIONS: should be ignored." in content
        assert '{"test": "value"}' not in content


class TestTranslationExtraction:
    """Test phrase translation extraction from text-first format."""
    
    def test_extract_phrase_translations_text_first_format(self, enforcer):
        """Test translation extraction from new text-first format."""
        response = {
            'choices': [{
                'message': {
                    'content': """[TAGALOG-FEMALE-1]: Magandang umaga po! Kailangan ko po ng tubig.

PHRASE_TRANSLATIONS:
{
  "magandang umaga po": "good morning (polite)",
  "kailangan ko po": "I need (polite)",
  "tubig": "water",
  "po": "(polite marker)"
}"""
                }
            }]
        }
        
        translations = enforcer._extract_phrase_translations(response)
        
        # Should extract all translations with default confidence
        assert len(translations) == 4
        
        # Check specific translations
        translation_dict = {t['filipino']: t['english'] for t in translations}
        assert translation_dict['magandang umaga po'] == 'good morning (polite)'
        assert translation_dict['kailangan ko po'] == 'I need (polite)'
        assert translation_dict['tubig'] == 'water'
        assert translation_dict['po'] == '(polite marker)'
        
        # Check that all have default confidence
        for translation in translations:
            assert translation['confidence'] == 0.9
    
    def test_extract_phrase_translations_malformed_json(self, enforcer):
        """Test translation extraction with malformed JSON in translations section."""
        response = {
            'choices': [{
                'message': {
                    'content': """[TAGALOG-FEMALE-1]: Test content.

PHRASE_TRANSLATIONS:
{
  "incomplete": "json"
  missing comma
}"""
                }
            }]
        }
        
        translations = enforcer._extract_phrase_translations(response)
        
        # Should return empty list when JSON is malformed
        assert translations == []
    
    def test_extract_phrase_translations_no_marker(self, enforcer):
        """Test translation extraction when PHRASE_TRANSLATIONS marker is missing."""
        response = {
            'choices': [{
                'message': {
                    'content': """[TAGALOG-FEMALE-1]: Just story content here."""
                }
            }]
        }
        
        translations = enforcer._extract_phrase_translations(response)
        
        # Should return empty list when no marker found
        assert translations == []
    
    def test_extract_phrase_translations_empty_json(self, enforcer):
        """Test translation extraction with empty JSON object."""
        response = {
            'choices': [{
                'message': {
                    'content': """[TAGALOG-FEMALE-1]: Test content.

PHRASE_TRANSLATIONS:
{}"""
                }
            }]
        }
        
        translations = enforcer._extract_phrase_translations(response)
        
        # Should return empty list for empty JSON
        assert translations == []


class TestBackwardCompatibility:
    """Test backward compatibility with old JSON format."""
    
    def test_extract_enforced_content_old_json_format(self, enforcer):
        """Test content extraction from old JSON format."""
        old_json_content = {
            "enforced_content": """[NARRATOR]: Day 8: Test Story

[TAGALOG-FEMALE-1]: Magandang umaga po!""",
            "phrase_translations": [
                {"filipino": "magandang umaga po", "english": "good morning", "confidence": 0.95}
            ]
        }
        
        response = {
            'choices': [{
                'message': {
                    'content': json.dumps(old_json_content)
                }
            }]
        }
        
        content = enforcer._extract_enforced_content(response)
        
        # Should extract enforced_content from JSON
        assert "[NARRATOR]: Day 8: Test Story" in content
        assert "Magandang umaga po!" in content
    
    def test_extract_phrase_translations_old_json_format(self, enforcer):
        """Test translation extraction from old JSON format."""
        old_json_content = {
            "enforced_content": "[TAGALOG-FEMALE-1]: Test content.",
            "phrase_translations": [
                {"filipino": "magandang umaga", "english": "good morning", "confidence": 0.95},
                {"filipino": "salamat", "english": "thank you", "confidence": 0.90}
            ]
        }
        
        response = {
            'choices': [{
                'message': {
                    'content': json.dumps(old_json_content)
                }
            }]
        }
        
        translations = enforcer._extract_phrase_translations(response)
        
        # Should extract translations array from JSON
        assert len(translations) == 2
        assert translations[0]['filipino'] == 'magandang umaga'
        assert translations[0]['english'] == 'good morning'
        assert translations[0]['confidence'] == 0.95
        assert translations[1]['filipino'] == 'salamat'
        assert translations[1]['english'] == 'thank you'
        assert translations[1]['confidence'] == 0.90
    
    def test_extract_enforced_content_plain_text_fallback(self, enforcer):
        """Test content extraction falls back to plain text."""
        response = {
            'choices': [{
                'message': {
                    'content': """Plain text story content without any special formatting."""
                }
            }]
        }
        
        content = enforcer._extract_enforced_content(response)
        
        # Should return the entire content as-is
        assert content == "Plain text story content without any special formatting."


class TestResponseFormatValidation:
    """Test validation of response formats and error handling."""
    
    def test_extract_enforced_content_string_response(self, enforcer):
        """Test content extraction when response is a plain string."""
        response_string = """[TAGALOG-FEMALE-1]: Direct string response.

PHRASE_TRANSLATIONS:
{"test": "value"}"""
        
        content = enforcer._extract_enforced_content(response_string)
        
        # Should handle string input and extract content before marker
        assert content.strip() == "[TAGALOG-FEMALE-1]: Direct string response."
    
    def test_extract_phrase_translations_string_response(self, enforcer):
        """Test translation extraction when response is a plain string."""
        response_string = """[TAGALOG-FEMALE-1]: Test content.

PHRASE_TRANSLATIONS:
{"magandang umaga": "good morning", "salamat": "thank you"}"""
        
        translations = enforcer._extract_phrase_translations(response_string)
        
        # Should extract translations from string format
        assert len(translations) == 2
        translation_dict = {t['filipino']: t['english'] for t in translations}
        assert translation_dict['magandang umaga'] == 'good morning'
        assert translation_dict['salamat'] == 'thank you'
    
    def test_extract_enforced_content_invalid_response_format(self, enforcer):
        """Test error handling with invalid response format."""
        invalid_response = {"invalid": "format"}
        
        with pytest.raises(ValueError, match="Invalid LLM response format"):
            enforcer._extract_enforced_content(invalid_response)
    
    def test_extract_phrase_translations_invalid_response_format(self, enforcer):
        """Test error handling with invalid response format for translations."""
        invalid_response = {"invalid": "format"}
        
        translations = enforcer._extract_phrase_translations(invalid_response)
        
        # Should return empty list and log warning for invalid format
        assert translations == []
    
    def test_extract_enforced_content_nested_response_format(self, enforcer):
        """Test content extraction from nested response format."""
        nested_response = {
            'response': {
                'choices': [{
                    'message': {
                        'content': """[TAGALOG-FEMALE-1]: Nested format test.

PHRASE_TRANSLATIONS:
{"test": "nested"}"""
                    }
                }]
            }
        }
        
        content = enforcer._extract_enforced_content(nested_response)
        
        # Should handle nested format
        assert content.strip() == "[TAGALOG-FEMALE-1]: Nested format test."


class TestRealWorldUseCases:
    """Test with real-world response scenarios."""
    
    def test_complete_story_response_text_first(self, enforcer):
        """Test parsing a complete story response in text-first format."""
        complete_response = {
            'choices': [{
                'message': {
                    'content': """[NARRATOR]: Day 8: Farewell El Nido

Key Phrases:

[TAGALOG-FEMALE-1]: salamat sa lahat
[NARRATOR]: thank you for everything
[TAGALOG-FEMALE-1]: salamat sa lahat

[TAGALOG-FEMALE-1]: babalik po ako
[NARRATOR]: I'll come back
[TAGALOG-FEMALE-1]: babalik po ako

[NARRATOR]: Natural Speed

[NARRATOR]: Hotel Checkout

[TAGALOG-FEMALE-1]: Salamat po sa lahat ng tulong ninyo!
[TAGALOG-FEMALE-2]: Walang anuman po! Babalik po kayo!

[NARRATOR]: Slow Speed

[TAGALOG-FEMALE-1]: Salamat... po... sa... lahat... ng... tulong... ninyo!

[NARRATOR]: Translated

[TAGALOG-FEMALE-1]: Salamat po sa lahat ng tulong ninyo!
[NARRATOR]: Thank you for all your help!

PHRASE_TRANSLATIONS:
{
  "salamat po": "thank you (polite)",
  "sa lahat": "for everything",
  "tulong": "help",
  "ninyo": "your (plural polite)",
  "walang anuman": "you're welcome",
  "babalik": "come back",
  "po": "(polite marker)"
}"""
                }
            }]
        }
        
        # Test content extraction
        content = enforcer._extract_enforced_content(complete_response)
        
        assert "[NARRATOR]: Day 8: Farewell El Nido" in content
        assert "Key Phrases:" in content
        assert "Natural Speed" in content
        assert "Slow Speed" in content
        assert "Translated" in content
        assert "PHRASE_TRANSLATIONS:" not in content
        
        # Test translation extraction
        translations = enforcer._extract_phrase_translations(complete_response)
        
        assert len(translations) == 7
        translation_dict = {t['filipino']: t['english'] for t in translations}
        assert translation_dict['salamat po'] == 'thank you (polite)'
        assert translation_dict['walang anuman'] == "you're welcome"
        assert translation_dict['po'] == '(polite marker)'
    
    def test_copyable_content_quality(self, enforcer):
        """Test that extracted content is clean and copyable."""
        response = {
            'choices': [{
                'message': {
                    'content': """[TAGALOG-FEMALE-1]: This should be easily copyable content!
[TAGALOG-MALE-1]: No JSON formatting should appear in the final output.

PHRASE_TRANSLATIONS:
{"easily": "madaling", "copyable": "makokopya"}"""
                }
            }]
        }
        
        content = enforcer._extract_enforced_content(response)
        
        # Content should be clean text, no JSON, no special markers
        assert content.startswith("[TAGALOG-FEMALE-1]:")
        assert "easily copyable content!" in content
        assert "No JSON formatting should appear" in content
        assert "{" not in content  # No JSON braces
        assert "PHRASE_TRANSLATIONS:" not in content
        
        # Should be suitable for copy-paste into other applications
        lines = content.split('\n')
        assert all(line.strip() == '' or line.startswith('[') or not line.startswith('{') for line in lines)
    
    def test_edge_case_multiple_colons_in_content(self, enforcer):
        """Test handling content with multiple colons that might confuse parsing."""
        response = {
            'choices': [{
                'message': {
                    'content': """[TAGALOG-FEMALE-1]: The time is 12:30 PM.
[TAGALOG-MALE-1]: Meeting at 2:45 PM: Don't forget!

PHRASE_TRANSLATIONS:
{"time": "oras", "meeting": "pulong"}"""
                }
            }]
        }
        
        content = enforcer._extract_enforced_content(response)
        
        # Should preserve colons in time expressions and other content
        assert "12:30 PM" in content
        assert "2:45 PM: Don't forget!" in content
        assert "PHRASE_TRANSLATIONS:" not in content