"""Unit tests for curriculum_service.py"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from curriculum_service import CurriculumGenerator, ValidationError
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
        with patch('curriculum_service.CURRICULUM_PATH', tmp_path / 'curriculum.json'):
            result = curriculum_generator.generate_curriculum("Test learning goal")
            
            # Verify LLM was called with correct prompt
            args, kwargs = mock_llm.get_response.call_args
            assert "Test learning goal" in kwargs['prompt']
            assert kwargs['response_type'] == "curriculum"
            
            # Verify result matches expected curriculum
            assert result == SAMPLE_CURRICULUM
            
            # Verify file was saved
            assert (tmp_path / 'curriculum.json').exists()
    
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
        mock_llm.get_response.return_value = {'invalid': 'response'}
        with pytest.raises(ValueError, match="Invalid response format from LLM"):
            curriculum_generator.generate_curriculum("Test goal")
    
    def test_parse_curriculum_empty_content(self, curriculum_generator):
        """Test parsing empty curriculum content."""
        with pytest.raises(ValueError, match="Empty curriculum content"):
            curriculum_generator._parse_curriculum_days("")
    
    def test_parse_curriculum_malformed(self, curriculum_generator):
        """Test parsing malformed curriculum text."""
        malformed = "Day 1:\n- No colon here"
        with pytest.raises(ValueError, match="Failed to parse curriculum"):
            curriculum_generator._parse_curriculum_days(malformed)
    
    def test_generate_curriculum_non_string_goal(self, curriculum_generator):
        """Test curriculum generation with non-string learning goal."""
        with pytest.raises(ValidationError, match="must be a string"):
            curriculum_generator.generate_curriculum(123)
    
    @patch('pathlib.Path.exists', return_value=False)
    @patch('pathlib.Path.mkdir')
    @patch('builtins.open', new_callable=mock_open, read_data="")
    def test_missing_prompt_template(self, mock_file, mock_mkdir, mock_exists, curriculum_generator):
        """Test behavior when prompt template is missing."""
        with patch('pathlib.Path.read_text', side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                curriculum_generator._load_prompt_template()
    
    @patch('json.loads')
    def test_parse_invalid_json_curriculum(self, mock_json, curriculum_generator, tmp_path):
        """Test handling of invalid JSON in saved curriculum."""
        test_file = tmp_path / 'invalid.json'
        test_file.write_text('{invalid json}')
        with patch('curriculum_service.CURRICULUM_PATH', test_file):
            with pytest.raises(json.JSONDecodeError):
                curriculum_generator._load_curriculum()
    
    def test_generate_curriculum_long_goal(self, curriculum_generator):
        """Test curriculum generation with very long learning goal."""
        long_goal = "A" * 1000
        with pytest.raises(ValidationError, match="Learning goal is too long"):
            curriculum_generator.generate_curriculum(long_goal)
    
    def test_curriculum_validation(self, curriculum_generator):
        """Test validation of curriculum structure."""
        # Test with missing required sections
        invalid_curriculum = "Day 1:\n- Topics: Test\n- Grammar: Test"
        with pytest.raises(ValueError, match="Missing required sections"):
            curriculum_generator._validate_curriculum_structure(invalid_curriculum)
        
        # Test with empty day content
        empty_day = "Day 1:\n\nDay 2:\n- Topics: Test"
        with pytest.raises(ValueError, match="Empty day content"):
            curriculum_generator._validate_curriculum_structure(empty_day)
