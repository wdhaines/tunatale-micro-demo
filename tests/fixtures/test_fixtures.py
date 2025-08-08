"""
Test fixtures and mock data for TunaTale testing.

This module provides comprehensive test fixtures that support:
1. Mock data for all components (curriculum, SRS, stories)
2. Test scenarios covering critical issues from CLAUDE.md
3. Strategy-aware test data for Go Wider vs Go Deeper framework
4. Data quality test cases (corrupted vs clean data)
5. Integration test fixtures
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any, List
import tempfile
from datetime import datetime

from curriculum_models import Curriculum, CurriculumDay
from srs_tracker import SRSTracker, CollocationStatus  
from content_strategy import ContentStrategy, DifficultyLevel, EnhancedStoryParams


# =============================================================================
# MOCK DATA CONSTANTS
# =============================================================================

# Clean collocation data
CLEAN_COLLOCATIONS = [
    "kumusta po kayo",
    "salamat po",  
    "paano po",
    "saan po",
    "magkano po ito",
    "pwede po bang",
    "tara na po",
    "magandang umaga",
    "magandang hapon", 
    "ingat po kayo"
]

# Corrupted collocation data (based on CLAUDE.md Issue 1.1)
CORRUPTED_COLLOCATIONS = [
    "ito po\\npo\\nito\\nto\\ni\\nito\\nito po\\nito po",
    "kumusta po\\npo\\nkumusta\\nkum\\nkumusta po", 
    "salamat po\\npo\\nsal\\nsamat\\nsalamat po",
    "magandang umaga\\nang\\nga\\ngandang\\numaga"
]

# Invalid SRS data (based on CLAUDE.md Issue 1.2)
INVALID_SRS_COLLOCATIONS = [
    "mango shake, they, the waiter, asks, tagalog-female-1",
    "voice-tag-english-1",
    "audio-marker-tagalog-male-2",
    "system-generated-pause-1000ms"
]

# Sample story content for testing
SAMPLE_STORY_CONTENT = {
    "clean_story": """
**Pagkain sa Palengke**

Si Maria ay pumunta sa palengke upang bumili ng mga gulay.

"Kumusta po kayo?" bati niya sa tindera.

"Mabuti naman po, salamat. Ano po ang kailangan ninyo?" sagot ng tindera.

"Pwede po bang makita ang mga kamatis?" tanong ni Maria.

"Sige po, dito po. Magkano po ba ang gusto ninyo?" 

"Isang kilo po. Magkano po ito?"

"Singkwenta pesos po ang isang kilo."

"Sige po, kukunin ko po. Salamat po!"

"Walang anuman po. Ingat po kayo!"
    """.strip(),
    
    "story_with_voice_tags": """
**Restaurant Visit**

[Voice: tagalog-female-1] Maria walked into the restaurant.

"Kumusta po!" she said to the waiter.

[Voice: tagalog-male-1] "Mabuti po, salamat. Table for how many?"

[Audio pause: 1000ms]

"Dalawa po," Maria replied.

