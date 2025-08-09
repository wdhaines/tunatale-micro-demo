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

# Note: Individual test modules are discovered and imported by pytest automatically
# Do not import them here as it creates dependency issues
