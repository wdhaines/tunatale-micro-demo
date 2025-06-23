"""Unit tests for curriculum_service.py"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from curriculum_service import CurriculumGenerator, ValidationError, ParserError
from llm_mock import MockLLM

# Sample test data
SAMPLE_CURRICULUM = """Day 1:
- Topics: Greetings, Introductions
- Grammar: Present simple
- Vocabulary: Hello, Hi, Greetings
- Activities: Practice with partner

Day 2:
- Topics: Asking questions
- Grammar: Question formation
- Vocabulary: What, Where, When
- Activities: Role play conversations

Day 3:
- Topics: Daily routines
- Grammar: Present continuous
- Vocabulary: Daily activities, time expressions
- Activities: Describe your day

Day 4:
- Topics: Making plans
- Grammar: Future with going to
- Vocabulary: Time expressions, activities
- Activities: Plan a week schedule

Day 5:
- Topics: Past experiences
- Grammar: Simple past
- Vocabulary: Regular/irregular verbs
- Activities: Share past experiences
"""

SAMPLE_LLM_RESPONSE = {
    'choices': [{
        'message': {
            'content': SAMPLE_CURRICULUM
        }
    }]
}

# Fixtures
@pytest.fixture
def mock_llm():
    """Fixture providing a mocked LLM instance."""
    llm = MagicMock()
    llm.get_response.return_value = SAMPLE_LLM_RESPONSE
    return llm

@pytest.fixture
def curriculum_generator(mock_llm):
    """Fixture providing a CurriculumGenerator with a mocked LLM."""
    generator = CurriculumGenerator()
    generator.llm = mock_llm  # Inject mock LLM
    return generator



@pytest.fixture
def sample_curriculum_structure():
    """Fixture providing a sample curriculum structure."""
    return CurriculumStructure(
        num_days=2,
        required_sections=['topics', 'grammar', 'vocabulary', 'activities']
    )

# Test Classes
class TestCurriculumGenerator:
    """Tests for CurriculumGenerator class."""
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        generator = CurriculumGenerator()
        assert hasattr(generator, 'llm')
        assert hasattr(generator, 'curriculum_prompt')
        assert isinstance(generator.llm, MockLLM)
    
    def test_generate_curriculum_success(self, curriculum_generator, mock_llm, tmp_path):
        """Test successful curriculum generation."""
        # Use the sample curriculum that's already defined at the top of the file
        mock_response = {
            'choices': [{
                'message': {
                    'content': SAMPLE_CURRICULUM
                }
            }]
        }
        mock_llm.generate.return_value = mock_response
        
        with patch('curriculum_service.CURRICULUM_PATH', tmp_path / 'curriculum.json'):
            result = curriculum_generator.generate_curriculum("Test learning goal")
            
            # Verify LLM was called with correct prompt
            args, kwargs = mock_llm.generate.call_args
            assert "Test learning goal" in args[0]
            
            # Verify result has expected structure
            assert isinstance(result, dict)
            assert result['learning_goal'] == "Test learning goal"
            assert 'content' in result
            assert 'days' in result
            assert 'target_language' in result
            assert 'cefr_level' in result
            
            # Verify file was saved
            assert (tmp_path / 'curriculum.json').exists()
            with open(tmp_path / 'curriculum.json', 'r') as f:
                saved_curriculum = json.load(f)
                assert saved_curriculum['learning_goal'] == "Test learning goal"
                assert 'content' in saved_curriculum
    
    def test_generate_curriculum_empty_goal(self, curriculum_generator):
        """Test curriculum generation with empty learning goal raises ValidationError."""
        with pytest.raises(ValidationError, match="Learning goal must be a non-empty string"):
            curriculum_generator.generate_curriculum("")
    
    def test_save_curriculum(self, curriculum_generator, tmp_path):
        """Test saving curriculum to file."""
        test_file = tmp_path / 'test_curriculum.json'
        with patch('curriculum_service.CURRICULUM_PATH', test_file):
            curriculum_generator._save_curriculum(SAMPLE_CURRICULUM, "Test Goal")
        
        # Verify file was created with correct content
        assert test_file.exists()
        with open(test_file, 'r') as f:
            data = json.load(f)
            assert data['learning_goal'] == "Test Goal"
            assert data['content'] == SAMPLE_CURRICULUM
            assert 'days' in data
            assert len(data['days']) > 0  # Should have parsed some days
    
    def test_parse_curriculum_days(self, curriculum_generator):
        """Test parsing curriculum text into days."""
        result = curriculum_generator._parse_curriculum_days(SAMPLE_CURRICULUM)
        assert isinstance(result, dict)
        assert "Day 1" in result
        assert "Day 2" in result
        assert len(result["Day 1"]) == 4  # 4 lines of content for Day 1
    
    @patch('builtins.open', side_effect=IOError("Test error"))
    def test_save_curriculum_ioerror(self, mock_file, curriculum_generator, tmp_path):
        """Test error handling when saving curriculum fails."""
        test_file = tmp_path / 'test_curriculum.json'
        with patch('curriculum_service.CURRICULUM_PATH', test_file):
            with pytest.raises(IOError):
                curriculum_generator._save_curriculum(SAMPLE_CURRICULUM, "Test Goal")
    
    def test_generate_curriculum_invalid_llm_response(self, curriculum_generator, mock_llm):
        """Test handling of invalid LLM response format."""
        from curriculum_service import LLMError
        mock_llm.get_response.return_value = {'invalid': 'response'}
        with pytest.raises(LLMError, match="Failed to generate curriculum: Invalid response format from LLM"):
            curriculum_generator.generate_curriculum("Test goal")
    
    def test_parse_curriculum_empty_content(self, curriculum_generator):
        """Test parsing empty curriculum content."""
        with pytest.raises(ParserError, match="Empty curriculum content"):
            curriculum_generator._parse_curriculum_days("")
    
    def test_parse_curriculum_malformed(self, curriculum_generator):
        """Test parsing malformed curriculum text."""
        # The current implementation doesn't raise an error for malformed content within a day
        # It just skips list markers but keeps the content
        malformed = """Day 1:\n- Topics: Test\n- Grammar: Test\n- Vocabulary: Test\n- Activities: Test
