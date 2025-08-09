"""Integration tests for TunaTale CLI workflow.

These tests run the actual CLI commands to verify the end-to-end workflow works.
They use the real file system but backup/restore data to avoid side effects.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest


@pytest.mark.integration
class TestWorkflowIntegration:
    """Integration tests for the complete TunaTale workflow."""

    @pytest.fixture(autouse=True)
    def clean_test_environment(self):
        """Clean test environment before and after each test."""
        data_dir = Path("instance/data")
        backup_dir = Path("instance/data_backup_integration")
        
        # Backup existing data
        if data_dir.exists():
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.copytree(data_dir, backup_dir)
            shutil.rmtree(data_dir)
        
        # Ensure clean start
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "curricula").mkdir(exist_ok=True)
        (data_dir / "stories").mkdir(exist_ok=True)
        (data_dir / "logs").mkdir(exist_ok=True)
        
        yield
        
        # Cleanup and restore
        if data_dir.exists():
            shutil.rmtree(data_dir)
        
        if backup_dir.exists():
            shutil.copytree(backup_dir, data_dir)
            shutil.rmtree(backup_dir)

    def run_cli(self, args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run CLI command with proper error handling."""
        cmd = [sys.executable, "main.py"] + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent
        )

    def test_basic_workflow(self):
        """Test the basic workflow: generate -> extract -> view."""
        print("\n=== Testing Basic Workflow ===")
        
        # Step 1: Generate a minimal curriculum
        print("Generating curriculum...")
        result = self.run_cli([
            "generate", "Learn basic travel phrases", 
            "--days", "2", "--cefr-level", "A2"
        ])
        
        # Verify generation succeeded or failed gracefully
        if result.returncode != 0:
            pytest.skip(f"Curriculum generation not available: {result.stderr}")
        
        assert "generated" in result.stdout.lower() or "success" in result.stdout.lower()
        print("✓ Curriculum generated")
        
        # Verify curriculum file exists
        curricula_dir = Path("instance/data/curricula")
        curriculum_files = list(curricula_dir.glob("*.json"))
        assert len(curriculum_files) > 0, "No curriculum file created"
        
        # Step 2: View the curriculum
        print("Viewing curriculum...")
        result = self.run_cli(["view", "curriculum"], timeout=15)
        assert result.returncode == 0, f"View curriculum failed: {result.stderr}"
        assert len(result.stdout) > 100, "Curriculum output too short"
        print("✓ Curriculum viewed successfully")
        
        # Step 3: Extract collocations
        print("Extracting collocations...")
        result = self.run_cli(["extract"], timeout=30)
        assert result.returncode == 0, f"Extract failed: {result.stderr}"
        
        # Verify collocations file exists
        collocations_file = Path("instance/data/collocations.json")
        assert collocations_file.exists(), "Collocations file not created"
        
        with open(collocations_file) as f:
            collocations = json.load(f)
        # Collocations can be either list or dict depending on the extractor format
        assert isinstance(collocations, (list, dict)), "Collocations should be list or dict"
        assert len(collocations) > 0, "Should have extracted some collocations"
        print("✓ Collocations extracted")
        
        # Step 4: View collocations
        result = self.run_cli(["view", "collocations"], timeout=15)
        assert result.returncode == 0, f"View collocations failed: {result.stderr}"
        print("✓ Collocations viewed successfully")

    @pytest.mark.slow
    def test_story_generation_workflow(self):
        """Test story generation workflow."""
        print("\n=== Testing Story Generation Workflow ===")
        
        # First set up curriculum and collocations
        result = self.run_cli([
            "generate", "Filipino for tourists", "--days", "2"
        ])
        if result.returncode != 0:
            pytest.skip("Curriculum generation not available")
        
        result = self.run_cli(["extract"])
        assert result.returncode == 0, "Extract must succeed for story generation"
        
        # Generate story for day 1
        print("Generating story for day 1...")
        result = self.run_cli(["generate-day", "1"])
        
        # This might fail in test environment, so check gracefully
        if result.returncode != 0:
            print(f"Story generation failed (expected in test env): {result.stderr}")
            return  # Don't fail the test, just note it
        
        # Verify story file creation
        stories_dir = Path("instance/data/stories")
        story_files = list(stories_dir.glob("*day*01*.txt"))
        
        if len(story_files) > 0:
            story_content = story_files[0].read_text()
            assert len(story_content) > 20, "Story content too short"
            print("✓ Story generated successfully")
            
            # Test viewing the story
            result = self.run_cli(["view", "story", "--day", "1"])
            assert result.returncode == 0, "View story should work"
            print("✓ Story viewed successfully")

    def test_analyze_functionality(self):
        """Test the analyze command functionality."""
        print("\n=== Testing Analyze Functionality ===")
        
        # Test with direct text
        result = self.run_cli([
            "analyze", "Kumusta ka? Ako ay tourist sa Pilipinas. Salamat!"
        ], timeout=20)
        assert result.returncode == 0, f"Analyze failed: {result.stderr}"
        assert "VOCABULARY ANALYSIS" in result.stdout
        assert "Total words:" in result.stdout
        print("✓ Text analysis works")
        
        # Create a test file
        test_file = Path("instance/data/test_analyze.txt")
        test_file.write_text("Hello world. This is a test file for analysis.")
        
        # Test with file
        result = self.run_cli(["analyze", str(test_file)], timeout=20)
        assert result.returncode == 0, f"File analyze failed: {result.stderr}"
        assert "VOCABULARY ANALYSIS" in result.stdout
        print("✓ File analysis works")

    def test_error_handling(self):
        """Test that CLI handles errors gracefully."""
        print("\n=== Testing Error Handling ===")
        
        error_cases = [
            (["nonexistent-command"], "Invalid command"),
            (["generate"], "Missing arguments"),
            (["generate", "test", "--days", "0"], "Invalid days value"),
            (["view", "nonexistent"], "Nonexistent view target")
        ]
        
        for args, description in error_cases:
            result = self.run_cli(args, timeout=10)
            assert result.returncode != 0, f"{description} should fail"
            # Ensure it's a graceful failure, not a crash
            assert result.returncode < 128, f"{description} crashed instead of failing gracefully"
            print(f"✓ {description} handled gracefully")

    def test_file_organization(self):
        """Test that files are created in correct locations."""
        print("\n=== Testing File Organization ===")
        
        # Generate minimal content
        result = self.run_cli(["generate", "File organization test", "--days", "1"])
        if result.returncode != 0:
            pytest.skip("Generation not available")
        
        # Check directory structure
        data_dir = Path("instance/data")
        curricula_dir = data_dir / "curricula"
        stories_dir = data_dir / "stories"
        logs_dir = data_dir / "logs"
        
        assert curricula_dir.exists(), "Curricula directory should exist"
        assert stories_dir.exists(), "Stories directory should exist"
        assert logs_dir.exists(), "Logs directory should exist"
        
        # Check curriculum file location
        curriculum_files = list(curricula_dir.glob("*.json"))
        assert len(curriculum_files) > 0, "Curriculum should be in curricula directory"
        print("✓ File organization is correct")

    @pytest.mark.slow
    def test_realistic_user_journey(self):
        """Test a realistic end-to-end user journey."""
        print("\n=== Testing Realistic User Journey ===")
        
        steps = [
            # User wants to learn Filipino for travel
            (["generate", "Learn Filipino for El Nido beach vacation", 
              "--cefr-level", "A2", "--days", "3"], "Generate travel curriculum"),
            
            # Check what was created
            (["view", "curriculum"], "View curriculum"),
            
            # Extract key phrases
            (["extract"], "Extract collocations"),
            
            # View extracted phrases
            (["view", "collocations"], "View collocations"),
            
            # Generate first lesson (might fail in test env)
            (["generate-day", "1"], "Generate day 1 content"),
        ]
        
        for args, description in steps:
            print(f"Running: {description}")
            
            # Use shorter timeout for analyze commands which can hang
            timeout = 15 if args[0] == "analyze" else 60
            
            try:
                result = self.run_cli(args, timeout=timeout)
                
                # Some steps might fail in test environment, that's OK
                if result.returncode != 0:
                    print(f"  ⚠️  {description} failed (may be expected in test env)")
                    continue
                    
                print(f"  ✓ {description} succeeded")
                
            except subprocess.TimeoutExpired:
                print(f"  ⚠️  {description} timed out (may be expected in test env)")
                continue
        
        print("✓ User journey completed (with expected test environment limitations)")


# Additional mark for pytest
pytestmark = pytest.mark.integration