[System: Generate audio for "Dalawa po"]
    """.strip()
}

# Curriculum test data (both dict and list formats)
DICT_FORMAT_CURRICULUM = {
    "learning_objective": "Learn Filipino restaurant conversations",
    "target_language": "Filipino",
    "learner_level": "A2", 
    "presentation_length": 30,
    "days": {
        "day_1": {
            "day": 1,
            "title": "Basic Greetings",
            "focus": "Introductory conversations", 
            "collocations": ["kumusta po", "salamat po"],
            "presentation_phrases": ["hello", "thank you"],
            "learning_objective": "Learn basic greetings"
        },
        "day_2": {
            "day": 2,
            "title": "Ordering Food",
            "focus": "Restaurant vocabulary",
            "collocations": ["pwede po bang", "magkano po"],
            "presentation_phrases": ["can I have", "how much"],
            "learning_objective": "Order food politely"
        }
    }
}

LIST_FORMAT_CURRICULUM = {
    "learning_objective": "Learn Filipino restaurant conversations",
    "target_language": "Filipino", 
    "learner_level": "A2",
    "presentation_length": 30,
    "days": [
        {
            "day": 1,
            "title": "Basic Greetings", 
            "focus": "Introductory conversations",
            "collocations": ["kumusta po", "salamat po"],
            "presentation_phrases": ["hello", "thank you"],
            "learning_objective": "Learn basic greetings",
            "story_guidance": ""
        },
        {
            "day": 2,
            "title": "Ordering Food",
            "focus": "Restaurant vocabulary", 
            "collocations": ["pwede po bang", "magkano po"],
            "presentation_phrases": ["can I have", "how much"],
            "learning_objective": "Order food politely",
            "story_guidance": ""
        }
    ]
}


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create subdirectories
        (temp_path / 'curricula').mkdir()
        (temp_path / 'stories').mkdir()
        (temp_path / 'srs').mkdir()
        (temp_path / 'mock_responses').mkdir()
        
        yield temp_path


@pytest.fixture
def clean_curriculum():
    """Fixture providing a clean, valid curriculum."""
    day1 = CurriculumDay(
        day=1,
        title="Basic Greetings",
        focus="Introductory conversations",
        collocations=["kumusta po", "salamat po"],
        presentation_phrases=["hello", "thank you"], 
        learning_objective="Learn basic greetings",
        story_guidance="Keep it simple and polite"
    )
    
    day2 = CurriculumDay(
        day=2,
        title="Market Shopping", 
        focus="Shopping vocabulary",
        collocations=["magkano po", "pwede po bang"],
        presentation_phrases=["how much", "can I"],
        learning_objective="Shop at the market",
        story_guidance="Include price negotiation"
    )
    
    day3 = CurriculumDay(
        day=3,
        title="Restaurant Dining",
        focus="Ordering food",
        collocations=["gusto ko po", "masarap po"],
        presentation_phrases=["I would like", "delicious"],
        learning_objective="Order food at restaurants", 
        story_guidance="Show polite ordering process"
    )
    
    return Curriculum(
        learning_objective="Filipino conversation basics",
        target_language="Filipino",
        learner_level="A2",
        presentation_length=30,
        days=[day1, day2, day3]
    )


@pytest.fixture
def corrupted_curriculum_data():
    """Fixture providing curriculum data with quality issues."""
    return {
        "learning_objective": "Test corrupted data handling",
        "target_language": "Filipino",
        "learner_level": "A2",
        "presentation_length": 30,
        "days": {  # Dict format (inconsistent)
            "day_1": {
                "day": 1,
                "title": "Corrupted Data Test",
                "focus": "Data quality issues",
                "collocations": [
                    "kumusta po",  # Clean
                    "ito po\\npo\\nito\\nto\\ni\\nito\\nito po\\nito po",  # Corrupted
                    "salamat po"   # Clean
                ],
                "presentation_phrases": [
                    "good morning",  # Clean
                    "tagalog-female-1",  # Voice tag (invalid)
                    "hello"  # Clean
                ],
                "learning_objective": "Test data validation"
                # Missing story_guidance field
            }
        }
    }


@pytest.fixture 
def srs_tracker_with_data(temp_data_dir):
    """Fixture providing SRS tracker with test data."""
    tracker = SRSTracker(data_dir=str(temp_data_dir / 'srs'), filename='test_srs.json')
    
    # Add collocations with different review states
    collocations_data = [
        ("kumusta po", 1, 0, 1.0),      # New, due day 1
        ("salamat po", 2, 1, 1.2),      # Reviewed once, due day 2  
        ("magkano po", 5, 2, 1.5),      # Reviewed twice, due day 5
        ("pwede po bang", 10, 3, 2.0),  # Well-reviewed, due day 10
        ("tara na po", 1, 0, 0.8)       # New, low stability
    ]
    
    for text, next_review_day, review_count, stability in collocations_data:
        tracker.collocations[text] = CollocationStatus(
            text=text,
            first_seen_day=1,
            last_seen_day=max(1, next_review_day - 1),
            appearances=[1] + list(range(2, next_review_day)),
            review_count=review_count,
            next_review_day=next_review_day,
            stability=stability
        )
    
    tracker._save_state()
    return tracker


@pytest.fixture
def strategy_test_params():
    """Fixture providing test parameters for different strategies."""
    return {
        'wider': EnhancedStoryParams(
            learning_objective="Restaurant scenario (new context)",
            language="Filipino",
            cefr_level="A2",
            phase=5,
            content_strategy=ContentStrategy.WIDER,
            difficulty_level=DifficultyLevel.BASIC,
            source_day=1,
            new_vocabulary=["mesa", "order", "bill"],
            review_collocations=["kumusta po", "salamat po"]
        ),
        
        'deeper': EnhancedStoryParams(
            learning_objective="Advanced market negotiations", 
            language="Filipino",
            cefr_level="B1",
            phase=7,
            content_strategy=ContentStrategy.DEEPER,
            difficulty_level=DifficultyLevel.INTERMEDIATE,
            source_day=2,
            complexity_target="native_expressions",
            new_vocabulary=["makakuha ng magandang presyo"],
            review_collocations=["magkano po", "pwede po bang", "tara na po", "salamat po"]
        ),
        
        'balanced': EnhancedStoryParams(
            learning_objective="Standard lesson progression",
            language="Filipino", 
            cefr_level="A2",
            phase=3,
            content_strategy=ContentStrategy.BALANCED,
            difficulty_level=DifficultyLevel.BASIC,
            new_vocabulary=["opo", "hindi po"],
            review_collocations=["kumusta po"]
        )
    }


# =============================================================================
# MOCK DATA GENERATION FUNCTIONS  
# =============================================================================

def create_mock_llm_responses() -> Dict[str, Dict[str, Any]]:
    """Create mock LLM responses for testing."""
    return {
        'story_generation': {
            'choices': [{
                'message': {
                    'content': SAMPLE_STORY_CONTENT['clean_story'],
                    'role': 'assistant'
                }
            }]
        },
        
        'curriculum_generation': {
            'choices': [{
                'message': {
                    'content': json.dumps(LIST_FORMAT_CURRICULUM),
                    'role': 'assistant'
                }
            }]
        },
        
        'empty_response': {
            'choices': [{
                'message': {
                    'content': '',
                    'role': 'assistant'
                }
            }]
        }
    }


def create_test_stories() -> Dict[str, str]:
    """Create test story content for various scenarios."""
    return {
        'day_1_greetings': """
