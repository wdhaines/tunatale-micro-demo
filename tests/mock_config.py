import os
from pathlib import Path

# Test directories
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent
TEST_DATA_DIR = TEST_DIR / "test_data"

# Ensure test directories exist
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Base directory structure matching the original config
BASE_DIR = PROJECT_ROOT  # Point to project root for test environment
INSTANCE_DIR = TEST_DATA_DIR / 'instance'
DATA_DIR = INSTANCE_DIR / 'data'

# Application data directories
CURRICULA_DIR = DATA_DIR / 'curricula'
STORIES_DIR = DATA_DIR / 'stories'  # Directory for storing generated stories
SRS_DIR = DATA_DIR / 'srs'  # Directory for Spaced Repetition System data
MOCK_RESPONSES_DIR = DATA_DIR / 'mock_responses'  # Directory for mock LLM responses
UPLOAD_DIR = DATA_DIR / 'uploads'  # Directory for user uploads (e.g., transcripts)
PROMPTS_DIR = TEST_DIR / "prompts"  # Keep prompts in test directory for tests

# Logging configuration
LOGS_DIR = DATA_DIR / 'logs'
DEBUG_LOG_PATH = LOGS_DIR / 'debug.log'

# Create necessary directories
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
CURRICULA_DIR.mkdir(parents=True, exist_ok=True)
STORIES_DIR.mkdir(parents=True, exist_ok=True)
SRS_DIR.mkdir(parents=True, exist_ok=True)
MOCK_RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Default configuration matching the original config
DEFAULT_STORY_LENGTH = int(os.getenv('DEFAULT_STORY_LENGTH', '500'))  # Match original default
DEFAULT_CEFR_LEVEL = 'A2'
DEFAULT_TARGET_LANGUAGE = 'English'
DEFAULT_NUM_DAYS = 30
DEFAULT_PRESENTATION_LENGTH = 30  # minutes

# File paths from the original config
CURRICULUM_PATH = CURRICULA_DIR / 'curriculum.json'
COLLOCATIONS_PATH = DATA_DIR / 'collocations.json'  # Keeping in root for backward compatibility
SRS_STATUS_PATH = SRS_DIR / 'srs_status.json'
VOCABULARY_PATH = DATA_DIR / 'a2_flat_vocabulary.json'  # This should eventually be moved to a vocab directory

# Create empty files if they don't exist
for path in [CURRICULUM_PATH, COLLOCATIONS_PATH, SRS_STATUS_PATH, VOCABULARY_PATH]:
    if not path.exists():
        if path == SRS_STATUS_PATH:
            path.write_text('{"current_day": 1, "collocations": {}}')
        elif path == VOCABULARY_PATH:
            path.write_text('{"test": 1}')
        else:
            path.write_text('{}')

# Set environment variables for consistent testing
os.environ['DEFAULT_STORY_LENGTH'] = str(DEFAULT_STORY_LENGTH)
os.environ['DEFAULT_CEFR_LEVEL'] = DEFAULT_CEFR_LEVEL

# Add any other constants that might be imported from config
# These are used in various parts of the application
STORY_TEMPLATE = """
# {title}

{content}
"""

# Add any other configuration values that might be needed
CONFIG = {
    'debug': True,
    'testing': True,
    'data_dir': str(DATA_DIR),
    'prompts_dir': str(PROMPTS_DIR),
    'mock_responses_dir': str(MOCK_RESPONSES_DIR),
}

# Make sure all required directories exist
for path in [DATA_DIR, PROMPTS_DIR, MOCK_RESPONSES_DIR]:
    path.mkdir(parents=True, exist_ok=True)
