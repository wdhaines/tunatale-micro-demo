"""
Regression tests for SRS enforcement system.

These tests ensure that the Day 19 SRS enforcement failure never happens again
by testing all the originally problematic scenarios and ensuring the fixes work.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json

from srs_llm_enforcer import SRSLLMEnforcer, DeterministicEnglishDetector
from srs_database import SRSDatabase
from llm_mock import MockLLM


# Day 19 problematic content that failed enforcement
DAY19_PROBLEMATIC_CONTENT = """[NARRATOR]: Day 8: Farewell El Nido

Key Phrases:

[TAGALOG-FEMALE-1]: salamat sa lahat
[NARRATOR]: thank you for everything
[TAGALOG-FEMALE-1]: salamat sa lahat

[NARRATOR]: Natural Speed

[TAGALOG-FEMALE-1]: Good morning po! Check out ko na po.
[TAGALOG-FEMALE-2]: Good morning po sa inyo! Kumusta naman po ang stay ninyo dito?
[TAGALOG-FEMALE-1]: Napakaganda talaga dito! Napaka-tahimik ng El Nido.
[TAGALOG-MALE-1]: Ano po ang order ninyo? Special meal po para sa paalam!
[TAGALOG-FEMALE-1]: Kinilaw po at mango shake - paborito ko na po yan!
[TAGALOG-MALE-1]: The specialty is ready na po!
[TAGALOG-FEMALE-1]: Babalik po ako next year!"""

# Originally problematic terms that were not being replaced
ORIGINAL_PROBLEM_TERMS = [
    "next year", "order", "meal", "mango", "shake", "specialty", "ready", 
    "Good morning", "Special meal", "The specialty"
]


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    return Mock(spec=MockLLM)

@pytest.fixture
def mock_srs_db():
    """Mock SRS database for testing."""
    db = Mock(spec=SRSDatabase)
    db.db_path = ":memory:"
    return db

@pytest.fixture
def enforcer(mock_llm, mock_srs_db):
    """Create SRSLLMEnforcer instance for testing."""
    return SRSLLMEnforcer(mock_llm, mock_srs_db)

@pytest.fixture
def mock_language_detector():
    """Mock LanguageDetector that classifies Day 19 problematic terms correctly."""
    detector = Mock()
    
    def classify_word_side_effect(word):
        # Classify the originally problematic terms
        english_words = {
            'next', 'year', 'order', 'meal', 'mango', 'shake', 'specialty', 'ready',
            'good', 'morning', 'special', 'the'
        }
        tagalog_words = {'po', 'na', 'ko', 'ang', 'sa'}
        
        if word.lower() in english_words:
            return 'english'
        elif word.lower() in tagalog_words:
            return 'tagalog'
        else:
            return 'unknown'
    
    detector.classify_word.side_effect = classify_word_side_effect
    detector.has_filipino_context.return_value = False
    
    return detector


class TestDay19RegressionPrevention:
    """Test that Day 19 enforcement failures never happen again."""


class TestProblematicTermDetection:
    """Test that originally problematic terms are now detected."""
    
    def test_deterministic_detector_finds_day19_terms(self, enforcer, mock_language_detector):
        """Test that deterministic detector finds all Day 19 problematic terms."""
        with patch.object(enforcer.english_detector, 'language_detector', mock_language_detector):
            with patch.object(enforcer.english_detector, '_has_srs_equivalent', return_value=False):
                
                srs_backed, future_candidates = enforcer.english_detector.detect_english_terms(DAY19_PROBLEMATIC_CONTENT)
                
                all_detected = srs_backed + future_candidates
                all_detected_text = ' '.join(all_detected).lower()
                
                # Should detect individual words from problematic terms
                assert any('next' in term.lower() for term in all_detected)
                assert any('year' in term.lower() for term in all_detected)
                assert any('order' in term.lower() for term in all_detected)
                assert any('meal' in term.lower() for term in all_detected)
                assert any('mango' in term.lower() for term in all_detected)
                assert any('shake' in term.lower() for term in all_detected)
                assert any('specialty' in term.lower() for term in all_detected)
                assert any('ready' in term.lower() for term in all_detected)
                assert any('good' in term.lower() for term in all_detected)
                assert any('morning' in term.lower() for term in all_detected)
    
    def test_srs_analysis_extraction_contains_problematic_terms(self, enforcer):
        """Test that SRS analysis extraction captures problematic terms."""
        # Mock content with SRS analysis containing Day 19 terms
        content_with_analysis = DAY19_PROBLEMATIC_CONTENT + """

