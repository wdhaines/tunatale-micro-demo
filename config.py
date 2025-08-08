import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).parent
INSTANCE_DIR = BASE_DIR / 'instance'
DATA_DIR = INSTANCE_DIR / 'data'

# Application data directories
CURRICULA_DIR = DATA_DIR / 'curricula'  # Directory for storing curriculum files
STORIES_DIR = DATA_DIR / 'stories'  # Directory for storing generated stories
SRS_DIR = DATA_DIR / 'srs'  # Directory for Spaced Repetition System data
MOCK_RESPONSES_DIR = DATA_DIR / 'mock_responses'  # Directory for mock LLM responses
UPLOAD_DIR = DATA_DIR / 'uploads'  # Directory for user uploads (e.g., transcripts)
PROMPTS_DIR = BASE_DIR / 'prompts'  # Keep prompts in project root as they are part of the code

# Logging configuration
LOGS_DIR = DATA_DIR / 'logs'
DEBUG_LOG_PATH = LOGS_DIR / 'debug.log'

# Create directories if they don't exist
INSTANCE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
CURRICULA_DIR.mkdir(exist_ok=True)
STORIES_DIR.mkdir(exist_ok=True)
SRS_DIR.mkdir(exist_ok=True)
MOCK_RESPONSES_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
PROMPTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Default configuration
DEFAULT_STORY_LENGTH = int(os.getenv('DEFAULT_STORY_LENGTH', '500'))  # Default to 500 words if not set

# File paths
CURRICULUM_PATH = DATA_DIR / 'curriculum_processed.json'
COLLOCATIONS_PATH = DATA_DIR / 'collocations.json'