**Pagkakakilala sa Palengke**

Si Ana ay bagong dating sa Manila. Pumunta siya sa palengke para bumili ng pagkain.

"Kumusta po kayo?" bati niya sa tindera ng prutas.

"Mabuti naman po, salamat. Bago po kayo dito?" tanong ng tindera.

"Opo, kakadating ko lang po. Pwede po bang makita ang mga mangga?"

"Sige po, dito po ang mga fresh na mangga. Masarap po ito."

"Magkano po ang isang kilo?"

"Singkwenta pesos po."

"Sige po, kukunin ko po. Salamat po!"

"Walang anuman po. Ingat po kayo!"
        """.strip(),
        
        'day_2_shopping': """
**Pamimili sa Grocery**

Si Maria ay kailangan ng mga groceries para sa hapunan.

"Excuse me po, saan po ang canned goods?" tanong niya sa staff.

"Doon po sa aisle 3. Ano po ang hinanhanap ninyo?"

"Corned beef po at sardinas. Meron po ba kayong brand na Del Monte?"

"Meron po. Dito po sa shelf na ito. Magkano po ba ang budget ninyo?"

"Dalawang daang pesos po lang. Enough na po ba yun?"

"Oo po, kasya na po yan. Ito po ang Del Monte corned beef, saka ito ang sardinas."

"Perfect po! Salamat po sa tulong."

"Walang anuman po. May kailangan pa po ba kayo?"

"Wala na po. Salamat ulit!"
        """.strip(),
        
        'day_3_restaurant': """
**Sa Restaurant**

Pumunta sina Carlos at Elena sa isang Filipino restaurant para sa dinner date nila.

"Good evening po! Table for two po?" bati ng waiter.

"Opo, pwede po bang sa may bintana?" sagot ni Carlos.