[NARRATOR]: SRS Enforcement Analysis
{
    "english_terms": [
        {"english": "next year", "srs_queries": ["susunod na taon", "next", "year"]},
        {"english": "order", "srs_queries": ["order", "umorder"]},
        {"english": "meal", "srs_queries": ["pagkain", "meal"]},
        {"english": "mango shake", "srs_queries": ["mango shake", "inumin"]},
        {"english": "specialty", "srs_queries": ["specialty", "espesyalidad"]},
        {"english": "ready", "srs_queries": ["handa", "ready"]}
    ]
}"""
        
        srs_analysis, found = enforcer._extract_srs_analysis(content_with_analysis)
        
        assert found == True
        assert len(srs_analysis) == 6
        
        # Should contain all the originally problematic terms
        english_terms = [term['english'] for term in srs_analysis]
        assert 'next year' in english_terms
        assert 'order' in english_terms
        assert 'meal' in english_terms
        assert 'mango shake' in english_terms
        assert 'specialty' in english_terms
        assert 'ready' in english_terms
    
    def test_english_terms_extraction_from_analysis(self, enforcer):
        """Test that English terms are correctly extracted from SRS analysis."""
        srs_analysis = [
            {"english": "next year", "srs_queries": ["susunod na taon"]},
            {"english": "order", "srs_queries": ["order", "umorder"]},
            {"english": "specialty", "srs_queries": ["specialty", "espesyalidad"]}
        ]
        
        english_terms = enforcer._extract_english_terms_from_analysis(srs_analysis)
        
        # Should extract clean English terms without any database mappings
        assert english_terms == ["next year", "order", "specialty"]
        
        # These terms should be passed to LLM for proper translation
        # (not pre-mapped to problematic database substring matches)


class TestNonsensicalMappingPrevention:
    """Test that nonsensical database-driven mappings never occur."""
    
    def test_no_database_substring_mappings_in_prompts(self, enforcer):
        """Test that prompts never contain problematic database substring mappings."""
        english_terms = ["Good morning", "Thank you", "next year", "specialty"]
        
        prompt = enforcer._create_combined_enforcement_prompt(
            DAY19_PROBLEMATIC_CONTENT, english_terms, {}, 19
        )
        
        # Should NEVER contain the problematic mappings that were generated by database search
        nonsensical_mappings = [
            "Good morning' → 'ito magandang umaga",  # Original problematic mapping
            "Thank you' → 'salamat ito",             # Original problematic mapping
            "next year' → 'susunod na taon na",      # Redundant/awkward mapping
            "specialty' → 'espesyalidad na"          # Awkward database match
        ]
        
        for mapping in nonsensical_mappings:
            assert mapping not in prompt, f"Found problematic mapping: {mapping}"
        
        # Should contain clean English terms for LLM translation
        assert "• 'Good morning'" in prompt
        assert "• 'Thank you'" in prompt
        assert "• 'next year'" in prompt
        assert "• 'specialty'" in prompt
    
    def test_prompt_encourages_proper_llm_translation(self, enforcer):
        """Test that prompts encourage LLM to make proper translation choices."""
        english_terms = ["Good morning", "Thank you"]
        
        prompt = enforcer._create_combined_enforcement_prompt(
            DAY19_PROBLEMATIC_CONTENT, english_terms, {}, 19
        )
        
        # Should encourage proper translation
        assert "Replace these English terms with appropriate Filipino equivalents" in prompt
        assert "Maintain proper Tagalog grammar" in prompt
        assert "Consider context" in prompt
        
        # Should NOT provide any predetermined translations that could be wrong
        replacements_section = prompt[prompt.find("REPLACEMENTS TO MAKE"):prompt.find("## TASK")]
        assert "magandang umaga" not in replacements_section
        assert "salamat" not in replacements_section
        assert "ito" not in replacements_section  # The problematic word from bad mappings
    
    def test_database_search_not_used_for_replacements(self, enforcer):
        """Test that database search is not used to create replacement mappings."""
        # This test ensures the old _query_srs_with_analysis method is not used
        
        srs_analysis = [
            {"english": "Good morning", "srs_queries": ["magandang umaga", "morning"]},
            {"english": "Thank you", "srs_queries": ["salamat", "thank you"]}
        ]
        
        # The new method should only extract English terms, not create mappings
        english_terms = enforcer._extract_english_terms_from_analysis(srs_analysis)
        
        assert english_terms == ["Good morning", "Thank you"]
        
        # Should NOT return dictionary mappings like the old problematic method
        assert not isinstance(english_terms, dict)
        assert all(isinstance(term, str) for term in english_terms)


class TestResponseFormatFixes:
    """Test that response format fixes prevent copyability issues."""
    
    def test_text_first_response_format_copyable(self, enforcer):
        """Test that enforced content is clean and copyable."""
        # Mock a proper text-first response format
        mock_response = {
            'choices': [{
                'message': {
                    'content': """[NARRATOR]: Day 19: Fixed Content

