#!/usr/bin/env python3
"""
Fast test runner for Phase 3 tests.

Runs only unit tests and skips slow integration tests to avoid timeouts.
"""
import subprocess
import sys
from pathlib import Path


def run_fast_tests():
    """Run fast unit tests only."""
    
    # Run unit tests with shorter timeout
    cmd = [
        sys.executable, "-m", "pytest", 
        # Only unit tests
        "-m", "unit",
        # Specific test files  
        "tests/test_phase3_integration.py::TestPhase3BasicFunctionality",
        "tests/test_phase3_cli.py::TestPhase3CLICommands",
        # Fast execution options
        "-v", "--tb=short", 
        "--timeout=10",  # 10 second timeout for unit tests
        "-x",  # Stop on first failure
    ]
    
    print("Running fast Phase 3 unit tests...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, timeout=300)  # 5 minute overall timeout
        return result.returncode
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out after 5 minutes")
        return 1


def run_integration_tests():
    """Run integration tests separately with longer timeout."""
    
    cmd = [
        sys.executable, "-m", "pytest",
        # Only integration tests
        "-m", "integration", 
        # Longer timeout
        "--timeout=60",
        "-v", "--tb=short",
        # Run fewer at a time
        "--maxfail=3"
    ]
    
    print("Running Phase 3 integration tests...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, timeout=600)  # 10 minute overall timeout
        return result.returncode
    except subprocess.TimeoutExpired:
        print("❌ Integration tests timed out after 10 minutes")
        return 1


def main():
    """Main test runner."""
    if len(sys.argv) > 1 and sys.argv[1] == "integration":
        return run_integration_tests()
    else:
        return run_fast_tests()


if __name__ == "__main__":
    sys.exit(main())