"Sige po, dito po kayo. Ito po ang menu. Ano po ang gusto ninyong inumin?"

"Dalawang iced tea po," sagot ni Elena.

"Sige po. Ready na po ba kayong mag-order ng pagkain?"

"Gusto namin po ng adobo, saka sisig. Meron din po ba kayong kare-kare?"

"Meron po. Gusto ninyo po ba ng rice?"

"Opo, dalawang cups po ng kanin. Salamat po!"

"Walang anuman po. Ilalabas po namin sa loob ng 15 minutes."
        """.strip()
    }


def create_progression_test_data() -> Dict[str, Any]:
    """Create test data showing learning progression across strategies."""
    return {
        'base_curriculum': {
            'day_1': {
                'collocations': ['kumusta po', 'salamat po'],
                'complexity_level': 'basic',
                'context': 'greetings'
            }
        },
        
        'wider_progression': {
            'day_5': {  # New scenario based on day 1
                'collocations': ['kumusta po', 'salamat po', 'mesa para dos', 'bill po'],
                'complexity_level': 'basic',  # Same complexity
                'context': 'restaurant_greetings',  # New context
                'source_day': 1
            }
        },
        
        'deeper_progression': {
            'day_8': {  # Enhanced version of day 1  
                'collocations': ['kumusta po naman kayo', 'maraming salamat po', 
                               'pagpalain po kayo'],
                'complexity_level': 'intermediate',  # Higher complexity
                'context': 'greetings',  # Same context
                'source_day': 1
            }
        }
    }


# =============================================================================
# DATA VALIDATION TEST HELPERS
# =============================================================================

def create_data_quality_test_cases() -> Dict[str, Any]:
    """Create test cases for data quality validation."""
    return {
        'clean_data': {
            'collocations': CLEAN_COLLOCATIONS,
            'expected_issues': 0,
            'description': 'Valid Filipino collocations'
        },
        
        'corrupted_syllables': {
            'collocations': CORRUPTED_COLLOCATIONS,
            'expected_issues': len(CORRUPTED_COLLOCATIONS),
            'description': 'Collocations with embedded syllable data'
        },
        
        'invalid_srs_data': {
            'collocations': INVALID_SRS_COLLOCATIONS,
            'expected_issues': len(INVALID_SRS_COLLOCATIONS), 
            'description': 'SRS data containing voice tags and system markers'
        },
        
        'mixed_data': {
            'collocations': CLEAN_COLLOCATIONS[:3] + CORRUPTED_COLLOCATIONS[:2] + INVALID_SRS_COLLOCATIONS[:1],
            'expected_issues': 3,  # 2 corrupted + 1 invalid
            'description': 'Mixed clean and problematic data'
        }
    }


# =============================================================================
# INTEGRATION TEST FIXTURES
# =============================================================================

@pytest.fixture
def full_system_mock(temp_data_dir, clean_curriculum, srs_tracker_with_data):
    """Fixture providing a complete mocked system for integration testing."""
    # Save curriculum to temp directory
    curriculum_path = temp_data_dir / 'curricula' / 'test_curriculum.json'
    clean_curriculum.save(curriculum_path)
    
    # Create story files
    stories = create_test_stories()
    stories_dir = temp_data_dir / 'stories'
    for i, (story_name, content) in enumerate(stories.items(), 1):
        story_path = stories_dir / f'story_day{i}_test.txt'
        story_path.write_text(content, encoding='utf-8')
    
    # Create mock responses
    responses = create_mock_llm_responses()
    mock_responses_dir = temp_data_dir / 'mock_responses'
    for response_name, content in responses.items():
        response_path = mock_responses_dir / f'{response_name}.json'
        response_path.write_text(json.dumps(content, indent=2), encoding='utf-8')
    
    return {
        'data_dir': temp_data_dir,
        'curriculum_path': curriculum_path,
        'curriculum': clean_curriculum,
        'srs_tracker': srs_tracker_with_data,
        'stories': stories,
        'mock_responses': responses
    }


@pytest.fixture 
def content_generator_mock(full_system_mock):
    """Fixture providing a mocked ContentGenerator for testing."""
    from unittest.mock import MagicMock
    
    generator = MagicMock()
    
    # Mock story generation
    generator.generate_story.return_value = full_system_mock['stories']['day_1_greetings']
    generator.generate_enhanced_story.return_value = full_system_mock['stories']['day_1_greetings']
    generator.generate_day_with_srs.return_value = full_system_mock['stories']['day_1_greetings']
    
    # Mock curriculum loading
    generator._load_curriculum.return_value = full_system_mock['curriculum']
    
    # Mock SRS integration
    generator.srs = full_system_mock['srs_tracker']
    
    # Mock LLM responses
    generator.llm.get_response.return_value = full_system_mock['mock_responses']['story_generation']
    
    return generator


# =============================================================================
# PERFORMANCE TEST DATA
# =============================================================================

def create_large_dataset_for_performance_testing(size: int = 1000) -> Dict[str, Any]:
    """Create large dataset for performance testing."""
    large_curriculum_days = []
    
    for i in range(1, size + 1):
        day = {
            "day": i,
            "title": f"Day {i} - Performance Test",
            "focus": f"Focus area {i % 10}",  # Cycle through 10 focus areas
            "collocations": [f"colloc_{i}_{j}" for j in range(1, 6)],  # 5 per day
            "presentation_phrases": [f"phrase_{i}"],
            "learning_objective": f"Objective for day {i}",
            "story_guidance": f"Guidance for day {i}"
        }
        large_curriculum_days.append(day)
    
    return {
        "learning_objective": f"Large curriculum with {size} days",
        "target_language": "Filipino",
        "learner_level": "A2", 
        "presentation_length": 30,
        "days": large_curriculum_days
    }


# =============================================================================
# UTILITY FUNCTIONS FOR TESTS
# =============================================================================

def assert_curriculum_integrity(curriculum: Curriculum) -> None:
    """Assert that curriculum maintains data integrity."""
    assert curriculum.learning_objective
    assert curriculum.target_language
    assert curriculum.learner_level
    assert curriculum.presentation_length > 0
    assert len(curriculum.days) > 0
    
    for day in curriculum.days:
        assert day.day > 0
        assert day.title
        assert day.focus  
        assert isinstance(day.collocations, list)
        assert isinstance(day.presentation_phrases, list)
        assert day.learning_objective
        assert hasattr(day, 'story_guidance')  # Should have this field


def assert_srs_data_quality(srs_tracker: SRSTracker) -> None:
    """Assert that SRS tracker contains only valid collocation data."""
    invalid_patterns = [
        'tagalog-female-1', 'tagalog-male-1', 'english-1',
        'voice-tag', 'audio-marker', 'system-generated'
    ]
    
    for collocation_text in srs_tracker.get_all_collocations():
        # Should not contain voice tags or system markers
        assert not any(pattern in collocation_text.lower() for pattern in invalid_patterns), \
            f"SRS contains invalid data: {collocation_text}"
        
        # Should not contain embedded syllables  
        assert '\\n' not in collocation_text, \
            f"SRS contains embedded syllables: {collocation_text}"
        
        # Should be non-empty string
        assert collocation_text.strip(), "SRS contains empty collocation"


def assert_strategy_consistency(params: EnhancedStoryParams) -> None:
    """Assert that strategy parameters are consistent with strategy type."""
    from content_strategy import get_strategy_config
    
    config = get_strategy_config(params.content_strategy)
    
    # Check vocabulary limits
    if params.new_vocabulary:
        assert len(params.new_vocabulary) <= config['max_new_collocations'], \
            f"Too many new collocations for {params.content_strategy.value} strategy"
    
    if params.review_collocations:
        assert len(params.review_collocations) >= config['min_review_collocations'], \
            f"Not enough review collocations for {params.content_strategy.value} strategy"
    
    # Check strategy-specific requirements
    if params.content_strategy == ContentStrategy.DEEPER:
        assert params.source_day is not None, "DEEPER strategy requires source_day"
        
    elif params.content_strategy == ContentStrategy.WIDER:
        assert params.source_day is not None, "WIDER strategy requires source_day"