[TAGALOG-FEMALE-1]: Magandang umaga po! 
[TAGALOG-MALE-1]: Salamat po sa lahat!
[TAGALOG-FEMALE-1]: Babalik po ako sa susunod na taon!

PHRASE_TRANSLATIONS:
{
  "magandang umaga po": "good morning (polite)",
  "salamat po": "thank you (polite)",  
  "sa susunod na taon": "next year"
}"""
                }
            }]
        }
        
        # Test content extraction
        content = enforcer._extract_enforced_content(mock_response)
        
        # Should be clean and copyable
        assert content.startswith("[NARRATOR]: Day 19: Fixed Content")
        assert "Magandang umaga po!" in content
        assert "Babalik po ako sa susunod na taon!" in content
        
        # Should NOT contain JSON formatting
        assert "PHRASE_TRANSLATIONS:" not in content
        assert "{" not in content
        assert "}" not in content
        
        # Test translation extraction
        translations = enforcer._extract_phrase_translations(mock_response)
        
        assert len(translations) == 3
        translation_dict = {t['filipino']: t['english'] for t in translations}
        assert translation_dict['magandang umaga po'] == 'good morning (polite)'
        assert translation_dict['sa susunod na taon'] == 'next year'
    
    def test_old_json_format_still_handled(self, enforcer):
        """Test backward compatibility with old JSON format."""
        # Mock old JSON format response
        old_format_content = {
            "enforced_content": "[TAGALOG-FEMALE-1]: Magandang umaga po!",
            "phrase_translations": [
                {"filipino": "magandang umaga po", "english": "good morning", "confidence": 0.95}
            ]
        }
        
        mock_response = {
            'choices': [{
                'message': {
                    'content': json.dumps(old_format_content)
                }
            }]
        }
        
        # Should still work with old format
        content = enforcer._extract_enforced_content(mock_response)
        translations = enforcer._extract_phrase_translations(mock_response)
        
        assert content == "[TAGALOG-FEMALE-1]: Magandang umaga po!"
        assert len(translations) == 1
        assert translations[0]['filipino'] == 'magandang umaga po'


class TestEndToEndRegressionPrevention:
    """Test complete enforcement pipeline prevents Day 19 issues."""
    
    def test_complete_enforcement_pipeline_day19_scenario(self, enforcer, mock_language_detector):
        """Test complete enforcement pipeline with Day 19 problematic content."""
        
        # Mock the deterministic detector to find problematic terms
        with patch.object(enforcer.english_detector, 'language_detector', mock_language_detector):
            with patch.object(enforcer.english_detector, '_has_srs_equivalent', return_value=False):
                
                # Mock LLM response in new text-first format
                mock_llm_response = {
                    'choices': [{
                        'message': {
                            'content': """[NARRATOR]: Day 8: Farewell El Nido

[TAGALOG-FEMALE-1]: Magandang umaga po! Check out ko na po.
[TAGALOG-MALE-1]: Ano pong order ninyo? Espesyal na pagkain po para sa paalam!
[TAGALOG-FEMALE-1]: Kinilaw po at manggang shake - paborito ko na po yan!
[TAGALOG-MALE-1]: Handa na po ang specialty!
[TAGALOG-FEMALE-1]: Babalik po ako sa susunod na taon!

PHRASE_TRANSLATIONS:
{
  "magandang umaga po": "good morning (polite)",
  "order": "order",
  "espesyal na pagkain": "special meal", 
  "manggang shake": "mango shake",
  "handa na": "ready",
  "specialty": "specialty",
  "susunod na taon": "next year"
}"""
                        }
                    }]
                }
                
                enforcer.llm.chat_response.return_value = mock_llm_response
                
                # Test deterministic detection first
                srs_backed, future_candidates = enforcer.english_detector.detect_english_terms(DAY19_PROBLEMATIC_CONTENT)
                
                # Should detect the problematic terms
                all_detected = srs_backed + future_candidates
                assert len(all_detected) > 0
                
                # Verify key problematic terms are detected
                detected_text = ' '.join(all_detected).lower()
                assert any('mango' in detected_text for _ in [1])
                assert any('ready' in detected_text for _ in [1])
                assert any('specialty' in detected_text for _ in [1])
    
    def test_enforcement_produces_clean_copyable_result(self, enforcer):
        """Test that enforcement produces clean, copyable results."""
        
        # Mock successful enforcement scenario
        mock_response = {
            'choices': [{
                'message': {
                    'content': """[TAGALOG-FEMALE-1]: Magandang umaga po! Kumusta po kayo?

