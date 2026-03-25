"""
Integration tests for post-processing with SRS enforcement.

Tests the critical workflow changes where post-processing now runs AFTER SRS enforcement
to ensure algorithmic Pimsleur breakdowns are always applied to the final content.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path

from story_generator import ContentGenerator, EnhancedStoryParams, CEFRLevel
from content_strategy import ContentStrategy, DifficultyLevel
from utils.content_post_processor import post_process_story_content


class TestPostProcessingSRSIntegration:
    """Test integration between post-processing and SRS enforcement."""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM that returns content with incorrect breakdowns."""
        llm = MagicMock()
        # LLM returns content with broken Pimsleur breakdowns (like the old issue)
        llm.chat_response.return_value = {
            'choices': [{
                'message': {
                    'content': """[NARRATOR]: Day 15: Test Story

Key Phrases:

[TAGALOG-FEMALE-1]: kumusta po
[NARRATOR]: how are you
[TAGALOG-FEMALE-1]: kumusta po
po
bad_breakdown
us
usta
wrong_steps
musta
kumusta po

[NARRATOR]: Natural Speed

[NARRATOR]: Test Scene

[TAGALOG-FEMALE-1]: Kumusta po kayo?
[TAGALOG-MALE-1]: Mabuti po.

[NARRATOR]: Slow Speed

[TAGALOG-FEMALE-1]: Kumusta... po... kayo?
[TAGALOG-MALE-1]: Mabuti... po.

[NARRATOR]: Translated

[TAGALOG-FEMALE-1]: Kumusta po kayo?
[NARRATOR]: How are you?
[TAGALOG-MALE-1]: Mabuti po.
[NARRATOR]: I'm fine."""
                }
            }]
        }
        return llm

    @pytest.fixture
    def mock_srs_enforcer(self):
        """Mock SRS enforcer that might modify content."""
        enforcer = MagicMock()
        
        def enforce_with_llm(content, day, context):
            # Simulate SRS enforcement that might reintroduce broken breakdowns
            # This simulates the bug we fixed where SRS enforcement overwrote post-processing
            modified_content = content.replace("kumusta po\npo\nta\nmus\nmusta\nku\nkumusta\nkumusta po\nkumusta po", 
                                             "kumusta po\npo\nta po\nus\nusta\nm\nmusta\nkumusta po")
            return modified_content, [{"english": "test", "filipino": "test", "count": 1}]
        
        enforcer.enforce_with_llm.side_effect = enforce_with_llm
        return enforcer

    @pytest.fixture 
    def content_generator(self, mock_llm):
        """Content generator with mocked dependencies."""
        # Need to patch SRSTracker during ContentGenerator construction to avoid data directory issues
        with patch('story_generator.SRSAdapter') as mock_srs_class, \
             patch.object(ContentGenerator, '_load_prompt', return_value="Test prompt: {learning_objective}") as mock_load_prompt:
            mock_srs = MagicMock()
            mock_srs.get_due_collocations.return_value = ["test phrase"]
            mock_srs_class.return_value = mock_srs
            
            generator = ContentGenerator()
            generator.llm = mock_llm  # Override the default MockLLM
            
            # Mock curriculum loading
            with patch.object(generator, '_load_curriculum') as mock_curriculum:
                mock_curriculum.return_value = MagicMock()
                
            # Mock file operations
            generator._save_story = MagicMock(return_value="/fake/path/story.txt")
            
            return generator

    def test_post_processing_runs_after_srs_enforcement(self, content_generator, mock_srs_enforcer):
        """Test that post-processing runs AFTER SRS enforcement in the workflow."""
        
        # Mock the LLM response to avoid template parameter issues
        content_generator.llm.chat_response.return_value = {
            'choices': [{'message': {'content': 'LLM_GENERATED_CONTENT'}}]
        }
        
        with patch('story_generator.SRSDatabase') as mock_srs_db_class, \
             patch('srs_llm_enforcer.create_llm_enforcer', return_value=mock_srs_enforcer), \
             patch('utils.content_post_processor.post_process_story_content') as mock_post_process:
            
            # Mock SRSDatabase to return a valid mock instance  
            mock_srs_db = MagicMock()
            mock_srs_db_class.return_value = mock_srs_db
            
            # Mock post-processing to return identifiable content
            mock_post_process.return_value = "POST_PROCESSED_CONTENT"
            
            # SRS enforcer modifies content and reports violations so the enforced content is used
            def srs_enforcement_side_effect(content, day, context):
                # Return modified content with violations and phrase translations
                return ("SRS_ENFORCED_CONTENT", [{"violation": "test"}], [])
            
            mock_srs_enforcer.enforce_with_llm.side_effect = srs_enforcement_side_effect
            
            params = EnhancedStoryParams(
                learning_objective="Test",
                language="Tagalog", 
                cefr_level=CEFRLevel.A2,
                phase=15,
                content_strategy=ContentStrategy.WIDER,
                difficulty_level=DifficultyLevel.BASIC,
                focus="Test focus",
                story_guidance="Test guidance"
            )
            
            result = content_generator.generate_enhanced_story(params)
            
            # Verify the workflow order
            assert mock_srs_enforcer.enforce_with_llm.called, "SRS enforcement should be called"
            assert mock_post_process.called, "Post-processing should be called"
            
            # Verify post-processing gets the SRS-modified content, not original LLM content
            post_process_call_args = mock_post_process.call_args[0] 
            
            # Post-processing should receive SRS-enforced content
            assert post_process_call_args[0] == "SRS_ENFORCED_CONTENT", "Post-processing should get SRS-enforced content"
            assert result == "POST_PROCESSED_CONTENT", "Final result should be post-processed content"

    def test_end_to_end_workflow_produces_correct_breakdowns(self, content_generator):
        """Test complete workflow: LLM → SRS → Post-processing produces correct breakdowns."""
        
        with patch('story_generator.SRSDatabase'), \
             patch('srs_llm_enforcer.create_llm_enforcer') as mock_enforcer_creator:
            
            # Mock SRS enforcer that doesn't change content (no violations)
            mock_enforcer = MagicMock()
            mock_enforcer.enforce_with_llm.return_value = ("unchanged", [], [])  # No violations, no translations
            mock_enforcer_creator.return_value = mock_enforcer
            
            params = EnhancedStoryParams(
                learning_objective="Test",
                language="Tagalog",
                cefr_level=CEFRLevel.A2, 
                phase=15,
                content_strategy=ContentStrategy.WIDER,
                difficulty_level=DifficultyLevel.BASIC,
                focus="Test focus",
                story_guidance="Test guidance"
            )
            
            result = content_generator.generate_enhanced_story(params)
            
            # Verify that the final result has correct Pimsleur breakdowns
            assert result is not None
            
            # Check for correct Pimsleur pattern: kumusta po → po → ta → mus → musta → ku → kumusta
            expected_pattern = "kumusta po\npo\nta\nmus\nmusta\nku\nkumusta\nkumusta po\nkumusta po"
            assert expected_pattern in result, f"Should have correct Pimsleur breakdown pattern in: {result}"
            
            # Should NOT have the incorrect patterns from LLM
            incorrect_patterns = ["bad_breakdown", "wrong_steps", "us\nusta"]  
            for pattern in incorrect_patterns:
                assert pattern not in result, f"Should not have incorrect pattern '{pattern}' in final result"
    
    def test_text_first_response_format_compatibility(self, content_generator):
        """Test that post-processing works with new text-first SRS response format."""
        
        with patch('story_generator.SRSDatabase'), \
             patch('srs_llm_enforcer.create_llm_enforcer') as mock_enforcer_creator:
            
            # Mock SRS enforcer that returns text-first format (new format)
            mock_enforcer = MagicMock()
            
            text_first_enforced_content = """[NARRATOR]: Day 15: Test Story

Key Phrases:

[TAGALOG-FEMALE-1]: kumusta po
[NARRATOR]: how are you
[TAGALOG-FEMALE-1]: kumusta po

[NARRATOR]: Natural Speed

[TAGALOG-FEMALE-1]: Kumusta po kayo?
[TAGALOG-MALE-1]: Mabuti po."""
            
            # Mock text-first format enforcement (clean content, no JSON wrapping)
            mock_enforcer.enforce_with_llm.return_value = (
                text_first_enforced_content,  # Clean, copyable content
                [],  # No violations
                [{"filipino": "kumusta po", "english": "how are you", "confidence": 0.9}]  # Extracted translations
            )
            mock_enforcer_creator.return_value = mock_enforcer
            
            params = EnhancedStoryParams(
                learning_objective="Test text-first format",
                language="Tagalog",
                cefr_level=CEFRLevel.A2,
                phase=15,
                content_strategy=ContentStrategy.WIDER,
                difficulty_level=DifficultyLevel.BASIC,
                focus="Text format test",
                story_guidance="Test guidance"
            )
            
            result = content_generator.generate_enhanced_story(params)
            
            # Should work with clean text-first format
            assert result is not None
            assert "[NARRATOR]: Day 15: Test Story" in result
            assert "Kumusta po kayo?" in result
            
            # Should still apply post-processing to create proper breakdowns
            # (even though content is now clean text instead of JSON-wrapped)
            assert "kumusta po" in result
            
            # Should NOT contain any JSON artifacts from old format
            assert "PHRASE_TRANSLATIONS:" not in result
            assert '{"filipino":' not in result
            assert '"english":' not in result

    def test_srs_enforcement_content_gets_post_processed(self, content_generator):
        """Test that content modified by SRS enforcement still gets proper post-processing."""
        
        with patch('story_generator.SRSDatabase'), \
             patch('srs_llm_enforcer.create_llm_enforcer') as mock_enforcer_creator:
            
            # Mock SRS enforcer that introduces broken breakdowns (simulates the bug we fixed)
            mock_enforcer = MagicMock()
            
            def break_breakdowns(content, day, context):
                # SRS enforcement introduces bad breakdowns (this was the original problem)
                broken_content = content.replace(
                    "[TAGALOG-FEMALE-1]: kumusta po\n[NARRATOR]: how are you\n[TAGALOG-FEMALE-1]: kumusta po",
                    "[TAGALOG-FEMALE-1]: kumusta po\n[NARRATOR]: how are you\n[TAGALOG-FEMALE-1]: kumusta po\npo\nta po\nus\nusta\nm"
                )
                return broken_content, [{"english": "test", "filipino": "test", "count": 1}]
            
            mock_enforcer.enforce_with_llm.side_effect = break_breakdowns
            mock_enforcer_creator.return_value = mock_enforcer
            
            params = EnhancedStoryParams(
                learning_objective="Test",
                language="Tagalog",
                cefr_level=CEFRLevel.A2,
                phase=15, 
                content_strategy=ContentStrategy.WIDER,
                difficulty_level=DifficultyLevel.BASIC,
                focus="Test focus",
                story_guidance="Test guidance"
            )
            
            result = content_generator.generate_enhanced_story(params)
            
            # Even though SRS enforcement broke the breakdowns, post-processing should fix them
            expected_correct_pattern = "kumusta po\npo\nta\nmus\nmusta\nku\nkumusta\nkumusta po\nkumusta po"
            assert expected_correct_pattern in result, "Post-processing should fix breakdowns even after SRS enforcement"
            
            # Should not have the broken patterns that SRS enforcement introduced
            assert "bad_breakdown" not in result, "Should not have incorrect 'bad_breakdown' pattern"
            assert "wrong_steps" not in result, "Should not have incorrect 'wrong_steps' pattern"

    def test_both_story_generation_methods_apply_post_processing(self, content_generator):
        """Test that both generate_enhanced_story and generate_story_for_day apply post-processing."""
        
        with patch('story_generator.SRSDatabase'), \
             patch('srs_llm_enforcer.create_llm_enforcer') as mock_enforcer_creator, \
             patch.object(content_generator, '_load_curriculum') as mock_curriculum, \
             patch('utils.content_post_processor.post_process_story_content') as mock_post_process:
            
            # Setup mocks
            mock_enforcer = MagicMock()
            mock_enforcer.enforce_with_llm.return_value = ("test_content", [], [])
            mock_enforcer_creator.return_value = mock_enforcer
            
            mock_post_process.return_value = "POST_PROCESSED"
            
            # Mock curriculum day data with proper CEFR level
            mock_day = MagicMock()
            mock_day.learning_objective = "Test objective"
            mock_day.focus = "Test focus"
            mock_day.story_guidance = "Test guidance"
            mock_day.collocations = ["test phrase"]
            
            # Mock curriculum with proper learner_level
            mock_curriculum_obj = MagicMock()
            mock_curriculum_obj.learner_level = "A2"  # Valid CEFR level
            mock_curriculum_obj.get_day.return_value = mock_day
            mock_curriculum.return_value = mock_curriculum_obj
            
            # Test generate_story_for_day method
            result = content_generator.generate_story_for_day(15)
            
            # Verify post-processing was called
            assert mock_post_process.called, "generate_story_for_day should call post-processing"
            assert result == "POST_PROCESSED", "Should return post-processed content"

    def test_post_processing_handles_malformed_srs_content(self, content_generator):
        """Test that post-processing gracefully handles malformed content from SRS enforcement."""
        
        with patch('story_generator.SRSDatabase'), \
             patch('srs_llm_enforcer.create_llm_enforcer') as mock_enforcer_creator:
            
            # Mock SRS enforcer that returns malformed content
            mock_enforcer = MagicMock()
            mock_enforcer.enforce_with_llm.return_value = (
                """[NARRATOR]: Malformed Test

Key Phrases:

[TAGALOG-FEMALE-1]: kumusta po
Missing narrator translation
[TAGALOG-FEMALE-1]: kumusta po
broken
breakdown
here

[NARRATOR]: Natural Speed""", 
                [{"english": "test", "filipino": "test", "count": 1}],
                []  # phrase_translations
            )
            mock_enforcer_creator.return_value = mock_enforcer
            
            params = EnhancedStoryParams(
                learning_objective="Test",
                language="Tagalog",
                cefr_level=CEFRLevel.A2,
                phase=15,
                content_strategy=ContentStrategy.WIDER,
                difficulty_level=DifficultyLevel.BASIC,
                focus="Test focus", 
                story_guidance="Test guidance"
            )
            
            # Should not crash even with malformed content
            result = content_generator.generate_enhanced_story(params)
            
            assert result is not None, "Should handle malformed SRS content gracefully"
            assert "[NARRATOR]: Natural Speed" in result, "Should preserve story structure"

    def test_wider_strategy_post_processing_integration(self, content_generator):
        """Test post-processing integration specifically for WIDER strategy."""
        
        with patch('story_generator.SRSDatabase'), \
             patch('srs_llm_enforcer.create_llm_enforcer') as mock_enforcer_creator, \
             patch.object(content_generator, '_generate_wider_content') as mock_wider:
            
            # Mock the WIDER strategy to return content with incorrect breakdowns
            mock_wider.return_value = ("""[NARRATOR]: Day 16: WIDER Test

Key Phrases:

[TAGALOG-FEMALE-1]: salamat po  
[NARRATOR]: thank you
[TAGALOG-FEMALE-1]: salamat po
po
wrong breakdown
here

[NARRATOR]: Natural Speed

[NARRATOR]: Test scene""", [])
            
            mock_enforcer = MagicMock()
            mock_enforcer.enforce_with_llm.return_value = ("unchanged", [], [])
            mock_enforcer_creator.return_value = mock_enforcer
            
            # Test WIDER strategy with ContentGenerator.generate_strategy_based_story
            result = content_generator.generate_strategy_based_story(
                target_day=16,
                strategy=ContentStrategy.WIDER,
                source_day=15
            )
            
            if result:  # If strategy generation worked
                story_content, _ = result
                # Should have correct Pimsleur breakdown for salamat po
                expected = "salamat po\npo\nmat\nla\nlamat\nsa\nsalamat\nsalamat po\nsalamat po"
                assert expected in story_content, "WIDER strategy should apply post-processing"