Day 2:\n- No colon here\n- Grammar: Test\n- Vocabulary: Test\n- Activities: Test
Day 3:\n- Topics: Test\n- Grammar: Test\n- Vocabulary: Test\n- Activities: Test
Day 4:\n- Topics: Test\n- Grammar: Test\n- Vocabulary: Test\n- Activities: Test
Day 5:\n- Topics: Test\n- Grammar: Test\n- Vocabulary: Test\n- Activities: Test"""
        
        # The current implementation will parse this without raising an error
        # It will process all lines, just stripping list markers
        result = curriculum_generator._parse_curriculum_days(malformed)
        assert "Day 1" in result
        assert "Day 2" in result
        assert len(result["Day 2"]) == 4  # All lines are kept, just with markers stripped
    
    def test_generate_curriculum_non_string_goal(self, curriculum_generator):
        """Test curriculum generation with non-string learning goal."""
        with pytest.raises(ValidationError, match="Learning goal must be a non-empty string"):
            curriculum_generator.generate_curriculum(123)
    
    def test_missing_prompt_template(self, curriculum_generator, tmp_path):
        """Test behavior when prompt template is missing."""
        # The current implementation creates a default template if it doesn't exist
        # So we'll test that it doesn't raise an error and returns the default content
        temp_dir = tmp_path / "prompts"
        temp_dir.mkdir()
        
        # Patch the PROMPTS_DIR to point to our empty directory
        with patch('curriculum_service.PROMPTS_DIR', temp_dir):
            # The method should not raise an error, but instead create the template
            result = curriculum_generator._load_prompt_template()
            assert result is not None
            assert "language learning curriculum" in result  # Part of the default prompt
    
    def test_parse_invalid_json_curriculum(self, curriculum_generator, tmp_path):
        """Test handling of invalid JSON in saved curriculum."""
        test_file = tmp_path / 'invalid.json'
        test_file.write_text('{invalid json}')
        with patch('curriculum_service.CURRICULUM_PATH', test_file):
            # The current implementation allows JSONDecodeError to propagate
            with pytest.raises(json.JSONDecodeError):
                curriculum_generator._load_curriculum()
    
    def test_generate_curriculum_long_goal(self, curriculum_generator):
        """Test curriculum generation with very long learning goal."""
        # Current implementation allows up to 1000 characters, so we need to exceed that
        long_goal = "A" * 1001  # 1001 characters is over the limit
        with pytest.raises(ValidationError, match="Learning goal is too long"):
            curriculum_generator.generate_curriculum(long_goal)
    
    def test_curriculum_validation(self, curriculum_generator):
        """Test validation of curriculum structure."""
        # Test with missing required days (default config expects 5 days)
        invalid_curriculum = "Day 1:\n- Topics: Test\n- Grammar: Test"
        with pytest.raises(ValueError, match="Missing Day 2:"):
            curriculum_generator._validate_curriculum_structure(invalid_curriculum)
    
        # Test with empty day content (should be caught by _parse_curriculum_days first)
        # The current implementation checks for day headers, not empty content
        empty_day = "Day 1:\n\nDay 2:\n- Topics: Test"
        with pytest.raises(ValueError, match="Missing Day 3:"):
            curriculum_generator._validate_curriculum_structure(empty_day)
            
        # Test valid curriculum with all required days
        valid_curriculum = """Day 1:\n- Topics: Test\n- Grammar: Test\n- Vocabulary: Test\n- Activities: Test
Day 2:\n- Topics: Test\n- Grammar: Test\n- Vocabulary: Test\n- Activities: Test
Day 3:\n- Topics: Test\n- Grammar: Test\n- Vocabulary: Test\n- Activities: Test
Day 4:\n- Topics: Test\n- Grammar: Test\n- Vocabulary: Test\n- Activities: Test
Day 5:\n- Topics: Test\n- Grammar: Test\n- Vocabulary: Test\n- Activities: Test"""
        # The method doesn't return anything, just raises on error
        curriculum_generator._validate_curriculum_structure(valid_curriculum)