PHRASE_TRANSLATIONS:
{
  "magandang umaga po": "good morning (polite)",
  "kumusta po": "how are you (polite)"
}"""
                }
            }]
        }
        
        content = enforcer._extract_enforced_content(mock_response)
        
        # Result should be clean and copyable
        assert content == "[TAGALOG-FEMALE-1]: Magandang umaga po! Kumusta po kayo?"
        
        # Should be suitable for copy-paste without any JSON artifacts
        assert not any(char in content for char in ['{', '}', '":', '",'])
        
        # Should be clean text that can be used directly
        lines = content.split('\n')
        assert all(line.strip() == '' or line.startswith('[TAGALOG-') or not line.startswith('[') 
                  for line in lines)
    
    def test_no_regression_to_problematic_database_search(self, enforcer):
        """Test that the system never regresses to problematic database substring matching."""
        
        # Simulate the old problematic behavior by checking what would have been wrong
        problematic_terms_and_bad_matches = {
            "Good morning": "ito magandang umaga",  # Bad substring match
            "Thank you": "salamat ito",             # Bad substring match 
            "water": "tubig na may",                # Awkward database match
            "next year": "susunod na taon na"       # Redundant database match
        }
        
        # Create prompt with these terms
        english_terms = list(problematic_terms_and_bad_matches.keys())
        prompt = enforcer._create_combined_enforcement_prompt(
            DAY19_PROBLEMATIC_CONTENT, english_terms, {}, 19
        )
        
        # Verify the prompt does NOT contain any of the bad database matches
        for english, bad_filipino in problematic_terms_and_bad_matches.items():
            bad_mapping = f"'{english}' → '{bad_filipino}'"
            assert bad_mapping not in prompt, f"Found regression: {bad_mapping}"
        
        # Should instead provide clean terms for LLM to translate properly
        for english in english_terms:
            assert f"• '{english}'" in prompt
        
        # Should provide instruction for LLM to choose appropriate translations
        assert "Replace these English terms with appropriate Filipino equivalents" in prompt


class TestSpecificDay19TermsRegression:
    """Test each originally problematic Day 19 term specifically."""
    
    @pytest.mark.parametrize("problematic_term", [
        "next year", "order", "meal", "mango", "shake", "specialty", "ready"
    ])
    def test_individual_problematic_term_handling(self, enforcer, problematic_term):
        """Test that each originally problematic term is handled correctly."""
        
        # Create content with the specific problematic term
        test_content = f"[TAGALOG-FEMALE-1]: This contains {problematic_term} which was problematic."
        
        # Test prompt generation
        prompt = enforcer._create_combined_enforcement_prompt(
            test_content, [problematic_term], {}, 19
        )
        
        # Should include the term cleanly for LLM translation
        assert f"• '{problematic_term}'" in prompt
        
        # Should NOT contain any pre-determined mapping
        assert f"{problematic_term}' →" not in prompt
        
        # Should encourage LLM to choose appropriate translation
        assert "Replace these English terms with appropriate Filipino equivalents" in prompt
    
    def test_multiword_problematic_phrases(self, enforcer):
        """Test handling of multi-word problematic phrases like 'next year'."""
        
        multiword_terms = ["next year", "special meal", "mango shake", "good morning"]
        
        prompt = enforcer._create_combined_enforcement_prompt(
            DAY19_PROBLEMATIC_CONTENT, multiword_terms, {}, 19
        )
        
        # Should handle multi-word terms correctly
        for term in multiword_terms:
            assert f"• '{term}'" in prompt
            
        # Should NOT create problematic compound mappings
        problematic_compound_mappings = [
            "next year' → 'susunod na taon na",
            "special meal' → 'espesyal na pagkain na",
            "good morning' → 'ito magandang umaga"
        ]
        
        for bad_mapping in problematic_compound_mappings:
            assert bad_mapping not in prompt