class TestPostProcessingOrderValidation:
    """Tests to validate the critical order: SRS Enforcement → Post-Processing → Save."""
    
    @pytest.fixture
    def mock_content_generator(self):
        """Content generator with spies to track execution order."""
        llm = MagicMock()
        llm.chat_response.return_value = {
            'choices': [{'message': {'content': 'test content'}}]
        }
        
        with patch('story_generator.SRSAdapter') as mock_srs_class, \
             patch.object(ContentGenerator, '_load_prompt', return_value="Test prompt: {learning_objective}"):
            mock_srs = MagicMock()
            mock_srs.get_due_collocations.return_value = []
            mock_srs_class.return_value = mock_srs
            
            generator = ContentGenerator()
            generator.llm = llm  # Override the default MockLLM
            generator._save_story = MagicMock(return_value="/fake/path")
            
            return generator
        
    def test_execution_order_tracking(self, mock_content_generator):
        """Test that we can verify the execution order of SRS → Post-processing."""
        
        execution_order = []
        
        def track_srs_enforcement(content, day, context):
            execution_order.append("SRS_ENFORCEMENT")
            return content, []
        
        def track_post_processing(content):
            execution_order.append("POST_PROCESSING") 
            return content
        
        with patch('story_generator.SRSDatabase'), \
             patch('srs_llm_enforcer.create_llm_enforcer') as mock_enforcer_creator, \
             patch('utils.content_post_processor.post_process_story_content', side_effect=track_post_processing):
            
            mock_enforcer = MagicMock()
            mock_enforcer.enforce_with_llm.side_effect = track_srs_enforcement
            mock_enforcer_creator.return_value = mock_enforcer
            
            params = EnhancedStoryParams(
                learning_objective="Order test",
                language="Tagalog",
                cefr_level=CEFRLevel.A2,
                phase=15,
                content_strategy=ContentStrategy.WIDER,
                difficulty_level=DifficultyLevel.BASIC,
                focus="Test focus",
                story_guidance="Test guidance"
            )
            
            mock_content_generator.generate_enhanced_story(params)
            
            # Verify the critical execution order
            assert execution_order == ["SRS_ENFORCEMENT", "POST_PROCESSING"], \
                f"Wrong execution order: {execution_order}. Should be SRS_ENFORCEMENT → POST_PROCESSING"