import pytest
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
from story_generator import ContentGenerator, StoryParams, CEFRLevel
from llm_mock import MockLLM

class TestStoryGeneratorVocab:
    @patch('story_generator.MockLLM')
    @patch.object(ContentGenerator, '_load_prompt', return_value='test prompt')
    def test_generate_story_with_vocabulary(self, mock_load_prompt, mock_llm_class, tmp_path):
        """Test that vocabulary parameters are correctly passed to the prompt template."""
        # Setup
        mock_llm = Mock()
        mock_llm.get_response.return_value = {
            'choices': [{'message': {'content': 'Test story content'}}]
        }
        mock_llm_class.return_value = mock_llm
        
        generator = ContentGenerator()
        generator.llm = mock_llm
        
        # Create test parameters with vocabulary
        params = StoryParams(
            learning_objective="test objective",
            language="English",
            cefr_level=CEFRLevel.A1,
            phase=1,
            length=100,
            new_vocabulary=["vocab1", "vocab2"],
            recycled_vocabulary=["recycled1"],
            recycled_collocations=["collocation1", "collocation2"]
        )
        
        # Call the method
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file
            
            result = generator.generate_story(params)
        
        # Assertions
        assert result == 'Test story content'
        
        # Get the prompt that was passed to the LLM
        call_args = mock_llm.get_response.call_args
        
        # The prompt could be passed as a positional or keyword argument
        prompt = None
        if call_args[0]:  # Check positional args
            prompt = call_args[0][0]
        elif 'prompt' in call_args[1]:  # Check keyword args
            prompt = call_args[1]['prompt']
            
        assert prompt is not None, "Prompt was not passed to get_response"
        
        # With the mocked _load_prompt, we should just see 'test prompt'
        assert prompt == 'test prompt'
        
    @patch('story_generator.MockLLM')
    @patch.object(ContentGenerator, '_load_prompt', return_value='test prompt')
    def test_generate_story_with_empty_vocabulary(self, mock_load_prompt, mock_llm_class, tmp_path):
        """Test that empty vocabulary parameters are handled correctly."""
        # Setup
        mock_llm = Mock()
        mock_llm.get_response.return_value = {
            'choices': [{'message': {'content': 'Test story content'}}]
        }
        mock_llm_class.return_value = mock_llm
        
        generator = ContentGenerator()
        generator.llm = mock_llm
        
        # Create test parameters with empty vocabulary
        params = StoryParams(
            learning_objective="test objective",
            language="English",
            cefr_level=CEFRLevel.A1,
            phase=1,
            length=100,
            new_vocabulary=[],
            recycled_vocabulary=None,
            recycled_collocations=[]
        )
        
        # Call the method
        with patch('builtins.open', create=True):
            result = generator.generate_story(params)
               
        # Get the prompt that was passed to the LLM
        call_args = mock_llm.get_response.call_args
        
        # The prompt could be passed as a positional or keyword argument
        prompt = None
        if call_args[0]:  # Check positional args
            prompt = call_args[0][0]
        elif 'prompt' in call_args[1]:  # Check keyword args
            prompt = call_args[1]['prompt']
            
        assert prompt is not None, "Prompt was not passed to get_response"
        
        # With the mocked _load_prompt, we should just see 'test prompt'
        assert prompt == 'test prompt'
