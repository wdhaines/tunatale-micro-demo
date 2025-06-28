"""Pytest configuration for the project."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import mock config before any other imports
from tests import mock_config

# Patch the config module before any other imports
import sys
sys.modules['config'] = mock_config

# Import the config (which will be our mock)
import config

# Verify the patch worked
assert config.DATA_DIR == mock_config.DATA_DIR, "Config patching failed!"

# Set up test environment variables
os.environ["TESTING"] = "1"
os.environ["PYTHONPATH"] = str(PROJECT_ROOT)
