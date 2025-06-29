"""Test package for TunaTale."""

import os
import sys
from pathlib import Path

# Set up test environment before any other imports
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent

# Add project root to Python path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set up test environment variables
os.environ["TESTING"] = "1"
os.environ["PYTHONPATH"] = str(PROJECT_ROOT)

# Import and set up mock config
from tests import mock_config

# Patch the config module before any other imports
import sys
sys.modules['config'] = mock_config

# Import the config (which will be our mock)
import config

# Verify the patch worked
assert config.DATA_DIR == mock_config.DATA_DIR, "Config patching failed!"

# Now import the rest of the test modules
from . import test_curriculum_models
from . import test_curriculum_service
from . import test_main
from . import test_mock_llm
from . import test_srs_integration
from . import test_story_generator
from . import test_story_generator_vocab
from . import test_story_prompt_template
from . import test_text_utils
