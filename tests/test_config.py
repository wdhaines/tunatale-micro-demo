from pathlib import Path

# Test directories
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent
TEST_DATA_DIR = TEST_DIR / "test_data"

# Ensure test directories exist
TEST_DATA_DIR.mkdir(exist_ok=True)

# Configuration for testing
DATA_DIR = TEST_DATA_DIR
PROMPTS_DIR = PROJECT_ROOT / "prompts"
MOCK_RESPONSES_DIR = TEST_DATA_DIR / "mock_responses"

# Create necessary directories
DATA_DIR.mkdir(exist_ok=True)
PROMPTS_DIR.mkdir(exist_ok=True)
MOCK_RESPONSES_DIR.mkdir(exist_ok=True)
(DATA_DIR / 'generated_content').mkdir(exist_ok=True)
